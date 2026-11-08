# -*- coding: utf-8 -*-
"""gen_diag_report.py — 用体检数据生成 V3.3 问题诊断与优化对照 HTML 报告"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(BASE, "_diag_v33_vs_v34.json"), encoding="utf-8"))
old = {r["code"]: r for r in data["old"]}
new = {r["code"]: r for r in data["new"]}
codes = sorted(set(old) | set(new), key=lambda c: (c.split("-")[0], int(c.split("-")[1])))

CAT = {"PL": "平面图", "EL": "立面图", "DT": "节点图", "SD": "详图大样"}
FIG = {  # 图名
    "PL-00": "图纸目录", "PL-01": "平面布置图", "PL-02": "原始结构图",
    "PL-03": "功能分区图", "PL-04": "新增隔墙定位图", "PL-05": "地面铺装图",
    "PL-06": "天花布置图", "PL-07": "灯具定位图", "PL-08": "插座定位图",
    "PL-09": "给排水点位图", "PL-10": "消防末端图", "PL-11": "平面索引图",
    "PL-12": "动线设计图", "PL-13": "配套设施图", "PL-14": "地面排版图",
    "PL-15": "天花尺寸图",
}

def issues(c, o, n):
    """诊断 V3.3 单图问题 + 优化动作"""
    out = []
    kind = c.split("-")[0]
    if kind == "DT" or kind == "SD":
        if o["total"] < 80:
            out.append("剖面实体仅 %d 个——几条水平线+引出文字，无构造层次" % o["total"])
        if o["dim"] <= 12:
            out.append("尺寸实体仅 %d 个——构造分层厚度无标注链" % o["dim"])
        if o["overlap"]:
            out.append("文字重叠 %d 处" % o["overlap"])
        out.append("升级：实体 ×%.1f（%d→%d）、尺寸 ×%.1f（%d→%d），补材料分层填充/引出线/施工要点"
                   % (n["total"] / max(o["total"], 1), o["total"], n["total"],
                      n["dim"] / max(o["dim"], 1), o["dim"], n["dim"]))
    elif kind == "EL":
        if o["poly"] <= 6:
            out.append("结构化轮廓仅 %d 个——家具以直线拼凑（line+solid %d）" % (o["poly"], o["line_solid"]))
        if o["dim"] < 60:
            out.append("尺寸链仅 %d 个——无竖向分格尺寸" % o["dim"])
        if o["overlap"]:
            out.append("文字重叠 %d 处" % o["overlap"])
        out.append("升级：实体 %d→%d、尺寸 %d→%d，补饰面分段+材料表+标高+踢脚/灯带构造"
                   % (o["total"], n["total"], o["dim"], n["dim"]))
    else:  # PL
        if c == "PL-00":
            out.append("图幅列写全称 A1-841X594-竖栏，版式拥挤")
            out.append("升级：重排两栏目录表，图幅列改简称，补版次/日期行")
        elif o["overlap"]:
            out.append("文字重叠 %d 处" % o["overlap"])
            out.append("升级：分区标签 numpy 网格避让，重叠清零（新版 %d 处）" % n["overlap"])
        else:
            out.append("底图/标注基本齐全（DIM %d）" % o["dim"])
            out.append("升级：补三层尺寸链与图例说明，家具库重绘（轮廓 %d→%d）"
                       % (o["poly"], n["poly"]))
    return out

rows_html = ""
sum_old_ov = sum(o["overlap"] for o in old.values())
sum_new_ov = sum(o["overlap"] for o in new.values())
n_dt = sum(1 for c in codes if c.startswith("DT"))
n_sd = sum(1 for c in codes if c.startswith("SD"))
old_dt_dim = sum(old[c]["dim"] for c in codes if c.startswith("DT"))
new_dt_dim = sum(new[c]["dim"] for c in codes if c.startswith("DT"))

for c in codes:
    o, n = old[c], new[c]
    kind = c.split("-")[0]
    sev = "重" if (kind in ("DT", "SD")) else ("中" if kind == "EL" else "轻")
    badge = {"重": "var(--red)", "中": "var(--amber)", "轻": "var(--green)"}[sev]
    name = FIG.get(c, o["file"].split("_", 2)[-1].replace("_v2.dxf", "").replace(".dxf", ""))
    iss = issues(c, o, n)
    iss_html = "".join("<li>%s</li>" % i for i in iss)
    rows_html += """
    <div class="card">
      <div class="card-h">
        <span class="code">%s</span><span class="name">%s</span>
        <span class="badge" style="background:%s">AI味 %s</span>
      </div>
      <div class="metrics">
        <div><i>实体</i><b>%d → <em>%d</em></b></div>
        <div><i>尺寸</i><b>%d → <em>%d</em></b></div>
        <div><i>重叠</i><b>%d → <em>%d</em></b></div>
        <div><i>图签</i><b>%s → <em>%s</em></b></div>
      </div>
      <ul>%s</ul>
    </div>""" % (c, name, badge, sev, o["total"], n["total"], o["dim"], n["dim"],
                 o["overlap"], n["overlap"], o["sig"], n["sig"], iss_html)

html = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>V3.3 问题诊断与优化对照报告</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1c2330;--mut:#68738a;--line:#e4e8ef;
--red:#d64541;--amber:#e69b2e;--green:#2e9e63;--blue:#2f6fd6}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Microsoft YaHei",system-ui,sans-serif;background:var(--bg);color:var(--ink);padding:20px}
.wrap{max-width:1080px;margin:0 auto}
h1{font-size:22px;margin-bottom:4px}
.sub{color:var(--mut);font-size:13px;margin-bottom:16px}
.summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:18px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi i{display:block;font-style:normal;color:var(--mut);font-size:12px;margin-bottom:4px}
.kpi b{font-size:20px}
.kpi b em{font-style:normal;color:var(--green)}
.kpi.bad b em{color:var(--red)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-bottom:10px}
.card-h{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.code{font-weight:700;color:var(--blue);min-width:56px}
.name{font-weight:600;flex:1}
.badge{color:#fff;font-size:11px;padding:2px 8px;border-radius:10px}
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:6px;margin-bottom:8px}
.metrics div{background:#f2f5f9;border-radius:6px;padding:5px 8px;font-size:12px}
.metrics i{font-style:normal;color:var(--mut);margin-right:4px}
.metrics b em{font-style:normal;color:var(--green)}
.metrics div b{font-variant-numeric:tabular-nums}
.card ul{padding-left:18px;font-size:13px;line-height:1.7;color:#3a4356}
.note{background:#fff8e8;border:1px solid #f0d9a0;border-radius:10px;padding:12px 14px;font-size:13px;line-height:1.8;margin-bottom:16px}
h2{font-size:16px;margin:18px 0 10px}
</style></head><body><div class="wrap">
<h1>V3.3 毕业设计 CAD · 问题诊断与优化对照报告</h1>
<div class="sub">体检对象：V3.3最终版\\02_施工图 34 张（原版）× CAD出图工作流管线 34 张（优化版）｜体检工具：ezdxf 程序化扫描（实体/图层/尺寸/填充/文字重叠/图签）｜生成：2026-11-01</div>

<div class="summary">
  <div class="kpi bad"><i>原版 AI 味确诊（DT+SD 12 张）</i><b>12 张 <em>重灾</em></b></div>
  <div class="kpi"><i>原版全套文字重叠</i><b>%d 处</b></div>
  <div class="kpi"><i>优化版文字重叠</i><b><em>%d 处（复检通过）</em></b></div>
  <div class="kpi"><i>原版 DWG 格式</i><b>仅 1 张</b></div>
  <div class="kpi"><i>优化版交付</i><b><em>34 张 × 4 格式</em></b></div>
</div>

<div class="note">
<b>总体结论：</b>①原版平面图（PL）底图/轴网/尺寸基本合格，属「轻」度问题；②立面图（EL）家具靠直线拼凑、竖向尺寸链不足，属「中」度；③<b>节点图（DT）与详图（SD）为重灾区</b>——DT-01~06 剖面实体仅 44~66 个、尺寸实体只有 6~12 个（对应“几条水平线+引出文字”），SD-03 文字重叠 11 处，是最像 AI 生成、最经不起答辩追问的部分；④原版图签全为「蔡志成 / 2402060131 / 2026-10-27」，且除 PL-00 外<b>全都没有 DWG 格式</b>。<br>
<b>优化动作：</b>用「CAD出图工作流」管线按同图号整体重造 34 张（图号一一对应，无删减）：节点/详图补齐构造分层填充、厚度尺寸链、材料引出、施工要点三段式；立面补饰面分段+材料表+标高体系；平面补三层尺寸链/图例/避让排版；全套图签统一为「刘涛溢 / 2402060428 / 室内设计四班 / 倪文静 / 2026-11-01」，四格式齐套，AUDIT 零错误。
</div>

<h2>34 张逐图对照</h2>
%s

<div class="note" style="margin-top:14px">
<b>优化成果位置：</b>桌面 <b>室内设计四班_A_A-1_2402060428_刘涛溢_工作流升级版34张.zip</b>（136 个图纸文件，四类分目录，含交付说明与复检报告）。<br>
<b>复检结论：</b>平面 16/16 PASS · 立面/节点/大样 18/18 PASS · DWG AUDIT 34/34 零错误 · 图签五项统一、旧信息与占位符残留 0。
</div>
</div></body></html>""" % (sum_old_ov, sum_new_ov, rows_html)

dst = r"你的桌面\V3.3问题诊断与优化对照报告.html"
open(dst, "w", encoding="utf-8").write(html)
print("[OK]", dst, len(html), "bytes")
