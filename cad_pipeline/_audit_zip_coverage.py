# -*- coding: utf-8 -*-
"""压缩包覆盖度全量比对：源目录 vs zip 内条目 vs 桌面其他成果目录。"""
import os, zipfile, collections

import sys
from config import ROOT
ZIP = sys.argv[1] if len(sys.argv) > 1 else str(ROOT) + ".zip"
SRC = r"你的桌面\毕业设计核心内容指导方案_同学版_CAD调整版_2026-10-31"
OTHER = [
    r"你的桌面\办公任务成果\20261031_CAD九张平面图补全",
    r"你的桌面\办公任务成果\20261031_CAD立面节点大样图",
]

# ---- 1. 源目录全部文件 ----
src_all = []
for root, dirs, files in os.walk(SRC):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for fn in files:
        src_all.append(os.path.relpath(os.path.join(root, fn), SRC).replace("\\", "/"))
print("源目录文件总数（已排除 __pycache__ 目录）: %d" % len(src_all))

# ---- 2. zip 内条目 ----
with zipfile.ZipFile(ZIP) as z:
    names = [n.replace("\\", "/") for n in z.namelist()]
PREFIX = os.path.basename(SRC) + "/"
inzip = set(n[len(PREFIX):] for n in names if n.startswith(PREFIX))
print("zip 内归属本项目的条目: %d" % len(inzip))
outside = [n for n in names if not n.startswith(PREFIX)]
print("zip 内前缀异常条目: %d" % len(outside))

# ---- 3. 源目录里未被打包的 ----
missing = sorted(set(src_all) - inzip)
print("\n=== 源目录有、但 zip 里没有：%d 个 ===" % len(missing))
by_ext = collections.Counter(m.rsplit(".", 1)[-1].lower() if "." in m else "(无扩展名)" for m in missing)
print("按扩展名:", dict(by_ext))
by_dir = collections.Counter(m.split("/")[0] if "/" in m else "(根)" for m in missing)
print("按顶层目录:", dict(by_dir))
for m in missing[:40]:
    print("   -", m)
if len(missing) > 40:
    print("   ... 其余 %d 个略" % (len(missing) - 40))

# ---- 4. zip 里有、源目录没有的（陈旧/孤儿条目）----
extra = sorted(inzip - set(src_all))
print("\n=== zip 里有、源目录已没有（陈旧条目）：%d 个 ===" % len(extra))
for m in extra[:20]:
    print("   -", m)

# ---- 5. 桌面其他成果目录是否被纳入 ----
print("\n=== 桌面其他劳动成果目录覆盖检查 ===")
for d in OTHER:
    if not os.path.isdir(d):
        print("  [不存在]", d)
        continue
    files = []
    for root, dirs, fs in os.walk(d):
        for fn in fs:
            files.append(os.path.relpath(os.path.join(root, fn), d).replace("\\", "/"))
    hit = [f for f in files if any(f in n for n in names)]
    print("  %s  共 %d 文件，zip 内命中 %d" % (os.path.basename(d), len(files), len(hit)))
    if not hit:
        print("     >>> 完全未纳入压缩包！")
        for f in files[:10]:
            print("        -", f)

# ---- 6. zip 顶层结构 ----
print("\n=== zip 顶层目录结构 ===")
top = collections.Counter()
for n in names:
    parts = n.split("/")
    key = "/".join(parts[:3]) if len(parts) >= 3 else n
    top[key] += 1
for k, v in sorted(top.items())[:30]:
    print("  %-70s %d" % (k, v))
