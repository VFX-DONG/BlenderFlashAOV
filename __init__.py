bl_info = {
    "name": "Flash AOV(Alpha)",
    "author": "DONG",
    "description": "Quickly complete blender AOV output configuration",
    "blender": (3, 50, 0),
    "version": (1, 1, 0),
    "location": "N Panel",
    "doc_url":"https://www.notion.so/Flash-AOV-1e31c885588c802fb145f7e8ab8dc1d0?pvs=4",
    "warning": "",
    "category": ""
}


from . import main




def register():
    main.register()
    # LightGroupMananger.register()

def unregister():
    main.unregister()
    # LightGroupMananger.unregister()
