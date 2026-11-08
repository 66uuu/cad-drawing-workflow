# -*- coding: utf-8 -*-
"""v2 DXF → DWG 回写"""
import os, shutil, subprocess, tempfile
from pathlib import Path

ACCORE = r"D:/CAD2024/AutoCAD 2024/accoreconsole.exe"
CLEAN_V2 = Path(__file__).resolve().parent / "_zhu_audit" / "cleaned_v2"
SRC_ROOT = Path(r"D:/UserFiles/Desktop/朱")
MAP = __import__("json").loads((Path(__file__).resolve().parent / "_zhu_audit" / "file_map.json").read_text(encoding="utf-8"))

WORK = Path(tempfile.mkdtemp(prefix="zhu_v2_"))
dxf_files = sorted(CLEAN_V2.glob("*.dxf"))
print("待转换:", len(dxf_files))

# 复制到ASCII临时目录
tag_map = {}
for i, dxf in enumerate(dxf_files, 1):
    tag = "v2_%02d" % i
    shutil.copy2(dxf, WORK / (tag + ".dxf"))
    tag_map[tag] = dxf.name

# 生成SCR
lines = []
for tag in tag_map:
    dxf_p = (WORK / (tag + ".dxf")).as_posix()
    dwg_p = (WORK / (tag + ".dwg")).as_posix()
    if (WORK / (tag + ".dwg")).exists():
        (WORK / (tag + ".dwg")).unlink()
    lines += [
        '(command "_.OPEN" "%s")' % dxf_p,
        '(command "_.DELAY" 200)',
        '(command "_.SAVEAS" "" "%s")' % dwg_p,
        '(princ (strcat "DONE|%s\\n"))' % tag,
    ]
lines.append('(command "_.QUIT" "_Y")')
scr = WORK / "v2.scr"
scr.write_text("\n".join(lines) + "\n", encoding="ascii")

env = os.environ.copy()
env["MSYS_NO_PATHCONV"] = "1"
print("运行AutoCAD...")
try:
    proc = subprocess.run([ACCORE, "/s", str(scr)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300, env=env)
    rc = proc.returncode
    raw = proc.stdout
except subprocess.TimeoutExpired as e:
    rc = "TIMEOUT"
    raw = (e.stdout or b"") + (e.stderr or b"")
log = raw.decode("utf-16-le", errors="replace") if raw else ""
(Path(__file__).resolve().parent / "_zhu_audit" / "v2_convert.log").write_text(log + "\nRC=%s\n" % rc, encoding="utf-8")
print("返回码:", rc)

# 回写
success = 0
fail = 0
for tag, dxf_name in tag_map.items():
    dwg_name = dxf_name.replace(".dxf", ".dwg")
    generated = WORK / (tag + ".dwg")
    # 找原路径
    for mtag, minfo in MAP.items():
        if minfo["name"] == dwg_name:
            target = Path(minfo["src"])
            break
    else:
        print("  FAIL 找不到:", dwg_name)
        fail += 1
        continue
    if generated.exists():
        shutil.copy2(generated, target)
        success += 1
        print("  OK:", target.relative_to(SRC_ROOT))
    else:
        print("  FAIL 未生成:", dwg_name)
        fail += 1

print("\n完成: 成功%d / 失败%d" % (success, fail))
