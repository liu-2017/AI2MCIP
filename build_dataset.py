#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建统一分析与对比数据集（5 条链条 x 2025-10-27..11-04）

链条：
  CTL_WRF  : ERA5 -> WPS/WRF v3.9 -> MCIP -> CMAQ          （传统基准链）
  ERA5_ADP : ERA5 -> AI-to-MCIP Adapter -> MCIP -> CMAQ    （同一大尺度场，仅换诊断路径）
  PANGU    : Pangu-Weather -> Adapter -> MCIP -> CMAQ
  FENGWU   : FengWu -> Adapter -> MCIP -> CMAQ
  FENGYUAN : FengYuan -> Adapter -> MCIP -> CMAQ

输出：
  data/station_pm25.csv    站点逐小时 PM2.5（模型）
  data/city_series.csv     城市逐小时 PM2.5（模型 vs 国控城市均值）
  data/met_city.csv        城市逐小时气象诊断量（MCIP METCRO2D）
  data/profiles.npz        城市平均垂直廓线（METCRO3D）
"""
import os, sys, glob
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import netCDF4 as nc
from pyproj import Proj

ROOT = '/home/ubuntu01/sda/AI2MCIP'
OUT = os.path.join(ROOT, 'paper', 'data')
os.makedirs(OUT, exist_ok=True)

CHAINS = {
    'CTL_WRF':  dict(dom='ERA5_WRF_2025-10-17'),
    'ERA5_ADP': dict(dom='ERA5_2025-10-17_V7'),
    'PANGU':    dict(dom='ECPGV3_2025-10-26'),
    'FENGWU':   dict(dom='ECPGV3_2025-10-26'),
    'FENGYUAN': dict(dom='ECPGV3_2025-10-26'),
}
BASEDIR = {
    'CTL_WRF':  'ERA5_AQF',
    'ERA5_ADP': 'ERA5_AQF',
    'PANGU':    'Pangu_AQF',
    'FENGWU':   'Fengwu_AQF',
    'FENGYUAN': 'Fengyuan_AQF',
}
DAYS = ['20251027', '20251028', '20251029', '20251030', '20251031',
        '20251101', '20251102', '20251103', '20251104']

MET2D_VARS = ['PRSFC', 'USTAR', 'WSTAR', 'PBL', 'MOLI', 'HFX', 'LH', 'TEMPG',
              'TEMP2', 'Q2', 'WSPD10', 'WDIR10', 'GLW', 'GSW', 'RGRND', 'RN',
              'RC', 'CFRAC', 'CLDT', 'WBAR']


# ---------------------------------------------------------------- helpers
def jdate2dt(jd, hhmmss):
    s = str(int(hhmmss)).zfill(6)
    d = datetime.strptime(str(int(jd)), '%Y%j')
    return d + timedelta(hours=int(s[:2]))


def station_table():
    st = pd.read_excel(os.path.join(
        ROOT, 'Pangu_AQF/run_scripts/OUT_CITY/run_scripts/CMAQ/BTH.xls'))
    st = st.rename(columns={'lng': 'lon', 'lat': 'lat'})
    # 观测列名为“北京/石家庄/雄安新区”，站点表为“北京市/石家庄市/雄安新区”
    st['city_obs'] = [c[:-1] if c.endswith('市') else c for c in st['city']]
    return st


def grid_proj(inn_file):
    ds = nc.Dataset(inn_file)
    p = Proj(proj='lcc +a=6370000 +b=6370000 +lon_0={} +lat_0={} +lat_1={} +lat_2={}'
             .format(float(ds.XCENT), float(ds.YCENT), float(ds.P_ALP), float(ds.P_BET)))
    info = dict(xorig=float(ds.XORIG), yorig=float(ds.YORIG),
                xcell=float(ds.XCELL), ycell=float(ds.YCELL),
                ncols=int(ds.NCOLS), nrows=int(ds.NROWS))
    ds.close()
    return p, info


def lonlat2cr(p, info, lons, lats):
    x, y = p(np.asarray(lons), np.asarray(lats))
    cols = np.floor((x - info['xorig']) / info['xcell']).astype(int)
    rows = np.floor((y - info['yorig']) / info['ycell']).astype(int)
    ok = (cols >= 0) & (cols < info['ncols']) & (rows >= 0) & (rows < info['nrows'])
    return cols, rows, ok


# ---------------------------------------------------------------- main
def main():
    st = station_table()
    cctm0 = os.path.join(ROOT, BASEDIR['PANGU'], 'MIDDLE_DATA', CHAINS['PANGU']['dom'],
                         'cctm/d01', 'combine.20251027.d01.nc')
    p, info = grid_proj(cctm0)
    cols, rows, ok = lonlat2cr(p, info, st['lon'].values, st['lat'].values)
    st = st.assign(col=cols, row=rows, in_dom=ok)
    st = st[st.in_dom].reset_index(drop=True)
    st.to_csv(os.path.join(OUT, 'stations.csv'), index=False, encoding='utf-8-sig')
    print('stations in domain:', len(st), 'cities:', st.city.nunique())

    # 城市 -> 站点索引
    city_station_idx = {c: g.index.values for c, g in st.groupby('city_obs')}

    # ---- 观测（城市均值，逐小时，北京时间）
    obs_frames = []
    for d in DAYS:
        f = os.path.join(ROOT, 'Pangu_AQF/run_scripts/OUT_CITY/data_base/城市2025',
                         'china_cities_%s.csv' % d)
        if not os.path.exists(f):
            print('  missing obs', f); continue
        df = pd.read_csv(f)
        pm = df[df.type == 'PM2.5'].copy()
        pm['dt'] = pd.to_datetime(pm['date'].astype(str) + pm['hour'].astype(str).str.zfill(2),
                                  format='%Y%m%d%H')
        obs_frames.append(pm)
    obs = pd.concat(obs_frames)
    keep = [c for c in obs.columns if c in set(st['city_obs'])]
    obs_long = obs.melt(id_vars=['dt', 'date', 'hour'], value_vars=keep,
                        var_name='city', value_name='pm25_obs')
    obs_long = obs_long.dropna(subset=['pm25_obs'])
    obs_long.to_csv(os.path.join(OUT, 'obs_city_pm25.csv'), index=False, encoding='utf-8-sig')

    # ---- 逐链条读取
    station_rec = []
    met_rec = []
    prof_store = {}

    for chain, cfg in CHAINS.items():
        base = os.path.join(ROOT, BASEDIR[chain], 'MIDDLE_DATA', cfg['dom'])
        cdir = os.path.join(base, 'cctm/d01')
        mdir = os.path.join(base, 'mcip/d01')
        for d in DAYS:
            f = os.path.join(cdir, 'combine.%s.d01.nc' % d)
            if not os.path.exists(f):
                print('  [%s] missing %s' % (chain, d)); continue
            ds = nc.Dataset(f)
            pm = ds.variables['PM25_TOT'][:, 0, :, :]
            tf = ds.variables['TFLAG'][:, 0, :]
            times = [jdate2dt(tf[i, 0], tf[i, 1]) for i in range(pm.shape[0])]
            vals = pm[:, rows, cols]
            for j, t in enumerate(times):
                for k in range(len(st)):
                    station_rec.append((chain, t, st.city_obs.iloc[k], st.station.iloc[k],
                                        float(vals[j, k])))
            ds.close()

            # ---- met 2D
            fm = os.path.join(mdir, 'METCRO2D_%s' % d)
            if os.path.exists(fm):
                dm = nc.Dataset(fm)
                tmf = dm.variables['TFLAG'][:, 0, :]
                mt = [jdate2dt(tmf[i, 0], tmf[i, 1]) for i in range(tmf.shape[0])]
                for j, t in enumerate(mt):
                    recs = {}
                    for v in MET2D_VARS:
                        if v in dm.variables:
                            arr = dm.variables[v][j, 0, :, :]
                            recs[v] = arr[rows, cols].astype(float)
                    # 城市尺度聚合
                    for c, idx in city_station_idx.items():
                        r = dict(chain=chain, time=t, city=c)
                        for v, a in recs.items():
                            r[v] = float(np.nanmean(a[idx]))
                        met_rec.append(r)
                # ---- 垂直廓线（城市平均）
                f3 = os.path.join(mdir, 'METCRO3D_%s' % d)
                if os.path.exists(f3):
                    d3 = nc.Dataset(f3)
                    t3 = d3.variables['TFLAG'][:, 0, :]
                    t3s = [jdate2dt(t3[i, 0], t3[i, 1]) for i in range(t3.shape[0])]
                    for v in ['TA', 'QV', 'PRES', 'ZH', 'WWIND']:
                        arr = d3.variables[v][:, :, :, :][:, :, rows, cols]   # (T, L, Nst)
                        city_mean = np.stack([
                            np.nanmean(arr[:, :, city_station_idx[c]], axis=2)
                            for c in city_station_idx], axis=0)      # (C, T, L)
                        prof_store.setdefault(chain, {}).setdefault(v, []).append(
                            (t3s, np.array(city_mean)))
                    d3.close()
                dm.close()
        print('  [%s] done' % chain)

    sd = pd.DataFrame(station_rec, columns=['chain', 'time', 'city', 'station', 'pm25'])
    sd.to_csv(os.path.join(OUT, 'station_pm25.csv'), index=False, encoding='utf-8-sig')
    print('station rows', len(sd))

    # 城市平均（站点等权）
    city_mod = sd.groupby(['chain', 'time', 'city'], as_index=False)['pm25'].mean()
    city_mod.to_csv(os.path.join(OUT, 'city_pm25_model.csv'), index=False,
                    encoding='utf-8-sig')

    md = pd.DataFrame(met_rec)
    md['TEMP2'] = md['TEMP2']
    md.to_csv(os.path.join(OUT, 'met_city.csv'), index=False, encoding='utf-8-sig')

    # 廓线保存：链条 x 变量 -> (C, T, L) + 时间轴
    out = {}
    for chain, dvar in prof_store.items():
        for v, lst in dvar.items():
            arr = np.concatenate([x[1] for x in lst], axis=1)     # (C, T, L)
            out['%s|%s' % (chain, v)] = arr
    # 时间轴（任取）
    tl = np.array([np.datetime64(t) for t in
                   pd.to_datetime([x[0][0] for x in prof_store['PANGU']['TA']])])
    out['time'] = np.concatenate([np.array([np.datetime64(t, 'h') for t in x[0]])
                                  for x in prof_store['PANGU']['TA']])
    out['city'] = np.array(list(city_station_idx.keys()), dtype=object)
    np.savez_compressed(os.path.join(OUT, 'profiles.npz'), **out)
    print('saved all')


if __name__ == '__main__':
    main()
