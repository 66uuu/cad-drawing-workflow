# -*- coding: utf-8 -*-
"""
run_all.py — 一键出图编排（跨电脑一致的执行顺序）
=================================================
顺序：build(平面/立面/节点/详图) → DXF→DWG 转换 → AUDIT 校验 → verify 复检 → 打包前自检。

用法：
    python run_all.py              # 全流程
    python run_all.py --build      # 只出 DXF/PDF/PNG，不转 DWG
    python run_all.py --convert    # 只对已有 DXF 转 DWG
    python run_all.py --verify     # 只跑复检

前置：先跑过 setup_env.py（建好 .venv + 字体）。
"""
import os
import sys
import glob
import subprocess
from pathlib import Path

import config

ROOT = config.ROOT
VENV = ROOT / ".venv"
PY = (VENV / "Scripts" / "python.exe") if os.name == "nt" else (VENV / "bin" / "python")


def run_script(script_name, *extra):
    sp = ROOT / script_name
    if not sp.exists():
        print("[跳过] 不存在: %s" % script_name)
        return
    print("\n===== 运行 %s =====" % script_name)
    subprocess.run([str(PY), str(sp), *extra], cwd=str(ROOT), check=False)


def find_dxf_dirs():
    """返回 cad_pipeline 下所有含 .dxf 的子目录（即各出图目录）。"""
    out = []
    for d in sorted(os.listdir(ROOT)):
        p = ROOT / d
        if p.is_dir() and any(f.lower().endswith(".dxf") for f in os.listdir(p)):
            out.append(p)
    return out


def build():
    # 平面（生产版 v2 —— 单一数据源 student_master，零偏差基准）
    run_script("build_9plans_同学版_v2.py")
    # 补充平面 7 张（PL-00 目录 / PL-03 分区 / PL-10 消防 / PL-11 索引 /
    #                PL-12 动线 / PL-13 配套 / PL-14 排版）
    run_script("build_7extra_plans.py")
    # 立面 / 节点大样 / 详图（生产版）
    run_script("build_18drawings_同学版.py")
    # 说明：build_9plans_同学版.py（旧版）与 build_PL01_同学版.py（PoC 试片）
    # 已被 v2 / 18drawings 取代，且旧版会写同一 02_平面图_四格式 目录覆盖 v2 成果，
    # 故默认编排不运行它们。如需重跑试片，可单独：
    #   .venv/Scripts/python.exe build_PL01_同学版.py


def convert():
    dirs = find_dxf_dirs()
    if not dirs:
        print("[!] 没找到任何含 DXF 的目录，先跑 --build")
        return
    for d in dirs:
        print("\n===== DXF→DWG: %s =====" % d.name)
        subprocess.run([str(PY), "-c",
                        "import dwg_convert,sys; dwg_convert.convert_dir(sys.argv[1])",
                        str(d)], cwd=str(ROOT), check=False)


def audit():
    dirs = find_dxf_dirs()
    for d in dirs:
        print("\n===== AUDIT: %s =====" % d.name)
        subprocess.run([str(PY), "-c",
                        "import dwg_convert,sys; dwg_convert.audit_dir(sys.argv[1])",
                        str(d)], cwd=str(ROOT), check=False)


def verify():
    for s in ("verify_9plans.py", "verify_18drawings.py",
             "verify_dwg_9plans.py", "verify_dwg_18drawings.py",
             "_check_titleblock.py"):
        run_script(s)


def main():
    args = sys.argv[1:]
    if not PY.exists():
        print("[!!] 未检测到 .venv，请先运行： python setup_env.py")
        sys.exit(1)

    only_build = "--build" in args
    only_convert = "--convert" in args
    only_verify = "--verify" in args

    if only_convert:
        convert(); audit(); return
    if only_verify:
        verify(); return
    if only_build:
        build(); return

    build()
    convert()
    audit()
    verify()
    print("\n===== 全部完成 =====")
    print("DXF/PDF/PNG 必定产出；DWG 取决于本机是否装有 AutoCAD/ODA（见 config 自检）。")


if __name__ == "__main__":
    main()
