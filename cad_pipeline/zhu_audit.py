# -*- coding: utf-8 -*-
"""
朱文件夹 DXF 全面审计
=====================
对每个 DXF 输出：
  1. 图层清单（名/颜色/线宽/线型/冻结）
  2. 每图层实体类型计数
  3. 文字样式清单 + 字高分布
  4. 标注实体计数
  5. 疑似轴网线（长直线，在 X/Y 整数坐标附近）
  6. 插入块（INSERT）清单
"""
import json, math
from pathlib import Path
from collections import Counter, defaultdict
import ezdxf
from ezdxf.enums import TextEntityAlignment

DXF_DIR = Path(__file__).resolve().parent / "_zhu_audit" / "dxf"
OUT = Path(__file__).resolve().parent / "_zhu_audit" / "audit_report.json"

def audit_dxf(path):
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    result = {"file": path.name}

    # 1. 图层
    layers = []
    for layer in doc.layers:
        layers.append({
            "name": layer.dxf.name,
            "color": layer.dxf.color,
            "lineweight": getattr(layer.dxf, "lineweight", -3),
            "ltype": layer.dxf.linetype,
            "locked": layer.is_locked,
            "frozen": layer.is_frozen,
        })
    result["layers"] = layers

    # 2. 实体类型 × 图层 计数
    type_layer = defaultdict(Counter)
    entity_count = Counter()
    for e in msp:
        t = e.dxftype()
        ly = e.dxf.layer
        type_layer[ly][t] += 1
        entity_count[t] += 1
    result["entity_total"] = dict(entity_count)
    result["layer_entities"] = {ly: dict(cnt) for ly, cnt in type_layer.items()}

    # 3. 文字样式
    styles = []
    for s in doc.styles:
        styles.append({
            "name": s.dxf.name,
            "font": s.dxf.font,
            "bigfont": getattr(s.dxf, "bigfont", ""),
        })
    result["text_styles"] = styles

    # 4. 文字高度分布
    heights = []
    for e in msp:
        if e.dxftype() == "TEXT":
            heights.append(round(e.dxf.height, 1))
        elif e.dxftype() == "MTEXT":
            heights.append(round(e.dxf.char_height, 1))
    result["text_height_dist"] = dict(Counter(heights).most_common(15))

    # 5. 标注
    dim_count = entity_count.get("DIMENSION", 0)
    result["dim_count"] = dim_count

    # 6. INSERT 块清单
    blocks = Counter()
    for e in msp:
        if e.dxftype() == "INSERT":
            blocks[e.dxf.name] += 1
    result["insert_blocks"] = dict(blocks.most_common(30))

    # 7. 图元包围盒（判断轴网范围）
    try:
        ext = msp.wcs_extymin if hasattr(msp, 'wcs_extymin') else None
        # 用 ezdxf 的 bbox
        from ezdxf import bbox
        cache = bbox.Cache()
        ext = bbox.extents(msp, cache=cache)
        result["bbox"] = {
            "xmin": round(ext.extmin.x, 0), "ymin": round(ext.extmin.y, 0),
            "xmax": round(ext.extmax.x, 0), "ymax": round(ext.extmax.y, 0),
            "w": round(ext.extmax.x - ext.extmin.x, 0),
            "h": round(ext.extmax.y - ext.extmin.y, 0),
        }
    except Exception as ex:
        result["bbox_error"] = str(ex)

    return result

reports = []
for p in sorted(DXF_DIR.glob("*.dxf")):
    print("审计:", p.name)
    try:
        r = audit_dxf(p)
        reports.append(r)
    except Exception as e:
        reports.append({"file": p.name, "error": str(e)})

OUT.write_text(json.dumps(reports, ensure_ascii=False, indent=1), encoding="utf-8")
print("\n=== 汇总 ===")
print("报告:", OUT)
for r in reports:
    if "error" in r:
        print("ERR %s: %s" % (r["file"], r["error"]))
        continue
    bbox = r.get("bbox", {})
    print("%-40s 图层=%2d 实体=%5d 文字=%4d 标注=%3d 块=%2d bbox=%s" % (
        r["file"], len(r["layers"]), sum(r["entity_total"].values()),
        r["entity_total"].get("TEXT",0)+r["entity_total"].get("MTEXT",0),
        r["dim_count"], len(r["insert_blocks"]),
        "%.0fx%.0f" % (bbox.get("w",0), bbox.get("h",0)) if bbox else "?"
    ))
