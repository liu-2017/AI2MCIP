#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图 3（独立脚本，期刊规范版，灰度）：京津冀多城市 PM2.5 逐时演变时间序列

灰度绘图：链条用“灰度 + 线型 + 标记”区分，阶段阴影用“灰度 + 填充图案”区分，
黑白打印可辨。字号按期刊“6 号字”要求放大（约 9～9.5 pt），图例置于图底部，
阶段标签与城市名加白底，不覆盖数据。图下方含中英文对照图题。
"""
from __future__ import annotations

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import pandas as pd

from figs_common import FIG, CHAINS, NAME, load_series, load_city, panel_tag

# 阶段：起、止、灰度、填充图案、标签
PHASES = [
    ('2025-10-27', '2025-10-29', 0.94, None,     'P1 累积'),
    ('2025-10-29', '2025-10-31', 0.86, '///',    'P2 峰值'),
    ('2025-10-31', '2025-11-03', 0.94, '\\\\\\', 'P3 清除'),
    ('2025-11-03', '2025-11-05', 0.86, 'xxx',    'P4 二次累积'),
]

DEFAULT_CITIES = ('北京', '石家庄', '天津')

# 链条样式：灰度 + 线型 + 标记（黑白可辨）
_GREYS = [0.25, 0.32, 0.48, 0.64, 0.78]
_LS = ['-', '--', '-.', ':', (0, (3, 1, 1, 1))]
_MARKERS = ['o', 's', '^', 'D', 'v']

_YLABEL = r'$\rho(\mathrm{PM}_{2.5})$/(μg·m$^{-3}$)'


def _setup_style():
    """按期刊要求设置全局字体与字号（中文宋体、英文 Times New Roman，字号已放大）。"""
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
    # 字号：按最终排版 8～9 cm 宽设计
    plt.rcParams['font.size'] = 10
    plt.rcParams['axes.labelsize'] = 9.5
    plt.rcParams['xtick.labelsize'] = 9
    plt.rcParams['ytick.labelsize'] = 9
    plt.rcParams['legend.fontsize'] = 8
    plt.rcParams['axes.linewidth'] = 0.6
    plt.rcParams['xtick.direction'] = 'in'
    plt.rcParams['ytick.direction'] = 'in'
    plt.rcParams['hatch.linewidth'] = 0.4
    if cn is None:
        print('[警告] 未找到中文字体，中文可能显示为方框；请安装 SimSun/Songti SC。',
              file=sys.stderr)


def _grey(v):
    return plt.cm.Greys(v)


def _shade(ax):
    for a, b, g, h, _ in PHASES:
        kw = dict(facecolor=str(g), edgecolor='0.55', lw=0, alpha=0.60, zorder=0)
        if h:
            kw['hatch'] = h
        ax.axvspan(pd.Timestamp(a), pd.Timestamp(b), **kw)


def _day_ticks(ax, show_labels=True):
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.tick_params(axis='x', labelsize=9, rotation=0)
    if not show_labels:
        ax.set_xticklabels([])


def _set_tag(ax, text, dx=0.02, dy=0.01, size=10):
    """调用 panel_tag 后单独放大小字号，兼容其返回 None 的情况。"""
    t = panel_tag(ax, text, dx=dx, dy=dy)
    if t is not None and hasattr(t, 'set_fontsize'):
        t.set_fontsize(size)


def fig3(cities=DEFAULT_CITIES, out=None, width=7.2, dpi=600,
         title_cn=None, title_en=None, note=True):
    """绘制多城市 PM2.5 时间序列（期刊规范版，灰度，大字号）。

    Parameters
    ----------
    cities : sequence of str
        城市名，需与 ``data/stations.csv`` 中的 ``city_obs`` 一致。
    out : str | None
        输出路径；默认 ``figures/fig3_timeseries.png``。
    width : float
        图宽（英寸）。
    dpi : int
        位图分辨率；矢量格式（pdf/eps/svg）忽略。
    title_cn, title_en : str | None
        中英文图题；None 时使用默认。
    note : bool
        是否显示底部图注。
    """
    _setup_style()

    cities = list(cities)
    ser = load_series()
    m = load_city()

    avail = [c for c in cities if c in set(m.city)]
    missing = [c for c in cities if c not in set(m.city)]
    if missing:
        print('[警告] 以下城市无数据，已跳过：%s' % '、'.join(missing), file=sys.stderr)
        print('       可选城市：%s' % '、'.join(sorted(m.city.unique())), file=sys.stderr)
    if not avail:
        raise SystemExit('没有可绘制的城市。')

    n = len(avail)
    # 底部需要容纳：链条图例（两行）+ 阶段图例 + 图注 + 中英文图题
    height = 2.0 + 1.05 * n + 1.15
    fig = plt.figure(figsize=(width, height))
    gs = fig.add_gridspec(n + 1, 1, height_ratios=[1.5] + [1] * n, hspace=0.32)

    styles = {}
    for i, ch in enumerate(CHAINS):
        styles[ch] = dict(grey=_GREYS[i % len(_GREYS)],
                          ls=_LS[i % len(_LS)],
                          marker=_MARKERS[i % len(_MARKERS)])

    # ---------------- (a) 区域平均
    ax = fig.add_subplot(gs[0])
    _shade(ax)
    o = ser[ser.chain == 'PANGU']
    ax.plot(o.dt, o.obs, color='k', lw=1.8, label='观测（14城市均值）', zorder=5)
    for ch in CHAINS:
        s = ser[ser.chain == ch]
        if len(s) == 0:
            continue
        st = styles[ch]
        ax.plot(s.dt, s['sim'], lw=1.0, color=_grey(st['grey']),
                linestyle=st['ls'], marker=st['marker'], ms=2.0, markevery=6,
                zorder=4)
    ax.set_ylabel(_YLABEL)
    ax.set_xlim(pd.Timestamp('2025-10-26 20:00'), pd.Timestamp('2025-11-05 02:00'))
    ax.set_ylim(0, 200)
    # 阶段标签：白底、贴近底部，不压数据
    for a, b, _, _, label in PHASES:
        mid = pd.Timestamp(a) + (pd.Timestamp(b) - pd.Timestamp(a)) / 2
        ax.text(mid, 4, label, fontsize=8.5, ha='center', va='bottom',
                color='#333333', zorder=6,
                bbox=dict(fc='white', ec='none', alpha=0.9, pad=0.9))
    _day_ticks(ax)
    _set_tag(ax, '(a)', dx=-0.09, dy=0.01, size=10)

    # ---------------- (b) 逐城市
    for k, city in enumerate(avail):
        ax = fig.add_subplot(gs[k + 1])
        _shade(ax)
        sub = m[m.city == city]
        ob = sub[sub.chain == 'PANGU'][['dt', 'obs']].drop_duplicates('dt')
        ax.plot(ob.dt, ob.obs, color='k', lw=1.6, zorder=5)
        for ch in CHAINS:
            s = sub[sub.chain == ch]
            if len(s) == 0:
                continue
            st = styles[ch]
            ax.plot(s.dt, s['sim'], lw=0.9, color=_grey(st['grey']),
                    linestyle=st['ls'], marker=st['marker'], ms=1.8, markevery=6,
                    zorder=4)
        # 共享量纲：仅第一个城市面板标注 y 轴标目
        if k == 1:
            ax.set_ylabel(_YLABEL)
        # 城市名：左上角白底，不压曲线
        ax.text(0.006, 0.92, city, transform=ax.transAxes, fontsize=9.5,
                fontweight='bold', va='top', zorder=6,
                bbox=dict(fc='white', ec='none', alpha=0.85, pad=1.2))
        ax.set_xlim(pd.Timestamp('2025-10-26 20:00'), pd.Timestamp('2025-11-05 02:00'))
        _day_ticks(ax, show_labels=(k == n - 1))
        if k == 0:
            _set_tag(ax, '(b)', dx=-0.09, dy=0.01, size=10)
        if k == n - 1:
            ax.set_xlabel('日期')

    fig.subplots_adjust(left=0.11, right=0.98, top=0.96, bottom=0.32)

    # ---------------- 图例：链条（可两行）+ 阶段（一行）
    chain_handles = [Line2D([0], [0], color='k', lw=1.8, label='观测（14城市均值）')]
    for ch in CHAINS:
        st = styles[ch]
        chain_handles.append(
            Line2D([0], [0], color=_grey(st['grey']), ls=st['ls'],
                   marker=st['marker'], ms=4, lw=1.0, label=NAME[ch]))
    fig.legend(handles=chain_handles, loc='lower center',
               bbox_to_anchor=(0.5, 0.178), ncol=4,
               frameon=False, fontsize=8, handlelength=2.6,
               columnspacing=1.4, handletextpad=0.4, labelspacing=0.4)

    phase_handles = [
        Patch(facecolor=str(g), edgecolor='0.55', lw=0,
              hatch=(h if h else None), alpha=0.60, label=lab)
        for _, _, g, h, lab in PHASES
    ]
    fig.legend(handles=phase_handles, loc='lower center',
               bbox_to_anchor=(0.5, 0.128), ncol=4,
               frameon=False, fontsize=8, handlelength=1.8,
               columnspacing=1.4, handletextpad=0.4)

    # ---------------- 图注
    if note:
        note_txt = '注：阴影为 P1—P4 阶段；时间轴为 UTC；观测为 14 城市算术平均。'
        fig.text(0.5, 0.090, note_txt, ha='center', va='top', fontsize=8)

    # ---------------- 中英文图题
    # if title_cn is None:
    #     title_cn = ('图3  京津冀及周边14城市PM₂.₅逐时演变'
    #                 '（2025-10-27—11-04，UTC）')
    # if title_en is None:
    #     title_en = ('Fig.3  Hourly evolution of PM₂.₅ in 14 cities of '
    #                 'Beijing-Tianjin-Hebei and surrounding areas '
    #                 '(2025-10-27—11-04, UTC)')
    # fig.text(0.5, 0.052, title_cn, ha='center', va='bottom',fontsize=11, fontweight='bold')
    # fig.text(0.5, 0.016, title_en, ha='center', va='bottom',fontsize=11, fontweight='bold')

    out = out or os.path.join(FIG, 'fig3_timeseries.png')
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
    ap = argparse.ArgumentParser(description='图 3：多城市 PM2.5 逐时时间序列（灰度、大字号）')
    ap.add_argument('--cities', nargs='+', default=list(DEFAULT_CITIES),
                    help='城市列表，默认 北京 石家庄 天津')
    ap.add_argument('--out', default=None,
                    help='输出路径（默认 figures/fig3_timeseries.png）')
    ap.add_argument('--width', type=float, default=7.2, help='图宽（英寸）')
    ap.add_argument('--dpi', type=int, default=600, help='位图分辨率（默认 600）')
    ap.add_argument('--title-cn', default=None, help='中文图题')
    ap.add_argument('--title-en', default=None, help='英文图题')
    ap.add_argument('--no-note', action='store_true', help='不显示底部图注')
    args = ap.parse_args(argv)
    kw = {}
    if args.title_cn:
        kw['title_cn'] = args.title_cn
    if args.title_en:
        kw['title_en'] = args.title_en
    fig3(cities=args.cities, out=args.out, width=args.width, dpi=args.dpi,
         note=not args.no_note, **kw)


if __name__ == '__main__':
    main()