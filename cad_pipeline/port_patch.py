# -*- coding: utf-8 -*-
"""
port_patch.py — 把标杆成品的脚本迁移进 cad_pipeline 并「去硬编码」（可复现的关键）
=================================================================================
标杆成品在 D:/UserFiles/Desktop/<标杆学生名>/.../CAD成果_同学版/scripts/ 下，
逻辑已被证明能产出高质量成品。本脚本：
  1) 把它们整份复制到 cad_pipeline/（保留已验证逻辑不变）
  2) 用精确字符串替换，把里面所有「本机专属」硬路径改成从 config 解析：
       · 字体  C:/Windows/Fonts/simhei.ttf / simplex_.ttf / msyh.ttc
       · AutoCAD  <D盘>\\CAD2024\\AutoCAD 2024\\accoreconsole.exe
       · BASE（桌面绝对路径）、WORK（C:\\wbtmp9）
  3) 把 dwg_convert_*.py / verify_dwg_*.py 改写成调用统一后端 dwg_convert.py 的薄包装，
     这样「换电脑找不到 AutoCAD/ODA」时优雅跳过而不是 sys.exit(1)。

替换全部使用精确子串，跑完会打印每条是否命中，未命中会告警（便于发现脚本版本漂移）。
重新跑本脚本是幂等的（基于源码目录最新内容重拷）。
"""
import os
import shutil
from pathlib import Path

SRC = Path(r"D:/UserFiles/Desktop/<标杆学生名>/毕业设计核心内容指导方案_同学版_CAD调整版_2026-10-31/CAD成果_同学版/scripts")  # 【脱敏占位】迁移已完成后此路径不再使用
DST = Path(__file__).resolve().parent

# 需要复制的脚本（诊断脚本也一并带走，方便复检）
COPY_ALL = True  # True = 复制 SRC 下全部 .py

# 每个文件要做的 (old, new) 替换
REPL = {
    "student_cad.py": [
        ("from ezdxf.fonts import fonts as _ezfonts",
         "from ezdxf.fonts import fonts as _ezfonts\nfrom config import FONT_SCAN_DIRS"),
        ("_ezfonts.font_manager.scan_folder(Path(r\"C:\\Windows\\Fonts\"))",
         "for _fd in FONT_SCAN_DIRS:\n    _ezfonts.font_manager.scan_folder(_fd)"),
    ],
    "build_9plans_同学版.py": [
        ("from matplotlib import font_manager as fm",
         "from matplotlib import font_manager as fm\nfrom config import SYSTEM_FONT_DIR, HEI_FONT"),
        ("FONTPATH = \"C:/Windows/Fonts/simhei.ttf\"", "FONTPATH = HEI_FONT"),
        ("\"C:/Windows/Fonts\"", "SYSTEM_FONT_DIR"),
    ],
    "build_PL01_同学版.py": [
        ("from PIL import Image, ImageDraw, ImageFont",
         "from PIL import Image, ImageDraw, ImageFont\nfrom config import MSYH_FONT"),
        ("\"C:/Windows/Fonts/msyh.ttc\"", "str(MSYH_FONT)"),
    ],
    "build_9plans_同学版_v2.py": [
        ("BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))",
         "from config import ROOT as BASE"),
    ],
    "build_18drawings_同学版.py": [
        ("BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))",
         "from config import ROOT as BASE"),
    ],
    "_audit_zip_coverage.py": [
        ("ZIP = r\"<D盘>\\UserFiles\\Desktop\\毕业设计核心内容指导方案_同学版_CAD调整版_2026-10-31.zip\"",
         "import sys\nfrom config import ROOT\nZIP = sys.argv[1] if len(sys.argv) > 1 else str(ROOT) + \".zip\""),
    ],
}

# dwg_convert_*.py 与 verify_dwg_*.py 改写成薄包装（统一后端）
WRAPPER_DWG_CONVERT = """# -*- coding: utf-8 -*-
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
"""

WRAPPER_VERIFY_DWG = """# -*- coding: utf-8 -*-
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
"""


def copy_and_patch():
    if not SRC.exists():
        print("[!!] 源脚本目录不存在：%s" % SRC)
        return
    files = [f for f in os.listdir(SRC) if f.endswith(".py")] if COPY_ALL else list(REPL.keys())
    for f in files:
        src = SRC / f
        dst = DST / f
        txt = src.read_text(encoding="utf-8")
        if f in REPL:
            for old, new in REPL[f]:
                if old in txt:
                    txt = txt.replace(old, new, 1)
                    print("  [patch] %s : 命中替换" % f)
                else:
                    print("  [!!] %s : 未命中「%s」(脚本可能已变，请人工核对)" % (f, old[:40]))
        dst.write_text(txt, encoding="utf-8")
        print("  [copy] %s -> %s" % (f, dst.name))
    # 改写两个包装器
    (DST / "dwg_convert_9plans.py").write_text(WRAPPER_DWG_CONVERT, encoding="utf-8")
    (DST / "dwg_convert_18drawings.py").write_text(WRAPPER_DWG_CONVERT, encoding="utf-8")
    (DST / "verify_dwg_9plans.py").write_text(WRAPPER_VERIFY_DWG, encoding="utf-8")
    (DST / "verify_dwg_18drawings.py").write_text(WRAPPER_VERIFY_DWG, encoding="utf-8")
    print("\n[完成] 已复制并打补丁；dwg_convert_*/verify_dwg_* 已统一为后端薄包装。")


if __name__ == "__main__":
    copy_and_patch()
