# -*- coding: utf-8 -*-
"""
同学版 · 9 张平面图生成器（v2 返修版）
口径：37000×37000 单一数据源（student_master.py）+ 图库（student_cad.py）
修复合板级缺陷：
  D1 每图 25 根 CENTER 轴网
  D2 每图三级尺寸链（总尺寸 → 轴线链 → 分区/门洞/家具定位）
  D3 每图叠画 FURNITURE 家具底图
  D4 每图补装修装饰（前台/展示墙/地毯/导视/电话亭/吧台/书架…）
  D5 字号放大（图纸字高 ≥2.5mm）
  D6 文字防重叠：图内只放"区号+短名"，详细信息移到图外明细表
  D7 HATCH 轮廓渲染（不实心黑块）
  D8 坐标口径统一 37000（不再用 43160 作废值）
"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ezdxf
from ezdxf.bbox import extents
from ezdxf.addons.drawing.properties import LayoutProperties

import student_master as MD
import student_cad as cl
import student_furniture as SF

from config import ROOT as BASE
OUT = os.path.join(BASE, "02_平面图_四格式")
os.makedirs(OUT, exist_ok=True)

S = MD.SCALE_PLAN          # 100
TXT_H = 3.2                # 图纸字高 mm（≥2.5 硬下限）
TXT_H_SMALL = 2.8
TXT_H_BIG = 4.0

ZONE_BY_CODE = {z[0]: z for z in MD.ZONES}
# 图内短标签位置：手工指定"空闲位"，保证不压家具、不互相压盖
LABEL_POS = {k: v[1] for k, v in SF.ZONE_SHORT_LABEL.items()}


# ================================================================ 家具绘制
def _rot_box(w, h, rot):
    """按旋转角返回 (dx, dy) 尺寸"""
    return (h, w) if rot in (90, 270) else (w, h)


def draw_item(msp, name, spec_key, cx, cy, rot=0, label=None):
    """按规格库绘制单件家具（矩形轮廓 + 必要内构）"""
    w, h = SF.SPEC[spec_key]
    dw, dh = _rot_box(w, h, rot)
    x1, y1, x2, y2 = cx - dw / 2, cy - dh / 2, cx + dw / 2, cy + dh / 2

    if name in ("绿植", "纸箱"):
        cl.circle(msp, cx, cy, dw / 2, "FURNITURE")
        return
    if name in ("小圆桌", "洽谈圆桌"):
        cl.circle(msp, cx, cy, dw / 2, "FURNITURE")
        return
    if name in ("会议椅", "访客椅", "高脚椅", "办公椅", "阅读椅"):
        cl.rect(msp, x1, y1, x2, y2, layer="FURNITURE", lw=0.18)
        cl.line(msp, (x1, cy), (x2, cy), "FURNITURE")
        return
    if name == "电话亭":
        cl.rect(msp, x1, y1, x2, y2, layer="FURNITURE", lw=0.30)
        cl.line(msp, (x2, cy - 600), (x2 + 300, cy - 600), "FURNITURE")
        return
    if name == "工位桌":
        cl.rect(msp, x1, y1, x2, y2, layer="FURNITURE", lw=0.25)
        # 屏风（沿桌长边）+ 活动柜
        if dw > dh:   # 横向（1400 沿 x）
            cl.line(msp, (x1, cy), (x2, cy), "FURNITURE")
            cl.rect(msp, x1 + 80, y1 + 80, x1 + 420, y1 + 560, layer="FURNITURE", lw=0.13)
        else:        # 纵向
            cl.line(msp, (cx, y1), (cx, y2), "FURNITURE")
            cl.rect(msp, x1 + 80, y1 + 80, x1 + 560, y1 + 420, layer="FURNITURE", lw=0.13)
        return
    if name == "地毯":
        cl.rect(msp, x1, y1, x2, y2, layer="FURNITURE", lw=0.13)
        return
    if name in ("展示墙", "导视墙", "投影幕", "显示屏"):
        cl.rect(msp, x1, y1, x2, y2, layer="FURNITURE", lw=0.35)
        return
    if name in ("书架", "文件柜", "归档柜", "货架", "清洁柜", "设备柜", "冰柜"):
        cl.rect(msp, x1, y1, x2, y2, layer="FURNITURE", lw=0.25)
        n = max(1, int(dw // 600))
        for i in range(1, n):
            xx = x1 + dw * i / n
            cl.line(msp, (xx, y1), (xx, y2), "FURNITURE")
        return
    if name in ("等候沙发", "单人沙发"):
        cl.rect(msp, x1, y1, x2, y2, layer="FURNITURE", lw=0.25)
        cl.line(msp, (x1, y1 + 120), (x2, y1 + 120), "FURNITURE")
        return
    if name == "前台L型":
        cl.rect(msp, x1, y1, x2, y2, layer="FURNITURE", lw=0.35)
        cl.rect(msp, x1 + 1800, y1 - 900, x2, y1, layer="FURNITURE", lw=0.35)
        return
    # 其余（桌、台、吧台、设备）通用矩形
    cl.rect(msp, x1, y1, x2, y2, layer="FURNITURE", lw=0.25)


def draw_all_furniture(msp, codes=None):
    """绘制全部分区家具 + 工位 + 端部缓冲。返回件数。"""
    n = 0
    for code, items in SF.ZONE_FURNITURE.items():
        if codes and code not in codes:
            continue
        for it in items:
            name, spec, cx, cy, rot, qty = it
            for _ in range(qty):
                draw_item(msp, name, spec, cx, cy, rot)
                n += 1
    # 工位（42）
    for (x1, y1, x2, y2) in MD.WORKSTATIONS:
        draw_item(msp, "工位桌", "工位桌", (x1 + x2) / 2, (y1 + y2) / 2,
                  90 if (y2 - y1) > (x2 - x1) else 0)
        n += 1
    # 端部缓冲
    for code, items in SF.END_BUFFER.items():
        if codes and code not in codes:
            continue
        for name, spec, cx, cy, rot, qty in items:
            for _ in range(qty):
                draw_item(msp, name, spec, cx, cy, rot)
                n += 1
    return n


# ================================================================ 分区标注（防重叠）
def _furniture_boxes(codes=None):
    """收集全部家具外包围盒（模型 mm），用于标签自动避让。"""
    boxes = []
    for code, items in SF.ZONE_FURNITURE.items():
        if codes and code not in codes:
            continue
        for name, spec, cx, cy, rot, qty in items:
            w, h = SF.SPEC[spec]
            dw, dh = _rot_box(w, h, rot)
            boxes.append((cx - dw / 2, cy - dh / 2, cx + dw / 2, cy + dh / 2))
    for (x1, y1, x2, y2) in MD.WORKSTATIONS:
        boxes.append((x1, y1, x2, y2))
    for code, items in SF.END_BUFFER.items():
        if codes and code not in codes:
            continue
        for name, spec, cx, cy, rot, qty in items:
            w, h = SF.SPEC[spec]
            dw, dh = _rot_box(w, h, rot)
            boxes.append((cx - dw / 2, cy - dh / 2, cx + dw / 2, cy + dh / 2))
    return boxes


def _text_width(s, h_paper):
    """估算文本宽度（图纸 mm）：中文 1.0em，ASCII 0.55em"""
    em = h_paper
    return sum(em * (1.0 if ord(ch) > 0x2E80 else 0.55) for ch in s)


def _door_label_boxes():
    """门洞标注文字包围盒（门牌 + 宽度的落位）——分区标签也要避开它们。"""
    out = []
    for d in MD.DOORS:
        code, name, (x, y), w, h, _ = d
        s = "%s  %d" % (code, w)
        tw = _text_width(s, TXT_H_SMALL) * S
        th = TXT_H_SMALL * S
        cy = y - 500
        out.append((x - tw / 2, cy - th / 2, x + tw / 2, cy + th / 2))
    return out


def _wall_label_boxes():
    """墙体编号标注（W1…W17）包围盒——分区标签同样要避开。"""
    out = []
    for w in MD.WALLS:
        code, name, (x1, y1), (x2, y2), t, h, _ = w
        tw = _text_width(code, TXT_H) * S
        th = TXT_H * S
        if x1 == x2:
            cx, cy = x1 + 500, (y1 + y2) / 2
        else:
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2 + 450
        out.append((cx - tw / 2, cy - th / 2, cx + tw / 2, cy + th / 2))
    return out


_LABEL_CACHE = {}


def place_zone_labels(codes=None, extra_boxes=None):
    """为每个分区标签自动搜索「离家具最远」的落位，彻底消除标签压家具。

    旧做法是把标签坐标手工写死在 ZONE_SHORT_LABEL 里，改一次家具就要重调一次，
    且仍会压住家具。现在改为：按标签包围盒尺寸在分区内网格扫描，
    取与家具包围盒最小间隙最大的点；若全被占则退到该分区外缘。
    避让对象 = 家具 + 工位 + 端部缓冲 + 门洞标注文字。

    用 numpy 批量算间隙（避免纯 Python 逐点遍历导致 9 图 × 14 区超时），
    并把结果缓存起来 —— 9 张图用的是同一套家具与分区，落位完全相同。
    """
    key = (tuple(sorted(codes)) if codes else "ALL", len(extra_boxes or []))
    if key in _LABEL_CACHE:
        return _LABEL_CACHE[key]
    try:
        import numpy as np
    except ImportError:
        np = None

    boxes = _furniture_boxes(codes) + _door_label_boxes() + _wall_label_boxes() \
        + list(extra_boxes or [])
    if np is not None and boxes:
        arr = np.array(boxes, dtype=float)          # (N,4)
    else:
        arr = None

    placed = []
    out = {}
    for code, (s, _) in SF.ZONE_SHORT_LABEL.items():
        if codes and code not in codes:
            continue
        z = ZONE_BY_CODE[code]
        zx1, zy1, zx2, zy2 = z[2], z[3], z[4], z[5]
        tw = _text_width(s, TXT_H) * S
        th = TXT_H * S
        best = None
        step = 500
        xs = np.arange(zx1 + tw / 2 + 200, zx2 - tw / 2 - 200 + 1, step) if np else \
            list(range(int(zx1 + tw / 2 + 200), int(zx2 - tw / 2 - 200) + 1, step))
        ys = np.arange(zy1 + th / 2 + 200, zy2 - th / 2 - 200 + 1, step) if np else \
            list(range(int(zy1 + th / 2 + 200), int(zy2 - th / 2 - 200) + 1, step))
        if len(xs) == 0 or len(ys) == 0:
            out[code] = (s, ((zx1 + zx2) / 2, (zy1 + zy2) / 2))
            continue
        if np is not None and arr is not None:
            X, Y = np.meshgrid(xs, ys)
            cx = X.ravel()
            cy = Y.ravel()
            bx1 = cx - tw / 2
            by1 = cy - th / 2
            bx2 = cx + tw / 2
            by2 = cy + th / 2
            # 对每个候选点，取与所有家具框的最小间隙（压住 → 负值）
            gap = np.full(cx.shape, 1e9)
            for i in range(arr.shape[0]):
                fx1, fy1, fx2, fy2 = arr[i]
                ix = np.minimum(bx2, fx2) - np.maximum(bx1, fx1)
                iy = np.minimum(by2, fy2) - np.maximum(by1, fy1)
                inter = np.minimum(ix, iy)
                hit = (ix > 0) & (iy > 0)
                sep = np.maximum(np.maximum(fx1 - bx2, bx1 - fx2),
                                 np.maximum(fy1 - by2, by1 - fy2))
                g = np.where(hit, -np.minimum(ix, iy), sep)
                gap = np.minimum(gap, g)
            # 与已放置标签的间距（权重减半，避免标签互相贴太近）
            for pb in placed:
                ix = np.minimum(bx2, pb[2]) - np.maximum(bx1, pb[0])
                iy = np.minimum(by2, pb[3]) - np.maximum(by1, pb[1])
                hit = (ix > 0) & (iy > 0)
                sep = np.maximum(np.maximum(pb[0] - bx2, bx1 - pb[2]),
                                 np.maximum(pb[1] - by2, by1 - pb[3]))
                g = np.where(hit, -np.minimum(ix, iy), sep * 0.5)
                gap = np.minimum(gap, g)
            k = int(np.argmax(gap))
            gv = float(gap[k])
            bx, by = float(cx[k]), float(cy[k])
        else:
            for y in ys:
                for x in xs:
                    bx1, by1 = x - tw / 2, y - th / 2
                    bx2, by2 = x + tw / 2, y + th / 2
                    g = 1e9
                    for fb in boxes:
                        ix = min(bx2, fb[2]) - max(bx1, fb[0])
                        iy = min(by2, fb[3]) - max(by1, fb[1])
                        if ix > 0 and iy > 0:
                            g = -min(ix, iy)
                            break
                        g = min(g, max(fb[0] - bx2, bx1 - fb[2], fb[1] - by2, by1 - fb[3]))
                    for pb in placed:
                        ix = min(bx2, pb[2]) - max(bx1, pb[0])
                        iy = min(by2, pb[3]) - max(by1, pb[1])
                        if ix > 0 and iy > 0:
                            g = min(g, -min(ix, iy))
                    if best is None or g > best[0]:
                        best = (g, x, y)
            gv, bx, by = best
        if gv < 0:
            bx, by = zx1 + tw / 2 + 200, zy1 - 400
        out[code] = (s, (bx, by))
        placed.append((bx - tw / 2, by - th / 2, bx + tw / 2, by + th / 2))
    _LABEL_CACHE[key] = out
    return out


def zone_labels(msp, codes=None, extra_boxes=None):
    """图内只放区号 + 短名；详细信息见图外明细表。落位自动避让家具。

    extra_boxes: 额外的避让对象（本图特有的标注，如 PL-15 的分区标高）。
    """
    for code, (s, (x, y)) in place_zone_labels(codes, extra_boxes).items():
        cl.text(msp, x, y, s, TXT_H, S, align="C")


# ================================================================ 右侧栏排版
# 右侧栏左边界：必须避开东侧分区定位尺寸链（x = OUT_X+4600 = 41600）
# 与轴网外伸（OUT_X + AXIS_EXT + 轴号半径 ≈ 38500），否则尺寸线会压到表格。
RC_X = 43500           # 右侧栏左边界
RC_TOP = 45500         # 右侧栏顶
RC_LEGEND_W = 70       # 图例框宽（图纸 mm）
RC_TBL_W = [14, 46, 18, 14]   # 分区明细表列宽（图纸 mm），总 92mm


class RightPanel:
    """右侧栏纵向排版游标：按调用顺序自上而下堆叠，各段互不压叠。

    旧版把「分区明细表 / 图例 / 说明」分别硬编码在 y=22000 / 19500 / 13200，
    三段纵向区间互相重叠 → 文字压盖不可读。本类改为单一游标顺排，
    每段结束返回当前 y，天然消除重叠。
    """

    def __init__(self, msp, x=RC_X, y=RC_TOP):
        self.msp = msp
        self.x = x
        self.y = y

    def title(self, t, h=TXT_H_BIG):
        cl.text(self.msp, self.x, self.y, t, h, S)
        self.y -= h * S * 1.8

    def lines(self, items, h=TXT_H_SMALL, step=900):
        for t in items:
            cl.text(self.msp, self.x, self.y, t, h, S)
            self.y -= step
        self.y -= 500

    def table(self, col_w, rows, rh=8.5, fs=2.6):
        ybot = cl.table(self.msp, self.x, self.y, col_w, rows, S, rh=rh, fs=fs)
        self.y = ybot - 900

    def legend(self, items, title="图例"):
        # 用 legend_items（支持 rect/wall/line/dot/zone 五类图元）；
        # 旧代码用的 cl.legend 只认 zone/line/dot，wall/rect 会只出字不出符号。
        cl.legend_items(self.msp, self.x, self.y, items, S, title=title,
                        w_paper=RC_LEGEND_W, rh=6.5, fs=3.0)
        self.y -= (len(items) + 1) * 650 + 80 + 600

    def zone_table(self, codes=None):
        """分区明细表 + 各分区家具与装修配置（家具明细单列段落，不做表格）"""
        rows = [["区号", "名称", "面积㎡", "人数"]]
        for z in MD.ZONES:
            code = z[0]
            if codes and code not in codes:
                continue
            rows.append([code, z[1], f"{z[6]:.1f}", str(SF.PEOPLE.get(code, 0))])
        self.title("分区明细表（同学版）")
        self.table(RC_TBL_W, rows)
        self.title("各分区家具与装修配置：", TXT_H)
        self.lines(SF.FURNITURE_NOTE)


# ================================================================ 三级尺寸链
def three_level_dims(msp):
    """三级尺寸链：①总尺寸 ②轴线链 ③分区定位尺寸"""
    # ① 总尺寸
    cl.dim_h(msp, 0, MD.OUT_X, -4600, -3400, label=str(MD.OUT_X), scale=S)
    cl.dim_v(msp, 0, MD.OUT_Y, -4600, -3400, label=str(MD.OUT_Y), scale=S)
    # ② 轴线尺寸链
    cl.dim_chain_h(msp, MD.XS, -2600, 0, S)
    cl.dim_chain_v(msp, MD.YS, -2600, 0, S)
    # ③ 分区定位尺寸（东侧竖向 / 北侧横向）
    ys = sorted({round(z[3]) for z in MD.ZONES} | {round(z[5]) for z in MD.ZONES})
    prev = None
    for y in ys:
        if prev is not None and y - prev > 500:
            cl.dim_v(msp, prev, y, MD.OUT_X + 4600, MD.OUT_X + 3400,
                     label=str(int(y - prev)), scale=S)
        prev = y
    xs = sorted({round(z[2]) for z in MD.ZONES} | {round(z[4]) for z in MD.ZONES})
    prev = None
    for x in xs:
        if prev is not None and x - prev > 500:
            cl.dim_h(msp, prev, x, MD.OUT_Y + 4600, MD.OUT_Y + 3400,
                     label=str(int(x - prev)), scale=S)
        prev = x


def door_dims(msp):
    """门洞尺寸（第三级细节）"""
    for d in MD.DOORS:
        code, name, (x, y), w, h, _ = d
        cl.text(msp, x, y - 500, "%s  %d" % (code, w), TXT_H_SMALL, S,
                align="C", layer="DIM")


def furniture_dims(msp):
    """工位定位尺寸（第三级细节）"""
    ws = MD.WORKSTATIONS
    if not ws:
        return
    # 一个代表性工位的定位尺寸：1400×700
    x1, y1, x2, y2 = ws[0]
    cl.dim_h(msp, x1, x2, y1 - 900, y1, label="1400", scale=S)
    cl.dim_v(msp, y1, y2, x1 - 900, x1, label="700", scale=S)
    cl.text(msp, x1 - 1600, (y1 + y2) / 2, "工位1400×700 屏风1200",
            TXT_H_SMALL, S, align="L", layer="DIM")


# ================================================================ 图例
def plan_legend(msp, x, y, items, title="图例"):
    """图例：统一走 legend_items，支持 rect / wall / line / dot / zone 五类图元。
    旧实现 cl.legend 只识别 zone/line/dot，wall/rect 会「只出文字不出符号」。"""
    cl.legend_items(msp, x, y, items, S, title=title, w_paper=RC_LEGEND_W,
                    rh=6.5, fs=3.0)


# ================================================================ 公共底图
def base_plan(msp, furniture=True, codes=None, dims=True):
    cl.axis_grid(msp, S)
    cl.curtain_wall(msp, S)
    cl.core_walls(msp, S, gray=True)
    for w in MD.WALLS:
        cl.wall_seg(msp, w)
    for d in MD.DOORS:
        cl.door(msp, d, S)
    if furniture:
        draw_all_furniture(msp, codes)
    if dims:
        three_level_dims(msp)


# ================================================================ 各图
def gen_PL01(msp, S):
    base_plan(msp, furniture=True)
    zone_labels(msp)
    furniture_dims(msp)
    door_dims(msp)
    rp = RightPanel(msp)
    rp.zone_table()
    rp.legend([
        ("wall", "轻钢龙骨石膏板隔墙 100"),
        ("rect", "办公工位 1400×700×750"),
        ("rect", "会议桌 / 前台 / 茶水台"),
        ("dot", "声学电话亭 1200×1200"),
        ("rect", "文件柜 2200×450"),
        ("dot", "绿植 Φ600"),
    ])
    rp.title("说明：", TXT_H)
    rp.lines([
        "1. 工位屏风高 1200，桌面高 750；",
        "2. 隔墙 100 厚，内填 50 玻璃棉；",
        "3. 门洞宽度见 PL-04，轴网尺寸见本图三级尺寸链；",
        "4. 核心筒为既有建筑构件，本次仅做界面交接；",
        "5. 固定工位 42 位（Z8 24 + Z9 18），共享高桌 4 席为临时席。"])
    # 核心筒引注：放在核心筒北侧环廊空白带（原位置落在 Z1 分区内，会压分区标签）
    cl.index_bubble(msp, 23000, 28800, "①", S)
    cl.text(msp, 23600, 28800, "① 核心筒（既有构件，详见本图）", TXT_H_SMALL, S)
    cl.north_arrow(msp, -2600, 46200, S)


def gen_PL02(msp, S):
    """原始结构图：只保留结构，新增实体为 0"""
    cl.axis_grid(msp, S)
    for x in MD.XS:
        cl.fill_rect(msp, [(x - 125, 0), (x + 125, 0), (x + 125, MD.OUT_Y), (x - 125, MD.OUT_Y)],
                     layer="COLUMN")
    for y in MD.YS:
        cl.fill_rect(msp, [(0, y - 125), (MD.OUT_X, y - 125), (MD.OUT_X, y + 125), (0, y + 125)],
                     layer="COLUMN")
    for x in MD.XS:
        for y in MD.YS:
            if not (MD.CORE_X1 - 300 < x < MD.CORE_X2 + 300 and MD.CORE_Y1 - 300 < y < MD.CORE_Y2 + 300):
                cl.fill_rect(msp, [(x - 300, y - 300), (x + 300, y - 300),
                                   (x + 300, y + 300), (x - 300, y + 300)],
                             layer="COLUMN")
    cl.curtain_wall(msp, S)
    cl.core_walls(msp, S, gray=True)
    # 核心筒引注：放在核心筒北侧环廊空白带（原位置落在 Z1 分区内，会压分区标签）
    cl.index_bubble(msp, 23000, 28800, "①", S)
    cl.text(msp, 23600, 28800, "① 核心筒（既有构件，详见本图）", TXT_H_SMALL, S)
    zone_labels(msp)
    three_level_dims(msp)
    cl.north_arrow(msp, -2600, 46200, S)
    rp = RightPanel(msp)
    rp.legend([
        ("wall", "幕墙（保留外框）"),
        ("wall", "核心筒剪力墙（保留）"),
        ("zone", "结构梁 250 宽（推定）"),
        ("zone", "结构柱 600×600（推定）"),
    ])
    rp.lines(["构件标注：C-01 柱 600×600；B-01 梁 250"])
    rp.title("说明：", TXT_H)
    rp.lines([
        "1. 本图为原始结构图，仅表达原建筑外墙、幕墙、",
        "　 核心筒、结构梁柱及轴网，新增实体为 0；",
        "2. 梁、柱位置按轴网推定，规格以结构施工图为准；",
        "3. 楼板为 120 厚现浇板；",
        "4. 外框 37000×37000，X 轴 13 根、Y 轴 12 根，严格闭合。"])


def gen_PL04(msp, S):
    base_plan(msp, furniture=True)
    for w in MD.WALLS:
        code, name, (x1, y1), (x2, y2), t, h, _ = w
        if x1 == x2:
            cl.text(msp, x1 + 500, (y1 + y2) / 2, code, TXT_H, S, align="C")
        else:
            cl.text(msp, (x1 + x2) / 2, (y1 + y2) / 2 + 450, code, TXT_H, S, align="C")
    for d in MD.DOORS:
        code, name, (x, y), w, h, _ = d
        cl.text(msp, x, y + 700, code, TXT_H_SMALL, S, align="C")
    zone_labels(msp)
    door_dims(msp)
    rp = RightPanel(msp)
    rp.legend([
        ("wall", "新增隔墙 100（17 段）"),
        ("line", "墙体定位尺寸"),
        ("wall", "保留幕墙 / 核心筒"),
        ("rect", "家具底图（定位参照）"),
    ])
    rp.title("说明：", TXT_H)
    rp.lines([
        "1. 17 段新增隔墙均为 100 厚轻钢龙骨石膏板隔墙，",
        "　 内填 50 玻璃棉，双面双层 9.5 石膏板；",
        "2. 定位以轴网为基准，尺寸见平面图三级尺寸链；",
        "3. 门洞 7 樘：D-01~D-07，宽 900~1500，高 2100/2400；",
        "4. 本图未新增隔墙，墙线均取自原底图，未虚构墙线；",
        "5. 家具底图仅作定位参照，不表示新增隔墙。"])


def _hatch_rect(msp, x1, y1, x2, y2, step=600, angle=45, color=None):
    """平行斜线填充（避免 HATCH 实心黑块）"""
    import math as m
    ca, sa = m.cos(m.radians(angle)), m.sin(m.radians(angle))
    nx, ny = -sa, ca
    corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    projs = [cx * nx + cy * ny for cx, cy in corners]
    d0, d1 = min(projs), max(projs)
    d = d0 + step / 2
    while d < d1:
        p0 = (nx * d, ny * d)
        p1 = (p0[0] + ca * 1e5, p0[1] + sa * 1e5)
        seg = _clip_seg(p0, p1, x1, y1, x2, y2)
        if seg:
            cl.line(msp, seg[0], seg[1], "HATCH")
        d += step


def _clip_seg(p1, p2, x1, y1, x2, y2):
    px, py = p1
    qx, qy = p2
    dx, dy = qx - px, qy - py
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, px - x1), (dx, x2 - px), (-dy, py - y1), (dy, y2 - py)):
        if p == 0:
            if q < 0:
                return None
        else:
            r = q / p
            if p < 0:
                if r > t1:
                    return None
                t0 = max(t0, r)
            else:
                if r < t1:
                    t1 = r
    return (px + t0 * dx, py + t0 * dy), (px + t1 * dx, py + t1 * dy)


def gen_PL05(msp, S):
    base_plan(msp, furniture=True)
    carpet = ["Z8", "Z8b", "Z9", "Z10", "Z2", "Z3", "Z3b"]
    tile = ["Z1", "Z4", "Z11"]
    for code in carpet:
        z = ZONE_BY_CODE[code]
        _hatch_rect(msp, z[2], z[3], z[4], z[5], step=520, angle=90)
        _hatch_rect(msp, z[2], z[3], z[4], z[5], step=520, angle=0)
    for code in tile:
        z = ZONE_BY_CODE[code]
        _hatch_rect(msp, z[2], z[3], z[4], z[5], step=780, angle=90)
    zone_labels(msp)
    rp = RightPanel(msp)
    rp.zone_table()
    rp.legend([
        ("line", "阻燃地毯（交叉斜线）"),
        ("line", "石材/地砖（单向斜线）"),
        ("wall", "新增隔墙 100"),
    ])
    rp.title("地面材料表：", TXT_H)
    rp.lines([
        "Z8 Z9 开放办公区：架空网络地板 600×600；",
        "Z2 培训评审室 / Z10 协作图书：阻燃地毯；",
        "Z4 展示前厅 / Z1 前台：石材地面；",
        "Z11 茶水区：防滑地砖；",
        "Z8b 阅读角：块地毯；Z5 Z6 Z3 Z12：地砖；",
        "环廊：架空网络地板（同办公区）；",
        "起铺点：各区入口处，交界处设金属收口条。"])


def gen_PL06(msp, S):
    base_plan(msp, furniture=True)
    for code, z in ZONE_BY_CODE.items():
        cl.rect(msp, z[2], z[3], z[4], z[5], layer="MEP", lw=0.13)
    # 面板灯：按分区均匀布
    panel = 0
    for code in ("Z8", "Z9", "Z2", "Z10", "Z11", "Z7", "Z4"):
        z = ZONE_BY_CODE[code]
        x1, y1, x2, y2 = z[2], z[3], z[4], z[5]
        nx = max(1, int((x2 - x1) // 2600))
        ny = max(1, int((y2 - y1) // 2600))
        for i in range(nx):
            for j in range(ny):
                cx = x1 + (x2 - x1) * (i + 0.5) / nx
                cy = y1 + (y2 - y1) * (j + 0.5) / ny
                cl.rect(msp, cx - 300, cy - 300, cx + 300, cy + 300, "MEP")
                panel += 1
    # 筒灯：环廊 + 前厅射灯
    down = 0
    for x in range(2000, int(MD.OUT_X) - 1000, 2600):
        for y in (MD.CORE_Y1 - 1500, MD.CORE_Y2 + 1500):
            if 0 < x < MD.OUT_X:
                cl.circle(msp, x, y, 90, "MEP")
                down += 1
    for y in range(int(MD.CORE_Y1), int(MD.CORE_Y2), 2200):
        for x in (MD.CORE_X1 - 1500, MD.CORE_X2 + 1500):
            cl.circle(msp, x, y, 90, "MEP")
            down += 1
    for y in (20500, 23000, 25500, 28000):
        cl.circle(msp, 36500, y, 100, "MEP")
        down += 1
    # 风口 / 烟感
    for code in ("Z8", "Z9", "Z2", "Z10"):
        z = ZONE_BY_CODE[code]
        for i in range(3):
            cx = z[2] + (z[4] - z[2]) * (i + 1) / 4
            cy = (z[3] + z[5]) / 2
            cl.rect(msp, cx - 200, cy - 200, cx + 200, cy + 200, "MEP")
            cl.line(msp, (cx - 200, cy - 200), (cx + 200, cy + 200), "MEP")
            cl.line(msp, (cx - 200, cy + 200), (cx + 200, cy - 200), "MEP")
    smoke = 0
    for code, z in ZONE_BY_CODE.items():
        cx, cy = (z[2] + z[4]) / 2, (z[3] + z[5]) / 2
        cl.circle(msp, cx, cy, 80, "MEP")
        cl.line(msp, (cx - 80, cy), (cx + 80, cy), "MEP")
        cl.line(msp, (cx, cy - 80), (cx, cy + 80), "MEP")
        smoke += 1
    # 检修口
    for x, y in ((10000, MD.CORE_Y1 - 1500), (25000, MD.CORE_Y1 - 1500),
                 (10000, MD.CORE_Y2 + 1500), (25000, MD.CORE_Y2 + 1500)):
        cl.rect(msp, x - 300, y - 300, x + 300, y + 300, "MEP", lt="DASHED")
        cl.text(msp, x + 900, y, "检修口600×600", TXT_H_SMALL, S, align="L")
    zone_labels(msp)
    rp = RightPanel(msp)
    rp.zone_table()
    rp.legend([
        ("rect", "面板灯 600×600"),
        ("dot", "筒灯 Φ150"),
        ("rect", "风口（方框加叉）"),
        ("dot", "烟感（圆圈加十字）"),
    ])
    rp.title("天花材料与标高：", TXT_H)
    rp.lines([
        "Z8 Z9 开放办公区：矿棉板 600×600 明架，吊顶标高 +2.700；",
        "Z2 培训评审室：石膏板造型，吊顶标高 +2.900；",
        "Z4 展示前厅：石膏板 + 灯带，吊顶标高 +3.000；",
        "Z10 协作图书：矿棉板 + 线性灯，吊顶标高 +2.800；",
        "Z11 茶水区：铝扣板，吊顶标高 +2.600；",
        "环廊：石膏板平顶，吊顶标高 +2.600。",
        "本图灯具合计：面板灯 %d 盏，筒灯 %d 盏，烟感 %d 只。"
        % (panel, down, smoke)])


def gen_PL07(msp, S):
    base_plan(msp, furniture=True)
    # 灯具定位（含回路标注）
    panels = []
    for code in ("Z8", "Z9", "Z2", "Z10", "Z11", "Z7", "Z4"):
        z = ZONE_BY_CODE[code]
        nx = max(1, int((z[4] - z[2]) // 2600))
        ny = max(1, int((z[5] - z[3]) // 2600))
        for i in range(nx):
            for j in range(ny):
                cx = z[2] + (z[4] - z[2]) * (i + 0.5) / nx
                cy = z[3] + (z[5] - z[3]) * (j + 0.5) / ny
                cl.rect(msp, cx - 300, cy - 300, cx + 300, cy + 300, "MEP")
                panels.append((cx, cy))
    n_down = 0
    for x in range(2000, int(MD.OUT_X) - 1000, 2600):
        for y in (MD.CORE_Y1 - 1500, MD.CORE_Y2 + 1500):
            cl.circle(msp, x, y, 90, "MEP")
            n_down += 1
    for y in range(int(MD.CORE_Y1), int(MD.CORE_Y2), 2200):
        for x in (MD.CORE_X1 - 1500, MD.CORE_X2 + 1500):
            cl.circle(msp, x, y, 90, "MEP")
            n_down += 1
    for y in (20500, 23000, 25500, 28000):
        cl.circle(msp, 36500, y, 100, "MEP")
        n_down += 1
    # Z2 投影灯 / Z4 展示灯带 / Z10 共享高桌灯
    for x in (35200, 36800):
        cl.circle(msp, x, 36300, 100, "MEP")
        n_down += 1
    cl.line(msp, (36700, 20000), (36700, 29000), "MEP")
    cl.line(msp, (36780, 20000), (36780, 29000), "MEP")
    for x in (28300,):
        cl.circle(msp, x, 36200, 100, "MEP")
        n_down += 1
    zone_labels(msp)
    rp = RightPanel(msp)
    rp.zone_table()
    rp.legend([
        ("rect", "面板灯 600×600"),
        ("dot", "筒灯 Φ150 / 射灯"),
        ("line", "展示灯带"),
    ])
    rp.lines(["灯具合计：面板灯 %d 盏，筒灯/射灯 %d 盏，展示灯带 1 条（9.0m）"
              % (len(panels), n_down)])
    rp.title("照明回路：", TXT_H)
    rp.lines([
        "L1  Z8 办公区面板灯",
        "L2  Z9 办公区面板灯",
        "L3  环廊筒灯（应急兼日常）",
        "L4  Z2 培训室面板灯及投影灯",
        "L5  Z4 展示灯带及射灯",
        "L6  Z10 Z11 面板灯及共享高桌吊灯",
        "应急照明：环廊筒灯及出口指示，双回路供电。",
        "注：工位阵列已减至 42 个固定位，灯具随工位同步核减。"])


def gen_PL08(msp, S):
    base_plan(msp, furniture=True)
    # 工位地插：42 个（与固定工位一一对应）
    n_fb = 0
    for (x1, y1, x2, y2) in MD.WORKSTATIONS:
        if (y2 - y1) > (x2 - x1):
            cx, cy = (x1 + x2) / 2, y1 + 250
        else:
            cx, cy = x2 - 250, (y1 + y2) / 2
        cl.rect(msp, cx - 120, cy - 60, cx + 120, cy + 60, "MEP")
        n_fb += 1
    # 墙边插座
    n_ws = 0
    for y in range(3000, int(MD.OUT_Y) - 2000, 3400):
        cl.circle(msp, 400, y, 90, "MEP")
        n_ws += 1
        cl.circle(msp, MD.OUT_X - 400, y, 90, "MEP")
        n_ws += 1
    for x in range(3000, int(MD.OUT_X) - 2000, 3400):
        cl.circle(msp, x, 400, 90, "MEP")
        n_ws += 1
        cl.circle(msp, x, MD.OUT_Y - 400, 90, "MEP")
        n_ws += 1
    # 专用插座
    sp = [(36000, 36300, "投影电源"), (34700, 34400, "白板电源"),
          (28300, 34100, "共享高桌插座"), (26800, 2200, "共享高桌插座"),
          (26800, 6000, "共享高桌插座"),
          (36000, 9600, "复印机专插"), (4000, 7100, "茶水设备"),
          (5400, 7100, "茶水设备"), (6400, 7100, "茶水设备"),
          (36500, 21000, "展示灯带电源")]
    n_sp = 0
    for x, y, s in sp:
        cl.circle(msp, x, y, 110, "MEP")
        cl.text(msp, x + 400, y + 150, s, TXT_H_SMALL, S, align="L")
        n_sp += 1
    zone_labels(msp)
    rp = RightPanel(msp)
    rp.zone_table()
    rp.legend([
        ("rect", "工位地插 120×60"),
        ("dot", "墙边插座"),
        ("dot", "专用设备插座"),
    ])
    rp.lines(["点位合计：工位地插 %d 个（对应 42 固定工位）  墙边插座 %d 个  专用插座 %d 个"
              % (n_fb, n_ws, n_sp)])
    rp.title("回路划分：", TXT_H)
    rp.lines([
        "W1 W2  Z8 办公区地插及墙插",
        "W3 W4  Z9 办公区地插及墙插",
        "W5  Z2 培训室 投影 视频会议 移动白板专用",
        "W6  Z11 茶水设备专用",
        "W7  Z5 文印室复印机专用",
        "W8  Z4 展示前厅灯带",
        "共享高桌插座为可变席位预留，随席设置。",
        "注：插座数量已按 42 个固定工位重新核算。"])


def gen_PL09(msp, S):
    base_plan(msp, furniture=True)
    # 茶水区给排水（沿用母版点位，不新增）
    pts = [(2200, 6400, "给水J1 DN20"), (5200, 6400, "地漏DN50"),
           (7000, 6400, "地漏DN50"), (7200, 4600, "排水立管DN100")]
    for x, y, s in pts:
        cl.circle(msp, x, y, 120, "MEP")
        cl.text(msp, x, y - 700, s, TXT_H_SMALL, S, align="C")
    cl.line(msp, (2200, 7000), (7000, 7000), "MEP")
    cl.text(msp, 4500, 7600, "排水横管 i=0.005 坡向排水立管", TXT_H_SMALL, S, align="C")
    # 给水点标高注：放在管线标注下方空白，避免与「给水J1 DN20」压叠
    cl.text(msp, 2200, 4900, "给水点标高 H+0.300 台盆处", TXT_H_SMALL, S, align="C")
    zone_labels(msp)
    rp = RightPanel(msp)
    rp.zone_table()
    rp.legend([
        ("dot", "给水点 DN20"),
        ("dot", "地漏 DN50"),
        ("dot", "排水立管 DN100"),
    ])
    rp.title("给排水说明：", TXT_H)
    rp.lines([
        "1. 本图仅表达茶水区给排水点位，其余区域沿用原建筑给排水系统，未新增点位；",
        "2. 给水由原建筑立管引入 DN20，沿吊顶敷设至台盆处；",
        "3. 排水 DN50 接原建筑排水立管，横管坡度 i=0.005；",
        "4. 地漏设于操作台端部，便于清洁排水；",
        "5. 热水由茶水间就地小型热水器提供。",
        "注：茶水区功能调整为“茶水·员工交流”后，给排水规则仍按原图核验，未增加点位。"])


def gen_PL15(msp, S):
    base_plan(msp, furniture=True)
    elev = {"Z8": "+2.700", "Z9": "+2.700", "Z2": "+2.900", "Z10": "+2.800",
            "Z4": "+3.000", "Z1": "+3.000", "Z11": "+2.600", "Z7": "+2.700",
            "Z5": "+2.700", "Z6": "+2.700", "Z3": "+2.700", "Z3b": "+2.700",
            "Z8b": "+2.700", "Z12": "+2.700"}
    # 标高文字：先算好包围盒，交给 zone_labels 一并避让（否则标高会压住分区标签）
    elev_boxes = []
    for code, z in ZONE_BY_CODE.items():
        cx, cy = (z[2] + z[4]) / 2, (z[3] + z[5]) / 2
        s = "标高%s" % elev[code]
        tw = _text_width(s, TXT_H) * S
        th = TXT_H * S
        cl.text(msp, cx, cy + 500, s, TXT_H, S, align="C")
        elev_boxes.append((cx - tw / 2, cy + 500 - th / 2,
                           cx + tw / 2, cy + 500 + th / 2))
    # 注：分区定位尺寸链已由 base_plan → three_level_dims 绘制，此处不再重复
    # （重复绘制会在同一位置产生两份重叠数字）
    # 培训室投影墙 / 展示墙灯带 / 共享高桌灯具 定位尺寸
    # 投影幕尺寸放到比分区定位尺寸链更外一圈（y=44600），避免两排数字叠在一起
    cl.dim_h(msp, 34800, 37200, 44600, 44200, label="投影幕2400", scale=S)
    cl.dim_v(msp, 20000, 29000, 36200, 36400, label="展示墙9000", scale=S)
    cl.dim_h(msp, 27100, 29500, 33400, 33200, label="高桌2400", scale=S)
    zone_labels(msp, extra_boxes=elev_boxes)
    rp = RightPanel(msp)
    rp.zone_table()
    rp.legend([
        ("line", "吊顶分区线"),
        ("line", "标高符号"),
        ("rect", "家具底图（定位参照）"),
    ])
    rp.title("天花分区尺寸与标高：", TXT_H)
    rp.lines([
        "各分区吊顶标高见图面标注，环廊标高 +2.600；",
        "Z2 培训室投影幕居中，幕宽 2400，与灯具对位；",
        "Z4 展示墙灯带沿东侧 9000 连续布置；",
        "Z10 共享高桌上方设吊灯，与高桌中心对位；",
        "高差处设暗藏灯带收口。",
        "注：本图尺寸链已按同学版分区边界重新核算。"])


BUILDERS = {
    "PL-01": ("平面布置图", gen_PL01),
    "PL-02": ("原始结构图", gen_PL02),
    "PL-04": ("新增隔墙定位图", gen_PL04),
    "PL-05": ("地面铺装图", gen_PL05),
    "PL-06": ("天花布置图", gen_PL06),
    "PL-07": ("灯具定位图", gen_PL07),
    "PL-08": ("插座定位图", gen_PL08),
    "PL-09": ("给排水点位图", gen_PL09),
    "PL-15": ("天花尺寸图", gen_PL15),
}

META = {c: (n, r, f, s, q) for (c, n, r, f, s, q) in MD.DRAWINGS}


def build(code):
    name, ratio, frame, sub, seq = META[code]
    doc = cl.new_drawing()
    msp = doc.modelspace()
    BUILDERS[code][1](msp, S)
    try:
        bb = extents(msp, fast=True)
        bbox = (bb.extmin.x, bb.extmin.y, bb.extmax.x, bb.extmax.y)
    except Exception:
        bbox = (-20000, -20000, 20000, 20000)
    attrs = MD.title_attrs(code, code, name, ratio, seq,
                           ext="%s｜同学版CAD调整方案 v2" % code)
    cl.insert_frame(msp, doc, code, attrs, bbox)
    fn = "%s_%s" % (code, name)
    dxf = os.path.join(OUT, fn + ".dxf")
    png = os.path.join(OUT, fn + ".png")
    pdf = os.path.join(OUT, fn + ".pdf")
    # 目标文件若被 AutoCAD 等程序占用，直接覆盖会 PermissionError。
    # 策略：先写临时文件，再逐个替换；替换失败则落到 _新 后缀，绝不中断整批。
    tmpd = os.path.join(OUT, "_tmp_" + fn)
    tmpp = os.path.join(OUT, "_tmp_" + fn + ".png")
    tmpf = os.path.join(OUT, "_tmp_" + fn + ".pdf")
    cl.export(doc, msp, tmpd, tmpf, tmpp, paper=(841, 594), dpi=150)
    for tmp, dst in ((tmpd, dxf), (tmpp, png), (tmpf, pdf)):
        try:
            if os.path.exists(dst):
                os.replace(tmp, dst)
            else:
                os.rename(tmp, dst)
        except OSError:
            alt = dst.replace(".dxf", "_新.dxf").replace(".png", "_新.png").replace(".pdf", "_新.pdf")
            os.replace(tmp, alt)
            print("    [占用] %s → %s" % (os.path.basename(dst), os.path.basename(alt)))
    return fn, len(msp)


def main():
    codes = sys.argv[1:] or list(BUILDERS)
    ok, fail = [], []
    for code in codes:
        code = code.upper()
        if code not in BUILDERS:
            print("SKIP", code)
            continue
        try:
            fn, n = build(code)
            ok.append(code)
            print("[OK] %s %s 实体 %d" % (code, fn, n), flush=True)
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
