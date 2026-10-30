#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 pangu2wrf（AI-to-MCIP Adapter）技术文档的流程示意图。

输出： figures/fig_tech_pipeline.png
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))          # scripts/（figs_common 所在）

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

from figs_common import FIG

plt.rcParams['font.sans-serif'] = plt.rcParams['font.sans-serif']
plt.rcParams['axes.unicode_minus'] = False


def box(ax, x, y, w, h, text, fc, fs=7.6, ec='#333333', bold=False, ha='center'):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.04,rounding_size=0.06',
                                fc=fc, ec=ec, lw=0.9))
    ax.text(x + w / 2 if ha == 'center' else x + 0.06, y + h / 2, text,
            ha=ha, va='center', fontsize=fs, linespacing=1.35,
            fontweight='bold' if bold else 'normal')


def arrow(ax, x1, y1, x2, y2, ls='-', color='#333333', lw=1.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>',
                                 mutation_scale=9, lw=lw, color=color, linestyle=ls,
                                 shrinkA=1, shrinkB=1))


def main():
    fig, ax = plt.subplots(figsize=(7.4, 4.3))
    ax.set_xlim(0, 10.3)
    ax.set_ylim(0, 7.4)
    ax.axis('off')

    def title(x, t):
        ax.text(x, 7.05, t, fontsize=7.8, color='#555555')

    # ---------------- 列标题
    title(0.10, '(a) 输入契约')
    title(2.35, '(b) 网格与插值')
    title(4.35, '(c) 逐时次三阶段')
    title(6.60, '(d) 输出与下游')

    # ---------------- (a) 输入
    box(ax, 0.10, 5.45, 1.95, 1.05, 'surface_%03d.npy\n(4, 721, 1440)\nmsl, u10, v10, t2m', '#e8eef7', fs=7.0)
    box(ax, 0.10, 4.30, 1.95, 1.05, 'upper_%03d.npy\n(5, 13, 721, 1440)\nz, q, t, u, v', '#e8eef7', fs=7.0)
    box(ax, 0.10, 3.15, 1.95, 1.05, '模板 wrfout\n99×99×34\nZNW/P_TOP/HGT', '#eef0e8', fs=7.0)

    # ---------------- (b) 网格
    box(ax, 2.35, 3.15, 1.65, 3.35,
        'GridTemplate\n投影 / 土地利用\nMAPFAC / F\nSINALPHA\n\n'
        'BilinearMapper\n0.25° → 99×99\n窗口裁剪', '#f2f2f2', fs=6.8)

    # ---------------- (c) 三阶段
    box(ax, 4.35, 5.40, 1.90, 1.10,
        '阶段 A  convert_hour_core\nPSFC / eta / 垂直插值\n云 / 辐射 / 通量 / TSK', '#d9edf7', fs=6.8)
    box(ax, 4.35, 4.20, 1.90, 0.90,
        '阶段 B  advance_carry\nRAINC/RAINNC、PBL 加热\n夜间 dθ 松弛', '#e6f2e6', fs=6.8)
    box(ax, 4.35, 3.00, 1.90, 0.90,
        '阶段 C  convert_hour_tail\nW / PBLH / 降水累积\n组装 64 个字段', '#fdf0e0', fs=6.8)

    # ---------------- (d) 输出
    box(ax, 6.60, 3.95, 1.45, 2.05,
        '伪 wrfout\nNETCDF3_64BIT\n\n64 变量\n~22 MB/时次', '#fff2cc', fs=7.0)
    box(ax, 8.40, 5.00, 1.75, 0.85, 'MCIP V4.4\n→ METCRO 2D/3D', '#f2f2f2', fs=7.0)
    box(ax, 8.40, 3.75, 1.75, 0.85, 'CMAQ CCTM\n(V5.2)', '#f2f2f2', fs=6.8)

    # ---------------- 箭头
    arrow(ax, 2.05, 5.95, 2.35, 5.60)
    arrow(ax, 2.05, 4.82, 2.35, 4.75)
    arrow(ax, 2.05, 3.67, 2.35, 3.95, ls=':')
    arrow(ax, 4.00, 5.45, 4.35, 5.95)
    arrow(ax, 4.00, 4.60, 4.35, 4.65)
    arrow(ax, 5.30, 5.40, 5.30, 5.12)
    arrow(ax, 5.30, 4.20, 5.30, 3.92)
    arrow(ax, 6.25, 3.45, 6.60, 4.20)
    arrow(ax, 8.05, 5.35, 8.40, 5.35)
    arrow(ax, 9.27, 5.00, 9.27, 4.62)
    # 循环标注
    ax.annotate('', xy=(4.35, 6.62), xytext=(6.05, 6.62),
                arrowprops=dict(arrowstyle='-|>', color='#888888', lw=0.9))
    ax.text(5.20, 6.70, 'n = 1 … N', ha='center', fontsize=6.8, color='#666666')

    # ---------------- 脚注
    ax.text(0.10, 2.55,
            '阶段 A 只依赖当前时次（可并行）；阶段 B 仅对 (ny,nx) 数组做乘加（串行，开销可忽略）；\n'
            '阶段 C 依赖 A+B 的结果（可并行）。三个跨时次累加器：RAINC/RAINNC、pbl_acc（∫HFX/ρcp dt）、\n'
            'dtheta_acc（夜间等效地表位温亏损）。',
            fontsize=6.7, va='top', color='#333333', linespacing=1.65)
    ax.text(0.10, 1.45,
            '输出 99×99 为 WRF 域（e_we = 100），MCIP 切除边界后为 94×94（ncols = e_we − 6）；\n'
            '时间轴由 Times 变量逐时次给出（UTC，YYYY-MM-DD_HH:MM:SS）。',
            fontsize=6.7, va='top', color='#333333', linespacing=1.65)

    out = os.path.join(FIG, 'fig_tech_pipeline.png')
    fig.savefig(out, bbox_inches='tight', dpi=300)
    plt.close(fig)
    print('saved: %s' % out)


if __name__ == '__main__':
    main()
