# -*- coding: utf-8 -*-
"""只读提取参考 DWG：复制到 ASCII 临时目录后用 AutoCAD 转为 DXF。"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ACCORE = r"D:/CAD2024/AutoCAD 2024/accoreconsole.exe"
REFS = [
    r"D:/UserFiles/Desktop/题目/图模附件/附件-CAD模板及图框.dwg",
    r"D:/UserFiles/Desktop/题目/图模附件/附件-建筑楼层平面 - 10F_ARC(46-000).dwg",
    r"D:/UserFiles/Desktop/题目/图模附件/附件-大样参考.dwg",
]
OUT = Path(__file__).resolve().parent / "_layer_audit" / "reference_dxf"
OUT.mkdir(parents=True, exist_ok=True)
WORK = Path(tempfile.mkdtemp(prefix="layer_ref_"))

lines = []
for i, src in enumerate(REFS, 1):
    tag = "ref%d" % i
    dwg = WORK / (tag + ".dwg")
    shutil.copy2(src, dwg)
    dxf = WORK / (tag + ".dxf")
    if dxf.exists():
        dxf.unlink()
    p1 = str(dwg).replace("\\", "\\\\")
    p2 = str(dxf).replace("\\", "\\\\")
    lines += [
        '(command "_.OPEN" "%s")' % p1,
        '(command "_.DELAY" 400)',
        '(command "_.SAVEAS" "DXF" 16 "%s")' % p2,
        '(princ (strcat "EXPORTED|%s\\n"))' % tag,
    ]
lines.append('(command "_.QUIT")')
scr = WORK / "convert.scr"
scr.write_text("\n".join(lines) + "\n", encoding="ascii")
env = os.environ.copy()
env["MSYS_NO_PATHCONV"] = "1"
try:
    proc = subprocess.run([ACCORE, "/s", str(scr)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=300, env=env)
    rc, raw = proc.returncode, proc.stdout
except subprocess.TimeoutExpired as exc:
    rc, raw = "TIMEOUT", (exc.stdout or b"") + (exc.stderr or b"")
log = raw.decode("utf-16-le", errors="replace") if raw else ""
(OUT / "convert.log").write_text(log + "\nRC=%s\n" % rc, encoding="utf-8")
for i, src in enumerate(REFS, 1):
    tag = "ref%d" % i
    produced = WORK / (tag + ".dxf")
    dxf = OUT / (tag + ".dxf")
    if produced.exists():
        shutil.copy2(produced, dxf)
    print("OK" if dxf.exists() else "FAIL", tag, Path(src).name,
          dxf.stat().st_size if dxf.exists() else 0)
print("RC", rc, "OUT", OUT)
