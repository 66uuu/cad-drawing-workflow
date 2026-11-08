# -*- coding: utf-8 -*-
"""
朱文件夹 DXF 标准化清洗脚本
============================
按 9+1 标准图层重分类、统一颜色线宽线型、修正文字样式。
几何内容不动，只动图层归属和图层属性。
"""
import shutil
from pathlib import Path
from collections import Counter
import ezdxf
from ezdxf.enums import TextEntityAlignment

DXF_IN = Path(__file__).resolve().parent / "_zhu_audit" / "dxf"
DXF_OUT = Path(__file__).resolve().parent / "_zhu_audit" / "cleaned"
DXF_OUT.mkdir(parents=True, exist_ok=True)

# ============ 标准图层定义 ============
# (name, color_aci, lineweight_mm, linetype)
STANDARD_LAYERS = {
    "AXIS":      (3,  15,  "CENTER"),     # 绿, 0.15mm, 点划线
    "WALL":      (7,  50,  "Continuous"), # 白, 0.50mm
    "COLUMN":    (7,  50,  "Continuous"), # 白, 0.50mm
    "DOOR_WIN":  (4,  25,  "Continuous"), # 青, 0.25mm
    "FURNITURE": (4,  25,  "Continuous"), # 青, 0.25mm
    "MEP":       (6,  9,   "Continuous"), # 紫, 0.09mm
    "DIM":       (3,  9,   "Continuous"), # 绿, 0.09mm
    "TEXT":      (2,  9,   "Continuous"), # 黄, 0.09mm
    "HATCH":     (9,  9,   "Continuous"), # 灰, 0.09mm
    "FRAME":     (7,  9,   "Continuous"), # 白, 0.09mm
}

# ============ 旧图层 → 标准图层 映射表 ============
# 平面组通用映射
PLAN_MAP = {
    "0":          None,      # 0层特殊处理
    "AXIS":       "AXIS",
    "WALL":       "WALL",
    "WALL_IN":    "WALL",    # 内墙合并到WALL
    "COLUMN":     "COLUMN",
    "DOOR":       "DOOR_WIN",
    "WINDOW":     "DOOR_WIN",
    "STAIR":      "WALL",    # 楼梯归结构墙
    "FURN":       "FURNITURE",
    "FURNITURE":  "FURNITURE",
    "DIM":        "DIM",
    "TEXT":       "TEXT",
    "SYM":        "MEP",     # 符号层→机电
    "HATCH":      "HATCH",
    "CEIL":       "MEP",     # 天花机电末端
    "LEGEND":     "TEXT",    # 图例归文字
    "ELEV":       "DIM",     # 标高归DIM
    "TOILET":     "FURNITURE",
    "Defpoints":  "Defpoints",
}

# 立面组映射
ELEV_MAP = dict(PLAN_MAP)
ELEV_MAP.update({
    "WIN":        "DOOR_WIN",
    "FLOOR":      "WALL",    # 楼面线归WALL
})

# 节点组：大部分在0层，需要按实体类型分
NODE_MAP = {
    "0":          None,
    "Defpoints":  "Defpoints",
}

# 修正版平面图（特殊）
FIXED_MAP = dict(PLAN_MAP)
FIXED_MAP.update({
    "ELEV":       "DIM",
    "TOILET":     "FURNITURE",
})

# 按文件名前缀判断用哪张映射
def pick_map(fname):
    if fname.startswith("N-"):
        return NODE_MAP, "node"
    if fname.startswith("E-"):
        return ELEV_MAP, "elev"
    if "轴网尺寸修正版" in fname:
        return FIXED_MAP, "plan_fixed"
    return PLAN_MAP, "plan"


def ensure_standard_layers(doc):
    """确保10个标准图层都存在，设置好颜色线宽线型"""
    # 先确保CENTER线型存在
    if "CENTER" not in doc.linetypes:
        try:
            doc.linetypes.add("CENTER", pattern="A,12.5,-3.125", description="____ . ____ . ____")
        except Exception:
            pass  # 可能已存在或无法加载

    for name, (color, lw, lt) in STANDARD_LAYERS.items():
        if name not in doc.layers:
            doc.layers.add(name)
        ly = doc.layers.get(name)
        ly.dxf.color = color
        # lineweight 单位是 0.01mm（AutoCAD约定），所以 0.50mm = 50
        try:
            ly.dxf.lineweight = lw
        except Exception:
            pass
        try:
            ly.dxf.linetype = lt
        except Exception:
            pass


def classify_zero_layer_entity(e):
    """对0层实体按类型智能分类"""
    t = e.dxftype()
    if t in ("TEXT", "MTEXT"):
        return "TEXT"
    if t == "DIMENSION":
        return "DIM"
    if t == "HATCH":
        return "HATCH"
    if t == "INSERT":
        return "FURNITURE"
    if t == "CIRCLE":
        # 小圆可能是轴网圆圈
        r = e.dxf.radius
        if r < 200:  # 小圆圈
            return "AXIS"
        return "MEP"
    if t == "ARC":
        return "DOOR_WIN"  # 门弧
    if t in ("LINE", "LWPOLYLINE", "POLYLINE"):
        # 节点图中大部分线是构造剖面线→WALL
        return "WALL"
    return "WALL"  # 默认归WALL


def clean_dxf(in_path, out_path):
    doc = ezdxf.readfile(in_path)
    msp = doc.modelspace()
    fname = in_path.name
    layer_map, kind = pick_map(fname)

    # 1. 确保标准图层存在
    ensure_standard_layers(doc)

    # 2. 遍历实体，重新分配图层
    moved = Counter()
    zero_classified = Counter()
    for e in msp:
        old_layer = e.dxf.layer
        if old_layer in layer_map:
            new_layer = layer_map[old_layer]
            if new_layer is None:
                # 0层实体→智能分类
                new_layer = classify_zero_layer_entity(e)
                zero_classified[new_layer] += 1
            if new_layer != old_layer:
                e.dxf.layer = new_layer
                moved[(old_layer, new_layer)] += 1
        else:
            # 未知图层名，尝试模糊匹配
            upper = old_layer.upper()
            if upper.startswith("AXIS"):
                e.dxf.layer = "AXIS"
                moved[(old_layer, "AXIS")] += 1
            elif upper.startswith("WALL"):
                e.dxf.layer = "WALL"
                moved[(old_layer, "WALL")] += 1
            elif upper.startswith("DIM"):
                e.dxf.layer = "DIM"
                moved[(old_layer, "DIM")] += 1
            elif upper.startswith("TEXT") or upper == "STANDARD":
                e.dxf.layer = "TEXT"
                moved[(old_layer, "TEXT")] += 1
            else:
                # 未知图层→默认WALL
                e.dxf.layer = "WALL"
                moved[(old_layer, "WALL")] += 1

    # 3. 统一文字样式：所有TEXT/MTEXT用HEI样式（如果存在）
    # 先创建HEI样式
    if "HEI" not in doc.styles:
        try:
            doc.styles.add("HEI", font="simhei.ttf")
        except Exception:
            pass
    if "XZC" not in doc.styles:
        try:
            doc.styles.add("XZC", font="simplex.shx")
        except Exception:
            pass

    text_style_fixed = 0
    for e in msp:
        if e.dxftype() in ("TEXT", "MTEXT"):
            try:
                old_style = e.dxf.style
                # 尺寸数字（短数字、标高数字）用XZC，其他用HEI
                txt = e.dxf.text if e.dxftype() == "TEXT" else e.text
                if txt and any(c.isdigit() for c in txt) and len(txt) < 20:
                    e.dxf.style = "XZC"
                else:
                    e.dxf.style = "HEI"
                text_style_fixed += 1
            except Exception:
                pass

    # 4. 删除空的旧图层（非标准、非Defpoints、非0层）
    removed_layers = []
    standard_set = set(STANDARD_LAYERS.keys()) | {"Defpoints", "0"}
    for layer in list(doc.layers):
        name = layer.dxf.name
        if name not in standard_set:
            # 检查是否还有实体在该层
            try:
                doc.layers.remove(name)
                removed_layers.append(name)
            except Exception:
                pass  # 图层非空或被引用，保留

    # 5. 保存
    doc.saveas(out_path)

    return {
        "file": fname,
        "kind": kind,
        "moved": dict(moved),
        "zero_classified": dict(zero_classified),
        "text_style_fixed": text_style_fixed,
        "removed_layers": removed_layers,
    }


# ============ 批量执行 ============
results = []
for p in sorted(DXF_IN.glob("*.dxf")):
    out = DXF_OUT / p.name
    print("清洗:", p.name)
    try:
        r = clean_dxf(p, out)
        results.append(r)
        print("  移动:", r["moved"])
        print("  0层分类:", r["zero_classified"])
        print("  文字样式:", r["text_style_fixed"])
        print("  删除图层:", r["removed_layers"])
    except Exception as e:
        import traceback
        print("  ERROR:", e)
        traceback.print_exc()
        results.append({"file": p.name, "error": str(e)})

print("\n=== 清洗完成 ===")
print("输出目录:", DXF_OUT)
print("成功:", sum(1 for r in results if "error" not in r), "/", len(results))
