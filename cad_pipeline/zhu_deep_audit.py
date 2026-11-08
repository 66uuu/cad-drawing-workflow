# -*- coding: utf-8 -*-
"""深度审计：检查轴网、标注、标高、文字内容、HATCH填充、节点分类"""
from pathlib import Path
from collections import Counter
import ezdxf

CLEAN = Path(__file__).resolve().parent / "_zhu_audit" / "cleaned"

def audit_detail(p):
    doc = ezdxf.readfile(p)
    msp = doc.modelspace()
    info = {"file": p.name}

    # 1. AXIS层详情：轴线数量、长度、位置、是否有编号
    axis_lines = []
    axis_circles = []
    axis_text = []
    for e in msp:
        if e.dxf.layer == "AXIS":
            t = e.dxftype()
            if t == "LINE":
                s, en = e.dxf.start, e.dxf.end
                length = ((en.x-s.x)**2 + (en.y-s.y)**2)**0.5
                axis_lines.append((round(s.x), round(s.y), round(en.x), round(en.y), round(length)))
            elif t == "CIRCLE":
                axis_circles.append((round(e.dxf.center.x), round(e.dxf.center.y), round(e.dxf.radius)))
            elif t == "TEXT":
                axis_text.append(e.dxf.text)
    info["axis_lines"] = axis_lines
    info["axis_circles"] = axis_circles
    info["axis_text"] = axis_text[:20]

    # 2. DIM层详情：是真DIMENSION还是手绘LINE
    dim_lines = 0
    dim_dim = 0
    dim_text = []
    for e in msp:
        if e.dxf.layer == "DIM":
            t = e.dxftype()
            if t == "LINE":
                dim_lines += 1
            elif t == "DIMENSION":
                dim_dim += 1
            elif t == "TEXT":
                dim_text.append(e.dxf.text)
    info["dim_handmade_lines"] = dim_lines
    info["dim_real_dimension"] = dim_dim
    info["dim_text"] = dim_text[:20]

    # 3. TEXT层详情：文字内容样本+字高
    text_items = []
    for e in msp:
        if e.dxf.layer == "TEXT" and e.dxftype() == "TEXT":
            h = e.dxf.height
            txt = e.dxf.text
            text_items.append((round(h), txt[:30]))
    info["text_items"] = text_items[:30]
    info["text_height_counter"] = Counter(h for h,_ in text_items)

    # 4. HATCH层：有多少填充
    hatch_count = 0
    for e in msp:
        if e.dxf.layer == "HATCH":
            hatch_count += 1
    info["hatch_count"] = hatch_count

    # 5. WALL层：线长度分布
    wall_lines = 0
    wall_long = 0
    for e in msp:
        if e.dxf.layer == "WALL" and e.dxftype() == "LINE":
            wall_lines += 1
            s, en = e.dxf.start, e.dxf.end
            length = ((en.x-s.x)**2 + (en.y-s.y)**2)**0.5
            if length > 1000:
                wall_long += 1
    info["wall_line_count"] = wall_lines
    info["wall_long_lines(>1m)"] = wall_long

    # 6. 检查是否有标高文字（含±或+或-的数字）
    elev_texts = []
    for e in msp:
        if e.dxftype() == "TEXT":
            txt = e.dxf.text
            if ("±" in txt or "+" in txt or "-" in txt) and any(c.isdigit() for c in txt):
                elev_texts.append(txt)
    info["elev_texts"] = elev_texts[:20]

    return info

# 选几个代表性文件深度审计
samples = [
    "01_原始结构图.dxf",
    "02_平面布置图.dxf",
    "09_灯具定位图.dxf",
    "E-01_前厅立面图.dxf",
    "E-06_核心筒立面图.dxf",
    "N-01_吊顶收口节点图.dxf",
    "N-06_门套收口大样图.dxf",
    "办公空间平面图_CAD_轴网尺寸修正版.dxf",
]

for s in samples:
    p = CLEAN / s
    if not p.exists():
        continue
    print("\n" + "="*70)
    print("文件:", s)
    info = audit_detail(p)
    print("  轴网线: %d 条, 轴网圆: %d 个, 轴网文字: %s" % (
        len(info["axis_lines"]), len(info["axis_circles"]), info["axis_text"]))
    if info["axis_lines"]:
        for ln in info["axis_lines"][:5]:
            print("    线: (%d,%d) -> (%d,%d) 长%d" % ln)
    print("  DIM层: 手绘线=%d, 真标注=%d, DIM文字=%s" % (
        info["dim_handmade_lines"], info["dim_real_dimension"], info["dim_text"]))
    print("  HATCH填充: %d 个" % info["hatch_count"])
    print("  WALL层: %d条线, 其中长墙(>1m)=%d" % (info["wall_line_count"], info["wall_long_lines(>1m)"]))
    print("  标高文字: %s" % info["elev_texts"])
    print("  文字样本(字高:内容):")
    for h, t in info["text_items"][:15]:
        print("    %.0fmm: %s" % (h, t))
