#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图 2：模拟域地形、119 个环境空气监测站与 14 个评估城市

独立运行：``python3 fig2_domain.py``（在本目录或其上级目录均可）；也可被导入：

    from fig2_domain import fig2
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
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from figs_common import (ROOT, D, FIG, CHAINS, NAME, COLOR, MARKER, base,
                         load_series, load_city, panel_tag)

PROJ = ccrs.PlateCarree()

def fig2():
    g = nc.Dataset(os.path.join(base('PANGU'), 'mcip/d01/GRIDCRO2D_20251027'))
    hgt = g.variables['HT'][0, 0]
    lat = g.variables['LAT'][0, 0]
    lon = g.variables['LON'][0, 0]
    st = pd.read_csv(os.path.join(D, 'stations.csv'))
    g.close()

    fig = plt.figure(figsize=(6.4, 5.0))
    ax = fig.add_subplot(111, projection=PROJ)
    ax.set_extent([106.5, 122.5, 32.5, 43.5], crs=PROJ)
    im = ax.pcolormesh(lon, lat, hgt, cmap='terrain', vmin=0, vmax=1800,
                       shading='nearest', transform=PROJ, alpha=0.85)
    ax.add_feature(cfeature.COASTLINE, lw=0.6)
    ax.add_feature(cfeature.BORDERS, lw=0.5, ls=':')
    ax.add_feature(cfeature.RIVERS, lw=0.4, edgecolor='#5b8db8')
    cb = fig.colorbar(im, ax=ax, orientation='horizontal', pad=0.06, aspect=38, shrink=0.85)
    cb.set_label('地形高度 (m)', fontsize=8)
    cb.ax.tick_params(labelsize=7)

    cities = st.groupby('city_obs')[['lon', 'lat']].mean()
    ax.scatter(st['lon'], st['lat'], s=9, c='#d7301f', edgecolor='white', lw=0.3,
               transform=PROJ, zorder=5, label='国控/城市站 (n=%d)' % len(st))
    for c, r in cities.iterrows():
        ax.text(r['lon'] + 0.22, r['lat'] + 0.12, c, fontsize=6.8, transform=PROJ, zorder=6)
    gl = ax.gridlines(draw_labels=True, lw=0.3, color='gray', alpha=0.4)
    gl.top_labels = False; gl.right_labels = False
    gl.xlabel_style = {'size': 7}; gl.ylabel_style = {'size': 7}
    ax.legend(loc='lower left', fontsize=7, frameon=True)
    # 内嵌：域格点
    axins = fig.add_axes([0.70, 0.60, 0.18, 0.18])
    axins.pcolormesh(hgt, cmap='terrain', vmin=0, vmax=1800)
    axins.set_xticks([]); axins.set_yticks([])
    axins.set_title('94×94 格点\n27 km', fontsize=6.5)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, 'fig2_domain.png'), bbox_inches='tight')
    plt.close(fig)



if __name__ == '__main__':
    fig2()
