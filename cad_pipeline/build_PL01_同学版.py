# -*- coding: utf-8 -*-
"""
PL-01 平面布置图（A-1 开放办公区 · 四周环带）
依据：20_CAD分区刻画与家具布置手册.md（§1 坐标、§2 分区表、§3 逐区卡、§4 图元库、§5 图层）
输出：PL-01_平面布置图_A1.dxf / .svg / .png / inserts.jsonl
环境：<D盘>\\UserFiles\\Desktop\\CAD_AI连接器\\Scripts\\python.exe（ezdxf 1.4.4 + PIL）
"""
import os, math, json

# 输出目录：落在 cad_pipeline 包内（可整体随包移动），不再写死外部盘符
from config import ROOT as _PIPE_ROOT
OUT = os.path.normpath(os.path.join(str(_PIPE_ROOT), "01_PL-01_PoC"))
NAME = "PL-01_平面布置图_A1_同学版"

import ezdxf
from ezdxf.enums import TextEntityAlignment
import ezdxf.units

# ---------------------------------------------------------------- 图层（9 层红线）
LAYERS = [
    ("WALL",      7, 50),
    ("COLUMN",    7, 50),
    ("DOOR_WIN",  4, 25),
    ("FURNITURE", 4, 25),
    ("MEP",       6, 9),
    ("DIM",       3, 9),
    ("TEXT",      2, 9),
    ("HATCH",     9, 9),
    ("FRAME",     7, 9),
]

# ---------------------------------------------------------------- 场景（DXF + PNG 双写）
SHAPES = []          # [(kind, data, layer)]  kind: L/C/A/P
BLOCK_PRIMS = {}     # name -> [(kind, data)]
_cur_block = [None]


def _emit(kind, data):
    if _cur_block[0] is None:
        SHAPES.append((kind, data, _cur_layer[0]))
        tgt = MPS
    else:
        BLOCK_PRIMS.setdefault(_cur_block[0], []).append((kind, data))
        tgt = BLOCKS[_cur_block[0]]
    return tgt, kind, data


_cur_layer = ["WALL"]


def layer(n):
    _cur_layer[0] = n


def L(x1, y1, x2, y2):
    tgt, kind, data = _emit("L", (x1, y1, x2, y2))
    tgt.add_line((x1, y1), (x2, y2), dxfattribs={"layer": "0" if _cur_block[0] else n_layer()})


def C(cx, cy, r):
    tgt, kind, data = _emit("C", (cx, cy, r))
    tgt.add_circle((cx, cy), r, dxfattribs={"layer": "0" if _cur_block[0] else n_layer()})


def A(cx, cy, r, a1, a2):
    tgt, kind, data = _emit("A", (cx, cy, r, a1, a2))
    tgt.add_arc((cx, cy), r, a1, a2, dxfattribs={"layer": "0" if _cur_block[0] else n_layer()})


def n_layer():
    return _cur_layer[0]


def R(x1, y1, x2, y2):
    L(x1, y1, x2, y1); L(x2, y1, x2, y2); L(x2, y2, x1, y2); L(x1, y2, x1, y1)


def RR(x1, y1, x2, y2, r=60):
    """圆角矩形（用 4 段直线 + 4 段圆弧近似，r 为圆角半径）"""
    L(x1 + r, y1, x2 - r, y1); A(x2 - r, y1 + r, r, 270, 360)
    L(x2, y1 + r, x2, y2 - r); A(x2 - r, y2 - r, r, 0, 90)
    L(x2 - r, y2, x1 + r, y2); A(x1 + r, y2 - r, r, 90, 180)
    L(x1, y2 - r, x1, y1 + r); A(x1 + r, y1 + r, r, 180, 270)


# ---------------------------------------------------------------- DXF 文档
doc = ezdxf.new("R2010", setup=True)
doc.units = ezdxf.units.MM
doc.header["$INSUNITS"] = 4
doc.header["$MEASUREMENT"] = 1
for nm, col, lw in LAYERS:
    if nm not in doc.layers:
        doc.layers.add(nm, color=col, lineweight=lw)

MPS = doc.modelspace()
BLOCKS = {}

# ================================================================ 家具图元库
# 约定：矩形块基点 = 左下角；圆块基点 = 圆心。块内图元一律画在 0 层。
FURN = {}


def blk(name):
    def deco(fn):
        FURN[name] = fn
        return fn
    return deco


@blk("FUR-DESK-1400")
def _(w=1400, h=700):
    RR(0, 0, w, h, 40)
    L(0, h - 130, w, h - 130)            # 后挡板线
    C(w / 2, h / 2, 35)                  # 走线孔


@blk("FUR-DESK-1800")
def _(w=1800, h=800):
    RR(0, 0, w, h, 40)
    L(0, h - 150, w, h - 150)
    C(w * 0.72, h / 2, 40)


def _chair(w, h, back=True, arms=False, star=False):
    RR(0, 0, w, h, 60)
    if back:
        L(0, h - 90, w, h - 90)
    if arms:
        L(60, 90, 60, h - 90); L(w - 60, 90, w - 60, h - 90)
    if star:
        C(w / 2, h / 2, 60)
        for a in (0, 72, 144, 216, 288):
            L(w / 2, h / 2, w / 2 + 150 * math.cos(math.radians(a)),
              h / 2 + 150 * math.sin(math.radians(a)))


@blk("FUR-CHAIR-TASK")
def _(w=600, h=600):
    _chair(w, h, arms=True, star=True)


@blk("FUR-CHAIR-MEET")
def _(w=600, h=600):
    _chair(w, h, arms=True)


@blk("FUR-CHAIR-GUEST")
def _(w=600, h=600):
    _chair(w, h)


@blk("FUR-CHAIR-DINING")
def _(w=450, h=450):
    _chair(w, h)


@blk("FUR-CHAIR-EXEC")
def _(w=650, h=650):
    _chair(w, h, arms=True, star=True)
    L(90, h - 150, w - 90, h - 150)      # 头枕


@blk("FUR-SCREEN-23400")
def _(w=100, h=23400):
    L(0, 0, 0, h); L(w, 0, w, h)
    y = 1800
    while y < h:
        L(0, y, w, y); y += 1800


@blk("FUR-SCREEN-18000")
def _(w=100, h=18000):
    L(0, 0, 0, h); L(w, 0, w, h)
    y = 1800
    while y < h:
        L(0, y, w, y); y += 1800


@blk("FUR-PED-400")
def _(w=400, h=500):
    R(0, 0, w, h)
    for y in (h / 3, 2 * h / 3):
        L(0, y, w, y)


@blk("FUR-MON-600")
def _(w=600, h=200):
    R(0, 0, w, h)
    L(w * 0.15, h * 0.35, w * 0.85, h * 0.35)


@blk("FUR-KB-450")
def _(w=450, h=150):
    RR(0, 0, w, h, 15)


@blk("FUR-LAMP")
def _(r=100):
    C(0, 0, r); L(-r, 0, r, 0); L(0, -r, 0, r)


@blk("FUR-FLOORBOX")
def _(w=120, h=120):
    R(0, 0, w, h); L(0, 0, w, h); L(0, h, w, 0)


def _sofa(w, h, seats):
    R(0, 0, w, h)
    L(0, 150, w, 150)                    # 座面前沿
    for i in range(1, seats):
        L(w * i / seats, 150, w * i / seats, h)


@blk("FUR-SOFA-3P")
def _(w=2100, h=850):
    _sofa(w, h, 3)


@blk("FUR-SOFA-2P")
def _(w=1600, h=800):
    _sofa(w, h, 2)


@blk("FUR-SOFA-1P")
def _(w=800, h=800):
    _sofa(w, h, 1)


@blk("FUR-TABLE-900")
def _(w=900, h=500):
    RR(0, 0, w, h, 60)


@blk("FUR-TABLE-1200")
def _(w=1200, h=600):
    RR(0, 0, w, h, 60)


@blk("FUR-TABLE-2400")
def _(w=2400, h=900):
    RR(0, 0, w, h, 80)


@blk("FUR-TABLE-1800")
def _(w=1800, h=750):
    RR(0, 0, w, h, 60)


def _round(d):
    r = d / 2
    C(0, 0, r); L(-r, 0, r, 0); L(0, -r, 0, r)


@blk("FUR-ROUND-800")
def _(d=800):
    _round(d)


@blk("FUR-ROUND-900")
def _(d=900):
    _round(d)


@blk("FUR-ROUND-1000")
def _(d=1000):
    _round(d)


def _meet(w, h):
    RR(0, 0, w, h, 100)
    L(w / 2, 0, w / 2, h)                # 走线槽中线


@blk("FUR-MEET-3000")
def _(w=3000, h=1200):
    _meet(w, h)


@blk("FUR-MEET-4800")
def _(w=4800, h=1600):
    _meet(w, h)


@blk("FUR-COUNTER-5400")
def _(w=5400, h=600):
    R(0, 0, w, h)
    L(0, h - 60, w, h - 60)              # 台面前沿
    x = 600
    while x < w:
        L(x, 0, x, h - 60); x += 600
    L(0, 40, w, 40)                      # 踢脚线


@blk("FUR-UPPER-5400")
def _(w=5400, h=350):
    L(0, 0, w, 0); L(0, h, w, h)
    x = 0
    while x < w:
        L(x, 0, x, h); x += 300


@blk("FUR-SINK-900")
def _(w=900, h=450):
    R(0, 0, w, h)
    R(60, 60, w / 2 - 30, h - 60)
    R(w / 2 + 30, 60, w - 60, h - 60)
    C(w / 2, h - 60, 35)


@blk("FUR-FRIDGE-700")
def _(w=700, h=700):
    R(0, 0, w, h); L(0, h - 120, w, h - 120); L(w - 60, h - 120, w - 60, h)


@blk("FUR-WATER-400")
def _(w=400, h=400):
    R(0, 0, w, h); C(w / 2, h / 2, 130); C(w / 2, h / 2, 40)


@blk("FUR-MICRO-600")
def _(w=600, h=400):
    R(0, 0, w, h); L(0, h - 80, w, h - 80); R(w - 120, 20, w - 20, h - 100)


@blk("FUR-COFFEE-400")
def _(w=400, h=350):
    R(0, 0, w, h); R(40, h - 90, w - 40, h - 20)


def _cab(w, h):
    R(0, 0, w, h); L(w / 2, 0, w / 2, h)


@blk("FUR-CAB-900")
def _(w=900, h=450):
    _cab(w, h)


@blk("FUR-CAB-1200")
def _(w=1200, h=450):
    _cab(w, h)


@blk("FUR-SHELF-1200")
def _(w=1200, h=350):
    R(0, 0, w, h)
    for i in (1, 2, 3):
        L(0, h * i / 4, w, h * i / 4)


@blk("FUR-RACK-1200")
def _(w=1200, h=600):
    R(0, 0, w, h)
    for i in (1, 2, 3):
        L(0, h * i / 4, w, h * i / 4)


@blk("FUR-WARDROBE")
def _(w=900, h=600):
    R(0, 0, w, h); L(w / 2, 0, w / 2, h)
    L(80, h - 120, w - 80, h - 120)      # 挂衣杆


@blk("FUR-DISPLAY-1200")
def _(w=1200, h=450):
    R(0, 0, w, h)
    x = 300
    while x < w:
        L(x, 0, x, h); x += 300


@blk("FUR-RECEPTION-L")
def _(w=2400, h=3600):
    R(0, 0, 800, h)                      # 主段 800 × 3600
    R(800, h - 800, w, h)                # 侧段 1600 × 800
    L(0, 0, 0, h); L(0, 120, 800, 120)


@blk("FUR-WORKTOP-1800")
def _(w=1800, h=600):
    RR(0, 0, w, h, 40); L(0, 100, w, 100)


@blk("FUR-COPIER-1200")
def _(w=1200, h=700):
    R(0, 0, w, h)
    L(0, h - 200, w, h - 200)            # 出纸口
    R(w - 260, h - 180, w - 40, h - 20)  # 操作面板


@blk("FUR-SHRED-400")
def _(w=400, h=350):
    R(0, 0, w, h); R(60, h - 90, w - 60, h - 20)


@blk("FUR-POD-1200")
def _(w=1200, h=1200):
    R(0, 0, w, h); R(80, 80, w - 80, h - 80)
    A(0, 0, 700, 0, 90)                  # 门向外开


@blk("FUR-HIGHTABLE-2400")
def _(w=2400, h=900):
    RR(0, 0, w, h, 60)


@blk("FUR-STOOL-400")
def _(r=200):
    C(0, 0, r); C(0, 0, 40)


@blk("FUR-PRINT-1200")
def _(w=1200, h=600):
    R(0, 0, w, h); R(60, h - 180, 560, h - 40); R(660, h - 180, w - 60, h - 40)


def _board(w, h):
    R(0, 0, w, h); R(40, 40, w - 40, h - 40)


@blk("FUR-BOARD-1200")
def _(w=1200, h=900):
    _board(w, h)


@blk("FUR-BOARD-1800")
def _(w=1800, h=1200):
    _board(w, h)


@blk("FUR-BOARD-MOVE")
def _(w=1200, h=1800):
    _board(w, h)
    C(150, 150, 80); C(w - 150, 150, 80)


@blk("FUR-TV-1800")
def _(w=1800, h=1100):
    R(0, 0, w, h); R(50, 50, w - 50, h - 50)


@blk("FUR-SCREEN-PROJ")
def _(w=2400, h=150):
    R(0, 0, w, h)
    x = 0
    while x < w:
        L(x, 0, x + 150, h); x += 300


def _sidebar(w, h):
    R(0, 0, w, h); L(w / 2, 0, w / 2, h); L(0, h - 100, w, h - 100)


@blk("FUR-SIDEBAR-1800")
def _(w=1800, h=400):
    _sidebar(w, h)


@blk("FUR-SIDEBAR-2400")
def _(w=2400, h=400):
    _sidebar(w, h)


@blk("FUR-PLANT-700")
def _(r=350):
    C(0, 0, r)
    for a in (90, 210, 330):
        L(0, 0, r * 0.8 * math.cos(math.radians(a)), r * 0.8 * math.sin(math.radians(a)))


@blk("FUR-BIN-400")
def _(w=400, h=400):
    RR(0, 0, w, h, 60); C(w / 2, h / 2, 90)


@blk("FUR-COAT")
def _(r=200):
    C(0, 0, r); C(0, 0, 40); L(0, 0, r * 0.7, r * 0.7)


@blk("FUR-RUG-3000")
def _(w=3000, h=4000):
    L(0, 0, w, 0); L(w, 0, w, h); L(w, h, 0, h); L(0, h, 0, 0)
    L(150, 150, w - 150, 150); L(w - 150, 150, w - 150, h - 150)
    L(w - 150, h - 150, 150, h - 150); L(150, h - 150, 150, 150)


@blk("FUR-WALL-LOGO")
def _(w=3600, h=100):
    R(0, 0, w, h); R(w * 0.35, 0, w * 0.65, h)


@blk("FUR-SIGN-600")
def _(w=600, h=200):
    R(0, 0, w, h); L(w * 0.2, h / 2, w * 0.7, h / 2)
    L(w * 0.55, h * 0.25, w * 0.75, h / 2); L(w * 0.55, h * 0.75, w * 0.75, h / 2)


@blk("FUR-MOP-600")
def _(w=600, h=500):
    R(0, 0, w, h); R(60, 60, w - 60, h - 60); C(w / 2, h / 2, 60)


# 块外形尺寸（w, h）
DIM = {
    "FUR-DESK-1400": (1400, 700), "FUR-DESK-1800": (1800, 800),
    "FUR-CHAIR-TASK": (600, 600), "FUR-CHAIR-MEET": (600, 600),
    "FUR-CHAIR-GUEST": (600, 600), "FUR-CHAIR-DINING": (450, 450),
    "FUR-CHAIR-EXEC": (650, 650),
    "FUR-SCREEN-23400": (100, 23400), "FUR-SCREEN-18000": (100, 18000),
    "FUR-PED-400": (400, 500), "FUR-MON-600": (600, 200), "FUR-KB-450": (450, 150),
    "FUR-LAMP": (200, 200), "FUR-FLOORBOX": (120, 120),
    "FUR-SOFA-3P": (2100, 850), "FUR-SOFA-2P": (1600, 800), "FUR-SOFA-1P": (800, 800),
    "FUR-TABLE-900": (900, 500), "FUR-TABLE-1200": (1200, 600), "FUR-TABLE-1800": (1800, 750), "FUR-TABLE-2400": (2400, 900),
    "FUR-ROUND-800": (800, 800), "FUR-ROUND-900": (900, 900), "FUR-ROUND-1000": (1000, 1000),
    "FUR-MEET-3000": (3000, 1200), "FUR-MEET-4800": (4800, 1600),
    "FUR-COUNTER-5400": (5400, 600), "FUR-UPPER-5400": (5400, 350),
    "FUR-SINK-900": (900, 450), "FUR-FRIDGE-700": (700, 700), "FUR-WATER-400": (400, 400),
    "FUR-MICRO-600": (600, 400), "FUR-COFFEE-400": (400, 350),
    "FUR-CAB-900": (900, 450), "FUR-CAB-1200": (1200, 450),
    "FUR-SHELF-1200": (1200, 350), "FUR-RACK-1200": (1200, 600),
    "FUR-WARDROBE": (900, 600), "FUR-DISPLAY-1200": (1200, 450),
    "FUR-RECEPTION-L": (2400, 3600), "FUR-WORKTOP-1800": (1800, 600),
    "FUR-COPIER-1200": (1200, 700), "FUR-SHRED-400": (400, 350),
    "FUR-POD-1200": (1200, 1200), "FUR-HIGHTABLE-2400": (2400, 900),
    "FUR-STOOL-400": (400, 400), "FUR-PRINT-1200": (1200, 600),
    "FUR-BOARD-1200": (1200, 900), "FUR-BOARD-1800": (1800, 1200),
    "FUR-BOARD-MOVE": (1200, 1800), "FUR-TV-1800": (1800, 1100),
    "FUR-SCREEN-PROJ": (2400, 150), "FUR-SIDEBAR-1800": (1800, 400),
    "FUR-SIDEBAR-2400": (2400, 400), "FUR-PLANT-700": (700, 700),
    "FUR-BIN-400": (400, 400), "FUR-COAT": (400, 400),
    "FUR-RUG-3000": (3000, 4000), "FUR-WALL-LOGO": (3600, 100),
    "FUR-SIGN-600": (600, 200), "FUR-MOP-600": (600, 500),
}

# 圆心为基点的块
ROUND_BASE = {"FUR-LAMP", "FUR-STOOL-400", "FUR-PLANT-700", "FUR-COAT",
              "FUR-ROUND-800", "FUR-ROUND-900", "FUR-ROUND-1000"}

# 真正建块：只建实际用到的
for nm, fn in FURN.items():
    b = doc.blocks.new(name=nm)
    BLOCKS[nm] = b
    _cur_block[0] = nm
    fn()
    _cur_block[0] = None

# ================================================================ 插入器
INSERTS = []
COUNT = {}


WARN = []


def put(name, x1=None, y1=None, x2=None, y2=None, rot=0, cx=None, cy=None, lay="FURNITURE"):
    """矩形块：给目标轴对齐包围盒；圆块：给圆心。自动换算插入点。"""
    w, h = DIM[name]
    if cx is not None:
        ix, iy = cx, cy
        r = 0
    else:
        if rot in (90, 270):
            tw, th = y2 - y1, x2 - x1
        else:
            tw, th = x2 - x1, y2 - y1
        if abs(tw - w) > 5 or abs(th - h) > 5:
            WARN.append("%s rot%d 块 %.0fx%.0f / 目标 %.0fx%.0f" % (name, rot, w, h, tw, th))
        r = rot
        if rot == 0:
            ix, iy = x1, y1
        elif rot == 90:
            ix, iy = x2, y1
        elif rot == 180:
            ix, iy = x2, y2
        else:
            ix, iy = x1, y2
    MPS.add_blockref(name, (ix, iy), dxfattribs={"layer": lay, "rotation": r})
    COUNT[name] = COUNT.get(name, 0) + 1
    INSERTS.append({"block": name, "x": round(ix, 1), "y": round(iy, 1), "rot": r, "layer": lay})
    # PNG：把块内图元变换后落到场景
    ca, sa = math.cos(math.radians(r)), math.sin(math.radians(r))

    def T(px, py):
        return (ix + px * ca - py * sa, iy + px * sa + py * ca)

    for kind, data in BLOCK_PRIMS.get(name, []):
        if kind == "L":
            x1_, y1_, x2_, y2_ = data
            SHAPES.append(("L", T(x1_, y1_) + T(x2_, y2_), lay))
        elif kind == "C":
            cx_, cy_, rr_ = data
            p = T(cx_, cy_)
            SHAPES.append(("C", (p[0], p[1], rr_), lay))
        elif kind == "A":
            cx_, cy_, rr_, a1_, a2_ = data
            pts = []
            a = a1_
            while a <= a2_ + 0.01:
                p = T(cx_ + rr_ * math.cos(math.radians(a)), cy_ + rr_ * math.sin(math.radians(a)))
                pts.append(p); a += 6
            for i in range(len(pts) - 1):
                SHAPES.append(("L", pts[i] + pts[i + 1], lay))


def putc(name, cx, cy, rot=0):
    put(name, cx=cx, cy=cy, rot=rot)


# ================================================================ 建筑骨架
layer("WALL")
# 外框（双线：外皮 + 内皮 200）
R(-21580, -20980, 21580, 20980)
R(-21380, -20780, 21380, 20780)
# 核心筒
R(-10250, -10550, 10250, 10550)
R(-10050, -10350, 10050, 10350)
# 环廊外边线
R(-12650, -12950, 12650, 12950)

# 分区隔墙（100 厚，画双线）
def wall_h(y, x1, x2, t=100):
    L(x1, y, x2, y); L(x1, y + t, x2, y + t)


def wall_v(x, y1, y2, t=100):
    L(x, y1, x, y2); L(x + t, y1, x + t, y2)


wall_h(12950, -21580, -12650)      # Z1 走廊 / Z2
wall_h(13950, -21580, -12650)      # Z1 南墙
wall_h(-12950, -21580, -12650)     # Z2 / Z3
wall_h(-12950, -12650, 7590)       # Z9 北
wall_h(-12950, 7690, 12650)        # Z10 北
wall_h(-12950, 12650, 21580)       # Z7 / Z8
wall_h(12950, -12650, 12650)       # Z12 南（敞口段留空，此处为环廊边线）
wall_h(12950, 12650, 21580)        # Z4 北
wall_h(750, 12650, 21580)          # Z4 / Z5
wall_h(-4910, 12650, 21580)        # Z5 / Z6
wall_h(-8760, 12650, 21580)        # Z6 / Z7
wall_h(14050, 13650, 21580)        # Z11 前室 / 会议室
wall_h(-16200, 7690, 9690)         # Z10 清洁间隔断
wall_v(-17115, 13950, 20980)       # Z1 中隔墙
wall_v(-12650, -20980, 12950)      # 西带东侧（幕墙）
wall_v(12650, -20980, 12950)       # 东带西侧（幕墙）
wall_v(7590, -20980, -12950)       # Z9 / Z10
wall_v(7690, -20980, -12950)
wall_v(13650, 14050, 20980)        # Z11 西墙

# 玻璃隔断（Z8、Z12 项目室）
layer("DOOR_WIN")
R(12650, -20980, 12710, -12950)                       # Z8 玻璃
L(-12650, 16980, -7650, 16980); L(-12650, 17040, -7650, 17040)
L(-7650, 16980, -7650, 20980); L(-7590, 16980, -7590, 20980)
L(-12650, 16980, -12650, 20980)

# 门（门扇 + 90° 开启弧）
def door(x, y, w, sw=1, sh=1, up=True):
    """在 (x,y) 处开门洞宽 w；sw/sh 控制开启方向"""
    layer("DOOR_WIN")
    L(x, y, x, y + sh * w)                      # 门扇
    if up:
        A(x, y, w, 0 if sw > 0 else 90, 90 if sw > 0 else 180)
    else:
        A(x, y, w, 270 if sw > 0 else 180, 360 if sw > 0 else 270)


door(-20500, 13950, 900, 1, 1, True)     # Z1a
door(-16000, 13950, 900, -1, 1, True)    # Z1b
door(14000, -12950, 900, 1, -1, False)   # Z8
door(14000, -4910, 900, 1, -1, False)    # Z5/Z6
# Z11 双开门 1500
layer("DOOR_WIN")
L(15600, 14050, 15600, 14800); A(15600, 14050, 750, 0, 90)
L(17100, 14050, 17100, 14800); A(17100, 14050, 750, 90, 180)

# ================================================================ 12 分区家具
layer("FURNITURE")


def zone_Z1():  # 同学版 Z7：主管室(左房) + 访客洽谈室(右房)
    # —— 主管室（左房：1800×800 主管桌、主管椅、背柜、两把客椅）——
    put("FUR-DESK-1800", -21380, 18900, -19580, 19700)
    putc("FUR-CHAIR-EXEC", -19000, 19300, 180)
    put("FUR-CAB-900", -17215, 18900, -16765, 19800, 90)   # 背柜
    putc("FUR-CHAIR-GUEST", -19300, 19600)
    putc("FUR-CHAIR-GUEST", -19300, 19000)
    # —— 访客洽谈室（右房：1000 圆桌、4 客椅、展示屏、资料柜）——
    ox = 4415
    putc("FUR-ROUND-1000", -20000 + ox, 19300)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        putc("FUR-CHAIR-GUEST", (-20000 + ox) + 720 * math.cos(a), 19300 + 720 * math.sin(a))
    put("FUR-TV-1800", -16965 + ox, 19900, -15165 + ox, 21000, 90)   # 展示屏
    put("FUR-CAB-1200", -16965 + ox, 18900, -15765 + ox, 19800, 90)  # 资料柜
    putc("FUR-PLANT-700", -21000, 14300)


def zone_Z2():
    put("FUR-SCREEN-23400", -17165, -11700, -17065, 11700)
    for i in range(12):  # 同学版 Z8：12 组双排 = 24 固定工位（原 13 组 26 位）
        y = -11700 + 1800 * i
        put("FUR-DESK-1400", -17065, y, -16365, y + 1400, 90)   # 东排
        put("FUR-DESK-1400", -17865, y, -17165, y + 1400, 90)   # 西排
        putc("FUR-CHAIR-TASK", -16065, y + 700)
        putc("FUR-CHAIR-TASK", -18165, y + 700)
        put("FUR-PED-400", -17065, y, -16665, y + 500)          # 东排柜
        put("FUR-PED-400", -17865, y, -17465, y + 500)          # 西排柜
        put("FUR-MON-600", -17065, y + 400, -16865, y + 1000, 90)
        put("FUR-MON-600", -17865, y + 400, -17665, y + 1000, 90)
        put("FUR-KB-450", -16665, y + 300, -16215, y + 450)
        put("FUR-KB-450", -17815, y + 300, -17365, y + 450)
        putc("FUR-LAMP", -16900, y + 200)
        putc("FUR-LAMP", -17700, y + 200)
    for i in range(13):
        y0 = -11700 + 1800 * i + 840
        put("FUR-FLOORBOX", -17145, y0, -17025, y0 + 120)
    for i in range(12):
        put("FUR-CAB-1200", -13100, -11400 + 2000 * i, -12650, -10200 + 2000 * i, 90)
    for cx, cy in ((-19800, 6000), (-19800, -6000)):
        putc("FUR-ROUND-900", cx, cy)
        for k in range(4):
            a = math.radians(45 + 90 * k)
            putc("FUR-CHAIR-GUEST", cx + 650 * math.cos(a), cy + 650 * math.sin(a))
    put("FUR-PRINT-1200", -21580, -3000, -20380, -2400)
    for cx, cy in ((-17400, 12000), (-16700, 12000), (-17400, -12000), (-16700, -12000)):
        putc("FUR-COAT", cx, cy)
    for i in range(6):
        putc("FUR-PLANT-700", -13300, -10000 + 4000 * i)


def zone_Z3():
    put("FUR-COUNTER-5400", -21000, -20980, -15600, -20380)
    put("FUR-SINK-900", -20500, -20880, -19600, -20430)
    put("FUR-UPPER-5400", -21000, -20980, -15600, -20630)
    put("FUR-FRIDGE-700", -15400, -20680, -14700, -19980)
    put("FUR-WATER-400", -14400, -20400, -14000, -20000)
    put("FUR-WATER-400", -13800, -20400, -13400, -20000)
    put("FUR-MICRO-600", -19000, -20780, -18400, -20380)
    put("FUR-COFFEE-400", -18200, -20780, -17800, -20430)
    for cx, cy in ((-20000, -17000), (-16000, -17000)):
        putc("FUR-ROUND-1000", cx, cy)
        for k in range(4):
            a = math.radians(45 + 90 * k)
            putc("FUR-CHAIR-DINING", cx + 720 * math.cos(a), cy + 720 * math.sin(a))
    put("FUR-TABLE-2400", -19200, -14650, -16800, -13750)
    for i in range(4):
        x = -19000 + 550 * i
        putc("FUR-CHAIR-DINING", x, -14950)
        putc("FUR-CHAIR-DINING", x, -13450)
    put("FUR-SOFA-2P", -21580, -16500, -20780, -14900, 90)
    put("FUR-SOFA-1P", -20780, -16400, -19980, -15600)
    put("FUR-SOFA-1P", -20780, -14800, -19980, -14000)
    put("FUR-TABLE-900", -20400, -16000, -19500, -15500)
    putc("FUR-BIN-400", -15000, -19000)
    putc("FUR-BIN-400", -13500, -19000)
    for cx, cy in ((-21200, -13600), (-13000, -13600), (-18000, -19600)):
        putc("FUR-PLANT-700", cx, cy)


def zone_Z4():
    put("FUR-WALL-LOGO", 21480, 3000, 21580, 6600, 90)
    put("FUR-SOFA-3P", 19000, 9000, 21100, 9850)
    put("FUR-SOFA-2P", 16500, 9000, 18100, 9800)
    put("FUR-SOFA-2P", 16500, 7500, 18100, 8300)
    put("FUR-SOFA-1P", 14600, 9100, 15400, 9900)
    put("FUR-SOFA-1P", 14600, 7400, 15400, 8200)
    put("FUR-TABLE-1200", 17000, 9150, 18200, 9750)
    put("FUR-TABLE-1200", 16200, 7600, 17400, 8200)
    for i in range(4):
        x = 13000 + 1300 * i
        put("FUR-DISPLAY-1200", x, 12500, x + 1200, 12950)
    putc("FUR-SIGN-600", 13500, 11000)
    putc("FUR-SIGN-600", 13500, 4000)
    put("FUR-RUG-3000", 16100, 6700, 19100, 10700)
    for cx, cy in ((12900, 12400), (21200, 12400), (12900, 1200), (21200, 1200),
                   (18300, 10600), (14200, 8600)):
        putc("FUR-PLANT-700", cx, cy)


def zone_Z5():
    put("FUR-RECEPTION-L", 14000, -2000, 16400, 1600)
    putc("FUR-CHAIR-TASK", 14600, 400)
    putc("FUR-CHAIR-TASK", 15200, 1200)
    putc("FUR-CHAIR-GUEST", 13600, 400)
    putc("FUR-CHAIR-GUEST", 13600, -400)
    for i in range(4):
        put("FUR-SOFA-1P", 20000, -3800 + 1100 * i, 20800, -3000 + 1100 * i)
    put("FUR-SOFA-2P", 19000, -4700, 20600, -3900)
    put("FUR-TABLE-900", 18550, -2250, 19450, -1750)
    for cx, cy in ((13200, -4500), (13200, 600), (21000, 600)):
        putc("FUR-PLANT-700", cx, cy)


def zone_Z6():
    put("FUR-COPIER-1200", 19000, -5600, 20200, -4900)
    put("FUR-COPIER-1200", 19000, -6500, 20200, -5800)
    put("FUR-WORKTOP-1800", 16000, -5400, 17800, -4800)
    for i in range(4):
        x = 13000 + 950 * i
        put("FUR-CAB-900", x, -8760, x + 900, -8310)
    putc("FUR-SHRED-400", 20500, -8200)
    put("FUR-SHELF-1200", 20600, -8000, 21050, -6800, 90)
    put("FUR-SHELF-1200", 20600, -6800, 21050, -5600, 90)
    putc("FUR-PLANT-700", 13000, -5200)


def zone_Z7():
    put("FUR-POD-1200", 20000, -9500, 21200, -8300)
    put("FUR-POD-1200", 20000, -11000, 21200, -9800)
    putc("FUR-ROUND-800", 16500, -10500)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        putc("FUR-CHAIR-GUEST", 16500 + 620 * math.cos(a), -10500 + 620 * math.sin(a))
    put("FUR-SOFA-2P", 13400, -9600, 15000, -8800)
    put("FUR-TABLE-900", 13750, -10450, 14650, -9950)
    putc("FUR-PLANT-700", 13000, -12500)
    putc("FUR-PLANT-700", 21000, -12500)


def zone_Z8():
    put("FUR-MEET-3000", 15615, -17565, 18615, -16365)
    for i in range(3):
        x = 16315 + 800 * i
        putc("FUR-CHAIR-MEET", x, -16065)
        putc("FUR-CHAIR-MEET", x, -17865)
    put("FUR-TV-1800", 20580, -17500, 21480, -15700, 90)
    put("FUR-BOARD-1200", 14000, -13850, 15200, -12950)
    put("FUR-SIDEBAR-1800", 15000, -20980, 16800, -20580)
    putc("FUR-PLANT-700", 13200, -13400)
    putc("FUR-PLANT-700", 21000, -20500)


def zone_Z9():
    put("FUR-SCREEN-18000", -11530, -17015, 6470, -16915, 90)
    for i in range(9):  # 同学版 Z9：9 组双排 = 18 固定工位（原 10 组 20 位）
        x = -11530 + 1800 * i
        put("FUR-DESK-1400", x, -16915, x + 1400, -16215)      # 北排
        put("FUR-DESK-1400", x, -17715, x + 1400, -17015)      # 南排
        putc("FUR-CHAIR-TASK", x + 700, -15865)
        putc("FUR-CHAIR-TASK", x + 700, -18165)
        put("FUR-PED-400", x, -16915, x + 400, -16415)
        put("FUR-PED-400", x, -17715, x + 400, -17215)
        put("FUR-MON-600", x + 400, -16915, x + 1000, -16715)
        put("FUR-MON-600", x + 400, -17715, x + 1000, -17515)
        put("FUR-KB-450", x + 475, -16415, x + 925, -16265)
        put("FUR-KB-450", x + 475, -17215, x + 925, -17065)
        putc("FUR-LAMP", x + 200, -16715)
        putc("FUR-LAMP", x + 200, -17515)
    for i in range(10):
        x = -10630 + 3600 * i
        put("FUR-FLOORBOX", x, -17065, x + 120, -16945)
    for i in range(6):
        x = -11000 + 2000 * i
        put("FUR-CAB-1200", x, -20980, x + 1200, -20530)
    for cx, cy in ((-12500, -13300), (7300, -13300), (-12500, -20600), (7300, -20600)):
        putc("FUR-PLANT-700", cx, cy)
    # 同学版 Z9 端部共享高桌（临时席 ×2，不计入固定工位）
    put("FUR-HIGHTABLE-2400", -11930, -16915, -9530, -16015)
    put("FUR-HIGHTABLE-2400", -11930, -17715, -9530, -16815)
    for hx in (-10715, -8700):
        putc("FUR-STOOL-400", hx, -16465)
        putc("FUR-STOOL-400", hx, -17265)


def zone_Z10():
    for i in range(6):
        put("FUR-RACK-1200", 12050, -20400 + 1100 * i, 12650, -19200 + 1100 * i, 90)
    for i in range(4):
        put("FUR-CAB-900", 8000, -20000 + 1000 * i, 8450, -19100 + 1000 * i, 90)
    layer("WALL")
    L(7690, -16200, 9690, -16200); L(7690, -16100, 9690, -16100)
    layer("FURNITURE")
    put("FUR-MOP-600", 7800, -20800, 8400, -20300)
    put("FUR-CAB-900", 8800, -20500, 9250, -20050)
    # 隔断计入 13 件（与 20 号手册 Z10 件数一致）
    COUNT["WALL-100"] = COUNT.get("WALL-100", 0) + 1
    INSERTS.append({"block": "WALL-100", "x": 7690, "y": -16200, "rot": 0, "layer": "WALL"})


def zone_Z11():  # 同学版 Z2：多功能培训/评审室（Z2a 主桌区 + Z2b 移动展板）
    # Z2a 主桌区：2 张 1800×750 可拼接桌组
    put("FUR-TABLE-1800", 15200, 16700, 17000, 17450)
    put("FUR-TABLE-1800", 17400, 16700, 19200, 17450)
    # 10 把可移动椅（桌组两侧）
    for i in range(5):
        x = 15600 + 800 * i
        putc("FUR-CHAIR-GUEST", x, 16400)
        putc("FUR-CHAIR-GUEST", x, 17700)
    # 2400 投影幕
    put("FUR-SCREEN-PROJ", 15200, 20830, 17600, 20980)
    # Z2b 移动展板 ×2
    put("FUR-BOARD-MOVE", 14000, 14050, 15200, 15850)
    put("FUR-BOARD-MOVE", 19800, 14050, 21000, 15850)
    # 设备柜
    put("FUR-CAB-1200", 20000, 16600, 21200, 17500, 90)
    putc("FUR-PLANT-700", 14000, 20400)
    putc("FUR-PLANT-700", 21100, 14400)


def zone_Z12():
    put("FUR-MEET-3000", -11650, 18380, -8650, 19580)
    for i in range(3):
        x = -11200 + 750 * i
        putc("FUR-CHAIR-MEET", x, 19880)
        putc("FUR-CHAIR-MEET", x, 18080)
    putc("FUR-CHAIR-MEET", -11850, 18980)
    putc("FUR-CHAIR-MEET", -8450, 18980)
    put("FUR-BOARD-1200", -11000, 20080, -9800, 20980)
    put("FUR-POD-1200", -6800, 19780, -5600, 20980)
    put("FUR-POD-1200", -5400, 19780, -4200, 20980)
    put("FUR-HIGHTABLE-2400", -3600, 18450, -1200, 19350)
    for i in range(3):
        x = -3400 + 700 * i
        putc("FUR-STOOL-400", x, 18200)
        putc("FUR-STOOL-400", x, 19600)
    for i in range(6):
        x = 200 + 1300 * i
        put("FUR-SHELF-1200", x, 20530, x + 1200, 20980)
    put("FUR-SOFA-2P", 1500, 14200, 3100, 15000)
    put("FUR-SOFA-2P", 3800, 14200, 5400, 15000)
    put("FUR-SOFA-1P", 5600, 14300, 6400, 15100)
    put("FUR-SOFA-1P", 6600, 14300, 7400, 15100)
    put("FUR-TABLE-1200", 1700, 15500, 2900, 16100)
    put("FUR-TABLE-1200", 4000, 15500, 5200, 16100)
    put("FUR-PRINT-1200", 8000, 20380, 9200, 20980)
    putc("FUR-BOARD-MOVE", -2000, 13500)
    putc("FUR-BOARD-MOVE", 2000, 13500)
    put("FUR-SIDEBAR-1800", -12500, 17080, -10700, 17530)
    putc("FUR-BIN-400", -7000, 14000)
    putc("FUR-BIN-400", 11500, 14000)
    # 同学版 Z10 共享高桌（临时席，与 Z9 合计 4 席）
    put("FUR-HIGHTABLE-2400", 5000, 14500, 7400, 15400)
    putc("FUR-STOOL-400", 5400, 14950)
    putc("FUR-STOOL-400", 6600, 14950)
    for cx, cy in ((-12500, 20500), (12000, 20500), (1000, 13300),
                   (9000, 15000), (-7500, 14500)):
        putc("FUR-PLANT-700", cx, cy)


ZONES = [
    ("Z1", "前台 · 导视等候", 14, zone_Z5, 17500, -2000, 49.0),
    ("Z2", "培训 / 评审室", 18, zone_Z11, 17500, 15500, 56.0),
    ("Z3", "小会议室", 12, zone_Z8, 17500, -14500, 24.0),
    ("Z4", "展示接待前厅", 21, zone_Z4, 17500, 7000, 107.0),
    ("Z5", "文印 · 归档", 11, zone_Z6, 17500, -6800, 32.0),
    ("Z6", "声学电话亭 · 洽谈", 11, zone_Z7, 17500, -11200, 37.0),
    ("Z7", "主管室 · 访客洽谈", 13, zone_Z1, -18000, 17500, 31.4),
    ("Z8", "开放工位 A · 24 位", 188, zone_Z2, -18000, 500, 231.3),
    ("Z9", "开放工位 B · 18 位", 143, zone_Z9, -3000, -19000, 162.5),
    ("Z10", "项目协作 · 共享图书", 42, zone_Z12, 0, 15500, 198.0),
    ("Z11", "茶水 · 员工交流", 36, zone_Z3, -18000, -17500, 57.0),
    ("Z12", "设备储物 · 物流暂存", 13, zone_Z10, 10000, -19000, 40.0),
]

EXPECT = {}
for code, nm, n, fn, tx, ty, area in ZONES:
    before = sum(COUNT.values())
    fn()
    got = sum(COUNT.values()) - before
    EXPECT[code] = (n, got)
    if got != n:
        print("!! %s 件数不符：应 %d，实 %d" % (code, n, got))

# ================================================================ 填充
layer("HATCH")


def hatch(pts, pat="ANSI32", scale=25, color=9):
    h = MPS.add_hatch(color=color, dxfattribs={"layer": "HATCH"})
    h.set_pattern_fill(pat, scale=scale)
    h.paths.add_polyline_path(pts, is_closed=True)


hatch([(-21580, -20980), (-12650, -20980), (-12650, -12950), (-21580, -12950)], "ANSI31", 25)   # Z3
hatch([(12650, 750), (21580, 750), (21580, 12950), (12650, 12950)], "ANSI32", 25)               # Z4
hatch([(12650, -4910), (21580, -4910), (21580, 750), (12650, 750)], "ANSI32", 25)               # Z5
hatch([(-10250, -10550), (10250, -10550), (10250, 10550), (-10250, 10550)], "ANSI31", 40)       # 核心筒

# ================================================================ 文字
layer("TEXT")


def txt(s, x, y, h=350, align=TextEntityAlignment.MIDDLE_CENTER):
    t = MPS.add_text(s, height=h, dxfattribs={"layer": "TEXT"})
    t.set_placement((x, y), align=align)
    SHAPES.append(("T", (s, x, y, h, align), "TEXT"))


LABEL = {
    "Z1": (13050, -4300), "Z2": (13950, 20300), "Z3": (13050, -13800),
    "Z4": (13050, 11400), "Z5": (13050, -5300), "Z6": (13050, -12500),
    "Z7": (-21050, 14300), "Z8": (-21050, 11800), "Z9": (-12050, -13400),
    "Z10": (-12050, 16300), "Z11": (-21050, -13600), "Z12": (7900, -13400),
}
for code, nm, n, fn, tx, ty, area in ZONES:
    lx, ly = LABEL[code]
    t = MPS.add_text(code, height=700, dxfattribs={"layer": "TEXT"})
    t.set_placement((lx, ly), align=TextEntityAlignment.LEFT)
    SHAPES.append(("T", (code, lx, ly, 700, TextEntityAlignment.LEFT), "TEXT"))

# ---- 图外：分区一览表（放在 A1 左侧空白，避免区内压字）----
txt("分 区 一 览 表", -40500, 22600, 600, TextEntityAlignment.LEFT)
txt("区号   分区名称              净面积    家具", -40500, 21300, 330, TextEntityAlignment.LEFT)
LY = 20400
for code, nm, n, fn, tx, ty, area in ZONES:
    s_ = "%s   %-18s %6.1f ㎡  %4d 件" % (code, nm.replace(" · ", "·"), area, n)
    txt(s_, -40500, LY, 330, TextEntityAlignment.LEFT)
    LY -= 1500
txt("合计   12 个分区          1129.2 ㎡   545 件", -40500, LY - 300, 330, TextEntityAlignment.LEFT)

txt("A-1 开放办公区 · 平面布置图（同学版 CAD 调整）  1:100", 0, 23200, 900)
txt("建筑面积 1811 ㎡ ｜ 分区毛面积 1129.2 ㎡ ｜ 固定工位 42 位 ｜ 共享高桌 4 席", 0, 21900, 400)
txt("环廊 2400 宽（不计家具）", 0, -12100, 300)
txt("核心筒（保留）", 0, 0, 500)
txt("图例：绿=FURNITURE 家具 ｜ 青=DOOR_WIN 门窗/玻璃隔断 ｜ 灰=HATCH 铺装 ｜ 黄=DIM 尺寸", -40500, -25000, 330, TextEntityAlignment.LEFT)

# ================================================================ 图框 A1 @1:100
layer("FRAME")
R(-42050, -29700, 42050, 29700)          # 841 × 594 mm
R(-39550, -27200, 39550, 27200)          # 内框（留 25mm 装订边）
# 图签 180 × 60 mm，右下
R(21550, -27200, 39550, -21200)
L(21550, -24200, 39550, -24200)
L(21550, -25500, 39550, -25500)
L(30550, -27200, 30550, -24200)
txt("A-1 开放办公区 平面布置图", 30800, -26350, 700)
txt("比例 1:100    图幅 A1    图号 PL-01", 30550, -24850, 380)
txt("毕业设计 · 办公空间室内设计", 26050, -23200, 400)
txt("班级 / 姓名 / 指导教师 / 日期", 35050, -23200, 350)

# 三级尺寸（总尺寸）
layer("DIM")
L(-21580, -22400, 21580, -22400)
for x in (-21580, 21580):
    L(x, -22800, x, -22000)
L(21580, -23800, 21580, -23800)
L(-21580, 22200, 21580, 22200)
for x in (-21580, 21580):
    L(x, 21800, x, 22600)
L(22800, -20980, 22800, 20980)
for y in (-20980, 20980):
    L(22400, y, 23200, y)
txt("43160", 0, -23200, 350)
txt("41960", 24000, 0, 350)

# ================================================================ 保存
os.makedirs(OUT, exist_ok=True)
dxf_path = os.path.join(OUT, NAME + ".dxf")
doc.saveas(dxf_path)

with open(os.path.join(OUT, "inserts.jsonl"), "w", encoding="utf-8") as f:
    for r in INSERTS:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

total = sum(COUNT.values())
print("=== 家具统计 ===")
for k in sorted(COUNT, key=lambda s: -COUNT[s]):
    print("  %-22s %4d" % (k, COUNT[k]))
print("块种类 %d ｜ 插入总数 %d" % (len([k for k in COUNT if k.startswith('FUR-')]), total))
print("逐区：", {k: v[1] for k, v in EXPECT.items()})
print("DXF:", dxf_path)

# ================================================================ PNG 预览（PIL）
from PIL import Image, ImageDraw, ImageFont
from config import MSYH_FONT

S = 0.017                      # px / mm
X0, Y0, X1, Y1 = -42500, -30200, 42500, 30200
W = int((X1 - X0) * S); H = int((Y1 - Y0) * S)
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)

COL = {"WALL": (0, 0, 0), "COLUMN": (0, 0, 0), "DOOR_WIN": (0, 140, 160),
       "FURNITURE": (0, 120, 0), "MEP": (200, 0, 0), "DIM": (170, 140, 0),
       "TEXT": (30, 30, 30), "HATCH": (170, 170, 170), "FRAME": (90, 90, 90)}
LW = {"WALL": 2, "COLUMN": 2, "DOOR_WIN": 1, "FURNITURE": 1, "MEP": 1,
      "DIM": 1, "TEXT": 1, "HATCH": 1, "FRAME": 2}


def P(x, y):
    return ((x - X0) * S, (Y1 - y) * S)


for kind, data, lay in SHAPES:
    if kind == "L":
        x1, y1, x2, y2 = data
        d.line([P(x1, y1), P(x2, y2)], fill=COL.get(lay, (0, 0, 0)), width=LW.get(lay, 1))
    elif kind == "C":
        cx, cy, r = data
        a, b = P(cx - r, cy + r), P(cx + r, cy - r)
        d.ellipse([a, b], outline=COL.get(lay, (0, 0, 0)), width=LW.get(lay, 1))
    elif kind == "T":
        s, x, y, h, al = data
        px = max(6, int(h * S * 1.5))
        try:
            f = ImageFont.truetype(str(MSYH_FONT), px)
        except Exception:
            f = ImageFont.load_default()
        anc = "lm" if al == TextEntityAlignment.LEFT else "mm"
        d.text(P(x, y), s, fill=COL.get(lay, (0, 0, 0)), font=f, anchor=anc)

png_path = os.path.join(OUT, NAME + ".png")
img.save(png_path, "PNG")
print("PNG:", png_path, img.size)

# ---------------------------------------------------------------- PDF 预览
pdf_path = os.path.join(OUT, NAME + ".pdf")
img.save(pdf_path, "PDF", resolution=150.0)
print("PDF:", pdf_path)
