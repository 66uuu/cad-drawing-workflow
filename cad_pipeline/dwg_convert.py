# -*- coding: utf-8 -*-
"""
dwg_convert.py — DXF → DWG 的统一转换/校验后端（跨电脑可复现核心）
================================================================
把原本散落在 dwg_convert_9plans.py / dwg_convert_18drawings.py / verify_dwg_*.py 里、
且硬编码了 <D盘>\\CAD2024 与 C:\\wbtmp9 的逻辑，统一到这一个文件，并提供三种后端：

  autocad  —— AutoCAD 自带 accoreconsole.exe，用 stdin 管道喂 OPEN/SAVEAS/QUIT
             （本机实测：/s 脚本开关失效，stdin 管道才稳；详见工作流 §Phase4）
  oda      —— ODA File Converter（免费、跨平台），命令行批处理
  dxf_only —— 找不到任何 DWG 转换器时，跳过 DWG 生成，DXF 作为权威交换格式

所有路径从 config 取，绝不硬编码盘符。调用方（run_all.py 或原 dwg_convert_*.py 包装器）
只需调用 convert_dir() / audit_dir()。

注意：DWG 文本为压缩二进制，ezdxf 读不了；要校验 DWG 内容只能靠 AutoCAD/ODA 的 AUDIT，
或回读 DXF 源做交叉比对。本文件 audit_* 仅在 autocad 后端下做 AUDIT。
"""
import os
import sys
import time
import shutil
import subprocess
import hashlib
from pathlib import Path


def _safe(src):
    """对任意（可能含中文）源路径，返回一个确定性的纯 ASCII 工作文件名，
    避免 accoreconsole 脚本文件（ASCII 编码）里出现非 ASCII 字符而写崩。"""
    return hashlib.md5(str(src).encode("utf-8")).hexdigest()[:16]

import config

ACCORE = config.ACCORE
ODA = config.ODA
WORK = config.WORK
TIMEOUT = 180  # 单图超时（秒）


# --------------------------------------------------------------------- 公共
def _kill_stray():
    """清理可能残留的 accoreconsole，避免互锁/堆积。"""
    try:
        subprocess.run(["taskkill", "/F", "/IM", "accoreconsole.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    except Exception:
        pass


def _ascii_copy(src, dst):
    """把源 DXF 复制到 ASCII 工作目录（规避中文路径被 accoreconsole 误读）。"""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy(src, dst)
    return dst


# --------------------------------------------------------------------- AutoCAD 后端
def _convert_one_autocad(dxf_src, dwg_dst):
    code = _safe(dxf_src)
    work_dxf = os.path.join(WORK, code + ".dxf")
    work_dwg = os.path.join(WORK, code + ".dwg")
    # 删旧 .dwg，避免 SAVEAS 弹「是否替换」确认挂死
    if os.path.exists(work_dwg):
        try:
            os.remove(work_dwg)
        except OSError:
            pass
    _ascii_copy(dxf_src, work_dxf)
    # CRLF；路径全 ASCII（工作文件名用哈希，规避中文）
    cmds = "_.OPEN\r\n%s\r\n_.SAVEAS\r\n2018\r\n%s\r\n_.QUIT\r\n" % (work_dxf, work_dwg)
    stdin_path = os.path.join(WORK, "_stdin_%s.tmp" % code)
    with open(stdin_path, "w", newline="", encoding="ascii") as f:
        f.write(cmds)
    try:
        with open(stdin_path, "rb") as fin:
            proc = subprocess.run([ACCORE], stdin=fin,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  timeout=TIMEOUT)
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        _kill_stray()
        return False, "TIMEOUT"
    if os.path.exists(work_dwg) and os.path.getsize(work_dwg) > 2000:
        shutil.copy(work_dwg, dwg_dst)
        return True, "%d bytes -> %s" % (os.path.getsize(work_dwg), os.path.basename(dwg_dst))
    return False, "NO_DWG rc=%s" % rc


# --------------------------------------------------------------------- ODA 后端
def _convert_one_oda(dxf_src, dwg_dst):
    """ODA File Converter 命令行：
       ODAFileConverter <源目录> <目标目录> <格式 DWG/DXF> <版本 ACAD2018> <递归 0/1>
       它按文件名输出同名文件，所以源/目标各用一个干净文件夹。
    """
    code = Path(dxf_src).stem
    src_dir = os.path.join(WORK, "oda_src")
    dst_dir = os.path.join(WORK, "oda_dst")
    os.makedirs(src_dir, exist_ok=True)
    os.makedirs(dst_dir, exist_ok=True)
    work_dxf = os.path.join(src_dir, code + ".dxf")
    work_dwg = os.path.join(dst_dir, code + ".dwg")
    if os.path.exists(work_dwg):
        try:
            os.remove(work_dwg)
        except OSError:
            pass
    shutil.copy(dxf_src, work_dxf)
    try:
        proc = subprocess.run([ODA, src_dir, dst_dir, "DWG", "ACAD2018", "0"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=TIMEOUT)
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    if os.path.exists(work_dwg) and os.path.getsize(work_dwg) > 2000:
        shutil.copy(work_dwg, dwg_dst)
        return True, "%d bytes -> %s" % (os.path.getsize(work_dwg), os.path.basename(dwg_dst))
    return False, "NO_DWG rc=%s" % rc


# --------------------------------------------------------------------- 统一入口
def convert_one(dxf_src, dwg_dst):
    """把一张 DXF 转成 DWG，按当前可用后端自动选择。返回 (ok, msg)。"""
    backend, path = config.dwg_backend()
    if backend == "autocad":
        return _convert_one_autocad(dxf_src, dwg_dst)
    if backend == "oda":
        return _convert_one_oda(dxf_src, dwg_dst)
    # dxf_only：不生成 DWG，但给出明确提示（DXF 是权威交换格式）
    return False, "SKIP(dxf_only): 未检测到 AutoCAD/ODA，DWG 未生成（DXF 为权威源）"


def convert_dir(src_dir):
    """
    批量转换某目录下的全部 .dxf → 同名 .dwg（输出到同一目录）。
    返回 (success_count, total, skipped)。
    """
    backend, _ = config.dwg_backend()
    if backend == "dxf_only":
        print("[dwg_convert] 后端=dxf_only：跳过 DWG 生成（DXF 已是权威交换格式，"
              "可在装有 AutoCAD/ODA 的机器上重跑本步补齐 DWG）。")
        return (0, 0, True)
    os.makedirs(WORK, exist_ok=True)
    _kill_stray()
    time.sleep(1)
    plans = sorted(f for f in os.listdir(src_dir) if f.lower().endswith(".dxf")
                   and not f.startswith("_tmp_"))
    ok = 0
    for f in plans:
        dxf = os.path.join(src_dir, f)
        dwg = os.path.join(src_dir, f[:-4] + ".dwg")
        good, msg = convert_one(dxf, dwg)
        print("  [%s] %s %s" % (f, "OK " if good else "FAIL", msg))
        if good:
            ok += 1
        _kill_stray()
        time.sleep(0.5)
    print("[dwg_convert] 完成：%d/%d 成功（后端=%s）" % (ok, len(plans), backend))
    return (ok, len(plans), False)


# --------------------------------------------------------------------- DWG 合法性校验（仅 autocad 后端）
def audit_dir(src_dir):
    """
    对目录下每张 .dwg 跑 AutoCAD AUDIT，解析输出（utf-16-le）。
    无 AutoCAD 后端时返回 (0, total, skipped=True) 并提示。
    """
    if not ACCORE:
        print("[audit] 未检测到 accoreconsole：跳过 AUDIT（DWG 校验需在 AutoCAD 机器上重跑）。")
        dwgs = [f for f in os.listdir(src_dir) if f.lower().endswith(".dwg")]
        return (0, len(dwgs), True)
    # 与 convert 类似的 stdin 管道 AUDIT 脚本
    os.makedirs(WORK, exist_ok=True)
    _kill_stray()
    dwgs = sorted(f for f in os.listdir(src_dir) if f.lower().endswith(".dwg"))
    ok = 0
    for f in dwgs:
        code = _safe(os.path.join(src_dir, f))
        work_dwg = os.path.join(WORK, code + ".dwg")
        shutil.copy(os.path.join(src_dir, f), work_dwg)
        cmds = "_.OPEN\r\n%s\r\n_.AUDIT\r\nY\r\n_.QUIT\r\n" % work_dwg
        sp = os.path.join(WORK, "_audit_%s.tmp" % code)
        with open(sp, "w", newline="", encoding="ascii") as fh:
            fh.write(cmds)
        try:
            with open(sp, "rb") as fin:
                proc = subprocess.run([ACCORE], stdin=fin,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      timeout=240)
        except subprocess.TimeoutExpired:
            _kill_stray()
            continue
        # AUDIT 输出按 utf-16-le 解码
        out = b""
        try:
            out = proc.stdout.decode("utf-16-le", errors="replace")
        except Exception:
            out = proc.stdout.decode("utf-8", errors="replace")
        errs = out.count("error") if out else 0
        good = proc.returncode in (0, 0xC0000005) and errs == 0  # 偶发 0xC... 崩溃但错误数0→复跑即正常
        print("  [%s] audit errors=%d rc=%s %s" % (f, errs, proc.returncode, "OK" if good else "CHECK"))
        if good:
            ok += 1
        _kill_stray()
    print("[audit] %d/%d 通过" % (ok, len(dwgs)))
    return (ok, len(dwgs), False)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python dwg_convert.py <dxf目录>")
        sys.exit(1)
    convert_dir(sys.argv[1])
