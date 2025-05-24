
from email.policy import default
from multiprocessing import active_children
import select
import bpy
import gpu
import random
import colorsys
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from math import sin, cos, pi
from bpy_extras.view3d_utils import location_3d_to_region_2d, region_2d_to_location_3d


draw_handler = None
import time

last_view_layer_name = ""
last_view_layer_check_time = 0.0  # 记录上次检查时间


# 定义翻译字典
translations = {
    "en_US": {
        "Flash AOV": "Flash AOV",
        "Light Groups": "Light Groups",
        "Light Groups Manager": "Light Groups Manager",
        "Show Color": "Show Color",
        "Size": "Size",
        "From Lights": "From Lights",
        "From Collection": "From Collection",
        "Remove Empty": "Remove Empty",
        "WorldGroup": "WorldGroup",
        "Add/Remove to Group": "Add/Remove to Group",
        "Toggle Group Visibility": "Toggle Group Visibility",
        "Solo Group": "Solo Group",
        "No lights selected": "No lights selected",
        "Light group already exists, skipped creation": "Light group already exists, skipped creation",
        "Light groups created successfully": "Light groups created successfully",
        "No world to assign": "No world to assign",
        "Created group and assigned World": "Created group and assigned World",
        "Removed {count} empty light groups": "Removed {count} empty light groups",
        "Sync Light Groups": "Sync Light Groups",
        "Create a light group from the active collection (including nested collections)": "Create a light group from the active collection (including nested collections)",
        "Create light groups from selected lights (skips duplicates)": "Create light groups from selected lights (skips duplicates)",
        "Create a new empty light group": "Create a new empty light group",
        "Remove Selected Light Group": "Remove Selected Light Group"

    },
    "zh_HANS": {
        "Flash AOV": "闪光AOV",
        "Light Groups": "灯光组",
        "Light Groups Manager": "灯光组管理器",
        "Show Color": "显示颜色",
        "Size": "大小",
        "From Lights": "选中灯光创建",
        "From Collection": "激活集合创建",
        "Remove Empty": "移除空灯光组",
        "WorldGroup": "世界环境组",
        "Add/Remove to Group": "添加/移除到组",
        "Toggle Group Visibility": "切换组可见性",
        "Solo Group": "独显组",
        "No lights selected": "未选中任何灯光对象",
        "Light group already exists, skipped creation": "灯光组已存在，跳过创建",
        "Light groups created successfully": "灯光组创建完成",
        "No world to assign": "没有可分配的世界环境",
        "Created group and assigned World": "已创建世界环境灯光组",
        "Removed {count} empty light groups": "移除了 {count} 个空灯光组",
        "Sync Light Groups": "同步灯光组",
        "Create a light group from the active collection (including nested collections)": "从激活的集合创建灯光组（包括嵌套的集合）",
        "Create light groups from selected lights (skips duplicates)": "创建从选中灯光创建的灯光组（跳过重复项）",
        "Create a new empty light group": "创建一个空的灯光组",
        "Remove Selected Light Group": "移除选中的灯光组"
        
    }
}

# 动态翻译函数


def translate(key):
    lang = bpy.context.preferences.view.language
    return translations.get(lang, translations["en_US"]).get(key, key)


def calculate_screen_radius(context, location):
    """计算屏幕中小圆的世界空间Size"""
    region = context.region
    rv3d = context.region_data
    coord = location_3d_to_region_2d(region, rv3d, location)
    if coord is None:
        return 0.0

    # 使用用户设置的小圆Size
    desired_pixel_radius = context.scene.lightgroup_circle_radius
    offset = Vector((desired_pixel_radius, 0))
    new_coord = coord + offset
    world_offset = region_2d_to_location_3d(
        region, rv3d, new_coord, location) - location
    return world_offset.length


def draw_callback():
    """视口绘制函数：绘制小圆圈代表Light Groups"""
    context = bpy.context
    region = context.region
    rv3d = context.region_data
    if not rv3d:
        return

    if not context.scene.get("show_lightgroup_overlay", True):
        return

    area = next((a for a in context.screen.areas if a.type == 'VIEW_3D'), None)
    if area:
        space = next((s for s in area.spaces if s.type == 'VIEW_3D'), None)
        if space and not space.overlay.show_overlays:
            return
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    view_inv = rv3d.view_matrix.inverted()
    cam_right = view_inv.col[0].xyz.normalized()
    cam_up = view_inv.col[1].xyz.normalized()

    for obj in context.view_layer.objects:
        if obj.type != 'LIGHT' or not obj.visible_get():
            continue

        loc = obj.matrix_world.translation
        radius = calculate_screen_radius(context, loc)  # 动态获取Size
        segments = 12

        group = obj.lightgroup
        group_color = None
        for item in context.scene.lightgroup_list:
            if item.name == group:
                group_color = item.color
                break

        # 如果找不到组或未设置颜色，跳过绘制
        if group_color is None:
            continue

        color = tuple(group_color[:3]) + (1.0,)


        verts = [loc]
        for i in range(segments + 1):
            angle = 2 * pi * i / segments
            offset = (cos(angle) * cam_right + sin(angle) * cam_up) * radius
            verts.append(loc + offset)

        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": verts})
        shader.bind()
        shader.uniform_float("color", color)
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('LESS_EQUAL')  # 启用深度测试
        batch.draw(shader)
        gpu.state.blend_set('NONE')
        gpu.state.depth_test_set('NONE')  # 恢复默认状态

def update_group_color(self, context):
    """当组颜色发生变化时，更新所有属于该组的灯光对象的 flashaov_lgt_color"""
    scene = context.scene
    group_name = self.name

    # 更新所有灯光对象
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT' and obj.lightgroup == group_name:
            obj["flashaov_lgt_color"] = Vector(self.color)


class LightGroupItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        update=lambda self, context: LightGroupNameSynchronizer.sync_name(self, context)
    )  # type: ignore

    old_name: bpy.props.StringProperty(default="")  # type: ignore
    color: bpy.props.FloatVectorProperty(
        subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0),
        update=update_group_color  # 绑定回调
    )  # type: ignore
    selected: bpy.props.BoolProperty(default=False) # type: ignore
    visible: bpy.props.BoolProperty(default=True)  # type: ignore
    solo: bpy.props.BoolProperty(default=False)  # type: ignore
    has_world: bpy.props.BoolProperty(default=False)  # type: ignore



class LIGHTGROUP_UL_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # 添加空值检查
        if not item:
            return  # 跳过无效条目
        
        group = item
        scene = context.scene
        view_layer = context.view_layer

        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False)

        # 统计当前组中的灯光数量（含世界环境）
        count = 0

        # 计算属于该组的灯光数量
        count_light = sum(1 for o in bpy.data.objects
                          if o.type == 'LIGHT' and o.lightgroup == group.name)

        # 判断是否为世界组，并计算世界数量
        count_world = 1 if (
            item.has_world and scene.world and scene.world.lightgroup == group.name) else 0

        # 总数量 = 灯光数量 + 世界数量
        count = count_light + count_world

        # 显示图标和数量
        icon_type = 'WORLD' if count_world else 'LIGHT'
        row.label(text=f"{count}", icon=icon_type)

        # 对象是否属于该组
        obj = context.active_object
        in_group = obj and obj.select_get() and any(
            o.lightgroup == group.name for o in context.selected_objects if o.type == 'LIGHT'
        )
        toggle = row.operator("lightgroup.add_to", text="",
                              icon='FORCE_CHARGE' )
        toggle.group_name = group.name

        # The code is assigning the value of `group.name` to the variable `vis.group_name`.
        # 选择组灯光内对象
        select_op = row.operator("lightgroup.select_group", text="",
                                 icon='RESTRICT_SELECT_OFF' if in_group else 'RESTRICT_SELECT_ON')
        select_op.group_name = group.name
        
        # 显示可见性开关
        vis_icon = 'HIDE_OFF' if group.visible else 'HIDE_ON'
        vis = row.operator("lightgroup.toggle_group", text="", icon=vis_icon)
        vis.group_name = group.name

        solo_icon = 'RADIOBUT_ON' if group.solo else 'RADIOBUT_OFF'
        solo = row.operator("lightgroup.solo_group", text="", icon=solo_icon)
        solo.group_name = group.name

        sub = row.row(align=True)
        sub.scale_x = 0.4
        sub.prop(group, "color", text="", emboss=True)


class LIGHTGROUP_PT_npanel(bpy.types.Panel):
    bl_label = translate("Flash AOV")
    bl_idname = "LIGHTGROUP_PT_npanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = translate("Flash AOV")

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        if not hasattr(scene, "lightgroup_list") or not hasattr(scene, "lightgroup_active_index"):
            layout.label(text=translate("Light Groups数据未初始化"), icon='ERROR')
            return

        # 顶部显示控制
        row = layout.row(align=True)
        row.prop(scene, "show_lightgroup_overlay", text=translate(
            "Show Color"), toggle=True, icon='HIDE_OFF')
        row.prop(scene, "lightgroup_circle_radius", text=translate("Size"))

        layout.operator("lightgroup.create_world_group",
                        text=translate("WorldGroup"), icon='WORLD')

        # 直接使用 template_list，过滤逻辑由 UIList 自行处理
        layout.template_list("LIGHTGROUP_UL_list", "", scene,
                             "lightgroup_list", scene, "lightgroup_active_index")

        # 操作行
        row = layout.row(align=True)
        row.operator("lightgroup.create_empty", icon='ADD')
        row.operator("lightgroup.remove_group", icon='REMOVE')
        row.operator("lightgroup.remove_empty_groups",
                     icon='TRASH', text=translate("Remove Empty"))

        row2 = layout.row(align=True)
        row2.operator("lightgroup.create_from_selected",
                      icon='LIGHT', text=translate("From Lights"))
        row2.operator("lightgroup.create_from_collection",
                      icon='OUTLINER_COLLECTION', text=translate("From Collection"))
        
        layout.separator()
        layout.operator("lightgroup.sync_names", icon='FILE_REFRESH',
                        text=translate("Sync Light Groups"))



class LIGHTGROUP_OT_add_to(bpy.types.Operator):
    bl_idname = "lightgroup.add_to"
    bl_label = translate("Add/Remove to Group")
    bl_description = translate("将选中灯光分配到当前Light Groups")
    group_name: bpy.props.StringProperty() #  type: ignore

    def execute(self, context):
        group_name = self.group_name
        view_layer = context.view_layer
        selected_objects = context.selected_objects

        # 确保当前视图层存在这个 Light Group
        bpy.ops.scene.view_layer_add_lightgroup(name=group_name)

        lights = [obj for obj in selected_objects if obj.type == 'LIGHT']
        if not lights:
            self.report({'WARNING'}, translate("No lights selected"))
            return {'CANCELLED'}

        # 检查是否所有灯光已经在该组
        all_in_group = all(obj.lightgroup == group_name for obj in lights)

        scene = context.scene
        group_item = next((item for item in scene.lightgroup_list if item.name == group_name), None)

        # 如果组不在列表中，则创建它并使用默认颜色
        if not group_item:
            item = scene.lightgroup_list.add()
            item.name = group_name
            item.color = (0.5, 0.5, 0.5)
            item.visible = True
            item.solo = False
            item.has_world = False
            group_item = item

        default_color = group_item.color

        for obj in lights:
            if all_in_group:
                obj.lightgroup = ""  # 移除
            else:
                obj.lightgroup = group_name  # 添加
                obj["flashaov_lgt_color"] = Vector(default_color)  # 设置颜色
                print(f"{obj.name} assigned to {group_name}")

        # 刷新 UI
        for win in context.window_manager.windows:
            for area in win.screen.areas:
                if area.type in {'VIEW_3D', 'PROPERTIES'}:
                    area.tag_redraw()

        return {'FINISHED'}


class LIGHTGROUP_OT_select_group(bpy.types.Operator):
    bl_idname = "lightgroup.select_group"
    bl_label = translate("Select Group")
    bl_description = translate(
        "左键: 单选组\n"
        "Shift+左键: 加选组\n"
        "Ctrl+左键: 减选组\n"

    )
    group_name: bpy.props.StringProperty()
    shift: bpy.props.BoolProperty(default=False)  # type: ignore
    ctrl: bpy.props.BoolProperty(default=False)  # type: ignore
    is_double_click: bpy.props.BoolProperty(default=False)  # type: ignore

    # 用于检测双击的时间阈值（单位：秒）
    double_click_threshold = 0.3
    last_click_time = 0.0

    def invoke(self, context, event):
        # 检测双击事件
        
        current_time = time.time()
        if (current_time - self.last_click_time) < self.double_click_threshold:
            self.is_double_click = True
        else:
            self.is_double_click = False
        self.last_click_time = current_time

        # 捕获按键状态
        self.shift = event.shift
        self.ctrl = event.ctrl
        
            
        return self.execute(context)

    def execute(self, context):
        if self.is_double_click:
            return {'FINISHED'}

        group_name = self.group_name
        group_lights = self.get_group_lights(group_name)
        selected_objects = context.selected_objects
        active_obj = context.active_object

        # Ctrl减选模式
        if self.ctrl:
            for obj in group_lights:
                obj.select_set(False)
                if obj == active_obj:
                    context.view_layer.objects.active = None
        # Shift加选模式
        elif self.shift:
            for obj in group_lights:
                obj.select_set(True)
        # 默认单选模式
        else:
            bpy.ops.object.select_all(action='DESELECT')
            for obj in group_lights:
                obj.select_set(True)

        # 设置激活对象
        if not self.ctrl and group_lights:
            context.view_layer.objects.active = group_lights[0]

        self.update_view(context)
        return {'FINISHED'}

    def get_group_lights(self, group_name):
        """获取指定组的所有灯光"""
        return [
            obj for obj in bpy.data.objects
            if obj.type == 'LIGHT' and obj.lightgroup == group_name
        ]

    def update_view(self, context):
        """刷新3D视图"""
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


class LIGHTGROUP_OT_toggle_group(bpy.types.Operator):
    bl_idname = "lightgroup.toggle_group"
    bl_label = translate("Toggle Group Visibility")
    bl_description = translate("切换该Light Groups下所有灯光和世界环境的显示状态")
    group_name: bpy.props.StringProperty()  # type: ignore

    def set_world_output_mute(self, world, mute_state):
            """设置世界节点树中输出节点的 mute 状态"""

            node_tree = world.node_tree
            if not node_tree:
                return

            for node in node_tree.nodes:
                if node.type == 'OUTPUT_WORLD':
                    node.mute = mute_state

    def execute(self, context):
        scene = context.scene
        view_layer = context.view_layer
        current_item = None

        # 查找对应的UI列表项
        for item in scene.lightgroup_list:
            if item.name == self.group_name:
                current_item = item
                break

        if not current_item:
            self.report({'WARNING'}, f"找不到灯光组: {self.group_name}")
            return {'CANCELLED'}

        # 切换可见状态
        new_visibility = not current_item.visible
        current_item.visible = new_visibility

        # ===== 控制灯光对象 =====
        for obj in bpy.data.objects:
            if obj.type == 'LIGHT' and obj.lightgroup == self.group_name:
                # 设置视口和渲染可见性
                obj.hide_viewport = not new_visibility
                obj.hide_render = not new_visibility

        # ===== 控制世界环境 =====
        if current_item.has_world:
            world = scene.world
            if world:
                # 检查是否启用 use_nodes
                if world.use_nodes:
                    self.set_world_output_mute(world, not new_visibility)
                else:
                    self.report({'WARNING'}, translate(
                        "请先启用 World 的 'Use Nodes' 才能使用该命令"))
                    return {'CANCELLED'}
            else:
                self.report({'WARNING'}, translate("没有可用的世界环境"))
                return {'CANCELLED'}

        # 强制刷新界面
        for win in context.window_manager.windows:
            for area in win.screen.areas:
                if area.type in {'VIEW_3D', 'PROPERTIES'}:
                    area.tag_redraw()

        return {'FINISHED'}

class LIGHTGROUP_OT_solo_group(bpy.types.Operator):
    bl_idname = "lightgroup.solo_group"
    bl_label = translate("Solo Group")
    group_name: bpy.props.StringProperty()

    def set_world_output_mute(self, world, mute_state):
            """设置世界节点树中输出节点的 mute 状态"""

            node_tree = world.node_tree
            if not node_tree:
                return

            for node in node_tree.nodes:
                if node.type == 'OUTPUT_WORLD':
                    node.mute = mute_state

    def execute(self, context):
        scene = context.scene
        group_name = self.group_name
        objects = bpy.data.objects

        # 找到该组在 UI 列表中的项
        current_item = None
        for item in scene.lightgroup_list:
            if item.name == group_name:
                current_item = item
                break

        if not current_item:
            self.report({'WARNING'}, f"Group '{group_name}' not found")
            return {'CANCELLED'}

        # 切换当前组的 solo 状态
        current_item.solo = not current_item.solo

        # 获取所有处于独显状态的组
        solo_groups = [item.name for item in scene.lightgroup_list if item.solo]

        # ===== 处理灯光可见性 =====
# ===== 处理灯光可见性 =====
        for obj in objects:
            if obj.type == 'LIGHT':
                group_name = obj.lightgroup

                # 获取当前 Light Group 的 visible 状态
                group_item = next((item for item in scene.lightgroup_list if item.name == group_name), None)
                is_visible = group_item.visible if group_item else True

                # 是否属于任意独显组
                in_solo_group = group_name in solo_groups

                # 决策逻辑：如果当前处于独显模式，则仅显示 solo 组；否则回到 visible 设置
                should_show = in_solo_group or (not solo_groups and is_visible)

                obj.hide_viewport = not should_show
                obj.hide_render = not should_show

                obj.update_tag()

        # ===== 处理世界环境 =====
        world = scene.world
        if world and hasattr(world, "lightgroup") and world.lightgroup:
            # 只有当世界环境属于某个 Light Group 时才进行操作
            if world.use_nodes:
                world_in_solo = world.lightgroup in solo_groups
                self.set_world_output_mute(world, not world_in_solo)

                if not solo_groups:
                    self.set_world_output_mute(world, False)
            else:
                self.report({'WARNING'}, translate("请先启用 World 的节点功能"))
                return {'CANCELLED'}

        # 强制刷新界面
        for area in context.screen.areas:
            if area.type in {'VIEW_3D', 'PROPERTIES'}:
                area.tag_redraw()

        # 手动触发 depsgraph 更新，强制刷新灯光状态
        context.view_layer.update()

        return {'FINISHED'}


class LIGHTGROUP_OT_create_empty(bpy.types.Operator):
    bl_idname = "lightgroup.create_empty"
    bl_label = ""
    bl_description = translate("Create a new empty light group")

    def execute(self, context):
        scene = context.scene
        view_layer = context.view_layer
        group_list = scene.lightgroup_list

        # 在 view_layer.lightgroups 中创建新组
        bpy.ops.scene.view_layer_add_lightgroup()
        new_group_name = view_layer.active_lightgroup.name

        # 在 lightgroup_list 中添加对应项
        new_item = group_list.add()
        new_item.name = new_group_name
        new_item.visible = True
        new_item.solo = False
        new_item.has_world = False
        
        scene.lightgroup_active_index = len(group_list) - 1

        self.report({'INFO'}, translate(
            "Created new empty light group: {}").format(new_group_name))
        return {'FINISHED'}


class LIGHTGROUP_OT_create_from_selected(bpy.types.Operator):
    bl_idname = "lightgroup.create_from_selected"
    bl_label = translate("From Lights")
    bl_description = translate(
        "Create light groups from selected lights (skips duplicates)")

    def execute(self, context):
        scene = context.scene
        view_layer = context.view_layer

        created_count = 0
        skipped_count = 0


        # 获取所有选中的灯光对象
        selected_lights = [
            obj for obj in context.selected_objects if obj.type == 'LIGHT' and obj.visible_get()]
        
        if not selected_lights:
            self.report({'WARNING'}, translate("No lights selected"))
            return {'CANCELLED'}

        # 创建一个字典来记录每个组名对应的灯光对象
        group_membership = {}

        for obj in selected_lights:
            # 转换对象名称中的特殊字符为下划线
            group_name = self.sanitize_name(obj.name)

            # 检查转换后的组名是否已存在
            if group_name not in group_membership:
                # 检查该组名是否已存在于 view_layer.lightgroups 中
                if group_name not in [lg.name for lg in view_layer.lightgroups]:
                    # 创建新的灯光组
                    bpy.ops.scene.view_layer_add_lightgroup(name=group_name)
                    created_count += 1
                else:
                    skipped_count += 1  # 组名已存在，跳过创建

                # 将该组名添加到字典中
                group_membership[group_name] = [obj]
            else:
                # 如果组名已存在于字典中，将当前对象添加到该组
                group_membership[group_name].append(obj)

        # 分配灯光对象到对应的灯光组
        for group_name, lights in group_membership.items():
            # print(group_name, lights)
            # 如果插件自己的列表中没有该组，给 scene.lightgroup_list 添加条目
            if not any(item.name == group_name for item in scene.lightgroup_list):
                item = scene.lightgroup_list.add()
                item.name = group_name
                item.color = self.generate_vivid_color()
                item.visible = True
                item.solo = False
                item.has_world = False
                
            for light in lights:
                light.lightgroup = group_name
                print(light)
                # 获取组颜色并赋值给flashaov_lgt_color
                group_item = next((item for item in scene.lightgroup_list if item.name == group_name), None)
                if group_item:
                    color = group_item.color  # 返回的是 FloatVectorProperty 的 tuple: (r, g, b)
                    light["flashaov_lgt_color"] = Vector(color)

        # 设置激活元素为第一个
        group_list = scene.lightgroup_list
        scene.lightgroup_active_index = len(group_list) - created_count
        
        # —— 结果反馈 —— #
        if created_count:
            self.report({'INFO'}, translate(
                "Created {} new light groups").format(created_count))
        if skipped_count:
            self.report({'INFO'}, translate(
                "{} light group(s) already exist, skipped creation").format(skipped_count))
        if created_count == 0 and skipped_count == 0:
            self.report({'WARNING'}, translate(
                "No new light groups were created or skipped"))
        if not any(obj.lightgroup for obj in selected_lights):
            self.report({'WARNING'}, translate(
                "No lights were assigned to any group"))

        # 刷新 UI / 视口
        for win in context.window_manager.windows:
            for area in win.screen.areas:
                if area.type in {'VIEW_3D', 'PROPERTIES'}:
                    area.tag_redraw()

        return {'FINISHED'}

    def sanitize_name(self, name):
        """将名称中的特殊字符转换为下划线"""
        import re
        # 替换所有非字母数字字符为下划线
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # 避免连续下划线
        sanitized = re.sub(r'_+', '_', sanitized)
        # 去除首尾下划线
        sanitized = sanitized.strip('_')
        return sanitized if sanitized else "Unnamed"

    @staticmethod
    def generate_vivid_color():
        """生成更鲜艳的 RGB 颜色"""
        return colorsys.hsv_to_rgb(
            random.random(),
            random.uniform(0.85, 1.0),
            random.uniform(0.8, 1.0)
        )


class LIGHTGROUP_OT_create_from_collection(bpy.types.Operator):
    bl_idname = "lightgroup.create_from_collection"
    bl_label = translate("From Collection")
    bl_description = translate("Create a light group from the active collection (excluding nested collections)")

    def execute(self, context):
        scene = context.scene
        view_layer = context.view_layer
        created_count = 0
        skipped_count = 0

        active_collection = context.collection
        if not active_collection:
            self.report({'WARNING'}, translate("未选中任何集合"))
            return {'CANCELLED'}

        # 生成合法组名
        group_name = self.sanitize_name(active_collection.name)

        # 检查是否已存在同名组
        existing_groups = [lg.name for lg in view_layer.lightgroups]
        if group_name in existing_groups:
            self.report({'INFO'}, translate("灯光组已存在，跳过创建"))
        else:
            try:
                bpy.ops.scene.view_layer_add_lightgroup(name=group_name)
                created_count += 1
            except RuntimeError as e:
                self.report({'ERROR'}, str(e))
                return {'CANCELLED'}

        # 仅收集当前集合的直接子对象（不递归子集合）
        all_lights = [
            obj for obj in active_collection.objects
            if obj.type == 'LIGHT' and obj.visible_get()
        ]

        # 确保在插件列表中存在该组
        group_item = next((item for item in scene.lightgroup_list if item.name == group_name), None)
        if not group_item:
            item = scene.lightgroup_list.add()
            item.name = group_name
            item.color = (0.5, 0.5, 0.5)
            item.visible = True
            item.solo = False
            item.has_world = False
            group_item = item

        # 分配灯光并设置颜色
        default_color = group_item.color
        for light in all_lights:
            light.lightgroup = group_name
            light["flashaov_lgt_color"] = Vector(default_color)

        group_list = scene.lightgroup_list
        scene.lightgroup_active_index = len(group_list) - 1

        # 结果反馈
        msg = translate("已从集合创建灯光组: {} (包含 {} 个灯光)").format(group_name, len(all_lights))
        self.report({'INFO'}, msg)

        # 刷新界面
        for area in context.screen.areas:
            if area.type in {'VIEW_3D', 'OUTLINER'}:
                area.tag_redraw()

        return {'FINISHED'}

    def sanitize_name(self, name):
        """清理集合名称为有效标识符"""
        import re
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        sanitized = re.sub(r'_+', '_', sanitized)
        return sanitized.strip('_') or "Unnamed"


class LIGHTGROUP_OT_remove_group(bpy.types.Operator):
    bl_idname = "lightgroup.remove_group"
    bl_label = ""
    bl_description = translate("Remove Selected Light Group")

    @classmethod
    def poll(cls, context):
        return len(context.scene.lightgroup_list) > 0 and context.scene.lightgroup_active_index >= 0

    def execute(self, context):
        scene = context.scene
        view_layer = context.view_layer
        group_list = scene.lightgroup_list
        index = scene.lightgroup_active_index

        # 检查是否选择了有效的组
        if index < 0 or index >= len(group_list):
            self.report({'WARNING'}, translate("未选择任何灯光组"))
            return {'CANCELLED'}

        group_name = group_list[index].name

        # 查找在 view_layer.lightgroups 中的索引
        lightgroups = view_layer.lightgroups
        group_index = next((i for i, g in enumerate(
            lightgroups) if g.name == group_name), None)

        if group_index is None:
            self.report({'WARNING'}, translate(
                "在视图层中找不到该灯光组: {}").format(group_name))
        else:
            view_layer.active_lightgroup_index = group_index
            bpy.ops.scene.view_layer_remove_lightgroup()

        # 同步移除插件自己的 lightgroup_list 中的条目
        group_list.remove(index)
        if len(group_list) == scene.lightgroup_active_index:
            scene.lightgroup_active_index = min(
                max(0, index - 1), len(group_list) - 1)
        # 清理所有灯光对该组的引用
        for obj in bpy.data.objects:
            if obj.type == 'LIGHT' and obj.lightgroup == group_name:
                obj.lightgroup = ""

        # 刷新UI界面
        for win in context.window_manager.windows:
            for area in win.screen.areas:
                if area.type in {'VIEW_3D', 'PROPERTIES'}:
                    area.tag_redraw()

        self.report({'INFO'}, translate("已移除灯光组: {}").format(group_name))
        return {'FINISHED'}


class LIGHTGROUP_OT_create_world_group(bpy.types.Operator):
    bl_idname = "lightgroup.create_world_group"
    bl_label = translate("Create World Group")
    bl_description = translate("创建一个新的Light Groups并将当前世界分配给它")

    def execute(self, context):
        scene = context.scene
        view_layer = context.view_layer
        group_list = scene.lightgroup_list

        world = scene.world
        if not world:
            self.report({'WARNING'}, translate("没有可分配的世界环境"))
            return {'CANCELLED'}

        group_name = "WorldGroup"

        # 检查是否已存在同名组
        existing_names = {lg.name for lg in view_layer.lightgroups}
        if group_name in existing_names:
            self.report({'INFO'}, translate("WorldGroup 已存在，跳过创建"))
        else:
            # 创建新的灯光组
            bpy.ops.scene.view_layer_add_lightgroup(name=group_name)
            self.report({'INFO'}, translate(
                "已创建世界环境灯光组: {}").format(group_name))

        # 同步更新插件内部 lightgroup_list
        if not any(item.name == group_name for item in group_list):
            item = group_list.add()
            item.name = group_name
            item.color = (1, 1, 1)  # 蓝色系颜色
            item.visible = True
            item.solo = False
            item.has_world = True  # 标记该组包含世界环境

        # 更新所有灯光组中 has_world 状态（确保只有一个组标记为 has_world=True）
        for item in group_list:
            item.has_world = (item.name == group_name)

        # 设置世界环境的 lightgroup 属性
        if hasattr(world, "lightgroup"):
            world.lightgroup = group_name
        else:
            self.report({'ERROR'}, translate("当前世界环境不支持 lightgroup 属性"))
            return {'CANCELLED'}

        # 设置为激活组索引
        index = next((i for i, item in enumerate(
            group_list) if item.name == group_name), -1)
        if index >= 0:
            scene.lightgroup_active_index = index

        # 刷新UI界面
        for win in context.window_manager.windows:
            for area in win.screen.areas:
                if area.type in {'VIEW_3D', 'PROPERTIES'}:
                    area.tag_redraw()

        self.report({'INFO'}, translate("Created group and assigned World"))

        return {'FINISHED'}


class LIGHTGROUP_OT_remove_empty_groups(bpy.types.Operator):
    bl_idname = "lightgroup.remove_empty_groups"
    bl_label = translate("Remove Empty")
    bl_description = translate("Remove all empty light groups")

    def execute(self, context):
        scene = context.scene
        view_layer = context.view_layer

        # 获取当前所有灯光组名称
        current_lightgroups = scene.lightgroup_list.keys()
        # 过滤 lightgroup_list，只保留仍然存在的灯光组
        bpy.ops.scene.view_layer_remove_unused_lightgroups()
        new_lightgroups = view_layer.lightgroups.keys()
        items_to_remove = [
            item for item in current_lightgroups if item not in new_lightgroups]
        # 记录移除的数量
        removed_count = len(current_lightgroups)

        # 移除未使用的项
        for item in items_to_remove:
            scene.lightgroup_list.remove(scene.lightgroup_list.find(item))

        self.report({'INFO'}, translate(
            "Removed {} empty light groups").format(removed_count))

        # 刷新UI
        for win in context.window_manager.windows:
            for area in win.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

        return {'FINISHED'}


class LIGHTGROUP_OT_sync_names(bpy.types.Operator):
    bl_idname = "lightgroup.sync_names"
    bl_label = "Sync Light Groups"
    bl_description = "Manually sync names between Scene and View Layer"

    def execute(self, context):
        LightGroupNameSynchronizer.force_resync_scene_list_from_view_layer(context)
        self.report({'INFO'}, "Scene lightgroup_list forcefully synced from View Layer.")
        return {'FINISHED'}



class LightGroupNameSynchronizer:
    """
    同步 lightgroup_list 和 view_layer.lightgroups 的名称和状态。
    支持双向同步，并在视图层切换时,开关集合时自动更新。
    """

    # @classmethod
    # def sync_from_scene_to_view_layer(cls, context):
    #     """从 scene.lightgroup_list 同步到 view_layer.lightgroups"""
    #     scene = context.scene
    #     view_layer = context.view_layer
    #     group_list = scene.lightgroup_list
    #     vl_groups = view_layer.lightgroups

    #     # 删除视图层中不在 lightgroup_list 中的组
    #     for i in reversed(range(len(vl_groups))):
    #         vl_group_name = vl_groups[i].name
    #         if not any(item.name == vl_group_name for item in group_list):
    #             view_layer.active_lightgroup_index = i
    #             bpy.ops.scene.view_layer_remove_lightgroup()

    #     # 添加 lightgroup_list 中存在但视图层没有的组
    #     existing_names = {g.name for g in vl_groups}
    #     for item in group_list:
    #         if item.name not in existing_names:
    #             bpy.ops.scene.view_layer_add_lightgroup(name=item.name)
    #             existing_names.add(item.name)

    #     # 更新 active index
    #     active_name = group_list[scene.lightgroup_active_index].name if group_list else ""
    #     for i, vl_group in enumerate(vl_groups):
    #         if vl_group.name == active_name:
    #             view_layer.active_lightgroup_index = i
    #             break

    # @classmethod
    # def sync_from_view_layer_to_scene(cls, context):
    #     """从 view_layer.lightgroups 同步到 scene.lightgroup_list"""
    #     scene = context.scene
    #     view_layer = context.view_layer
    #     group_list = scene.lightgroup_list
    #     vl_groups = view_layer.lightgroups

    #     # 删除 lightgroup_list 中多余的组
    #     for i in reversed(range(len(group_list))):
    #         item = group_list[i]
    #         if not any(g.name == item.name for g in vl_groups):
    #             group_list.remove(i)

    #     # 添加缺失的组
    #     existing_names = {item.name for item in group_list}
    #     for vl_group in vl_groups:
    #         if vl_group.name not in existing_names:
    #             new_item = group_list.add()
    #             new_item.name = vl_group.name
    #             new_item.visible = True
    #             new_item.solo = False
    #             new_item.has_world = False
    #             new_item.color = (1.0, 1.0, 1.0)  # 默认白色
    #             existing_names.add(vl_group.name)

    #     # 同步 has_world 状态（可选）
    #     world = scene.world
    #     world_group_name = world.lightgroup if world and hasattr(world, "lightgroup") else None
    #     for item in group_list:
    #         item.has_world = (item.name == world_group_name)

    #     # 更新 active index
    #     active_vl_name = vl_groups[view_layer.active_lightgroup_index].name if vl_groups else ""
    #     for i, item in enumerate(group_list):
    #         if item.name == active_vl_name:
    #             scene.lightgroup_active_index = i
    #             break

    @classmethod
    def sync_name(cls, self, context):
        """
        PropertyGroup name 属性的 update 回调函数
        实现双向同步：当 lightgroup_list 中的 name 被修改时，同步到 view_layer.lightgroups
        """
        old_name = getattr(self, 'old_name', "")
        new_name = self.name

        if old_name == new_name or not new_name:
            return

        scene = context.scene
        view_layer = context.view_layer

        # 同步到 view_layer
        for i, lg in enumerate(view_layer.lightgroups):
            if lg.name == old_name:
                lg.name = new_name
                break

        # 获取当前所有灯光组名称
        group_names = {item.name for item in scene.lightgroup_list}

        # 更新属于该组的灯光引用
        for obj in bpy.data.objects:
            if obj.type == 'LIGHT' and obj.lightgroup == old_name and obj.lightgroup in group_names:
                obj.lightgroup = new_name

        # 更新世界环境引用
        world = scene.world
        if world and hasattr(world, 'lightgroup') and world.lightgroup == old_name:
            world.lightgroup = new_name

        # 更新 has_world 标记
        for item in scene.lightgroup_list:
            if item.name == new_name:
                item.has_world = (new_name == world.lightgroup if world and hasattr(world, "lightgroup") else False)
            elif item.name == old_name:
                item.name = new_name  # 已经被上面的逻辑处理了

        self.old_name = new_name

    @classmethod
    # def on_scene_or_view_layer_update(cls, scene, depsgraph):
    #     """
    #     场景或视图层变化时的回调
    #     """
    #     global last_view_layer_name

    #     context = bpy.context
    #     view_layer = context.view_layer

    #     if view_layer:
    #         current_name = view_layer.name
    #         if current_name != last_view_layer_name:
    #             last_view_layer_name = current_name
    #             cls.force_resync_scene_list_from_view_layer(context)
    #             print(f"View Layer: {current_name}")




    @classmethod
    def register(cls):
        """注册回调"""
        if cls.on_scene_or_view_layer_update not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(cls.on_scene_or_view_layer_update)

    @classmethod
    def unregister(cls):
        """取消注册回调"""
        if cls.on_scene_or_view_layer_update in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(cls.on_scene_or_view_layer_update)

    @staticmethod
    def generate_vivid_color():
        """生成更鲜艳的 RGB 颜色"""
        return colorsys.hsv_to_rgb(
            random.random(),
            random.uniform(0.85, 1.0),
            random.uniform(0.8, 1.0)
        )

    @staticmethod
    def force_resync_scene_list_from_view_layer(context):
        scene = context.scene
        view_layer = context.view_layer

        # 原始 lightgroup 名列表
        active_names = [g.name for g in view_layer.lightgroups]

        # 移除 UI 中多余的组
        for item in list(scene.lightgroup_list):
            if item.name not in active_names:
                scene.lightgroup_list.remove(scene.lightgroup_list.find(item.name))

        # 补充缺失组
        for name in active_names:
            if not any(item.name == name for item in scene.lightgroup_list):
                item = scene.lightgroup_list.add()
                item.name = name
                item.color = LightGroupNameSynchronizer.generate_vivid_color()
                item.visible = True

        # ✅ 只检查当前视图层中启用集合的灯光对象，防止污染其他灯光
        valid_lights = [
            obj for obj in context.view_layer.objects
            if obj.type == 'LIGHT' and obj.visible_get()
        ]

        for item in scene.lightgroup_list:
            for light in valid_lights:
                try:
                    if light.lightgroup == item.name:
                        # 为分组内的灯光添加可视标识颜色（避免重复写 obj["lightgroup"]）
                        if "flashaov_lgt_color" not in light:
                            light["flashaov_lgt_color"] = Vector(item.color)
                except Exception:
                    continue  # 安全屏蔽不兼容数据块
                
def view_layer_monitor():
    global last_view_layer_name, last_view_layer_check_time
    context = bpy.context

    # 检查冷却时间
    current_time = time.time()
    if current_time - last_view_layer_check_time < 0.5:
        return  # 一秒内不再检查
    last_view_layer_check_time = current_time

    # 检查视图层变化
    if context.view_layer:
        current_name = context.view_layer.name
        if current_name != last_view_layer_name:
            last_view_layer_name = current_name
            LightGroupNameSynchronizer.force_resync_scene_list_from_view_layer(context)
            print(f"[LightGroup] View Layer changed to: {current_name}")


def register_handler():
    global draw_handler
    if draw_handler is None:
        bpy.types.SpaceView3D.draw_handler_add(
            draw_callback, (), 'WINDOW', 'POST_VIEW')
        print("[DEBUG] 绘制回调已注册")
    bpy.types.SpaceView3D.draw_handler_add(
    view_layer_monitor, (), 'WINDOW', 'POST_PIXEL'
)


def unregister_handler():
    global draw_handler
    if draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(draw_handler, 'WINDOW')
        draw_handler = None


classes = [
    LightGroupItem,
    LIGHTGROUP_UL_list,
    LIGHTGROUP_PT_npanel,
    LIGHTGROUP_OT_add_to,
    LIGHTGROUP_OT_select_group,
    LIGHTGROUP_OT_toggle_group,
    LIGHTGROUP_OT_solo_group,
    LIGHTGROUP_OT_create_empty,
    LIGHTGROUP_OT_create_from_selected,
    LIGHTGROUP_OT_create_from_collection,
    LIGHTGROUP_OT_remove_group,
    LIGHTGROUP_OT_remove_empty_groups,
    LIGHTGROUP_OT_create_world_group,
    LIGHTGROUP_OT_sync_names, 

]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.lightgroup_list = bpy.props.CollectionProperty(type=LightGroupItem)
    bpy.types.Scene.lightgroup_active_index = bpy.props.IntProperty()
    bpy.types.Scene.show_lightgroup_overlay = bpy.props.BoolProperty(default=True)
    bpy.types.Scene.lightgroup_circle_radius = bpy.props.FloatProperty(default=8.0, min=1.0, max=50.0)

    register_handler()

    # 初始化 old_name
    for item in bpy.context.scene.lightgroup_list:
        item.old_name = item.name

    # 注册同步器
    LightGroupNameSynchronizer.register()

    # 首次加载时同步一次
    LightGroupNameSynchronizer.force_resync_scene_list_from_view_layer(bpy.context)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.lightgroup_list
    del bpy.types.Scene.lightgroup_active_index
    del bpy.types.Scene.show_lightgroup_overlay
    del bpy.types.Scene.lightgroup_circle_radius

    unregister_handler()

    # 取消注册同步器
    LightGroupNameSynchronizer.unregister()



if __name__ == "__main__":
    register()
