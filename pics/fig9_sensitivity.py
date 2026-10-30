#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图 9（期刊规范版，灰度）：诊断敏感性实验（A1/A2 的 PBLH 与 PM2.5、KZ0UT 对照、指标）

灰度绘图：A1/A2/KZ0UT/观测用“灰度 + 线型 + 标记”区分，阶段阴影用“灰度 + 填充图案”区分。
图例统一置于图底部，不覆盖任何面板。
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
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from figs_common import D, FIG, base, load_series, panel_tag

DAYS = ['20251027', '20251028', '20251029', '20251030', '20251031',
        '20251101', '20251102', '20251103', '20251104']

# 阶段阴影：起、止、灰度、填充图案、标签
PH = [
    ('2025-10-27', '2025-10-29', 0.94, None,    'P1 累积'),
    ('2025-10-29', '2025-10-31', 0.86, '///',   'P2 峰值'),
    ('2025-10-31', '2025-11-03', 0.94, '\\\\\\', 'P3 清除'),
    ('2025-11-03', '2025-11-05', 0.86, 'xxx',   'P4 二次累积'),
]

# 实验样式：灰度 + 线型 + 标记
_STYLE = {
    'A1':  dict(grey=0.40, ls='-',  marker='o', label='A1 默认'),
    'A2':  dict(grey=0.55, ls='--', marker='s', label='A2 仅Rib'),
    'KZ1': dict(grey=0.78, ls='-.', marker='^', label='KZ0UT=1.0'),
    'OBS': dict(grey=0.00, ls='-',  marker=None, label='观测'),
}


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
    plt.rcParams['hatch.linewidth'] = 0.4
    if cn is None:
        print('[警告] 未找到中文字体，中文可能显示为方框；请安装 SimSun/Songti SC。',
              file=sys.stderr)


def _grey(v):
    return plt.cm.Greys(v)


def _shade(ax):
    for a, b, g, h, _ in PH:
        kw = dict(facecolor=str(g), edgecolor='0.55', lw=0,
                  alpha=0.60, zorder=0)
        if h:
            kw['hatch'] = h
        ax.axvspan(pd.Timestamp(a), pd.Timestamp(b), **kw)


def load_sens(chain, tag):
    """读取敏感性实验的城市均值序列（复用 build_dataset 的站点映射）。"""
    import build_dataset as B
    st = pd.read_csv(os.path.join(D, 'stations.csv'))
    rec = []
    for d in DAYS:
        f = os.path.join(base(chain), 'cctm/d01/combine.%s.d01.nc' % d)
        if not os.path.exists(f):
            continue
        ds = nc.Dataset(f)
        pm = ds.variables['PM25_TOT'][:, 0, :, :]
        tf = ds.variables['TFLAG'][:, 0, :]
        times = [B.jdate2dt(tf[i, 0], tf[i, 1]) for i in range(pm.shape[0])]
        v = pm[:, st.row.values, st.col.values]
        for j, t in enumerate(times):
            for c in st.city_obs.unique():
                k = st.city_obs.values == c
                rec.append((tag, t, c, float(np.nanmean(v[j, k]))))
        ds.close()
    return pd.DataFrame(rec, columns=['chain', 'dt', 'city', 'sim'])


def fig9(out=None, dpi=600, width=7.2,
         title_cn=None, title_en=None, note=True):
    """绘制诊断敏感性实验四面板图（灰度版）。

    Parameters
    ----------
    out : str | None
        输出路径；默认 ``figures/fig9_sensitivity.png``。
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
    ser = load_series()

    fig = plt.figure(figsize=(width, 6.0))
    gs = fig.add_gridspec(2, 2, hspace=0.44, wspace=0.30)

    # ---------------- (a) PBLH 日变化 A1 vs A2
    ax = fig.add_subplot(gs[0, 0])
    for key, ch in [('A1', 'PANGU'), ('A2', 'PBL2')]:
        st = _STYLE[key]
        g = os.path.join(base(ch), 'mcip/d01/METCRO2D_20251030')
        if not os.path.exists(g):
            continue
        d = nc.Dataset(g)
        pbl = d.variables['PBL'][:, 0]
        hrs = np.arange(pbl.shape[0])
        ax.plot(hrs, pbl.mean(axis=(1, 2)),
                color=_grey(st['grey']), ls=st['ls'],
                marker=st['marker'], ms=2.4, lw=1.2)
        d.close()

    ax.set_xlabel('时次（UTC）')
    ax.set_ylabel('边界层高度/m')
    ax.set_xlim(0, 23)
    ax.set_xticks(range(0, 24, 6))
    panel_tag(ax, '(a)')

    # ---------------- (b) 两种 PBLH 下 PM2.5 序列
    ax = fig.add_subplot(gs[0, 1])
    _shade(ax)
    st = _STYLE['A1']
    s1 = ser[ser.chain == 'PANGU']
    ax.plot(s1.dt, s1['sim'], color=_grey(st['grey']), ls=st['ls'],
            marker=st['marker'], ms=2.2, markevery=6, lw=1.1)
    try:
        s2 = load_sens('PBL2', 'PBL2').groupby('dt')['sim'].mean()
        st2 = _STYLE['A2']
        ax.plot(s2.index, s2.values, color=_grey(st2['grey']), ls=st2['ls'],
                marker=st2['marker'], ms=2.2, markevery=6, lw=1.1)
    except Exception as e:
        print('PBL2 结果尚未就绪: %s' % e, file=sys.stderr)
    ob = s1[['dt', 'obs']].drop_duplicates('dt')
    ax.plot(ob.dt, ob.obs, color='k', lw=1.5)
    ax.set_xlabel('日期')
    ax.set_ylabel('ρ(PM₂.₅)/(μg·m⁻³)')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.tick_params(axis='x', labelsize=10, rotation=30)
    panel_tag(ax, '(b)')

    # ---------------- (c) Kzmin 对照
    ax = fig.add_subplot(gs[1, 0])
    _shade(ax)
    ax.plot(s1.dt, s1['sim'], color=_grey(_STYLE['A1']['grey']),
            ls=_STYLE['A1']['ls'], marker=_STYLE['A1']['marker'],
            ms=2.2, markevery=6, lw=1.1)
    try:
        s3 = load_sens('KZ1', 'KZ1').groupby('dt')['sim'].mean()
        st3 = _STYLE['KZ1']
        ax.plot(s3.index, s3.values, color=_grey(st3['grey']), ls=st3['ls'],
                marker=st3['marker'], ms=2.2, markevery=6, lw=1.1)
    except Exception as e:
        print('KZ1 结果尚未就绪: %s' % e, file=sys.stderr)
    ax.plot(ob.dt, ob.obs, color='k', lw=1.5)
    ax.set_xlabel('日期')
    ax.set_ylabel('ρ(PM₂.₅)/(μg·m⁻³)')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.tick_params(axis='x', labelsize=10, rotation=30)
    panel_tag(ax, '(c)')

    # ---------------- (d) 指标对比：NMB（柱）与 RMSE（x 轴标签）
    ax = fig.add_subplot(gs[1, 1])
    try:
        df = pd.read_csv(os.path.join(D, 'sens_scores.csv'))
        x = np.arange(len(df))
        bar_specs = [
            (_grey(_STYLE['A1']['grey']), None),
            (_grey(_STYLE['A2']['grey']), '//'),
            (_grey(_STYLE['KZ1']['grey']), 'xx'),
        ]
        for xi, (n, r, (c, h)) in enumerate(zip(df.NMB, df.RMSE, bar_specs)):
            ax.bar(xi, n, 0.5, color=c, edgecolor='k', lw=0.4,
                   hatch=(h if h else None))
        span = max(abs(df.NMB).max(), 5.0)
        for xi, n in enumerate(df.NMB):
            ax.text(xi, n + (0.05 * span if n >= 0 else -0.05 * span),
                    '%+.1f%%' % n, ha='center',
                    va='bottom' if n >= 0 else 'top', fontsize=7)
        ax.axhline(0, color='k', lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels([
            'A1 默认\nRMSE %.1f' % df.RMSE.iloc[0],
            'A2 仅Rib\nRMSE %.1f' % df.RMSE.iloc[1],
            'KZ0UT=1.0\nRMSE %.1f' % df.RMSE.iloc[2],
        ], fontsize=10)
        ax.set_ylabel('NMB/%')
        ax.set_ylim(-1.35 * span, 1.35 * span)
    except Exception as e:
        print('敏感性指标表未就绪: %s' % e, file=sys.stderr)
        ax.text(0.5, 0.5, '敏感性实验运行中', ha='center', va='center',
                transform=ax.transAxes, fontsize=10, color='0.4')
        ax.set_xticks([]); ax.set_yticks([])
    panel_tag(ax, '(d)')

    fig.subplots_adjust(left=0.09, right=0.97, top=0.96, bottom=0.30)

    # ---------------- 图例：第一行（实验），第二行（阶段）
    handles = []
    for key in ['A1', 'A2', 'KZ1', 'OBS']:
        st = _STYLE[key]
        handles.append(Line2D([0], [0], color=_grey(st['grey']),ls=st['ls'], marker=st['marker'],ms=3.2, lw=1.1, label=st['label']))
    fig.legend(handles=handles, loc='lower center',bbox_to_anchor=(0.5, 0.10), ncol=4,frameon=False, fontsize=10, handlelength=2.2,columnspacing=1.4, handletextpad=0.3)

    phase_handles = [
        Patch(facecolor=str(g), edgecolor='0.55', lw=0,hatch=(h if h else None), alpha=0.60, label=lab)
        for _, _, g, h, lab in PH
    ]
    fig.legend(handles=phase_handles, loc='lower center',bbox_to_anchor=(0.5, 0.140), ncol=4,frameon=False, fontsize=10, handlelength=1.6,columnspacing=1.2, handletextpad=0.3)

    # ---------------- 图注
    # if note:
    #     note_txt = ('注：A1 为默认方案（Rib 与对流封顶），A2 仅用 Rib，KZ0UT=1.0 为最小扩散系数对照；'
    #                 '时间为 UTC；(b)(c) 阴影为 P1—P4 阶段；(d) 柱顶为 NMB，横轴标签中标注 RMSE；'
    #                 '敏感性实验未就绪时相应曲线不显示。')
    #     fig.text(0.5, 0.098, note_txt, ha='center', va='top', fontsize=6,
    #              linespacing=1.4)

    # # ---------------- 中英文图题
    # if title_cn is None:
    #     title_cn = '图9  诊断敏感性实验的边界层高度与PM₂.₅模拟效果对比'
    # if title_en is None:
    #     title_en = ('Fig.9  Comparison of PBLH and PM₂.₅ simulation performance '
    #                 'in diagnostic sensitivity experiments')
    # fig.text(0.5, 0.055, title_cn, ha='center', va='bottom',
    #          fontsize=9, fontweight='bold')
    # fig.text(0.5, 0.022, title_en, ha='center', va='bottom',
    #          fontsize=9, fontweight='bold')

    out = out or os.path.join(FIG, 'fig9_sensitivity.png')
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
    ap = argparse.ArgumentParser(description='图 9：诊断敏感性实验（灰度版）')
    ap.add_argument('--out', default=None, help='输出路径（默认 figures/fig9_sensitivity.png）')
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
    fig9(out=args.out, dpi=args.dpi, width=args.width,
         note=not args.no_note, **kw)


if __name__ == '__main__':
    main()