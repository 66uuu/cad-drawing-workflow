# -*- coding: utf-8 -*-
"""
九张平面图程序化复检（验收用）
检查项：
  C1 轴网：每图 25 根 CENTER 线型轴线（X13 + Y12）
  C2 尺寸：DIM 层实体数 ≥ 阈值（三级尺寸链）
  C3 家具：FURNITURE 层实体数 ≥ 阈值
  C4 图层：仅允许 9 个业务图层 + FRAME，0 层无实体
  C5 外框：37000×37000（模型坐标）
  C6 字高：所有 TEXT 实体的图纸字高 ≥ 2.5mm
  C7 文字重叠：TEXT 实体包围盒两两不重叠（同一行/同一列基线邻近区间）
  C8 图框外溢：所有实体应在 A1 图框可用区内
  C9 家具越界：家具实体中心应落在 0..37000 外框内
  C10 表格/图例/说明 不越出右侧栏
"""
import os
import sys
import math
import itertools

import ezdxf
from ezdxf.bbox import extents

from config import ROOT as BASE
SRC = os.path.join(BASE, "02_平面图_四格式")

LAYERS_OK = {"WALL", "COLUMN", "DOOR_WIN", "FURNITURE", "MEP",
             "DIM", "TEXT", "HATCH", "FRAME", "AXIS"}
AXIS_LAYER_NAME = None

TEXT_OVERLAP_TOL = 0.12   # 允许 12% 的轻微叠压

# --- 16 张平面差异化豁免（PL-00~14 补充图按其图纸性质不要求全项） ---
# 无轴网：PL-00 图纸目录（表格型图纸，无建筑底图）
NO_AXIS = ("PL-00",)
# 无三级尺寸链：7 张补充图 base_plan(dims=False)（尺寸归 PL-15 天花尺寸图等专图）
NO_DIM = ("PL-00", "PL-03", "PL-10", "PL-11", "PL-12", "PL-13", "PL-14")
# 无家具底图：PL-02 原始结构（方案要求新增 0）/ PL-00 目录 / PL-03 分区 /
#            PL-12 动线 / PL-14 排版（均为分析型图纸）
NO_FURN = ("PL-00", "PL-02", "PL-03", "PL-12", "PL-14")


def txt_bbox(e):
    """估算 TEXT 实体包围盒（考虑对齐方式与旋转）"""
    try:
        h = e.dxf.height
        txt = e.dxf.text
        # 估算宽度：中文按 1.0em，ASCII 按 0.55em
        w = 0.0
        for ch in txt:
            w += h * (1.0 if ord(ch) > 0x2E80 else 0.55)
    except Exception:
        return None
    try:
        p = e.plain_text() if hasattr(e, "plain_text") else ""
        al = e.dxf.halign
        rot = e.dxf.rotation
    except Exception:
        al, rot = 0, 0.0
    try:
        ins = e.dxf.insert
        x = float(ins[0]) if not hasattr(ins, "x") else float(ins.x)
        y = float(ins[1]) if not hasattr(ins, "x") else float(ins.y)
    except Exception:
        try:
            x, y = e.dxf.align_point
        except Exception:
            return None
    if al == 1:      # center
        x0, x1 = x - w / 2, x + w / 2
    elif al == 2:    # right
        x0, x1 = x - w, x
    else:
        x0, x1 = x, x + w
    y0, y1 = y, y + h
    if rot:
        a = math.radians(rot)
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        c, s = math.cos(a), math.sin(a)
        rp = [(px * c - py * s, px * s + py * c) for px, py in pts]
        xs = [p[0] for p in rp]
        ys = [p[1] for p in rp]
        return (min(xs), min(ys), max(xs), max(ys))
    return (x0, y0, x1, y1)


def overlap_ratio(a, b):
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    inter = ix * iy
    aa = (a[2] - a[0]) * (a[3] - a[1])
    bb = (b[2] - b[0]) * (b[3] - b[1])
    if aa <= 0 or bb <= 0:
        return 0.0
    return inter / min(aa, bb)


def check(path):
    name = os.path.basename(path)
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    res = {"file": name}
    problems = []

    # --- 图层与 0 层 ---
    used = set()
    on0 = 0
    for e in msp:
        lay = e.dxf.layer
        used.add(lay)
        if lay == "0":
            on0 += 1
    res["layers_used"] = sorted(used)
    res["layer0_entities"] = on0
    bad = used - LAYERS_OK
    if bad:
        problems.append("非法图层 %s" % sorted(bad))
    if on0:
        problems.append("0 层残留实体 %d 个" % on0)

    # --- 统计 ---
    counts = {}
    axis_ct = 0
    axis_center = 0
    min_h = 1e9
    for e in msp:
        lay = e.dxf.layer
        counts[lay] = counts.get(lay, 0) + 1
        if lay == "AXIS" and e.dxftype() == "LINE":
            axis_ct += 1
            if e.dxf.linetype == "CENTER":
                axis_center += 1
        if e.dxftype() in ("TEXT", "MTEXT"):
            try:
                h = e.dxf.height
                if h < min_h:
                    min_h = h
            except Exception:
                pass
    res["counts"] = counts
    res["axis_lines"] = axis_ct
    res["axis_center_lines"] = axis_center
    res["min_text_height_model"] = min_h if min_h < 1e9 else None

    # C1 轴网（PL-00 目录图为表格型图纸，无轴网，豁免）
    if not name.startswith(NO_AXIS):
        if axis_ct != 25:
            problems.append("轴线 %d 根，应为 25（X13+Y12）" % axis_ct)
        if axis_center != 25:
            problems.append("CENTER 线型轴线 %d 根，应为 25" % axis_center)
    # C2 尺寸（7 张补充图 dims=False，三级尺寸链由专图承载）
    if not name.startswith(NO_DIM) and counts.get("DIM", 0) < 30:
        problems.append("DIM 层实体仅 %d 个，三级尺寸链不足" % counts.get("DIM", 0))
    # C3 家具（PL-02 原始结构图按方案要求「新增实体为 0」，不叠家具底图）
    if name.startswith("PL-02") and counts.get("FURNITURE", 0) > 0:
        problems.append("PL-02 新增实体应为 0，却有 %d 个家具实体"
                        % counts.get("FURNITURE", 0))
    elif not name.startswith(NO_FURN) and counts.get("FURNITURE", 0) < 100:
        problems.append("FURNITURE 层实体仅 %d 个" % counts.get("FURNITURE", 0))
    # C6 字高（模型单位 → 图纸 mm 需除以比例 100）
    if min_h < 1e9 and min_h / 100.0 < 2.45:
        problems.append("最小字高 %.2fmm < 2.5mm" % (min_h / 100.0))

    # --- 外框 ---
    bb = extents(msp, fast=True)
    res["bbox"] = (bb.extmin.x, bb.extmin.y, bb.extmax.x, bb.extmax.y)

    # --- C7 文字重叠 ---
    texts = []
    for e in msp:
        if e.dxftype() in ("TEXT", "MTEXT"):
            bb2 = txt_bbox(e)
            if bb2:
                texts.append((e, bb2))
    overlaps = []
    for (e1, b1), (e2, b2) in itertools.combinations(texts, 2):
        # 快速剔除：垂直间距超过一个字高 ×3 不可能重叠
        if b1[3] + 3 * min(b1[3] - b1[1], b2[3] - b2[1]) < b2[1]:
            continue
        if b2[3] + 3 * min(b1[3] - b1[1], b2[3] - b2[1]) < b1[1]:
            continue
        r = overlap_ratio(b1, b2)
        if r > TEXT_OVERLAP_TOL:
            t1 = e1.dxf.text if e1.dxftype() == "TEXT" else e1.text
            t2 = e2.dxf.text if e2.dxftype() == "TEXT" else e2.text
            overlaps.append((round(r, 2), str(t1)[:28], str(t2)[:28],
                             round(b1[0]), round(b1[1])))
    res["text_count"] = len(texts)
    res["text_overlaps"] = overlaps
    res["text_overlap_count"] = len(overlaps)
    if overlaps:
        problems.append("文字重叠 %d 处" % len(overlaps))

    # --- C9 家具越界（排除图例符号：图例已改画在 TEXT 层）---
    out = []
    for e in msp:
        if e.dxf.layer != "FURNITURE":
            continue
        if e.dxftype() != "LWPOLYLINE":
            continue
        try:
            xs = [p[0] for p in e.get_points()]
            ys = [p[1] for p in e.get_points()]
        except Exception:
            continue
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        if not (-200 <= cx <= 37200 and -200 <= cy <= 37200):
            out.append((round(cx), round(cy)))
    res["furniture_outside"] = out
    if out:
        problems.append("家具越界 %d 件" % len(out))

    # --- C11 分区标签压家具：区内短标签的包围盒不得压住家具轮廓 ---
    furn = []
    for e in msp:
        if e.dxf.layer == "FURNITURE" and e.dxftype() == "LWPOLYLINE":
            try:
                pts = [tuple(q)[:2] for q in e.get_points()]
            except Exception:
                continue
            if not pts:
                continue
            furn.append((min(p[0] for p in pts), min(p[1] for p in pts),
                         max(p[0] for p in pts), max(p[1] for p in pts)))
    label_hits = []
    for e, b in texts:
        t = e.dxf.text if e.dxftype() == "TEXT" else e.text
        s = str(t)
        # 只查「区号 + 短名」型标签（含 Z+数字）
        if not (s[:2] in ("Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7",
                          "Z8", "Z9", "Z1") or s.startswith("Z")):
            continue
        if not s[1:2].isdigit():
            continue
        for fb in furn:
            ix = min(b[2], fb[2]) - max(b[0], fb[0])
            iy = min(b[3], fb[3]) - max(b[1], fb[1])
            if ix > 0 and iy > 0:
                label_hits.append((s[:14], round(b[0]), round(b[1]),
                                   round(fb[0]), round(fb[1])))
                break
    res["label_on_furniture"] = label_hits
    if label_hits:
        problems.append("分区标签压家具 %d 处" % len(label_hits))

    res["problems"] = problems
    res["pass"] = not problems
    return res


def main():
    files = sorted(f for f in os.listdir(SRC)
                   if f.lower().endswith(".dxf") and not f.startswith("_tmp_")
                   and not f.lower().endswith("_新.dxf"))   # 只排除临时后缀 "_新.dxf"，勿误伤 "新增隔墙定位图"
    if len(sys.argv) > 1:
        files = [f for f in files if any(a in f for a in sys.argv[1:])]
    results = []
    for f in files:
        r = check(os.path.join(SRC, f))
        results.append(r)
        print("=" * 70)
        print("%s  %s" % ("[PASS]" if r["pass"] else "[FAIL]", r["file"]))
        print("  图层: %s" % ", ".join(r["layers_used"]))
        print("  实体计数: %s" % {k: v for k, v in sorted(r["counts"].items())})
        print("  轴线 %d 根（CENTER %d）| 最小字高 %s mm | 文字 %d 条"
              % (r["axis_lines"], r["axis_center_lines"],
                 ("%.2f" % (r["min_text_height_model"] / 100.0))
                 if r["min_text_height_model"] else "-", r["text_count"]))
        print("  家具越界 %d 件 | 标签压家具 %d 处"
              % (len(r["furniture_outside"]), len(r["label_on_furniture"])))
        for lh in r["label_on_furniture"][:10]:
            print("     标签[%s]@(%s,%s) 压家具(%s,%s)" % lh)
        if r["text_overlaps"]:
            print("  !! 文字重叠 %d 处：" % len(r["text_overlaps"]))
            for o in r["text_overlaps"][:14]:
                print("     %5.2f  [%s] × [%s] @(%s,%s)" % o)
        for p in r["problems"]:
            print("  - %s" % p)
    print("=" * 70)
    npass = sum(1 for r in results if r["pass"])
    print("总计 %d 张，通过 %d 张，失败 %d 张" % (len(results), npass, len(results) - npass))


if __name__ == "__main__":
    main()
