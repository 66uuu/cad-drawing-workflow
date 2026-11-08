# -*- coding: utf-8 -*-
"""
setup_env.py — 一键把工作流装到「当前这台电脑」（跨电脑复现的第 0 步）
=====================================================================
在任何一台新电脑上，只需：
    python setup_env.py
即可：
  1. 在 cad_pipeline/ 内建一个隔离 .venv（不污染系统 Python）
  2. 安装 requirements.txt 里的依赖（ezdxf / matplotlib / Pillow）
  3. 把系统里的中文字体（simhei.ttf / simplex_.ttf / msyh.ttc）拷贝进 fonts/
     —— 这样换电脑后中文/尺寸数字渲染完全一致，不依赖目标机恰好装有这些字体
  4. 自动探测 AutoCAD / ODA（决定能否生成 DWG）
  5. 跑 _selfcheck.py 验证整条链能 import、数据源断言通过、字体就位

注意：本脚本用「运行它的那个 Python」去建 venv 和装包。建议用 3.10+ 的 python。
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PY = (VENV / "Scripts" / "python.exe") if os.name == "nt" else (VENV / "bin" / "python")
REQ = ROOT / "requirements.txt"
SELFCHECK = ROOT / "_selfcheck.py"

# 需要从系统拷贝进 fonts/ 的字体（文件名固定，随包走）
FONT_FILES = ["simhei.ttf", "simplex_.ttf", "msyh.ttc"]


def step(msg):
    print("\n>>> " + msg)


def run(cmd):
    print("  $ " + " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def make_venv():
    if PY.exists():
        print("  .venv 已存在，跳过创建")
        return
    step("1/5 创建隔离虚拟环境 .venv")
    run([sys.executable, "-m", "venv", str(VENV)])


def install():
    step("2/5 安装依赖（ezdxf / matplotlib / Pillow）")
    run([str(PY), "-m", "pip", "install", "--upgrade", "pip", "-q"])
    run([str(PY), "-m", "pip", "install", "-r", str(REQ), "-q"])


def bundle_fonts():
    step("3/5 打包字体到 fonts/（保证跨电脑一致）")
    import config  # 同目录可直接 import
    sys_font_dir = config.SYSTEM_FONT_DIR
    fonts_dir = ROOT / "fonts"
    fonts_dir.mkdir(exist_ok=True)
    if not sys_font_dir:
        print("  [!] 未找到系统字体目录，无法自动拷贝。请手动把以下文件放到 fonts/：")
        for f in FONT_FILES:
            print("      - %s" % f)
        return
    for f in FONT_FILES:
        src = os.path.join(sys_font_dir, f)
        dst = fonts_dir / f
        if dst.exists():
            print("  [ok] fonts/%s 已存在，跳过" % f)
            continue
        if os.path.exists(src):
            shutil.copy(src, dst)
            print("  [拷贝] %s -> fonts/%s" % (src, f))
        else:
            print("  [!] 系统缺失 %s，请手动补齐（否则中文/尺寸数字渲染可能异常）" % f)


def detect_backend():
    step("4/5 探测 DWG 后端（AutoCAD / ODA / 纯 DXF）")
    import config
    bk, path = config.dwg_backend()
    if bk == "dxf_only":
        print("  [提示] 未检测到 AutoCAD 或 ODA File Converter。")
        print("         DWG 暂不会生成；DXF 仍是权威交换格式。")
        print("         若要 DWG，请安装 AutoCAD（设环境变量 ACCORECONSOLE 指向 accoreconsole.exe）")
        print("         或安装免费 ODA File Converter（设 ODA_FILE_CONVERTER）。")
    else:
        print("  [ok] DWG 后端 = %s : %s" % (bk, path))


def selfcheck():
    step("5/5 跑 _selfcheck.py 验证整链")
    run([str(PY), str(SELFCHECK)])


def main():
    step("== cad_pipeline 安装到本机 ==")
    make_venv()
    install()
    bundle_fonts()
    detect_backend()
    selfcheck()
    step("== 完成 ==")
    print("下一步：运行  python run_all.py   即可一键出图（或分步运行各 build_*.py）。")


if __name__ == "__main__":
    main()
