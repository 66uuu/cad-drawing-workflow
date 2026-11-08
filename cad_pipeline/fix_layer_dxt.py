# -*- coding: utf-8 -*-
"""修复 V3.3 图层错误：把 PL-12/PL-14 中放错到 DIM 层的 SOLID 填充移到 HATCH 层。
   先备份原 DXF/DWG，再改 DXF，再重生成 DWG。"""
import os
import shutil
import sys
import time
from pathlib import Path
import ezdxf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

PLANS = Path(r"D:/UserFiles/Desktop/V3.3最终版/02_施工图/01_平面")
BK = Path(r"D:/UserFiles/Desktop/V3.3最终版/99_工具与数据/图层修复备份_20261102")
BK.mkdir(parents=True, exist_ok=True)

TARGETS = [
    "2402060131_蔡志成_动线设计图_PL-12_v2",
    "2402060131_蔡志成_地面排版图_PL-14_v2",
]

results = []
for base in TARGETS:
    dxf = PLANS / (base + ".dxf")
    dwg = PLANS / (base + ".dwg")
    # 1) 备份
    for f in (dxf, dwg):
        if f.exists():
            shutil.copy2(f, BK / f.name)
    # 2) 改 DXF
    doc = ezdxf.readfile(dxf)
    msp = doc.modelspace()
    moved = 0
    for e in msp:
        if e.dxftype() == "HATCH" and e.dxf.layer == "DIM":
            e.dxf.layer = "HATCH"
            moved += 1
    doc.saveas(dxf)
    # 3) 重生成 DWG
    import dwg_convert  # noqa: E402
    if dwg.exists():
        os.remove(dwg)
    ok, msg = dwg_convert.convert_one(str(dxf), str(dwg))
    results.append((base, moved, ok, msg))
    print("%-40s 移动填充=%d  DWG重生成=%s %s" % (base, moved, "OK" if ok else "FAIL", msg))
    time.sleep(1)

print("\n完成。备份目录:", BK)
