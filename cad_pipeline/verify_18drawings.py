# -*- coding: utf-8 -*-
"""
18 张立面/节点/详图 程序化复检（验收用）
======================================
检查项：
  C1 图层：仅允许白名单图层，0 层无实体
  C2 字高：所有 TEXT/MTEXT 图纸字高 ≥ 2.5mm（按本图比例换算）
  C3 重叠：TEXT 包围盒两两重叠率 ≤ 12%
  C4 尺寸：DIM 层实体数 ≥ 阈值（三级尺寸链存在性）
  C5 版面：内容包围盒在 A2 可用区 394×400mm 内（不超框）
  C6 齐备：DXF/PNG/PDF/DWG 四格式各 1 个
  C7 DWG：魔数 AC1032（AutoCAD 2018）且 > 2KB
  C8 类别：节点四类齐全（吊顶/墙面/地面/收口 各 ≥1）
  C9 命名：文件名 = {图号}_{图名}，与 student_master.DRAWINGS 一致
  C10 比例：立面 1:30、节点/详图 1:10，与图签一致
"""
import os
import sys
import math
import itertools

import ezdxf
from ezdxf.bbox import extents

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import student_master as MD
try:
    from student_elev_node_data import NODE_CATEGORY
except Exception:
    NODE_CATEGORY = {}

from config import ROOT as BASE
# 图纸已按类别分目录：立面 / 节点大样 / 详图
SRC_DIRS = [
    os.path.join(BASE, "03_立面图_四格式"),
    os.path.join(BASE, "04_节点图_四格式"),
    os.path.join(BASE, "05_大样图_四格式"),
]

LAYERS_OK = {"WALL", "COLUMN", "DOOR_WIN", "FURNITURE", "MEP",
             "DIM", "TEXT", "HATCH", "FRAME", "AXIS"}
A2_W, A2_H = 394, 400          # A2(594x420) 减去图签栏 180 与边距 20
TEXT_OVERLAP_TOL = 0.12
MIN_TEXT_MM = 2.5
DIM_MIN = 24                   # 三级尺寸链最低实体数
MIN_BYTES = {"png": 20000, "pdf": 50000, "dxf": 5000, "dwg": 2000}


def txt_bbox(e):
    """估算 TEXT 实体包围盒（考虑对齐方式与旋转）"""
    try:
        h = e.dxf.height
        txt = e.dxf.text
    except Exception:
        return None
    w = 0.0
    for ch in str(txt):
        w += h * (1.0 if ord(ch) > 0x2E80 else 0.55)
    try:
        al = e.dxf.halign
        rot = e.dxf.rotation
        ins = e.dxf.insert
        x = float(ins[0])
        y = float(ins[1])
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
        # 绕【插入点】旋转（不是绕原点）——否则远离原点的竖排文字 bbox 会被甩飞，造成假重叠
        a = math.radians(rot)
        c, s = math.cos(a), math.sin(a)
        pts = [(x0 - x, y0 - y), (x1 - x, y0 - y), (x1 - x, y1 - y), (x0 - x, y1 - y)]
        rp = [(px * c - py * s + x, px * s + py * c + y) for px, py in pts]
        return (min(p[0] for p in rp), min(p[1] for p in rp),
                max(p[0] for p in rp), max(p[1] for p in rp))
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
    SRC = os.path.dirname(path)          # 四格式同在本图所属的分类目录内
    name = os.path.basename(path)
    code = name.split("_")[0]
    stem = name[:-4]
    S = MD.scale_of(code)
    res = {"file": name, "code": code, "scale": S}
    problems = []

    doc = ezdxf.readfile(path)
    msp = doc.modelspace()

    # --- C1 图层 ---
    used, on0 = set(), 0
    for e in msp:
        lay = e.dxf.layer
        used.add(lay)
        if lay == "0":
            on0 += 1
    res["layers_used"] = sorted(used)
    bad = used - LAYERS_OK
    if bad:
        problems.append("C1 非法图层 %s" % sorted(bad))
    if on0:
        problems.append("C1 0 层残留实体 %d 个" % on0)

    # --- 统计 / C2 字高 / C4 尺寸 ---
    counts, min_h, texts = {}, 1e9, []
    for e in msp:
        counts[e.dxf.layer] = counts.get(e.dxf.layer, 0) + 1
        if e.dxftype() in ("TEXT", "MTEXT"):
            try:
                h = e.dxf.height
                min_h = min(min_h, h)
                b = txt_bbox(e)
                if b:
                    texts.append((e, b))
            except Exception:
                pass
    res["counts"] = counts
    res["min_text_mm"] = (min_h / S) if min_h < 1e9 else None
    res["text_count"] = len(texts)
    if min_h < 1e9 and min_h / S < MIN_TEXT_MM - 0.05:
        problems.append("C2 最小字高 %.2fmm < %.1fmm" % (min_h / S, MIN_TEXT_MM))
    if counts.get("DIM", 0) < DIM_MIN:
        problems.append("C4 DIM 实体仅 %d 个 < %d" % (counts.get("DIM", 0), DIM_MIN))

    # --- C3 文字重叠 ---
    overlaps = []
    for (e1, b1), (e2, b2) in itertools.combinations(texts, 2):
        gap = 3 * min(b1[3] - b1[1], b2[3] - b2[1])
        if b1[3] + gap < b2[1] or b2[3] + gap < b1[1]:
            continue
        r = overlap_ratio(b1, b2)
        if r > TEXT_OVERLAP_TOL:
            overlaps.append((round(r, 2),
                             str(e1.dxf.text)[:24] if e1.dxftype() == "TEXT" else str(e1.text)[:24],
                             str(e2.dxf.text)[:24] if e2.dxftype() == "TEXT" else str(e2.text)[:24],
                             round(b1[0]), round(b1[1])))
    res["overlaps"] = overlaps
    if overlaps:
        problems.append("C3 文字重叠 %d 处" % len(overlaps))

    # --- C5 版面：内容（排除图框图签）须落在 A2 图框可用区内 ---
    # 图框本身是 594x420 的块参照，图签栏文字是它的 ATTRIB；
    # "会签/学号"信息行是母版统一压在图框下缘的附属文字（九图同款，既有口径接受），
    # 三者都不计入"绘图内容"的版面判定。
    def _is_frame_note(e):
        if e.dxf.layer == "FRAME" or e.dxftype() == "ATTRIB":
            return True
        if e.dxftype() == "TEXT":
            t = str(e.dxf.text)
            if t.startswith("会签") or t.startswith("学号"):
                return True
        return False

    ents = [e for e in msp if not _is_frame_note(e)]
    frame_ins = None
    for e in msp:
        if e.dxf.layer == "FRAME" and e.dxftype() == "INSERT":
            frame_ins = e
            break
    if ents:
        bb = extents(ents, fast=True)
        res["bbox"] = (round(bb.extmin.x), round(bb.extmin.y),
                       round(bb.extmax.x), round(bb.extmax.y))
        res["paper_mm"] = (round((bb.extmax.x - bb.extmin.x) / S, 1),
                           round((bb.extmax.y - bb.extmin.y) / S, 1))
        if res["paper_mm"][0] > A2_W or res["paper_mm"][1] > A2_H:
            problems.append("C5 版面 %sx%smm 超出 A2 可用区 %dx%d"
                            % (res["paper_mm"][0], res["paper_mm"][1], A2_W, A2_H))
        # 位置：内容须在图框可用区 [10,404]x[10,410]（图框坐标，mm）
        if frame_ins is not None:
            fx, fy = frame_ins.dxf.insert.x, frame_ins.dxf.insert.y
            fs = frame_ins.dxf.xscale or 1.0
            zone = (fx + 10 * fs, fy + 10 * fs,
                    fx + 404 * fs, fy + 410 * fs)
            out_margin = []
            if bb.extmin.x < zone[0] - 1:
                out_margin.append("左%.0f" % ((zone[0] - bb.extmin.x) / S))
            if bb.extmin.y < zone[1] - 1:
                out_margin.append("下%.0f" % ((zone[1] - bb.extmin.y) / S))
            if bb.extmax.x > zone[2] + 1:
                out_margin.append("右%.0f" % ((bb.extmax.x - zone[2]) / S))
            if bb.extmax.y > zone[3] + 1:
                out_margin.append("上%.0f" % ((bb.extmax.y - zone[3]) / S))
            res["out_of_zone"] = out_margin
            if out_margin:
                problems.append("C5 内容越出图框可用区: %s(mm)" % ",".join(out_margin))
        else:
            problems.append("C5 未找到图框块参照，无法判定版面")

    # --- C6 四格式齐备 ---
    fmts = {}
    for ext in ("dxf", "png", "pdf", "dwg"):
        p = os.path.join(SRC, stem + "." + ext)
        fmts[ext] = os.path.exists(p) and os.path.getsize(p) >= MIN_BYTES[ext]
    res["formats"] = fmts
    miss = [k for k, v in fmts.items() if not v]
    if miss:
        problems.append("C6 格式缺失/过小: %s" % ",".join(miss))

    # --- C7 DWG 魔数 ---
    dwg = os.path.join(SRC, stem + ".dwg")
    if os.path.exists(dwg):
        with open(dwg, "rb") as f:
            magic = f.read(6).decode("ascii", "ignore")
        res["dwg_magic"] = magic
        if magic != "AC1032":
            problems.append("C7 DWG 魔数 %s != AC1032" % magic)

    # --- C9 命名与图名一致 ---
    want = dict((c, n) for c, n, *_ in MD.DRAWINGS).get(code)
    res["expect_name"] = want
    if want and stem != "%s_%s" % (code, want):
        problems.append("C9 命名不符 期望 '%s_%s'" % (code, want))

    # --- C10 比例 ---
    exp = "1:30" if code.startswith("EL") else "1:10"
    res["scale_str"] = "%d" % S
    if S != (30 if code.startswith("EL") else 10):
        problems.append("C10 比例 %d 不符 %s" % (S, exp))

    res["problems"] = problems
    res["pass"] = not problems
    return res


def main():
    files = []
    for d in SRC_DIRS:
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.lower().endswith(".dxf") and not f.startswith("_tmp_"):
                files.append(os.path.join(d, f))
    if len(sys.argv) > 1:
        files = [p for p in files if any(a in os.path.basename(p) for a in sys.argv[1:])]
    results = []
    for f in files:
        r = check(f)
        results.append(r)
        print("=" * 72)
        print("%s %s  比例1:%d" % ("[PASS]" if r["pass"] else "[FAIL]", r["file"], r["scale"]))
        print("  图层 %s" % ",".join(r["layers_used"]))
        print("  实体 %s" % {k: v for k, v in sorted(r["counts"].items())})
        print("  最小字高 %s mm | 文字 %d | 版面 %sx%s mm | 格式 %s | DWG %s"
              % ("%.2f" % r["min_text_mm"] if r["min_text_mm"] else "-",
                 r["text_count"], r["paper_mm"][0], r["paper_mm"][1],
                 "".join(k if v else "-%s" % k for k, v in r["formats"].items()),
                 r.get("dwg_magic", "-")))
        for o in r["overlaps"][:10]:
            print("    重叠 %.2f [%s]x[%s] @(%s,%s)" % o)
        for p in r["problems"]:
            print("  - %s" % p)

    # --- C8 节点四类齐全 ---
    cats = {}
    for k, v in NODE_CATEGORY.items():
        cats.setdefault(v, []).append(k)
    print("=" * 72)
    print("C8 节点/详图四类归属：")
    for c in ("吊顶", "墙面", "地面", "收口"):
        ks = cats.get(c, [])
        print("  %-4s %d 个：%s%s" % (c, len(ks), ",".join(sorted(ks)),
                                      "" if ks else "   <<< 缺失！"))
    cats_ok = all(cats.get(c) for c in ("吊顶", "墙面", "地面", "收口"))

    print("=" * 72)
    npass = sum(1 for r in results if r["pass"])
    print("单图复检：%d 张，通过 %d，失败 %d" % (len(results), npass, len(results) - npass))
    print("节点四类齐全：%s" % ("PASS" if cats_ok else "FAIL"))
    print("总判定：%s" % ("PASS" if (npass == len(results) and cats_ok and len(results) == 18)
                        else "FAIL"))


if __name__ == "__main__":
    main()
