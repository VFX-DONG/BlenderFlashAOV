
# from networkx import radius
import bpy
import gpu
import random
import colorsys
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from math import sin, cos, pi
from bpy_extras.view3d_utils import location_3d_to_region_2d, region_2d_to_location_3d


draw_handler = None

# 定义翻译字典
translations = {
    "en_US": {
        "灯光组": "Light Groups",
        "灯光组管理器": "Light Groups Manager",
        "显示灯光组": "Show LightGroup Color",
        "大小": "Size",
        "选中的灯光创建": "From Selected Lights",
        "选中的集合创建": "From Selected Collection",
        "移除空灯光组": "Remove Empty Light Groups",
        "世界环境": "WorldGroup",
        "添加/移除到组": "Add/Remove to Group",
        "切换组可见性": "Toggle Group Visibility",
        "独显组": "Solo Group",
        "未选中任何灯光对象": "No lights selected",
        "灯光组已存在，跳过创建": "Light group already exists, skipped creation",
        "灯光组创建完成": "Light groups created successfully",
        "没有可分配的世界环境": "No world to assign",
        "已创建世界环境灯光组": "Created group and assigned World",
        "移除了 {count} 个空灯光组": "Removed {count} empty light groups"
    },
    "zh_HANS": {
        "灯光组": "灯光组",
        "灯光组管理器": "灯光组管理器",
        "显示灯光组": "显示灯光组",
        "大小": "大小",
        "选中的灯光创建": "选中的灯光创建",
        "选中的集合创建": "选中的集合创建",
        "移除空灯光组": "移除空灯光组",
        "世界环境": "世界环境",
        "添加/移除到组": "添加/移除到组",
        "切换组可见性": "切换组可见性",
        "独显组": "独显组",
        "未选中任何灯光对象": "未选中任何灯光对象",
        "灯光组已存在，跳过创建": "灯光组已存在，跳过创建",
        "灯光组创建完成": "灯光组创建完成",
        "没有可分配的世界环境": "没有可分配的世界环境",
        "已创建世界环境灯光组": "已创建世界环境灯光组",
        "移除了 {count} 个空灯光组": "移除了 {count} 个空灯光组"
    }
}

# 动态翻译函数


def translate(key):
    lang = bpy.context.preferences.view.language
    return translations.get(lang, translations["en_US"]).get(key, key)


def calculate_screen_radius(context, location):
    """计算屏幕中小圆的世界空间大小"""
    region = context.region
    rv3d = context.region_data
    coord = location_3d_to_region_2d(region, rv3d, location)
    if coord is None:
        return 0.0

    # 使用用户设置的小圆大小
    desired_pixel_radius = context.scene.lightgroup_circle_radius
    offset = Vector((desired_pixel_radius, 0))
    new_coord = coord + offset
    world_offset = region_2d_to_location_3d(
        region, rv3d, new_coord, location) - location
    return world_offset.length


def draw_callback():
    """视口绘制函数：绘制小圆圈代表灯光组"""
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
        radius = calculate_screen_radius(context, loc)  # 动态获取大小
        # radius = 20
        segments = 32

        group = obj.get("lightgroup", "")
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


class LightGroupItem(bpy.types.PropertyGroup):
    def update_name(self, context):
        old_name = self.old_name
        new_name = self.name
        if old_name != new_name:
            # 更新灯光对象的绑定关系
            for obj in bpy.data.objects:
                if obj.get("lightgroup") == old_name:
                    obj["lightgroup"] = new_name

            # 更新世界环境的绑定关系
            world = context.scene.world
            if world and world.get("lightgroup") == old_name:
                world["lightgroup"] = new_name

            # 更新旧名称
            self.old_name = new_name

    old_name: bpy.props.StringProperty()  # type: ignore
    name: bpy.props.StringProperty(update=update_name)  # type: ignore
    color: bpy.props.FloatVectorProperty(
        subtype='COLOR', size=3, min=0.0, max=1.0)  # type: ignore
    visible: bpy.props.BoolProperty(default=True)  # type: ignore
    solo: bpy.props.BoolProperty(default=False)  # type: ignore
    has_world: bpy.props.BoolProperty(
        name="Has World", default=False)  # type: ignore


class LIGHTGROUP_UL_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        group = item
        if self.layout_type not in {'DEFAULT', 'COMPACT'}:
            return

        view_layer = context.view_layer
        scene = context.scene
        enabled_collections = set()

        # 获取当前视图层中所有启用的集合
        def collect_enabled_collections(layer_col):
            if not layer_col.exclude:
                enabled_collections.add(layer_col.collection)
                for child in layer_col.children:
                    collect_enabled_collections(child)
        collect_enabled_collections(view_layer.layer_collection)

        # 判断该灯光组中是否有任何灯光在启用的集合中
        any_light_visible = False
        for obj in bpy.data.objects:
            if obj.type == 'LIGHT' and obj.get("lightgroup") == group.name:
                if any(c in enabled_collections for c in obj.users_collection):
                    any_light_visible = True
                    break

        # 若该组中无任何灯光位于启用集合中，跳过绘制
        # if not any_light_visible:
        #     return

        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False)

        # 统计数量（同样受限于启用集合）
        count = 0
        for obj in bpy.data.objects:
            if obj.type == 'LIGHT' and obj.get("lightgroup") == item.name:
                if any(c in enabled_collections for c in obj.users_collection):
                    count += 1
        if scene.world and scene.world.get("lightgroup") == item.name:
            count += 1

        icon_type = 'WORLD' if item.has_world else 'LIGHT'
        row.label(text=f"{count}", icon=icon_type)

        obj = context.active_object
        in_group = obj and obj.select_get() and any(
            o.get("lightgroup") == item.name for o in context.selected_objects if o.type == 'LIGHT')
        toggle = row.operator("lightgroup.add_to", text="",
                              icon='RADIOBUT_ON' if in_group else 'RADIOBUT_OFF', emboss=True)
        toggle.group_name = item.name

        vis_icon = 'HIDE_OFF' if item.visible else 'HIDE_ON'
        vis = row.operator("lightgroup.toggle_group",
                           text="", icon=vis_icon, emboss=True)
        vis.group_name = item.name

        solo_icon = 'SOLO_ON' if item.solo else 'BLANK1'
        solo = row.operator("lightgroup.solo_group",
                            text="", icon=solo_icon, emboss=True)
        solo.group_name = item.name

        sub = row.row(align=True)
        sub.scale_x = 0.4
        sub.prop(item, "color", text="", emboss=True)



class LIGHTGROUP_PT_npanel(bpy.types.Panel):
    bl_label = translate("灯光组管理器")
    bl_idname = "LIGHTGROUP_PT_npanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = translate("灯光组")

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        if not hasattr(scene, "lightgroup_list") or not hasattr(scene, "lightgroup_index"):
            layout.label(text=translate("灯光组数据未初始化"), icon='ERROR')
            return

        # 顶部显示控制
        row = layout.row(align=True)
        row.prop(scene, "show_lightgroup_overlay", text=translate("显示灯光组"), toggle=True, icon='HIDE_OFF')
        row.prop(scene, "lightgroup_circle_radius", text=translate("大小"))

        layout.operator("lightgroup.create_world_group", text=translate("世界环境"), icon='WORLD')

        # 直接使用 template_list，过滤逻辑由 UIList 自行处理
        layout.template_list("LIGHTGROUP_UL_list", "", scene, "lightgroup_list", scene, "lightgroup_index")

        # 操作行
        row = layout.row(align=True)
        row.operator("lightgroup.create_empty", icon='ADD')
        row.operator("lightgroup.remove_group", icon='REMOVE')
        row.operator("lightgroup.remove_empty_groups", icon='TRASH', text=translate("移除空灯光组"))

        row2 = layout.row(align=True)
        row2.operator("lightgroup.create_from_selected", icon='LIGHT', text=translate("选中的灯光创建"))
        row2.operator("lightgroup.create_from_collection", icon='OUTLINER_COLLECTION', text=translate("选中的集合创建"))


class LIGHTGROUP_OT_add_to(bpy.types.Operator):
    bl_idname = "lightgroup.add_to"
    bl_label = translate("添加/移除到组")
    bl_description = translate("将选中灯光分配到当前灯光组")
    group_name: bpy.props.StringProperty()

    def execute(self, context):
        # 获取当前场景和选中灯光
        scene = context.scene
        selected_lights = [obj for obj in context.selected_objects if obj.type == 'LIGHT']
        
        # 确保当前灯光组有效
        if not self.group_name:
            self.report({'ERROR'}, translate("未选择有效灯光组"))
            return {'CANCELLED'}

        # 遍历所有选中灯光
        for obj in selected_lights:
            # 如果灯光已属于当前组，则移除关联
            if obj.get("lightgroup") == self.group_name:
                del obj["lightgroup"]
            else:
                # 设置灯光组属性
                obj["lightgroup"] = self.group_name

        # 刷新界面
        context.area.tag_redraw()
        return {'FINISHED'}


class LIGHTGROUP_OT_toggle_group(bpy.types.Operator):
    bl_idname = "lightgroup.toggle_group"
    bl_label = "Toggle Group Visibility"
    group_name: bpy.props.StringProperty() # type: ignore

    def execute(self, context):
        view_layer = context.view_layer
        viewlayer_lightgroup_dict = context.scene.viewlayer_lightgroup_dict
        viewlayer_group_info = next(
            (g for g in viewlayer_lightgroup_dict if g.name == view_layer.name), None)
        if not viewlayer_group_info:
            self.report({'ERROR'}, "Light Group not found in this View Layer")
            return {'CANCELLED'}

        group_info = next(
            (g for g in viewlayer_group_info.groups if g.name == self.group_name), None)
        if not group_info:
            self.report({'ERROR'}, "Light Group not found in this View Layer")
            return {'CANCELLED'}

        # 切换可见性
        group_info.visible = not group_info.visible

        # 更新灯光组项的可见性属性
        group_item = next(
            (g for g in context.scene.lightgroup_list if g.name == self.group_name), None)
        if group_item:
            group_item.visible = group_info.visible

        # 控制灯光对象的显示
        for obj in bpy.data.objects:
            if obj.get("lightgroup") == self.group_name:
                obj.hide_render = not group_info.visible
                obj.hide_viewport = not group_info.visible

        # 控制 World 可见性
        world = context.scene.world
        if world and world.get("lightgroup") == self.group_name:
            ntree = world.node_tree
            if ntree:
                output_node = next(
                    (n for n in ntree.nodes if n.type == 'OUTPUT_WORLD'), None)
                if output_node:
                    output_node.mute = not group_info.visible

        # 同步视图层可见性
        for view_layer in context.scene.view_layers:
            for obj in view_layer.objects:
                if obj.get("lightgroup") == self.group_name:
                    obj.hide_viewport = not group_info.visible

        # 同步集合可见性
        for collection in bpy.data.collections:
            for obj in collection.objects:
                if obj.get("lightgroup") == self.group_name:
                    obj.hide_viewport = not group_info.visible

        return {'FINISHED'}


class LIGHTGROUP_OT_solo_group(bpy.types.Operator):
    bl_idname = "lightgroup.solo_group"
    bl_label = translate("独显组")
    group_name: bpy.props.StringProperty() # type: ignore

    def execute(self, context):
        view_layer = context.view_layer
        viewlayer_lightgroup_dict = context.scene.viewlayer_lightgroup_dict
        viewlayer_group_info = next(
            (g for g in viewlayer_lightgroup_dict if g.name == view_layer.name), None)
        if not viewlayer_group_info:
            self.report({'ERROR'}, "Light Group not found in this View Layer")
            return {'CANCELLED'}

        group_info = next(
            (g for g in viewlayer_group_info.groups if g.name == self.group_name), None)
        if not group_info:
            self.report({'ERROR'}, "Light Group not found in this View Layer")
            return {'CANCELLED'}

        # 切换独显状态
        group_info.solo = not group_info.solo

        # 更新灯光组项的独显属性
        group_item = next(
            (g for g in context.scene.lightgroup_list if g.name == self.group_name), None)
        if group_item:
            group_item.solo = group_info.solo

        # 控制其他组的可见性
        for g in viewlayer_group_info.groups:
            if g.name != self.group_name:
                g.visible = False
                g.solo = False
                g_item = next(
                    (gi for gi in context.scene.lightgroup_list if gi.name == g.name), None)
                if g_item:
                    g_item.visible = False

        # 控制灯光对象的独显
        for obj in bpy.data.objects:
            if obj.type == 'LIGHT':
                group = obj.get("lightgroup")
                obj.hide_render = group != self.group_name if group_info.solo else not next(
                    (gi for gi in context.scene.lightgroup_list if gi.name == group and gi.visible), True)
                obj.hide_viewport = obj.hide_render

        # 控制世界环境的独显
        world = context.scene.world
        if world:
            ntree = world.node_tree
            if ntree:
                output_node = next(
                    (n for n in ntree.nodes if n.type == 'OUTPUT_WORLD'), None)
                if output_node:
                    world_group = world.get("lightgroup")
                    output_node.mute = world_group != self.group_name if group_info.solo else not next(
                        (gi for gi in context.scene.lightgroup_list if gi.name == world_group and gi.visible), True)

        return {'FINISHED'}


class LIGHTGROUP_OT_create_empty(bpy.types.Operator):
    bl_idname = "lightgroup.create_empty"
    bl_label = ""

    def execute(self, context):
        view_layer = context.view_layer
        group_name = f"Group{len(context.scene.lightgroup_list)}"
        group_collection = bpy.data.collections.new(name=group_name)
        view_layer.layer_collection.collection.children.link(group_collection)

        # 创建新的灯光组项
        item = context.scene.lightgroup_list.add()
        item.name = group_name
        item.color = (1.0, 1.0, 1.0)
        item.old_name = item.name  # 初始化 old_name

        # 将灯光组信息存储在 Scene 的自定义属性中
        viewlayer_lightgroup_dict = context.scene.viewlayer_lightgroup_dict
        viewlayer_group_info = next(
            (g for g in viewlayer_lightgroup_dict if g.name == view_layer.name), None)
        if not viewlayer_group_info:
            viewlayer_group_info = viewlayer_lightgroup_dict.add()
            viewlayer_group_info.name = view_layer.name

        group_info = viewlayer_group_info.groups.add()
        group_info.name = group_name
        group_info.color = item.color
        group_info.visible = True
        group_info.solo = False
        group_info.has_world = False

        self.report({'INFO'}, "灯光组创建完成")
        return {'FINISHED'}



class LIGHTGROUP_OT_create_from_selected(bpy.types.Operator):
    bl_idname = "lightgroup.create_from_selected"
    bl_label = "从选中灯光创建"
    bl_description = "为每个选中的灯光创建独立灯光组（同名灯光提示跳过）"

    def execute(self, context):
        scene = context.scene
        view_layer = context.view_layer
        active_layer_collection = view_layer.active_layer_collection

        created_count = 0
        skipped_count = 0

        for obj in context.selected_objects:
            if obj.type != 'LIGHT' or not obj.visible_get():
                continue

            group_name = obj.name

            # 避免重复组
            if any(item.name == group_name for item in view_layer.lightgroups):
                skipped_count += 1
                continue

            # 创建 ViewLayer 原生 lightgroup
            bpy.ops.scene.view_layer_add_lightgroup(name=group_name)
            obj.lightgroup = group_name

            # 添加到 scene.lightgroup_list（避免重复）
            group_item = next((item for item in scene.lightgroup_list if item.name == group_name), None)
            if not group_item:
                group_item = scene.lightgroup_list.add()
                group_item.name = group_name
                group_item.color = self.generate_vivid_color()
                group_item.visible = True
                # 设置当前索引
                scene.lightgroup_index = len(scene.lightgroup_list) - 1

                # 强制刷新 UI
                context.area.tag_redraw()

            # 添加到 viewlayer_lightgroup_dict（避免重复）
            viewlayer_group_info = next(
                (g for g in scene.viewlayer_lightgroup_dict if g.name == view_layer.name), None)
            if not viewlayer_group_info:
                viewlayer_group_info = scene.viewlayer_lightgroup_dict.add()
                viewlayer_group_info.name = view_layer.name

            if not any(g.name == group_name for g in viewlayer_group_info.groups):
                new_group = viewlayer_group_info.groups.add()
                new_group.name = group_name
                new_group.color = group_item.color
                new_group.visible = True

            # 确保链接到激活集合（防止 orphan）
            if active_layer_collection and obj.name not in active_layer_collection.collection.objects:
                active_layer_collection.collection.objects.link(obj)

            created_count += 1

        # 构建信息反馈
        msg_parts = []
        if created_count > 0:
            msg_parts.append(translate("成功创建 {count} 个组").format(count=created_count))
        if skipped_count > 0:
            msg_parts.append(translate("跳过 {count} 个重复组").format(count=skipped_count))

        self.report({'INFO'}, "，".join(msg_parts) if msg_parts else translate("无有效操作"))
        return {'FINISHED'}

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
    bl_label = "From Selected Collection"

    def execute(self, context):
        obj = context.active_object
        if obj and obj.users_collection:
            col = obj.users_collection[0]
            item = context.scene.lightgroup_list.add()
            item.name = col.name
            item.color = obj.data.color[:]
            item.old_name = item.name  # 初始化 old_name
            for o in col.objects:
                if o.type == 'LIGHT':
                    o["lightgroup"] = col.name
        return {'FINISHED'}


class LIGHTGROUP_OT_remove_group(bpy.types.Operator):
    bl_idname = "lightgroup.remove_group"
    bl_label = ""

    def execute(self, context):
        scene = context.scene
        idx = scene.lightgroup_index
        if 0 <= idx < len(scene.lightgroup_list):
            group_name = scene.lightgroup_list[idx].name
            for obj in bpy.data.objects:
                if obj.get("lightgroup") == group_name:
                    del obj["lightgroup"]
            scene.lightgroup_list.remove(idx)
        return {'FINISHED'}


class LIGHTGROUP_OT_create_world_group(bpy.types.Operator):
    bl_idname = "lightgroup.create_world_group"
    bl_label = translate("创建世界环境")
    bl_description = translate("创建一个新的灯光组并将当前世界分配给它")

    def execute(self, context):
        scene = context.scene
        world = scene.world
        group_list = scene.lightgroup_list

        if not world:
            self.report({'WARNING'}, translate("没有可分配的世界环境"))
            return {'CANCELLED'}

        if any(item.name == world.name for item in context.scene.lightgroup_list):
            self.report({'INFO'}, f"世界环境灯光组 '{world.name}' 已存在")
            return {'CANCELLED'}

        # 创建新组
        new_group = group_list.add()
        new_group.name = world.name
        new_group.color = (0.8, 0.8, 0.1)
        new_group.has_world = True

        # 绑定 World 数据
        world["lightgroup"] = world.name

        self.report({'INFO'}, translate(
            "已创建世界环境灯光组").format(group_name=world.name))
        return {'FINISHED'}


class LIGHTGROUP_OT_remove_empty_groups(bpy.types.Operator):
    bl_idname = "lightgroup.remove_empty_groups"
    bl_label = translate("移除空灯光组")

    def execute(self, context):
        scene = context.scene
        lightgroup_list = scene.lightgroup_list

        # 记录需要移除的灯光组索引
        groups_to_remove = []

        for idx, group in enumerate(lightgroup_list):
            # 检查是否有灯光对象或世界环境属于该组
            has_lights = any(obj.get(
                "lightgroup") == group.name for obj in bpy.data.objects if obj.type == 'LIGHT')
            has_world = scene.world and scene.world.get(
                "lightgroup") == group.name
            if not (has_lights or has_world):  # 如果既没有灯光也没有世界环境，则标记为移除
                groups_to_remove.append(idx)

        # 从后往前移除，避免索引错乱
        for idx in reversed(groups_to_remove):
            lightgroup_list.remove(idx)

        self.report({'INFO'}, translate("移除了 {count} 个空灯光组").format(
            count=len(groups_to_remove)))
        return {'FINISHED'}


class ViewLayerLightGroupInfo(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    groups: bpy.props.CollectionProperty(type=LightGroupItem)


def register_handler():
    global draw_handler
    if draw_handler is None:
        draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            draw_callback, (), 'WINDOW', 'POST_VIEW')
        print("[LightGroup] draw_handler registered")

        


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
    LIGHTGROUP_OT_toggle_group,
    LIGHTGROUP_OT_solo_group,
    LIGHTGROUP_OT_create_empty,
    LIGHTGROUP_OT_create_from_selected,
    LIGHTGROUP_OT_create_from_collection,
    LIGHTGROUP_OT_remove_group,
    LIGHTGROUP_OT_remove_empty_groups,
    LIGHTGROUP_OT_create_world_group,
    ViewLayerLightGroupInfo  # 添加这一行
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.lightgroup_list = bpy.props.CollectionProperty(
        type=LightGroupItem)
    bpy.types.Scene.lightgroup_index = bpy.props.IntProperty()
    bpy.types.Scene.show_lightgroup_overlay = bpy.props.BoolProperty(
        name="Show Light Group Overlay",
        default=True,
        description="Toggle the light group circle overlay"
    )
    bpy.types.Scene.lightgroup_circle_radius = bpy.props.FloatProperty(
        name="Circle Size",
        default=8.0,
        min=1.0,
        max=50.0,
        description="Set the radius of the light group circles"
    )

    # 为 Scene 添加自定义属性来存储视图层独立的灯光组信息
    bpy.types.Scene.viewlayer_lightgroup_dict = bpy.props.CollectionProperty(
        type=ViewLayerLightGroupInfo,
        description="Dictionary to store light group information for each view layer"
    )

    # 初始化 old_name 属性
    for item in bpy.context.scene.lightgroup_list:
        item.old_name = item.name

    register_handler()
    


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.lightgroup_list
    del bpy.types.Scene.lightgroup_index
    del bpy.types.Scene.show_lightgroup_overlay

    unregister_handler()



if __name__ == "__main__":
    register()
