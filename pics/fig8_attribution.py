#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图 8（期刊规范版，灰度）：偏差归因（通风/PBLH 偏差 vs NMB、链条替换效应、逐日偏差）

灰度绘图：散点/线条用“灰度 + 标记”区分，替换效应柱用“灰度 + 填充图案”区分。
(a)(b) 的统计文字（r、n）置于面板右上角空白处，不覆盖数据点。
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
import matplotlib.dates as mdates
from matplotlib.lines import Line2D

from figs_common import D, FIG, CHAINS, NAME, load_city, panel_tag

_GREYS = [0.15, 0.32, 0.48, 0.64, 0.78]
_MARKERS = ['o', 's', '^', 'D', 'v']


def _setup_style():
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
    plt.rcParams['hatch.linewidth'] = 0.4
    if cn is None:
        print('[警告] 未找到中文字体，中文可能显示为方框；请安装 SimSun/Songti SC。',
              file=sys.stderr)


def _grey(v):
    return plt.cm.Greys(v)


def _corner_text(ax, txt):
    """右上角统计文字：右对齐、顶对齐、白底半透明，不压数据。"""
    ax.text(0.965, 0.955, txt, transform=ax.transAxes,
            ha='right', va='top', fontsize=7, zorder=10,
            bbox=dict(fc='white', ec='none', alpha=0.82, pad=1.6))


def fig8(out=None, dpi=600, width=7.2,
         title_cn=None, title_en=None, note=True):
    """绘制偏差归因四面板图（灰度版）。"""
    _setup_style()

    # ---------------- 数据准备（与原脚本一致）
    m = load_city()
    m['day'] = m.dt.dt.date
    dn = m.groupby(['chain', 'day']).apply(
        lambda g: 100 * (g.sim - g.obs).sum() / g.obs.sum(),
        include_groups=False).rename('nmb')
    agg = pd.read_csv(os.path.join(D, 'met_daily.csv'), parse_dates=['day'])
    agg['day'] = agg.day.dt.date
    ref = agg[agg.chain == 'ERA5_ADP'].set_index('day')
    rows = []
    for ch in agg.chain.unique():
        s = agg[agg.chain == ch].set_index('day')
        for d in s.index:
            if d not in ref.index:
                continue
            rows.append(dict(chain=ch, day=d,
                             dPBL=100 * (s.loc[d, 'PBL'] / ref.loc[d, 'PBL'] - 1),
                             dWSP=100 * (s.loc[d, 'WSPD'] / ref.loc[d, 'WSPD'] - 1),
                             dVI=100 * (s.loc[d, 'VI'] / ref.loc[d, 'VI'] - 1)))
    met = pd.DataFrame(rows).set_index(['chain', 'day'])
    j = dn.to_frame().join(met, how='inner').reset_index()
    j.to_csv(os.path.join(D, 'attribution.csv'), index=False, float_format='%.2f')

    use = [c for c in CHAINS if c in set(j.chain)]
    n = len(use)
    styles = {ch: dict(grey=_GREYS[i % len(_GREYS)],
                       marker=_MARKERS[i % len(_MARKERS)])
              for i, ch in enumerate(use)}

    fig = plt.figure(figsize=(width, 5.6))
    gs = fig.add_gridspec(2, 2, hspace=0.44, wspace=0.32)

    kk = j[j.chain != 'ERA5_ADP']

    # ---------------- (a) 通风指数偏差 vs NMB
    ax = fig.add_subplot(gs[0, 0])
    for ch in use:
        st = styles[ch]
        s = j[j.chain == ch]
        ax.scatter(s.dVI, s.nmb, s=26, color=_grey(st['grey']),marker=st['marker'], edgecolor='k', lw=0.4,label=NAME[ch], zorder=3)
    ax.axhline(0, color='0.5', lw=0.7, zorder=1)
    ax.axvline(0, color='0.5', lw=0.7, zorder=1)
    if len(kk) >= 2:
        z = np.polyfit(kk.dVI, kk.nmb, 1)
        xx = np.linspace(kk.dVI.min(), kk.dVI.max(), 10)
        r_vi = np.corrcoef(kk.dVI, kk.nmb)[0, 1]
        ax.plot(xx, np.polyval(z, xx), 'k--', lw=0.9, zorder=2)
        # 抬高 y 轴上限，给右上角文字留空白
        y0, y1 = ax.get_ylim()
        ax.set_ylim(y0, y1 + 0.18 * (y1 - y0))
        _corner_text(ax, 'r = %.2f\nn = %d' % (r_vi, len(kk)))
    ax.set_xlabel('通风指数相对偏差/%')
    ax.set_ylabel('NMB/%')
    ax.margins(x=0.08)
    panel_tag(ax, '(a)')

    # ---------------- (b) PBLH 偏差 vs NMB
    ax = fig.add_subplot(gs[0, 1])
    for ch in use:
        st = styles[ch]
        s = j[j.chain == ch]
        ax.scatter(s.dPBL, s.nmb, s=26, color=_grey(st['grey']), marker=st['marker'], edgecolor='k', lw=0.4, zorder=3)
    ax.axhline(0, color='0.5', lw=0.7, zorder=1)
    ax.axvline(0, color='0.5', lw=0.7, zorder=1)
    if len(kk) >= 2:
        r_pbl = np.corrcoef(kk.dPBL, kk.nmb)[0, 1]
        y0, y1 = ax.get_ylim()
        ax.set_ylim(y0, y1 + 0.18 * (y1 - y0))
        _corner_text(ax, 'r = %.2f\nn = %d' % (r_pbl, len(kk)))
    ax.set_xlabel('边界层高度相对偏差/%')
    ax.set_ylabel('NMB/%')
    ax.margins(x=0.08)
    panel_tag(ax, '(b)')

    # ---------------- (c) 链条替换效应
    ax = fig.add_subplot(gs[1, 0])
    tot = pd.read_csv(os.path.join(D, 'scores_total.csv')).set_index('chain')
    base_nmb = tot.loc['ERA5_ADP', 'NMB']
    cases = [
        ('WRF→Adapter\n(同一ERA5场)',
         tot.loc['ERA5_ADP', 'NMB'] - tot.loc['CTL_WRF', 'NMB'],
         0.62, ''),
        ('Pangu场\n(替代ERA5)',
         tot.loc['PANGU', 'NMB'] - base_nmb,
         0.32, '//'),
        ('FengWu场\n(替代ERA5)',
         tot.loc['FENGWU', 'NMB'] - base_nmb,
         0.78, 'xx'),
    ]
    vals = [c[1] for c in cases]
    for i, (lab, v, g, h) in enumerate(cases):
        ax.bar(i, v, color=_grey(g), edgecolor='k', lw=0.4,width=0.55, hatch=(h if h else None))
        ax.text(i, v + (3 if v > 0 else -3), '%+.1f' % v,ha='center', va='bottom' if v > 0 else 'top', fontsize=7)
    ax.axhline(0, color='k', lw=0.8)
    ax.set_xticks(range(len(cases)))
    ax.set_xticklabels([c[0] for c in cases], fontsize=10)
    ax.set_ylabel('ΔNMB/%')
    if vals:
        span = max(abs(v) for v in vals) or 5.0
        ax.set_ylim(-1.45 * span, 1.45 * span)
    panel_tag(ax, '(c)')

    # ---------------- (d) 逐日平均偏差
    ax = fig.add_subplot(gs[1, 1])
    mb = m.groupby(['chain', 'day']).apply(
        lambda g: (g.sim - g.obs).mean(), include_groups=False).rename('mb')
    for ch in use:
        st = styles[ch]
        s = mb.loc[ch]
        ax.plot(pd.to_datetime(list(s.index)), s.values,
                color=_grey(st['grey']), marker=st['marker'],
                ms=3, lw=1.1, linestyle='-')
    ax.axhline(0, color='k', lw=0.7)
    ax.set_xlabel('日期')
    ax.set_ylabel('平均偏差/(μg·m⁻³)')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.tick_params(axis='x', labelsize=10, rotation=30)
    panel_tag(ax, '(d)')

    fig.subplots_adjust(left=0.09, right=0.97, top=0.96, bottom=0.26)

    # ---------------- 链条图例（图底部）
    handles = [
        Line2D([0], [0], color=_grey(styles[ch]['grey']),
               marker=styles[ch]['marker'], ms=3.5, lw=1.0,
               linestyle='', label=NAME[ch])
        for ch in use
    ]
    fig.legend(handles=handles, loc='lower center',
               bbox_to_anchor=(0.5, 0.11), ncol=min(n, 5),
               frameon=False, fontsize=10, handlelength=1.6,
               columnspacing=1.2, handletextpad=0.3)

    # ---------------- 图注（不再包含 r、n，只留参照与虚线说明）
    # if note:
    #     note_txt = ('注：相对偏差与 ΔNMB 均以 ERA5_ADP 为参照；'
    #                 '虚线为线性拟合；(a)(b) 中 r 与 n 仅基于非 ERA5_ADP 链条。')
    #     fig.text(0.5, 0.092, note_txt, ha='center', va='top', fontsize=6)

    # # ---------------- 中英文图题
    # if title_cn is None:
    #     title_cn = '图8  各链条相对ERA5-ADP的通风指数、边界层高度偏差与NMB的关系'
    # if title_en is None:
    #     title_en = ('Fig.8  Relationships of ventilation index and PBLH biases '
    #                 'to NMB among chains relative to ERA5-ADP')
    # fig.text(0.5, 0.055, title_cn, ha='center', va='bottom',
    #          fontsize=9, fontweight='bold')
    # fig.text(0.5, 0.022, title_en, ha='center', va='bottom',
    #          fontsize=9, fontweight='bold')

    out = out or os.path.join(FIG, 'fig8_attribution.png')
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
    ap = argparse.ArgumentParser(description='图 8：偏差归因（灰度版）')
    ap.add_argument('--out', default=None, help='输出路径（默认 figures/fig8_attribution.png）')
    ap.add_argument('--dpi', type=int, default=600, help='位图分辨率（默认 600）')
    ap.add_argument('--width', type=float, default=7.2, help='图宽（英寸）')
    ap.add_argument('--title-cn', default=None, help='中文图题')
    ap.add_argument('--title-en', default=None, help='英文图题')
    ap.add_argument('--no-note', action='store_true', help='不显示底部图注')
    args = ap.parse_args(argv)
    kw = {}
    if args.title_cn:
        kw['title_cn'] = args.title_cn
    if args.title_en:
        kw['title_en'] = args.title_en
    fig8(out=args.out, dpi=args.dpi, width=args.width,
         note=not args.no_note, **kw)


if __name__ == '__main__':
    main()