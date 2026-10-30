#!/usr/bin/env bash
# 一键重建：数据集 -> 指标 -> 图件 -> Word
# 用法： bash make_figs.sh [--skip-data]
set -euo pipefail

cd "$(dirname "$0")"
SKIP_DATA=0
[[ "${1:-}" == "--skip-data" ]] && SKIP_DATA=1

echo "==> 1/5 数据集（站点/城市/气象）"
if [[ $SKIP_DATA -eq 0 ]]; then
  python3 build_dataset.py
else
  echo "    跳过（沿用 paper/data 现有结果）"
fi

echo "==> 2/5 统计指标"
python3 metrics.py | tee ../data/metrics_report.txt >/dev/null

echo "==> 3/5 敏感性实验指标"
python3 sens_metrics.py || echo "    （敏感性结果尚未生成，跳过）"

echo "==> 4/5 图件（每图一个脚本，位于 pics/）"
for f in pics/fig1_framework.py pics/fig2_domain.py pics/fig3_timeseries.py \
         pics/fig4_spatial.py pics/fig5_scores.py pics/fig6_met.py \
         pics/fig7_profiles.py pics/fig8_attribution.py pics/fig9_sensitivity.py \
         pics/fig10_runtime.py; do
  python3 "$f"
done

echo "==> 5/5 Word 文档"
( cd .. && node build_docx.js )

echo "完成： paper/figures/*.png, paper/论文_初稿.docx"
