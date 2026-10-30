#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公共绘图设置与数据读取。"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

ROOT = '/home/ubuntu01/sda/AI2MCIP'
PAPER = os.path.join(ROOT, 'paper')
D = os.path.join(PAPER, 'data')
FIG = os.path.join(PAPER, 'figures')
os.makedirs(FIG, exist_ok=True)

# ---- 中文字体
for cand in ['Noto Sans CJK SC', 'Noto Sans CJK JP', 'WenQuanYi Zen Hei', 'AR PL UMing CN']:
    if any(cand in f.name for f in fm.fontManager.ttflist):
        plt.rcParams['font.sans-serif'] = [cand]
        break
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams.update({
    'font.size': 9, 'axes.linewidth': 0.8, 'axes.titlesize': 9.5,
    'xtick.direction': 'in', 'ytick.direction': 'in',
    'xtick.major.size': 3, 'ytick.major.size': 3,
    'savefig.dpi': 300, 'figure.dpi': 120, 'axes.grid': False,
})

CHAINS = ['CTL_WRF', 'ERA5_ADP', 'PANGU', 'FENGWU', 'FENGYUAN']
NAME = {'CTL_WRF': 'CTL: ERA5-WRF', 'ERA5_ADP': 'ERA5-ADP', 'PANGU': 'Pangu',
        'FENGWU': 'FengWu', 'FENGYUAN': 'FengYuan'}
COLOR = {'CTL_WRF': '#4d4d4d', 'ERA5_ADP': '#1f78b4', 'PANGU': '#e31a1c',
         'FENGWU': '#33a02c', 'FENGYUAN': '#ff7f00'}
MARKER = {'CTL_WRF': 'o', 'ERA5_ADP': 's', 'PANGU': '^', 'FENGWU': 'v', 'FENGYUAN': 'D'}

MHOME = {'CTL_WRF': ('ERA5_AQF', 'ERA5_WRF_2025-10-17'),
         'ERA5_ADP': ('ERA5_AQF', 'ERA5_2025-10-17_V7'),
         'PANGU': ('Pangu_AQF', 'ECPGV3_2025-10-26'),
         'FENGWU': ('Fengwu_AQF', 'ECPGV3_2025-10-26'),
         'FENGYUAN': ('Fengyuan_AQF', 'ECPGV3_2025-10-26'),
         'KZ1': ('Pangu_AQF', 'ECPGV3_KZ1'),
         'PBL2': ('Pangu_AQF', 'ECPGV3_PBL2')}


def base(chain):
    a, b = MHOME[chain]
    return os.path.join(ROOT, a, 'MIDDLE_DATA', b)


def load_series():
    return pd.read_csv(os.path.join(D, 'bth_series.csv'), parse_dates=['dt'])


def load_city():
    mod = pd.read_csv(os.path.join(D, 'city_pm25_model.csv'), parse_dates=['time'])
    obs = pd.read_csv(os.path.join(D, 'obs_city_pm25.csv'), parse_dates=['dt'])
    m = mod.rename(columns={'time': 'dt', 'pm25': 'sim'}).merge(
        obs[['dt', 'city', 'pm25_obs']].rename(columns={'pm25_obs': 'obs'}),
        on=['dt', 'city'], how='inner')
    return m.dropna(subset=['sim', 'obs'])


def panel_tag(ax, tag, dx=-0.09, dy=0.025):
    ax.text(dx, 1 + dy, tag, transform=ax.transAxes, fontsize=10,
            fontweight='bold', va='bottom', ha='left')
