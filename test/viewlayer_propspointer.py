import bpy

# 定义自定义属性组
class MyCustomProperties(bpy.types.PropertyGroup):
    custom_string: bpy.props.StringProperty(name="Custom String", default="Hello")
    custom_bool: bpy.props.BoolProperty(name="Custom Bool", default=True)

    # 新增按钮功能，打印所有集合
    def print_collections(self, context):
        view_layer = context.view_layer
        print("Visible Collections in Current View Layer:")

        # 遍历当前视图层的所有集合，并筛选出 exclude == 0 的集合
        for collection in view_layer.layer_collection.children:
            if not collection.exclude:  # exclude == 0
                print(collection.collection.name)

# N 面板 UI
class VIEWLAYER_PT_CustomPropertiesPanel(bpy.types.Panel):
    bl_label = "ViewLayer Custom Properties"
    bl_idname = "VIEWLAYER_PT_CustomPropertiesPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        view_layer = context.view_layer

        # 获取当前视图层的自定义属性
        custom_props = getattr(view_layer, "my_view_layer_props", None)

        if custom_props:
            layout.prop(custom_props, "custom_string")
            layout.prop(custom_props, "custom_bool")

            # 添加按钮，点击时调用 print_collections 函数
            layout.operator("view_layer.print_collections", text="Print Visible Collections")
        else:
            layout.label(text="No properties for this view layer.")

# 自定义操作
class VIEWLAYER_OT_PrintCollections(bpy.types.Operator):
    bl_idname = "view_layer.print_collections"
    bl_label = "Print Visible Collections"

    def execute(self, context):
        # 获取当前视图层的自定义属性
        custom_props = getattr(context.view_layer, "my_view_layer_props", None)
        
        if custom_props:
            custom_props.print_collections(context)
        return {'FINISHED'}

# 注册和注销
def register():
    bpy.utils.register_class(MyCustomProperties)
    bpy.utils.register_class(VIEWLAYER_PT_CustomPropertiesPanel)
    bpy.utils.register_class(VIEWLAYER_OT_PrintCollections)

    # 在视图层类型中添加 PointerProperty，指向 MyCustomProperties
    bpy.types.ViewLayer.my_view_layer_props = bpy.props.PointerProperty(type=MyCustomProperties)


def unregister():
    bpy.utils.unregister_class(MyCustomProperties)
    bpy.utils.unregister_class(VIEWLAYER_PT_CustomPropertiesPanel)
    bpy.utils.unregister_class(VIEWLAYER_OT_PrintCollections)

    # 删除 PointerProperty
    del bpy.types.ViewLayer.my_view_layer_props

if __name__ == "__main__":
    register()
