import bpy
from .CompositorOutfileSet import BlenderCompositor  # 导入节点操作文件


class FlashAOVProperties(bpy.types.PropertyGroup):
    render_path: bpy.props.StringProperty(
        name="Path",
        description="Base path for rendering",
        default="//render/{scene}/{scene}_{viewlayer}/{type}",
    )# type: ignore

    render_name: bpy.props.StringProperty(
        name="Name",
        description="File name template",
        default="{scene}_{viewlayer}_{type}_{v}_####.exr",
    )# type: ignore

    version_number: bpy.props.IntProperty(
        name="v",
        description="Version number for {v}",
        default=1,
        min=1,
        max=999
    )# type: ignore
    enable_denoise: bpy.props.BoolProperty(
        name="Enable Denoise",
        default=True
    )# type: ignore
    show_advanced: bpy.props.BoolProperty(
        name="Show Advanced Settings", default=False)# type: ignore

    # 分离控制
    separate_data: bpy.props.BoolProperty(name="Separate Data", default=True)# type: ignore
    separate_cryptomatte: bpy.props.BoolProperty(
        name="Separate Cryptomatte", default=True)# type: ignore
    separate_shaderaov: bpy.props.BoolProperty(
        name="Separate Shader AOV", default=True)# type: ignore
    separate_lightgroup: bpy.props.BoolProperty(
        name="Separate Light Group", default=True) # type: ignore

    # 输出格式
    rgb_format: bpy.props.EnumProperty(
        name="RGB Format",
        items=[('OPEN_EXR', "OpenEXR", ""), ('PNG', "PNG", ""), ('TIFF', "TIFF", ""), ('JPEG', "JPEG", ""), ('BMP', "BMP", "")],
        default='OPEN_EXR'
    )# type: ignore
    data_format: bpy.props.EnumProperty(
        name="Data Format",
        items=[('OPEN_EXR', "OpenEXR", ""), ('PNG', "PNG", ""), ('TIFF', "TIFF", ""), ('JPEG', "JPEG", ""), ('BMP', "BMP", "")],
        default='OPEN_EXR'
    )# type: ignore

    color_depth: bpy.props.EnumProperty(
        name="Color Depth",
        items=[('8', "8 bit", ""), ('16', "16 bit", ""), ('32', "32 bit", "")],
        default='16'
    )# type: ignore
    exr_codec: bpy.props.EnumProperty(
        name="EXR Codec",
        items=[('ZIP', "ZIP", ""), ('PIZ', "PIZ", ""), ('DWAA', "DWAA", ""), ('DWAB', "DWAB", "")],
        default='ZIP'
    )# type: ignore
    png_compression: bpy.props.IntProperty(
        name="PNG Compression",
        description="PNG compression level (0-15)",
        min=0, max=15, default=15
    )# type: ignore
    color_management: bpy.props.EnumProperty(
        name="Color Management",
        items=[('sRGB', "sRGB", ""), ('Linear', "Linear", "")],
        default='Linear'
    )# type: ignore
    parsed_output_path: bpy.props.StringProperty(
        name="Resolved Output Path",
        description="Resolved path with variables",
        default=""
    ) # type: ignore

def resolve_output_path(scene):
    import os
    path_template = scene.flash_aov.render_path
    name_template = scene.flash_aov.render_name
    v = scene.flash_aov.version_number
    view_layer = bpy.context.view_layer
    camera = scene.camera
    project_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0] if bpy.data.filepath else "MyProject"
    formatted_v = f"v{v:02d}"
    try:
        resolved_path = path_template.format(
            scene=scene.name,
            viewlayer=view_layer.name,
            type="rgb",
            v=formatted_v,
            prj=project_name,
            cam=camera.name if camera else "Camera"
        )
        resolved_name = name_template.format(
            scene=scene.name,
            viewlayer=view_layer.name,
            type="rgb",
            v=formatted_v,
            prj=project_name,
            cam=camera.name if camera else "Camera"
        )
        if resolved_path.startswith("//"):
            resolved_path = bpy.path.abspath(resolved_path)
        resolved = os.path.join(resolved_path, resolved_name)
        scene.flash_aov.parsed_output_path = resolved
    except Exception as e:
        scene.flash_aov.parsed_output_path = f"Error: {str(e)}"


class FLASH_OT_setup_compositor(bpy.types.Operator):
    bl_idname = "flash.setup_compositor"
    bl_label = "配置渲染"

    def execute(self, context):
        props = context.scene.flash_aov

        compositor = BlenderCompositor(
            separate_data=props.separate_data,
            separate_cryptomatte=props.separate_cryptomatte,
            separate_shaderaov=props.separate_shaderaov,
            separate_lightgroup=props.separate_lightgroup,
        )
        compositor.enable_denoise = props.enable_denoise
        compositor.setup_compositor_nodes()

        self.report({'INFO'}, "渲染节点配置完成！")
        return {'FINISHED'}


class FLASH_OT_refresh_output_path(bpy.types.Operator):
    bl_idname = "flash.refresh_output_path"
    bl_label = "刷新路径"

    def execute(self, context):
        resolve_output_path(context.scene)
        self.report({'INFO'}, "路径已刷新")
        return {'FINISHED'}


class FLASH_PT_aov_panel(bpy.types.Panel):
    bl_label = "Flash AOV"
    bl_idname = "NODE_PT_flash_aov"  # 修改 ID 名称以避免冲突
    bl_space_type = 'NODE_EDITOR'  # 修改为空间类型 NODE_EDITOR
    bl_region_type = 'UI'  # 修改为 UI 区域类型
    bl_category = "Flash AOV"  # 设置 N 面板的分类

    @classmethod
    def poll(cls, context):
        # 确保仅在合成节点编辑器中显示
        return context.space_data.tree_type == 'CompositorNodeTree'

    def draw(self, context):
        layout = self.layout
        props = context.scene.flash_aov

        col = layout.column(align=True)
        col.label(text="Path")
        col.prop(props, "render_path", text="")  # 展示输入框

        col = layout.column(align=True)
        col.label(text="Name")
        col.prop(props, "render_name", text="")  # 展示输入框

        row = layout.row(align=True)
        row.prop(props, "version_number")
        row.operator("flash.refresh_output_path", text="", icon='FILE_REFRESH')
        layout.label(text=f"Output Path: {props.parsed_output_path}")

        layout.prop(props, "enable_denoise")

        row = layout.row()
        row.scale_y = 1.6
        row.operator("flash.setup_compositor", icon='RENDER_STILL')

        box = layout.box()
        row = box.row()
        row.prop(props, "show_advanced", toggle=True, text="Advanced Settings",
                    icon='TRIA_DOWN' if props.show_advanced else 'TRIA_RIGHT')

        if props.show_advanced:
            box.label(text="RGB Format")
            box.prop(props, "rgb_format")
            if props.rgb_format == 'OPEN_EXR':
                box.prop(props, "color_depth")
                box.prop(props, "exr_codec")
            elif props.rgb_format == 'PNG':
                box.prop(props, "color_depth")
                box.prop(props, "png_compression")
            box.prop(props, "color_management")

            box.separator()
            box.label(text="Data Format")
            box.prop(props, "data_format")
            if props.data_format == 'OPEN_EXR':
                box.prop(props, "color_depth")
                box.prop(props, "exr_codec")
            elif props.data_format == 'PNG':
                box.prop(props, "color_depth")
                box.prop(props, "png_compression")
            box.prop(props, "color_management")

            box.separator()
            box.prop(props, "separate_data")
            box.prop(props, "separate_cryptomatte")
            box.prop(props, "separate_shaderaov")
            box.prop(props, "separate_lightgroup")


classes = [
    FlashAOVProperties,
    FLASH_OT_setup_compositor,
    FLASH_OT_refresh_output_path,
    FLASH_PT_aov_panel
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.flash_aov = bpy.props.PointerProperty(
        type=FlashAOVProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.flash_aov


if __name__ == "__main__":
    register()