#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图 1：五条模拟链条与 AI-to-MCIP Adapter 架构示意图（纯示意图，无数据依赖）

独立运行：``python3 fig1_framework.py``（在本目录或其上级目录均可）；也可被导入：

    from fig1_framework import fig1
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
from matplotlib import cm
from matplotlib.colors import BoundaryNorm
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from figs_common import (ROOT, D, FIG, CHAINS, NAME, COLOR, MARKER, base,
                         load_series, load_city, panel_tag)

PROJ = ccrs.PlateCarree()

def fig1():
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ax.set_xlim(0, 10.4); ax.set_ylim(0, 6.6); ax.axis('off')

    def box(x, y, w, h, text, fc, fs=8.0, bold=False, ec='#333333'):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.05,rounding_size=0.10',
                                    fc=fc, ec=ec, lw=0.9))
        ax.text(x + w / 2, y + h / 2, text, ha='center', va='center', fontsize=fs,
                fontweight='bold' if bold else 'normal', linespacing=1.35)

    def arrow(x1, y1, x2, y2, ls='-', color='#333333', lw=1.0):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>',
                                     mutation_scale=9, lw=lw, color=color,
                                     linestyle=ls, shrinkA=1, shrinkB=1))

    # 驱动层
    box(0.10, 4.85, 1.75, 1.05, 'ERA5 再分析\n0.25°', '#e8eef7')
    box(0.10, 3.35, 1.75, 0.95, 'Pangu-Weather\n0.25°', '#fbe6e6')
    box(0.10, 2.30, 1.75, 0.85, 'FengWu 0.25°', '#e6f2e6')
    box(0.10, 1.35, 1.75, 0.75, 'FengYuan 0.25°', '#fdf0e0')

    # 传统路径（上层）
    box(2.35, 4.75, 1.70, 1.20, 'WPS + WRF v3.9\n动力降尺度', '#cfd8e8')
    box(4.35, 4.95, 1.15, 0.80, 'wrfout\n(逐时)', '#cfd8e8')
    # 适配器路径（下层）
    box(2.35, 1.35, 1.70, 3.20,
        'AI-to-MCIP Adapter\n\n· 变量契约 (64 变量)\n· 气压层→sigma 插值\n'
        '· 地形与地表处理\n· 诊断补全插槽:\n   PBLH / u* / 通量 /\n   云与辐射', '#d9edf7', fs=7.2)
    box(4.35, 2.05, 1.15, 0.85, 'wrfout-like\n中间场', '#d9edf7')

    # 统一框架
    box(5.95, 2.45, 1.05, 3.30, 'MCIP\n\n→ METCRO\n2D / 3D\n→ GRIDCRO', '#f2f2f2', fs=7.6)
    box(7.35, 2.45, 1.05, 3.30, 'CMAQ v5.2\nCCTM\n\nACM2\nAERO6', '#f2f2f2', fs=7.6)
    box(8.75, 4.25, 1.55, 1.00, 'PM$_{2.5}$ 浓度场\n(逐时, 27 km)', '#fff2cc')
    box(8.75, 2.95, 1.55, 0.95, 'PM$_{2.5}$ / 气象\n观测', '#fff2cc')
    box(6.15, 0.75, 4.15, 0.80, '偏差归因：气象场来源 × 诊断路径', '#ffe6cc', fs=8.2)

    # 箭头
    arrow(1.85, 5.35, 2.35, 5.35)                  # ERA5 → WRF
    arrow(1.85, 4.95, 2.35, 3.20, ls=':')          # ERA5 → Adapter（虚线，同一场替换）
    arrow(1.85, 3.82, 2.35, 3.60)
    arrow(1.85, 2.72, 2.35, 2.60, ls=':')
    arrow(1.85, 1.72, 2.35, 1.90, ls=':')
    arrow(4.05, 5.35, 4.35, 5.35)                  # WRF → wrfout
    arrow(4.05, 2.47, 4.35, 2.47)                  # Adapter → wrfout-like
    arrow(5.50, 5.35, 5.95, 5.05)                  # wrfout → MCIP
    arrow(5.50, 2.47, 5.95, 2.90)                  # wrfout-like → MCIP
    arrow(7.00, 4.10, 7.35, 4.10)                  # MCIP → CCTM
    arrow(8.40, 4.40, 8.75, 4.60)                  # CCTM → 浓度场
    arrow(8.75, 3.55, 8.40, 3.30)                  # 观测 → CCTM（虚线反馈）
    arrow(8.10, 2.45, 8.20, 1.55, ls='--')
    arrow(9.30, 2.95, 8.95, 1.55, ls='--')

    ax.text(0.10, 6.20, '(a) 大尺度驱动', fontsize=8.5, color='#555555')
    ax.text(2.35, 6.20, '(b) 区域化路径', fontsize=8.5, color='#555555')
    ax.text(5.95, 6.20, '(c) 统一化学传输框架与归因', fontsize=8.5, color='#555555')
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'fig1_framework.png'), bbox_inches='tight')
    plt.close(fig)



if __name__ == '__main__':
    fig1()
