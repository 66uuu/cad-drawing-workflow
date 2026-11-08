# -*- coding: utf-8 -*-
# 薄包装：调用统一后端 dwg_convert.audit_dir（无 AutoCAD 时跳过并提示）
import os
from config import ROOT
import dwg_convert

def main():
    targets = [ROOT / "02_平面图_四格式"]
    for t in targets:
        if t.exists():
            dwg_convert.audit_dir(str(t))
    for d in sorted(os.listdir(ROOT)):
        p = ROOT / d
        if p.is_dir() and any(f.lower().endswith(".dwg") for f in os.listdir(p)) and p not in targets:
            dwg_convert.audit_dir(str(p))

if __name__ == "__main__":
    main()
