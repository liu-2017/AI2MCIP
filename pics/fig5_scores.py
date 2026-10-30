#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图 5（期刊规范版，灰度）：PM2.5 统计指标（散点、R/IOA、分阶段 NMB 与 RMSE）

灰度绘图：用不同灰度 + 填充图案 + 标记形状区分各链条，黑白打印可辨。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from figs_common import D, FIG, CHAINS, NAME, load_city, panel_tag


# 灰度值 + 填充图案 + 标记：保证黑白打印可辨
_GREYS = [0.15, 0.32, 0.48, 0.64, 0.78]
_HATCHES = ['', '//', '\\\\', 'xx', '..']
_MARKERS = ['o', 's', '^', 'D', 'v']


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
    plt.rcParams['axes.labelsize'] = 10
    plt.rcParams['xtick.labelsize'] = 10
    plt.rcParams['ytick.labelsize'] = 10
    plt.rcParams['legend.fontsize'] = 10
    plt.rcParams['axes.linewidth'] = 0.5
    plt.rcParams['xtick.direction'] = 'in'
    plt.rcParams['ytick.direction'] = 'in'
    if cn is None:
        print('[警告] 未找到中文字体，中文可能显示为方框；请安装 SimSun/Songti SC。',
              file=sys.stderr)


def _grey(v):
    """按灰度值取颜色（0=黑，1=白）。"""
    return plt.cm.Greys(v)


def fig5(out=None, dpi=600, width=7.2,
         title_cn=None, title_en=None):
    """绘制统计指标四面板图（灰度版）。

    Parameters
    ----------
    out : str | None
        输出路径；默认 ``figures/fig5_scores.png``。
    dpi : int
        位图分辨率；矢量格式（pdf/eps/svg）忽略。
    width : float
        图宽（英寸）。
    title_cn, title_en : str | None
        中英文图题；None 时使用默认。
    """
    _setup_style()

    tot = pd.read_csv(os.path.join(D, 'scores_total.csv')).set_index('chain')
    ph = pd.read_csv(os.path.join(D, 'scores_phase.csv'))
    m = load_city()
    use = [c for c in CHAINS if c in tot.index]
    n = len(use)

    greys = {ch: _GREYS[i % len(_GREYS)] for i, ch in enumerate(use)}
    hatches = {ch: _HATCHES[i % len(_HATCHES)] for i, ch in enumerate(use)}
    markers = {ch: _MARKERS[i % len(_MARKERS)] for i, ch in enumerate(use)}

    fig = plt.figure(figsize=(width, 5.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], hspace=0.42, wspace=0.32)

    # ---------------- (a) 散点：观测 vs 模拟
    ax = fig.add_subplot(gs[0, 0])
    for ch in use:
        g = m[m.chain == ch]
        ax.scatter(g.obs, g.sim, s=4, alpha=0.45,
                   facecolors=_grey(greys[ch]), edgecolors='none',
                   marker=markers[ch], label=NAME[ch], linewidths=0)
    ax.plot([0, 260], [0, 260], 'k--', lw=0.8)
    ax.set_xlim(0, 260); ax.set_ylim(0, 260)
    ax.set_xlabel('观测ρ(PM₂.₅)/(μg·m⁻³)')
    ax.set_ylabel('模拟ρ(PM₂.₅)/(μg·m⁻³)')
    ax.legend(fontsize=5.5, markerscale=2.2, loc='upper left', frameon=True,handletextpad=0.3, labelspacing=0.25, borderpad=0.35)
    panel_tag(ax, '(a)')

    # ---------------- (b) R / IOA
    ax = fig.add_subplot(gs[0, 1])
    x = np.arange(n); w = 0.36
    ax.bar(x - w/2, tot.loc[use, 'R'], w, color='0.68', edgecolor='k', lw=0.4,label='R')
    ax.bar(x + w/2, tot.loc[use, 'IOA'], w, color='0.32', edgecolor='k', lw=0.4, hatch='//', label='IOA')

    ax.set_xticks(x); ax.set_xticklabels([NAME[c] for c in use], rotation=20,fontsize=8, ha='right')
    ax.set_ylim(0, 1); ax.set_ylabel('统计量')
    ax.legend(fontsize=6.5, ncol=2, loc='upper right')
    panel_tag(ax, '(b)')

    # ---------------- (c) 分阶段 NMB
    ax = fig.add_subplot(gs[1, 0])
    nmb = ph.pivot(index='phase', columns='chain', values='NMB').loc[:, use]
    x = np.arange(len(nmb)); w = 0.8 / n
    for i, ch in enumerate(use):
        ax.bar(x + (i - (n - 1) / 2) * w, nmb[ch], w * 0.92,
               color=_grey(greys[ch]), edgecolor='k', lw=0.4,
               hatch=hatches[ch])
    ax.axhline(0, color='k', lw=0.7)
    ax.set_xticks(x); ax.set_xticklabels(nmb.index, fontsize=10)
    ax.set_ylabel('NMB/%')
    panel_tag(ax, '(c)')

    # ---------------- (d) 分阶段 RMSE
    ax = fig.add_subplot(gs[1, 1])
    rm = ph.pivot(index='phase', columns='chain', values='RMSE').loc[:, use]
    for i, ch in enumerate(use):
        ax.bar(x + (i - (n - 1) / 2) * w, rm[ch], w * 0.92,color=_grey(greys[ch]), edgecolor='k', lw=0.4,hatch=hatches[ch])
    ax.set_xticks(x); ax.set_xticklabels(rm.index, fontsize=10)
    ax.set_ylabel('RMSE/(μg·m⁻³)')
    panel_tag(ax, '(d)')

    fig.subplots_adjust(left=0.09, right=0.97, top=0.95, bottom=0.22)

    # ---------------- 统一链条图例（(c)(d) 下方横排）
    chain_handles = [
        Patch(facecolor=_grey(greys[ch]), edgecolor='k', lw=0.4,hatch=hatches[ch], label=NAME[ch])
        for ch in use
    ]
    fig.legend(handles=chain_handles, loc='lower center',
               bbox_to_anchor=(0.5, 0.115), ncol=min(n, 5),
               frameon=False, fontsize=10, handlelength=1.6,
               columnspacing=1.2, handletextpad=0.3)

    # ---------------- 中英文图题
    # if title_cn is None:
    #     title_cn = '图5  各链条PM₂.₅模拟效果统计指标对比'
    # if title_en is None:
    #     title_en = ('Fig.5  Comparison of statistical metrics for PM₂.₅ '
    #                 'simulations among different chains')
    fig.text(0.5, 0.055, title_cn, ha='center', va='bottom',
             fontsize=9, fontweight='bold')
    fig.text(0.5, 0.020, title_en, ha='center', va='bottom',
             fontsize=9, fontweight='bold')

    out = out or os.path.join(FIG, 'fig5_scores.png')
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
    fig5()