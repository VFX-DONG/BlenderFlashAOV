import bpy
from .CompositorOutfileSet import BlenderCompositor  # 导入节点操作文件

# 定义一个字典来存储 rgb 和 data 参数
format_properties_dict = {
    "format": {
        "name": "RGB Format",
        "items": [
            ('OpenEXR MultiLayer', "OpenEXR MultiLayer", ""),
            ('OpenEXR', "OpenEXR", ""),
            ('PNG', "PNG", ""),
            ('JPEG', "JPEG", "")
        ],
        "default": 'OpenEXR MultiLayer'
    },
    "png_color_depth": {
            "name": "Color Depth",
            "items": [
                ('8', "8 bit", ""),
                ('16', "16 bit", ""),
                ('32', "32 bit", "")
            ],
            "default16": '16',
            "default32": '32'
    },
    "exr_color_depth": {
            "name": "Color Depth",
            "items": [
                ('16', "Float(Half)", ""),
                ('32', "Float(Full)", "")
            ],
            "default16": '16',
            "default32": '32'
            
    },
    "exr_codec": {
        "name": "EXR Codec",
        "items": [
            ('None', 'None', "No compression"),
            ('ZIP', "ZIP", "Lossless ZIP compression"),
            ('PIZ', "PIZ", "Lossless PIZ compression"),
            ('DWAA', "DWAA(lossy)", "Lossy DWAA compression"),
            ('DWAB', "DWAB(lossy)", "Lossy DWAB compression"),
            ('ZIPS', "ZIPS", "Lossless ZIPS compression"),
            ('RLE', "RLE", "Lossless RLE compression"),
            ('Pxr24', "Pxr24(lossy)", "Lossless Pxr24 compression")
        ],
        "defaultZIP": "ZIP",
        "defaultDWAA": "DWAA"
    },
    "color_mode": {
        "name": "Color Node",
        "items":[
            ('BW', 'BW', ""),
            ('RGB', "RGB", ""),
            ('RGBA', "RGBA", "")
        ],
        "default": "RGBA"
    },
    "png_compression": {
        "name": "PNG Compression",
        "description": "PNG compression level (0-15)",
        "min": 0,
        "max": 100,
        "default": 90
    },

    }

class RGBFormatProperties(bpy.types.PropertyGroup):
    format: bpy.props.EnumProperty(
        name=format_properties_dict["format"]["name"],
        items=format_properties_dict["format"]["items"],
        default=format_properties_dict["format"]["default"]
    )  # type: ignore

    png_color_depth: bpy.props.EnumProperty(
        name=format_properties_dict["png_color_depth"]["name"],
        items=format_properties_dict["png_color_depth"]["items"],
        default=format_properties_dict["png_color_depth"]["default16"]
    )  # type: ignore
    exr_color_depth: bpy.props.EnumProperty(
        name=format_properties_dict["exr_color_depth"]["name"],
        items=format_properties_dict["exr_color_depth"]["items"],
        default=format_properties_dict["exr_color_depth"]["default16"]
    )  # type: ignore
    exr_codec: bpy.props.EnumProperty(
        name=format_properties_dict["exr_codec"]["name"],
        items=format_properties_dict["exr_codec"]["items"],
        default=format_properties_dict["exr_codec"]["defaultDWAA"]
    )  # type: ignore
    color_mode: bpy.props.EnumProperty(
        name=format_properties_dict["color_mode"]["name"],
        items=format_properties_dict["color_mode"]["items"],
        default=format_properties_dict["color_mode"]["default"]
    )  # type: ignore
    png_compression: bpy.props.IntProperty(
        name=format_properties_dict["png_compression"]["name"],
        description=format_properties_dict["png_compression"]["description"],
        min=format_properties_dict["png_compression"]["min"],
        max=format_properties_dict["png_compression"]["max"],
        default=format_properties_dict["png_compression"]["default"]
    )  # type: ignore



class DataFormatProperties(bpy.types.PropertyGroup):
    format: bpy.props.EnumProperty(
        name=format_properties_dict["format"]["name"],
        items=format_properties_dict["format"]["items"],
        default=format_properties_dict["format"]["default"]
    )  # type: ignore

    png_color_depth: bpy.props.EnumProperty(
        name=format_properties_dict["png_color_depth"]["name"],
        items=format_properties_dict["png_color_depth"]["items"],
        default=format_properties_dict["png_color_depth"]["default32"]
    )  # type: ignore
    exr_color_depth: bpy.props.EnumProperty(
        name=format_properties_dict["exr_color_depth"]["name"],
        items=format_properties_dict["exr_color_depth"]["items"],
        default=format_properties_dict["exr_color_depth"]["default32"]
    )  # type: ignore
    exr_codec: bpy.props.EnumProperty(
        name=format_properties_dict["exr_codec"]["name"],
        items=format_properties_dict["exr_codec"]["items"],
        default=format_properties_dict["exr_codec"]["defaultZIP"]
    )  # type: ignore
    color_mode: bpy.props.EnumProperty(
        name=format_properties_dict["color_mode"]["name"],
        items=format_properties_dict["color_mode"]["items"],
        default=format_properties_dict["color_mode"]["default"]
    )  # type: ignore
    png_compression: bpy.props.IntProperty(
        name=format_properties_dict["png_compression"]["name"],
        description=format_properties_dict["png_compression"]["description"],
        min=format_properties_dict["png_compression"]["min"],
        max=format_properties_dict["png_compression"]["max"],
        default=format_properties_dict["png_compression"]["default"]
    )  # type: ignore

class FlashAOVProperties(bpy.types.PropertyGroup):
    render_path: bpy.props.StringProperty(
        name="Path",
        description="Base path for rendering",
        default="//render\{scene}_{viewlayer}\{type}",
    ) # type: ignore
    render_name: bpy.props.StringProperty(
        name="Name",
        description="File name template",
        default="{scene}_{viewlayer}_{type}_{v}_####",
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
        name="Show Advanced Settings", default=True)# type: ignore

    # 分离控制
    separate_data: bpy.props.BoolProperty(name="Separate Data", default=True)# type: ignore
    separate_cryptomatte: bpy.props.BoolProperty(
        name="Separate Cryptomatte", default=True)# type: ignore
    separate_shaderaov: bpy.props.BoolProperty(
        name="Separate Shader AOV", default=True)# type: ignore
    separate_lightgroup: bpy.props.BoolProperty(
        name="Separate Light Group", default=True)# type: ignore

    # 输出格式
    rgb: bpy.props.PointerProperty(type=RGBFormatProperties)# type: ignore
    data: bpy.props.PointerProperty(type=DataFormatProperties)# type: ignore

    rgb_parsed_output_path: bpy.props.StringProperty(
        name="Resolved Output Path",
        description="Resolved path with variables",
        default=""
    )# type: ignore


def resolve_output_path(scene, viewlayer_outfile_nodes) -> dict:
    import os

    path_template = scene.flash_aov.render_path
    name_template = scene.flash_aov.render_name
    v = scene.flash_aov.version_number
    project_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0] if bpy.data.filepath else "MyProject"
    formatted_v = f"v{v:02d}"
    paths_dict = {}

    for view_layer_name, nodes in viewlayer_outfile_nodes.items():
        camera = scene.camera
        try:
            for node_type, node in nodes.items():
                resolved_path = path_template.format(
                    scene=scene.name,
                    viewlayer=view_layer_name,
                    type=node_type,
                    v=formatted_v,
                    prj=project_name,
                    cam=camera.name if camera else "Camera"
                )
                resolved_name = name_template.format(
                    scene=scene.name,
                    viewlayer=view_layer_name,
                    type=node_type,
                    v=formatted_v,
                    prj=project_name,
                    cam=camera.name if camera else "Camera"
                )

                full_path = os.path.join(resolved_path, resolved_name)

                if resolved_path.startswith("//"):
                    resolved_path = bpy.path.abspath(resolved_path)

                if view_layer_name not in paths_dict:
                    paths_dict[view_layer_name] = {}

                paths_dict[view_layer_name][node_type] = full_path

        except Exception as e:
            if view_layer_name not in paths_dict:
                paths_dict[view_layer_name] = {}

            paths_dict[view_layer_name][node_type] = f"Error: {str(e)}"

    return paths_dict

def assign_paths_to_nodes(viewlayer_outfile_nodes, paths_dict):
    """将路径字典赋值给合成器输出节点"""
    for view_layer_name, nodes in viewlayer_outfile_nodes.items():
        # 获取该视图层的路径配置
        viewlayer_paths = paths_dict.get(view_layer_name, {})
        
        # 遍历每个输出类型和对应节点
        for node_type, node in nodes.items():
            # 获取对应类型的路径
            path = viewlayer_paths.get(node_type)
            
            if path and node:
                try:
                    node.base_path = path
                    # print(f"成功设置路径 | 视图层：{view_layer_name} | 类型：{node_type} | 路径：{path}")
                except Exception as e:
                    print(f"路径设置失败 | 视图层：{view_layer_name} | 类型：{node_type} | 错误：{str(e)}")
            else:
                missing_info = []
                if not path: missing_info.append("路径")
                if not node: missing_info.append("节点")
                print(f"配置缺失 | 视图层：{view_layer_name} | 类型：{node_type} | 缺失：{'、'.join(missing_info)}")


class FLASH_OT_setup_compositor(bpy.types.Operator):
    bl_idname = "flash.setup_compositor"
    bl_label = "配置输出"

    def execute(self, context):
        flash_aov = context.scene.flash_aov

        compositor = BlenderCompositor(
            separate_data=flash_aov.separate_data,
            separate_cryptomatte=flash_aov.separate_cryptomatte,
            separate_shaderaov=flash_aov.separate_shaderaov,
            separate_lightgroup=flash_aov.separate_lightgroup,
        )
        compositor.enable_denoise = flash_aov.enable_denoise
        viewlayer_outfile_nodes = compositor.setup_compositor_nodes()
        # print(viewlayer_outfile_nodes)
        paths_dict = resolve_output_path(context.scene, viewlayer_outfile_nodes)
        viewlayer_outfile_nodes = compositor.get_output_nodes_by_name()
        assign_paths_to_nodes(viewlayer_outfile_nodes, paths_dict)
        self.report({'INFO'}, "渲染节点配置完成！")
        return {'FINISHED'}


class FLASH_OT_refresh_output_path(bpy.types.Operator):
    bl_idname = "flash.refresh_output_path"
    bl_label = "刷新路径"

    def execute(self, context):
        compositor = BlenderCompositor()
        viewlayer_outfile_nodes = compositor.get_output_nodes_by_name()
        paths_dict = resolve_output_path(context.scene, viewlayer_outfile_nodes)
        assign_paths_to_nodes(viewlayer_outfile_nodes, paths_dict)
        # print(viewlayer_outfile_nodes)
        self.report({'INFO'}, "路径已刷新")
        return {'FINISHED'}

class FLASH_PT_aov_panel(bpy.types.Panel):
    bl_label = "Flash AOV"
    bl_idname = "NODE_PT_flash_aov"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Flash AOV"

    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'CompositorNodeTree'

    def draw(self, context):
        layout = self.layout
        props = context.scene.flash_aov

        col = layout.column(align=True)
        col.label(text="Path")
        col.prop(props, "render_path", text="")

        col = layout.column(align=True)
        col.label(text="Name")
        col.prop(props, "render_name", text="")

        col = layout.column(align=True)
        col.label(text="Version")
        row = col.row(align=True)
        row.prop(props, "version_number", text='')
        row.operator("flash.refresh_output_path", text="", icon='FILE_REFRESH')

        col = layout.column(align=True)
        col.separator()

        row = layout.row()
        row.scale_y = 1.6
        row.operator("flash.setup_compositor", icon='RENDER_STILL')

        box = layout.box()
        row = box.row()
        row.prop(props, "show_advanced", toggle=True, text="Advanced Settings",
                icon='TRIA_DOWN' if props.show_advanced else 'TRIA_RIGHT')

        if props.show_advanced:
            box.label(text="RGB Format", icon='STRIP_COLOR_04')
            box.prop(props.rgb, "format")
            if props.rgb.format == 'OpenEXR' or props.rgb.format == 'OpenEXR MultiLayer':
                box.prop(props.rgb, "exr_color_depth")
                box.prop(props.rgb, "exr_codec")
            elif props.rgb.format == 'PNG':
                box.prop(props.rgb, "png_color_depth")
                box.prop(props.rgb, "color_mode")
                box.prop(props.rgb, "png_color_depth")
                box.prop(props.rgb, "png_compression")
            

            box.separator()
            box.label(text="Data Format", icon='STRIP_COLOR_06')
            box.prop(props.data, "format")
            if props.data.format == 'OpenEXR' or props.data.format == 'OpenEXR MultiLayer':
                box.prop(props.data, "exr_color_depth")
                box.prop(props.data, "exr_codec")
            elif props.data.format == 'PNG':
                box.prop(props.data, "png_color_depth")
                box.prop(props.data, "color_mode")
                box.prop(props.data, "png_color_depth")
                box.prop(props.data, "png_compression")
            

            box.separator()
            box.prop(props, "enable_denoise")
            box.prop(props, "separate_data")
            box.prop(props, "separate_cryptomatte")
            box.prop(props, "separate_shaderaov")
            box.prop(props, "separate_lightgroup")


classes = [
    RGBFormatProperties,
    DataFormatProperties,
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