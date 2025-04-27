
bl_info = {
    "name": "Flash AOV",
    "author": "Xiao ZhenDong",
    "description": "",
    "blender": (2, 80, 0),
    "version": (1, 0, 0),
    "location": "",
    "warning": "",
    "category": "Generic",
}

from . import auto_load
from . import main
# from . import LightGroupMananger

def register():
    # auto_load.register()
    main.register()
    
    # LightGroupMananger.register()

def unregister():
    # auto_load.unregister()
    main.unregister()
    # LightGroupMananger.unregister()
