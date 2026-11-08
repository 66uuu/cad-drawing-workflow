# -*- coding: utf-8 -*-
import os, sys
import ezdxf
from ezdxf.bbox import extents
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import student_master as MD

from config import ROOT as BASE
SRC = os.path.join(BASE, "04_节点图_四格式")

for fn in ["DT-01_吊顶与幕墙交接节点.dxf", "EL-01_前台导视墙与等候区立面.dxf",
           "SD-01_标准固定工位大样.dxf"]:
    p = os.path.join(SRC, fn)
    code = fn.split("_")[0]
    S = MD.scale_of(code)
    doc = ezdxf.readfile(p)
    msp = doc.modelspace()
    ents = [e for e in msp if e.dxf.layer != "FRAME" and e.dxftype() != "ATTRIB"]
    bb = extents(ents, fast=True)
    fi = None
    for e in msp:
        if e.dxf.layer == "FRAME" and e.dxftype() == "INSERT":
            fi = e
            break
    print("=" * 66)
    print(fn, "S=", S)
    print("  内容bbox min=(%.0f,%.0f) max=(%.0f,%.0f)  尺寸=%.1fx%.1f mm"
          % (bb.extmin.x, bb.extmin.y, bb.extmax.x, bb.extmax.y,
             (bb.extmax.x-bb.extmin.x)/S, (bb.extmax.y-bb.extmin.y)/S))
    if fi:
        fx, fy = fi.dxf.insert.x, fi.dxf.insert.y
        fs = fi.dxf.xscale
        print("  图框 insert=(%.0f,%.0f) scale=%.0f" % (fx, fy, fs))
        print("  可用区(模型) x[%.0f,%.0f] y[%.0f,%.0f]"
              % (fx+10*fs, fx+404*fs, fy+10*fs, fy+410*fs))
        print("  越界: 左%.1f 下%.1f 右%.1f 上%.1f (mm)"
              % ((fx+10*fs-bb.extmin.x)/S, (fy+10*fs-bb.extmin.y)/S,
                 (bb.extmax.x-(fx+404*fs))/S, (bb.extmax.y-(fy+410*fs))/S))
        # 找出最底下的实体
        lowest = sorted(ents, key=lambda e: extents([e], fast=True).extmin.y)[:3]
        for e in lowest:
            eb = extents([e], fast=True)
            t = e.dxf.text if e.dxftype() == "TEXT" else e.dxftype()
            print("    最低实体 %s %s y=%.0f" % (e.dxf.layer, str(t)[:20], eb.extmin.y))
