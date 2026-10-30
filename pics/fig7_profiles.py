#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图 7（期刊规范版，灰度）：峰值日 14 城市平均垂直廓线（位温、相对湿度、PM2.5）

灰度绘图：链条用“灰度 + 线型 + 稀疏标记”三重区分，黑白打印可辨。
三个面板共享高度量纲，仅 (a) 标注纵轴标目。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))          # scripts/（figs_common 所在）

import numpy as np
import pandas as pd
import netCDF4 as nc
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from figs_common import D, FIG, CHAINS, NAME, base, panel_tag

# 链条样式：灰度 + 线型 + 标记（黑白可辨）
_GREYS = [0.15, 0.32, 0.48, 0.64, 0.78]
_LS = ['-', '--', '-.', ':', (0, (3, 1, 1, 1))]
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
    plt.rcParams['font.size'] = 12
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
    return plt.cm.Greys(v)


def _compute_profiles(day):
    """读取并计算 14 城市平均垂直廓线（原脚本逻辑，未改动）。"""
    st = pd.read_csv(os.path.join(D, 'stations.csv'))
    idx = st.groupby('city_obs').indices
    prof = {}
    for ch in CHAINS[:5]:
        g = os.path.join(base(ch), 'mcip/d01/METCRO3D_%s' % day)
        d = nc.Dataset(g)
        zf = d.variables['ZF'][:, :, :, :].mean(axis=(2, 3))
        ta = d.variables['TA'][:, :, :, :]
        pres = d.variables['PRES'][:, :, :, :]
        qv = d.variables['QV'][:, :, :, :]

        def cmean(a):
            arr = a[:, :, st.row.values, st.col.values]           # (T,L,Nst)
            out = np.stack([arr[:, :, i].mean(axis=-1) for i in idx.values()], axis=0)
            return out.mean(axis=0)                               # (T,L)

        theta = cmean(ta) * (100000.0 / cmean(pres)) ** 0.286
        q = cmean(qv)
        e = q * cmean(pres) / (0.622 + q)
        es = 611.2 * np.exp(17.67 * (cmean(ta) - 273.15) / (cmean(ta) - 29.65))
        rh = np.clip(100 * e / es, 0, 100)
        d.close()

        pm = None
        cf = os.path.join(base(ch), 'cctm/d01/CCTM_CGRID_v52_gcc_%s_%s.nc' %
                          (os.path.basename(base(ch)), day))
        if os.path.exists(cf):
            a = nc.Dataset(cf)
            names = [v for v in a.variables
                     if v[:1] == 'A' and a.variables[v].units.strip() == 'micrograms/m**3']
            tot = sum(a.variables[v][0, :, :, :] for v in names)     # (L, R, C)
            pm_city = [tot[:, st.row.values[i], st.col.values[i]].mean(axis=-1)
                       for i in idx.values()]
            pm = np.mean(np.stack(pm_city, axis=0), axis=0)          # (L,)
            a.close()

        prof[ch] = dict(z=zf.mean(axis=0), theta=theta.mean(axis=0),
                        rh=rh.mean(axis=0), pm=pm)
    return prof


def fig7(day='20251030', out=None, dpi=600, width=7.2,
         title_cn=None, title_en=None, note=True):
    """绘制峰值日 14 城市平均垂直廓线（灰度版）。

    Parameters
    ----------
    day : str
        日期，YYYYMMDD（UTC）。
    out : str | None
        输出路径；默认 ``figures/fig7_profiles.png``。
    dpi : int
        位图分辨率；矢量格式（pdf/eps/svg）忽略。
    width : float
        图宽（英寸）。
    title_cn, title_en : str | None
        中英文图题；None 时按日期自动生成。
    note : bool
        是否显示底部图注。
    """
    _setup_style()

    prof = _compute_profiles(day)
    use = list(prof.keys())
    n = len(use)

    styles = {}
    for i, ch in enumerate(use):
        styles[ch] = dict(grey=_GREYS[i % len(_GREYS)],
                          ls=_LS[i % len(_LS)],
                          marker=_MARKERS[i % len(_MARKERS)])

    fig = plt.figure(figsize=(width, 4.8))
    gs = fig.add_gridspec(1, 3, wspace=0.28)

    # ---------------- (a) 位温
    ax = fig.add_subplot(gs[0])
    for ch in use:
        st = styles[ch]
        ax.plot(prof[ch]['theta'], prof[ch]['z'],color=_grey(st['grey']), linestyle=st['ls'],marker=st['marker'], ms=2.4, markevery=8, lw=1.0)
    ax.set_xlabel('位温/K')
    ax.set_ylabel('高度/m')
    ax.set_ylim(0, 1500)
    # 位温范围按数据自动确定，避免硬编码截断
    all_theta = np.concatenate([prof[ch]['theta'] for ch in use])
    ax.set_xlim(np.floor(all_theta.min()) - 0.5, np.ceil(all_theta.max()) + 0.5)
    panel_tag(ax, '(a)')

    # ---------------- (b) 相对湿度
    ax = fig.add_subplot(gs[1])
    for ch in use:
        st = styles[ch]
        ax.plot(prof[ch]['rh'], prof[ch]['z'],color=_grey(st['grey']), linestyle=st['ls'],marker=st['marker'], ms=2.4, markevery=8, lw=1.0)
    ax.set_xlabel('相对湿度/%')
    ax.set_ylim(0, 1500)
    ax.tick_params(labelleft=False)          # 共享高度量纲，仅 (a) 标注
    panel_tag(ax, '(b)')

    # ---------------- (c) PM2.5
    ax = fig.add_subplot(gs[2])
    for ch in use:
        st = styles[ch]
        if prof[ch]['pm'] is None:
            continue
        ax.plot(prof[ch]['pm'], prof[ch]['z'],color=_grey(st['grey']), linestyle=st['ls'],marker=st['marker'], ms=2.4, markevery=8, lw=1.0)
    ax.set_xlabel('ρ(PM₂.₅)/(μg·m⁻³)')
    ax.set_ylim(0, 1500)
    ax.set_xlim(left=0)
    ax.tick_params(labelleft=False)
    panel_tag(ax, '(c)')

    fig.subplots_adjust(left=0.09, right=0.98, top=0.96, bottom=0.26)

    # ---------------- 链条图例（图底部横排）
    handles = [
        Line2D([0], [0], color=_grey(styles[ch]['grey']),
               linestyle=styles[ch]['ls'], marker=styles[ch]['marker'],
               ms=3, lw=1.0, label=NAME[ch])
        for ch in use
    ]
    fig.legend(handles=handles, loc='lower center',
               bbox_to_anchor=(0.5, 0.10), ncol=min(n, 5),
               frameon=False, fontsize=10, handlelength=2.4,
               columnspacing=1.2, handletextpad=0.3)

    # ---------------- 图注
    tstr = '%s-%s-%s' % (day[:4], day[4:6], day[6:])
    if note:
        note_txt = ('注：位温与相对湿度为时段平均，PM₂.₅为 CCTM_CGRID 首时次；高度为模式层高度；各要素均为 14 城市平均。')
        fig.text(0.5, 0.092, note_txt, ha='center', va='top', fontsize=6)

    # ---------------- 中英文图题
    # if title_cn is None:
    #     title_cn = '图7  峰值日14城市平均垂直廓线（%s）' % tstr
    # if title_en is None:
    #     title_en = ('Fig.7  Mean vertical profiles of 14 cities on the peak '
    #                 'day (%s)' % tstr)
    # fig.text(0.5, 0.055, title_cn, ha='center', va='bottom',fontsize=12, fontweight='bold')
    # fig.text(0.5, 0.022, title_en, ha='center', va='bottom',fontsize=12, fontweight='bold')

    out = out or os.path.join(FIG, 'fig7_profiles.png')
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
    ap = argparse.ArgumentParser(description='图 7：峰值日 14 城市平均垂直廓线（灰度版）')
    ap.add_argument('--day', default='20251030', help='日期 YYYYMMDD（UTC）')
    ap.add_argument('--out', default=None, help='输出路径（默认 figures/fig7_profiles.png）')
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
    fig7(day=args.day, out=args.out, dpi=args.dpi, width=args.width,
         note=not args.no_note, **kw)


if __name__ == '__main__':
    main()