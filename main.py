import bpy
import os

from .CompositorOutFileSet import BlenderCompositor


# 全局变量存储上次状态
# 修改全局状态字典，添加工程名跟踪
last_state = {
    'camera_name': "",
    'view_layer_name': "",
    'scene_name': "",
    'project_name': "",  # 新增工程名跟踪
    'file_saved': False  # 新增保存状态跟踪
}

class RenderPathManager:
    @staticmethod
    def format_version_number(version_int):
        """将整型版本号格式化为v+两位数字"""
        return f"v{version_int:02d}"

    @staticmethod
    def update_render_path(scene):
        try:
            # 获取最新数据
            camera = scene.camera
            view_layer = bpy.context.view_layer
            current_scene = bpy.context.scene
            
            # 错误处理
            error_msgs = []
            if not camera:
                error_msgs.append("No camera")
            if not view_layer:
                error_msgs.append("No view layer")
                
            if error_msgs:
                scene.parsed_output_path = f"Error: {', '.join(error_msgs)}"
                return
                
            # 工程名称处理
            blend_file_path = bpy.path.abspath(bpy.data.filepath)
            project_name = os.path.splitext(os.path.basename(blend_file_path))[0] if blend_file_path else "MyProject"
            
            # 格式化版本号
            formatted_version = RenderPathManager.format_version_number(scene.version_number)
            
            # 路径生成
            output_path = scene.render_path_input.format(
                cam=camera.name,
                viewlayer=view_layer.name,
                scene=current_scene.name,
                prj=project_name,
                v=formatted_version
            )
            
            # 处理相对路径
            if output_path.startswith("//"):
                if blend_file_path:
                    base_dir = os.path.dirname(blend_file_path)
                    full_path = os.path.join(base_dir, output_path[2:])
                    scene.parsed_output_path = bpy.path.abspath(full_path)
                else:
                    scene.parsed_output_path = "Error: Save file first"
            else:
                scene.parsed_output_path = output_path
                
        except KeyError as e:
            scene.parsed_output_path = f"Missing variable: {e}"
        except Exception as e:
            scene.parsed_output_path = f"Error: {str(e)}"

    @staticmethod
    def on_render_pre(scene):
        """在渲染开始前强制更新路径"""
        RenderPathManager.update_render_path(scene)
        # 立即应用最新路径到渲染设置
        if not scene.parsed_output_path.startswith("Error"):
            scene.render.filepath = scene.parsed_output_path

    @staticmethod
    def on_save_post(scene):
        """文件保存后强制更新路径"""
        RenderPathManager.update_render_path(scene)
        # 重置状态触发后续更新
        last_state.update({
            'project_name': "",
            'file_saved': False
        })

    @staticmethod
    def detect_name_changes(scene):
        current_project = ""
        if bpy.data.filepath:
            current_project = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
        
        condition_changed = (
            last_state['camera_name'] != (scene.camera.name if scene.camera else "") or
            last_state['view_layer_name'] != bpy.context.view_layer.name or
            last_state['scene_name'] != bpy.context.scene.name or
            last_state['project_name'] != current_project or
            last_state['file_saved'] != bool(bpy.data.filepath)
        )

        if condition_changed:
            RenderPathManager.update_render_path(scene)
            last_state.update({
                'camera_name': scene.camera.name if scene.camera else "",
                'view_layer_name': bpy.context.view_layer.name,
                'scene_name': bpy.context.scene.name,
                'project_name': current_project,
                'file_saved': bool(bpy.data.filepath)
            })


class CustomProperties:
    @staticmethod
    def register():
        # 核心属性注册（补全parsed_output_path）
        bpy.types.Scene.render_path_input = bpy.props.StringProperty(
            name="Render Path",
            default="//render\{prj}_{scene}_{viewlayer}_{cam}_{v}.png",
            update=lambda self, _: update_render_path(self)
        )
        
        bpy.types.Scene.version_number = bpy.props.IntProperty(
            name="Version",
            description="Enter the version number",
            default=1,
            min=1,
            max=99,
            update=lambda self, _: update_render_path(self)
        )
        
        # 必须添加的输出路径属性 ↓
        bpy.types.Scene.parsed_output_path = bpy.props.StringProperty(
            name="Parsed Output Path",
            description="Automatically generated render path",
            default=""
        )

    @staticmethod
    def unregister():
        # 正确的属性注销顺序
        del bpy.types.Scene.render_path_input
        del bpy.types.Scene.version_number
        del bpy.types.Scene.parsed_output_path  # 确保注销该属性


class SetupCompositorNodesOperator(bpy.types.Operator):
    """配置合成器节点"""
    bl_idname = "node.setup_compositor"
    bl_label = "Setup Compositor Nodes"
    bl_options = {'REGISTER', 'UNDO'}

    separate_data: bpy.props.BoolProperty(
        name="Separate Data",
        default=True,
        description="分离数据通道（深度/法线等）"
    )
    separate_cryptomatte: bpy.props.BoolProperty(
        name="Separate Cryptomatte",
        default=True,
        description="分离Cryptomatte通道"
    )
    separate_shadervaov: bpy.props.BoolProperty(
        name="Separate Shader AOV",
        default=True,
        description="分离Shader AOV通道"
    )
    separate_lightgroup: bpy.props.BoolProperty(
        name="Separate Light Groups",
        default=True,
        description="分离灯光组"
    )

    def execute(self, context):
        try:
            # 确保启用节点
            if not context.scene.use_nodes:
                context.scene.use_nodes = True
                context.scene.render.use_compositing = True

            # 初始化合成器
            compositor = BlenderCompositor(context.view_layer.name)
            compositor.setup_compositor_nodes(
                separate_data=self.separate_data,
                separate_cryptomatte=self.separate_cryptomatte,
                separate_shadervaov=self.separate_shadervaov,
                separate_lightgroup=self.separate_lightgroup
            )
            
            self.report({'INFO'}, "合成器节点配置完成!")
            return {'FINISHED'}
            
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"配置失败: {str(e)}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class RenderPathPanel(bpy.types.Panel):
    bl_label = "Render Path Panel"
    bl_idname = "VIEWLAYER_PT_render_path"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "view_layer"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # 主设置区域
        box = layout.box()
        box.prop(scene, "render_path_input")
        box.prop(scene, "version_number")
        box.label(text=f"Current Path: {scene.parsed_output_path}")
        
        # 新增合成器配置按钮
        layout.separator()
        comp_box = layout.box()
        comp_box.label(text="Compositor Setup", icon='NODETREE')
        comp_box.operator(SetupCompositorNodesOperator.bl_idname)

def register():
    CustomProperties.register()
    bpy.utils.register_class(RenderPathManager)
    bpy.utils.register_class(RenderPathPanel)
    bpy.utils.register_class(SetupCompositorNodesOperator)  # 注册新操作类
    bpy.app.handlers.depsgraph_update_post.append(RenderPathManager.detect_name_changes)
    bpy.app.handlers.save_post.append(RenderPathManager.on_save_post)
    bpy.app.handlers.render_pre.append(RenderPathManager.on_render_pre)

def unregister():
    CustomProperties.unregister()
    bpy.utils.unregister_class(RenderPathManager)
    bpy.utils.unregister_class(RenderPathPanel)
    bpy.utils.unregister_class(SetupCompositorNodesOperator)  # 注销新操作类
    if RenderPathManager.detect_name_changes in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(RenderPathManager.detect_name_changes)
    if RenderPathManager.on_save_post in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(RenderPathManager.on_save_post)
    if RenderPathManager.on_render_pre in bpy.app.handlers.render_pre:
        bpy.app.handlers.render_pre.remove(RenderPathManager.on_render_pre)


if __name__ == "__main__":
    register()
    print("Render Path Panel registered!")