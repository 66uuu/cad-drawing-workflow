# -*- coding: utf-8 -*-
"""快速验证清洗后的图层结构"""
from pathlib import Path
from collections import Counter
import ezdxf

CLEAN = Path(__file__).resolve().parent / "_zhu_audit" / "cleaned"

for p in sorted(CLEAN.glob("*.dxf")):
    doc = ezdxf.readfile(p)
    msp = doc.modelspace()
    layers = Counter()
    for e in msp:
        layers[e.dxf.layer] += 1
    layer_attrs = []
    for ly in doc.layers:
        if ly.dxf.name not in ("Defpoints",):
            try:
                c = ly.dxf.color
                lw = ly.dxf.lineweight
                lt = ly.dxf.linetype
            except:
                c = "?"; lw = "?"; lt = "?"
            layer_attrs.append((ly.dxf.name, c, lw, lt))
    print("=== %s ===" % p.name)
    print("  图层:", dict(layers.most_common()))
    print("  属性:")
    for name, c, lw, lt in sorted(layer_attrs):
        print("    %-12s color=%-3s lw=%-4s ltype=%s" % (name, c, lw, lt))
