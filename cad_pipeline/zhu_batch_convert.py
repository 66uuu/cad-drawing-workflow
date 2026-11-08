# -*- coding: utf-8 -*-
"""
朱文件夹 DWG → DXF 批量转换
=============================
1. 扫描 D:/UserFiles/Desktop/朱 下所有 .dwg
2. 复制到 ASCII 临时目录（中文名→zhu_xx.dwg）
3. 用 AutoCAD accoreconsole 批量 SAVEAS DXF
4. 输出到 _zhu_audit/dxf/，保留原始文件名映射
"""
import os, shutil, subprocess, tempfile, json
from pathlib import Path

ACCORE = r"D:/CAD2024/AutoCAD 2024/accoreconsole.exe"
SRC_ROOT = Path(r"D:/UserFiles/Desktop/朱")
OUT_DIR = Path(__file__).resolve().parent / "_zhu_audit" / "dxf"
MAP_DIR = Path(__file__).resolve().parent / "_zhu_audit"

# ---------- 1. 收集所有 DWG ----------
dwg_files = sorted(SRC_ROOT.rglob("*.dwg"))
# 排除 .bak（.bak 不是 .dwg 后缀，rglob 不会匹配）
print("发现 %d 个 DWG 文件:" % len(dwg_files))
for i, p in enumerate(dwg_files, 1):
    print("  %2d. %s" % (i, p.relative_to(SRC_ROOT)))

# ---------- 2. 创建映射 ----------
mapping = {}
for i, p in enumerate(dwg_files, 1):
    tag = "zhu_%02d" % i
    mapping[tag] = {
        "src": str(p),
        "rel": str(p.relative_to(SRC_ROOT)),
        "name": p.name,
    }

# ---------- 3. ASCII 临时目录 ----------
WORK = Path(tempfile.mkdtemp(prefix="zhu_cvt_"))
print("\n临时目录:", WORK)

# 复制 DWG 进去（ASCII 名）
for tag, info in mapping.items():
    shutil.copy2(info["src"], WORK / (tag + ".dwg"))

# ---------- 4. 生成 AutoCAD SCR 脚本 ----------
lines = []
for tag in mapping:
    dwg_p = (WORK / (tag + ".dwg")).as_posix()
    dxf_p = (WORK / (tag + ".dxf")).as_posix()
    # 删除旧 DXF
    if (WORK / (tag + ".dxf")).exists():
        (WORK / (tag + ".dxf")).unlink()
    lines += [
        '(command "_.OPEN" "%s")' % dwg_p,
        '(command "_.DELAY" 300)',
        '(command "_.SAVEAS" "DXF" 16 "%s")' % dxf_p,
        '(princ (strcat "DONE|%s\\n"))' % tag,
    ]
lines.append('(command "_.QUIT" "_Y")')

scr = WORK / "convert.scr"
scr.write_text("\n".join(lines) + "\n", encoding="ascii")
print("SCR 脚本:", scr)

# ---------- 5. 运行 accoreconsole ----------
env = os.environ.copy()
env["MSYS_NO_PATHCONV"] = "1"
print("\n运行 AutoCAD 转换（可能需要1-3分钟）...")
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
OUT_DIR.parent.mkdir(parents=True, exist_ok=True)
(OUT_DIR.parent / "convert.log").write_text(log + "\nRC=%s\n" % rc, encoding="utf-8")
print("返回码:", rc)
print("日志前500字:", log[:500])

# ---------- 6. 复制 DXF 回输出目录 ----------
OUT_DIR.mkdir(parents=True, exist_ok=True)
success = []
fail = []
for tag, info in mapping.items():
    src_dxf = WORK / (tag + ".dxf")
    if src_dxf.exists():
        # 用原始文件名（去掉.dwg换成.dxf）
        out_name = info["name"].replace(".dwg", ".dxf")
        out_path = OUT_DIR / out_name
        shutil.copy2(src_dxf, out_path)
        success.append((tag, out_name, out_path.stat().st_size))
    else:
        fail.append((tag, info["name"]))

# 保存映射
(MAP_DIR / "file_map.json").write_text(
    json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")

print("\n=== 转换结果 ===")
print("成功: %d / %d" % (len(success), len(mapping)))
for tag, name, size in success:
    print("  OK %s -> %s (%d bytes)" % (tag, name, size))
if fail:
    print("失败:")
    for tag, name in fail:
        print("  FAIL %s -> %s" % (tag, name))

print("\nDXF 输出目录:", OUT_DIR)
print("映射文件:", MAP_DIR / "file_map.json")
