# -*- coding: utf-8 -*-
"""读取参考 DXF 的图层表及模型空间实用图层统计。"""
import collections
import json
from pathlib import Path
import ezdxf

ROOT = Path(__file__).resolve().parent / "_layer_audit"
OUT = ROOT / "reference_layers.json"
rows = {}
for p in sorted((ROOT / "reference_dxf").glob("ref*.dxf")):
    doc = ezdxf.readfile(p)
    msp = doc.modelspace()
    used = collections.Counter(e.dxf.layer for e in msp)
    layers = []
    for lay in doc.layers:
        d = lay.dxf
        layers.append({
            "name": d.name,
            "color": d.get("color", 7),
            "linetype": d.get("linetype", "Continuous"),
            "lineweight": d.get("lineweight", -3),
            "on": lay.is_on(),
            "frozen": lay.is_frozen(),
            "locked": lay.is_locked(),
            "plot": lay.dxf.get("plot", 1),
            "used_modelspace": used.get(d.name, 0),
        })
    rows[p.stem] = {"file": str(p), "layer_count": len(layers), "layers": layers}
    print("\n=== %s: %d layers, %d modelspace entities ===" % (p.stem, len(layers), len(msp)))
    for x in layers:
        print("%-36s color=%-4s lw=%-4s lt=%-18s on=%s frozen=%s used=%d" % (
            x["name"], x["color"], x["lineweight"], x["linetype"], x["on"], x["frozen"], x["used_modelspace"]))
OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nJSON", OUT)
