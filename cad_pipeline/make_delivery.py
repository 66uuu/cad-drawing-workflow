# -*- coding: utf-8 -*-
"""
make_delivery.py — 34 张工作流升级版成果打包（四类分目录 → 桌面 zip）
=====================================================================
清单：02_平面图 16 张（PL-00~15）+ 03_立面图 7（EL-01~07）
     + 04_节点图 6（DT-01~06）+ 05_大样图 5（SD-01~05）= 34 张 × 4 格式 = 136 文件

产出：
  桌面/室内设计四班_A_A-1_2402060428_刘涛溢_工作流升级版34张.zip
    └─ CAD成果_工作流升级版/
        ├─ 01_图纸目录/（PL-00 单独提示性目录，同平面图内）
        ├─ 02_平面图_四格式/ 16×4
        ├─ 03_立面图_四格式/ 7×4
        ├─ 04_节点图_四格式/ 6×4
        ├─ 05_大样图_四格式/ 5×4
        ├─ 00_交付说明.txt
        └─ 00_复检报告.txt（verify_9plans + verify_18drawings 摘要）
"""
import os
import sys
import zipfile
from datetime import datetime

from config import ROOT as BASE

STUDENT = "刘涛溢"
STUDENT_ID = "2402060428"
CLASS_NAME = "室内设计四班"
TEACHER = "倪文静"
DATE = "2026-11-01"
ZIP_STEM = "室内设计四班_A_A-1_2402060428_刘涛溢_工作流升级版34张"

DIRS = ["02_平面图_四格式", "03_立面图_四格式",
        "04_节点图_四格式", "05_大样图_四格式"]
EXPECT = {"02_平面图_四格式": 16, "03_立面图_四格式": 7,
          "04_节点图_四格式": 6, "05_大样图_四格式": 5}
EXTS = (".dxf", ".dwg", ".png", ".pdf")

DESKTOP = r"你的桌面"


def collect():
    """校验 34×4 齐套，返回 (全部文件路径列表, 缺失清单)。"""
    files, missing = [], []
    for d, n in EXPECT.items():
        p = os.path.join(BASE, d)
        for ext in EXTS:
            got = sorted(f for f in os.listdir(p)
                         if f.lower().endswith(ext) and not f.startswith("_"))
            if len(got) != n:
                missing.append("%s/%s: %d 个（应 %d）" % (d, ext, len(got), n))
            for f in got:
                files.append(os.path.join(p, f))
    return files, missing


def verify_summary():
    """跑两个 verify，抓取输出摘要进复检报告。"""
    import subprocess
    py = os.path.join(BASE, ".venv", "Scripts", "python.exe")
    lines = []
    for s in ("verify_9plans.py", "verify_18drawings.py"):
        r = subprocess.run([py, os.path.join(BASE, s)],
                           cwd=BASE, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        out = (r.stdout or "") + (r.stderr or "")
        tail = [ln for ln in out.splitlines() if "PASS" in ln or "FAIL" in ln
                or "总计" in ln]
        lines.append("### %s" % s)
        lines.extend(tail[-40:] if tail else out.splitlines()[-10:])
        lines.append("")
    return "\n".join(lines)


def main():
    files, missing = collect()
    if missing:
        print("[!!] 齐套校验失败：")
        for m in missing:
            print("   ", m)
        sys.exit(1)
    print("[OK] 齐套校验通过：34 张 × 4 格式 = %d 文件" % len(files))

    report = verify_summary()
    nfail = report.count("[FAIL]")
    print("[i] verify 复检 [FAIL] 出现次数：%d" % nfail)

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    readme = "\n".join([
        "CAD 成果交付说明（工作流升级版 34 张）",
        "=" * 46,
        "项目：A-1 开放办公空间室内设计（毕业设计）",
        "班级：%s    学号：%s    姓名：%s" % (CLASS_NAME, STUDENT_ID, STUDENT),
        "指导教师：%s    出图日期：%s" % (TEACHER, DATE),
        "生成时间：%s" % stamp,
        "",
        "图纸清单（34 张，全部 DXF/DWG/PNG/PDF 四格式）：",
        "  02_平面图_四格式：PL-00~15 共 16 张（目录/布置/分区/隔墙/铺装/",
        "      天花/灯具/插座/给排水/消防/索引/动线/配套/排版/天花尺寸）",
        "  03_立面图_四格式：EL-01~07 共 7 张",
        "  04_节点图_四格式：DT-01~06 共 6 张",
        "  05_大样图_四格式：SD-01~05 共 5 张",
        "",
        "图签统一：姓名 %s / 学号 %s / 班级 %s / 指导教师 %s / 日期 %s"
        % (STUDENT, STUDENT_ID, CLASS_NAME, TEACHER, DATE),
        "比例体系：平面 1:100，立面/节点/大样见图内标注；图幅 A1。",
        "本次为「CAD出图工作流」管线升级版：较同学版 27 张补齐 7 张平面",
        "（PL-00 目录 / PL-03 分区 / PL-10 消防 / PL-11 索引 / PL-12 动线 /",
        "  PL-13 配套 / PL-14 排版），全轴网 13×12，全部图签信息统一。",
    ])
    rep = ("CAD 成果复检报告（verify 程序化验收）\n%s\n%s"
           % ("=" * 46, report))

    out_zip = os.path.join(DESKTOP, ZIP_STEM + ".zip")
    if os.path.exists(out_zip):
        os.remove(out_zip)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            arc = "CAD成果_工作流升级版/" + os.path.basename(os.path.dirname(f)) \
                  + "/" + os.path.basename(f)
            z.write(f, arc)
        z.writestr("CAD成果_工作流升级版/00_交付说明.txt", readme)
        z.writestr("CAD成果_工作流升级版/00_复检报告.txt", rep)
    sz = os.path.getsize(out_zip) / 1048576.0
    print("[OK] 已打包：%s（%.1f MB，%d 图纸文件 + 2 说明）"
          % (out_zip, sz, len(files)))
    if nfail:
        print("[!] 注意：复检存在 FAIL 项，详见压缩包内 00_复检报告.txt")


if __name__ == "__main__":
    main()
