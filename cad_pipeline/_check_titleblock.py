# -*- coding: utf-8 -*-
"""抽查图签信息：确认姓名/学号/班级/指导教师/日期 已全量换成新信息。"""
import os, sys, glob
import ezdxf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ROOT as BASE
DIRS = ["02_平面图_四格式", "03_立面图_四格式",
        "04_节点图_四格式", "05_大样图_四格式"]

# 图签期望值不再硬编码：直接取自唯一数据源 student_master（换人/换号只改那边）
import student_master as MD
WANT = {MD.STUDENT, MD.STUDENT_ID, MD.CLASS_NAME, MD.TEACHER, MD.DATE}
# 上一版个人信息已脱敏清除，旧信息残留检查保留机制、置空集合
OLD = set()

for d in DIRS:
    p = os.path.join(BASE, d)
    files = sorted(glob.glob(os.path.join(p, "*.dxf")))
    if not files:
        print("[空] %s" % d)
        continue
    for f in files[:2]:
        doc = ezdxf.readfile(f)
        msp = doc.modelspace()
        hits_want, hits_old = set(), set()
        for e in msp:
            if e.dxftype() == "INSERT":
                for a in e.attribs:
                    v = str(a.dxf.text)
                    for w in WANT:
                        if w in v:
                            hits_want.add(w)
                    for o in OLD:
                        if o in v:
                            hits_old.add(o)
            elif e.dxftype() == "TEXT":
                v = str(e.dxf.text)
                for w in WANT:
                    if w in v:
                        hits_want.add(w)
                for o in OLD:
                    if o in v:
                        hits_old.add(o)
        print("%-16s %-34s 新信息=%s  旧信息残留=%s"
              % (d, os.path.basename(f)[:30],
                 ",".join(sorted(hits_want)) or "无",
                 ",".join(sorted(hits_old)) or "无"))
