from itertools import count
import os
from random import shuffle
import re
import select
from tkinter import NO

from cv2 import merge
from numpy import dot, stack

# ------------------------------
# 配置参数
# ------------------------------
AOV_GROUPS = {
    "Diff": ["DiffDir", "DiffInd", "DiffCol"],
    "Gloss": ["GlossDir", "GlossInd", "GlossCol"],
    "Trans": ["TransDir", "TransInd", "TransCol"],
    "VOlume": ["VolumeDir", "VolumeInd", ""],
}

INDEPENDENT_AOVS = ["Emit", "Env"]

NODE_WIDTH = 66

BASE_X = -200
BASE_Y = -500  # 基础Y坐标下移以便上方放置Dot
X_SPACING = 100 # 向右横向间隔
Y_SPACING = -100  # 负值表示向上排列

# ------------------------------
# 节点生成工具函数
# ------------------------------

def create_read(x, y, name="Read", path = "", selected=True):
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
    x = x + NODE_WIDTH/2
    code = f"set {name} [stack 0]\n"
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
    code = f"set {name} [stack 0]\n"
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
    push1 = ""
    push2 = ""
    if input0 and input1:
        count = 2
        push1 = f"push ${input0}"
        push2 = f"push ${input1}"
    elif input0 or input1:
        if input0:
            count = 1
            push1 = f"push ${input0}"                       
        else:
            count = 1
            push2 = f"push ${input1}"
    else:
        count = 0
    code = f"""
set ${name} [statck 0]
{push1}
{push2}
Merge2 {{
 inputs {count}
 operation {operation}
 name {name}
 xpos {x}
 ypos {y}
}}"""
    return code






def add_layer(channel):
    return f"add_layer {{{channel} {channel}.red {channel}.green {channel}.blue {channel}.alpha}}"
def create_set(name):
    return f"set {name} [stack 0]"

def create_push(name):
    return f"push {name}"

# ------------------------------
# 布局生成器类
# ------------------------------
class AOVLayoutGenerator:
    def __init__(self):
        self.script = []
        self.group_start_x = BASE_X
        self.current_group_x = BASE_X
        self.merge_stack = []
        
    def add_line(self, content):
        if content: self.script.append(content)
        

    def add_base_blender_layout(self, posx=0, posy=0, channels=None):
        Col = channels[0]
        Dir = channels[1]
        Ind = channels[2]
        
        w = 200
        h = 400

        
        dot1 = create_dot(posx, posy, "dot1")
        create_set("dot1")
        dot2 = create_dot(posx+w, posy, "dot2")
        create_set("dot2")
        dot3 = create_dot(posx+w*2, posy, "dot3")
        
        
        layer_Ind  = add_layer("DiffInd")
        shuffle1 = create_shuffle(posx+w*2, posy+h, Ind, Ind, 'rgba')
        
        dot4 = create_dot(posx+w*2, posy+h*2, "dot4")
        create_push("dot2")
        layer_Dir  = add_layer("DiffDir")
        shuffle2 = create_shuffle(posx+w*1, posy+h, Dir, Dir, 'rgba')
        merge1 = create_merge(posx+w, posy+h*2, 'plus')
        
        dot5 = create_dot(posx+w, posy+h*3, "dot5")
        create_push("dot1")
        layer_Col  = add_layer("DiffCol")
        shuffle3 = create_shuffle(posx, posy+h, Col, Col, 'rgba')
        merge2 = create_merge(posx, posy+h*3, 'multply')
        
        
        lines = [dot1, dot2, dot3, layer_Ind, shuffle1, dot4, layer_Dir, 
                        shuffle2, merge1, dot5, layer_Col, shuffle3, merge2]

        for i in lines: self.add_line(i)
        
        return lines





    def start_group(self, group_name, posx, poy):
        """开始新AOV组布局"""
        self.add_line(f"# ---- {group_name} AOV Group ----")
        self.current_group_x = self.group_start_x
        
    def add_group_element(self, element_type, input_layer, output_layer):
        """添加组内元素（Dot + Shuffle）"""
        # 计算坐标
        dot_y = BASE_Y + Y_SPACING
        shuffle_y = BASE_Y
        
        # 生成Dot节点
        dot_name = f"Dot_{input_layer}" if input_layer else f"Dot_{output_layer}"
        self.add_line(create_dot(
            x=self.current_group_x,
            y=dot_y,
            name=dot_name
        ))
        
        # 生成Shuffle节点
        if input_layer:
            self.add_line(create_shuffle(
                x=self.current_group_x,
                y=shuffle_y,
                name=f"Shuffle_{input_layer}",
                input_layer=input_layer,
                output_layer=output_layer
            ))
            
        self.current_group_x += X_SPACING
        
    def add_group_merge(self, operation):
        """添加组内合并节点"""
        merge_x = self.current_group_x
        merge_y = BASE_Y + 150  # 合并节点下移
        
        merge_name = f"Merge_{len(self.merge_stack)+1}"
        self.add_line(create_merge(
            x=merge_x,
            y=merge_y,
            name=merge_name,
            operation=operation
        ))
        self.merge_stack.append(merge_name)
        self.current_group_x += X_SPACING * 2  # 合并节点后留更多空间
        
    def finalize_group(self):
        """完成当前组布局"""
        self.group_start_x = self.current_group_x + X_SPACING * 3  # 组间大间距
        
    def build_merge_tree(self):
        """构建最终合并链"""
        last_merge = None
        final_x = self.group_start_x
        
        for merge_name in self.merge_stack:
            if last_merge:
                self.add_line(create_merge(
                    x=final_x,
                    y=BASE_Y + 300,  # 最终合并链更高位置
                    name=f"FinalMerge_{merge_name}",
                    operation="plus"
                ))
                final_x += X_SPACING
                last_merge = f"FinalMerge_{merge_name}"
            else:
                last_merge = merge_name
                
        # 添加最终输出
        if last_merge:
            self.add_line(f"""Viewer {{
 name FinalViewer
 xpos {final_x}
 ypos {BASE_Y + 400}
}}""")

# ------------------------------
# 主生成逻辑
# ------------------------------
def generate_nuke_script():
    gen = AOVLayoutGenerator()
    
    # 基础节点
    gen.add_line('version 15.1 v4')
    gen.add_line('Root { inputs 0 name auto_generated.nk }')
    gen.add_line('Read { inputs 0 file_type exr name MainRead xpos -500 ypos -800 }')
    
    # # 处理每个AOV组
    # for group_name, layers in AOV_GROUPS.items():
    #     dir_layer, ind_layer, col_layer = layers
        
    #     gen.start_group(group_name)
        
    #     # 直接光通道
    #     gen.add_group_element("Dir", dir_layer, group_name)
        
    #     # 间接光通道
    #     gen.add_group_element("Ind", ind_layer, group_name)
        
    #     # 颜色混合
    #     if col_layer:
    #         gen.add_group_element("Col", col_layer, group_name)
    #         gen.add_group_merge("multiply")
    #     else:
    #         gen.add_group_merge("plus")
            
    #     gen.finalize_group()
    
    # # 独立AOV处理
    # gen.add_line("\n# ---- Independent AOVs ----")
    # current_x = gen.group_start_x
    # for aov in INDEPENDENT_AOVS:
    #     gen.add_line(create_dot(current_x, BASE_Y + Y_SPACING, f"Dot_{aov}"))
    #     gen.add_line(create_shuffle(current_x, BASE_Y, f"Shuffle_{aov}", aov, aov))
    #     current_x += X_SPACING * 2
    
    # # 构建最终合并树
    # gen.build_merge_tree()
    
    gen.add_base_blender_layout(channels=AOV_GROUPS['Diff'])
    
    # 写入文件
    with open("auto_layout.nk", "w") as f:
        f.write("\n\n".join(gen.script))


    
# 示例用法：生成完整片段
def generate_example():
    parts = []
    parts.append(create_read(x=0, y=0, name="Read", path="input.exr"))
    parts.append(create_dot(x=0, y=200, name="DotAA", input="Read"))
    parts.append(create_dot(x=200, y=200, name="DotBB", input="DotAA"))
    parts.append(create_dot(x=400, y=200, name="DotCC", input="DotBB"))
    parts.append(create_shuffle(x=200, y=400, name="shuffleA", input_layer="rgba", output_layer="rgba", input="DotBB"))
    parts.append(create_shuffle(x=400, y=400, name="shuffleB", input_layer="rgba", output_layer="rgba", input="DotCC"))

    # 创建 Shuffle 节点（接在 Dot 后）
    
    # parts.append(create_shuffle(100, 200, name="ShuffleA", input_layer="DiffDir", output_layer="Diff"), input="DotA")

    # 创建 Merge 节点（连接 Dot 和 Shuffle）
    # parts.append(create_merge(100, 300, name="MergeA", operation="plus", input0="DotA", input1="DotB"))

    return "\n".join(parts)


# 打印或写入 .nk 文件
if __name__ == "__main__":
    nk_script = generate_example()
    print(nk_script)

    # 如果想写入文件
    with open(".//test//example_aov_nodes.nk", "w") as f:
        f.write(nk_script)
