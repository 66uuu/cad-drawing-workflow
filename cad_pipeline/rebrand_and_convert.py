# -*- coding: utf-8 -*-
"""
一键：把 9 张(实际 11 张)平面图的图签改为 朱增涛 / 郑睿 / 室内设计二班 / 今天，
学号暂用占位 XXXXXXXXXX（用户要求暂不添加），然后转 DWG 覆盖到桌面文件夹。
不重跑 build（DXF 图签为明文，直接文本替换最快）。
"""
import os, shutil, subprocess, tempfile
from pathlib import Path

SRC = Path(r"你的桌面\CAD出图工作流\cad_pipeline\02_平面图_四格式")
DST = Path(r"你的桌面\9张CAD平面图_DWG")
JPG = Path(r"你的桌面\新建文件夹")
ACCORE = r"D:/CAD2024/AutoCAD 2024/accoreconsole.exe"
DST.mkdir(parents=True, exist_ok=True)
(DST / "原图jpg参考").mkdir(parents=True, exist_ok=True)

# (源dxf, 目标dwg, 是否用户9张之一, 对应原图jpg)
PLANS = [
    ("PL-01_平面布置图.dxf",   "PL-01_平面布置图.dwg",   True,  "8cade4261513fa5036aa51234a4029e2.jpg"),
    ("PL-02_原始结构图.dxf",   "PL-02_原始结构图.dwg",   True,  "e80937c90429c829077b75b4d02bc528.jpg"),
    ("PL-03_功能分区图.dxf",   "PL-03_功能分区图.dwg",   False, None),
    ("PL-04_新增隔墙定位图.dxf","PL-04_新增隔墙定位图.dwg",True, "c4256c8a331a0173aeb0f4ddd50fae13.jpg"),
    ("PL-05_地面铺装图.dxf",   "PL-05_地面铺装图.dwg",   True,  "36886e237c7f619c68dd3bd27e54be47.jpg"),
    ("PL-06_天花布置图.dxf",   "PL-06_天花布置图.dwg",   True,  "a4caec177b0e9205dc46914ad0db5315.jpg"),
    ("PL-07_灯具定位图.dxf",   "PL-07_灯具定位图.dwg",   True,  "ebf6f47997cba393d35ea00690d4d03e.jpg"),
    ("PL-08_插座定位图.dxf",   "PL-08_插座定位图.dwg",   True,  "f2d487cb1ee9de24791a3b5534c53f07.jpg"),
    ("PL-09_给排水点位图.dxf", "PL-09_给排水点位图.dwg", True,  "1dd1e8cad6a9aecc9a30fa6e129bdc5a.jpg"),
    ("PL-10_消防末端图.dxf",   "PL-10_消防末端图.dwg",   False, None),
    ("PL-15_天花尺寸图.dxf",   "PL-15_天花尺寸图.dwg",   True,  "8cdcdad3d5ba0e23cb97bc78415485af.jpg"),
]

REPL = [("刘涛溢", "朱增涛"), ("倪文静", "郑睿"), ("室内设计四班", "室内设计二班"),
        ("2026-11-01", "2026-11-03"), ("2402060428", "XXXXXXXXXX")]

print("=== 1) 替换 DXF 图签文本 ===")
for dxf_name, _, _, _ in PLANS:
    p = SRC / dxf_name
    if not p.exists():
        print("  缺失:", dxf_name); continue
    t = p.read_text(encoding="utf-8", errors="ignore")
    for a, b in REPL:
        t = t.replace(a, b)
    p.write_text(t, encoding="utf-8")
    print("  OK", dxf_name)

print("\n=== 2) AutoCAD 内核转 DWG ===")
WORK = Path(tempfile.mkdtemp(prefix="rebrand_"))
for i, (dxf_name, _, _, _) in enumerate(PLANS, 1):
    s = SRC / dxf_name
    if s.exists():
        shutil.copy2(s, WORK / ("p%02d.dxf" % i))
lines = []
for i in range(1, len(PLANS) + 1):
    dxf = (WORK / ("p%02d.dxf" % i)).as_posix()
    dwg = (WORK / ("p%02d.dwg" % i)).as_posix()
    lines += ['(command "_.OPEN" "%s")' % dxf, '(command "_.DELAY" 300)',
              '(command "_.SAVEAS" "" "%s")' % dwg, '(princ (strcat "DONE|%d\\n"))' % i]
lines.append('(command "_.QUIT" "_Y")')
scr = WORK / "c.scr"
scr.write_text("\n".join(lines) + "\n", encoding="ascii")
env = os.environ.copy(); env["MSYS_NO_PATHCONV"] = "1"
if not os.path.exists(ACCORE):
    print("  [!] 未找到 accoreconsole:", ACCORE)
else:
    proc = subprocess.run([ACCORE, "/s", str(scr)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300, env=env)
    print("  accore 返回码:", proc.returncode)

print("\n=== 3) 复制到桌面并覆盖（锁定的文件跳过，不中断整批） ===")
ok = 0
locked = []
for i, (dxf_name, dwg_name, is_user, jpg) in enumerate(PLANS, 1):
    g = WORK / ("p%02d.dwg" % i)
    if not g.exists():
        print("  FAIL", dwg_name); continue
    dst = DST / dwg_name
    try:
        shutil.copy2(g, dst)
        kb = round(dst.stat().st_size / 1024, 1)
        tag = "【你的9张之一】" if is_user else "【你点名补充】"
        print("  %s %s (%sKB)" % (tag, dwg_name, kb)); ok += 1
    except PermissionError:
        locked.append(dwg_name)
        print("  [锁定跳过] %s（被 AutoCAD 占用，稍后关掉再覆盖）" % dwg_name)
# 原图
for dxf_name, dwg_name, is_user, jpg in PLANS:
    if is_user and jpg:
        sj = JPG / jpg
        if sj.exists():
            shutil.copy2(sj, DST / "原图jpg参考" / jpg)

# 清单
lines_md = ["# 9张CAD平面图 · DWG 交付清单（已更新图签）", "",
            "**图签已更新为：** 姓名 朱增涛 · 指导老师 郑睿 · 班级 室内设计二班 · 日期 2026-11-03 · 学号 XXXXXXXXXX（占位，暂不添加）",
            "全部为可编辑矢量 DWG（AutoCAD 2018 / AC1032 格式），可用 AutoCAD / ODA 打开修改。", "",
            "## 一、你给的 9 张平面图 → 对应 DWG", "",
            "| 原图 jpg | 图名 | DWG 文件名 |",
            "|---|---|---|"]
for dxf_name, dwg_name, is_user, jpg in PLANS:
    if is_user:
        lines_md.append("| %s | %s | %s |" % (jpg, dwg_name.replace('.dwg',''), dwg_name))
lines_md += ["", "## 二、你点名问的图（额外补充）", "",
             "| 图名 | DWG 文件名 |", "|---|---|",
             "| 功能分区图 | PL-03_功能分区图.dwg |",
             "| 消防末端图 | PL-10_消防末端图.dwg |",
             "", "## 三、图号速查", "",
             "- PL-01 平面布置图：家具、工位、分区落位",
             "- PL-02 原始结构图：建筑外墙、核心筒、轴网（无装修）",
             "- PL-03 功能分区图：各功能区域划分",
             "- PL-04 新增隔墙定位图：新建隔墙中心线 + 尺寸",
             "- PL-05 地面铺装图：地面材料分区 + 铺装方向",
             "- PL-06 天花布置图：吊顶完成面 + 造型分界",
             "- PL-07 灯具定位图：灯具点位网格",
             "- PL-08 插座定位图：强弱电插座点位",
             "- PL-09 给排水点位图：茶水间给排水 + 涉水区",
             "- PL-10 消防末端图：喷淋/烟感/消火栓末端",
             "- PL-15 天花尺寸图：天花造型 + 灯槽定位尺寸",
             "", "## 四、学号说明", "",
             "你要求学号暂不添加，故图签学号栏为占位 `XXXXXXXXXX`。拿到学号后，把 `cad_pipeline/student_master.py` 里 `STUDENT_ID` 改成真实值并重跑 build 即可。"]
(DST / "清单.md").write_text("\n".join(lines_md), encoding="utf-8")

print("\n完成：DWG %d 张 + 清单.md 已覆盖到 %s" % (ok, DST))
