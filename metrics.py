#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计指标：逐链条、分阶段 PM2.5 模拟效果；峰值捕捉；气象诊断汇总。"""
import os
import numpy as np
import pandas as pd

ROOT = '/home/ubuntu01/sda/AI2MCIP/paper'
D = os.path.join(ROOT, 'data')

CHAINS = ['CTL_WRF', 'ERA5_ADP', 'PANGU', 'FENGWU', 'FENGYUAN']
LABEL = {'CTL_WRF': 'ERA5→WRF→MCIP→CMAQ', 'ERA5_ADP': 'ERA5→Adapter→MCIP→CMAQ',
         'PANGU': 'Pangu→Adapter→MCIP→CMAQ', 'FENGWU': 'FengWu→Adapter→MCIP→CMAQ',
         'FENGYUAN': 'FengYuan→Adapter→MCIP→CMAQ'}

PHASES = {
    'P1 累积': ('2025-10-27 00:00', '2025-10-29 00:00'),
    'P2 峰值': ('2025-10-29 00:00', '2025-10-31 00:00'),
    'P3 清除': ('2025-10-31 00:00', '2025-11-03 00:00'),
    'P4 二次累积': ('2025-11-03 00:00', '2025-11-05 00:00'),
}


def load():
    mod = pd.read_csv(os.path.join(D, 'city_pm25_model.csv'), parse_dates=['time'])
    obs = pd.read_csv(os.path.join(D, 'obs_city_pm25.csv'), parse_dates=['dt'])
    m = mod.rename(columns={'time': 'dt', 'pm25': 'sim'}).merge(
        obs[['dt', 'city', 'pm25_obs']].rename(columns={'pm25_obs': 'obs'}),
        on=['dt', 'city'], how='inner')
    return m.dropna(subset=['sim', 'obs'])


def metrics(g):
    o, s = g['obs'].values, g['sim'].values
    n = len(o)
    mb = np.mean(s - o)
    mae = np.mean(np.abs(s - o))
    rmse = np.sqrt(np.mean((s - o) ** 2))
    r = np.corrcoef(o, s)[0, 1] if n > 2 else np.nan
    nmb = 100 * mb / np.mean(o)
    ioa = 1 - np.sum((s - o) ** 2) / np.sum((np.abs(s - np.mean(o)) + np.abs(o - np.mean(o))) ** 2)
    slope = np.polyfit(o, s, 1)[0]
    return pd.Series(dict(N=n, MB=mb, NMB=nmb, MAE=mae, RMSE=rmse, R=r, IOA=ioa, slope=slope))


def main():
    m = load()
    # 总体
    rows = []
    for ch, g in m.groupby('chain'):
        met = metrics(g)
        met['chain'] = ch
        rows.append(met)
    tot = pd.DataFrame(rows).set_index('chain').loc[[c for c in CHAINS if c in m.chain.unique()]]
    tot.to_csv(os.path.join(D, 'scores_total.csv'), float_format='%.3f')
    print('== 总体（城市逐小时，%.0f 个样本）==' % len(m))
    print(tot.round(2).to_string())

    # 分阶段
    rows = []
    for ph, (a, b) in PHASES.items():
        sub = m[(m.dt >= a) & (m.dt < b)]
        for ch, g in sub.groupby('chain'):
            met = metrics(g)
            met['chain'] = ch
            met['phase'] = ph
            rows.append(met)
    ph = pd.DataFrame(rows)[['phase', 'chain', 'N', 'MB', 'NMB', 'MAE', 'RMSE', 'R']]
    ph.to_csv(os.path.join(D, 'scores_phase.csv'), index=False, float_format='%.3f')
    print('\n== 分阶段 NMB(%) / RMSE ==')
    print(ph.pivot(index='phase', columns='chain', values='NMB').round(1).to_string())

    # 峰值捕捉：逐城市日最大值
    m['day'] = m.dt.dt.date
    pk = m.groupby(['chain', 'city', 'day']).agg(sim_max=('sim', 'max'), obs_max=('obs', 'max')).reset_index()
    pk = pk[pk.obs_max >= 50]
    rows = []
    for ch, g in pk.groupby('chain'):
        rows.append(dict(chain=ch, N=len(g),
                         bias_peak=np.mean(g.sim_max - g.obs_max),
                         nmb_peak=100 * np.mean(g.sim_max - g.obs_max) / np.mean(g.obs_max),
                         r_peak=np.corrcoef(g.obs_max, g.sim_max)[0, 1]))
    pt = pd.DataFrame(rows).set_index('chain').loc[[c for c in CHAINS if c in pk.chain.unique()]]
    pt.to_csv(os.path.join(D, 'scores_peak.csv'), float_format='%.2f')
    print('\n== 日峰值（obs_max>=50）==')
    print(pt.round(2).to_string())

    # BTH 14 城市均值逐时序列（写作与绘图共用）
    ser = m.groupby(['chain', 'dt'])[['sim', 'obs']].mean().reset_index()
    ser.to_csv(os.path.join(D, 'bth_series.csv'), index=False, float_format='%.2f')

    # 气象诊断汇总
    mt = pd.read_csv(os.path.join(D, 'met_city.csv'), parse_dates=['time'])
    e = mt.Q2 * mt.PRSFC / (0.622 + mt.Q2)
    es = 611.2 * np.exp(17.67 * (mt.TEMP2 - 273.15) / (mt.TEMP2 - 29.65))
    mt['RH'] = (100 * e / es).clip(0, 100)
    mt['VI'] = mt.PBL * mt.WSPD10
    mt['day'] = mt.time.dt.date
    agg = mt.groupby(['chain', 'day']).agg(PBL=('PBL', 'mean'), WSPD=('WSPD10', 'mean'),
                                           VI=('VI', 'mean'), RH=('RH', 'mean'),
                                           T2=('TEMP2', 'mean'), GSW=('GSW', 'mean'),
                                           HFX=('HFX', 'mean'), CFRAC=('CFRAC', 'mean'),
                                           USTAR=('USTAR', 'mean'), WSTAR=('WSTAR', 'mean'),
                                           MOLI=('MOLI', 'mean')).reset_index()
    agg.to_csv(os.path.join(D, 'met_daily.csv'), index=False, float_format='%.2f')
    print('\n== 逐日域平均 PBL(m) ==')
    print(agg.pivot(index='day', columns='chain', values='PBL').round(0).to_string())
    print('\n== 逐日域平均 10 m 风速(m/s) ==')
    print(agg.pivot(index='day', columns='chain', values='WSPD').round(2).to_string())
    print('\n== 逐日域平均 通风指数 ==')
    print(agg.pivot(index='day', columns='chain', values='VI').round(0).to_string())
    mt.to_csv(os.path.join(D, 'met_city_rh.csv'), index=False, float_format='%.2f')


if __name__ == '__main__':
    main()
