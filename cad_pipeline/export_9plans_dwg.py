# -*- coding: utf-8 -*-
"""
9张核心平面图 DXF→DWG 批量转换 + 桌面输出
"""
import os, shutil, subprocess, tempfile
from pathlib import Path

ACCORE = r"D:/CAD2024/AutoCAD 2024/accoreconsole.exe"
DXF_DIR = Path(r"你的桌面\CAD出图工作流\cad_pipeline\02_平面图_四格式")
OUT_DIR = Path(r"C:\Users\<USER>\Desktop\毕业设计_9张平面图_DWG")
OUT_DIR.mkdir(exist_ok=True)

# 选9张核心图，命名清晰
PLANS = [
    ("PL-01_平面布置图.dxf",       "01_平面布置图.dwg"),
    ("PL-02_原始结构图.dxf",       "02_原始结构图.dwg"),
    ("PL-03_功能分区图.dxf",       "03_功能分区图.dwg"),
    ("PL-04_新增隔墙定位图.dxf",   "04_新增隔墙定位图.dwg"),
    ("PL-05_地面铺装图.dxf",       "05_地面铺装图.dwg"),
    ("PL-06_天花布置图.dxf",       "06_天花布置图.dwg"),
    ("PL-07_灯具定位图.dxf",       "07_灯具定位图.dwg"),
    ("PL-08_插座定位图.dxf",       "08_插座定位图.dwg"),
    ("PL-10_消防末端图.dxf",       "09_消防末端图.dwg"),
]

WORK = Path(tempfile.mkdtemp(prefix="zhu9_"))
print("临时目录:", WORK)

# 复制DXF到ASCII临时目录
for i, (dxf_name, dwg_name) in enumerate(PLANS, 1):
    src = DXF_DIR / dxf_name
    if not src.exists():
        print("缺失:", dxf_name)
        continue
    shutil.copy2(src, WORK / ("p%02d.dxf" % i))

# 生成SCR
lines = []
for i in range(1, len(PLANS)+1):
    dxf_p = (WORK / ("p%02d.dxf" % i)).as_posix()
    dwg_p = (WORK / ("p%02d.dwg" % i)).as_posix()
    if Path(dwg_p).exists():
        Path(dwg_p).unlink()
    lines += [
        '(command "_.OPEN" "%s")' % dxf_p,
        '(command "_.DELAY" 200)',
        '(command "_.SAVEAS" "" "%s")' % dwg_p,
        '(princ (strcat "DONE|%d\\n"))' % i,
    ]
lines.append('(command "_.QUIT" "_Y")')
scr = WORK / "convert.scr"
scr.write_text("\n".join(lines) + "\n", encoding="ascii")

# 运行AutoCAD
env = os.environ.copy()
env["MSYS_NO_PATHCONV"] = "1"
print("运行AutoCAD转换9张图...")
proc = subprocess.run([ACCORE, "/s", str(scr)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300, env=env)
log = proc.stdout.decode("utf-16-le", errors="replace") if proc.stdout else ""
print("返回码:", proc.returncode)

# 复制到桌面输出目录
success = 0
for i, (dxf_name, dwg_name) in enumerate(PLANS, 1):
    generated = WORK / ("p%02d.dwg" % i)
    if generated.exists():
        dst = OUT_DIR / dwg_name
        shutil.copy2(generated, dst)
        size_kb = round(dst.stat().st_size / 1024, 1)
        print("  OK: %s (%d KB)" % (dwg_name, size_kb))
        success += 1
    else:
        print("  FAIL: %s" % dwg_name)

print("\n完成: %d/9" % success)
print("输出目录:", OUT_DIR)
