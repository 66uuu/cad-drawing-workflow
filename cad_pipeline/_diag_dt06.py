# -*- coding: utf-8 -*-
import os, sys
import ezdxf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import student_master as MD

from config import ROOT as BASE
SRC = os.path.join(BASE, "04_节点图_四格式")
fn = "DT-06_金属踢脚线收口节点.dxf"
S = MD.scale_of("DT-06")
doc = ezdxf.readfile(os.path.join(SRC, fn))
msp = doc.modelspace()
print("S=", S)
for e in msp:
    if e.dxftype() != "TEXT":
        continue
    x, y = e.dxf.insert.x, e.dxf.insert.y
    if not (-600 < x < 100 and -400 < y < 500):
        continue
    print("  layer=%-6s x=%7.0f(%6.1fmm) y=%7.0f(%6.1fmm) h=%.1f rot=%3.0f | %s"
          % (e.dxf.layer, x, x / S, y, y / S, e.dxf.height, e.dxf.rotation, str(e.dxf.text)[:30]))
