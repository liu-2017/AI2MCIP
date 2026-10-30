# 论文图件与统计脚本（plotting / analysis scripts）

本目录保留论文《面向 AI 气象大模型的标准化 MCIP 驱动接口……》与《pangu2wrf v7 技术文档》的**全部绘图与统计脚本**，可在不改动原始模式输出的前提下，从 `MIDDLE_DATA` 重新生成 `paper/data/` 与 `paper/figures/`。

## 目录结构

```
scripts/
├── pics/                     # 每张图一个独立脚本（推荐入口）
│   ├── fig1_framework.py        图 1  五条链条与适配器架构（示意图）
│   ├── fig2_domain.py           图 2  域地形与 119 个站点
│   ├── fig3_timeseries.py       图 3  多城市 PM2.5 时间序列（城市可传参）
│   ├── fig4_spatial.py          图 4  PM2.5 空间分布（日期/时次/链条可传参）
│   ├── fig5_scores.py           图 5  统计指标（散点、R/IOA、分阶段）
│   ├── fig6_met.py              图 6  PBLH / 风速 / 通风指数
│   ├── fig7_profiles.py         图 7  峰值日垂直廓线（--day 可传参）
│   ├── fig8_attribution.py      图 8  偏差归因
│   ├── fig9_sensitivity.py      图 9  诊断敏感性实验
│   ├── fig10_runtime.py         图 10 计算时效
│   └── fig_tech_pipeline.py     技术文档 图 1  适配器数据流
├── figs_common.py           # 公共设置：中文字体、配色、链条命名、路径
├── figs_part1.py            # 兼容层（deprecated）：导入 pics/fig1、fig2、fig5
├── figs_part2.py            # 兼容层（deprecated）：导入 pics/fig6…fig10
├── build_dataset.py         # 站点/城市/气象序列提取
├── metrics.py               # 总体/分阶段/峰值统计
├── sens_metrics.py          # 敏感性实验指标
├── apply_citations.py       # 参考文献编号与文献表重建
├── make_figs.sh             # 一键重建：数据 → 指标 → 图 → docx
├── pangu2wrf_a2.py          # 适配器副本（实验 A2 的 PBLH 开关）
└── run_*.csh                # 敏感性/补跑链条的启动脚本
```

## 一键复现

```bash
cd /home/ubuntu01/sda/AI2MCIP/paper/scripts
bash make_figs.sh              # 数据 → 指标 → 图（pics/ 下 10 个脚本）→ docx
bash make_figs.sh --skip-data  # 沿用已有 data/，只重绘
```

## 单独重绘某张图

每个图脚本都可独立运行，默认输出到 `../figures/`：

```bash
python3 pics/fig1_framework.py
python3 pics/fig3_timeseries.py                          # 默认 北京/石家庄/天津
python3 pics/fig3_timeseries.py --cities 北京 天津 邯郸
python3 pics/fig4_spatial.py                             # 默认 20251030 12 UTC、4 条链条
python3 pics/fig4_spatial.py --date 20251031 --hour 0
python3 pics/fig4_spatial.py --chains PANGU FENGWU --no-obs
python3 pics/fig7_profiles.py --day 20251029
python3 pics/fig9_sensitivity.py
python3 pics/fig_tech_pipeline.py                        # 技术文档流程图
```

也可以当模块导入（便于批量出图）：

```python
from pics.fig3_timeseries import fig3
from pics.fig4_spatial import fig4
fig3(cities=('北京', '保定'), out='/tmp/ts.png')
fig4(chains=('PANGU',), when='20251029', hour=6)
```

## 各脚本的作用与输出

| 脚本 | 作用 | 主要输出 |
|---|---|---|
| `pics/fig1_framework.py` | 五条链条与适配器架构示意（纯矢量框图） | `figures/fig1_framework.png` |
| `pics/fig2_domain.py` | 域地形 + 站点 + 城市标注 | `figures/fig2_domain.png` |
| `pics/fig3_timeseries.py` | 14 城市平均 + 逐城市逐时序列（`--cities`） | `figures/fig3_timeseries.png` |
| `pics/fig4_spatial.py` | 多面板 PM2.5 空间分布（`--date/--hour/--chains/--levels/--extent/--no-obs`） | `figures/fig4_spatial.png` |
| `pics/fig5_scores.py` | 散点、R/IOA、分阶段 NMB/RMSE | `figures/fig5_scores.png` |
| `pics/fig6_met.py` | PBLH 日变化、逐日 PBLH/风速/通风指数 | `figures/fig6_met.png` |
| `pics/fig7_profiles.py` | 位温/相对湿度/PM2.5 垂直廓线（`--day`） | `figures/fig7_profiles.png` |
| `pics/fig8_attribution.py` | 通风/PBLH 偏差 vs NMB、链条替换效应、逐日偏差 | `figures/fig8_attribution.png` |
| `pics/fig9_sensitivity.py` | A1/A2 的 PBLH 与 PM2.5、KZ0UT 对照、指标 | `figures/fig9_sensitivity.png` |
| `pics/fig10_runtime.py` | 单位模拟日墙钟时间 | `figures/fig10_runtime.png` |
| `pics/fig_tech_pipeline.py` | 技术文档适配器数据流图 | `figures/fig_tech_pipeline.png` |
| `build_dataset.py` | 从 5 条链条的 `combine.*.nc` / `METCRO2D` / `METCRO3D` 提取 119 站点、14 城市序列 | `data/station_pm25.csv`、`city_pm25_model.csv`、`met_city.csv`、`profiles.npz`、`stations.csv` |
| `metrics.py` | 总体/分阶段/日峰值统计、气象诊断汇总 | `data/scores_*.csv`、`met_daily.csv`、`metrics_report.txt` |
| `sens_metrics.py` | 敏感性实验的指标与 PBLH 日变化 | `data/sens_scores.csv`、`sens_pbl.csv` |
| `apply_citations.py` | `[@key]` 占位按首次出现重排编号并重建文献表 | `论文_初稿.md` |
| `../build_docx.js` / `../build_tech_docx.js` | Markdown → Word | `论文_初稿.docx`、`pangu2wrf_技术文档.docx` |

## 敏感性实验（如需重跑模式）

| 脚本 | 说明 |
|---|---|
| `pangu2wrf_a2.py` | 适配器副本，新增 `pbl_conv_on` 开关（0 = 仅 Richardson 数，实验 A2） |
| `run_mcip_pbl2.csh` | A2 的 MCIP（域 `ECPGV3_PBL2`） |
| `run_cctm_pbl2.csh` | A2 的 CCTM + combine |
| `run_cctm_kz1_wrap.csh` / `run_cctm_kz1.csh` / `run_combine_kz1.csh` | 实验 B：`KZMIN=Y` 改为 `KZ0UT=1.0`（域 `ECPGV3_KZ1`） |
| `run_fengyuan_cctm.csh` | 补跑 FengYuan 分支 9 天 CCTM + combine |

## 依赖

`python 3.10`、`netCDF4`、`numpy`、`pandas`、`matplotlib`、`cartopy`、`pyproj`、`openpyxl/xlrd`（读 `BTH.xls`）；
`node` + `docx`（`build_docx.js`，依赖见 `../node_modules` → `参考文献/.build/node_modules`）；
`libreoffice`（可选，用于导出 PDF）。

## 约定

- 所有模式时间为 **UTC**；观测（国控站）为北京时间，绘图与统计时按 UTC 对齐。
- 城市值 = 城市内站点等权平均；观测取中国环境监测总站城市均值。
- 阶段划分：P1 10-27—10-28、P2 10-29—10-30、P3 10-31—11-02、P4 11-03—11-05（UTC）。
- 颜色/标记在 `figs_common.py` 中统一定义，新增图件请复用，避免风格漂移。
- 新增图件时，在 `pics/` 下新建 `figN_<name>.py`，按现有脚本的模板写 `if __name__ == '__main__':` 入口，并把文件名加入 `make_figs.sh` 的循环。
