bl_info = {
    "name": "Flash AOV", 
    "author": "ZhenDong",
    "description": "Quickly complete blender AOV output configuration",
    "blender": (4, 0, 0),
    "version": (1, 5, 0),
    "location": "N Panel",
    "doc_url": "https://www.notion.so/Flash-AOV-1e31c885588c802fb145f7e8ab8dc1d0?pvs=4",
    "warning": "",
    "category": "Render",
}


from . import main
from . import LightGroupMananger



def register():          
    main.register()
    LightGroupMananger.register()

def unregister():
    main.unregister()
    LightGroupMananger.unregister()
    
