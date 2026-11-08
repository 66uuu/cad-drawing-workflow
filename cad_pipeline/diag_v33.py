# -*- coding: utf-8 -*-
"""
diag_v33.py — V3.3 原版 34 张 vs 工作流优化版 34 张 同尺对比体检
指标：实体总数 / 图层数 / DIM 尺寸实体 / TEXT 数与最小字高 / HATCH 数 /
     LINE 直线占比（线条堆砌指标）/ LWPOLYLINE 结构化轮廓数 /
     文字重叠对数 / 图签姓名学号
"""
import os
import re
import itertools
import math
import ezdxf

V33 = r"你的桌面\V3.3最终版\02_施工图"
V34 = r"你的桌面\CAD出图工作流\cad_pipeline"

V33_DIRS = {
    "PL": os.path.join(V33, "01_平面"),
    "PL-00": os.path.join(V33, "00_图纸目录"),
    "EL": os.path.join(V33, "02_立面"),
    "DT": os.path.join(V33, "03_节点大样"),
    "SD": os.path.join(V34, "05_大样图_四格式"),  # placeholder, fix below
}
V33_DIRS["SD"] = os.path.join(V33, "04_详图")

V34_DIRS = {
    "PL": os.path.join(V34, "02_平面图_四格式"),
    "EL": os.path.join(V34, "03_立面图_四格式"),
    "DT": os.path.join(V34, "04_节点图_四格式"),
    "SD": os.path.join(V34, "05_大样图_四格式"),
}


def txt_bbox(e):
    try:
        h = e.dxf.height
        txt = e.dxf.text
        w = sum(h * (1.0 if ord(c) > 0x2E80 else 0.55) for c in txt)
    except Exception:
        return None
    try:
        al = e.dxf.halign
        rot = e.dxf.rotation
        ins = e.dxf.insert
        x, y = float(ins[0]), float(ins[1])
    except Exception:
        return None
    if al == 1:
        x0, x1 = x - w / 2, x + w / 2
    elif al == 2:
        x0, x1 = x - w, x
    else:
        x0, x1 = x, x + w
    y0, y1 = y, y + h
    if rot:
        a = math.radians(rot)
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        c, s = math.cos(a), math.sin(a)
        rp = [(px * c - py * s, px * s + py * c) for px, py in pts]
        return (min(p[0] for p in rp), min(p[1] for p in rp),
                max(p[0] for p in rp), max(p[1] for p in rp))
    return (x0, y0, x1, y1)


def scan(path):
    try:
        doc = ezdxf.readfile(path)
    except Exception as e:
        return {"file": os.path.basename(path), "err": str(e)[:60]}
    msp = doc.modelspace()
    n = {"LINE": 0, "LWPOLYLINE": 0, "DIMENSION": 0, "HATCH": 0,
         "TEXT": 0, "MTEXT": 0, "INSERT": 0, "CIRCLE": 0, "ARC": 0,
         "SOLID": 0, "ELLIPSE": 0}
    layers = set()
    min_h = None
    title_hits = set()
    texts = []
    for e in msp:
        t = e.dxftype()
        n[t] = n.get(t, 0) + 1
        layers.add(e.dxf.layer)
        if t in ("TEXT", "MTEXT"):
            try:
                h = e.dxf.height
                min_h = h if min_h is None else min(min_h, h)
                s = e.dxf.text if t == "TEXT" else e.plain_text()
                s = str(s)
                for key in ("蔡志成", "2402060131", "刘涛溢", "2402060428"):
                    if key in s:
                        title_hits.add(key)
                if len(s) > 1:
                    bb = txt_bbox(e) if t == "TEXT" else None
                    if bb:
                        texts.append(bb)
            except Exception:
                pass
    # 文字重叠对（TEXT 估算，MTEXT 跳过）
    ov = 0
    for a, b in itertools.combinations(texts, 2):
        ix = min(a[2], b[2]) - max(a[0], b[0])
        iy = min(a[3], b[3]) - max(a[1], b[1])
        if ix > 0 and iy > 0:
            ov += 1
    total = sum(v for k, v in n.items())
    lines = n["LINE"] + n.get("SOLID", 0)
    dim = n["DIMENSION"] + sum(
        1 for e in msp if e.dxf.layer == "DIM")
    return {
        "file": os.path.basename(path),
        "total": total,
        "layers": len(layers),
        "dim": dim,
        "text": n["TEXT"] + n["MTEXT"],
        "min_h_mm": round(min_h, 1) if min_h else None,
        "hatch": n["HATCH"],
        "poly": n["LWPOLYLINE"],
        "line_solid": lines,
        "overlap": ov,
        "sig": "蔡志成" if "蔡志成" in title_hits else
               ("刘涛溢" if "刘涛溢" in title_hits else "无"),
    }


def collect(dirs, kinds):
    rows = []
    for kind, d in dirs.items():
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith(".dxf"):
                continue
            code = None
            m = re.search(r"(PL-\d+|EL-\d+|DT-\d+|SD-\d+)", f)
            if m:
                code = m.group(1)
            elif kind == "PL-00":
                code = "PL-00"
            if not code or code.split("-")[0] not in kinds:
                continue
            r = scan(os.path.join(d, f))
            r["code"] = code
            rows.append(r)
    return rows


old = collect(V33_DIRS, {"PL", "EL", "DT", "SD"})
new = collect(V34_DIRS, {"PL", "EL", "DT", "SD"})
old.sort(key=lambda r: r["code"])
new.sort(key=lambda r: r["code"])

import json
out = {"old": old, "new": new}
dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_diag_v33_vs_v34.json")
with open(dst, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("原版 %d 张，优化版 %d 张 → %s" % (len(old), len(new), dst))
for r in old:
    print("旧 %(code)s total=%(total)s dim=%(dim)s hatch=%(hatch)s poly=%(poly)s line+solid=%(line_solid)s ov=%(overlap)s sig=%(sig)s" % r)
print("---")
for r in new:
    print("新 %(code)s total=%(total)s dim=%(dim)s hatch=%(hatch)s poly=%(poly)s line+solid=%(line_solid)s ov=%(overlap)s sig=%(sig)s" % r)
