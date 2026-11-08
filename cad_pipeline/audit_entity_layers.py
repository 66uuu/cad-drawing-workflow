# -*- coding: utf-8 -*-
"""实体级图层归属审计：按图元类型判定是否放错层。"""
import json
import re
from pathlib import Path
import ezdxf

PIPE = Path(__file__).resolve().parent
ROOT = Path(r"D:/UserFiles/Desktop/V3.3最终版")
OUT = PIPE / "_layer_audit"

# 图元类型 → 期望图层（强约束）
EXPECT = {
    "TEXT": "TEXT",
    "MTEXT": "TEXT",
    "DIMENSION": "DIM",
    "HATCH": "HATCH",
    "ARC": None,  # 门扇弧线看层名
    "INSERT": None,  # 需看块名
}

def classify(doc):
    """返回 (违规列表, 统计)"""
    msp = doc.modelspace()
    issues = []
    type_layer = {}
    for e in msp:
        t = e.dxftype()
        ly = e.dxf.layer
        type_layer.setdefault(t, {})
        type_layer[t][ly] = type_layer[t].get(ly, 0) + 1
        if t == "TEXT" and ly != "TEXT":
            issues.append(("TEXT不在TEXT层", ly, e.dxf.get("text", "")[:20] if e.dxf.hasattr("text") else ""))
        elif t == "MTEXT" and ly != "TEXT":
            issues.append(("MTEXT不在TEXT层", ly, ""))
        elif t == "DIMENSION" and ly != "DIM":
            issues.append(("DIMENSION不在DIM层", ly, ""))
        elif t == "HATCH" and ly != "HATCH":
            issues.append(("HATCH不在HATCH层", ly, ""))
        elif t == "INSERT":
            name = e.dxf.name if e.dxf.hasattr("name") else "?"
            issues.append(("INSERT块", ly, name))
    return issues, type_layer

rows = []
for sub in ["00_图纸目录", "01_平面", "02_立面", "03_节点大样", "04_详图"]:
    for p in sorted((ROOT / "02_施工图" / sub).glob("*_v2.dxf")):
        m = re.search(r"_(PL|EL|DT|SD)-(\d{2})_v2\.dxf$", p.name)
        code = "%s-%s" % (m.group(1), m.group(2)) if m else p.stem
        doc = ezdxf.readfile(p)
        issues, tl = classify(doc)
        rows.append({"code": code, "sub": sub, "issues": issues, "type_layer": tl})

# 汇总打印
for r in rows:
    tls = r["type_layer"]
    text_bad = [i for i in r["issues"] if "TEXT" in i[0] or "MTEXT" in i[0]]
    dim_bad = [i for i in r["issues"] if "DIMENSION" in i[0]]
    hatch_bad = [i for i in r["issues"] if "HATCH" in i[0]]
    inserts = [i for i in r["issues"] if i[0] == "INSERT块"]
    print("== %-6s TEXT错层=%d DIM错层=%d HATCH错层=%d INSERT=%s" % (
        r["code"], len(text_bad), len(dim_bad), len(hatch_bad),
        "; ".join("%s:%s" % (i[2], i[1]) for i in inserts) or "-"))

# 统计全局：每类实体在各层的分布
print("\n===== 实体类型 vs 图层（全34张汇总，只看非预期组合） =====")
from collections import Counter
cnt = Counter()
for r in rows:
    for t, d in r["type_layer"].items():
        for ly, n in d.items():
            cnt[(t, ly)] += n
for (t, ly), n in sorted(cnt.items()):
    flag = ""
    if t in ("TEXT", "MTEXT") and ly != "TEXT":
        flag = "  <<< 应在TEXT"
    elif t == "DIMENSION" and ly != "DIM":
        flag = "  <<< 应在DIM"
    elif t == "HATCH" and ly != "HATCH":
        flag = "  <<< 应在HATCH"
    if flag or t in ("INSERT",):
        print("%-10s %-16s %6d%s" % (t, ly, n, flag))

(OUT / "v33_entity_layer_audit.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("\nJSON", OUT / "v33_entity_layer_audit.json")
