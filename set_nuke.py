from itertools import count
import os
from random import shuffle
import re
import select
from textwrap import indent
from tkinter import NO, X

from cv2 import merge
from numpy import dot, stack

# ------------------------------
# 配置参数
# ------------------------------
AOV_GROUPS = {
    "Diff": ["DiffCol", "DiffDir", "DiffInd"],
    "Gloss": ["GlossCol", "GlossDir", "GlossInd"],
    "Trans": ["TransCol", "TransDir", "TransInd"],
    "Volume": ["", "VolumeDir", "VolumeInd"],
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


# def create_shuffle(x, y, name, input_layer, output_layer, input=""):
#     code = "\n"
#     code += f"set {name} [stack 0]\n"
#     code += f"push {input}\n"
#     code += f"""Shuffle2 {{
#     fromInput1 {{{{0}} B}}
#     in1 {input_layer}
#     fromInput2 {{{{0}} B}}
#     mappings "4 {input_layer}.red 0 0 {output_layer}.red 0 0 {input_layer}.green 0 1 {output_layer}.green 0 1 {input_layer}.blue 0 2 {output_layer}.blue 0 2 {input_layer}.alpha 0 3 {output_layer}.alpha 0 3"
#     name {name}
#     xpos {x}
#     ypos {y}
#     postage_stamp true
# }}"""
#     return code

def create_shuffle(x, y, name, input_layer, output_layer, input=""):
    code = "\n"
    code += f"set {name} [stack 0]\n"
    code += f"push {input}\n"
    code += f"""Shuffle2 {{
    fromInput1 {{{{0}} B}}
    in1 rgba
    fromInput2 {{{{0}} B}}
    mappings "4 rgba.red 0 0 {output_layer}.red 0 0 rgba.green 0 1 {output_layer}.green 0 1 rgba.blue 0 2 {output_layer}.blue 0 2 rgba.alpha 0 3 {output_layer}.alpha 0 3"
    name {name}
    xpos {x}
    ypos {y}
    postage_stamp true
}}"""
    return code

def create_merge(x, y, name, operation="plus", input0="", input1=""):
    code = "\n"
    code += f"set {name} [stack 0]\n"
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
    def generate_col_mult_light(base_x, base_y, chan_key, input="", hash = ""):
        col = AOV_GROUPS[chan_key][0]
        dir = AOV_GROUPS[chan_key][1]
        ind = AOV_GROUPS[chan_key][2]


        name = chan_key
    
        parts = []
        if chan_key != "Volume":
            parts.append(create_dot(x=base_x, y=base_y, name="DotA1_"+name+"_"+hash, input=input))
            parts.append(create_dot(x=base_x+STEP_X, y=base_y, name="DotA2_"+name+"_"+hash, input="DotA1_"+name+"_"+hash))
            parts.append(create_dot(x=base_x+STEP_X*2, y=base_y, name="DotA3_"+name+"_"+hash, input="DotA2_"+name+"_"+hash))
            
            parts.append(create_shuffle(x=base_x, y=base_y+STEP_Y, name=col+"_"+hash, input_layer=col, output_layer="rgba", input="DotA1_"+name+"_"+hash))
            parts.append(create_shuffle(x=base_x+STEP_X, y=base_y+STEP_Y, name=dir+"_"+hash, input_layer=dir, output_layer="rgba", input="DotA2_"+name+"_"+hash))
            parts.append(create_shuffle(x=base_x+STEP_X*2, y=base_y+STEP_Y, name=ind+"_"+hash, input_layer=ind, output_layer="rgba", input="DotA3_"+name+"_"+hash))
            
            parts.append(create_dot(x=base_x+STEP_X*2, y=base_y+STEP_Y*3, name="DotC3_"+name+"_"+hash, input=ind+"_"+hash))
            parts.append(create_merge(x=base_x+STEP_X, y=base_y+STEP_Y*3, name="merge_"+ind+"_"+hash, operation="plus", input0="DotC3_"+name+"_"+hash, input1=dir+"_"+hash))
            
            parts.append(create_dot(x=base_x+STEP_X, y=base_y+STEP_Y*4, name="DotD2_"+name+"_"+hash, input="merge_"+ind+"_"+hash))
            parts.append(create_merge(x=base_x, y=base_y+STEP_Y*4, name="merge_"+name+"_"+hash, operation="multiply", input0="DotD2_"+name+"_"+hash, input1=col+"_"+hash))

        else:
            parts.append(create_dot(x=base_x, y=base_y, name="DotA1_"+name+"_"+hash, input=input))
            parts.append(create_dot(x=base_x+STEP_X, y=base_y, name="DotA2_"+name+"_"+hash, input="DotA1_"+name+"_"+hash))
            
            parts.append(create_shuffle(x=base_x, y=base_y+STEP_Y, name=dir+"_"+hash, input_layer=col, output_layer="rgba", input="DotA1_"+name+"_"+hash))
            parts.append(create_shuffle(x=base_x+STEP_X, y=base_y+STEP_Y, name=ind+"_"+hash, input_layer=dir, output_layer="rgba", input="DotA2_"+name+"_"+hash))
            
            parts.append(create_dot(x=base_x+STEP_X, y=base_y+STEP_Y*2, name="DotC3_"+name+"_"+hash, input=ind+"_"+hash))
            parts.append(create_merge(x=base_x, y=base_y+STEP_Y*2, name="merge_"+ind+"_"+hash, operation="plus", input0="DotC3_"+name+"_"+hash, input1=dir+"_"+hash))



        return "\n".join(parts)

    @staticmethod
    def generate_channels_merge(base_x, base_y, aov_groups, input="", hash = ""):
        channels_merge_script = ""
        x = base_x
        y = base_y
        group_x = STEP_X*3
        
        
        input_read = "Dot_read_"+hash
        input_diff = "DotA3_"+"Diff_"+hash
        input_trans = "DotA3_"+"Trans_"+hash
        input_glass = "DotA3_"+"Gloss_"+hash

        input = "Dot_read_"+hash
        if 'Diff' in aov_groups:
            channels_merge_script += BlenderAOVLayout.generate_col_mult_light(base_x=x, base_y=y, chan_key='Diff', input=input, hash = hash)
            if 'Gloss' in aov_groups:
                x += group_x if 'Diff' in aov_groups else 0
                channels_merge_script += BlenderAOVLayout.generate_col_mult_light(base_x=x, base_y=y, chan_key='Gloss', input=input, hash = hash)
            if 'Trans' in aov_groups:
                x += group_x if 'Gloss' in aov_groups else 0
                channels_merge_script += BlenderAOVLayout.generate_col_mult_light(base_x=x, base_y=y, chan_key='Trans', input=input, hash = hash)
            if 'Volume' in aov_groups:
                x += group_x if 'Trans' in aov_groups else 0
                channels_merge_script += BlenderAOVLayout.generate_col_mult_light(base_x=x, base_y=y, chan_key='Volume', input=input, hash = hash)
        # else:
            


        return channels_merge_script



    @staticmethod
    def create_read(x, y, path, hash=""):
        nk_script = ""
        nk_script = create_read(x=0, y=0, name="Read_"+hash, path="input.exr")
        nk_script += create_dot(x=0, y=200, name="Dot_read_"+hash, input="Read_"+hash)
        return nk_script

    
    @staticmethod
    def generate_group_merge(base_x, base_y, aov_groups, hash=""):
        # 合并灯光层的merge节点
        # col = AOV_GROUPS[chan_key][0]
        # dir = AOV_GROUPS[chan_key][1]
        # ind = AOV_GROUPS[chan_key][2]

        
        nk_script = ""
        x = base_x
        y = base_y
        group_x = STEP_X*3
        group_y = STEP_Y*2
        count = len(aov_groups)
        
        if count == 2:
            input = "merge_" + aov_groups[1] + "_"+hash
            dot_e2_name = "Dot_" + 'E2_' + hash
            nk_script += create_dot(x+group_x, y, name=dot_e2_name, input=input, selected=True)
            
            input1 = "merge_" + aov_groups[0] + "_"+hash
            merge_E1 = "merge_" + 'E1_' + hash
            nk_script += create_merge(x=x, y=y, name=merge_E1, operation="plus", input0=dot_e2_name, input1=input1)
            
        if count == 3:
            input = "merge_" + aov_groups[1] + "_"+hash
            dot_e2_name = "Dot_" + 'E2_' + hash
            nk_script += create_dot(x+group_x, y, name=dot_e2_name, input=input, selected=True)
            
            input1 = "merge_" + aov_groups[0] + "_"+hash
            merge_E1 = "merge_" + 'E1_' + hash
            nk_script += create_merge(x=x, y=y, name=merge_E1, operation="plus", input0=dot_e2_name, input1=input1)
            
            
            input = "merge_" + aov_groups[2] + "_"+hash
            dot_f2_name = "Dot_" + 'F2_' + hash
            nk_script += create_dot(x=x+group_x*2, y=y+group_y, name=dot_f2_name, input=input, selected=True)
            
            input1 = "merge_" + aov_groups[0] + "_"+hash
            merge_F1 = "merge_" + 'F1_' + hash
            nk_script += create_merge(x=x, y=y+group_y, name=merge_F1, operation="plus", input0=dot_f2_name, input1=merge_E1)
            
        if count == 4:
            input = "merge_" + aov_groups[1] + "_"+hash
            dot_e2_name = "Dot_" + 'E2_' + hash
            nk_script += create_dot(x+group_x, y, name=dot_e2_name, input=input, selected=True)
            
            input1 = "merge_" + aov_groups[0] + "_"+hash
            merge_E1 = "merge_" + 'E1_' + hash
            nk_script += create_merge(x=x, y=y, name=merge_E1, operation="plus", input0=dot_e2_name, input1=input1)


            input = "merge_" + aov_groups[2] + "_"+hash
            dot_f2_name = "Dot_" + 'F2_' + hash
            nk_script += create_dot(x=x+group_x*2, y=y+group_y, name=dot_f2_name, input=input, selected=True)
            
            input1 = "merge_" + aov_groups[0] + "_"+hash
            merge_F1 = "merge_" + 'F1_' + hash
            nk_script += create_merge(x=x, y=y+group_y, name=merge_F1, operation="plus", input0=dot_f2_name, input1=merge_E1)
            
            
            input = "merge_" + aov_groups[3] + "_"+hash
            dot_g2_name = "Dot_" + 'G2_' + hash
            nk_script += create_dot(x=x+group_x*3, y=y+group_y*2, name=dot_g2_name, input=input, selected=True)
            
            input1 = "merge_" + aov_groups[0] + "_"+hash
            merge_G1 = "merge_" + 'G1_' + hash
            nk_script += create_merge(x=x, y=y+group_y*2, name=merge_G1, operation="plus", input0=dot_g2_name, input1=merge_F1)

            
                
        return nk_script

# 打印或写入 .nk 文件
if __name__ == "__main__":
    hash = "hash"
    nk_script = ""
    
    nk_script = BlenderAOVLayout.create_read(x=0, y=0, path="./", hash=hash)
    
    nk_script += BlenderAOVLayout.generate_channels_merge(base_x=200, base_y=200, aov_groups=['Diff','Gloss',"Trans", 'Volume'], input="Dot_read_", hash = hash)
    
    nk_script += BlenderAOVLayout.generate_group_merge(base_x=200, base_y=800, aov_groups=['Diff','Gloss',"Trans", 'Volume'], hash = hash)
    
    print(nk_script)

    # 如果想写入文件
    with open(".//test//example_aov_nodes.nk", "w") as f:
        f.write(nk_script)
