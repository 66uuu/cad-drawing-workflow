# -*- coding: utf-8 -*-
"""
config.py — 跨电脑可复现的「唯一解耦点」
=========================================
本工作流搬到任何一台电脑、换任何一个账号，都只改这一个文件（或什么都不改，靠自动探测）。

职责：
  1. ROOT          —— 整个 cad_pipeline 目录（所有输出都落在此目录内，整包可随意移动/拷贝）
  2. 字体解析      —— 优先用包内 fonts/，回退系统字体目录；保证中文/尺寸数字渲染一致
  3. AutoCAD/ODA   —— 自动探测 accoreconsole / ODA File Converter，找不到则降级为「纯 DXF」
  4. 临时工作区    —— 用系统临时目录，绝不硬编码 C:\\wbtmp9 之类

设计原则：脚本里**禁止**再出现任何绝对盘符路径（C:/ D:/ C:\\ <D盘>\\）、任何字体文件名硬编码。
所有路径都从本文件取。
"""
import os
import sys
import glob
import tempfile
import shutil
import subprocess
from pathlib import Path

# ------------------------------------------------------------------------ 根目录
# __file__ 所在目录即 cad_pipeline/。整套输出（02_平面图_四格式 …）都放在它下面，
# 这样把 cad_pipeline 整个文件夹拷到别的电脑，路径关系完全不变。
ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT  # 所有 .py 脚本与本文件同目录，互相 import 即可

# 字体目录（包内自带，随包走）与资产目录（核心筒源底图等）
FONTS_DIR = ROOT / "fonts"
ASSETS_DIR = ROOT / "assets"

# 临时工作区：每次运行新建一个系统临时目录，避免硬编码盘符 + 避免跨盘移动 OSError
WORK = Path(tempfile.mkdtemp(prefix="cad_wb_"))

# ------------------------------------------------------------------------ 字体解析
def _system_font_dir():
    """按操作系统返回系统字体目录（找不到返回 None）。"""
    if os.name == "nt":
        d = os.environ.get("SystemRoot", "C:/Windows")
        p = os.path.join(d, "Fonts")
        return p if os.path.isdir(p) else None
    if sys.platform == "darwin":
        return "/System/Library/Fonts"
    # Linux / 其他
    for cand in ("/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts")):
        if os.path.isdir(cand):
            return cand
    return None

SYSTEM_FONT_DIR = _system_font_dir()

def _resolve_font(filename, extra_system_dirs=None):
    """
    解析一个字体文件：
      1) 包内 fonts/<filename> 优先（随包走，保证跨电脑一致）
      2) 系统字体目录
      3) 额外指定的系统目录
      4) 都找不到 → 只返回文件名，交给 ezdxf/PIL 默认扫描（缺失时会告警，但不致命）
    """
    p = FONTS_DIR / filename
    if p.exists():
        return str(p)
    dirs = []
    if SYSTEM_FONT_DIR:
        dirs.append(SYSTEM_FONT_DIR)
    if extra_system_dirs:
        dirs.extend(extra_system_dirs)
    for d in dirs:
        cand = os.path.join(d, filename)
        if os.path.exists(cand):
            return cand
    # 最后兜底：返回文件名，依赖程序内置字体表
    return filename

# 三个关键字体（文件名固定，文件本身放在 fonts/ 里随包走）
HEI_FONT  = _resolve_font("simhei.ttf")    # 黑体：房间名/图签中文
XZC_FONT  = _resolve_font("simplex_.ttf")  # 尺寸数字（AutoCAD 标准形字体，TTF 替代）
MSYH_FONT = _resolve_font("msyh.ttc")      # 微软雅黑：PNG 预览叠字用

# ezdxf 字体扫描目录：包内 fonts 必扫，系统目录有则扫；保证 simhei/simplex 能被找到
FONT_SCAN_DIRS = [str(FONTS_DIR)]
if SYSTEM_FONT_DIR:
    FONT_SCAN_DIRS.append(SYSTEM_FONT_DIR)

# ------------------------------------------------------------------------ 后端探测
def _detect_accore():
    """
    探测 AutoCAD 无头转换器 accoreconsole.exe：
      1) 环境变量 ACCORECONSOLE 优先（用户可手动指定）
      2) 常见安装位置（覆盖 2021~2026 多版本 + 非 C 盘安装）
      3) Program Files / 常见自定义盘符通配
    找不到返回 None。
    """
    env = os.environ.get("ACCORECONSOLE")
    if env and os.path.exists(env):
        return env
    candidates = [
        r"D:/CAD2024/AutoCAD 2024/accoreconsole.exe",
        r"C:/Program Files/Autodesk/AutoCAD 2026/accoreconsole.exe",
        r"C:/Program Files/Autodesk/AutoCAD 2025/accoreconsole.exe",
        r"C:/Program Files/Autodesk/AutoCAD 2024/accoreconsole.exe",
        r"C:/Program Files/Autodesk/AutoCAD 2023/accoreconsole.exe",
        r"C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe",
        r"C:/Program Files/Autodesk/AutoCAD 2021/accoreconsole.exe",
        r"C:/Program Files/Autodesk/AutoCAD/accoreconsole.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # 通配兜底
    for pat in [
        r"C:/Program Files/Autodesk/AutoCAD */accoreconsole.exe",
        r"D:/CAD*/accoreconsole.exe",
        r"E:/CAD*/accoreconsole.exe",
        r"D:/AutoCAD*/accoreconsole.exe",
    ]:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]  # 取版本号最大的
    return None

def _detect_oda():
    """
    探测 ODA File Converter（免费、跨平台，可从官网下载安装）：
      1) 环境变量 ODA_FILE_CONVERTER 优先
      2) 常见安装位置通配
    找不到返回 None。
    """
    env = os.environ.get("ODA_FILE_CONVERTER")
    if env and os.path.exists(env):
        return env
    for pat in [
        r"C:/Program Files/ODA/ODA File Converter */ODAFileConverter.exe",
        r"C:/Program Files (x86)/ODA/ODA File Converter */ODAFileConverter.exe",
        r"D:/ODA/ODA File Converter */ODAFileConverter.exe",
    ]:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    # Linux / macOS
    for pat in ["/usr/bin/ODAFileConverter", "/opt/oda/*/ODAFileConverter",
                "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter"]:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None

ACCORE = _detect_accore()
ODA = _detect_oda()

def dwg_backend():
    """返回当前可用的 DWG 后端：(名称, 可执行路径)。优先级：AutoCAD > ODA > 纯 DXF。"""
    if ACCORE:
        return ("autocad", ACCORE)
    if ODA:
        return ("oda", ODA)
    return ("dxf_only", None)

# ------------------------------------------------------------------------ 便捷：输出目录
def out_dir(sub):
    """cad_pipeline 内的输出子目录（如 '02_平面图_四格式'）。"""
    return ROOT / sub

# ------------------------------------------------------------------------ 自检信息
def report():
    bk, path = dwg_backend()
    lines = [
        "== cad_pipeline config 自检 ==",
        "ROOT        : %s" % ROOT,
        "FONTS_DIR   : %s  (存在=%s)" % (FONTS_DIR, FONTS_DIR.exists()),
        "HEI_FONT    : %s" % HEI_FONT,
        "XZC_FONT    : %s" % XZC_FONT,
        "MSYH_FONT   : %s" % MSYH_FONT,
        "ACCORE      : %s" % (ACCORE or "(未找到)"),
        "ODA         : %s" % (ODA or "(未找到)"),
        "DWG 后端    : %s %s" % (bk, path or ""),
        "WORK        : %s" % WORK,
    ]
    return "\n".join(lines)

if __name__ == "__main__":
    print(report())
