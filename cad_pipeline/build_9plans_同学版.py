# -*- coding: utf-8 -*-
"""
同学版 9 张平面图批量生成（制图规范表格3）
输出: DXF + PNG + PDF，DWG 由 dwg_convert.py 经 AutoCAD COM 另存
运行: managed venv python (ezdxf + matplotlib + pywin32)
"""
import os, math
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from config import SYSTEM_FONT_DIR, HEI_FONT
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy, TextPolicy

# 中文字体：matplotlib 原生渲染用（ezdxf 自带 fontTools 渲染器对 图/置 等字形有 bug，
# 故 PNG/PDF 由 matplotlib 直接叠字；DXF 内文字体绑 SimHei 供 AutoCAD 正常显示）
FONTPATH = HEI_FONT
fm.fontManager.addfont(FONTPATH)
CNF = fm.FontProperties(fname=FONTPATH)

from config import ROOT as BASE  # 旧版 BASE 写死桌面路径，改为随包根目录（见 config）
OUT = os.path.join(BASE, "02_平面图_四格式")
POC_DXF = os.path.join(BASE, "01_PL-01_PoC", "PL-01_平面布置图_A1_同学版.dxf")
os.makedirs(OUT, exist_ok=True)

STYLE = "CN"
LAYERS = [("WALL",7,50),("COLUMN",7,50),("DOOR_WIN",4,25),("FURNITURE",4,25),
          ("MEP",6,9),("DIM",3,9),("TEXT",2,9),("HATCH",9,9),("FRAME",7,9)]

def fix_style_fonts(doc):
    """把系统不存在的字体样式(OpenSans/Liberation等, ezdxf setup=True 生成)
    重定向到 AutoCAD 自带 txt.shx —— 防止打开时弹字体替换对话框卡死COM转换。
    不能直接删样式: DIMSTYLE 引用了它们, 删了导出会崩。"""
    for s in doc.styles:
        f = (s.dxf.font or "").strip()
        if not f:
            continue
        low = f.lower()
        if low.endswith(".shx"):
            continue  # SHX 由 AutoCAD 自带目录解析
        cand = [low, low + ".ttf"]
        if any(os.path.exists(os.path.join(SYSTEM_FONT_DIR, c)) for c in cand):
            continue
        s.dxf.font = "txt"

def new_doc():
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4
    doc.header["$MEASUREMENT"] = 1
    for nm, col, lw in LAYERS:
        if nm not in doc.layers:
            doc.layers.add(nm, color=col, lineweight=lw)
    doc.styles.add(STYLE, font="SimHei")
    return doc

def line(msp, x1, y1, x2, y2, lay="WALL", lt=None, color=None):
    at = {"layer": lay}
    if lt: at["linetype"] = lt
    if color is not None: at["color"] = color
    msp.add_line((x1, y1), (x2, y2), dxfattribs=at)

def rect(msp, x1, y1, x2, y2, lay="WALL", lt=None):
    line(msp, x1, y1, x2, y1, lay, lt); line(msp, x2, y1, x2, y2, lay, lt)
    line(msp, x2, y2, x1, y2, lay, lt); line(msp, x1, y2, x1, y1, lay, lt)

def circle(msp, cx, cy, r, lay="MEP"):
    msp.add_circle((cx, cy), r, dxfattribs={"layer": lay})

def _rec(msp, kind, s, x, y, h, align=None):
    """记录文字元数据，供 render() 用 matplotlib 叠字（避开 ezdxf 字形 bug）"""
    lst = getattr(msp.doc, "overlay_texts", None)
    if lst is None:
        lst = []
        msp.doc.overlay_texts = lst
    lst.append((kind, s, x, y, h, align))

def txt(msp, s, x, y, h=350, lay="TEXT", align=TA.MIDDLE_CENTER):
    e = msp.add_text(s, dxfattribs={"layer": lay, "style": STYLE, "height": h}).set_placement((x, y), align=align)
    _rec(msp, "t", s, x, y, h, align)
    return e

def mtxt(msp, s, x, y, h=320, lay="TEXT"):
    m = msp.add_mtext(s, dxfattribs={"layer": lay, "style": STYLE, "char_height": h})
    m.set_location((x, y))
    m.dxf.attachment_point = 1   # 顶部左对齐
    _rec(msp, "m", s, x, y, h)
    return m

def wall_h(msp, y, x1, x2, t=100):
    line(msp, x1, y, x2, y); line(msp, x1, y + t, x2, y + t)

def wall_v(msp, x, y1, y2, t=100):
    line(msp, x, y1, x, y2); line(msp, x + t, y1, x + t, y2)

def door(msp, x, y, w, sw=1, up=True):
    line(msp, x, y, x, y + w, "DOOR_WIN")
    if up:
        a1, a2 = (0, 90) if sw > 0 else (90, 180)
    else:
        a1, a2 = (270, 360) if sw > 0 else (180, 270)
    msp.add_arc((x, y), w, a1, a2, dxfattribs={"layer": "DOOR_WIN"})

def skeleton(msp, doors=True):
    """建筑骨架：外框幕墙+核心筒+环廊+分区隔墙（同学版沿用成品坐标）"""
    rect(msp, -21580, -20980, 21580, 20980)
    rect(msp, -21380, -20780, 21380, 20780)
    rect(msp, -10250, -10550, 10250, 10550)
    rect(msp, -10050, -10350, 10050, 10350)
    rect(msp, -12650, -12950, 12650, 12950)
    wall_h(msp, 12950, -21580, -12650)
    wall_h(msp, 13950, -21580, -12650)
    wall_h(msp, -12950, -21580, -12650)
    wall_h(msp, -12950, -12650, 7590)
    wall_h(msp, -12950, 7690, 12650)
    wall_h(msp, -12950, 12650, 21580)
    wall_h(msp, 12950, -12650, 12650)
    wall_h(msp, 12950, 12650, 21580)
    wall_h(msp, 750, 12650, 21580)
    wall_h(msp, -4910, 12650, 21580)
    wall_h(msp, -8760, 12650, 21580)
    wall_h(msp, 14050, 13650, 21580)
    wall_h(msp, -16200, 7690, 9690)
    wall_v(msp, -17115, 13950, 20980)
    wall_v(msp, -12650, -20980, 12950)
    wall_v(msp, 12650, -20980, 12950)
    wall_v(msp, 7590, -20980, -12950)
    wall_v(msp, 7690, -20980, -12950)
    wall_v(msp, 13650, 14050, 20980)
    # 玻璃隔断
    rect(msp, 12650, -20980, 12710, -12950, "DOOR_WIN")
    for a in [(-12650,16980,-7650,16980), (-12650,17040,-7650,17040),
              (-7650,16980,-7650,20980), (-7590,16980,-7590,20980),
              (-12650,16980,-12650,20980)]:
        line(msp, a[0], a[1], a[2], a[3], "DOOR_WIN")
    if doors:
        door(msp, -20500, 13950, 900, 1, True)
        door(msp, -16000, 13950, 900, -1, True)
        door(msp, 14000, -12950, 900, 1, False)
        door(msp, 14000, -4910, 900, 1, False)
        line(msp, 15600, 14050, 15600, 14800, "DOOR_WIN")
        msp.add_arc((15600, 14050), 750, 0, 90, dxfattribs={"layer": "DOOR_WIN"})
        line(msp, 17100, 14050, 17100, 14800, "DOOR_WIN")
        msp.add_arc((17100, 14050), 750, 90, 180, dxfattribs={"layer": "DOOR_WIN"})

def axis_grid(msp):
    """轴网 37000x37000：X 13轴 3084x11+3076，Y 12轴 3364x10+3360"""
    xs = [-18500 + 3084 * k for k in range(12)] + [18500]
    ys = [-18500 + 3364 * k for k in range(11)] + [18500]
    for i, x in enumerate(xs):
        line(msp, x, -19400, x, 19400, "DIM", "CENTER", 1)
        msp.add_circle((x, 20200), 800, dxfattribs={"layer": "DIM"})
        txt(msp, str(i + 1), x, 20200, 450, "DIM")
    for j, y in enumerate(ys):
        line(msp, -19400, y, 19400, y, "DIM", "CENTER", 1)
        msp.add_circle((-20200, y), 800, dxfattribs={"layer": "DIM"})
        txt(msp, chr(65 + j), -20200, y, 450, "DIM")

def dim_h(msp, y, x1, x2, label, th=280):
    line(msp, x1, y, x2, y, "DIM")
    for x in (x1, x2):
        line(msp, x, y - 150, x, y + 150, "DIM")
    txt(msp, label, (x1 + x2) / 2, y + 120, th, "DIM", TA.BOTTOM_CENTER)

def dim_v(msp, x, y1, y2, label, th=280):
    line(msp, x, y1, x, y2, "DIM")
    for y in (y1, y2):
        line(msp, x - 150, y, x + 150, y, "DIM")
    txt(msp, label, x + 120, (y1 + y2) / 2, th, "DIM", TA.BOTTOM_LEFT)

def frame(msp, dwno, dwname, scale="1:50"):
    rect(msp, -42050, -29700, 42050, 29700, "FRAME")
    rect(msp, -39550, -27200, 39550, 27200, "FRAME")
    rect(msp, 21550, -27200, 39550, -21200, "FRAME")
    line(msp, 21550, -24200, 39550, -24200, "FRAME")
    line(msp, 21550, -22700, 39550, -22700, "FRAME")
    line(msp, 30550, -27200, 30550, -24200, "FRAME")
    txt(msp, dwname, 35050, -26200, 550)
    txt(msp, "图号 %s   比例 %s   图幅 A1" % (dwno, scale), 35050, -24800, 330)
    txt(msp, "毕业设计 办公空间室内设计", 26050, -26200, 380)
    txt(msp, "同学版CAD调整方案", 26050, -24800, 330)
    txt(msp, "制图 XXX  学号 XXXXXXXXXX", 30550, -23600, 330)
    txt(msp, "日期 2026-10-31  阶段 施工图", 30550, -22200, 330)
    txt(msp, "%s  比例 %s" % (dwname, scale), 0, 23500, 800)
    txt(msp, "同学版CAD调整方案  建筑面积1811平米", 0, 22200, 380)

# ---------------------------------------------------------------- 分区标注数据
ZONE_INFO = [
    ("Z7", -21200, 20500, "主管室\n1800x800主管桌 主管椅 背柜\n客椅2把"),
    ("Z7", -16600, 20500, "访客洽谈室\n1000圆桌 访客椅4把\n展示屏 资料柜"),
    ("Z8", -21300, 13300, "开放办公区A  固定工位24位\n12组双排 桌1400x700\n活动柜 显示器 端部打印绿植缓冲"),
    ("Z11", -21300, -13400, "茶水 员工交流区\n固定餐位12席\n操作台5400 水槽 冰箱\n微波炉 咖啡设备 站立交流台"),
    ("Z9", -12400, -13400, "开放办公区B  固定工位18位\n9组双排 桌1400x700\n端部共享高桌2张(临时席) 高脚椅4"),
    ("Z12", 7800, -13400, "设备储物 物流暂存\n货架6组 清洁柜1组\n设备柜2组 靠门快递暂存位"),
    ("Z2", 12800, 20700, "多功能培训 评审室\n可变座位10席\n可拼接桌组2张 投影幕2400\n移动白板2块 设备柜"),
    ("Z10", -12400, 20700, "项目协作 共享图书区\n项目桌3000 会议椅8\n书架6组 阅读桌2 阅读椅4\n移动白板2 共享高桌2(临时席)"),
    ("Z4", 12800, 13700, "展示接待前厅\n连续展示墙 可更换展板4\n灯带1条 等候岛\n双人沙发 单椅2 茶几"),
    ("Z1", 12800, 600, "前台 导视等候区\nL型前台背靠东幕墙\n导视墙2400 访客椅2\n双人沙发 茶几900"),
    ("Z5", 12800, -5050, "文印 归档室\n复合打印机1 工作台1800\n归档柜4组 碎纸机\n开放资料架2组"),
    ("Z6", 12800, -8900, "声学电话亭 一对一洽谈\n电话亭2个(1200x1200)\n圆桌800 访客椅4 壁挂屏"),
    ("Z3", 12800, -13100, "小会议室  6席\n圆桌1200 会议椅6\n白板1块"),
]
ZONE_SHORT = {  # 简短标签（辅助图用）
    "Z1": (17000, -2100, "Z1 前台 导视等候"), "Z2": (17000, 17500, "Z2 培训 评审室"),
    "Z3": (17000, -16900, "Z3 小会议室"), "Z4": (17000, 7300, "Z4 展示接待前厅"),
    "Z5": (17000, -6800, "Z5 文印 归档"), "Z6": (17000, -10800, "Z6 电话亭 洽谈"),
    "Z7": (-17000, 17500, "Z7 主管室 访客洽谈"), "Z8": (-17000, 500, "Z8 开放办公区A"),
    "Z9": (-2500, -16900, "Z9 开放办公区B"), "Z10": (0, 16900, "Z10 项目协作 共享图书"),
    "Z11": (-17000, -16900, "Z11 茶水 员工交流"), "Z12": (10100, -16900, "Z12 设备储物 物流暂存"),
}

def zone_rich(msp):
    for code, x, y, s in ZONE_INFO:
        mtxt(msp, "%s  %s" % (code, s), x, y, 320)
    mtxt(msp, "环廊 宽2400\n消防疏散通道\n不得布置家具", -700, 11500, 300)
    mtxt(msp, "环廊 宽2400\n消防疏散通道", -700, -12300, 300)
    txt(msp, "核心筒 保留题目真实几何", 0, 0, 450)

def zone_short(msp):
    for code, (x, y, s) in ZONE_SHORT.items():
        txt(msp, s, x, y, 380)
    txt(msp, "核心筒", 0, 0, 420)
    mtxt(msp, "环廊 宽2400 消防疏散通道", -3000, 11500, 300)
    mtxt(msp, "环廊 宽2400 消防疏散通道", -3000, -12300, 300)

# ---------------------------------------------------------------- 分区边界（用于铺装/天花）
ZB = {
    "Z8": [(-21380,-12850),(-12750,-12850),(-12750,13850),(-21380,13850)],
    "Z9": [(-12550,-20880),(7590,-20880),(7590,-13050),(-12550,-13050)],
    "Z7": [(-21380,14050),(-12750,14050),(-12750,20880),(-21380,20880)],
    "Z11":[(-21380,-20880),(-12750,-20880),(-12750,-13050),(-21380,-13050)],
    "Z12":[(7690,-20880),(12550,-20880),(12550,-13050),(7690,-13050)],
    "Z2": [(12750,14150),(21480,14150),(21480,20880),(12750,20880)],
    "Z4": [(12750,850),(21480,850),(21480,13850),(12750,13850)],
    "Z1": [(12750,-4810),(21480,-4810),(21480,650),(12750,650)],
    "Z5": [(12750,-8660),(21480,-8660),(21480,-5010),(12750,-5010)],
    "Z6": [(12750,-12850),(21480,-12850),(21480,-8860),(12750,-8860)],
    "Z3": [(12750,-20880),(21480,-20880),(21480,-13050),(12750,-13050)],
    "Z10":[(-12550,13050),(12550,13050),(12550,20880),(-12550,20880)],
}
def hatch_zone(msp, pts, pat, scale=25):
    h = msp.add_hatch(color=9, dxfattribs={"layer": "HATCH"})
    h.set_pattern_fill(pat, scale=scale)
    h.paths.add_polyline_path(pts, is_closed=True)

# ---------------------------------------------------------------- 各图
def build_PL02():
    doc = new_doc(); msp = doc.modelspace()
    skeleton(msp); axis_grid(msp)
    # 总尺寸
    dim_h(msp, -22300, -21580, 21580, "43160", 380)
    dim_v(msp, 22400, -20980, 20980, "41960", 380)
    # 轴线尺寸链（下）
    xs = [-18500 + 3084 * k for k in range(12)] + [18500]
    line(msp, -18500, -21200, 18500, -21200, "DIM")
    for k in range(12):
        v = "3076" if k == 11 else "3084"
        dim_h(msp, -20850, xs[k], xs[k + 1], v, 240)
    for x in xs:
        line(msp, x, -21580, x, -20600, "DIM")
    # 轴线尺寸链（左）
    ys = [-18500 + 3364 * k for k in range(11)] + [18500]
    line(msp, -21200, -18500, -21200, 18500, "DIM")
    for k in range(11):
        v = "3360" if k == 10 else "3364"
        dim_v(msp, -20850, ys[k], ys[k + 1], v, 240)
    # 核心筒尺寸
    dim_h(msp, 11000, -10250, 10250, "核心筒宽20500", 300)
    dim_v(msp, 11000, -10550, 10550, "核心筒深21100", 300)
    dim_h(msp, -11600, 10250, 12650, "环廊2400", 260)
    dim_h(msp, -11600, -12650, -10250, "环廊2400", 260)
    zone_short(msp)
    txt(msp, "说明: 本图为原始结构图, 仅表达原建筑外墙 幕墙 核心筒 轴网及原分区隔墙, 新增隔墙为0", -39500, -26500, 300, "TEXT", TA.BOTTOM_LEFT)
    frame(msp, "PL-02", "原始结构图")
    return doc, "PL-02_原始结构图"

def build_PL04():
    doc = new_doc(); msp = doc.modelspace()
    skeleton(msp)
    # 隔墙定位尺寸链（右带竖向）
    ys_r = [20980, 14050, 750, -4910, -8760, -12950, -20980]
    line(msp, 22100, 20980, 22100, -20980, "DIM")
    vals = ["6930", "13300", "5660", "3850", "4190", "8030"]
    for k in range(6):
        dim_v(msp, 21800, ys_r[k + 1], ys_r[k], vals[k], 260)
    # 左带竖向墙
    line(msp, -17500, 13950, -17500, 20980, "DIM")
    dim_v(msp, -17800, 13950, 20980, "7030", 260)
    # 底带横向墙 7590/7690
    dim_h(msp, -21600, -21580, -12650, "8930", 260)
    dim_h(msp, -21600, 7590, 7690, "100", 240)
    dim_h(msp, -21600, -12650, 7590, "20240", 260)
    # 门洞尺寸
    txt(msp, "门洞900", -20200, 14250, 260, "DIM")
    txt(msp, "门洞900", -16000, 14250, 260, "DIM")
    txt(msp, "门洞900", 14000, -12700, 260, "DIM")
    txt(msp, "门洞900", 14000, -4700, 260, "DIM")
    txt(msp, "双开门洞1500", 16350, 14250, 260, "DIM")
    # 墙厚说明
    mtxt(msp, "墙厚说明:\n外墙及幕墙 t=200\n核心筒 t=200\n分区隔墙 t=100\n玻璃隔断 t=60", -40500, 13000, 320, "TEXT")
    mtxt(msp, "隔墙定位: 均自轴线/外墙内皮引出, 详尺寸链", -40500, 10000, 320, "TEXT")
    zone_short(msp)
    frame(msp, "PL-04", "墙体定位图")
    return doc, "PL-04_墙体定位图"

def build_PL05():
    doc = new_doc(); msp = doc.modelspace()
    skeleton(msp)
    mats = [("Z8", "ANSI31", 30), ("Z9", "ANSI31", 30), ("Z2", "DOTS", 40), ("Z10", "DOTS", 40),
            ("Z4", "ANSI37", 25), ("Z1", "ANSI37", 25), ("Z11", "ANSI33", 30),
            ("Z7", "NET", 30), ("Z5", "ANSI32", 30), ("Z6", "ANSI32", 30),
            ("Z3", "ANSI32", 30), ("Z12", "ANSI32", 30)]
    for code, pat, sc in mats:
        hatch_zone(msp, ZB[code], pat, sc)
    zone_short(msp)
    mtxt(msp, "地面材料表:\nZ8 Z9 开放办公区: 架空网络地板600x600\nZ2 培训评审室: 阻燃地毯\nZ10 项目协作区: 阻燃地毯\nZ4 展示前厅 Z1 前台: 石材地面\nZ11 茶水区: 防滑地砖\nZ5 Z6 Z3 Z12: 地砖\nZ7 主管室 洽谈: 地毯\n环廊: 架空网络地板(同办公区)\n起铺点: 各区入口处, 交界处设金属收口条", -40500, 12000, 300, "TEXT")
    frame(msp, "PL-05", "地面铺装图")
    return doc, "PL-05_地面铺装图"

def _ceiling_rects(msp):
    for code, pts in ZB.items():
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        rect(msp, min(xs), min(ys), max(xs), max(ys), "MEP", "DASHED")

def build_PL06():
    doc = new_doc(); msp = doc.modelspace()
    skeleton(msp, doors=False)
    _ceiling_rects(msp)
    cnt = {"panel": 0, "down": 0, "smoke": 0, "vent": 0}
    # 开放办公A 面板灯 + 风口
    for i in range(12):
        y = -11700 + 1800 * i + 900
        for x in (-16800, -17600):
            rect(msp, x - 300, y - 300, x + 300, y + 300, "MEP"); cnt["panel"] += 1
    for i in (2, 7):
        x, y = -17200, -11700 + 1800 * i + 900
        rect(msp, x - 200, y - 200, x + 200, y + 200, "MEP")
        line(msp, x - 200, y - 200, x + 200, y + 200, "MEP")
        line(msp, x - 200, y + 200, x + 200, y - 200, "MEP"); cnt["vent"] += 1
    # 开放办公B
    for i in range(9):
        x = -11530 + 1800 * i + 700
        for y in (-16400, -17200):
            rect(msp, x - 300, y - 300, x + 300, y + 300, "MEP"); cnt["panel"] += 1
    for i in (2, 6):
        x = -11530 + 1800 * i + 700; y = -16800
        rect(msp, x - 200, y - 200, x + 200, y + 200, "MEP")
        line(msp, x - 200, y - 200, x + 200, y + 200, "MEP")
        line(msp, x - 200, y + 200, x + 200, y - 200, "MEP"); cnt["vent"] += 1
    # 培训室 面板灯
    for x in (15600, 17200, 18800):
        for y in (17000, 18600):
            rect(msp, x - 300, y - 300, x + 300, y + 300, "MEP"); cnt["panel"] += 1
    # 前厅 射灯 + 展示灯带
    for y in (2000, 4200, 6400, 8600, 10800):
        circle(msp, 20800, y, 100); cnt["down"] += 1
    line(msp, 21300, 3000, 21300, 6600, "MEP"); line(msp, 21380, 3000, 21380, 6600, "MEP")
    # 协作区 面板灯
    for x in (-9000, -3000, 3000, 9000):
        rect(msp, x - 300, 16900 - 300, x + 300, 16900 + 300, "MEP"); cnt["panel"] += 1
    # 茶水区
    for x in (-19600, -17600, -15600):
        rect(msp, x - 300, -17600 - 300, x + 300, -17600 + 300, "MEP"); cnt["panel"] += 1
    # 环廊筒灯 + 烟感
    for x in range(-10800, 10900, 2400):
        circle(msp, x, 11750, 90); circle(msp, x, -11750, 90); cnt["down"] += 2
    for y in range(-9350, 9400, 2400):
        circle(msp, 11450, y, 90); circle(msp, -11450, y, 90); cnt["down"] += 2
    for x, y in [(-17000, 500), (-17000, -16900), (-17000, 17500), (17000, 7300),
                 (17000, 17500), (17000, -2100), (17000, -6800), (17000, -10800),
                 (17000, -16900), (-2500, -16900), (10100, -16900), (0, 16900)]:
        circle(msp, x, y, 80, "MEP")
        line(msp, x - 80, y, x + 80, y, "MEP"); line(msp, x, y - 80, x, y + 80, "MEP"); cnt["smoke"] += 1
    # 检修口
    for x, y in [(0, 11750), (0, -11750)]:
        rect(msp, x - 300, y - 300, x + 300, y + 300, "MEP", "DASHED")
        txt(msp, "检修口600x600", x + 900, y, 240, "TEXT", TA.BOTTOM_LEFT)
    zone_short(msp)
    mtxt(msp, "天花材料分区:\nZ8 Z9 开放办公区: 矿棉板600x600明架 吊顶标高+2.700\nZ2 培训评审室: 石膏板造型 吊顶标高+2.900\nZ4 展示前厅: 石膏板+灯带 吊顶标高+3.000\nZ11 茶水区: 铝扣板 吊顶标高+2.600\n环廊: 石膏板平顶 吊顶标高+2.600\n其余区域: 矿棉板600x600 吊顶标高+2.700\n图例: 方框600x600=面板灯  圆圈=筒灯  方框加叉=风口  圆圈加十字=烟感", -40500, 12000, 300, "TEXT")
    frame(msp, "PL-06", "天花布置图")
    return doc, "PL-06_天花布置图"

def build_PL15():
    doc = new_doc(); msp = doc.modelspace()
    skeleton(msp, doors=False)
    _ceiling_rects(msp)
    elev = {"Z8": "+2.700", "Z9": "+2.700", "Z2": "+2.900", "Z10": "+2.800", "Z4": "+3.000",
            "Z1": "+3.000", "Z11": "+2.600", "Z7": "+2.700", "Z5": "+2.700", "Z6": "+2.700",
            "Z3": "+2.700", "Z12": "+2.700"}
    for code, pts in ZB.items():
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        txt(msp, "标高%s" % elev[code], (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, 320)
    txt(msp, "核心筒顶 标高+2.600", 0, 0, 320)
    # 分区尺寸
    dim_v(msp, 22100, 750, 14050, "13300", 300)
    dim_v(msp, 22100, -4910, 750, "5660", 300)
    dim_h(msp, -22300, -21580, 21580, "43160", 380)
    zone_short(msp)
    mtxt(msp, "天花分区尺寸与标高:\n各分区吊顶标高见图面标注\n环廊标高+2.600\n高差处设暗藏灯带收口", -40500, 12000, 300, "TEXT")
    frame(msp, "PL-15", "天花尺寸图")
    return doc, "PL-15_天花尺寸图"

def build_PL07():
    doc = new_doc(); msp = doc.modelspace()
    skeleton(msp, doors=False)
    n_panel = n_down = n_strip = 0
    for i in range(12):
        y = -11700 + 1800 * i + 900
        for x in (-16800, -17600):
            rect(msp, x - 300, y - 300, x + 300, y + 300, "MEP"); n_panel += 1
    for i in range(9):
        x = -11530 + 1800 * i + 700
        for y in (-16400, -17200):
            rect(msp, x - 300, y - 300, x + 300, y + 300, "MEP"); n_panel += 1
    for x in (15600, 17200, 18800):
        for y in (17000, 18600):
            rect(msp, x - 300, y - 300, x + 300, y + 300, "MEP"); n_panel += 1
    for x in (-9000, -3000, 3000, 9000):
        rect(msp, x - 300, 16600, x + 300, 17200, "MEP"); n_panel += 1
    for x in (-19600, -17600, -15600):
        rect(msp, x - 300, -17900, x + 300, -17300, "MEP"); n_panel += 1
    for y in (2000, 4200, 6400, 8600, 10800):
        circle(msp, 20800, y, 100); n_down += 1
    for x in range(-10800, 10900, 2400):
        circle(msp, x, 11750, 90); circle(msp, x, -11750, 90); n_down += 2
    for y in range(-9350, 9400, 2400):
        circle(msp, 11450, y, 90); circle(msp, -11450, y, 90); n_down += 2
    line(msp, 21300, 3000, 21300, 6600, "MEP"); line(msp, 21380, 3000, 21380, 6600, "MEP"); n_strip += 1
    # 培训室投影灯
    for x in (15800, 18600):
        circle(msp, x, 20000, 100); n_down += 1
    zone_short(msp)
    txt(msp, "灯具合计: 面板灯600x600 共%d盏  筒灯 共%d盏  展示灯带 %d条(3.6米)" % (n_panel, n_down, n_strip),
        -39500, -26500, 300, "TEXT", TA.BOTTOM_LEFT)
    mtxt(msp, "照明回路:\nL1 Z8办公区面板灯\nL2 Z9办公区面板灯\nL3 环廊筒灯(应急兼日常)\nL4 Z2培训室面板灯及投影灯\nL5 Z4展示灯带及射灯\nL6 Z10 Z11面板灯\n应急照明: 环廊筒灯及出口指示 双回路供电", -40500, 12000, 300, "TEXT")
    frame(msp, "PL-07", "灯具定位图")
    return doc, "PL-07_灯具定位图"

def build_PL08():
    doc = new_doc(); msp = doc.modelspace()
    skeleton(msp, doors=False)
    n_fb = n_ws = n_sp = 0
    # 工位地插: 每组1个
    for i in range(12):
        y = -11700 + 1800 * i + 840
        rect(msp, -17145, y, -17025, y + 120, "MEP"); n_fb += 1
    for i in range(9):
        x = -10630 + 3600 * i
        rect(msp, x, -17065, x + 120, -16945, "MEP"); n_fb += 1
    # 墙边插座
    for y in range(-12000, 13200, 3600):
        circle(msp, -21250, y, 90); n_ws += 1
    for x in range(-12000, 6600, 3600):
        circle(msp, x, -20850, 90); n_ws += 1
    for y in range(2000, 13600, 3600):
        circle(msp, 21450, y, 90); n_ws += 1
    # 专用插座
    sp = [(16500, 20650, "投影电源"), (14000, 14300, "白板电源"), (5100, 15000, "高桌插座"),
          (6300, 15000, "高桌插座"), (-10700, -16300, "高桌插座"), (-9500, -16300, "高桌插座"),
          (-20000, -20500, "茶水设备"), (-18000, -20500, "茶水设备"), (-16200, -20500, "茶水设备"),
          (19600, -5300, "复印机专插"), (20800, 4000, "展示灯带电源")]
    for x, y, s in sp:
        circle(msp, x, y, 110); txt(msp, s, x + 350, y + 100, 220, "TEXT", TA.BOTTOM_LEFT); n_sp += 1
    zone_short(msp)
    txt(msp, "点位合计: 工位地插 %d组(对应42固定工位)  墙边插座 %d个  专用插座 %d个" % (n_fb, n_ws, n_sp),
        -39500, -26500, 300, "TEXT", TA.BOTTOM_LEFT)
    mtxt(msp, "回路划分:\nW1 W2 Z8办公区地插及墙插\nW3 W4 Z9办公区地插及墙插\nW5 Z2培训室 投影 白板专用\nW6 茶水区设备专用\nW7 文印室复印机专用\nW8 展示前厅灯带及高桌临时席\n共享高桌插座为可变席位预留", -40500, 12000, 300, "TEXT")
    frame(msp, "PL-08", "插座定位图")
    return doc, "PL-08_插座定位图"

def build_PL09():
    doc = new_doc(); msp = doc.modelspace()
    skeleton(msp, doors=False)
    # 茶水区给排水
    circle(msp, -20050, -20600, 120)
    line(msp, -20170, -20600, -19930, -20600, "MEP")
    line(msp, -20050, -20720, -20050, -20480, "MEP")
    txt(msp, "给水J1 DN20", -20050, -20150, 260)
    circle(msp, -20050, -20700, 120)
    txt(msp, "排水P1 DN50", -20050, -21200, 260)
    circle(msp, -15800, -20650, 120)
    txt(msp, "地漏DN50", -15800, -21200, 260)
    line(msp, -15400, -20100, -12800, -20100, "MEP")
    msp.add_line((-13050, -20100), (-12800, -20100), dxfattribs={"layer": "MEP"})
    txt(msp, "排水坡度i=0.005 坡向排水立管", -14100, -19800, 240)
    txt(msp, "给水点标高 H+0.300 台盆处", -20050, -19700, 240)
    circle(msp, -12900, -20400, 140)
    txt(msp, "排水立管DN100 沿用原建筑", -12900, -21000, 240)
    zone_short(msp)
    mtxt(msp, "给排水说明:\n1 本图仅表达茶水区给排水点位, 其余区域沿用原建筑给排水系统, 不新增点位\n2 给水由原建筑立管引入 DN20 沿吊顶敷设 至台盆处\n3 排水 DN50 接原建筑排水立管 横管坡度 i=0.005\n4 地漏设于操作台端部 便于清洁排水\n5 热水由茶水间就地小型热水器提供", -40500, 12000, 300, "TEXT")
    frame(msp, "PL-09", "给排水点位图")
    return doc, "PL-09_给排水点位图"

# ---------------------------------------------------------------- PL-01: 改造 PoC 图（清掉乱码文字 重写规范标注）
def build_PL01():
    doc = ezdxf.readfile(POC_DXF)
    if STYLE not in doc.styles:
        doc.styles.add(STYLE, font="SimHei")
    msp = doc.modelspace()
    for e in list(msp.query("TEXT")):
        msp.delete_entity(e)
    for e in list(msp.query("MTEXT")):
        msp.delete_entity(e)
    zone_rich(msp)
    # 总尺寸数字
    txt(msp, "43160", 0, -23200, 350, "DIM")
    txt(msp, "41960", 24000, 0, 350, "DIM")
    # 分区一览表
    rows = [("Z1", "前台 导视等候", "49"), ("Z2", "培训 评审室", "56"),
            ("Z3", "小会议室", "24"), ("Z4", "展示接待前厅", "107"),
            ("Z5", "文印 归档", "32"), ("Z6", "电话亭 洽谈", "37"),
            ("Z7", "主管室 访客洽谈", "31"), ("Z8", "开放办公区A 24位", "231"),
            ("Z9", "开放办公区B 18位", "163"), ("Z10", "项目协作 共享图书", "198"),
            ("Z11", "茶水 员工交流", "57"), ("Z12", "设备储物 物流暂存", "40")]

    def dispw(s):  # 中文按2列宽计
        return sum(2 if ord(c) > 0x2E80 else 1 for c in s)

    def pad(s, w):
        return s + " " * max(0, w - dispw(s))

    txt(msp, "分区一览表", -40500, 22600, 550, "TEXT", TA.BOTTOM_LEFT)
    txt(msp, "区号  名称                 面积", -40500, 21400, 300, "TEXT", TA.BOTTOM_LEFT)
    y = 20500
    for c, n, a in rows:
        line = "%s %s %s平米" % (pad(c, 4), pad(n, 22), a.rjust(5))
        txt(msp, line, -40500, y, 300, "TEXT", TA.BOTTOM_LEFT)
        y -= 1400
    txt(msp, "合计 12个分区  固定工位42位  共享高桌4席", -40500, y - 200, 300, "TEXT", TA.BOTTOM_LEFT)
    txt(msp, "图例: 双线=墙体  虚线=玻璃隔断  绿色=家具  灰色=铺装填充", -40500, -25000, 300, "TEXT", TA.BOTTOM_LEFT)
    frame(msp, "PL-01", "平面布置图")   # PoC标题栏文字已随旧TEXT删除，此处按统一图框重写
    fix_style_fonts(doc)
    return doc, "PL-01_平面布置图"

# ---------------------------------------------------------------- 渲染
def render(doc, name):
    fig = plt.figure(figsize=(16.8, 11.9))
    ax = fig.add_axes([0, 0, 1, 1])
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE,
                        color_policy=ColorPolicy.BLACK,
                        text_policy=TextPolicy.IGNORE)  # ezdxf 跳过文字（字形有bug）
    ctx = RenderContext(doc)
    be = MatplotlibBackend(ax)
    Frontend(ctx, be, config=cfg).draw_layout(doc.modelspace(), finalize=True)
    # matplotlib 原生叠字：中文 100% 正确
    xlim = ax.get_xlim()
    ppx = (fig.get_figwidth() * 72.0) / (xlim[1] - xlim[0])
    for kind, s, x, y, h, al in getattr(doc, "overlay_texts", []):
        fs = max(2.0, h * ppx)
        if kind == "m":
            yy = y
            for ln in s.split("\n"):
                ax.text(x, yy, ln, ha="left", va="top", fontsize=fs,
                        fontproperties=CNF, color="black")
                yy -= h * 1.35
        else:
            if al == TA.MIDDLE_CENTER: ha, va = "center", "center"
            elif al == TA.BOTTOM_CENTER: ha, va = "center", "bottom"
            elif al == TA.BOTTOM_LEFT: ha, va = "left", "bottom"
            else: ha, va = "left", "bottom"
            ax.text(x, y, s, ha=ha, va=va, fontsize=fs,
                    fontproperties=CNF, color="black")
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=300, facecolor="white")
    fig.savefig(os.path.join(OUT, name + ".pdf"), facecolor="white")
    plt.close(fig)

BUILDERS = [build_PL01, build_PL02, build_PL04, build_PL05, build_PL06,
            build_PL15, build_PL07, build_PL08, build_PL09]

if __name__ == "__main__":
    for b in BUILDERS:
        doc, name = b()
        fix_style_fonts(doc)
        dxf = os.path.join(OUT, name + ".dxf")
        doc.saveas(dxf)
        try:
            render(doc, name)
            print("OK", name, "dxf+png+pdf")
        except Exception as ex:
            print("OK", name, "dxf  (渲染失败:", repr(ex)[:80], ")")
