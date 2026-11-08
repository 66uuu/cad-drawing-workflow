# -*- coding: utf-8 -*-
"""
_selfcheck.py — 管线自检（被 setup_env.py 调用，也可单独跑）
=========================================================
验证三件事：路径解耦生效、数据源断言通过、字体就位、后端可知。
任何一项失败都给出明确指引，而不是让后续出图在奇怪的地方崩。
"""
import os
import sys
from pathlib import Path

import config

def check(msg, cond):
    print(("  [ok] " if cond else "  [!!] ") + msg)
    return cond


def main():
    print(config.report())
    ok = True

    # 1) 字体必须真实存在（否则中文/尺寸数字渲染会丢字或换字体）
    print("\n-- 字体 --")
    for name, val in (("HEI", config.HEI_FONT), ("XZC", config.XZC_FONT), ("MSYH", config.MSYH_FONT)):
        exists = os.path.exists(val)
        ok &= check("%s 字体文件存在: %s" % (name, val), exists)
        if not exists:
            print("        → 请运行 setup_env.py 自动拷贝，或手动把该字体放入 fonts/")

    # 2) 数据源：导入 student_master 会执行其中的所有 assert（数量/闭合/面积）
    print("\n-- 数据源 student_master --")
    try:
        import student_master as MD
        print("  [ok] student_master 导入成功，内置 assert 全部通过")
        # 抽查几个关键数量，证明数据完整
        checks = [
            ("ZONES(分区)", len(MD.ZONES)),
            ("WALLS(隔墙)", len(MD.WALLS)),
            ("DOORS(门)", len(MD.DOORS)),
            ("SPRINKLERS(喷淋)", len(MD.SPRINKLERS)),
            ("SMOKES(烟感)", len(MD.SMOKES)),
            ("LIGHTS(灯具)", len(MD.LIGHTS)),
            ("VENTS(风口)", len(MD.VENTS)),
            ("OUTLETS(地插)", len(MD.OUTLETS)),
            ("WORKSTATIONS(工位)", len(MD.WORKSTATIONS)),
        ]
        for label, n in checks:
            print("       %-18s = %d" % (label, n))
        # 外框闭合断言（直接复算，证明几何口径没漂移）
        assert sum(MD.XS[i+1]-MD.XS[i] for i in range(len(MD.XS)-1)) == 37000
        assert sum(MD.YS[i+1]-MD.YS[i] for i in range(len(MD.YS)-1)) == 37000
        ok &= check("X/Y 轴网严格闭合 37000", True)
    except Exception as e:
        ok = check("student_master 导入与断言: %r" % e, False)

    # 3) 后端
    print("\n-- DWG 后端 --")
    bk, path = config.dwg_backend()
    if bk == "dxf_only":
        print("  [提示] 后端=dxf_only：DWG 不会生成，DXF 为权威源（不影响 DXF/PDF/PNG 出图）")
    else:
        ok &= check("DWG 后端可用: %s" % bk, True)

    print("\n== 自检结果：%s ==" % ("全部通过 ✅" if ok else "有异常 ⚠️，见上"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
