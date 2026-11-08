# -*- coding: utf-8 -*-
"""
清洗后 DXF → DWG 回写脚本
=========================
1. 先备份原 DWG 到 _zhu_backup/
2. 用 AutoCAD accoreconsole 把清洗后的 DXF 转成 DWG
3. 按原路径覆盖回朱文件夹
"""
import os, shutil, subprocess, tempfile, json
from pathlib import Path

ACCORE = r"D:/CAD2024/AutoCAD 2024/accoreconsole.exe"
CLEAN_DXF = Path(__file__).resolve().parent / "_zhu_audit" / "cleaned"
SRC_ROOT = Path(r"D:/UserFiles/Desktop/朱")
BACKUP = Path(__file__).resolve().parent / "_zhu_audit" / "original_backup"

# 读取文件映射
MAP = json.loads((Path(__file__).resolve().parent / "_zhu_audit" / "file_map.json").read_text(encoding="utf-8"))

# ---------- 1. 备份原始 DWG ----------
BACKUP.mkdir(parents=True, exist_ok=True)
print("=== 备份原始 DWG ===")
for tag, info in MAP.items():
    src = Path(info["src"])
    rel = info["rel"]
    dst = BACKUP / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy2(src, dst)
        print("  备份:", rel)

# ---------- 2. 准备 ASCII 临时目录做 DXF→DWG ----------
WORK = Path(tempfile.mkdtemp(prefix="zhu_dwg_"))
print("\n临时目录:", WORK)

# 收集清洗后的 DXF
dxf_files = sorted(CLEAN_DXF.glob("*.dxf"))
print("待转换 DXF:", len(dxf_files))

# 复制 DXF 到临时目录（ASCII 名）
tag_map = {}
for i, dxf in enumerate(dxf_files, 1):
    tag = "out_%02d" % i
    shutil.copy2(dxf, WORK / (tag + ".dxf"))
    tag_map[tag] = {
        "dxf_name": dxf.name,
        "dwg_name": dxf.name.replace(".dxf", ".dwg"),
    }

# ---------- 3. 生成 AutoCAD SCR 脚本 ----------
lines = []
for tag in tag_map:
    dxf_p = (WORK / (tag + ".dxf")).as_posix()
    dwg_p = (WORK / (tag + ".dwg")).as_posix()
    if (WORK / (tag + ".dwg")).exists():
        (WORK / (tag + ".dwg")).unlink()
    lines += [
        '(command "_.OPEN" "%s")' % dxf_p,
        '(command "_.DELAY" 300)',
        '(command "_.SAVEAS" "" "%s")' % dwg_p,
        '(princ (strcat "DONE|%s\\n"))' % tag,
    ]
lines.append('(command "_.QUIT" "_Y")')

scr = WORK / "back.scr"
scr.write_text("\n".join(lines) + "\n", encoding="ascii")

# ---------- 4. 运行 AutoCAD ----------
env = os.environ.copy()
env["MSYS_NO_PATHCONV"] = "1"
print("\n运行 AutoCAD DXF→DWG 转换...")
try:
    proc = subprocess.run(
        [ACCORE, "/s", str(scr)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=300, env=env,
    )
    rc = proc.returncode
    raw = proc.stdout
except subprocess.TimeoutExpired as e:
    rc = "TIMEOUT"
    raw = (e.stdout or b"") + (e.stderr or b"")

log = raw.decode("utf-16-le", errors="replace") if raw else ""
(Path(__file__).resolve().parent / "_zhu_audit" / "back_convert.log").write_text(
    log + "\nRC=%s\n" % rc, encoding="utf-8")
print("返回码:", rc)

# ---------- 5. 把生成的 DWG 回写朱文件夹 ----------
print("\n=== 回写 DWG 到朱文件夹 ===")
success = []
fail = []
for tag, info in tag_map.items():
    generated = WORK / (tag + ".dwg")
    # 找到对应的原始路径
    dxf_name = info["dxf_name"]
    # 在MAP中反查
    for mtag, minfo in MAP.items():
        if minfo["name"].replace(".dwg", ".dxf") == dxf_name:
            target = Path(minfo["src"])
            break
    else:
        fail.append((dxf_name, "找不到原路径映射"))
        continue

    if generated.exists():
        shutil.copy2(generated, target)
        success.append((target.name, target.stat().st_size))
        print("  OK:", target.relative_to(SRC_ROOT))
    else:
        fail.append((dxf_name, "DWG未生成"))

print("\n=== 回写完成 ===")
print("成功:", len(success), "/", len(dxf_files))
if fail:
    print("失败:")
    for n, reason in fail:
        print("  FAIL:", n, reason)
