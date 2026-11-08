# -*- coding: utf-8 -*-
# 薄包装：调用统一后端 dwg_convert.convert_dir（已处理 AutoCAD/ODA/纯DXF 三选一）
import os, sys
from config import ROOT
import dwg_convert

def main():
    # 平面 / 立面+节点+详图 各自的 DXF 目录
    targets = [ROOT / "02_平面图_四格式"]
    for t in targets:
        if t.exists():
            dwg_convert.convert_dir(str(t))
    # 也扫描本目录下其它含 DXF 的子目录（兜底）
    for d in sorted(os.listdir(ROOT)):
        p = ROOT / d
        if p.is_dir() and any(f.lower().endswith(".dxf") for f in os.listdir(p)) and p not in targets:
            dwg_convert.convert_dir(str(p))

if __name__ == "__main__":
    main()
