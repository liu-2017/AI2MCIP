#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图 3（独立脚本，期刊规范版）：京津冀多城市 PM2.5 逐时演变时间序列

按《中国环境监测》插图规范调整：
  1. 坐标轴标目采用“量/单位”斜线格式（如 ρ(PM2.5)/(μg·m⁻³)）；
  2. 中文宋体、英文 Times New Roman，字号约 6 号（7.5 pt）；
  3. 多面板共享量纲只在外侧标注，避免冗余；
  4. 图下方补充中英文对照图题（中文黑体、英文 Times New Roman 加粗）；
  5. 为各链条增加线型区分，保证黑白打印仍可辨识；
  6. 默认 600 dpi，支持 PDF/EPS 矢量输出。

用法
----
    python3 pics/fig3_timeseries.py
    python3 pics/fig3_timeseries.py --cities 北京 天津
    python3 pics/fig3_timeseries.py --out figures/fig3.pdf --dpi 600
    python3 pics/fig3_timeseries.py --title-cn "图3 ..." --title-en "Fig.3 ..."
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
import pandas as pd

from figs_common import FIG, CHAINS, NAME, COLOR, MARKER, load_series, load_city, panel_tag

PHASES = [('2025-10-27', '2025-10-29', '#fff2cc', 'P1 累积'),
          ('2025-10-29', '2025-10-31', '#f8cbad', 'P2 峰值'),
          ('2025-10-31', '2025-11-03', '#e2efda', 'P3 清除'),
          ('2025-11-03', '2025-11-05', '#deebf7', 'P4 二次累积')]

DEFAULT_CITIES = ('北京', '石家庄', '天津')

# 黑白打印可辨识：不同链条用不同线型
_LINESTYLES = ['-', '--', '-.', ':', (0, (3, 1, 1, 1)), (0, (5, 1))]

_YLABEL = r'$\rho(\mathrm{PM}_{2.5})$/(μg·m$^{-3}$)'


def _setup_style():
    """按期刊要求设置全局字体与字号。"""
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
    plt.rcParams['font.size'] = 7.5
    plt.rcParams['axes.labelsize'] = 7.5
    plt.rcParams['xtick.labelsize'] = 7
    plt.rcParams['ytick.labelsize'] = 7
    plt.rcParams['legend.fontsize'] = 6
    plt.rcParams['axes.linewidth'] = 0.6
    plt.rcParams['xtick.direction'] = 'in'
    plt.rcParams['ytick.direction'] = 'in'
    if cn is None:
        print('[警告] 未找到中文字体，中文可能显示为方框；请安装 SimSun/Songti SC。',
              file=sys.stderr)


def _shade(ax):
    for a, b, c, _ in PHASES:
        ax.axvspan(pd.Timestamp(a), pd.Timestamp(b), color=c, alpha=0.55, lw=0)


def _day_ticks(ax, show_labels=True):
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.tick_params(axis='x', labelsize=7, rotation=0)
    if not show_labels:
        ax.set_xticklabels([])


def fig3(cities=DEFAULT_CITIES, out=None,
         title=None,
        #  title_cn='图3  京津冀及周边14城市PM$_{2.5}$逐时演变（2025-10-27—11-04，UTC）',
        #  title_en='Fig.3  Hourly evolution of PM$_{2.5}$ in 14 cities of Beijing-Tianjin-Hebei and surrounding areas (2025-10-27—11-04, UTC)',
         width=7.2, dpi=600, show_title=False):
    """绘制多城市 PM2.5 时间序列（期刊规范版）。

    Parameters
    ----------
    cities : sequence of str
        城市名，需与 ``data/stations.csv`` 中的 ``city_obs`` 一致。
    out : str | None
        输出路径；默认 ``figures/fig3_timeseries.png``。
    title : str | None
        面板 (a) 的标题；None 时使用默认。
    title_cn, title_en : str
        图下方中英文图题。
    width : float
        图宽（英寸）。
    dpi : int
        位图分辨率；矢量格式（pdf/eps/svg）忽略。
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
    height = 2.0 + 1.05 * n
    fig = plt.figure(figsize=(width, height))
    fig.subplots_adjust(left=0.10, right=0.98, top=0.96, bottom=0.12)
    gs = fig.add_gridspec(n + 1, 1, height_ratios=[1.5] + [1] * n, hspace=0.28)

    # if title is None:
    #     title = '京津冀及周边14城市平均PM$_{2.5}$逐时演变（2025-10-27—11-04，UTC）'

    # ---------------- (a) 区域平均
    ax = fig.add_subplot(gs[0])
    _shade(ax)
    o = ser[ser.chain == 'PANGU']
    ax.plot(o.dt, o.obs, color='k', lw=1.8, label='观测（14城市均值）', zorder=5)
    for i, ch in enumerate(CHAINS):
        s = ser[ser.chain == ch]
        if len(s) == 0:
            continue
        ax.plot(s.dt, s['sim'], lw=1.1, color=COLOR[ch], marker=MARKER[ch], ms=1.8,
                markevery=6, linestyle=_LINESTYLES[i % len(_LINESTYLES)],
                label=NAME[ch], zorder=4)
    ax.set_ylabel(_YLABEL)
    ax.set_xlim(pd.Timestamp('2025-10-26 20:00'), pd.Timestamp('2025-11-05 02:00'))
    ax.set_ylim(0, 200)
    ax.legend(ncol=6, fontsize=6, loc='upper center', frameon=True)
    
    # if show_title:
    #     ax.set_title(title, fontsize=9)

    for a, b, _, label in PHASES:
        mid = pd.Timestamp(a) + (pd.Timestamp(b) - pd.Timestamp(a)) / 2
        ax.text(mid, 3, label, fontsize=6.6, ha='center', va='bottom', color='#333333',
                bbox=dict(fc='white', ec='none', alpha=0.9, pad=0.9))
    _day_ticks(ax)
    panel_tag(ax, '(a)')

    # ---------------- (b) 逐城市
    for k, city in enumerate(avail):
        ax = fig.add_subplot(gs[k + 1])
        _shade(ax)
        sub = m[m.city == city]
        ob = sub[sub.chain == 'PANGU'][['dt', 'obs']].drop_duplicates('dt')
        ax.plot(ob.dt, ob.obs, color='k', lw=1.6)
        for i, ch in enumerate(CHAINS):
            s = sub[sub.chain == ch]
            if len(s) == 0:
                continue
            ax.plot(s.dt, s['sim'], lw=1.0, color=COLOR[ch], marker=MARKER[ch], ms=1.6,
                    markevery=6, linestyle=_LINESTYLES[i % len(_LINESTYLES)])
        # 共享量纲：仅第一个城市面板标注 y 轴标目，其余保留刻度
        if k == 0:
            ax.set_ylabel(_YLABEL)
        ax.text(0.006, 0.88, city, transform=ax.transAxes, fontsize=7.5, fontweight='bold',
                va='top', bbox=dict(fc='white', ec='none', alpha=0.7, pad=1.0))
        ax.set_xlim(pd.Timestamp('2025-10-26 20:00'), pd.Timestamp('2025-11-05 02:00'))
        _day_ticks(ax, show_labels=(k == n - 1))
        if k == 0:
            panel_tag(ax, '(b)', dx=-0.09, dy=0.01)
        if k == n - 1:
            ax.set_xlabel('日期')

    # # ---------------- 中英文图题（置于图下方）
    # fig.text(0.5, 0.045, title_cn, ha='center', va='bottom',
    #          fontsize=9, fontweight='bold')
    # fig.text(0.5, 0.018, title_en, ha='center', va='bottom',
    #          fontsize=9, fontweight='bold')

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
    ap = argparse.ArgumentParser(description='图 3：多城市 PM2.5 逐时时间序列（期刊规范版）')
    ap.add_argument('--cities', nargs='+', default=list(DEFAULT_CITIES),
                    help='城市列表，默认 北京 石家庄 天津')
    ap.add_argument('--out', default=None, help='输出路径（默认 figures/fig3_timeseries.png）')
    ap.add_argument('--width', type=float, default=7.2, help='图宽（英寸）')
    ap.add_argument('--dpi', type=int, default=600, help='位图分辨率（默认 600）')
    ap.add_argument('--no-title', action='store_true', help='不显示面板 (a) 标题')
    ap.add_argument('--title-cn', default=None, help='中文图题')
    ap.add_argument('--title-en', default=None, help='英文图题')
    args = ap.parse_args(argv)
    kw = {}
    if args.title_cn:
        kw['title_cn'] = args.title_cn
    if args.title_en:
        kw['title_en'] = args.title_en
    fig3(cities=args.cities, out=args.out, width=args.width, dpi=args.dpi, show_title=not args.no_title, **kw)


if __name__ == '__main__':
    main()