# -*- coding: utf-8 -*-
"""
同学版 · 7 张补充平面图生成器（PL-00/03/10/11/12/13/14）
==========================================================
来源：V3.3 最终版原版图纸清单（02_施工图/01_平面）中有、而同学版管线未覆盖的 7 张。
复用 build_9plans_同学版_v2 的全部底座（base_plan / RightPanel / zone_labels /
three_level_dims / _hatch_rect / _text_width），保证图面语言与 9 张平面完全一致。

图号清单：
  PL-00 图纸目录      —— 全套 34 张图清单表（无底图）
  PL-03 功能分区图    —— 六类功能填充 + 面积标注
  PL-10 消防末端图    —— 喷淋110 / 烟感24 / 消火栓 / 灭火器 / 疏散口
  PL-11 平面索引图    —— EL/DT/SD 索引符号 + 索引明细表
  PL-12 动线设计图    —— 环廊一级动线 + 分区二级动线
  PL-13 配套设施图    —— 电话亭/打印/茶水设备/快递柜等点位
  PL-14 地面排版图    —— 地毯 500×500 / 柔光砖 750×1500 真实模数排版
"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ezdxf
from ezdxf.bbox import extents

import student_master as MD
import student_cad as cl
import student_furniture as SF
import build_9plans_同学版_v2 as B9

try:
    from config import ROOT as BASE
except ImportError:
    BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "02_平面图_四格式")
os.makedirs(OUT, exist_ok=True)

S = MD.SCALE_PLAN
TXT_H = B9.TXT_H
TXT_H_SMALL = B9.TXT_H_SMALL
TXT_H_BIG = B9.TXT_H_BIG
ZONE_BY_CODE = B9.ZONE_BY_CODE

# 六类功能 → 填充模式（角度, 步距mm）；交通（环廊）不填充
CLASS_HATCH = {
    "开放办公": (45, 600),
    "会议": (90, 600),
    "接待": (0, 600),
    "后勤": (45, 300),
    "管理": (135, 600),
    "交通": None,
}


# ================================================================ 通用小件
def _arrow(msp, p1, p2, layer="MEP", head=400):
    """带实心三角箭头的流线段。"""
    cl.line(msp, p1, p2, layer)
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(dx, dy)
    if L == 0:
        return
    ux, uy = dx / L, dy / L
    px, py = -uy, ux
    tip = p2
    b1 = (p2[0] - ux * head + px * head * 0.42, p2[1] - uy * head + py * head * 0.42)
    b2 = (p2[0] - ux * head - px * head * 0.42, p2[1] - uy * head - py * head * 0.42)
    cl.fill_rect(msp, [tip, b1, b2], layer=layer)


def _index_symbol(msp, x, y, code, direct="E", r=650):
    """详图索引符号：圆 + 图号 + 指向三角（direct=N/E/S/W）。"""
    cl.circle(msp, x, y, r, "DIM")
    cl.circle(msp, x, y, r * 0.62, "DIM")
    cl.text(msp, x, y, code, TXT_H_SMALL, S, align="C", layer="DIM")
    d = r * 1.15
    tips = {"E": (x + d, y), "W": (x - d, y), "N": (x, y + d), "S": (x, y - d)}
    tx, ty = tips[direct]
    _arrow(msp, (x, y), (tx, ty), layer="DIM", head=350)


def _sprinkler(msp, x, y):
    """喷淋头：十字 + 圆。"""
    cl.line(msp, (x - 240, y), (x + 240, y), "MEP")
    cl.line(msp, (x, y - 240), (x, y + 240), "MEP")
    cl.circle(msp, x, y, 120, "MEP")


def _smoke(msp, x, y):
    """烟感：圆 + 内圆。"""
    cl.circle(msp, x, y, 130, "MEP")
    cl.circle(msp, x, y, 55, "MEP")


def _extinguisher(msp, x, y, label):
    cl.circle(msp, x, y, 110, "MEP")
    cl.text(msp, x, y - 800, label, TXT_H_SMALL, S, align="C")


def _exit_mark(msp, x, y, s="疏散口"):
    cl.rect(msp, x - 450, y - 250, x + 450, y + 250, layer="MEP", lw=0.30)
    cl.text(msp, x, y, s, TXT_H_SMALL, S, align="C")
    _arrow(msp, (x, y + 700), (x, y + 320), layer="MEP", head=300)


# ================================================================ 各图
def gen_PL00(msp, S):
    """图纸目录：全套 34 张清单，分两栏各 17 行。"""
    rows_all = [[c, n, r, ("A1" if f.startswith("A1") else "A2"), q]
                for (c, n, r, f, sub, q) in MD.DRAWINGS]
    half = (len(rows_all) + 1) // 2
    left, right = rows_all[:half], rows_all[half:]
    col_w = [22, 62, 18, 14, 12]           # 图号/图名/比例/图幅/序号（图纸mm，总128）
    y = 40000
    cl.text(msp, 0, y + 2500, "图纸目录", TXT_H_BIG + 2.0, S, align="C")
    cl.text(msp, 0, y + 800, "共 %d 张｜版次 %s｜日期 %s" % (len(rows_all), MD.REVISION, MD.DATE),
            TXT_H, S, align="C")
    head = ["图号", "图名", "比例", "图幅", "序号"]
    ybot = cl.table(msp, -14000, y, col_w, [head] + left, S, rh=9.0, fs=3.0)
    cl.table(msp, 1500, y, col_w, [head] + right, S, rh=9.0, fs=3.0)
    cl.text(msp, -14000, ybot - 2200,
            "说明：1. 本目录按图号升序排列，PL 平面 / EL 立面 / DT 节点大样 / SD 详图四大类；"
            "2. 各图均含 DXF/DWG/PNG/PDF 四格式；",
            TXT_H_SMALL, S)
    cl.text(msp, -14000, ybot - 3400,
            "　　　3. 图签信息全套统一（设计人/日期见各图图签）；4. 图纸依据《附件三 制图规范模板》绘制。",
            TXT_H_SMALL, S)
    cl.north_arrow(msp, -2600, 46200, S)


def gen_PL03(msp, S):
    """功能分区图：六类填充 + 面积标注 + 分类明细表。"""
    B9.base_plan(msp, furniture=False, dims=False)
    for z in MD.ZONES:
        code, name, x1, y1, x2, y2, area, cat = z
        hp = CLASS_HATCH.get(cat)
        if hp:
            ang, step = hp
            B9._hatch_rect(msp, x1, y1, x2, y2, step=step, angle=ang)
        cl.rect(msp, x1, y1, x2, y2, layer="HATCH", lw=0.30)
    B9.zone_labels(msp)
    # 面积标注（第二行，位于分区标签下方）
    for z in MD.ZONES:
        code, name, x1, y1, x2, y2, area, cat = z
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        cl.text(msp, cx, cy - 700, "%.1f ㎡" % area, TXT_H_SMALL, S, align="C")
    # 环廊标注（放环廊南腿中部，避开 Z1 标签与分区面积标注）
    cl.text(msp, (MD.CORE_X1 + MD.CORE_X2) / 2, MD.CORE_Y1 / 2,
            "环廊 %.1f ㎡" % MD.CORRIDOR_AREA, TXT_H_SMALL, S, align="C", rotation=0)
    rp = B9.RightPanel(msp)
    rows = [["区号", "名称", "类别", "面积㎡"]]
    for z in MD.ZONES:
        rows.append([z[0], z[1], z[7], "%.1f" % z[6]])
    rows.append(["—", "环廊主通道", "交通", "%.1f" % MD.CORRIDOR_AREA])
    rp.title("功能分区明细表")
    rp.table(B9.RC_TBL_W, rows)
    rp.legend([
        ("zone", "开放办公（45° 斜线）"),
        ("zone", "会议（竖线 90°）"),
        ("zone", "接待（横线 0°）"),
        ("zone", "后勤（密斜线 45°@300）"),
        ("zone", "管理（反斜线 135°）"),
        ("zone", "交通（环廊，不填充）"),
    ])
    rp.title("说明：", TXT_H)
    rp.lines([
        "1. 本图按功能六类划分，物理边界与 PL-01 一致；",
        "2. 面积为轴线净面积，分项之和与 PL-01 明细闭合；",
        "3. 逻辑子区（Z2a/Z2b 等）属家具划分，不单独设色；",
        "4. 核心筒为既有交通核，不属于本次设计范围。"])


def gen_PL10(msp, S):
    """消防末端图：喷淋 110 / 烟感 24 / 消火栓 / 灭火器 / 疏散口。"""
    B9.base_plan(msp, furniture=True, dims=False)
    n_sp = 0
    for (x, y) in MD.SPRINKLERS:
        _sprinkler(msp, x, y)
        n_sp += 1
    n_sk = 0
    for (x, y) in MD.SMOKES:
        _smoke(msp, x, y)
        n_sk += 1
    # 消火栓 2 个：环廊西腿 + 南腿
    hydr = [(MD.CORE_X1 - 1200, (MD.CORE_Y1 + MD.CORE_Y2) / 2),
            ((MD.CORE_X1 + MD.CORE_X2) / 2, MD.CORE_Y1 - 1200)]
    for i, (x, y) in enumerate(hydr, 1):
        cl.rect(msp, x - 350, y - 250, x + 350, y + 250, "MEP", lw=0.30)
        cl.line(msp, (x - 350, y - 250), (x + 350, y + 250), "MEP")
        # 南腿消火栓（i=2）紧邻核心筒长标签，文字放图块下方避让
        ty = y - 1000 if i == 2 else y + 550
        cl.text(msp, x, ty, "消火栓 H-%02d" % i, TXT_H_SMALL, S, align="C")
    # 灭火器 4 组
    ext = [(2200, 7400, "灭火器 M1"), (35800, 9800, "灭火器 M2"),
           (30600, 2000, "灭火器 M3"), (39500, 17500, "灭火器 M4")]
    for x, y, s in ext:
        _extinguisher(msp, x, y, s)
    # 疏散口：前台主入口 + 大会议门
    _exit_mark(msp, 41600, 19000, "主疏散口")
    _exit_mark(msp, 35380, 33300, "疏散口②")
    B9.zone_labels(msp)
    rp = B9.RightPanel(msp)
    rp.legend([
        ("dot", "喷淋头（中危险Ⅰ级）"),
        ("dot", "烟感探测器"),
        ("rect", "消火栓（环廊 2 处）"),
        ("dot", "灭火器 Group"),
        ("rect", "疏散口指示"),
    ])
    rp.title("消防末端数量表")
    rp.table([26, 40, 26], [
        ["末端", "数量", "规范依据"],
        ["喷淋头", "%d 个" % n_sp, "12.5㎡/个"],
        ["烟感", "%d 只" % n_sk, "5.8m 半径"],
        ["消火栓", "2 套", "环廊布置"],
        ["灭火器", "4 组", "每点 2 具"],
    ])
    rp.title("说明：", TXT_H)
    rp.lines([
        "1. 喷淋按中危险Ⅰ级，间距≤3.4m，距墙≤1.7m；",
        "2. 烟感保护半径 5.8m，单只 60~80㎡；",
        "3. 核心筒喷淋由原系统覆盖，本图不重复布点；",
        "4. 疏散距离与出口宽度经《规范自查清单》核验；",
        "5. 应急照明与出口指示详见 PL-07 回路说明。"])


def gen_PL11(msp, S):
    """平面索引图：EL 立面索引 7 + DT 节点索引 6 + SD 详图索引 5。"""
    B9.base_plan(msp, furniture=True, dims=False)
    # EL 立面索引（圆放在分区内靠索引墙一侧，箭头指向观看方向）
    el_idx = [
        ("EL-01", "E", 36000, 19000),
        ("EL-02", "W", 37000, 36000),
        ("EL-03", "N", 36500, 5000),
        ("EL-04", "W", 37000, 26000),
        ("EL-05", "E", 4500, 4000),
        ("EL-06", "S", 18000, 6800),
        ("EL-07", "E", 3600, 39000),
    ]
    for code, d, x, y in el_idx:
        _index_symbol(msp, x, y, code, direct=d)
    # DT 节点索引（位置=构造发生处）
    dt_idx = [
        ("DT-01", "E", 41000, 23000),
        ("DT-02", "N", 4500, 8100),
        ("DT-03", "N", 34500, 12000),
        ("DT-04", "S", 1600, 16000),
        ("DT-05", "E", 37000, 30500),
        ("DT-06", "W", 29400, 4000),
    ]
    for code, d, x, y in dt_idx:
        _index_symbol(msp, x, y, code, direct=d, r=560)
    # SD 详图索引
    sd_idx = [
        ("SD-01", "S", 2500, 20000),
        ("SD-02", "S", 3700, 7300),
        ("SD-03", "W", 35200, 35500),
        ("SD-04", "N", 29600, 33600),
        ("SD-05", "N", 35380, 8400),
    ]
    for code, d, x, y in sd_idx:
        _index_symbol(msp, x, y, code, direct=d, r=560)
    B9.zone_labels(msp)
    rp = B9.RightPanel(msp)
    rp.title("索引明细表")
    rows = [["索引", "指向", "详图内容", "详见"]]
    for code, name, ratio, frame, sub, seq in MD.DRAWINGS:
        if code.startswith(("EL", "DT", "SD")):
            rows.append([code, "—", name, "%s/%s" % (frame.split("-")[0], seq)])
    rp.table([14, 10, 50, 18], rows)
    rp.title("说明：", TXT_H)
    rp.lines([
        "1. 索引符号圆内为详图号，箭头为观看方向；",
        "2. 立面索引均指向该房间主观察面（详见 EL 图）；",
        "3. 节点索引位置=构造交接处，比例 1:10；",
        "4. 本图索引与 PL-00 目录一一对应，无悬空索引。"])


def gen_PL12(msp, S):
    """动线设计图：环廊一级动线 + 分区二级动线 + 入口流线。"""
    B9.base_plan(msp, furniture=False, dims=False)
    # 一级动线：环廊中线（核心筒外扩 1200）闭环
    mx1, my1 = MD.CORE_X1 - 1200, MD.CORE_Y1 - 1200
    mx2, my2 = MD.CORE_X2 + 1200, MD.CORE_Y2 + 1200
    ring = [(mx1, my1), (mx2, my1), (mx2, my2), (mx1, my2), (mx1, my1)]
    for i in range(len(ring) - 1):
        p1, p2 = ring[i], ring[i + 1]
        cl.line(msp, p1, p2, "MEP")
        _arrow(msp, p1, p2, layer="MEP", head=500)
    # 入口流线：主入口（东墙 Z1）→ 前台 → 环廊
    _arrow(msp, (42500, 19000), (36500, 19000), layer="MEP")
    _arrow(msp, (36500, 19000), (36500, 21000), layer="MEP")
    _arrow(msp, (36500, 21000), (mx2, 21000), layer="MEP")
    # 二级动线：环廊 → 各分区入口（短分支）
    branches = [
        ((mx1, 20000), (8000, 20000)),      # → Z8
        ((mx1, 35000), (4000, 35000)),      # → Z7
        ((mx2, 37000), (36000, 36500)),     # → Z2
        ((mx2, 5000), (35600, 5000)),       # → Z3
        ((18000, my1), (18000, 3500)),      # → Z9
        ((18000, my2), (18000, 35500)),     # → Z10
        ((mx1, 4000), (5000, 4000)),        # → Z11
    ]
    for p1, p2 in branches:
        _arrow(msp, p1, p2, layer="MEP", head=380)
    # 环廊宽度标注
    cl.dim_v(msp, MD.CORE_Y2, MD.CORE_Y2 + 2400, mx2 - 600, mx2 + 200,
             label="2400", scale=S)
    cl.text(msp, mx2 + 1800, MD.CORE_Y2 + 1200, "环廊宽 2400", TXT_H_SMALL, S)
    B9.zone_labels(msp)
    rp = B9.RightPanel(msp)
    rp.legend([
        ("line", "一级动线（环廊 2400）"),
        ("line", "二级动线（分支≥1500）"),
        ("rect", "主入口（东墙 Z1）"),
    ])
    rp.title("动线分级：", TXT_H)
    rp.lines([
        "一级：环廊主通道 2400 宽，双向通行，",
        "　　连接全部功能分区入口；",
        "二级：环廊至各分区分支，净宽≥1500；",
        "三级：开放区内工位通道 ≥1200（见 PL-01）。",
        "",
        "访客动线：主入口→前台→等候→洽谈；",
        "员工动线：主入口→环廊→工位/协作区；",
        "后勤动线：货运→Z12 储物→茶水/文印，",
        "　　　　　与访客动线基本不交叉。"])
    rp.title("说明：", TXT_H)
    rp.lines([
        "1. 本图流线为示意，宽度以各平面图尺寸为准；",
        "2. 疏散动线与消防末端见 PL-10；",
        "3. 动线组织经《附件X2 方案比选报告》论证。"])


def gen_PL13(msp, S):
    """配套设施图：电话亭/打印/茶水设备/快递柜/清洁/饮水点位。"""
    B9.base_plan(msp, furniture=True, dims=False)
    # (x, y, 名称, 规格, 左侧标签)：东侧点位（x>30000）标签放左侧，
    # 避免伸进右轴号列（x≈38479）与右侧栏；Q-2 原坐标 39000 超出外框 37000，已挪回。
    pts = [
        (35500, 13000, "电话亭 T-1", "1200×1200×2300", True),
        (35500, 14700, "电话亭 T-2", "1200×1200×2300", True),
        (35600, 9300, "打印复印 P-1", "复合机 1200×800", True),
        (36000, 9600, "碎纸机 S-1", "400×500", True),
        (7500, 1350, "冰箱 R-1", "700×700", False),
        (6300, 1900, "微波炉 W-1", "600×450", False),
        (6700, 2600, "咖啡机 C-1", "400×400", False),
        (1000, 7300, "净水点 Q-1", "台盆就近", False),
        (30500, 2000, "快递柜 E-1", "1200×450×1800", False),
        (30200, 5800, "清洁柜 K-1", "600×450", False),
        (34800, 11500, "饮水点 Q-2", "立式直饮机", True),
        (26800, 34400, "共享打印 P-2", "A3 复合机", False),
    ]
    for x, y, name, spec, left in pts:
        cl.circle(msp, x, y, 150, "MEP")
        if left:
            cl.line(msp, (x - 150, y), (x - 2200, y + 900), "DIM")
            cl.text(msp, x - 2300, y + 900, "%s（%s）" % (name, spec),
                    TXT_H_SMALL, S, align="R")
        else:
            cl.line(msp, (x + 150, y), (x + 2200, y + 900), "DIM")
            cl.text(msp, x + 2300, y + 900, "%s（%s）" % (name, spec),
                    TXT_H_SMALL, S, align="L")
    B9.zone_labels(msp)
    rp = B9.RightPanel(msp)
    rp.title("配套设施明细表")
    rp.table([12, 34, 16, 30], [
        ["编号", "设施", "数量", "位置"],
        ["T", "声学电话亭", "2", "Z6"],
        ["P", "打印复印", "2", "Z5 / Z10"],
        ["S", "碎纸机", "1", "Z5"],
        ["R/W/C", "冰箱/微波炉/咖啡机", "各1", "Z11"],
        ["Q", "饮水点", "2", "Z11 / Z1"],
        ["E", "快递柜", "1", "Z12"],
        ["K", "清洁柜", "1", "Z12"],
    ])
    rp.title("说明：", TXT_H)
    rp.lines([
        "1. 电话亭为成品件，自带照明与排风，",
        "　　不接入吊顶系统；",
        "2. 打印区预留专用插座（见 PL-08 W7 回路）；",
        "3. 茶水设备给排水点位见 PL-09；",
        "4. 快递柜设于 Z12 物流暂存区，靠墙明装；",
        "5. 全部设施落位不超出所属分区边界。"])


def gen_PL14(msp, S):
    """地面排版图：地毯 500×500 / 柔光砖 750×1500 真实模数排版。"""
    B9.base_plan(msp, furniture=False, dims=False)
    carpet = ["Z8", "Z8b", "Z9", "Z10", "Z2", "Z3", "Z3b"]
    tile = ["Z1", "Z4", "Z11"]
    # 地毯区：500 模数网格（横竖）
    for code in carpet:
        z = ZONE_BY_CODE[code]
        x1, y1, x2, y2 = z[2], z[3], z[4], z[5]
        x = x1 + 500
        while x < x2:
            cl.line(msp, (x, y1), (x, y2), "HATCH")
            x += 500
        y = y1 + 500
        while y < y2:
            cl.line(msp, (x1, y), (x2, y), "HATCH")
            y += 500
    # 柔光砖区：750×1500 横铺网格
    for code in tile:
        z = ZONE_BY_CODE[code]
        x1, y1, x2, y2 = z[2], z[3], z[4], z[5]
        y = y1 + 750
        while y < y2:
            cl.line(msp, (x1, y), (x2, y), "HATCH")
            y += 750
        x = x1 + 1500
        while x < x2:
            cl.line(msp, (x, y1), (x, y2), "HATCH")
            x += 1500
    # 起铺点（对角三角标记）+ 注
    for code in carpet[:1] + tile[:1]:
        z = ZONE_BY_CODE[code]
        x1, y1 = z[2], z[3]
        cl.fill_rect(msp, [(x1 + 300, y1 + 300), (x1 + 900, y1 + 300),
                           (x1 + 300, y1 + 900)], layer="HATCH", color=9)
        cl.text(msp, x1 + 1500, y1 + 500, "起铺点（整砖起铺，非整砖≥1/3 排至暗边）",
                TXT_H_SMALL, S, align="L")
    B9.zone_labels(msp)
    rp = B9.RightPanel(msp)
    rp.legend([
        ("zone", "方块地毯 500×500 模数网格"),
        ("zone", "柔光砖 750×1500 横铺网格"),
        ("rect", "起铺点标记"),
    ])
    rp.title("排版参数表")
    rp.table([16, 40, 36], [
        ["区域", "材料/规格", "排版方式"],
        ["Z8 Z8b Z9 Z10", "方块地毯 500×500×8", "整砖起铺 中间对齐"],
        ["Z2 Z3 Z3b", "方块地毯 500×500×8", "整砖起铺 中间对齐"],
        ["Z1 Z4 Z11", "柔光砖 750×1500×10", "横铺 非整砖≥1/3"],
        ["环廊", "柔光砖 750×1500×10", "横铺 对缝贯通"],
    ])
    rp.title("说明：", TXT_H)
    rp.lines([
        "1. 本图为排版示意，网格间距=材料真实模数；",
        "2. 地毯区自流平基层 20 厚（见 SD-04）；",
        "3. 非整砖宽度≥1/3 整砖，不足时两侧均分；",
        "4. 门口以门槛石过渡，高差 2~5mm（见 SD-04）；",
        "5. 材料用量按本排版核算，见材料表。"])


BUILDERS = {
    "PL-00": ("图纸目录", gen_PL00),
    "PL-03": ("功能分区图", gen_PL03),
    "PL-10": ("消防末端图", gen_PL10),
    "PL-11": ("平面索引图", gen_PL11),
    "PL-12": ("动线设计图", gen_PL12),
    "PL-13": ("配套设施图", gen_PL13),
    "PL-14": ("地面排版图", gen_PL14),
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
