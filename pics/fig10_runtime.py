#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图 10（期刊规范版，灰度）：单位模拟日墙钟时间对比

灰度绘图：水平柱用“灰度 + 填充图案”区分四条链，黑白打印可辨。
数值标签置于柱体外侧，不覆盖柱体。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))          # scripts/（figs_common 所在）

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from figs_common import FIG


def _setup_style():
    """按期刊要求设置全局字体与字号（中文宋体、英文 Times New Roman）。"""
    import matplotlib.font_manager as fm
    available = {f.name for f in fm.fontManager.ttflist}
    cn_candidates = ['SimSun', 'Songti SC', 'Noto Serif CJK SC', 'STSong', 'SimHei']
    en_candidates = ['Times New Roman', 'Nimbus Roman', 'DejaVu Serif']
    cn = next((c for c in cn_candidates if c in available), None)
    en = next((c for c in en_candidates if c in available), None)
    family = ([en] if en else []) + ([cn] if cn else []) + ['DejaVu Sans']
    plt.rcParams['font.family'] = family
    plt.rcParams['font.sans-serif'] = family
    plt.rcParams['font.serif'] = family
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['mathtext.fontset'] = 'stix'
    plt.rcParams['font.size'] = 10
    plt.rcParams['axes.labelsize'] =10
    plt.rcParams['xtick.labelsize'] = 10
    plt.rcParams['ytick.labelsize'] = 10
    plt.rcParams['legend.fontsize'] = 10
    plt.rcParams['axes.linewidth'] = 0.6
    plt.rcParams['xtick.direction'] = 'in'
    plt.rcParams['ytick.direction'] = 'in'
    plt.rcParams['hatch.linewidth'] = 0.5
    if cn is None:
        print('[警告] 未找到中文字体，中文可能显示为方框；请安装 SimSun/Songti SC。',
              file=sys.stderr)


def _grey(v):
    return plt.cm.Greys(v)


def fig10(out=None, dpi=600, width=7.0,
          title_cn=None, title_en=None, note=True):
    """绘制单位模拟日墙钟时间对比（灰度版）。

    Parameters
    ----------
    out : str | None
        输出路径；默认 ``figures/fig10_runtime.png``。
    dpi : int
        位图分辨率；矢量格式（pdf/eps/svg）忽略。
    width : float
        图宽（英寸）。
    title_cn, title_en : str | None
        中英文图题；None 时使用默认。
    note : bool
        是否显示底部图注。
    """
    _setup_style()

    # ---------------- 原始墙钟时间（min/d），数据口径与原脚本一致
    data = {
        'WPS (ungrib+metgrid)': 0.10,
        'WRF v3.9 动力积分': 5.30,
        'AI 推理 (Pangu)': 1.20,
        'AI 推理 (FengWu)': 1.98,
        'AI 推理 (FengYuan)': 2.47,
        'AI-to-MCIP Adapter': 0.37,
        'MCIP': 0.05,
        'CMAQ CCTM': 2.88,
    }
    wrf = (data['WPS (ungrib+metgrid)'] + data['WRF v3.9 动力积分']
           + data['MCIP'] + data['CMAQ CCTM'])
    ai = {k: (data['AI 推理 (%s)' % k] + data['AI-to-MCIP Adapter']
              + data['MCIP'] + data['CMAQ CCTM'])
          for k in ['Pangu', 'FengWu', 'FengYuan']}

    names = ['WRF 链条', 'Pangu 链条', 'FengWu 链条', 'FengYuan 链条']
    vals = [wrf, ai['Pangu'], ai['FengWu'], ai['FengYuan']]

    # 灰度 + 填充图案：与柱内数值一一对应
    specs = [
        (_grey(0.35), None),    # WRF：中深灰，无图案
        (_grey(0.60), '///'),   # Pangu：中灰，斜线
        (_grey(0.80), '\\\\\\'), # FengWu：浅灰，反斜线
        (_grey(0.50), 'xxx'),   # FengYuan：中浅灰，交叉
    ]

    fig, ax = plt.subplots(figsize=(width, 3.6))
    y = list(range(len(names)))
    for i, (name, v, (c, h)) in enumerate(zip(names, vals, specs)):
        ax.barh(i, v, color=c, edgecolor='k', linewidth=0.5,
                height=0.55, hatch=(h if h else None), zorder=3)

    # 数值标签：柱体外侧，不压柱体
    xmax = max(vals)
    for i, v in enumerate(vals):
        ax.text(v + 0.05 * xmax, i, '%.1f min/d' % v,va='center', ha='left', fontsize=8, zorder=4)

    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel('单位模拟日墙钟时间/min')
    ax.set_xlim(0, xmax * 1.28)
    ax.xaxis.grid(True, linestyle=':', linewidth=0.5, color='0.7', zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis='y', length=0)

    fig.subplots_adjust(left=0.16, right=0.98, top=0.96, bottom=0.34)

    # ---------------- 图注：气象环节时间对比（原脚本底注）
    wps_wrf = data['WPS (ungrib+metgrid)'] + data['WRF v3.9 动力积分']
    ai_pangu = data['AI 推理 (Pangu)'] + data['AI-to-MCIP Adapter']
    ai_fy = data['AI 推理 (FengYuan)'] + data['AI-to-MCIP Adapter']
    if note:
        note_txt = ('注：气象环节 WRF 为 WPS %.2f + 动力积分 %.2f = %.2f min/d；'
                    'AI 为推理 + Adapter，Pangu %.2f、FengYuan %.2f min/d；'
                    'WRF 气象环节为 AI 的 %.1f—%.1f 倍；'
                    '化学环节 MCIP + CCTM 为各链条共有，已计入总量。'
                    % (data['WPS (ungrib+metgrid)'],
                       data['WRF v3.9 动力积分'], wps_wrf,
                       ai_pangu, ai_fy,
                       wps_wrf / ai_fy, wps_wrf / ai_pangu))
        fig.text(0.5, 0.175, note_txt, ha='center', va='top',
                 fontsize=6.5, linespacing=1.5)

    # ---------------- 中英文图题
    if title_cn is None:
        title_cn = '图10  不同气象驱动链条的单位模拟日墙钟时间对比'
    if title_en is None:
        title_en = ('Fig.10  Comparison of wall-clock time per simulated day '
                    'among different meteorological driving chains')
    fig.text(0.5, 0.085, title_cn, ha='center', va='bottom',
             fontsize=9, fontweight='bold')
    fig.text(0.5, 0.030, title_en, ha='center', va='bottom',
             fontsize=9, fontweight='bold')

    out = out or os.path.join(FIG, 'fig10_runtime.png')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    ext = os.path.splitext(out)[1].lower()
    if ext in ('.pdf', '.eps', '.svg'):
        fig.savefig(out, bbox_inches='tight')
    else:
        fig.savefig(out, bbox_inches='tight', dpi=dpi)
    plt.close(fig)
    print('saved: %s' % out)
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description='图 10：单位模拟日墙钟时间对比（灰度版）')
    ap.add_argument('--out', default=None,
                    help='输出路径（默认 figures/fig10_runtime.png）')
    ap.add_argument('--dpi', type=int, default=600, help='位图分辨率（默认 600）')
    ap.add_argument('--width', type=float, default=7.0, help='图宽（英寸）')
    ap.add_argument('--title-cn', default=None, help='中文图题')
    ap.add_argument('--title-en', default=None, help='英文图题')
    ap.add_argument('--no-note', action='store_true', help='不显示底部图注')
    args = ap.parse_args(argv)
    kw = {}
    if args.title_cn:
        kw['title_cn'] = args.title_cn
    if args.title_en:
        kw['title_en'] = args.title_en
    fig10(out=args.out, dpi=args.dpi, width=args.width,
          note=not args.no_note, **kw)


if __name__ == '__main__':
    main()