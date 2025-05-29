from itertools import count
import os
from random import shuffle
import re
import select
from textwrap import indent
from tkinter import NO

from cv2 import merge
from flask import g
from numpy import dot, stack

# ------------------------------
# 配置参数
# ------------------------------
AOV_GROUPS = {
    "Diff": ["DiffCol", "DiffDir", "DiffInd"],
    "Gloss": ["GlossCol", "GlossDir", "GlossInd"],
    "Trans": ["TransCol", "TransDir", "TransInd"],
    "VOlume": ["", "VolumeDir", "VolumeInd"],
}
INDEPENDENT_AOVS = ["Emit", "Env"]

NODE_WIDTH = 66
NODE_HEIGHT = 8
STEP_X = 150 # 向右
STEP_Y = 100  # 向下


# ------------------------------
# 节点生成工具函数
# ------------------------------

def create_read(x, y, name="Read", path = "", selected=True):
    code = "\n"
    code = f"set {name} [stack 0]\n"
    code += f"""Read {{
    inputs 0
    file "{path}"
    origset true
    name {name}
    selected {selected}
    xpos {x}
    ypos {y}
    }}"""
    return code


def create_dot(x, y, name="DotA", input="", selected=True):
    code = "\n"
    x = x + NODE_WIDTH/2
    y = y + NODE_HEIGHT/2
    code += f"set {name} [stack 0]\n"
    code += f"push {input}\n"
    code += f"""Dot {{
    inputs {1}
    name {name}
    selected {selected}
    xpos {x}
    ypos {y}
    }}"""
    return code


def create_shuffle(x, y, name, input_layer, output_layer, input=""):
    code = "\n"
    code += f"set {name} [stack 0]\n"
    code += f"push {input}\n"
    code += f"""Shuffle2 {{
    fromInput1 {{{{0}} B}}
    in1 {input_layer}
    fromInput2 {{{{0}} B}}
    mappings "4 {input_layer}.red 0 0 {output_layer}.red 0 0 {input_layer}.green 0 1 {output_layer}.green 0 1 {input_layer}.blue 0 2 {output_layer}.blue 0 2 {input_layer}.alpha 0 3 {output_layer}.alpha 0 3"
    name {name}
    xpos {x}
    ypos {y}
    postage_stamp true
}}"""
    return code


def create_merge(x, y, name, operation="plus", input0="", input1=""):
    code = "\n"
    code = f"set {name} [stack 0]\n"
    code += f"push {input0}\n"
    code += f"push {input1}\n"
    code += f"""Merge2 {{
 inputs {2}
 operation {operation}
 name {name}
 xpos {x}
 ypos {y}
}}"""
    return code






def add_layer(channel):
    return f"add_layer {{{channel} {channel}.red {channel}.green {channel}.blue {channel}.alpha}}"




# ------------------------------
# 布局生成器类
# ------------------------------
class BlenderAOVLayout():
    def __init__(self):
        self.script = []
        self.base_x = 0
        self.base_y = 0

    @staticmethod
    def generate_col_mult_light(base_x, base_y, channels, input="", hash = ""):
        col = AOV_GROUPS[channels][0]
        dir = AOV_GROUPS[channels][1]
        ind = AOV_GROUPS[channels][2]


        name = col[0:-3]

        parts = []
        parts.append(create_dot(x=base_x, y=base_y, name="DotA1_"+name+hash, input=input))
        parts.append(create_dot(x=base_x+STEP_X, y=base_y, name="DotA2_"+name+hash, input="DotA1_"+name+hash))
        parts.append(create_dot(x=base_x+STEP_X*2, y=base_y, name="DotA3_"+name+hash, input="DotA2_"+name+hash))
        
        parts.append(create_shuffle(x=base_x, y=base_y+STEP_Y, name="col_"+hash, input_layer=col, output_layer="rgba", input="DotA1_"+name+hash))
        parts.append(create_shuffle(x=base_x+STEP_X, y=base_y+STEP_Y, name="dir_"+hash, input_layer=dir, output_layer="rgba", input="DotA2_"+name+hash))
        parts.append(create_shuffle(x=base_x+STEP_X*2, y=base_y+STEP_Y, name="ind_"+hash, input_layer=ind, output_layer="rgba", input="DotA3_"+name+hash))
        
        parts.append(create_dot(x=base_x+STEP_X*2, y=base_y+STEP_Y*3, name="DotC3_"+name+hash, input="ind_"+hash))
        parts.append(create_merge(x=base_x+STEP_X, y=base_y+STEP_Y*3, name="mergeInd_"+hash, operation="plus", input0="DotC3_"+name+hash, input1="dir_"+hash))
        
        parts.append(create_dot(x=base_x+STEP_X, y=base_y+STEP_Y*4, name="DotD2_"+name+hash, input="mergeInd_"+hash))
        parts.append(create_merge(x=base_x, y=base_y+STEP_Y*4, name="mergeDir_"+hash, operation="multiply", input0="DotD2_"+name+hash, input1="col_"+hash))

        return "\n".join(parts)


# 打印或写入 .nk 文件
if __name__ == "__main__":
    hash = "hash"
    
    nk_script = ""
    nk_script = create_read(x=0, y=0, name="Read", path="input.exr")
    nk_script += create_dot(x=0, y=200, name="DotAA", input="Read")
    
    generate_col_mult_light = BlenderAOVLayout.generate_col_mult_light
    base_x = 200
    hash = "hash1"
    nk_script += generate_col_mult_light(base_x=base_x, base_y=200, channels='Diff', input="DotAA", hash = hash)
    input = "DotA3_"+"Diff"+hash
    hash = "hash2"
    nk_script += generate_col_mult_light(base_x=base_x+STEP_X*3, base_y=200, channels='Gloss', input=input, hash = hash)
    input = "DotA3_"+"Gloss"+hash
    hash = "hash3"
    nk_script += generate_col_mult_light(base_x=base_x+STEP_X*6, base_y=200, channels='Trans', input=input, hash = hash)
    input = "DotA3_"+"Trans"+hash
    hash = "hash4"
    nk_script += generate_col_mult_light(base_x=base_x+STEP_X*9, base_y=200, channels='Diff', input=input, hash = hash)
    print(nk_script)

    # 如果想写入文件
    with open(".//test//example_aov_nodes.nk", "w") as f:
        f.write(nk_script)
