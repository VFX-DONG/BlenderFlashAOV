
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
        "Light Groups": "Light Groups",
        "Light Groups Manager": "Light Groups Manager",
        "Show LightGroup Color": "Show LightGroup Color",
        "Size": "Size",
        "From Selected Lights": "From Selected Lights",
        "From Selected Collection": "From Selected Collection",
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
        "Removed {count} empty light groups": "Removed {count} empty light groups"
    },
    "zh_HANS": {
        "Light Groups": "灯光组",
        "Light Groups Manager": "灯光组管理器",
        "Show LightGroup Color": "显示灯光组颜色",
        "Size": "大小",
        "From Selected Lights": "从选中灯光创建",
        "From Selected Collection": "从选中的集合创建",
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
        "Removed {count} empty light groups": "移除了 {count} 个空灯光组"
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
    name: bpy.props.StringProperty()  # type: ignore
    color: bpy.props.FloatVectorProperty(
        subtype='COLOR', size=3, min=0.0, max=1.0)  # type: ignore
    visible: bpy.props.BoolProperty(default=True)  # type: ignore
    solo: bpy.props.BoolProperty(default=False)  # type: ignore
    has_world: bpy.props.BoolProperty(
        name="Has World", default=False)  # type: ignore


class LIGHTGROUP_UL_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        group = item
        scene = context.scene
        view_layer = context.view_layer
        # enabled_collections = set()


        # 判断组中是否有灯光处于启用集合中



        # ==== UI 绘制开始 ====

        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False)

        # 显示灯光 + world 统计数量
        # 如果组内存在world, 显示world图标
        # icon_type = 'WORLD' if item.has_world else 'LIGHT'
        # row.label(text=f"{count}", icon=icon_type)

        # 选中对象是否属于该组
        obj = context.active_object
        in_group = obj and obj.select_get() and any(
            o.lightgroup == group.name for o in context.selected_objects if o.type == 'LIGHT'
        )
        toggle = row.operator("lightgroup.add_to", text="", icon='RADIOBUT_ON' if in_group else 'RADIOBUT_OFF')
        toggle.group_name = group.name

        vis_icon = 'HIDE_OFF' if group.visible else 'HIDE_ON'
        vis = row.operator("lightgroup.toggle_group", text="", icon=vis_icon)
        vis.group_name = group.name

        solo_icon = 'SOLO_ON' if group.solo else 'BLANK1'
        solo = row.operator("lightgroup.solo_group", text="", icon=solo_icon)
        solo.group_name = group.name

        sub = row.row(align=True)
        sub.scale_x = 0.4
        sub.prop(group, "color", text="", emboss=True)




class LIGHTGROUP_PT_npanel(bpy.types.Panel):
    bl_label = translate("Light Groups Manager")
    bl_idname = "LIGHTGROUP_PT_npanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = translate("Light Groups")

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        if not hasattr(scene, "lightgroup_list") or not hasattr(scene, "lightgroup_active_index"):
            layout.label(text=translate("Light Groups数据未初始化"), icon='ERROR')
            return

        # 顶部显示控制
        row = layout.row(align=True)
        row.prop(scene, "show_lightgroup_overlay", text=translate("Show LightGroup Color"), toggle=True, icon='HIDE_OFF')
        row.prop(scene, "lightgroup_circle_radius", text=translate("Size"))

        layout.operator("lightgroup.create_world_group", text=translate("WorldGroup"), icon='WORLD')

        # 直接使用 template_list，过滤逻辑由 UIList 自行处理
        layout.template_list("LIGHTGROUP_UL_list", "", scene, "lightgroup_list", scene, "lightgroup_active_index")

        # 操作行
        row = layout.row(align=True)
        row.operator("lightgroup.create_empty", icon='ADD')
        row.operator("lightgroup.remove_group", icon='REMOVE')
        row.operator("lightgroup.remove_empty_groups", icon='TRASH', text=translate("Remove Empty"))

        row2 = layout.row(align=True)
        row2.operator("lightgroup.create_from_selected", icon='LIGHT', text=translate("From Selected Lights"))
        row2.operator("lightgroup.create_from_collection", icon='OUTLINER_COLLECTION', text=translate("From Selected Collection"))


class LIGHTGROUP_OT_add_to(bpy.types.Operator):
    bl_idname = "lightgroup.add_to"
    bl_label = translate("Add/Remove to Group")
    bl_description = translate("将选中灯光分配到当前Light Groups")
    group_name: bpy.props.StringProperty()

    def execute(self, context):
        group_name = self.group_name
        view_layer = context.view_layer
        updated = False

        # 确保当前视图层存在这个 Light Group
        bpy.ops.scene.view_layer_add_lightgroup(name=group_name)

        for obj in context.selected_objects:
            if obj.type != 'LIGHT':
                continue

            # 如果已经在该组，则移除
            if obj.lightgroup == group_name:
                obj.lightgroup = ""
            else:
                obj.lightgroup = group_name

            updated = True

        if not updated:
            self.report({'WARNING'}, translate("No lights selected"))
            return {'CANCELLED'}

        # 刷新 UI
        for win in context.window_manager.windows:
            for area in win.screen.areas:
                if area.type in {'VIEW_3D', 'PROPERTIES'}:
                    area.tag_redraw()

        return {'FINISHED'}


class LIGHTGROUP_OT_toggle_group(bpy.types.Operator):
    bl_idname = "lightgroup.toggle_group"
    bl_label = translate("Toggle Group Visibility")
    bl_description = translate("切换该Light Groups下所有灯光的显示状态")
    group_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene

        # 查找当前视图层全部Light Groupslightgroups = context.view_layer.lightgroups
        # 通过匹配object.lightgroup属性，找到对应的灯光
        # 切换灯光可见性

        # 遍历所有灯光，定位属于该组的对象
        for obj in bpy.data.objects:
            if obj.type == 'LIGHT' and obj.lightgroup == self.group_name:
                obj.hide_viewport
                obj.hide_render
                
        # 如果是WorldGroup也属于该组，也同步控制它的lightoutput


        # 强制刷新 UI
        for win in context.window_manager.windows:
            for area in win.screen.areas:
                if area.type in {'VIEW_3D', 'PROPERTIES'}:
                    area.tag_redraw()

        return {'FINISHED'}



class LIGHTGROUP_OT_solo_group(bpy.types.Operator):
    bl_idname = "lightgroup.solo_group"
    bl_label = translate("Solo Group")
    group_name: bpy.props.StringProperty() # type: ignore

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
            self.report({'WARNING'}, f"Group '{group_name}' not found in scene.lightgroup_list")
            return {'CANCELLED'}

        # 切换当前组的 solo 状态
        new_solo_state = not current_item.solo

        # 更新所有组的 solo 标记
        for item in scene.lightgroup_list:
            item.solo = False
        current_item.solo = new_solo_state

        if new_solo_state:
            # 独显该组：隐藏其他组的灯光
            for obj in objects:
                if obj.type != 'LIGHT':
                    continue
                if obj.lightgroup == group_name:
                    obj.hide_viewport = False
                    obj.hide_render = False
                else:
                    obj.hide_viewport = True
                    obj.hide_render = True
        else:
            # 取消独显：恢复所有灯光显示
            for obj in objects:
                if obj.type == 'LIGHT':
                    obj.hide_viewport = False
                    obj.hide_render = False

        # 强制刷新界面
        for win in context.window_manager.windows:
            for area in win.screen.areas:
                if area.type in {'VIEW_3D', 'PROPERTIES'}:
                    area.tag_redraw()

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

        self.report({'INFO'}, translate("Created new empty light group: {}").format(new_group_name))
        return {'FINISHED'}


class LIGHTGROUP_OT_create_from_selected(bpy.types.Operator):
    bl_idname = "lightgroup.create_from_selected"
    bl_label = translate("From Selected Lights")
    bl_description = translate("Create light groups from selected lights (skips duplicates)")

    def execute(self, context):
        scene = context.scene
        view_layer = context.view_layer

        created_count = 0
        skipped_count = 0

        # 获取所有选中的灯光对象
        selected_lights = [obj for obj in context.selected_objects if obj.type == 'LIGHT' and obj.visible_get()]

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
            for light in lights:
                light.lightgroup = group_name

            # 如果插件自己的列表中没有该组，给 scene.lightgroup_list 添加条目
            if not any(item.name == group_name for item in scene.lightgroup_list):
                item = scene.lightgroup_list.add()
                item.name = group_name
                item.color = self.generate_vivid_color()
                item.visible = True
                item.solo = False
                item.has_world = False

        # —— 结果反馈 —— #
        if created_count:
            self.report({'INFO'}, translate("Created {} new light groups").format(created_count))
        if skipped_count:
            self.report({'INFO'}, translate("{} light group(s) already exist, skipped creation").format(skipped_count))
        if created_count == 0 and skipped_count == 0:
            self.report({'WARNING'}, translate("No new light groups were created or skipped"))
        if not any(obj.lightgroup for obj in selected_lights):
            self.report({'WARNING'}, translate("No lights were assigned to any group"))

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
    bl_label = "From Selected Collection"

    def execute(self, context):
        #如果集合启用，为选中集合在当前视图层创建Light Groups bpy.ops.scene.view_layer_add_lightgroup()
        #Light Groups名称为集合名称
        #遍历集合内灯光，为灯光对象的lightgroup属性赋值
        return {'FINISHED'}


class LIGHTGROUP_OT_remove_group(bpy.types.Operator):
    bl_idname = "lightgroup.remove_group"
    bl_label = ""

    def execute(self, context):
        #删除所选列表元素对应的灯光组bpy.ops.scene.view_layer_add_lightgroup()
        
        return {'FINISHED'}


class LIGHTGROUP_OT_create_world_group(bpy.types.Operator):
    bl_idname = "lightgroup.create_world_group"
    bl_label = translate("创建WorldGroup")
    bl_description = translate("创建一个新的Light Groups并将当前世界分配给它")

    def execute(self, context):
        scene = context.scene
        world = scene.world
        group_list = scene.lightgroup_list

        #创建一个新的Light Groups, bpy.ops.scene.view_layer_add_lightgroup()
        # 将当前世界分配给它
        # 绑定 World 数据 world.lightgroup = world.name

        self.report({'INFO'}, translate(
            "Created group and assigned World").format(group_name=world.name))
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
        items_to_remove = [item for item in current_lightgroups if item not in new_lightgroups]
        # 记录移除的数量
        removed_count = len(current_lightgroups)


        # 移除未使用的项
        for item in items_to_remove:
            scene.lightgroup_list.remove(scene.lightgroup_list.find(item))

        self.report({'INFO'}, translate("Removed {} empty light groups").format(removed_count))

        # 刷新UI
        for win in context.window_manager.windows:
            for area in win.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

        return {'FINISHED'}



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

]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.lightgroup_list = bpy.props.CollectionProperty(
        type=LightGroupItem)
    bpy.types.Scene.lightgroup_active_index = bpy.props.IntProperty()
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

 

    # 初始化 old_name 属性
    for item in bpy.context.scene.lightgroup_list:
        item.old_name = item.name

    register_handler()
    


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.lightgroup_list
    del bpy.types.Scene.lightgroup_active_index
    del bpy.types.Scene.show_lightgroup_overlay

    unregister_handler()



if __name__ == "__main__":
    register()
