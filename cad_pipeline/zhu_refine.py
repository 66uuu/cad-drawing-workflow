# -*- coding: utf-8 -*-
"""
精细优化第二轮
==============
1. TEXT层中纯数字轴号（1-10, A/B等）→ 移到AXIS层
2. 节点图中短引出线（标注材料用的）→ WALL移到DIM
3. E-06核心筒：识别门、栏杆、轴号、尺寸线，精细分类
4. 节点图字高200mm→32mm（1:10比例下3.2mm纸面）
5. 立面图字高280mm→96mm（1:30比例下3.2mm纸面）
6. 平面组字高350mm→320mm（1:100比例下3.2mm纸面）
"""
import re
from pathlib import Path
from collections import Counter
import ezdxf

CLEAN = Path(__file__).resolve().parent / "_zhu_audit" / "cleaned_v2"
CLEAN.mkdir(exist_ok=True)
SRC = Path(__file__).resolve().parent / "_zhu_audit" / "cleaned"

def is_axis_number(txt):
    """判断是否为轴号文字（纯数字1-15，或A/B/C等字母轴号）"""
    t = txt.strip()
    if re.match(r'^\d{1,2}$$', t):
        n = int(t)
        return 1 <= n <= 20
    if re.match(r'^[A-Z]$$', t) and len(t) == 1:
        return True
    return False

def classify_node_line(e, all_lines):
    """节点图中判断一条线属于哪类"""
    s, en = e.dxf.start, e.dxf.end
    length = ((en.x-s.x)**2 + (en.y-s.y)**2)**0.5
    # 短水平线（<500mm）大概率是材料标注引出线 → DIM
    if length < 500 and abs(en.y - s.y) < 50:
        return "DIM"
    # 短竖线（<500mm）也可能是引出线
    if length < 500 and abs(en.x - s.x) < 50:
        return "DIM"
    # 长墙线归WALL
    return "WALL"

def optimize_dxf(in_path, out_path):
    doc = ezdxf.readfile(in_path)
    msp = doc.modelspace()
    fname = in_path.name

    # 判断图纸类型
    is_plan = fname.startswith(("0","办公")) and not fname.startswith(("E-","N-"))
    is_elev = fname.startswith("E-")
    is_node = fname.startswith("N-")

    stats = Counter()

    # 1. TEXT层中的轴号数字 → AXIS层
    for e in msp:
        if e.dxf.layer == "TEXT" and e.dxftype() == "TEXT":
            txt = e.dxf.text.strip()
            if is_axis_number(txt):
                e.dxf.layer = "AXIS"
                stats["axis_numbers_moved"] += 1

    # 2. E-06核心筒立面图精细分类
    if "E-06" in fname:
        for e in msp:
            if e.dxf.layer != "WALL":
                continue
            t = e.dxftype()
            if t == "LINE":
                s, en = e.dxf.start, e.dxf.end
                length = ((en.x-s.x)**2 + (en.y-s.y)**2)**0.5
                # 很短的线（<200mm）大概率是标注线 → DIM
                if length < 200:
                    e.dxf.layer = "DIM"
                    stats["e06_dim_lines"] += 1
                # 水平线在底部（y<0）→ 地面线归WALL
                elif s.y < 0 and abs(en.y - s.y) < 10:
                    e.dxf.layer = "WALL"
            elif t == "CIRCLE":
                # 小圆圈在AXIS层（之前可能被分到MEP）
                e.dxf.layer = "AXIS"
                stats["e06_axis_circles"] += 1

    # 3. 节点图：短引出线从WALL移到DIM
    if is_node:
        for e in msp:
            if e.dxf.layer == "WALL" and e.dxftype() == "LINE":
                s, en = e.dxf.start, e.dxf.end
                length = ((en.x-s.x)**2 + (en.y-s.y)**2)**0.5
                # 短水平线或短竖线（<600mm）是材料标注引出线
                if length < 600:
                    e.dxf.layer = "DIM"
                    stats["node_dim_lines"] += 1

    # 4. 统一字高（按图纸类型设定目标模型字高）
    if is_plan:
        target_h = 320  # 1:100 → 纸面3.2mm
        small_h = 280
    elif is_elev:
        target_h = 96   # 1:30 → 纸面3.2mm
        small_h = 84
    elif is_node:
        target_h = 32   # 1:10 → 纸面3.2mm
        small_h = 28
    else:
        target_h = 320
        small_h = 280

    for e in msp:
        if e.dxftype() == "TEXT":
            try:
                h = e.dxf.height
                txt = e.dxf.text.strip()
                # 图名（大字号）保持
                if "图" in txt and len(txt) < 15:
                    continue
                # 图号 E-01, N-01 等保持
                if re.match(r'^[A-Z]-\d{2}$', txt):
                    continue
                # 比例 1:100 等保持
                if "1:" in txt:
                    continue
                # 其他文字缩放到目标字高
                if h > 0:
                    # 按比例缩放：从原h到target_h
                    scale = target_h / h
                    # 小字（标注、明细）用small_h
                    if h < 250 and is_plan:
                        e.dxf.height = small_h
                    elif h < 250 and is_elev:
                        e.dxf.height = small_h
                    elif h < 250 and is_node:
                        e.dxf.height = small_h
                    else:
                        e.dxf.height = target_h
                    stats["text_resized"] += 1
            except Exception:
                pass

    doc.saveas(out_path)
    return stats

# 批量处理
for p in sorted(SRC.glob("*.dxf")):
    out = CLEAN / p.name
    stats = optimize_dxf(p, out)
    print("%-45s %s" % (p.name, dict(stats) if stats else "(无改动)"))

print("\n输出:", CLEAN)
