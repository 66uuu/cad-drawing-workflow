# -*- coding: utf-8 -*-
"""
同学版 · 立面图 7 张（EL-01~07）/ 节点大样 6 张（DT-01~06）/ 详图 5 张（SD-01~05）
===============================================================================
口径：student_master.py（单一数据源）+ student_cad.py（图库）+ student_elev_node_data.py（内容）
沿用九张平面图 v2 的同一套逻辑与细节标准：
  · 三级尺寸链（总尺寸 → 轴线/分区 → 门洞/墙厚/家具定位；节点为总尺寸 → 构造层厚 → 细部）
  · 字号放大（图纸字高 ≥ 2.5mm）
  · 文字防重叠：图内只放索引编号 / 标高 / 尺寸数字，材料明细一律移到图外明细表
  · 右侧栏 / 底部栏用纵向游标顺排（RightPanel 同款思路），杜绝硬编码 y 造成压叠
  · HATCH 轮廓渲染，不出实心黑块

用法：
  python build_18drawings_同学版.py            # 全部 18 张
  python build_18drawings_同学版.py EL-01 DT-01  # 指定图号
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ezdxf.bbox import extents

import student_master as MD
import student_cad as cl
import student_elev_node_data as SD

from config import ROOT as BASE

# 【按类别分文件夹】立面 / 节点大样 / 详图 各归各目录，方便直接提交作业
OUT_DIRS = {
    "EL": os.path.join(BASE, "03_立面图_四格式"),
    "DT": os.path.join(BASE, "04_节点图_四格式"),
    "SD": os.path.join(BASE, "05_大样图_四格式"),
}


def out_dir(code):
    d = OUT_DIRS[code[:2]]
    os.makedirs(d, exist_ok=True)
    return d

TXT_H = 3.2           # 图纸字高 mm（≥2.5 硬下限）
TXT_SMALL = 2.8
TXT_BIG = 4.2

# A2 竖栏可用区（纸面 mm）：594-180-20 = 394 宽；420-20 = 400 高
A2_W, A2_H = 394, 400


# ================================================================ 通用底图元
def _band(msp, name, x0, y0, x1, y1, kind, S):
    """按填充类型绘制构造层带。薄层（<8mm）按制图惯例给最小可见厚度 4mm。"""
    if y1 - y0 < 4:
        m = (y0 + y1) / 2
        y0, y1 = m - 2, m + 2
    if x1 - x0 < 4:
        m = (x0 + x1) / 2
        x0, x1 = m - 2, m + 2
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if kind == "solid":
        cl.fill_rect(msp, pts, layer="WALL", color=7)
        cl.rect(msp, x0, y0, x1, y1, layer="WALL", lw=0.25)
    elif kind == "ansi31":
        h = msp.add_hatch(dxfattribs={"layer": "HATCH"})
        h.paths.add_polyline_path(pts, is_closed=True)
        h.set_pattern_fill("ANSI31", scale=4)
        cl.rect(msp, x0, y0, x1, y1, layer="WALL", lw=0.35)
    elif kind == "ansi37":
        h = msp.add_hatch(dxfattribs={"layer": "HATCH"})
        h.paths.add_polyline_path(pts, is_closed=True)
        h.set_pattern_fill("ANSI37", scale=4)
        cl.rect(msp, x0, y0, x1, y1, layer="WALL", lw=0.35)
    elif kind == "dots":
        h = msp.add_hatch(dxfattribs={"layer": "HATCH"})
        h.paths.add_polyline_path(pts, is_closed=True)
        h.set_pattern_fill("DOTS", scale=3)
        cl.rect(msp, x0, y0, x1, y1, layer="WALL", lw=0.18)
    elif kind == "grid":
        cl.rect(msp, x0, y0, x1, y1, layer="DOOR_WIN", lw=0.25)
        step = max((x1 - x0) / 6, (y1 - y0) / 4, 8)
        xx = x0 + step
        while xx < x1 - 2:
            cl.line(msp, (xx, y0), (xx, y1), "DOOR_WIN", lw=0.09)
            xx += step
    elif kind == "glass":
        cl.rect(msp, x0, y0, x1, y1, layer="DOOR_WIN", lw=0.25)
        if x1 - x0 < y1 - y0:      # 竖向玻璃：双线
            m = (x0 + x1) / 2
            cl.line(msp, (m - 2, y0), (m - 2, y1), "DOOR_WIN", lw=0.09)
            cl.line(msp, (m + 2, y0), (m + 2, y1), "DOOR_WIN", lw=0.09)
        else:
            m = (y0 + y1) / 2
            cl.line(msp, (x0, m - 2), (x1, m - 2), "DOOR_WIN", lw=0.09)
            cl.line(msp, (x0, m + 2), (x1, m + 2), "DOOR_WIN", lw=0.09)
    else:                          # none：只画轮廓
        cl.rect(msp, x0, y0, x1, y1, layer="FURNITURE", lw=0.18)


def _wrap(s, n=18):
    """中文按字数硬折行（无标点断词，保证版宽可控）。"""
    out, cur = [], ""
    for ch in s:
        cur += ch
        if len(cur) >= n:
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return out


# ---- 文字防重叠：全局已放文字包围盒（每张图 build 前清空）----
PLACED = []


def _txt_w(txt, h_mm, S):
    """估算文字宽度（模型单位）：中文 1.0em、ASCII 0.55em。"""
    w = 0.0
    for ch in str(txt):
        w += h_mm * (1.0 if ord(ch) > 0x2E80 else 0.55)
    return w * S


def _bbox_of(x, y, txt, h_mm, S, align="L", rot=0):
    w = _txt_w(txt, h_mm, S)
    h = h_mm * S
    if rot:                      # 竖排（rot=90）：沿 +y 排布，字高方向沿 -x
        return (x - h, y, x, y + w)
    if align == "C":
        x0, x1 = x - w / 2, x + w / 2
    elif align == "R":
        x0, x1 = x - w, x
    else:
        x0, x1 = x, x + w
    return (x0, y, x1, y + h)


def _hit(a, b, pad=0.0):
    """a 框外扩 pad 后是否与 b 相交（pad 是"必须留出的间隙"，不是"允许的重叠量"）。"""
    return (min(a[2] + pad, b[2]) - max(a[0] - pad, b[0]) > 0) and \
           (min(a[3] + pad, b[3]) - max(a[1] - pad, b[1]) > 0)


def _fit_text(msp, x, y, txt, h_mm, S, align="L", rot=0, axis=None,
              layer="TEXT", style="HEI", leader=True):
    """放文字并自动避让已放文字（薄构造层密集标注 / 标高密集 的通用解法）。

    axis: 'y' = 冲突时上下错开；'x' = 左右错开；None = 不避让。
    文字被移开后，从原锚点画一条细引出线，保证仍可判读归属。
    """
    h = h_mm * S
    step = 1.6 * h
    pad = 0.25 * h
    bx, by, box = x, y, _bbox_of(x, y, txt, h_mm, S, align, rot)
    if axis:
        offs = [0.0]
        for i in range(1, 13):
            offs += [i * step, -i * step]
        for off in offs:
            dx = off if axis == "x" else 0.0
            dy = off if axis == "y" else 0.0
            cand = _bbox_of(x + dx, y + dy, txt, h_mm, S, align, rot)
            if not any(_hit(cand, o, pad) for o in PLACED):
                bx, by, box = x + dx, y + dy, cand
                break
    cl.text(msp, bx, by, txt, h_mm, S, layer=layer, align=align,
            rotation=rot, style=style)
    PLACED.append(box)
    # 移位后补引出线，读者仍能判读该标注属于哪一段
    if leader and (abs(bx - x) > 0.5 or abs(by - y) > 0.5):
        if rot:
            cl.line(msp, (x, y), (bx - h / 2, by), layer, lw=0.09)
        else:
            cl.line(msp, (x, y), (bx, by + h / 2), layer, lw=0.09)
    return bx, by


def _elev(msp, x, y, lb, S, layer="TEXT"):
    """标高符号（三角）+ 带避让的标高文字。"""
    L = 3.0 * S
    cl.poly(msp, [(x, y), (x + L, y), (x, y - L)], layer=layer, close=True)
    _fit_text(msp, x + L * 1.2, y - L * 0.6, lb, 3.0, S,
              axis="y", layer=layer, style="HEI")


def _tick_h(msp, x, y, S, layer="DIM"):
    L = 2.5 * S
    cl.line(msp, (x - L / 2, y - L / 2), (x + L / 2, y + L / 2), layer)


def _dim_h(msp, x1, x2, y_dim, label, S, layer="DIM"):
    cl.line(msp, (x1, y_dim), (x2, y_dim), layer)
    _tick_h(msp, x1, y_dim, S, layer)
    _tick_h(msp, x2, y_dim, S, layer)
    if label:
        # 水平尺寸链：薄构造层密集时上下错开（制图惯例的错位标注）
        _fit_text(msp, (x1 + x2) / 2, y_dim + 0.5 * 3.0 * S, label, 3.0, S,
                  align="C", axis="y", layer=layer, style="XZC")


def _dim_v(msp, y1, y2, x_dim, label, S, layer="DIM"):
    cl.line(msp, (x_dim, y1), (x_dim, y2), layer)
    _tick_h(msp, x_dim, y1, S, layer)
    _tick_h(msp, x_dim, y2, S, layer)
    if label:
        # 竖直尺寸链：密集时左右错开
        _fit_text(msp, x_dim + 0.5 * 3.0 * S, (y1 + y2) / 2 - 1.2 * S, label, 3.0, S,
                  align="L", rot=90, axis="x", layer=layer, style="XZC")


# ================================================================ 立面图
def gen_elev(msp, code, S):
    PLACED.clear()
    d = SD.ELEV[code]
    W = d["W"]
    CEIL, BEAM = 2850, 3000

    # ---- 1. 立面主体 ----
    for kind, x0, y0, x1, y1, _lab in d["items"]:
        if kind == "wall":
            cl.fill_rect(msp, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                         layer="WALL", color=7)
            cl.rect(msp, x0, y0, x1, y1, layer="WALL", lw=0.50)
        elif kind == "finish":
            cl.rect(msp, x0, y0, x1, y1, layer="HATCH", lw=0.13)
            step = 600
            xx = x0 + step
            while xx < x1 - 60:
                cl.line(msp, (xx, y0), (xx, y1), "HATCH", lw=0.09)
                xx += step
        elif kind == "furn":
            cl.rect(msp, x0, y0, x1, y1, layer="FURNITURE", lw=0.25)
        elif kind == "cab":
            cl.rect(msp, x0, y0, x1, y1, layer="FURNITURE", lw=0.25)
            n = max(1, int((y1 - y0) // 500))
            for i in range(1, n):
                yy = y0 + (y1 - y0) * i / n
                cl.line(msp, (x0, yy), (x1, yy), "FURNITURE", lw=0.09)
        elif kind == "glass":
            cl.rect(msp, x0, y0, x1, y1, layer="DOOR_WIN", lw=0.25)
            xx = x0
            while xx < x1:
                cl.line(msp, (xx, y0), (xx, y1), "DOOR_WIN", lw=0.09)
                xx += 1200
        elif kind == "door":
            cl.rect(msp, x0, y0, x1, y1, layer="DOOR_WIN", lw=0.35)
            cl.line(msp, (x0, y1), (x1, y1), "DOOR_WIN", lw=0.35)
        elif kind == "mep":
            cl.rect(msp, x0, y0, x1, y1, layer="MEP", lw=0.13)
        elif kind == "plant":
            cl.circle(msp, (x0 + x1) / 2, (y0 + y1) * 0.62, min(x1 - x0, y1 - y0) / 2,
                      "FURNITURE")
            cl.rect(msp, (x0 + x1) / 2 - 120, y0, (x0 + x1) / 2 + 120, y0 + 250,
                    layer="FURNITURE", lw=0.13)
        elif kind == "sign":
            cl.rect(msp, x0, y0, x1, y1, layer="TEXT", lw=0.25)

    # ---- 2. 材料索引编号（图内只放编号，明细移到图外表格，杜绝压字）----
    for i, (nm, spec, ax, ay) in enumerate(d["mats"], start=1):
        cl.index_bubble(msp, ax, ay, str(i), S)

    # ---- 3. 三级尺寸链 ----
    # ① 总尺寸
    _dim_h(msp, 0, W, -1250, str(W), S)
    _dim_v(msp, 0, BEAM, -1250, str(BEAM), S)
    # ② 分区/开间尺寸
    for (xa, xb, lb) in d["hsegs"]:
        _dim_h(msp, xa, xb, -620, lb, S)
    # ③ 细部（家具/构造定位）
    hs = sorted({h for h, _ in d["heights"]})
    prev = None
    for h in hs:
        if prev is not None and h - prev > 120:
            _dim_v(msp, prev, h, -620, str(int(h - prev)), S)
        prev = h

    # ---- 4. 图名与索引说明（先占位登记，避免被后续标高/尺寸挤走）----
    y = BEAM + 420
    _fit_text(msp, 0, y, "%s  %s（%s）" % (code, d["zone"], "1:30"), TXT_BIG, S,
              axis=None)
    y -= 320
    _fit_text(msp, 0, y, "本图表达墙段索引见 PL-11 平面索引图；构造做法见对应节点大样/详图。",
              TXT_SMALL, S, axis=None)
    y -= 320
    _fit_text(msp, 0, y, "楼面完成面 ±0.000｜吊顶完成面 +2.850｜梁底 +3.000｜层高 4.500",
              TXT_SMALL, S, axis=None)

    # ---- 5. 标高（图内右侧，避开尺寸链；密集时自动上下错开）----
    mx = W - 260
    for (h, lb) in d["heights"]:
        cl.line(msp, (mx - 60, h), (mx + 60, h), "DIM", lw=0.09)
        _elev(msp, mx, h, lb, S)

    # ---- 6. 材料做法表（图外明细，纵向游标顺排）----
    y = -1750
    rows = [["编号", "材料 / 部位", "规格", "燃烧等级"]]
    for i, (nm, spec, _ax, _ay) in enumerate(d["mats"], start=1):
        rows.append([str(i), nm, spec, "A / B1（见材料表）"])
    ybot = cl.table(msp, 0, y, [12, 62, 100, 40], rows, S, rh=8.5, fs=2.8)
    # ---- 7. 施工要点 ----
    y = ybot - 420
    cl.text(msp, 0, y, "施工要点：", TXT_H, S)
    y -= 380
    for t in d["notes"]:
        cl.text(msp, 0, y, "· " + t, TXT_SMALL, S)
        y -= 340
    return y


# ================================================================ 节点大样 / 详图
def gen_section(msp, code, S):
    PLACED.clear()
    d = SD.SECTION[code]
    W, H = d["W"], d["H"]
    node = MD.NODES[code]

    # ---- 1. 构造层带 ----
    for (nm, x0, y0, x1, y1, kind) in d["bands"]:
        _band(msp, nm, x0, y0, x1, y1, kind, S)

    # ---- 2. 引出标注（自动顺排，杜绝压字）----
    # 按锚点 y 从高到低排序，目标点自上而下均匀分配 → 引出线不交叉
    # 锚点 = (构造层右边缘 x1, 层中高 y)，按 y 从高到低排序
    anchors = sorted([(b[3], (b[2] + b[4]) / 2) for b in d["bands"]],
                     key=lambda p: -p[1])
    XA = W + 520
    top, bot = H - 60, 60
    n = max(1, len(anchors) - 1)
    for i, (ax, ay) in enumerate(anchors):
        ty = top + (bot - top) * i / n
        cl.line(msp, (ax, ay), (XA, ty), "TEXT", lw=0.09)
        cl.line(msp, (XA, ty), (XA + 70, ty), "TEXT", lw=0.09)
        nm = ""
        for b in d["bands"]:
            if abs(b[3] - ax) < 0.6 and abs((b[2] + b[4]) / 2 - ay) < 0.6:
                nm = b[0]
                break
        _fit_text(msp, XA + 100, ty - 1.0 * S, "%d %s" % (i + 1, nm), TXT_SMALL, S,
                  axis="y", layer="TEXT")

    # ---- 3. 三级尺寸链 ----
    for (ya, yb, xd, lb) in d["dims_v"]:
        _dim_v(msp, ya, yb, xd, lb, S)
    for (xa, xb, yd, lb) in d["dims_h"]:
        _dim_h(msp, xa, xb, yd, lb, S)
    # 总尺寸
    _dim_h(msp, 0, W, -420, str(W), S)
    _dim_v(msp, 0, H, -620, str(H), S)

    # ---- 4. 图名与类别（先占位登记，避免被后续标高挤走）----
    y = H + 400
    _fit_text(msp, 0, y, "%s  %s（%s · 1:10）" % (code, node["name"], d["cat"]),
              TXT_BIG, S, axis=None)
    y -= 320
    _fit_text(msp, 0, y, "节点类别：%s　｜　索引：%s" % (d["cat"], node.get("ref", "—")),
              TXT_SMALL, S, axis=None)

    # ---- 5. 标高（密集时自动上下错开）----
    for (yy, lb) in d["elev"]:
        cl.line(msp, (-60, yy), (60, yy), "DIM", lw=0.09)
        _elev(msp, -60, yy, lb, S)

    # ---- 6. 构造层次表（题目「四步画法」②③④ 的载体）----
    # 施工要点与表格「同高并排」放右侧，且分两栏折行，避免撑爆 A2 394×400 可用区。
    y = -500
    rows = [["序", "构造层次", "规格 / 厚度", "标高 / 部位"]]
    for i, (nm, spec, elv) in enumerate(node["layers"], start=1):
        rows.append([str(i), nm, spec, elv])
    ybot = cl.table(msp, 0, y, [10, 55, 88, 55], rows, S, rh=8.0, fs=2.8)

    # ---- 7. 施工要点（表格右侧双栏折行）----
    lines = []
    for t in list(d["extra_notes"]) + [node["notes"]]:
        lines.extend(_wrap("· " + t, 17))
    half = (len(lines) + 1) // 2
    for ci, grp in enumerate((lines[:half], lines[half:])):
        xn = 2150 + ci * 490
        yn = y
        cl.text(msp, xn, yn, "施工要点：" if ci == 0 else "（续）", TXT_H, S)
        yn -= 300
        for t in grp:
            cl.text(msp, xn, yn, t, 2.5, S)
            yn -= 238
    return min(ybot, yn)


# ================================================================ 注册表
BUILDERS = {}
for _c in SD.ELEV:
    BUILDERS[_c] = ("elev", gen_elev)
for _c in SD.SECTION:
    BUILDERS[_c] = ("sect", gen_section)

META = {c: (n, r, f, s, q) for (c, n, r, f, s, q) in MD.DRAWINGS}


def build(code):
    name, ratio, frame, sub, seq = META[code]
    S = MD.scale_of(code)
    kind, fn = BUILDERS[code]
    doc = cl.new_drawing()
    msp = doc.modelspace()
    if kind == "elev":
        gen_elev(msp, code, S)
    else:
        gen_section(msp, code, S)
    try:
        bb = extents(msp, fast=True)
        bbox = (bb.extmin.x, bb.extmin.y, bb.extmax.x, bb.extmax.y)
    except Exception:
        bbox = (0, 0, 4000, 3000)
    attrs = MD.title_attrs(code, code, name, ratio, seq,
                           ext="%s｜同学版CAD调整方案" % code)
    cl.insert_frame(msp, doc, code, attrs, bbox)
    fn = "%s_%s" % (code, name)
    OUT = out_dir(code)
    dxf = os.path.join(OUT, fn + ".dxf")
    png = os.path.join(OUT, fn + ".png")
    pdf = os.path.join(OUT, fn + ".pdf")
    tmpd = os.path.join(OUT, "_tmp_" + fn + ".dxf")
    tmpp = os.path.join(OUT, "_tmp_" + fn + ".png")
    tmpf = os.path.join(OUT, "_tmp_" + fn + ".pdf")
    cl.export(doc, msp, tmpd, tmpf, tmpp, paper=(594, 420), dpi=150)
    # 用 bbox 与 A2 可用区比对，超限即在控制台预警（不中断整批）
    bw = (bbox[2] - bbox[0]) / S
    bh = (bbox[3] - bbox[1]) / S
    warn = ""
    if bw > A2_W or bh > A2_H:
        warn = "  [超框 %.0fx%.0fmm > %dx%d]" % (bw, bh, A2_W, A2_H)
    for tmp, dst in ((tmpd, dxf), (tmpp, png), (tmpf, pdf)):
        try:
            if os.path.exists(dst):
                os.replace(tmp, dst)
            else:
                os.rename(tmp, dst)
        except OSError:
            alt = (dst.replace(".dxf", "_新.dxf").replace(".png", "_新.png")
                      .replace(".pdf", "_新.pdf"))
            os.replace(tmp, alt)
            print("    [占用] %s → %s" % (os.path.basename(dst), os.path.basename(alt)))
    return fn, len(msp), (bw, bh), warn


def main():
    codes = sys.argv[1:] or list(BUILDERS)
    ok, fail = [], []
    for code in codes:
        code = code.upper()
        if code not in BUILDERS:
            print("SKIP", code)
            continue
        try:
            fn, n, (bw, bh), warn = build(code)
            ok.append(code)
            print("[OK] %-6s %s 实体 %d  版面 %.0fx%.0fmm%s"
                  % (code, fn, n, bw, bh, warn), flush=True)
        except Exception as ex:
            fail.append((code, repr(ex)))
            print("[FAIL] %s: %r" % (code, ex), flush=True)
            import traceback
            traceback.print_exc()
    print("\n完成 %d/%d" % (len(ok), len(codes)))
    for c, e in fail:
        print("  -", c, e)


if __name__ == "__main__":
    main()
