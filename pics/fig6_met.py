#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图 6（期刊规范版，灰度）：PBLH、10 m 风速与通风指数诊断

灰度绘图：链条用“灰度 + 线型 + 标记”三重区分，阶段阴影用“灰度 + 填充图案”区分，
黑白打印可辨。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))          # scripts/（figs_common 所在）

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

from figs_common import D, FIG, CHAINS, NAME, panel_tag

# 链条样式：灰度 + 线型 + 标记（保证黑白可辨）
_GREYS = [0.15, 0.32, 0.48, 0.64, 0.78]
_LS = ['-', '--', '-.', ':', (0, (3, 1, 1, 1))]
_MARKERS = ['o', 's', '^', 'D', 'v']

# 阶段划分：起、止、灰度、填充图案、标签
PH = [
    ('2025-10-27', '2025-10-29', 0.94, None,    'P1 累积'),
    ('2025-10-29', '2025-10-31', 0.84, '///',   'P2 峰值'),
    ('2025-10-31', '2025-11-03', 0.94, '\\\\\\','P3 清除'),
    ('2025-11-03', '2025-11-05', 0.84, 'xxx',   'P4 二次累积'),
]


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
    # ---- 字号整体放大（原 7 / 7 / 6.5 / 6.5 / 6 → 9.5 / 9.5 / 8.5 / 8.5 / 8）----
    plt.rcParams['font.size'] = 12
    plt.rcParams['axes.labelsize'] = 12
    plt.rcParams['xtick.labelsize'] = 12
    plt.rcParams['ytick.labelsize'] = 12
    plt.rcParams['legend.fontsize'] = 12
    plt.rcParams['axes.linewidth'] = 0.6
    plt.rcParams['xtick.direction'] = 'in'
    plt.rcParams['ytick.direction'] = 'in'
    plt.rcParams['hatch.linewidth'] = 0.4
    if cn is None:
        print('[警告] 未找到中文字体，中文可能显示为方框；请安装 SimSun/Songti SC。',
              file=sys.stderr)


def _shade(ax):
    for a, b, g, h, _ in PH:
        kw = dict(facecolor=str(g), edgecolor='0.55', lw=0,
                  alpha=0.60, zorder=0)
        if h:
            kw['hatch'] = h
        ax.axvspan(pd.Timestamp(a), pd.Timestamp(b), **kw)


def _grey(v):
    return plt.cm.Greys(v)


def fig6(out=None, dpi=600, width=8.5,title_cn=None, title_en=None, note=True):
    """绘制 PBLH / 10 m 风速 / 通风指数诊断图（灰度版）。

    Parameters
    ----------
    out : str | None
        输出路径；默认 ``figures/fig6_met.png``。
    dpi : int
        位图分辨率；矢量格式（pdf/eps/svg）忽略。
    width : float
        图宽（英寸）；默认 8.5，配合放大后的字号。
    title_cn, title_en : str | None
        中英文图题；None 时使用默认。
    note : bool
        是否显示底部图注。
    """
    _setup_style()

    mt = pd.read_csv(os.path.join(D, 'met_city_rh.csv'), parse_dates=['time'])
    agg = pd.read_csv(os.path.join(D, 'met_daily.csv'), parse_dates=['day'])
    use = [c for c in CHAINS if c in set(agg.chain)]
    n = len(use)

    styles = {}
    for i, ch in enumerate(use):
        styles[ch] = dict(grey=_GREYS[i % len(_GREYS)],
                          ls=_LS[i % len(_LS)],
                          marker=_MARKERS[i % len(_MARKERS)])

    # 画布高度同步放大：6.4 → 7.2
    fig = plt.figure(figsize=(width, 7.2))
    gs = fig.add_gridspec(2, 2, hspace=0.42, wspace=0.30)

    # ---------------- (a) PBL 日变化（BJT）
    ax = fig.add_subplot(gs[0, 0])
    mt['bjt'] = (mt.time.dt.hour + 8) % 24
    for ch in use:
        st = styles[ch]
        s = mt[mt.chain == ch].groupby('bjt')['PBL'].mean()
        ax.plot(s.index, s.values, color=_grey(st['grey']),linestyle=st['ls'], marker=st['marker'], ms=3.2, lw=1.2)
    ax.set_xlabel('地方时/h')
    ax.set_ylabel('边界层高度/m')
    ax.set_xticks(range(0, 25, 4))
    panel_tag(ax, '(a)')

    # ---------------- (b) 逐日 PBL
    ax = fig.add_subplot(gs[0, 1])
    _shade(ax)
    for ch in use:
        st = styles[ch]
        s = agg[agg.chain == ch]
        ax.plot(s.day, s.PBL, color=_grey(st['grey']),linestyle=st['ls'], marker=st['marker'], ms=3.2, lw=1.2)
    ax.set_ylabel('边界层高度/m')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.tick_params(axis='x', labelsize=12, rotation=30)
    panel_tag(ax, '(b)')

    # ---------------- (c) 逐日 10 m 风速
    ax = fig.add_subplot(gs[1, 0])
    _shade(ax)
    for ch in use:
        st = styles[ch]
        s = agg[agg.chain == ch]
        ax.plot(s.day, s.WSPD, color=_grey(st['grey']),linestyle=st['ls'], marker=st['marker'], ms=3.2, lw=1.2)
    ax.set_xlabel('日期')
    ax.set_ylabel('10 m风速/(m·s⁻¹)')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.tick_params(axis='x', labelsize=12, rotation=30)
    panel_tag(ax, '(c)')

    # ---------------- (d) 逐日通风指数
    ax = fig.add_subplot(gs[1, 1])
    _shade(ax)
    for ch in use:
        st = styles[ch]
        s = agg[agg.chain == ch]
        ax.plot(s.day, s.VI, color=_grey(st['grey']),linestyle=st['ls'], marker=st['marker'], ms=3.2, lw=1.2)
    ax.set_xlabel('日期')
    ax.set_ylabel('通风指数/(m²·s⁻¹)')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.tick_params(axis='x', labelsize=12, rotation=30)
    panel_tag(ax, '(d)')

    fig.subplots_adjust(left=0.09, right=0.97, top=0.96, bottom=0.30)

    # ---------------- 图例（链条 + 阶段）
    chain_handles = [
        Line2D([0], [0], color=_grey(styles[ch]['grey']),
               linestyle=styles[ch]['ls'], marker=styles[ch]['marker'],
               ms=4, lw=1.2, label=NAME[ch])
        for ch in use
    ]
    fig.legend(handles=chain_handles, loc='lower center',
               bbox_to_anchor=(0.5, 0.175), ncol=min(n, 5),
               frameon=False, fontsize=12, handlelength=2.2,
               columnspacing=1.2, handletextpad=0.4)

    phase_handles = [
        Patch(facecolor=str(g), edgecolor='0.55', lw=0,
              hatch=(h if h else None), alpha=0.60, label=lab)
        for _, _, g, h, lab in PH
    ]
    fig.legend(handles=phase_handles, loc='lower center',
               bbox_to_anchor=(0.5, 0.135), ncol=4,
               frameon=False, fontsize=12, handlelength=1.6,
               columnspacing=1.2, handletextpad=0.4)

    # ---------------- 图注（说明 BJT 与通风指数定义）
    if note:
        note_txt = ('注：阴影区为 P1 累积、P2 峰值、P3 清除、P4 二次累积；'
                    '地方时为北京时（BJT）；通风指数为边界层高度与 10 m 风速之积。')
        fig.text(0.5, 0.092, note_txt, ha='center', va='top', fontsize=8)

    # # ---------------- 中英文图题
    # if title_cn is None:
    #     title_cn = '图6  各链条边界层高度、10 m风速与通风指数对比'
    # if title_en is None:
    #     title_en = ('Fig.6  Comparison of PBLH, 10 m wind speed and ventilation '
    #                 'index among different chains')
    # fig.text(0.5, 0.055, title_cn, ha='center', va='bottom',
    #          fontsize=11, fontweight='bold')
    # fig.text(0.5, 0.022, title_en, ha='center', va='bottom',
    #          fontsize=11, fontweight='bold')

    out = out or os.path.join(FIG, 'fig6_met.png')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    ext = os.path.splitext(out)[1].lower()
    if ext in ('.pdf', '.eps', '.svg'):
        fig.savefig(out, bbox_inches='tight')
    else:
        fig.savefig(out, bbox_inches='tight', dpi=dpi)
    plt.close(fig)
    print('saved: %s' % out)
    return out


if __name__ == '__main__':
    fig6()