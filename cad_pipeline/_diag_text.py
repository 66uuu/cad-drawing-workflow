# -*- coding: utf-8 -*-
import os, sys
import ezdxf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import student_master as MD

from config import ROOT as BASE
SRC = os.path.join(BASE, "04_节点图_四格式")

for fn in ["SD-03_培训室可移动玻璃隔断大样.dxf", "DT-02_茶水间涉水墙面防水节点.dxf",
           "EL-06_开放工位与共享高桌立面.dxf"]:
    code = fn.split("_")[0]
    S = MD.scale_of(code)
    doc = ezdxf.readfile(os.path.join(SRC, fn))
    msp = doc.modelspace()
    print("=" * 70)
    print(fn, "S=%d  (y模型值 ÷ %d = 纸面mm)" % (S, S))
    rows = []
    for e in msp:
        if e.dxftype() != "TEXT":
            continue
        try:
            t = e.dxf.text
            x, y = e.dxf.insert.x, e.dxf.insert.y
            h = e.dxf.height
            rot = e.dxf.rotation
        except Exception:
            continue
        rows.append((y, x, h, rot, str(t)))
    rows.sort(key=lambda r: (-r[0], r[1]))
    for y, x, h, rot, t in rows:
        print("  y=%7.0f(%6.1fmm) x=%7.0f(%6.1fmm) h=%.1f(% .2fmm) rot=%3.0f | %s"
              % (y, y / S, x, x / S, h, h / S, rot, t[:34]))
