# -*- coding: utf-8 -*-
"""以题目附件-CAD模板及图框.dwg 为唯一图层标准，逐张审计 V3.3 的 34 张 DXF。"""
import collections
import json
import re
from pathlib import Path
import ezdxf

PIPE = Path(__file__).resolve().parent
ROOT = Path(r"D:/UserFiles/Desktop/V3.3最终版")
REF = PIPE / "_layer_audit" / "reference_dxf" / "ref1.dxf"
OUT = PIPE / "_layer_audit"
OUT.mkdir(exist_ok=True)

refdoc = ezdxf.readfile(REF)
ref = {}
for lay in refdoc.layers:
    d = lay.dxf
    ref[d.name] = {
        "color": d.get("color", 7),
        "linetype": d.get("linetype", "Continuous"),
        "lineweight": d.get("lineweight", -3),
        "on": lay.is_on(),
        "frozen": lay.is_frozen(),
        "locked": lay.is_locked(),
        "plot": d.get("plot", 1),
    }

sheets = []
for sub in ["00_图纸目录", "01_平面", "02_立面", "03_节点大样", "04_详图"]:
    for p in sorted((ROOT / "02_施工图" / sub).glob("*_v2.dxf")):
        m = re.search(r"_(PL|EL|DT|SD)-(\d{2})_v2\.dxf$", p.name)
        code = "%s-%s" % (m.group(1), m.group(2)) if m else p.stem
        sheets.append((code, sub, p))

rows = []
for code, sub, p in sheets:
    doc = ezdxf.readfile(p)
    msp = doc.modelspace()
    used = collections.Counter(e.dxf.layer for e in msp)
    types_by_layer = collections.defaultdict(collections.Counter)
    for e in msp:
        types_by_layer[e.dxf.layer][e.dxftype()] += 1
    layers = {x.dxf.name: x for x in doc.layers}
    missing = sorted(set(ref) - set(layers))
    extra = sorted(set(layers) - set(ref))
    propdiff = []
    for name in sorted(set(ref) & set(layers)):
        lay = layers[name]
        d = lay.dxf
        cur = {
            "color": d.get("color", 7),
            "linetype": d.get("linetype", "Continuous"),
            "lineweight": d.get("lineweight", -3),
            "on": lay.is_on(),
            "frozen": lay.is_frozen(),
            "locked": lay.is_locked(),
            "plot": d.get("plot", 1),
        }
        diffs = {k: {"reference": ref[name][k], "actual": cur[k]} for k in ref[name] if ref[name][k] != cur[k]}
        if diffs:
            propdiff.append({"layer": name, "diffs": diffs})
    row = {
        "code": code,
        "sub": sub,
        "file": str(p),
        "layer_count": len(layers),
        "reference_count": len(ref),
        "missing": missing,
        "extra": extra,
        "property_diffs": propdiff,
        "used_layers": dict(sorted(used.items())),
        "entity_types_by_layer": {k: dict(sorted(v.items())) for k, v in sorted(types_by_layer.items())},
        "exact_match": not missing and not extra and not propdiff,
    }
    rows.append(row)
    print("%-6s layers=%-3d missing=%-24s extra=%-18s propdiff=%-3d exact=%s" % (
        code, len(layers), ",".join(missing) or "-", ",".join(extra) or "-", len(propdiff), row["exact_match"]))

summary = {
    "reference": str(REF),
    "reference_layers": ref,
    "sheet_count": len(rows),
    "exact_count": sum(r["exact_match"] for r in rows),
    "rows": rows,
}
(OUT / "v33_layer_audit.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nSUMMARY %d/%d exact; JSON=%s" % (summary["exact_count"], len(rows), OUT / "v33_layer_audit.json"))
