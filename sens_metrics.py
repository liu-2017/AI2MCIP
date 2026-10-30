#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""敏感性实验（A2: 仅 Rib 的 PBLH；B: KZ0UT=1.0）的统计与诊断量对比。"""
import os
import numpy as np
import pandas as pd
import netCDF4 as nc

from figs_common import ROOT, D, base

DAYS = ['20251027', '20251028', '20251029', '20251030', '20251031',
        '20251101', '20251102', '20251103', '20251104']


def city_series(chain):
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
                rec.append((t, c, float(np.nanmean(v[j, k]))))
        ds.close()
    return pd.DataFrame(rec, columns=['dt', 'city', 'sim'])


def pbl_diurnal(chain, day='20251030'):
    f = os.path.join(base(chain), 'mcip/d01/METCRO2D_%s' % day)
    if not os.path.exists(f):
        return None
    d = nc.Dataset(f)
    p = d.variables['PBL'][:, 0].mean(axis=(1, 2))
    d.close()
    return p


def main():
    obs = pd.read_csv(os.path.join(D, 'obs_city_pm25.csv'), parse_dates=['dt'])
    obs = obs.rename(columns={'pm25_obs': 'obs'})
    rows, pbl_rows = [], []
    cases = [('A1 默认 (Rib+对流)', 'PANGU'), ('A2 仅 Rib (PBL2)', 'PBL2'),
             ('KZ0UT=1.0 (KZ1)', 'KZ1')]
    for tag, ch in cases:
        try:
            s = city_series(ch)
        except Exception as e:
            print('skip', tag, e); continue
        if s.empty:
            print('empty', tag); continue
        j = s.merge(obs, on=['dt', 'city'], how='inner').dropna()
        if j.empty:
            continue
        mb = (j.sim - j.obs).mean()
        rows.append(dict(case=tag, N=len(j), MB=mb,
                         NMB=100 * mb / j.obs.mean(),
                         RMSE=np.sqrt(((j.sim - j.obs) ** 2).mean()),
                         R=np.corrcoef(j.obs, j.sim)[0, 1]))
        print(tag, rows[-1])
    if rows:
        pd.DataFrame(rows).to_csv(os.path.join(D, 'sens_scores.csv'), index=False,
                                  float_format='%.3f')

    for tag, ch in cases[:2]:
        p = pbl_diurnal(ch)
        if p is None:
            continue
        for h, v in enumerate(p):
            pbl_rows.append(dict(case=tag, hour=h, PBL=v))
    if pbl_rows:
        pd.DataFrame(pbl_rows).to_csv(os.path.join(D, 'sens_pbl.csv'), index=False,
                                      float_format='%.1f')


if __name__ == '__main__':
    main()
