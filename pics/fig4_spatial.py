#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图 4（独立脚本，期刊规范版）：PM2.5 空间分布与同期城市观测

每个面板 = 一条链条在指定时刻的第一层 PM2.5 场；
圆点 = 同期城市观测均值（可选）；虚线 = 200 / 800 m 地形等高线；
叠加 /home/ubuntu01/sda/AI2MCIP/paper/china_shp/china.shp 作为国界/省界底图。

用法
----
    python3 pics/fig4_spatial.py
    python3 pics/fig4_spatial.py --date 20251031 --hour 0
    python3 pics/fig4_spatial.py --chains PANGU FENGWU
    python3 pics/fig4_spatial.py --chains CTL_WRF ERA5_ADP PANGU FENGWU FENGYUAN
    python3 pics/fig4_spatial.py --no-obs --out figures/fig4.pdf --dpi 600
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))          # scripts/（figs_common 所在）

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
from cartopy.feature import ShapelyFeature
import netCDF4 as nc
import numpy as np
import pandas as pd

from figs_common import D, FIG, CHAINS, NAME, base, panel_tag

PROJ = ccrs.PlateCarree()

SHP_PATH = '/home/ubuntu01/sda/AI2MCIP/paper/china_shp/china.shp'

# 默认色阶（μg m-3）
DEFAULT_LEVELS = [5, 15, 25, 35, 50, 75, 100, 125, 150, 175, 200, 250]
DEFAULT_EXTENT = (109.5, 121.5, 33.5, 42.8)   # lon_min, lon_max, lat_min, lat_max

CN_NAME = {'CTL_WRF': 'CTL: ERA5→WRF', 'ERA5_ADP': 'ERA5→Adapter',
           'PANGU': 'Pangu-Weather', 'FENGWU': 'FengWu', 'FENGYUAN': 'FengYuan'}

# 色标标目：量的名称/单位符号（期刊“量/单位”斜线格式）
_CB_LABEL = 'PM₂.₅质量浓度/(μg·m⁻³)'

_CHINA_FEATURE = None


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


def _china_feature():
    """读取中国国界/省界 shp；自动判断经纬度或 Albers 投影。"""
    global _CHINA_FEATURE
    if _CHINA_FEATURE is not None:
        return _CHINA_FEATURE
    try:
        reader = shpreader.Reader(SHP_PATH)
        geoms = list(reader.geometries())
        if not geoms:
            return None
        b = geoms[0].bounds
        if -180 <= b[0] <= 180 and -90 <= b[1] <= 90:
            src = PROJ
        else:
            # 中国常用 Albers：中央经线 105°，标准纬线 25°/47°
            src = ccrs.AlbersEqualArea(central_longitude=105, central_latitude=0,standard_parallels=(25, 47))
        _CHINA_FEATURE = ShapelyFeature(geoms, src, facecolor='none',edgecolor='k', linewidth=0.55)
        return _CHINA_FEATURE
    except Exception as e:
        print('[警告] 无法读取 %s：%s' % (SHP_PATH, e), file=sys.stderr)
        return None


def _load_field(chain, when, hour):
    """读取某链条某日 combine 文件的指定 UTC 时次，返回 (field2d | None, 说明)。"""
    f = os.path.join(base(chain), 'cctm/d01/combine.%s.d01.nc' % when)
    if not os.path.exists(f):
        return None, '缺少 %s' % os.path.basename(f)
    jd = int(dt.datetime.strptime(when, '%Y%m%d').strftime('%Y%j'))
    key = jd * 100 + int(hour)
    d = nc.Dataset(f)
    try:
        tf = d.variables['TFLAG'][:, 0, :]
        imap = {int(r[0]) * 100 + int(r[1]) // 10000: i for i, r in enumerate(tf)}
        if key not in imap:
            return None, '该文件无 %02d UTC 时次' % hour
        return d.variables['PM25_TOT'][imap[key], 0, :, :], ''
    finally:
        d.close()


def _load_obs(when, hour):
    """城市观测均值，返回 DataFrame(lon, lat, pm25_obs) 或 None。"""
    f = os.path.join(D, 'obs_city_pm25.csv')
    if not os.path.exists(f):
        return None
    obs = pd.read_csv(f, parse_dates=['dt'])
    t = pd.Timestamp('%s-%s-%s %02d:00' % (when[:4], when[4:6], when[6:], int(hour)))
    ot = obs[obs.dt == t]
    if ot.empty:
        return None
    st = pd.read_csv(os.path.join(D, 'stations.csv'))
    c = ot.groupby('city')['pm25_obs'].mean().reset_index()
    c = c.merge(st.groupby('city_obs')[['lon', 'lat']].mean().reset_index(),
                left_on='city', right_on='city_obs')
    return c[['lon', 'lat', 'pm25_obs']]


def _load_terrain():
    """地形与经纬度（取任一链条的 GRIDCRO2D）。"""
    for ch in CHAINS:
        p = os.path.join(base(ch), 'mcip/d01/GRIDCRO2D_20251027')
        if os.path.exists(p):
            g = nc.Dataset(p)
            lat = g.variables['LAT'][0, 0]
            lon = g.variables['LON'][0, 0]
            hgt = g.variables['HT'][0, 0]
            g.close()
            return lat, lon, hgt
    raise SystemExit('找不到 GRIDCRO2D，请先运行 MCIP。')


def _add_lonlat_ticks(ax, extent, show_x=True, show_y=True):
    """稀疏经纬度刻度：下排显示经度标签、左列显示纬度标签。"""
    lon0, lon1, lat0, lat1 = extent
    xticks = np.arange(np.ceil(lon0 / 4) * 4, lon1 + 0.1, 4)
    yticks = np.arange(np.ceil(lat0 / 4) * 4, lat1 + 0.1, 4)
    try:
        ax.set_xticks(xticks, crs=PROJ)
        ax.set_yticks(yticks, crs=PROJ)
    except TypeError:
        ax.set_xticks(xticks)
        ax.set_yticks(yticks)
    ax.set_xticklabels(['%g°E' % x for x in xticks] if show_x else [])
    ax.set_yticklabels(['%g°N' % y for y in yticks] if show_y else [])
    ax.tick_params(labelsize=10, length=2, pad=1)


def fig4(chains=None, when='20251030', hour=12, out=None, show_obs=True,
         dpi=600, width=7.4, levels=None, extent=None, title_note=False,
         title_cn=None, title_en=None):
    """绘制 PM2.5 空间分布多面板图（期刊规范版）。

    Parameters
    ----------
    chains : sequence of str | None
        链条名（CTL_WRF / ERA5_ADP / PANGU / FENGWU / FENGYUAN），默认前 4 条。
    when : str
        日期，YYYYMMDD（UTC）。
    hour : int
        UTC 时次（0—23）。
    show_obs : bool
        是否叠加同期城市观测圆点。
    levels : list | None
        色阶边界，默认 5…250 μg m⁻³。
    extent : tuple | None
        (lon_min, lon_max, lat_min, lat_max)。
    title_note : bool
        是否显示底部图注。
    title_cn, title_en : str | None
        中英文图题；None 时按日期自动生成。
    """
    _setup_style()

    chains = list(chains) if chains else list(CHAINS[:4])
    bad = [c for c in chains if c not in CHAINS]
    if bad:
        raise SystemExit('未知链条：%s（可选 %s）' % ('、'.join(bad), '、'.join(CHAINS)))
    levels = list(levels) if levels else list(DEFAULT_LEVELS)
    extent = tuple(extent) if extent else DEFAULT_EXTENT

    lat, lon, hgt = _load_terrain()
    obs = _load_obs(when, hour) if show_obs else None
    china = _china_feature()

    n = len(chains)
    ncol = 2 if n <= 4 else 3
    nrow = int(np.ceil(n / ncol))
    height = 0.78 * width * nrow / max(ncol, 1) + 1.35
    fig = plt.figure(figsize=(width, height))

    # cmap = plt.get_cmap('YlOrRd', len(levels) - 1)
    cmap = plt.get_cmap('Greys', len(levels) - 1)
    norm = BoundaryNorm(levels, cmap.N)

    for i, ch in enumerate(chains):
        ax = fig.add_subplot(nrow, ncol, i + 1, projection=PROJ)
        ax.set_extent(list(extent), crs=PROJ)
        ax.add_feature(cfeature.COASTLINE, lw=0.4)
        field, msg = _load_field(ch, when, hour)
        if field is not None:
            ax.pcolormesh(lon, lat, field, cmap=cmap, norm=norm, shading='nearest',transform=PROJ)
        else:
            ax.text(0.5, 0.5, '无数据\n%s' % msg, transform=ax.transAxes, ha='center', va='center', fontsize=10, color='#888888')
        # ax.contour(lon, lat, hgt, levels=[200, 800], colors='#666666',
        #            linewidths=0.4, linestyles='--', transform=PROJ)
        if china is not None:
            ax.add_feature(china, zorder=4)
        if obs is not None:
            ax.scatter(obs.lon, obs.lat, c=obs.pm25_obs, cmap=cmap, norm=norm, s=16,edgecolor='k', linewidths=0.3, transform=PROJ, zorder=5)

        ax.set_title(NAME.get(ch, CN_NAME.get(ch, ch)), fontsize=10)
        row, col = divmod(i, ncol)
        _add_lonlat_ticks(ax, extent,
                          show_x=(row == nrow - 1),
                          show_y=(col == 0))
        panel_tag(ax, '(%s)' % 'abcdefgh'[i], dx=0.02, dy=0.01)

    # ---------------- 色标
    cax = fig.add_axes([0.25, 0.11, 0.5, 0.02])
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax,orientation='horizontal', extend='max')
    cb.set_label(_CB_LABEL, fontsize=10)
    cb.ax.tick_params(labelsize=10)

    # ---------------- 图注（含地图审图号占位）
    tstr = '%s-%s-%s %02d:00 UTC' % (when[:4], when[4:6], when[6:], int(hour))
    if title_note:
        note = ('色块：模式第一层 PM₂.₅ 浓度；圆点：同期城市观测均值；虚线：200/800 m 地形等高线；'
                '经纬度为东经、北纬，单位（°）。\n'
                '底图：中国标准地图（%s）；地图审图号：GS(20XX)XXXX号（请替换为实际审图号）。'
                % tstr)
        fig.text(0.5, 0.098, note, ha='center', va='top', fontsize=6, linespacing=1.4)

    # ---------------- 中英文图题（置于图下方）
    # if title_cn is None:
    #     title_cn = '图4  京津冀及周边地区PM₂.₅质量浓度空间分布（%s）' % tstr
    # if title_en is None:
    #     title_en = ('Fig.4  Spatial distribution of PM₂.₅ mass concentration in '
    #                 'Beijing-Tianjin-Hebei and surrounding areas (%s)' % tstr)
    # fig.text(0.5, 0.060, title_cn, ha='center', va='bottom',fontsize=9, fontweight='bold')
    # fig.text(0.5, 0.028, title_en, ha='center', va='bottom',fontsize=9, fontweight='bold')

    fig.subplots_adjust(left=0.035, right=0.975, top=0.95, bottom=0.165,wspace=0.04, hspace=0.08)
    out = out or os.path.join(FIG, 'fig4_spatial.png')
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
    ap = argparse.ArgumentParser(description='图 4：PM2.5 空间分布多面板图（期刊规范版）')
    ap.add_argument('--date', default='20251030', help='日期 YYYYMMDD（UTC），默认 20251030')
    ap.add_argument('--hour', type=int, default=12, help='UTC 时次 0—23，默认 12')
    ap.add_argument('--chains', nargs='+', default=list(CHAINS[:4]),
                    help='链条列表，默认 CTL_WRF ERA5_ADP PANGU FENGWU')
    ap.add_argument('--out', default=None, help='输出路径（默认 figures/fig4_spatial.png）')
    ap.add_argument('--no-obs', action='store_true', help='不叠加观测圆点')
    ap.add_argument('--width', type=float, default=7.4, help='图宽（英寸）')
    ap.add_argument('--dpi', type=int, default=600, help='位图分辨率（默认 600）')
    ap.add_argument('--levels', nargs='+', type=float, default=None,
                    help='自定义色阶边界（μg m-3）')
    ap.add_argument('--extent', nargs=4, type=float, default=None,
                    metavar=('LON0', 'LON1', 'LAT0', 'LAT1'), help='显示范围')
    ap.add_argument('--title-cn', default=None, help='中文图题')
    ap.add_argument('--title-en', default=None, help='英文图题')
    args = ap.parse_args(argv)
    kw = {}
    if args.title_cn:
        kw['title_cn'] = args.title_cn
    if args.title_en:
        kw['title_en'] = args.title_en
    fig4(chains=args.chains, when=args.date, hour=args.hour, out=args.out,
         show_obs=not args.no_obs, dpi=args.dpi, width=args.width,
         levels=args.levels, extent=args.extent, **kw)


if __name__ == '__main__':
    main()