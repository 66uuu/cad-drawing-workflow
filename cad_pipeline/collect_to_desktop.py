# -*- coding: utf-8 -*-
"""
把 9 张平面图对应的 DWG 整理到桌面新文件夹，命名清晰，方便统筹检查。
DWG 来源：cad_pipeline/02_平面图_四格式（工作流已生成的矢量版，可编辑、带图签）
额外补入用户点名的两张：PL-03 功能分区图、PL-10 消防末端图
"""
import shutil
from pathlib import Path

SRC = Path(r"你的桌面\CAD出图工作流\cad_pipeline\02_平面图_四格式")
DST = Path(r"你的桌面\9张CAD平面图_DWG")
JPG_SRC = Path(r"你的桌面\新建文件夹")

DST.mkdir(parents=True, exist_ok=True)
(JPG_SRC and DST / "原图jpg参考").mkdir(parents=True, exist_ok=True)

# (源dwg, 目标dwg, 是否用户9张图之一, 对应原图jpg)
ITEMS = [
    ("PL-01_平面布置图.dwg",      "PL-01_平面布置图.dwg",       True,  "8cade4261513fa5036aa51234a4029e2.jpg"),
    ("PL-02_原始结构图.dwg",      "PL-02_原始结构图.dwg",       True,  "e80937c90429c829077b75b4d02bc528.jpg"),
    ("PL-04_新增隔墙定位图.dwg",  "PL-04_新增隔墙定位图.dwg",   True,  "c4256c8a331a0173aeb0f4ddd50fae13.jpg"),
    ("PL-05_地面铺装图.dwg",      "PL-05_地面铺装图.dwg",       True,  "36886e237c7f619c68dd3bd27e54be47.jpg"),
    ("PL-06_天花布置图.dwg",      "PL-06_天花布置图.dwg",       True,  "a4caec177b0e9205dc46914ad0db5315.jpg"),
    ("PL-07_灯具定位图.dwg",      "PL-07_灯具定位图.dwg",       True,  "ebf6f47997cba393d35ea00690d4d03e.jpg"),
    ("PL-08_插座定位图.dwg",      "PL-08_插座定位图.dwg",       True,  "f2d487cb1ee9de24791a3b5534c53f07.jpg"),
    ("PL-09_给排水点位图.dwg",    "PL-09_给排水点位图.dwg",     True,  "1dd1e8cad6a9aecc9a30fa6e129bdc5a.jpg"),
    ("PL-15_天花尺寸图.dwg",      "PL-15_天花尺寸图.dwg",       True,  "8cdcdad3d5ba0e23cb97bc78415485af.jpg"),
    # 用户点名补充（你问了“哪张是消防末端/功能分区”，工作流也生成了，一并放进来对照）
    ("PL-03_功能分区图.dwg",      "PL-03_功能分区图.dwg",       False, None),
    ("PL-10_消防末端图.dwg",      "PL-10_消防末端图.dwg",       False, None),
]

print("===== 复制 DWG =====")
ok = 0
for src_name, dst_name, is_user, jpg in ITEMS:
    s = SRC / src_name
    d = DST / dst_name
    if s.exists():
        shutil.copy2(s, d)
        kb = round(d.stat().st_size / 1024, 1)
        tag = "【你的9张之一】" if is_user else "【额外补充·你点名】"
        print("  %s %s (%s KB)" % (tag, dst_name, kb))
        ok += 1
    else:
        print("  缺失: %s" % src_name)

print("\n===== 复制原图 jpg 供对照 =====")
jk = 0
for src_name, dst_name, is_user, jpg in ITEMS:
    if is_user and jpg:
        sj = JPG_SRC / jpg
        dj = DST / "原图jpg参考" / jpg
        if sj.exists():
            shutil.copy2(sj, dj)
            jk += 1
print("  原图已复制 %d 张 -> 原图jpg参考/" % jk)

# 写清单
lines = ["# 9张CAD平面图 · DWG 交付清单", "",
         "本文件夹所有 .dwg 均为**可编辑矢量图**（工作流 ezdxf 程序化生成，非图片嵌入），可用 AutoCAD / ODA 打开修改。",
         "全部图签已脱敏（姓名/学号/班级/指导教师为占位符），交付前在 `student_master.py` 填回真实信息即可。", "",
         "## 一、你给的 9 张平面图 → 对应 DWG", "",
         "| 原图 jpg | 图名 | DWG 文件名 |", "|---|---|---|"]
for src_name, dst_name, is_user, jpg in ITEMS:
    if is_user:
        lines.append("| %s | %s | %s |" % (jpg, dst_name.replace('.dwg',''), dst_name))
lines += ["", "## 二、你点名问的图（额外补充，工作流也生成了）", "",
          "| 图名 | DWG 文件名 | 说明 |", "|---|---|---|",
          "| 功能分区图 | PL-03_功能分区图.dwg | 你举例问“哪张是功能分区图”，即此张 |",
          "| 消防末端图 | PL-10_消防末端图.dwg | 你举例问“哪张是消防末端”，即此张（喷淋/烟感/消火栓末端布置）|",
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
          "", "## 四、如只要你原来的 9 张", "",
          "删除 `PL-03_功能分区图.dwg` 和 `PL-10_消防末端图.dwg` 即可，其余 9 张即为你文件夹里那 9 张图的 CAD 版。"]
(DST / "清单.md").write_text("\n".join(lines), encoding="utf-8")

print("\n完成：DWG %d 张 + 原图 %d 张 + 清单.md" % (ok, jk))
print("输出目录:", DST)
