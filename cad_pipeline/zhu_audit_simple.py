# -*- coding: utf-8 -*-
"""简化版审计：直接打印每个文件的图层清单和实体分布"""
from pathlib import Path
from collections import Counter, defaultdict
import ezdxf
from ezdxf import bbox

DXF_DIR = Path(__file__).resolve().parent / "_zhu_audit" / "dxf"

def safe(v, default=0):
    try: return v
    except: return default

for p in sorted(DXF_DIR.glob("*.dxf")):
    print("\n" + "="*70)
    print("文件:", p.name)
    doc = ezdxf.readfile(p)
    msp = doc.modelspace()

    # 图层
    print("--- 图层清单 ---")
    layer_info = []
    for layer in doc.layers:
        try:
            c = layer.dxf.color
            lw = layer.dxf.lineweight
        except:
            c = "?"; lw = "?"
        lt = layer.dxf.linetype
        layer_info.append((layer.dxf.name, c, lw, lt))
    for name, c, lw, lt in layer_info:
        print("  %-20s color=%-3s lineweight=%-5s ltype=%s" % (name, c, lw, lt))

    # 实体统计
    type_layer = defaultdict(Counter)
    type_total = Counter()
    for e in msp:
        t = e.dxftype()
        ly = e.dxf.layer
        type_layer[ly][t] += 1
        type_total[t] += 1

    print("--- 实体类型总计 ---")
    for t, n in type_total.most_common():
        print("  %-12s %d" % (t, n))

    # 每图层实体分布
    print("--- 图层×实体类型 ---")
    for ly, cnt in sorted(type_layer.items()):
        items = ", ".join("%s:%d" % (t,n) for t,n in cnt.most_common())
        print("  [%s] %s" % (ly, items))

    # 文字样式
    print("--- 文字样式 ---")
    for s in doc.styles:
        try:
            print("  %-12s font=%s bigfont=%s" % (s.dxf.name, s.dxf.font, getattr(s.dxf, 'bigfont', '')))
        except:
            pass

    # 字高分布
    heights = Counter()
    for e in msp:
        if e.dxftype() == "TEXT":
            heights[round(e.dxf.height, 1)] += 1
        elif e.dxftype() == "MTEXT":
            heights[round(e.dxf.char_height, 1)] += 1
    print("--- 字高分布 ---")
    for h, n in heights.most_common(10):
        print("  %.1f mm × %d 个" % (h, n))

    # INSERT 块
    blocks = Counter()
    for e in msp:
        if e.dxftype() == "INSERT":
            blocks[e.dxf.name] += 1
    print("--- 插入块 ---")
    for name, n in blocks.most_common(15):
        print("  %-20s × %d" % (name, n))

    # 包围盒
    try:
        ext = bbox.extents(msp)
        print("--- 包围盒 ---")
        print("  X: %.0f ~ %.0f (宽 %.0f)" % (ext.extmin.x, ext.extmax.x, ext.extmax.x-ext.extmin.x))
        print("  Y: %.0f ~ %.0f (高 %.0f)" % (ext.extmin.y, ext.extmax.y, ext.extmax.y-ext.extmin.y))
    except Exception as ex:
        print("  bbox error:", ex)
