from ctypes import alignment
from os import fstat
import bpy
import mathutils
from numpy import choose
from .CompositorOutfileSet import BlenderCompositor  # 导入节点操作文件






translations = {
    "en_US": {
        "Path": "Path",
        "Name": "Name",
        "Version": "Version",
        "Configure Output": "Configure Output",
        "Refresh Path": "Refresh Path",
        "Path Protection": "Path Protection",
        "Node Color": "Node Color",
        "RGB Format": "RGB Format",
        "Data Format": "Data Format",
        "Color": "Color",
        "Color Depth": "Color Depth",
        "Codec": "Codec",
        "Compression": "Compression",
        "Quality": "Quality",
        "Enable Denoise": "Enable Denoise",
        "Axis Correct": "Axis Correct",
        "Separate Data": "Separate Data",
        "Separate Cryptomatte": "Separate Cryptomatte",
        "Separate Shader AOV": "Separate Shader AOV",
        "Separate Light Group": "Separate Light Group",
        "Rendering node configuration completed!": "Rendering node configuration completed!",
        "Path refreshed": "Path refreshed",
        "Configure output for all view layers in the current scene": "Configure output for all view layers in the current scene",
        "Project Name": "Project Name",
        "Choose Variable": "choose Variable",
        "Select a variable to insert into the path": "Select a variable to insert into the path",
        "Select a variable to insert into the name": "Select a variable to insert into the name",
        "Refresh version variables": "Refresh version variables",
        "Base output file name": "Base output file name",
        "Basic output path": "Basic output path",
        "Version number for {v}": "Version number for {v}",
        "Protect the current output path of the node": "Protect the current output path of the node",
        "Separate the data layer to a new output node, position, normal, etc": "Separate the data layer to a new output node, position, normal, etc",
        "Separate the cryptomattee layer to a new output node": "Separate the cryptomattee layer to a new output node",
        "Separate the shader AOV layer to a new output node": "Separate the shader AOV layer to a new output node",
        "Separate the light group layer to a new output node": "Separate the light group layer to a new output node"
    },
    "zh_HANS": {
        "Path": "路径",
        "Name": "名称",
        "Version": "版本",
        "Configure Output": "配置输出",
        "Refresh Path": "刷新路径",
        "Path Protection": "路径保护",
        "Node Color": "节点颜色",
        "RGB Format": "色彩层格式",
        "Data Format": "数据层格式",
        "Color": "颜色",
        "Color Depth": "颜色深度",
        "Codec": "编解码器",
        "Compression": "压缩",
        "Quality": "质量",
        "Enable Denoise": "启用降噪",
        "Axis Correct": "轴向修正",
        "Separate Data": "分离数据",
        "Separate Cryptomatte": "分离 Cryptomatte",
        "Separate Shader AOV": "分离 Shader AOV",
        "Separate Light Group": "分离灯光组",
        "Rendering node configuration completed!": "渲染节点配置完成！",
        "Path refreshed": "路径已刷新",
        "Configure output for all view layers in the current scene": "为当前场景所有视图层配置输出",
        "Project Name": "项目名称",
        "Choose Variable": "选择变量",
        "Select variable to insert into file path": "选择变量插入路径",
        "Select variable to insert into file name": "选择变量插入文件名",
        "Refresh version variables": "更新版本变量",
        "Base output file name": "输出文件名",
        "Basic output path": "输出路径",
        "Version number for {v}": "版本号{v}",
        "Protect the current output path of the node": "保护当前节点的输出路径",
        "Separate the data layer to a new output node, position, normal, etc": "分离数据层到新的输出节点，位置，法线，等等",
        "Separate the cryptomatte layer to a new output node":   "分离 Cryptomatte 层到新的输出节点",
        "Separate the shader AOV layer to a new output node": "分离 Shader AOV 层到新的输出节点",
        "Separate the light group layer to a new output node": "分离灯光组层到新的输出节点"
        }
    }


def translate(key):
    lang = bpy.context.preferences.view.language
    return translations.get(lang, translations["en_US"]).get(key, key)


PATH_VARIABLES = [
    ("{scene}", "Scene", "Current scene name"),
    ("{viewlayer}", "View Layer", "Name of the view layer"),
    ("{type}", "Type", "Output type (e.g. rgb, data, cryptomatte)"),
    ("{v}", "Version", "Project version number"),
    ("{prj}", "Project Name", "Base name of the .blend file"),
    ("{cam}", "Camera", "Active camera name"),
    ("{fps}", "FPS", "Frames per second in render settings"),
    ("{fstart}", "Start Frame", "Start frame of animation range"),
    ("{fend}", "End Frame", "End frame of animation range"),
    ("{w}", "Width", "Render resolution width"),
    ("{h}", "Height", "Render resolution height"),
]

# 定义一个字典来存储 rgb 和 data 参数
format_properties_dict = {
    "format": {
        "name": "RGB Format",
        "items": [
            ('OPEN_EXR_MULTILAYER', "OpenEXR MultiLayer", ""),
            ('OPEN_EXR', "OpenEXR", ""),
            ('PNG', "PNG", ""),
            ('JPEG', "JPEG", "")
        ],
        "default": 'OPEN_EXR_MULTILAYER'
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
            ('NONE', 'None', "No compression"),
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
    "png_color_depth": {
            "name": "Color Depth",
            "items": [
                ('8', "8", ""),
                ('16', "16", ""),
            ],
            "default16": '16',
    },
    "png_compression": {
        "name": "PNG Compression",
        "description": "PNG compression level (0-15)",
        "min": 0,
        "max": 100,
        "default": 90
    },
    "jpg_color_mode": {
        "name": "Color Node",
        "items":[
            ('BW', 'BW', ""),
            ('RGB', "RGB", ""),
        ],
        "default": "RGB"
    },
    "jpg_quality": {
        "name": "JPG Quality",
        "description": "JPG Quality",
        "min": 0,
        "max": 100,
        "default": 15
    },
    }

# 定义参数
class RGBFormatProperties(bpy.types.PropertyGroup):
    node_color: bpy.props.FloatVectorProperty(
        name="",
        description="Node color",
        default=(0.05,0.15,0.05),  # 绿色
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0
    )  # type: ignore
    format: bpy.props.EnumProperty(
        name="",
        items=format_properties_dict["format"]["items"],
        default=format_properties_dict["format"]["default"]
    )  # type: ignore
    color_mode: bpy.props.EnumProperty(
        name="",
        items=format_properties_dict["color_mode"]["items"],
        default=format_properties_dict["color_mode"]["default"]
    )  # type: ignore
    exr_color_depth: bpy.props.EnumProperty(
        name="",
        items=format_properties_dict["exr_color_depth"]["items"],
        default=format_properties_dict["exr_color_depth"]["default32"]
    )  # type: ignore
    exr_codec: bpy.props.EnumProperty(
        name="",
        items=format_properties_dict["exr_codec"]["items"],
        default=format_properties_dict["exr_codec"]["defaultDWAA"]
    )  # type: ignore
    png_color_depth: bpy.props.EnumProperty(
        name="",
        items=format_properties_dict["png_color_depth"]["items"],
        default=format_properties_dict["png_color_depth"]["default16"]
    )  # type: ignore
    png_compression: bpy.props.IntProperty(
        name="",
        description=format_properties_dict["png_compression"]["description"],
        min=format_properties_dict["png_compression"]["min"],
        max=format_properties_dict["png_compression"]["max"],
        default=format_properties_dict["png_compression"]["default"],
        subtype='PERCENTAGE'
    )  # type: ignore
    jpg_color_mode: bpy.props.EnumProperty(
        name="",
        items=format_properties_dict["jpg_color_mode"]["items"],
        default=format_properties_dict["jpg_color_mode"]["default"]
    )  # type: ignore
    jpg_quality: bpy.props.IntProperty(
        name="",
        description=format_properties_dict["jpg_quality"]["description"],
        min=format_properties_dict["jpg_quality"]["min"],
        max=format_properties_dict["jpg_quality"]["max"],
        default=format_properties_dict["jpg_quality"]["default"],
        subtype='PERCENTAGE'
    )  # type: ignore


class DataFormatProperties(bpy.types.PropertyGroup):
    node_color: bpy.props.FloatVectorProperty(
        name="",
        description="Node color",
        default=(0.08,0.06,0.2),  # 紫色
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0
    )  # type: ignore
    format: bpy.props.EnumProperty(
        name="",
        items=format_properties_dict["format"]["items"],
        default=format_properties_dict["format"]["default"]
    )  # type: ignore
    color_mode: bpy.props.EnumProperty(
        name="",
        items=format_properties_dict["color_mode"]["items"],
        default=format_properties_dict["color_mode"]["default"]
    )  # type: ignore
    exr_color_depth: bpy.props.EnumProperty(
        name="",
        items=format_properties_dict["exr_color_depth"]["items"],
        default=format_properties_dict["exr_color_depth"]["default32"]
    )  # type: ignore
    exr_codec: bpy.props.EnumProperty(
        name="",
        items=format_properties_dict["exr_codec"]["items"],
        default=format_properties_dict["exr_codec"]["defaultZIP"]
    )  # type: ignore
    png_color_depth: bpy.props.EnumProperty(
        name="",
        items=format_properties_dict["png_color_depth"]["items"],
        default=format_properties_dict["png_color_depth"]["default16"]
    )  # type: ignore
    png_compression: bpy.props.IntProperty(
        name="",
        description=format_properties_dict["png_compression"]["description"],
        min=format_properties_dict["png_compression"]["min"],
        max=format_properties_dict["png_compression"]["max"],
        default=format_properties_dict["png_compression"]["default"],
        subtype='PERCENTAGE'
    )  # type: ignore
    jpg_color_mode: bpy.props.EnumProperty(
        name="",
        items=format_properties_dict["jpg_color_mode"]["items"],
        default=format_properties_dict["jpg_color_mode"]["default"]
    )  # type: ignore
    jpg_quality: bpy.props.IntProperty(
        name="",
        description=format_properties_dict["jpg_quality"]["description"],
        min=format_properties_dict["jpg_quality"]["min"],
        max=format_properties_dict["jpg_quality"]["max"],
        default=format_properties_dict["jpg_quality"]["default"],
        subtype='PERCENTAGE'
    )  # type: ignore


class FlashAOVProperties(bpy.types.PropertyGroup):
    render_path: bpy.props.StringProperty(
        name="Path",
        description=translate("Basic output path"),
        default="//render\{viewlayer}_{v}\{type}",
    ) # type: ignore
    render_name: bpy.props.StringProperty(
        name="Name",
        description=translate("Base output file name"),
        default="{viewlayer}_{type}_####",
    )# type: ignore
    version_number: bpy.props.IntProperty(
        name="v",
        description=translate("Version number for {v}"),
        default=1,
        min=1,
        max=999
    )# type: ignore
    enable_denoise: bpy.props.BoolProperty(
        name=translate("Enable Denoise"), default=True,
        description=translate("Enable denoise")
    )# type: ignore
    axis_correct: bpy.props.BoolProperty(
        name=translate("Axis Correct"), default=True,
        description=translate("Axis Correct")
    )# type: ignore
    path_protection: bpy.props.BoolProperty(
        name="Path Protection", default=False,
        description=translate("Protect the current output path of the node")
        )# type: ignore
    
    # 分离控制
    separate_data: bpy.props.BoolProperty(
        name=translate("Separate Data"), default=False,
        description=translate("Separate the data layer to a new output node, position, normal, etc"))# type: ignore
    separate_cryptomatte: bpy.props.BoolProperty(
        name=translate("Separate Cryptomatte"), default=True,
        description=translate("Separate the cryptomatte layer to a new output node"))# type: ignore
    separate_shaderaov: bpy.props.BoolProperty(
        name=translate("Separate Shader AOV"), default=True,
        description=translate("Separate the shader AOV layer to a new output node"))# type: ignore
    separate_lightgroup: bpy.props.BoolProperty(
        name=translate("Separate Light Group"), default=True,
        description=translate("Separate the light group layer to a new output node"))# type: ignore

    # 输出格式
    rgb: bpy.props.PointerProperty(type=RGBFormatProperties)# type: ignore
    data: bpy.props.PointerProperty(type=DataFormatProperties)# type: ignore


    rgb_parsed_output_path: bpy.props.StringProperty(
        name="Resolved Output Path",
        description="Resolved path with variables",
        default=""
    )# type: ignore

    path_variable: bpy.props.EnumProperty(
        name="Path Variable",
        description="Select a variable to insert into the path",
        items=PATH_VARIABLES,
        # default="A"
    )  # type: ignore


class MY_OT_ChoosePathVariable(bpy.types.Operator):
    bl_idname = "flash.choose_variable_path"
    bl_label = translate("Choose Variable")
    bl_description= translate("Select variable to insert into file path")
    
    variable_path: bpy.props.EnumProperty(
        name=translate("Path Variable"),
        items=PATH_VARIABLES,
    ) #type: ignore

    def execute(self, context):
        props = props = context.scene.flash_aov
        props.render_path = props.render_path + self.variable_path
        return {'FINISHED'}


class MY_OT_ChooseNameVariable(bpy.types.Operator):
    bl_idname = "flash.choose_variable_name"
    bl_label = translate("Choose Variable")
    bl_description = translate("Select variable to insert into file name")
    
    variable_name: bpy.props.EnumProperty(
        name=translate("Path Variable"),
        items=PATH_VARIABLES
    ) #type: ignore

    def execute(self, context):
        props = props = context.scene.flash_aov
        props.render_name = props.render_name + self.variable_name
        return {'FINISHED'}

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
                    cam=camera.name if camera else "Camera",
                    fps=scene.render.fps,
                    fstart=scene.frame_start,
                    fend=scene.frame_end,
                    w=scene.render.resolution_x,
                    h=scene.render.resolution_y
                )
                resolved_name = name_template.format(
                    scene=scene.name,
                    viewlayer=view_layer_name,
                    type=node_type,
                    v=formatted_v,
                    prj=project_name,
                    cam=camera.name if camera else "Camera",
                    fps=scene.render.fps,
                    fstart=scene.frame_start,
                    fend=scene.frame_end,
                    w=scene.render.resolution_x,
                    h=scene.render.resolution_y
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
    bl_idname = "flash_aov.setup_compositor"
    bl_label = translate("Configure Output")
    bl_description  = translate("Configure output for all view layers in the current scene")

    def read_ui_parameters(self, context):
        flash_aov = context.scene.flash_aov
        self.rgb_node_color = flash_aov.rgb.node_color
        self.rgb_format = flash_aov.rgb.format
        self.rgb_color_mode = flash_aov.rgb.color_mode
        self.rgb_exr_color_depth = flash_aov.rgb.exr_color_depth
        self.rgb_exr_codec = flash_aov.rgb.exr_codec
        self.rgb_png_color_depth = flash_aov.rgb.png_color_depth
        self.rgb_png_compression = flash_aov.rgb.png_compression
        self.rgb_jpg_color_mode = flash_aov.rgb.jpg_color_mode
        self.rgb_jpg_quality = flash_aov.rgb.jpg_quality

        self.data_node_color = flash_aov.data.node_color
        self.data_format = flash_aov.data.format
        self.data_color_mode = flash_aov.data.color_mode
        self.data_exr_color_depth = flash_aov.data.exr_color_depth
        self.data_exr_codec = flash_aov.data.exr_codec
        self.data_png_color_depth = flash_aov.data.png_color_depth
        self.data_png_compression = flash_aov.data.png_compression
        self.data_jpg_color_mode = flash_aov.data.jpg_color_mode
        self.data_jpg_quality = flash_aov.data.jpg_quality

    def set_output_node_parameters(self, viewlayer_outfile_nodes):
        for view_layer_name, nodes in viewlayer_outfile_nodes.items():
            for node_type, node in nodes.items():
                node.use_custom_color = True
                if node_type in ['rgb', 'lightgroup']:
                    node.color = [ch**(1/2) for ch in self.rgb_node_color]
                    if self.rgb_format == 'OPEN_EXR_MULTILAYER' or self.rgb_format == 'OPEN_EXR':
                        if self.rgb_format == 'OPEN_EXR':
                            node.format.color_mode = self.rgb_color_mode
                        node.format.file_format = self.rgb_format
                        node.format.color_depth = self.rgb_exr_color_depth
                        node.format.exr_codec = self.rgb_exr_codec
                    elif self.rgb_format == 'PNG':
                        node.format.file_format = self.rgb_format
                        node.format.color_mode = self.rgb_color_mode
                        node.format.color_depth = self.rgb_png_color_depth
                        node.format.compression = self.rgb_png_compression
                    elif self.rgb_format == 'JPEG':
                        node.format.file_format = self.rgb_format
                        node.format.color_mode = self.rgb_jpg_color_mode
                        node.format.quality = self.rgb_jpg_quality

                else:
                    node.color = [ch**(1/2) for ch in self.data_node_color]
                    if self.data_format == 'OPEN_EXR_MULTILAYER' or self.data_format == 'OPEN_EXR':
                        if self.data_format == 'OPEN_EXR':
                            node.format.color_mode = self.data_color_mode
                        node.format.file_format = self.data_format
                        node.format.color_depth = self.data_exr_color_depth
                        node.format.exr_codec = self.data_exr_codec
                    elif self.data_format == 'PNG':
                        node.format.file_format = self.data_format
                        node.format.color_mode = self.rgb_color_mode
                        node.format.color_depth = self.data_png_color_depth
                        node.format.compression = self.data_png_compression
                    elif self.data_format == 'JPEG':
                        node.format.file_format = self.data_format
                        node.format.color_mode = self.data_jpg_color_mode
                        node.format.quality = self.rgb_jpg_quality

    def execute(self, context):
        flash_aov = context.scene.flash_aov

        compositor = BlenderCompositor(
            separate_data=flash_aov.separate_data,
            separate_cryptomatte=flash_aov.separate_cryptomatte,
            separate_shaderaov=flash_aov.separate_shaderaov,
            separate_lightgroup=flash_aov.separate_lightgroup,
        )
        compositor.enable_denoise = flash_aov.enable_denoise
        compositor.axis_correct = flash_aov.axis_correct
        viewlayer_outfile_nodes = compositor.setup_compositor_nodes()
        self.read_ui_parameters(context)
        self.set_output_node_parameters(viewlayer_outfile_nodes)
        
        paths_dict = resolve_output_path(context.scene, viewlayer_outfile_nodes)
        viewlayer_outfile_nodes = compositor.get_output_nodes_by_name()
        if not flash_aov.path_protection:
            assign_paths_to_nodes(viewlayer_outfile_nodes, paths_dict)
        self.report({'INFO'}, translate( "Rendering node configuration completed!"))
        
        
        return {'FINISHED'}


class FLASH_OT_refresh_version(bpy.types.Operator):
    bl_idname = "flash_aov.refresh_version"
    bl_label = translate("Refresh version variables")
    bl_description = ""

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


        row = layout.row()
        row.scale_y = 1.6
        row.operator("flash_aov.setup_compositor", icon='NODE_SEL')


        box = layout.box()
        row = box.row()

        box.prop(props, "path_protection", toggle=True, text=translate("Path Protection"),
            icon='LOCKED' if props.path_protection else 'UNLOCKED')
        
        col = box.column(align=True)
        # col.label(text="Version")
        row = col.row(align=True)
        row.prop(props, "version_number", text='Version')
        split_factor = 0.15
        row.operator("flash_aov.refresh_version", text="", icon='FILE_REFRESH')
        row.enabled = not props.path_protection

        # 修改 layout 布局
        split = box.split(factor=split_factor)
        split.enabled = not props.path_protection
        row = split.row(align=True)
        row.alignment = 'RIGHT'
        row.label(text="Path")
        split2 = split.split(factor=0.9)
        row = split2.row(align=True)
        row.prop(props, "render_path", text="")
        split2.operator_menu_enum("flash.choose_variable_path", "variable_path", text="")

        split = box.split(factor=split_factor)
        split.enabled = not props.path_protection
        row = split.row(align=True)
        row.alignment = 'RIGHT'
        row.label(text="Name")
        split2 = split.split(factor=0.9)
        row = split2.row(align=True)
        row.prop(props, "render_name", text="")
        split2.operator_menu_enum("flash.choose_variable_name", "variable_name", text="")

        
        
        ############################            
        split_factor = 0.3
        box = layout.box()
        #rgb color
        box.separator()
        # box = box.column(align=True)
        split = box.split(factor=split_factor)
        row = split.row()
        row.alignment = 'RIGHT'
        row.label(text=translate("Node Color"))
        split.prop(props.rgb, "node_color")
        #format
        split = box.split(factor=split_factor)
        row = split.row()
        row.alignment = 'RIGHT'
        row.label(text=translate("RGB Format"))
        split.prop(props.rgb, "format")
        # OpenEXR MultiLayer
        if props.rgb.format == 'OPEN_EXR_MULTILAYER' or props.rgb.format == 'OPEN_EXR':
            if props.rgb.format == 'OPEN_EXR':
                split = box.split(factor=split_factor)
                row = split.row()
                row.alignment = 'RIGHT'
                row.label(text="Color")
                row = split.row()
                row.prop(props.rgb, "color_mode", toggle=True, expand=True, text=" ")
                
            split = box.split(factor=split_factor)
            row = split.row()
            row.alignment = 'RIGHT'
            row.label(text="Color Depth")
            row = split.row()
            row.prop(props.rgb, "exr_color_depth", toggle=True, expand=True, text=" ")
            #codec
            split = box.split(factor=split_factor)
            row = split.row()
            row.alignment = 'RIGHT'
            row.label(text="Codec")
            split.prop(props.rgb, "exr_codec")

        elif props.rgb.format == 'PNG':
            split = box.split(factor=split_factor)
            row = split.row()
            row.alignment = 'RIGHT'
            row.label(text="Color")
            row = split.row()
            row.prop(props.rgb, "color_mode", toggle=True, expand=True, text=" ")
            
            split = box.split(factor=split_factor)
            row = split.row()
            row.alignment = 'RIGHT'
            row.label(text="Color Depth")
            row = split.row()
            row.prop(props.rgb, "png_color_depth", toggle=True, expand=True, text=" ")
            #codec
            split = box.split(factor=split_factor)
            row = split.row()
            row.alignment = 'RIGHT'
            row.label(text="Compression")
            split.prop(props.rgb, "png_compression")
            
        elif props.rgb.format == 'JPEG':
            split = box.split(factor=split_factor)
            row = split.row()
            row.alignment = 'RIGHT'
            row.label(text="Color")
            row = split.row()
            row.prop(props.rgb, "jpg_color_mode", toggle=True, expand=True, text=" ")
            
            #Quailty
            split = box.split(factor=split_factor)
            row = split.row()
            row.alignment = 'RIGHT'
            row.label(text="Quality")
            split.prop(props.rgb, "jpg_quality")
            
        box.separator()

        #data color
        split = box.split(factor=split_factor)
        row = split.row()
        row.alignment = 'RIGHT'
        row.label(text=translate("Node Color"))
        split.prop(props.data, "node_color")
        #format
        split = box.split(factor=split_factor)
        row = split.row()
        row.alignment = 'RIGHT'
        row.label(text=translate("Data Format"))
        split.prop(props.data, "format")
        # OpenEXR MultiLayer
        if props.data.format == 'OPEN_EXR_MULTILAYER' or props.data.format == 'OPEN_EXR':
            if props.data.format == 'OPEN_EXR':
                split = box.split(factor=split_factor)
                row = split.row()
                row.alignment = 'RIGHT'
                row.label(text="Color")
                row = split.row()
                row.prop(props.data, "color_mode", toggle=True, expand=True, text=" ")
                
            split = box.split(factor=split_factor)
            row = split.row()
            row.alignment = 'RIGHT'
            row.label(text="Color Depth")
            row = split.row()
            row.prop(props.data, "exr_color_depth", toggle=True, expand=True, text=" ")
            #codec
            split = box.split(factor=split_factor)
            row = split.row()
            row.alignment = 'RIGHT'
            row.label(text="Codec")
            split.prop(props.data, "exr_codec")

            
        elif props.data.format == 'PNG':
            split = box.split(factor=split_factor)
            row = split.row()
            row.alignment = 'RIGHT'
            row.label(text="Color")
            row = split.row()
            row.prop(props.data, "color_mode", toggle=True, expand=True, text=" ")
            
            split = box.split(factor=split_factor)
            row = split.row()
            row.alignment = 'RIGHT'
            row.label(text="Color Depth")
            row = split.row()
            row.prop(props.data, "png_color_depth", toggle=True, expand=True, text=" ")
            #codec
            split = box.split(factor=split_factor)
            row = split.row()
            row.alignment = 'RIGHT'
            row.label(text="Compression")
            split.prop(props.data, "png_compression")
            
        elif props.data.format == 'JPEG':
            split = box.split(factor=split_factor)
            row = split.row()
            row.alignment = 'RIGHT'
            row.label(text="Color")
            row = split.row()
            row.prop(props.data, "jpg_color_mode", toggle=True, expand=True, text=" ")
            
            #Quailty
            split = box.split(factor=split_factor)
            row = split.row()
            row.alignment = 'RIGHT'
            row.label(text="Quality")
            split.prop(props.data, "jpg_quality")
        

        box.separator()
        split = box.split(factor=split_factor)
        row = split.row()
        split.prop(props, "enable_denoise")
        split = box.split(factor=split_factor)
        row = split.row()
        split.prop(props, "axis_correct")
        split = box.split(factor=split_factor)
        row = split.row()
        split.prop(props, "separate_data")
        split = box.split(factor=split_factor)
        row = split.row()
        split.prop(props, "separate_cryptomatte")
        split = box.split(factor=split_factor)
        row = split.row()
        split.prop(props, "separate_shaderaov")
        split = box.split(factor=split_factor)
        row = split.row()
        split.prop(props, "separate_lightgroup")


classes = [
    RGBFormatProperties,
    DataFormatProperties,
    FlashAOVProperties,
    FLASH_OT_setup_compositor,
    FLASH_OT_refresh_version,
    FLASH_PT_aov_panel,
    MY_OT_ChoosePathVariable,
    MY_OT_ChooseNameVariable
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