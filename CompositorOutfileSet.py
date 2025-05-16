from sys import prefix
import bpy
import ctypes

# 常量和全局变量
CRYPTO_KEYWORDS = {'cryptomatte', 'crypto'}
DATA_CATEGORIES = {
    'Depth', 'Mist', 'Position', 'Normal', 'Vector', 'UV',
    'IndexOB', 'IndexMA', 'Debug Sample Count', 'Denoising Depth',
    'Denoising Normal', 'Denoising Albedo'
}
RGB_CATEGORIES = {
    'Image', 'Alpha', 'DiffDir', 'DiffInd', 'DiffCol', 'GlossDir',
    'GlossInd', 'GlossCol', 'TransDir', 'TransInd', 'TransCol',
    'VolumeDir', 'VolumeInd', 'Emit', 'Env', 'AO', 'Shadow Catcher',
    'Noisy Image', 'Noisy Shadow Catcher', 'Shadow', 'Transp'
}
NODE_TYPES = ['rgb', 'data', 'cryptomatte', 'shaderaov', 'lightgroup']

"""
节点布局类
"""
class NodeLayoutManager:
    def __init__(self, ui_scale):
        self.ui_scale = ui_scale

    def calculate_node_height(self, node):
        """准确计算节点高度"""
        height = node.dimensions[1] / self.ui_scale / self.get_system_scaling()
        return height + 20

    def get_nodes_bound(self, user_nodes):
        """节点系统原点在左上角"""
        if not user_nodes:
            return [0, 0, 0, 0]

        # 初始化首个节点的边界
        first_node = user_nodes[0]
        left = first_node.location.x
        right = left + first_node.width
        top = first_node.location.y
        bottom = top - self.calculate_node_height(first_node)

        # 遍历剩余节点更新边界
        for node in user_nodes[1:]:
            node_left = node.location.x
            node_right = node_left + node.width
            node_top = node.location.y
            node_bottom = node_top - self.calculate_node_height(node)

            left = min(left, node_left)
            right = max(right, node_right)
            top = max(top, node_top)
            bottom = min(bottom, node_bottom)

        return [left, right, top, bottom]

    def get_system_scaling(self):
        """获取Windows系统级缩放比例"""
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            scale_factor = ctypes.windll.shcore.GetScaleFactorForDevice(
                0) / 100
            return round(scale_factor, 2)
        except:
            return 1.0  # 默认无缩放


"""
以scene为工作单位的合成类,
获取当前场景，遍历viewlayer进行节点设置
节点命名规则{viewlayer}_{nodetype}_Flash
"""
class BlenderCompositor:
    def __init__(self,
                 separate_data=0,
                 separate_cryptomatte=1,
                 separate_shaderaov=0,
                 separate_lightgroup=0):
        # 启动节点合成器
        bpy.context.scene.use_nodes = 1
        # 全局变量
        self.scene = bpy.context.scene
        self.node_tree = bpy.context.scene.node_tree
        self.scene_view_layers = self.scene.view_layers
        self.ui_scale = bpy.context.preferences.view.ui_scale

        # 全局设置
        self.enable_denoise = 1
        self.render_out_nodes_width = 800
        self.view_layer_nodes_width = 500
        self.supported_classes = NODE_TYPES

        # 添加分离控制参数
        self.separate_data = separate_data
        self.separate_cryptomatte = separate_cryptomatte
        self.separate_shaderaov = separate_shaderaov
        self.separate_lightgroup = separate_lightgroup

        self.node_layout = NodeLayoutManager(self.ui_scale)

    def find_user_nodes(self):
        # 遍历节点，筛选名称以 "Flash" 结尾的节点（区分大小写）
        return [node for node in self.node_tree.nodes 
                if node.name and not node.name.endswith("Flash")]

    def create_node(self, bl_idname, location=(0, 0), prefix=None):
        """创建或获取一个节点"""
        # 生成唯一节点名称
        node_name = f"{prefix}_{bl_idname[14:]}_Flash"

        # 检查现有节点
        existing_node = self.node_tree.nodes.get(node_name)
        if existing_node and existing_node.bl_idname == bl_idname:
            # 复用现有节点
            node = existing_node
            node.location = location
        else:
            # 创建新节点
            node = self.node_tree.nodes.new(bl_idname)
            node.location = location
            node.name = node_name

        return node

    def set_render_layer_node(self, view_layer, location=(0, 0)):
        """为指定视图层创建/更新渲染节点"""
        # 获取视图层名称
        viewlayer_name = view_layer.name if hasattr(
            view_layer, 'name') else view_layer

        # 生成目标节点名称
        target_name = f"{viewlayer_name}_RLayers_Flash"

        # 查找现有节点
        existing_node = self.node_tree.nodes.get(target_name)
        if existing_node and existing_node.type == 'R_LAYERS':
            # 复用现有节点
            node = existing_node
            node.layer = viewlayer_name  # 更新视图层关联
            node.location = location
        else:
            # 创建新节点
            node = self.create_node(
                'CompositorNodeRLayers', location=location, prefix=viewlayer_name)
            node.label = viewlayer_name
            node.layer = viewlayer_name

        return node

    def get_viewlayer_aov(self, viewlayer_name: str) -> dict:
        # 需要先存在视图层节点，否则会报错
        # 初始化数据结构
        aov_dict = {category: [] for category in NODE_TYPES}

        # 查找对应的视图层对象
        target_view_layer = next(
            (vl for vl in self.scene.view_layers if vl.name == viewlayer_name), None)
        if not target_view_layer:
            print(f"ViewLayer '{viewlayer_name}' not found")
            return aov_dict

        # 获取关联的渲染层节点
        target_name = f"{viewlayer_name}_RLayers_Flash"
        render_layer_node = self.node_tree.nodes.get(target_name)
        if not render_layer_node:
            print(f"RenderLayer node for '{viewlayer_name}' not found")
            return aov_dict

        # 收集Shader AOV（从指定视图层获取）
        aov_dict['shaderaov'] = [aov.name for aov in target_view_layer.aovs]

        # 收集LightGroups（从指定视图层获取）
        aov_dict['lightgroup'] = [
            lg.name for lg in target_view_layer.lightgroups]

        # 分析节点输出端口
        for output in render_layer_node.outputs:
            # 跳过空端口
            if not output.enabled or not output.name:
                continue
            
            # 分类逻辑
            lower_name = output.name.lower()
            if any(kw in lower_name for kw in CRYPTO_KEYWORDS):
                aov_dict['cryptomatte'].append(output.name)
            elif output.name in DATA_CATEGORIES:
                aov_dict['data'].append(output.name)
            elif output.name in RGB_CATEGORIES:
                aov_dict['rgb'].append(output.name)

        return aov_dict

    def link_nodes(self, from_node, from_socket_name, to_node, to_socket_name):
        """连接两个节点"""
        from_socket = from_node.outputs[from_socket_name]
        to_socket = to_node.inputs[to_socket_name]
        self.node_tree.links.new(from_socket, to_socket)
        
    def set_output_nodes(self, view_layer, location=(0, 0)) -> dict:
        """为指定视图层创建完整输出节点系统
        返回: {类型: 节点} 的字典 (如 {'rgb': OutputFileNode, 'data': OutputFileNode})
        """
        # 获取AOV数据
        aov_dict = self.get_viewlayer_aov(view_layer.name)
        modified_aov = self._process_aov_data(aov_dict)
        
        # 创建输出文件节点字典
        output_nodes = {}
        x_offset = location[0]
        y_offset = location[1]

        # 配置分类规则
        category_rules = [
            ('rgb', True),  # RGB 总是需要创建
            ('data', self.separate_data),
            ('cryptomatte', self.separate_cryptomatte),
            ('shaderaov', self.separate_shaderaov),
            ('lightgroup', self.separate_lightgroup)
        ]

        for category, enabled in category_rules:
            # 仅当分类有内容且启用时创建节点
            if enabled and modified_aov.get(category):
                node = self._get_output_node(
                    position=(x_offset, y_offset),
                    aovs = modified_aov[category],
                    aov_dict = aov_dict,
                    view_layer=view_layer,
                    category=category,
                )
                output_nodes[category] = node
                # 更新Y轴偏移量
                y_offset -= self.node_layout.calculate_node_height(node) + 20

        return output_nodes

    def _get_output_node(self, position, aovs, aov_dict, view_layer, category, width=500):
        # 创建或复用一个指定分类（category）的输出文件节点（Output File Node），
        # 并根据当前 AOV（Arbitrary Output Variable）配置动态管理其插槽（file slots），
        # 以确保节点状态与数据一致。
        from contextlib import contextmanager
        @contextmanager
        def override_area(area_type='NODE_EDITOR'):
            for area in bpy.context.screen.areas:
                if area.type == area_type:
                    for region in area.regions:
                        if region.type == 'WINDOW':
                            override = {
                                'window': bpy.context.window,
                                'screen': bpy.context.screen,
                                'area': area,
                                'region': region,
                                'scene': bpy.context.scene,
                                'space_data': area.spaces.active,
                            }
                            with bpy.context.temp_override(**override):
                                yield
                            return
            yield

        def remove_named_slot_from_output_node(node: bpy.types.Node, name: str):
            # 从输出文件节点中删除指定名称的插槽（file slot），
            # 并断开该插槽的所有连接，最后重建其余插槽。
            if node and node.type == 'OUTPUT_FILE':
                node_tree = bpy.context.scene.node_tree
                # 设置节点为当前活动节点（激活节点）
                node_tree.nodes.active = node
                # 断开输入 socket 对应链接
                socket = node.inputs.get(name)
                if socket:
                    for link in list(socket.links):
                        node_tree.links.remove(link)
                    
                # 获取插槽列表和当前插槽数量
                file_slots = node.file_slots
                total_slots = len(file_slots)

                # 遍历插槽查找目标名称的插槽索引
                found_indices = [i for i, slot in enumerate(file_slots) if slot.path == name]

                # 倒序删除，防止索引偏移导致错误
                for index in reversed(found_indices):
                    # 设置当前插槽为激活状态
                    node.active_input_index = index

                    # 删除激活插槽
                    bpy.ops.node.output_file_remove_active_socket()
                    # node.output_file_remove_socket()
                
                print(f"已从节点 {node.name} 中删除插槽 '{name}' 的 {len(found_indices)} 个实例。")
            else:
                print("请提供一个有效的 Output File 节点。")

        
        """创建/匹配单个分类的输出节点"""
        node_name = f"{view_layer.name}_{category}_OutputFile_Flash"
        node = self.node_tree.nodes.get(node_name)

        if node and node.type == 'OUTPUT_FILE':
            # 移除不在 aovs 中且不在 aov_dict 中的端口
            existing_slots = {slot.path for slot in node.file_slots}
            for slot in list(node.file_slots):
                if slot.path not in aovs and slot.path not in aov_dict.get(category, []):
                    # print(slot.path)
                    # remove_named_slot_from_output_node(node, slot.path)
                    pass

        else:
            # 创建新节点并设置前缀
            prefix = f"{view_layer.name}_{category}"
            node = self.create_node(
                'CompositorNodeOutputFile', position, prefix=prefix)
            node.name = node_name
            # 删除名为 "Image" 的插槽（如果存在）
            if len(node.file_slots) == 1:
                node.file_slots.clear()
            # 添加初始插槽
            for aov in aovs:
                node.file_slots.new(aov)

        node.use_custom_color = True
        if category in ['rgb', 'lightgroup']:
            node.color = (0.15, 0.25, 0.15)
        else:
            node.color = (0.19, 0.15, 0.25)

        # 添加需要的插槽（确保不重复添加）
        existing_slots = {slot.path for slot in node.file_slots}
        for aov in aovs:
            if aov not in existing_slots:
                node.file_slots.new(aov)

        # 设置节点属性
        node.location = position
        node.width = width
        node.label = f"{view_layer.name} {category}"

        return node

    def _process_aov_data(self, aov_dict):
        """统一处理AOV分类数据（合并adjust_separate_aov功能）"""
        processed = {category: aov_dict.get(category, []).copy() for category in NODE_TYPES}

        # 特殊处理
        processed['rgb'] = [
            'rgb' if aov == 'Image' else aov  # 将 'Image' 替换为 'rgb'
            for aov in processed['rgb']
            if aov not in {'Alpha'}  # 过滤掉 'Alpha'
        ]
        processed['data'] = [aov for aov in processed['data'] if aov not in {'Denoising Normal', 'Denoising Albedo', 'Debug Sample Count', 'IndexOB', 'IndexMA'}]

        # 合并处理逻辑
        merge_categories = []
        for category, should_separate in [
            ('data', self.separate_data),
            ('cryptomatte', self.separate_cryptomatte),
            ('shaderaov', self.separate_shaderaov),
            ('lightgroup', self.separate_lightgroup)
        ]:
            if should_separate:
                processed[category] = processed.get(category, [])
            else:
                merge_categories.append(category)
                processed['rgb'].extend(processed.get(category, []))

        # 清空被合并的分类
        for category in merge_categories:
            processed[category] = []

        return processed

    def _get_normalized_aov_name(self, view_layer, aov_name: str) -> str:
        """集中处理所有特殊端口名称转换"""
        # 处理 LightGroup 前缀问题
        if aov_name in [lg.name for lg in view_layer.lightgroups]:
            return f"Combined_{aov_name}"

        # 处理 Image -> RGB 的映射
        if aov_name == "rgb":
            return "Image"

        return aov_name

    def auto_connect_aov(self, from_node, to_node, view_layer, aov_name: str):
        """智能连接方法（替换原link_nodes直接调用）"""
        normalized_name = self._get_normalized_aov_name(view_layer, aov_name)

        try:
            # 修正连接方向：原始输出端口 -> 标准化输入端口
            self.link_nodes(from_node, normalized_name, to_node, aov_name)
            self.link_nodes(from_node, aov_name, to_node, aov_name)
        except KeyError:
            # 回退到原始名称连接
            try:
                print(f"警告: 使用回退连接 {aov_name}")
            except Exception as e:
                print(f"连接失败: {aov_name} -> {str(e)}")

    def get_connected_nodes(self, start_node):
        """获取从指定节点开始的所有连接节点"""
        nodes = [start_node]
        visited = set()
        stack = [start_node]
        while stack:
            current_node = stack.pop()
            if current_node not in visited:
                visited.add(current_node)
                for output in current_node.outputs:
                    for link in output.links:
                        if link.to_node not in visited:
                            nodes.append(link.to_node)
                            stack.append(link.to_node)
        return nodes

    def connect_denoise_node(self, render_layer_node, output_files, aov_name, y_offset):
        """连接Denoise节点的输入和输出端口"""
        denoise_node = self.create_node(
            'CompositorNodeDenoise', location=(600, y_offset))
        denoise_node.hide = True  # 设置 Denoise 节点为最小折叠状态

        if not self.scene.cycles['use_denoising']:
            self.scene.cycles['use_denoising_store_passes'] = True
        self.link_nodes(render_layer_node, aov_name, denoise_node, 'Image')
        self.link_nodes(render_layer_node, 'Denoising Normal',
                        denoise_node, 'Normal')
        self.link_nodes(render_layer_node, 'Denoising Albedo',
                        denoise_node, 'Albedo')
        self.link_nodes(denoise_node, 'Image', output_files, aov_name)

        # 返回下一个节点的y偏移量
        return y_offset - 30

    def insert_node_between(self,
                            from_node,
                            to_node,
                            new_bl_idname,
                            from_socket_name,
                            to_socket_name,
                            prefix=None,
                            location_offset=(200, 0),
                            extra_links=None,
                            hide_node=True):
        """
        通用节点插入方法
        参数：
        - from_node: 上游节点
        - to_node: 下游节点
        - new_bl_idname: 要插入的新节点类型
        - from_socket_name: 上游连接的插槽名称
        - to_socket_name: 下游连接的插槽名称
        - prefix: 节点名称前缀
        - location_offset: 新节点位置偏移量 (相对下游节点)
        - extra_links: 需要额外连接的通道列表 [ (from_node, from_socket, to_socket) ]
        - hide_node: 是否自动折叠节点
        """
        # 创建新节点
        new_node = self.create_node(
            new_bl_idname,
            location=(to_node.location.x + location_offset[0],
                      to_node.location.y + location_offset[1]),
            prefix=prefix or f"{from_node.name}_{to_node.name}"
        )
        new_node.hide = hide_node

        # 获取原始链接
        original_links = []
        for link in to_node.inputs[to_socket_name].links:
            original_links.append((link.from_node, link.from_socket))

        # 断开原始连接
        for link in to_node.inputs[to_socket_name].links:
            self.node_tree.links.remove(link)

        # 建立新连接
        try:
            # 上游节点 -> 新节点
            self.link_nodes(from_node, from_socket_name, new_node, 'Image')

            # 新节点 -> 下游节点
            self.link_nodes(new_node, 'Image', to_node, to_socket_name)
        except KeyError as e:
            print(f"连接失败: {str(e)}")
            self.node_tree.nodes.remove(new_node)
            return None

        # 建立额外连接
        if extra_links:
            for link_info in extra_links:
                src_node, src_socket, dst_socket = link_info
                if src_node.outputs.get(src_socket) and new_node.inputs.get(dst_socket):
                    self.link_nodes(src_node, src_socket, new_node, dst_socket)

        return new_node

    def remove_node_between(self, middle_node):
        """
        移除中间节点但保持前后节点的第一个端口连接
        参数：
        - middle_node: 要移除的中间节点
        """
        if not middle_node:
            print("中间节点为空，无法移除")
            return

        # 获取上游节点和下游节点
        from_node = None
        to_node = None
        from_socket_name = None
        to_socket_name = None
        # 找到上游节点
        for input_socket in middle_node.inputs:
            if input_socket.is_linked:
                link = input_socket.links[0]
                from_node = link.from_node
                from_socket_name = link.from_socket.name
                break  # 只处理第一个有效连接

        # 找到下游节点
        for output_socket in middle_node.outputs:
            if output_socket.is_linked:
                link = output_socket.links[0]
                to_node = link.to_node
                to_socket_name = link.to_socket.name
                break  # 只处理第一个有效连接

        # 断开中间节点连接
        if from_node and to_node:
            try:
                # 断开中间节点的所有输入输出连接
                for input_socket in middle_node.inputs:
                    for link in input_socket.links:
                        self.node_tree.links.remove(link)
                for output_socket in middle_node.outputs:
                    for link in output_socket.links:
                        self.node_tree.links.remove(link)
                
                # 重新连接上下游节点
                self.link_nodes(from_node, from_socket_name, to_node, to_socket_name)
            except Exception as e:
                print(f"连接恢复失败: {str(e)}")

        # 无论是否成功重新连接，最终移除中间节点
        self.node_tree.nodes.remove(middle_node)

    def set_denoise(self, viewlayer):
        """为指定视图层的输出节点添加降噪"""
        if self.enable_denoise:
            viewlayer.cycles['denoising_store_passes'] = 1
            aov_dict = self.get_viewlayer_aov(viewlayer.name)
            processed_aov = {
                'rgb': ['rgb' if x == 'Image' else x for x in aov_dict.get('rgb', [])],
                'lightgroup': aov_dict.get('lightgroup', []),
            }
            denoise_layers = processed_aov['rgb'] + processed_aov['lightgroup']

            for category in ['rgb', 'lightgroup']:
                output_node = self.node_tree.nodes.get(
                    f"{viewlayer.name}_{category}_OutputFile_Flash")
                if not output_node:
                    continue
                
                # 遍历outfile node
                y_offset = 0  # 初始偏移量
                for input_socket in output_node.inputs:
                    if input_socket.is_linked and input_socket.name in denoise_layers:
                        # 获取上游连接
                        
                        from_node = input_socket.links[0].from_node
                        from_socket = input_socket.links[0].from_socket
                        if from_node.bl_idname == 'CompositorNodeRLayers':
                            # 插入降噪节点
                            self.insert_node_between(
                                from_node=from_node,
                                to_node=output_node,
                                new_bl_idname='CompositorNodeDenoise',
                                from_socket_name=from_socket.name,
                                to_socket_name=input_socket.name,
                                prefix=f"{viewlayer.name}_{from_socket.name}",
                                location_offset=(-500, y_offset),
                                extra_links=[
                                    (from_node, 'Denoising Normal', 'Normal'),
                                    (from_node, 'Denoising Albedo', 'Albedo')
                                ],
                                hide_node=True
                            )
                            y_offset -= 33  # 垂直间距调整
        else:
            for node in self.node_tree.nodes:
                if node.bl_idname == 'CompositorNodeDenoise' and node.name.endswith("_Flash"):
                    # self.remove_node_between(node)
                    bpy.ops.node.delete_reconnect()

    def preprocess_compositor_nodes(self):
        """预处理合成器节点"""
        # 新增逻辑：清理失效视图层节点（优先执行）
        scene_viewlayer_names = {vl.name for vl in self.scene.view_layers}
        # 查找所有RLayers节点（不包含自定义节点）
        rlayer_nodes = [node for node in self.node_tree.nodes 
                        if node.name.endswith("_RLayers_Flash")]
            
        # 验证并清理失效节点
        invalid_viewlayers = set()
        for node in rlayer_nodes:
            # 关键验证：节点关联的视图层是否存在
            viewlayer_name = node.name[:-len("_RLayers_Flash")]
            if not node.layer == viewlayer_name:
                invalid_viewlayers.add(viewlayer_name)
                self.node_tree.nodes.remove(node)
        

        # 清理与失效视图层相关的所有节点
        if invalid_viewlayers:
            for node in self.node_tree.nodes:
                # 检查节点名称是否包含任何失效视图层名称
                if any(name in node.name for name in invalid_viewlayers):
                    # 安全移除节点
                    try:
                        self.node_tree.nodes.remove(node)
                    except ReferenceError:
                        pass  # 节点已被其他过程移除

        # 删除默认节点
        user_nodes = self.find_user_nodes()
        if len(user_nodes) == 2:
            node_names = {n.name for n in user_nodes}
            if node_names == {'Render Layers', 'Composite'}:
                for node in user_nodes:
                    self.node_tree.nodes.remove(node)
                return

        # 原有逻辑：情况2 - 调整用户节点布局
        if user_nodes:
            bounds = self.node_layout.get_nodes_bound(user_nodes)
            if bounds[3] < 0:
                move_offset = -bounds[3] + 200
                for node in user_nodes:
                    node.location.y += move_offset

        # 原有逻辑：移除无用降噪节点
        for node in self.node_tree.nodes:
            if node.bl_idname == 'CompositorNodeDenoise' and node.name.endswith("_Flash"):
                has_output_links = any(output.is_linked for output in node.outputs)
                if not has_output_links:
                    self.node_tree.nodes.remove(node)


    def reconfigure_output_nodes(self):
        """重新配置已经存在的 File Output 节点"""
        # 创建一个字典来存储每个分类的分离状态
        separation_status = {
            'data': self.separate_data,
            'cryptomatte': self.separate_cryptomatte,
            'shaderaov': self.separate_shaderaov,
            'lightgroup': self.separate_lightgroup
        }

        # 遍历每个视图层
        for view_layer in self.scene.view_layers:
            viewlayer_name = view_layer.name

            # 获取 AOV 数据
            aov_dict = self.get_viewlayer_aov(viewlayer_name)
            processed_aov = self._process_aov_data(aov_dict)

            # 检查每个分类的 File Output 节点
            for category in separation_status:
                node_name = f"{viewlayer_name}_{category}_OutputFile_Flash"
                node = self.node_tree.nodes.get(node_name)
                if node and node.type == 'OUTPUT_FILE':
                    if not separation_status[category] or not processed_aov.get(category, []):
                        self.node_tree.nodes.remove(node)

    def get_output_nodes_by_name(self) -> dict:
        """通过节点名查找输出文件节点，返回{视图层: {类型: 节点}}结构"""
        output_structure = {}
        
        # 支持的输出类型列表
        valid_types = ['rgb', 'data', 'cryptomatte', 'shaderaov', 'lightgroup']
        
        for node in self.node_tree.nodes:
            # 筛选输出文件节点且名称符合命名规则
            if node.type == 'OUTPUT_FILE' and node.name.endswith("_OutputFile_Flash"):
                # 解析节点名称结构：{viewlayer}_{type}_OutputFile_Flash
                parts = node.name.rsplit('_', 3)  # 从后往前分割，分割成最多4部分
                if len(parts) != 4:
                    continue  # 跳过不符合命名规则的节点
                
                # 提取视图层名称和类型
                viewlayer_name = "_".join(parts[:-3])  # 合并所有部分，除了最后三个
                node_type = parts[-3]
                
                if node_type not in valid_types:
                    continue  # 没有找到有效类型
                
                # 验证视图层是否存在
                if not any(vl.name == viewlayer_name for vl in self.scene.view_layers):
                    continue
                
                # 构建数据结构
                if viewlayer_name not in output_structure:
                    output_structure[viewlayer_name] = {}
                
                output_structure[viewlayer_name][node_type] = node

        return output_structure

############
    def setup_compositor_nodes(self):
        self.preprocess_compositor_nodes()
        
        viewlayer_outfile_nodes = {}
        vertical_offset = 0  # 垂直布局起始偏移量
        
        # 遍历所有视图层
        for view_layer in self.scene.view_layers:
            # 创建渲染层节点
            self.set_render_layer_node(
                view_layer, 
                location=(-400, vertical_offset)
            )
            
            # 创建输出节点系统
            output_nodes = self.set_output_nodes(
                view_layer,
                location=(self.render_out_nodes_width, vertical_offset)
            )
            
            # 记录节点到返回字典
            viewlayer_outfile_nodes[view_layer.name] = output_nodes
            
            # 自动连接所有AOV通道
            def connect_aov_channels(output_node, category):
                if output_node:
                    for file_slot in output_node.file_slots:
                        self.auto_connect_aov(
                            self.node_tree.nodes.get(f"{view_layer.name}_RLayers_Flash"),
                            output_node,
                            view_layer,
                            file_slot.path
                        )
            
            # 连接所有输出类型
            for category in output_nodes:
                connect_aov_channels(output_nodes[category], category)
            
            # 计算下一个视图层的垂直偏移
            if output_nodes:
                nodes_list = list(output_nodes.values())
                bounds = self.node_layout.get_nodes_bound(nodes_list)
                vertical_offset += bounds[3] - bounds[2] - self.view_layer_nodes_width

        # 后处理配置
        self.reconfigure_output_nodes()
        
        # 配置降噪节点
        for view_layer in self.scene.view_layers:
            self.set_denoise(view_layer)
        
        return viewlayer_outfile_nodes