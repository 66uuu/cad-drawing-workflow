# -*- coding: utf-8 -*-
"""
A-1 毕业设计 · CAD 图库（ezdxf）
提供：9 专业图层 / A1·A2 竖栏图框块（17 ATTDEF，ATTRIB 与 ATTDEF 位置严格对齐）/
三级尺寸 / 墙 / 门 / 工位 / 家具 / 机电符号 / 标高 / 索引 / 图例 / PDF·PNG 导出。
约定：模型空间 = 真实 mm；文字字高 = 图纸字高(mm) × 比例分母。
"""
from pathlib import Path
import ezdxf
from ezdxf.fonts import fonts as _ezfonts
from config import FONT_SCAN_DIRS

for _fd in FONT_SCAN_DIRS:
    _ezfonts.font_manager.scan_folder(Path(_fd))

from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.config import Configuration, HatchPolicy
from ezdxf.addons.drawing import matplotlib as ezdxf_mpl
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import student_master as MD

# 图框块内 ATTDEF 位置缓存 {block_name: {tag: (x, y)}}
ATTDEF_POS = {}


def new_drawing():
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4          # mm
    doc.header["$MEASUREMENT"] = 1       # 公制
    doc.header["$LUNITS"] = 2            # 十进制
    doc.styles.add("HEI", font="simhei.ttf")     # 黑体
    doc.styles.add("XZC", font="simplex_.ttf")   # 尺寸数字
    # 预注册线型：CENTER（轴网）、DASHED（检修口/虚线构件），防 DXF 里引用未定义线型
    if "CENTER" not in doc.linetypes:
        doc.linetypes.add("CENTER", pattern=[2.0, 1.25, -0.25, 1.25, -0.25, 0.0],
                          description="Center __ . __ .")
    if "DASHED" not in doc.linetypes:
        doc.linetypes.add("DASHED", pattern=[5.0, -2.0, 1.0, -2.0],
                          description="Dashed __ __ __")
    for name, _, color, lw in MD.LAYERS:
        kw = {"color": color, "lineweight": int(round(lw * 100))}
        if name == "AXIS":
            kw["linetype"] = "CENTER"   # 附件三·二：轴网轴线必须用 CENTER 线型（图层默认即 CENTER）
        doc.layers.add(name, **kw)
    return doc


# ---------------------------------------------------------------- 图框块
def _cell(blk, pos_map, x1, y1, x2, y2, tag, label_h=2.0, val_h=3.0):
    """竖栏单元格：分隔线 + 标签文字 + ATTDEF（记录位置供 ATTRIB 对齐）"""
    blk.add_line((x1, y1), (x2, y1), dxfattribs={"layer": "FRAME"})
    blk.add_line((x1, y1), (x1, y2), dxfattribs={"layer": "FRAME"})
    blk.add_text(tag, dxfattribs={"layer": "TEXT", "style": "HEI",
                                  "height": label_h}).set_placement((x1 + 1.5, y2 - label_h - 1.0))
    px, py = (x1 + x2) / 2, (y1 + y2) / 2 - val_h / 2
    blk.add_attdef(tag, (px, py), dxfattribs={"layer": "TEXT", "style": "HEI",
                                              "height": val_h})
    pos_map[tag] = (px, py, val_h)


def _build_frame(doc, name, W, H):
    """竖栏图框：外框 + 内框 + 右侧 180 竖栏 + 17 ATTDEF。块空间 = 图纸 mm(1:1)。"""
    M = 10
    blk = doc.blocks.new(name)
    pos = {}
    blk.add_lwpolyline([(0, 0), (W, 0), (W, H), (0, H)], close=True,
                       dxfattribs={"layer": "FRAME", "lineweight": 70})
    blk.add_lwpolyline([(M, M), (W - M, M), (W - M, H - M), (M, H - M)], close=True,
                       dxfattribs={"layer": "FRAME", "lineweight": 35})
    sx = W - M - 180
    x1, x2, ytop = sx, W - M, H - M
    blk.add_line((x1, M), (x1, ytop), dxfattribs={"layer": "FRAME", "lineweight": 50})
    if W > 600:      # A1 841×594（可用 574）
        rows = [("工程名称", 45, 3.5), ("子项", 37, 3.0), ("(扩展图名)", 55, 2.5)]
        pair_rows = [("设计号", "审定人", 55), ("所长", "审核人", 55),
                     ("主持人", "校对人", 55), ("设计人", "负责人", 55), ("图幅", "序号", 45)]
        triple = [("日期", "图号", "比例", 55)]
        name_h, sign_h = 55, 62
    else:            # A2 594×420（可用 400）
        rows = [("工程名称", 37, 3.5), ("子项", 27, 3.0), ("(扩展图名)", 35, 2.5)]
        pair_rows = [("设计号", "审定人", 35), ("所长", "审核人", 35),
                     ("主持人", "校对人", 35), ("设计人", "负责人", 35), ("图幅", "序号", 30)]
        triple = [("日期", "图号", "比例", 35)]
        name_h, sign_h = 50, 46
    y = ytop
    for tag, h, vh in rows:
        y -= h
        _cell(blk, pos, x1, y, x2, y + h, tag, 2.0, vh)
    for ta, tb, h in pair_rows:
        y -= h
        xm = (x1 + x2) / 2
        _cell(blk, pos, x1, y, xm, y + h, ta)
        _cell(blk, pos, xm, y, x2, y + h, tb)
    for t1, t2, t3, h in triple:
        y -= h
        xa = x1 + (x2 - x1) * 0.28
        xb = x1 + (x2 - x1) * 0.72
        _cell(blk, pos, x1, y, xa, y + h, t1)
        _cell(blk, pos, xa, y, xb, y + h, t2)
        _cell(blk, pos, xb, y, x2, y + h, t3)
    y -= name_h
    _cell(blk, pos, x1, y, x2, y + name_h, "图名", 2.0, 5.0)
    y -= sign_h
    blk.add_line((x1, y), (x2, y), dxfattribs={"layer": "FRAME"})
    for i, t in enumerate(["会签：建筑 %s" % MD.STUDENT,
                           "总图— 结构— 给排水—",
                           "暖通— 动力— 电气— 电讯—"]):
        blk.add_text(t, dxfattribs={"layer": "TEXT", "style": "HEI",
                                    "height": 2.5}).set_placement(
            (x1 + 1.5, y + sign_h - 4.0 - i * 2.6))
    ATTDEF_POS[name] = pos
    return blk


def insert_frame(msp, doc, code, attrs, bbox):
    """按图形 bbox 把图框插到左侧绘图区居中；填 17 栏 + 学生信息行。返回插入点。"""
    frame = MD.frame_of(code)
    S = MD.scale_of(code)
    # 注意：ATTDEF_POS 是跨文档缓存，必须同时确认块在*本文档*里存在
    if frame not in ATTDEF_POS or frame not in doc.blocks:
        W, H = (841, 594) if frame == MD.FRAME_A1 else (594, 420)
        _build_frame(doc, frame, W, H)
    W, H = (841, 594) if frame == MD.FRAME_A1 else (594, 420)
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    ix = cx - (10 + (W - 180 - 20) / 2) * S
    iy = cy - (10 + (H - 20) / 2) * S
    ins = msp.add_blockref(frame, (ix, iy), dxfattribs={"layer": "FRAME"})
    ins.dxf.xscale = S
    ins.dxf.yscale = S
    ins.dxf.zscale = S
    for tag, (bx, by, bh) in ATTDEF_POS[frame].items():
        ins.add_attrib(tag, attrs.get(tag, ""), (ix + bx * S, iy + by * S),
                       dxfattribs={"layer": "TEXT", "style": "HEI",
                                   "height": bh * S})
    # 学生信息行 + 会签行（绘图区左下内侧）
    msp.add_text(MD.STUDENT_LINE, dxfattribs={"layer": "TEXT", "style": "HEI",
                                              "height": 3.5 * S}).set_placement(
        (ix + 12 * S, iy + 8 * S))
    _sign = "会签：建筑 %s｜总图 %s｜结构 %s｜给排水 %s｜暖通 %s｜动力 %s｜电气 %s｜电讯 %s" % (
        MD.STUDENT, *([MD.TEACHER] * 7))
    msp.add_text(_sign, dxfattribs={"layer": "TEXT", "style": "HEI",
                                    "height": 2.5 * S}).set_placement(
        (ix + 12 * S, iy + 4 * S))
    return (ix, iy)


# ---------------------------------------------------------------- 基础原语
def th(h_paper, scale):
    return h_paper * scale


def line(msp, p1, p2, layer="WALL", lw=None, lt=None):
    attribs = {"layer": layer}
    if lt:
        attribs["linetype"] = lt
    e = msp.add_line(p1, p2, dxfattribs=attribs)
    if lw:
        e.dxf.lineweight = int(round(lw * 100))
    return e


def rect(msp, x1, y1, x2, y2, layer="FURNITURE", lw=None, close=True, lt=None):
    attribs = {"layer": layer}
    if lt:
        attribs["linetype"] = lt
    e = msp.add_lwpolyline([(x1, y1), (x2, y1), (x2, y2), (x1, y2)], close=close,
                           dxfattribs=attribs)
    if lw:
        e.dxf.lineweight = int(round(lw * 100))
    return e


def poly(msp, pts, layer="FURNITURE", lw=None, close=True):
    e = msp.add_lwpolyline(pts, close=close, dxfattribs={"layer": layer})
    if lw:
        e.dxf.lineweight = int(round(lw * 100))
    return e


def fill_rect(msp, pts, layer="WALL", color=None):
    """实心填充；color=None 表示随图层色(BYLAYER)，符合附件三「按层设色」红线；
    color 支持 ACI int 或 (r,g,b) tuple（tuple 走 true_color）"""
    attribs = {"layer": layer}
    if isinstance(color, (tuple, list)):
        h = msp.add_hatch(dxfattribs=attribs)
        h.paths.add_polyline_path(pts, is_closed=True)
        h.set_solid_fill(rgb=tuple(int(c) for c in color))
    elif color is not None:
        h = msp.add_hatch(color=color, dxfattribs=attribs)
        h.paths.add_polyline_path(pts, is_closed=True)
        h.set_solid_fill(color)
    else:  # BYLAYER（256）
        h = msp.add_hatch(dxfattribs=attribs)
        h.paths.add_polyline_path(pts, is_closed=True)
        h.set_solid_fill(color=256)
    return h


def text(msp, x, y, s, h_paper, scale, layer="TEXT", align="L", rotation=0, style="HEI"):
    e = msp.add_text(s, dxfattribs={"layer": layer, "style": style,
                                    "height": th(h_paper, scale), "rotation": rotation})
    if align == "L":
        e.set_placement((x, y))
    elif align == "C":
        e.set_placement((x, y), align=ezdxf.enums.TextEntityAlignment.CENTER)
    else:
        e.set_placement((x, y), align=ezdxf.enums.TextEntityAlignment.RIGHT)
    return e


def circle(msp, x, y, r, layer="DIM"):
    return msp.add_circle((x, y), r, dxfattribs={"layer": layer})


def arc(msp, x, y, r, a1, a2, layer="DOOR_WIN"):
    return msp.add_arc((x, y), r, a1, a2, dxfattribs={"layer": layer})


# ---------------------------------------------------------------- 尺寸
def _tick(msp, x, y, scale, layer="DIM"):
    L = 2.5 * scale
    line(msp, (x - L / 2, y - L / 2), (x + L / 2, y + L / 2), layer)


def dim_h(msp, x1, x2, y_dim, y_ref, label=None, scale=100, layer="DIM"):
    """水平尺寸一段"""
    over = 250 if y_dim > y_ref else -250
    line(msp, (x1, y_ref), (x1, y_dim + over), layer)
    line(msp, (x2, y_ref), (x2, y_dim + over), layer)
    line(msp, (x1, y_dim), (x2, y_dim), layer)
    _tick(msp, x1, y_dim, scale, layer)
    _tick(msp, x2, y_dim, scale, layer)
    if label:
        text(msp, (x1 + x2) / 2, y_dim + 0.6 * th(3.0, scale), label, 3.0, scale,
             layer=layer, align="C", style="XZC")


def dim_chain_h(msp, xs, y_dim, y_ref, scale=100, layer="DIM"):
    """水平尺寸链"""
    for i in range(len(xs) - 1):
        x1, x2 = xs[i], xs[i + 1]
        line(msp, (x1, y_ref), (x1, y_dim - 250), layer)
        line(msp, (x1, y_dim), (x2, y_dim), layer)
        _tick(msp, x1, y_dim, scale, layer)
        text(msp, (x1 + x2) / 2, y_dim + 0.6 * th(3.0, scale), str(int(x2 - x1)),
             3.0, scale, layer=layer, align="C", style="XZC")
    line(msp, (xs[-1], y_ref), (xs[-1], y_dim - 250), layer)
    _tick(msp, xs[-1], y_dim, scale, layer)


def dim_v(msp, y1, y2, x_dim, x_ref, label=None, scale=100, layer="DIM"):
    over = 250 if x_dim > x_ref else -250
    line(msp, (x_ref, y1), (x_dim + over, y1), layer)
    line(msp, (x_ref, y2), (x_dim + over, y2), layer)
    line(msp, (x_dim, y1), (x_dim, y2), layer)
    _tick(msp, x_dim, y1, scale, layer)
    _tick(msp, x_dim, y2, scale, layer)
    if label:
        text(msp, x_dim + 0.6 * th(3.0, scale), (y1 + y2) / 2 - th(1.2, scale), label,
             3.0, scale, layer=layer, align="L", rotation=90, style="XZC")


def dim_chain_v(msp, ys, x_dim, x_ref, scale=100, layer="DIM"):
    for i in range(len(ys) - 1):
        y1, y2 = ys[i], ys[i + 1]
        line(msp, (x_ref, y1), (x_dim - 250, y1), layer)
        line(msp, (x_dim, y1), (x_dim, y2), layer)
        _tick(msp, x_dim, y1, scale, layer)
        text(msp, x_dim + 0.6 * th(3.0, scale), (y1 + y2) / 2 - th(1.2, scale),
             str(int(y2 - y1)), 3.0, scale, layer=layer, align="L", rotation=90, style="XZC")
    line(msp, (x_ref, ys[-1]), (x_dim - 250, ys[-1]), layer)
    _tick(msp, x_dim, ys[-1], scale, layer)


# ---------------------------------------------------------------- 平面构件
def curtain_wall(msp, scale, layer="WALL"):
    rect(msp, 0, 0, MD.OUT_X, MD.OUT_Y, layer=layer, lw=0.5)
    for x in range(0, MD.OUT_X + 1, 3600):
        line(msp, (x, 0), (x, 150), "DOOR_WIN")
        line(msp, (x, MD.OUT_Y), (x, MD.OUT_Y - 150), "DOOR_WIN")
    for y in range(0, MD.OUT_Y + 1, 3600):
        line(msp, (0, y), (150, y), "DOOR_WIN")
        line(msp, (MD.OUT_X, y), (MD.OUT_X - 150, y), "DOOR_WIN")


def _part_h(msp, x1, x2, y, t=200, layer="WALL", lw=0.35):
    """水平内隔墙（实心 poché）"""
    fill_rect(msp, [(x1, y - t / 2), (x2, y - t / 2), (x2, y + t / 2), (x1, y + t / 2)],
              layer=layer, color=7)
    rect(msp, x1, y - t / 2, x2, y + t / 2, layer=layer, lw=lw)


def _part_v(msp, y1, y2, x, t=200, layer="WALL", lw=0.35):
    """竖向内隔墙（实心 poché）"""
    fill_rect(msp, [(x - t / 2, y1), (x + t / 2, y1), (x + t / 2, y2), (x - t / 2, y2)],
              layer=layer, color=7)
    rect(msp, x - t / 2, y1, x + t / 2, y2, layer=layer, lw=lw)


def _fdoor(msp, hinge, ang0, w, scale, label=None, flip=False):
    """防火门：门扇线 + 90°开启弧 + 可选级别标签（DOOR_WIN 层）"""
    import math as _m
    hx, hy = hinge
    a1 = ang0 if not flip else ang0 + 90
    a2 = ang0 + 90 if not flip else ang0
    if ang0 in (0, 180):
        line(msp, (hx, hy), (hx + (w if ang0 == 0 else -w), hy), "DOOR_WIN")
    else:
        line(msp, (hx, hy), (hx, hy + (w if ang0 == 90 else -w)), "DOOR_WIN")
    arc(msp, hx, hy, w, min(a1, a2), max(a1, a2))
    if label:
        import math as _m2
        mx_ = hx + w * 0.5 * _m2.cos(_m2.radians(ang0 + 45))
        my_ = hy + w * 0.5 * _m2.sin(_m2.radians(ang0 + 45))
        text(msp, mx_, my_, label, 2.5, scale, layer="TEXT", align="C")


def _stair(msp, sx1, sy1, sx2, sy2, scale, up=True, label="楼梯"):
    """双跑楼梯：踏步线 + 两跑扶手 + 中间休息平台 + 上下行箭头 + 剖断线"""
    x1, y1, x2, y2 = sx1 + 200, sy1 + 200, sx2 - 200, sy2 - 200   # 内净空
    cxm = (x1 + x2) / 2
    land_h = 1400                                   # 顶部休息平台深
    fy2 = y2 - land_h                               # 跑步段顶
    half = (x2 - x1) / 2
    n = 9                                           # 每跑踏步数（含平台起步）
    # 踏步线（左右两跑）
    for i in range(1, n + 1):
        yy = y1 + (fy2 - y1) * i / (n + 0.5)
        line(msp, (x1 + 100, yy), (cxm - 60, yy), "DOOR_WIN", lw=0.13)
        line(msp, (cxm + 60, yy), (x2 - 100, yy), "DOOR_WIN", lw=0.13)
    # 扶手（两跑各一条，内偏 120）
    line(msp, (cxm - 180, y1 + 100), (cxm - 180, fy2), "DOOR_WIN", lw=0.13)
    line(msp, (cxm + 180, y1 + 100), (cxm + 180, fy2), "DOOR_WIN", lw=0.13)
    # 平台边线
    line(msp, (x1 + 100, fy2), (cxm - 60, fy2), "DOOR_WIN", lw=0.18)
    line(msp, (cxm + 60, fy2), (x2 - 100, fy2), "DOOR_WIN", lw=0.18)
    # 剖断线（右跑中部 斜断线）
    by = y1 + (fy2 - y1) * 0.45
    line(msp, (cxm + 60, by - 350), (x2 - 100, by + 350), "DOOR_WIN", lw=0.13)
    # 上下行箭头（左跑）
    ax_ = (x1 + cxm) / 2
    line(msp, (ax_, y1 + 250), (ax_, fy2 - 250), "DIM", lw=0.18)
    line(msp, (ax_ - 90, fy2 - 250 - 300), (ax_, fy2 - 250), "DIM")
    line(msp, (ax_ + 90, fy2 - 250 - 300), (ax_, fy2 - 250), "DIM")
    text(msp, ax_ - 250, y1 + 250 + 100, "上" if up else "下", 2.5, scale,
         layer="TEXT", align="L")
    text(msp, (x1 + x2) / 2, y2 - land_h / 2 - 150, label, 2.5, scale, align="C")


def _elev(msp, shaft_x1, shaft_x2, sy1, sy2, scale, label="电梯"):
    """电梯：井道轮廓 + 门洞（双滑门）+ 标签"""
    rect(msp, shaft_x1, sy1, shaft_x2, sy2, layer="WALL", lw=0.35)
    dx = shaft_x1                                  # 门开在井道西侧（面向电梯厅）
    dw = (sy2 - sy1) * 0.55                        # 门洞宽 1200 档
    my_ = (sy1 + sy2) / 2
    line(msp, (dx, my_ - dw / 2), (dx, my_ + dw / 2), "DOOR_WIN", lw=0.18)
    # 双扇滑门（错位短线）
    line(msp, (dx, my_ - dw / 2), (dx + 350, my_ - dw / 2 + 90), "DOOR_WIN", lw=0.13)
    line(msp, (dx, my_ + dw / 2), (dx + 350, my_ + dw / 2 - 90), "DOOR_WIN", lw=0.13)
    text(msp, (shaft_x1 + shaft_x2) / 2, my_, label, 2.5, scale, align="C")


def core_walls(msp, scale, gray=False, annotate=True):
    """V3.2 既有核心筒底图（真实 CAD 实体，跨图统一）：
    200 厚剪力墙 poché / 双跑楼梯×2（踏步+扶手+上下行箭头+剖断线）/
    电梯×2（井道+滑门）/ 卫生间（隔间+洗手台）/ 设备管井（45°填充+百叶）/
    防火门 FM乙（楼梯前室）与 FM甲（管井检修）。几何与标注全图统一；
    gray/annotate 参数保留兼容旧调用，不再改变图形内容。"""
    X1, Y1, X2, Y2 = MD.CORE_X1, MD.CORE_Y1, MD.CORE_X2, MD.CORE_Y2
    W, H = MD.CORE_W, MD.CORE_H
    T = 200                                        # 剪力墙厚
    ix1, iy1, ix2, iy2 = X1 + T, Y1 + T, X2 - T, Y2 - T   # 筒内净边界
    # ---- 1. 外墙 poché：外框与内面之间四条实心带 ----
    fill_rect(msp, [(X1, Y1), (X2, Y1), (X2, Y1 + T), (X1, Y1 + T)], color=7)
    fill_rect(msp, [(X1, Y2 - T), (X2, Y2 - T), (X2, Y2), (X1, Y2)], color=7)
    fill_rect(msp, [(X1, Y1 + T), (X1 + T, Y1 + T), (X1 + T, Y2 - T), (X1, Y2 - T)], color=7)
    fill_rect(msp, [(X2 - T, Y1 + T), (X2, Y1 + T), (X2, Y2 - T), (X2 - T, Y2 - T)], color=7)
    rect(msp, X1, Y1, X2, Y2, layer="WALL", lw=0.50)
    rect(msp, ix1, iy1, ix2, iy2, layer="WALL", lw=0.25)

    # ---- 2. 内部布局（相对核心筒净尺寸，保证任意改版仍闭合） ----
    # 楼梯A：左上；楼梯B：右下；电梯厅+井道：右中；卫生间：左下；管井：右上；中部前室
    sA_x2 = ix1 + 0.32 * W
    sA_y1 = iy2 - 0.30 * H
    sB_x1 = ix2 - 0.32 * W
    sB_y2 = iy1 + 0.30 * H
    wc_x2 = ix1 + 0.40 * W
    wc_y2 = iy1 + 0.26 * H
    sh_x1 = ix2 - 0.22 * W
    mj_x1 = ix2 - 0.26 * W
    mj_y1 = iy2 - 0.17 * H
    cy = (Y1 + Y2) / 2
    lby1, lby2 = cy - 0.14 * H, cy + 0.14 * H      # 电梯厅南北界

    # 内隔墙
    _part_h(msp, ix1, sA_x2, sA_y1)                # 楼梯A南墙
    _part_v(msp, sA_y1, iy2, sA_x2)                # 楼梯A东墙
    _part_h(msp, sB_x1, ix2, sB_y2)                # 楼梯B北墙
    _part_v(msp, iy1, sB_y2, sB_x1)                # 楼梯B西墙
    _part_h(msp, ix1, wc_x2, wc_y2)                # 卫生间北墙
    _part_v(msp, iy1, wc_y2, wc_x2)                # 卫生间东墙
    _part_h(msp, mj_x1, ix2, mj_y1)                # 管井南墙
    _part_v(msp, mj_y1, iy2, mj_x1)                # 管井西墙
    _part_h(msp, sh_x1, ix2, lby2)                 # 电梯厅北墙（管井以南）
    _part_v(msp, lby1, lby2, sh_x1)                # 电梯厅西墙
    _part_h(msp, sh_x1, ix2, lby1)                 # 电梯厅南墙（楼梯B以北）

    # ---- 3. 楼梯 ×2（真实踏步） ----
    _stair(msp, ix1, sA_y1, sA_x2, iy2, scale, up=True, label="楼梯A（上）")
    _stair(msp, sB_x1, iy1, ix2, sB_y2, scale, up=False, label="楼梯B（下）")
    # 楼梯前室防火门 FM乙-1121：A 南墙 / B 北墙，门洞 1100
    line(msp, (ix1 + 700, sA_y1 - 100), (ix1 + 1800, sA_y1 - 100), "WALL")   # 门洞（断墙示意）
    _fdoor(msp, (ix1 + 700, sA_y1 - 100), 90, 1100, scale, label="FM乙-1121")
    line(msp, (ix2 - 1800, sB_y2 + 100), (ix2 - 700, sB_y2 + 100), "WALL")
    _fdoor(msp, (ix2 - 1800, sB_y2 + 100), 270, 1100, scale, label="FM乙-1121", flip=True)

    # ---- 4. 电梯 ×2（井道 + 滑门） ----
    _elev(msp, sh_x1 + 200, ix2 - 200, cy + 300, cy + 0.13 * H - 200, scale, "电梯#1")
    _elev(msp, sh_x1 + 200, ix2 - 200, cy - 0.13 * H + 200, cy - 300, scale, "电梯#2")

    # ---- 5. 卫生间（2 隔间 + 洗手台 + 门） ----
    stall_w = (wc_y2 - iy1 - 400) / 2
    for i in range(2):
        yy1 = iy1 + 200 + i * stall_w
        _part_h(msp, ix1 + 300, ix1 + 2000, yy1, t=100, lw=0.18)
    _part_h(msp, ix1 + 300, ix1 + 2000, iy1 + 200 + 2 * stall_w, t=100, lw=0.18)
    # 洗手台（北墙下）
    rect(msp, ix1 + 2400, wc_y2 - 700, ix1 + 4200, wc_y2 - 200, layer="DOOR_WIN", lw=0.18)
    for i in range(2):
        circle(msp, ix1 + 2800 + i * 800, wc_y2 - 450, 180, "DOOR_WIN")
    # 卫生间门（东墙，向内开）
    _fdoor(msp, (wc_x2 - 100, iy1 + 1600), 180, 900, scale)
    text(msp, (ix1 + wc_x2) / 2 + 300, (iy1 + wc_y2) / 2, "卫生间", 2.5, scale, align="C")

    # ---- 6. 设备管井（45° 填充 + 百叶 + FM甲检修门） ----
    h = msp.add_hatch(dxfattribs={"layer": "HATCH"})
    h.paths.add_polyline_path(
        [(mj_x1 + 100, mj_y1 + 100), (ix2 - 100, mj_y1 + 100),
         (ix2 - 100, iy2 - 100), (mj_x1 + 100, iy2 - 100)], is_closed=True)
    h.set_pattern_fill("ANSI31", scale=8)
    # 百叶（南墙，双线）
    bl_x1, bl_x2 = mj_x1 + 400, mj_x1 + 1400
    line(msp, (bl_x1, mj_y1 - 100), (bl_x2, mj_y1 - 100), "DOOR_WIN", lw=0.13)
    line(msp, (bl_x1, mj_y1 - 200), (bl_x2, mj_y1 - 200), "DOOR_WIN", lw=0.13)
    text(msp, (bl_x1 + bl_x2) / 2, mj_y1 - 600, "百叶", 2.5, scale, align="C")
    _fdoor(msp, (ix2 - 1200, mj_y1 + 100), 270, 700, scale, label="FM甲-0601", flip=True)
    text(msp, (mj_x1 + ix2) / 2, (mj_y1 + iy2) / 2 + 300, "设备管井", 2.5, scale, align="C")

    # ---- 7. 房间名（2.5mm 小字，位置避开墙线；文字均为 TEXT 层） ----
    text(msp, (sh_x1 + ix2) / 2 - 0.06 * W, cy, "电梯厅", 2.5, scale, align="C")
    text(msp, cy - 0.02 * W, cy - 0.10 * H, "前室", 2.5, scale, align="C")
    # 总说明小字：不再使用大字遮挡
    text(msp, cy, Y1 - 0.018 * MD.OUT_Y, "既有核心筒（保留）｜电梯厅·楼梯×2·卫生间·设备管井",
         2.5, scale, align="C")


def axis_grid(msp, scale, ext=None):
    ext = ext or MD.AXIS_EXT
    # 轴号圆和文字按A1/A2实际打印清晰度加大；圆心仍严格落在轴线上。
    r = th(4.5, scale) * 0.62
    # 附件三·二：轴网轴线必须用 CENTER 线型（防呆：线型表缺 CENTER 时先建）
    if "CENTER" not in msp.doc.linetypes:
        msp.doc.linetypes.add("CENTER",
                              pattern=[2.0, 1.25, -0.25, 1.25, -0.25, 0.0],
                              description="Center __ . __ .")
    for i, x in enumerate(MD.XS):
        line(msp, (x, -ext), (x, MD.OUT_Y + ext), "AXIS", lt="CENTER")
        circle(msp, x, -ext - r, r)
        text(msp, x, -ext - r - th(1.2, scale), str(i + 1), 3.5, scale, align="C")
        circle(msp, x, MD.OUT_Y + ext + r, r)
        text(msp, x, MD.OUT_Y + ext + r - th(1.2, scale), str(i + 1), 3.5, scale, align="C")
    letters = "ABCDEFGHIJKL"
    for i, y in enumerate(MD.YS):
        line(msp, (-ext, y), (MD.OUT_X + ext, y), "AXIS", lt="CENTER")
        circle(msp, -ext - r, y, r)
        text(msp, -ext - r, y - th(1.2, scale), letters[i], 3.5, scale, align="C")
        circle(msp, MD.OUT_X + ext + r, y, r)
        text(msp, MD.OUT_X + ext + r, y - th(1.2, scale), letters[i], 3.5, scale, align="C")


def wall_seg(msp, w):
    _, _, (x1, y1), (x2, y2), t, h, _ = w
    if x1 == x2:
        fill_rect(msp, [(x1 - t / 2, y1), (x1 + t / 2, y1), (x1 + t / 2, y2), (x1 - t / 2, y2)])
    else:
        fill_rect(msp, [(x1, y1 - t / 2), (x2, y1 - t / 2), (x2, y1 + t / 2), (x1, y1 + t / 2)])


def door(msp, d, scale, show_leaf=True, vertical=None):
    code, _, (x, y), w, h, _ = d
    if vertical is None:
        vertical = ("西墙" in d[1]) or ("东墙" in d[1])   # 竖向墙上的门（D-05/D-06）
    horiz = not vertical
    if horiz:
        line(msp, (x - w / 2, y), (x + w / 2, y), "DOOR_WIN")
        if show_leaf:
            line(msp, (x - w / 2, y), (x - w / 2, y + w), "DOOR_WIN")
            arc(msp, x - w / 2, y, w, 0, 90)
    else:
        line(msp, (x, y - w / 2), (x, y + w / 2), "DOOR_WIN")
        if show_leaf:
            line(msp, (x, y - w / 2), (x + w, y - w / 2), "DOOR_WIN")
            arc(msp, x, y - w / 2, w, 90, 180)


def desk(msp, x1, y1, x2, y2, scale, screen=True):
    rect(msp, x1, y1, x2, y2, layer="FURNITURE", lw=0.25)
    if screen:
        if (y2 - y1) > (x2 - x1):
            line(msp, (x1, y2), (x2, y2), "FURNITURE")
            line(msp, (x1, y1), (x2, y1), "FURNITURE")
        else:
            line(msp, (x2, y1), (x2, y2), "FURNITURE")
            line(msp, (x1, y1), (x1, y2), "FURNITURE")
    rect(msp, x1 + 60, y1 + 60, x1 + 360, y1 + 560, layer="FURNITURE", lw=0.13)


def furn_rect(msp, box, layer="FURNITURE"):
    x1, y1, x2, y2 = box
    rect(msp, x1, y1, x2, y2, layer=layer, lw=0.25)


def plant(msp, x, y, scale, r=300):
    circle(msp, x, y, r, "FURNITURE")


def phone_booth(msp, x, y, scale):
    rect(msp, x, y, x + 1200, y + 1200, layer="FURNITURE", lw=0.25)
    line(msp, (x + 1200, y + 600), (x + 1500, y + 600), "FURNITURE")


def elev_mark(msp, x, y, s, scale, layer="TEXT"):
    L = 3.0 * scale
    poly(msp, [(x, y), (x + L, y), (x, y - L)], layer=layer, close=True)
    text(msp, x + L * 1.2, y - L * 0.6, s, 3.0, scale, layer=layer)


def index_bubble(msp, x, y, s, scale, r=None):
    r = r or th(3.5, scale)
    circle(msp, x, y, r, "DIM")
    text(msp, x, y - th(1.2, scale), s, 3.0, scale, align="C")


def leader(msp, x1, y1, x2, y2, s, scale, layer="TEXT"):
    line(msp, (x1, y1), (x2, y2), layer)
    line(msp, (x2, y2), (x2 + 2.5 * scale, y2 + 1.2 * scale), layer)
    text(msp, x2 + 3.0 * scale, y2 + 0.8 * scale, s, 3.0, scale, layer=layer)


def north_arrow(msp, x, y, scale):
    circle(msp, x, y, th(4.0, scale), "DIM")
    poly(msp, [(x, y + th(3.2, scale)), (x - th(1.4, scale), y - th(2.0, scale)),
               (x, y - th(0.8, scale)), (x + th(1.4, scale), y - th(2.0, scale))],
         layer="DIM", close=True)
    text(msp, x, y - th(3.6, scale), "N", 3.5, scale, align="C")


def legend(msp, x, y, items, scale, title="图例", w_paper=46):
    """图例框：items = [(kind, 文字)]，kind ∈ zone/line/dot"""
    rh = th(5.0, scale)
    n = len(items)
    h = (n + 1) * rh + th(2, scale)
    rect(msp, x, y - h, x + th(w_paper, scale), y, layer="TEXT", lw=0.25)
    text(msp, x + th(2, scale), y - rh + th(1.2, scale), title, 3.5, scale)
    for i, (kind, label) in enumerate(items):
        yy = y - rh * (i + 2) + th(1.2, scale)
        if kind == "zone":
            fill_rect(msp, [(x + th(2, scale), yy), (x + th(8, scale), yy),
                            (x + th(8, scale), yy + th(3, scale)),
                            (x + th(2, scale), yy + th(3, scale))], layer="HATCH", color=9)
        elif kind == "line":
            line(msp, (x + th(2, scale), yy + th(1.5, scale)),
                 (x + th(8, scale), yy + th(1.5, scale)), "DIM")
        elif kind == "dot":
            circle(msp, x + th(5, scale), yy + th(1.5, scale), th(1.2, scale), "MEP")
        text(msp, x + th(10, scale), yy, label, 3.0, scale)


# ---------------------------------------------------------------- 导出
def export(doc, msp, dxf_path, pdf_path=None, png_path=None, paper=(841, 594), dpi=150):
    """导出 DXF + PDF + PNG。PDF/PNG 走黑白正式出图（前景纯黑），
    分区淡彩填充与实体真色（分析动线四色）保留。"""
    doc.saveas(dxf_path)
    if not (pdf_path or png_path):
        return
    from ezdxf.bbox import extents
    from ezdxf.addons.drawing.properties import LayoutProperties
    try:
        bb = extents(msp, fast=False)
    except Exception:
        bb = None
    fig = plt.figure(figsize=(paper[0] / 25.4, paper[1] / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("white")
    # 黑白出图：把全部图层色临时刷成 ACI 7（黑/白语境色，渲染时解析为前景黑）。
    # 只影响本次渲染，DXF 内保留彩色图层（现场打印由 CTB 控制）；
    # 显式 true_color 的实体（分区淡彩填充 / 分析动线四色）不受影响。
    # 注意：必须在 RenderContext 构造前刷——ctx 在 __init__ 里缓存图层属性。
    for layer in doc.layers:
        if layer.dxf.color != 7:
            layer.dxf.color = 7
    ctx = RenderContext(doc)
    out = ezdxf_mpl.MatplotlibBackend(ax)
    lprops = LayoutProperties.from_layout(msp)
    lprops.set_colors("#FFFFFF", "#000000")   # 黑白出图：背景白 / 前景黑
    # 采用轮廓填充渲染，避免新版matplotlib对DXF真彩色填充的兼容错误；
    # 正式DWG/DXF仍保留原始填充，PDF/PNG重点保证墙柱、轴网和尺寸线清晰。
    Frontend(ctx, out, Configuration(hatch_policy=HatchPolicy.SHOW_OUTLINE)).draw_layout(
        msp, finalize=True, layout_properties=lprops)
    # ezdxf finalize() 会按数据宽高比把 figure 改回去（plt.figaspect），
    # 这里在保存前按纸张尺寸改回来，否则 PDF 页面与 PNG 分辨率全错
    fig.set_size_inches(paper[0] / 25.4, paper[1] / 25.4)
    if bb is not None:
        mx = max((bb.extmax.x - bb.extmin.x) * 0.02, 100)
        my = max((bb.extmax.y - bb.extmin.y) * 0.02, 100)
        ax.set_xlim(bb.extmin.x - mx, bb.extmax.x + mx)
        ax.set_ylim(bb.extmin.y - my, bb.extmax.y + my)
    ax.set_autoscale_on(False)   # 锁死视口：防 finalize 的 autoscale 回改边界
    ax.set_aspect("equal")
    ax.axis("off")
    if pdf_path:
        fig.savefig(pdf_path)
    if png_path:
        fig.savefig(png_path, dpi=dpi)
    plt.close(fig)


# ---------------------------------------------------------------- 表格与图例（同学版补充）
def table(msp, x, y_top, col_w, rows, S, rh=13.0, fs=2.5, header=True, title=None):
    """通用表格：col_w 纸面 mm；rows = [[str,...],...]；返回底部 y（模型 mm）"""
    W = sum(col_w)
    rh_m = rh * S
    y = y_top
    if title:
        text(msp, x, y + 200, title, 4.0, S)
        y -= 700
    if header:
        rect(msp, x, y - rh_m, x + W * S, y, layer="TEXT", lw=0.35)
        cx = x
        for j, w in enumerate(col_w):
            if j:
                line(msp, (cx, y - rh_m), (cx, y), "TEXT")
            text(msp, cx + w * S / 2, y - rh_m + rh_m * 0.28, rows[0][j], fs, S, align="C")
            cx += w * S
        y -= rh_m
        body = rows[1:]
    else:
        body = rows
    for row in body:
        rect(msp, x, y - rh_m, x + W * S, y, layer="TEXT", lw=0.13)
        cx = x
        for j, w in enumerate(col_w):
            if j:
                line(msp, (cx, y - rh_m), (cx, y), "TEXT")
            text(msp, cx + w * S / 2, y - rh_m + rh_m * 0.28, str(row[j]), fs, S, align="C")
            cx += w * S
        y -= rh_m
    return y


def legend_items(msp, x, y_top, items, S, title="图例", w_paper=52, rh=6.5, fs=3.0):
    """图例框：items = [(kind, label)]，kind ∈ rect/line/dot/zone/wall"""
    rh_m = rh * S
    n = len(items)
    h = (n + 1) * rh_m + 0.8 * S
    rect(msp, x, y_top - h, x + w_paper * S, y_top, layer="TEXT", lw=0.35)
    text(msp, x + 2 * S, y_top - rh_m + 0.3 * S, title, 3.5, S)
    for i, (kind, label) in enumerate(items):
        yy = y_top - rh_m * (i + 2) + 0.3 * S
        sx, ex = x + 2 * S, x + 8 * S
        # 图例符号一律画在 TEXT 层：避免污染 FURNITURE / WALL / HATCH 业务层
        # （否则图例矩形会被误判为「家具越界」，HATCH 图例块会被误判为实心填充）
        if kind == "rect":
            rect(msp, sx, yy, ex, yy + 3 * S, layer="TEXT", lw=0.25)
        elif kind == "wall":
            fill_rect(msp, [(sx, yy), (ex, yy), (ex, yy + 3 * S), (sx, yy + 3 * S)],
                      layer="TEXT", color=7)
        elif kind == "line":
            line(msp, (sx, yy + 1.5 * S), (ex, yy + 1.5 * S), "TEXT")
        elif kind == "dot":
            circle(msp, (sx + ex) / 2, yy + 1.5 * S, 1.2 * S, "TEXT")
        elif kind == "zone":
            fill_rect(msp, [(sx, yy), (ex, yy), (ex, yy + 3 * S), (sx, yy + 3 * S)],
                      layer="TEXT", color=9)
        text(msp, x + 10 * S, yy, label, fs, S)
    return y_top - h
