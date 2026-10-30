#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 [@key] 占位标记替换为按首次出现排序的编号引用，并重建参考文献表。

参考文献元数据均经 Crossref / 出版方页面核对（DOI 见条目）。
"""
import re
import sys

MD = '/home/ubuntu01/sda/AI2MCIP/paper/论文_初稿.md'

REFS = {
    'bi2023': 'Bi K, Xie L, Zhang H, et al. Accurate medium-range global weather forecasting with '
              '3D neural networks. Nature, 2023, 619(7970): 533–538. doi:10.1038/s41586-023-06185-3',
    'chenk2023': 'Chen K, Han T, Gong J, et al. FengWu: pushing the skillful global medium-range '
                 'weather forecast beyond 10 days lead. arXiv:2304.02948, 2023.',
    'chenl2023': 'Chen L, Zhong X, Zhang F, et al. FuXi: a cascade machine learning forecasting '
                 'system for 15-day global weather forecast. npj Climate and Atmospheric Science, '
                 '2023, 6: 190. doi:10.1038/s41612-023-00512-1',
    'skamarock2008': 'Skamarock W C, Klemp J B, Dudhia J, et al. A description of the Advanced '
                     'Research WRF version 3. NCAR Technical Note NCAR/TN-475+STR, 2008. '
                     'doi:10.5065/D68S4MVH',
    'otte2010': 'Otte T L, Pleim J E. The Meteorology-Chemistry Interface Processor (MCIP) for the '
                'CMAQ modeling system: updates through MCIPv3.4.1. Geoscientific Model Development, '
                '2010, 3(1): 243–256. doi:10.5194/gmd-3-243-2010',
    'byun2006': 'Byun D, Schere K L. Review of the governing equations, computational algorithms, and '
                'other components of the Models-3 Community Multiscale Air Quality (CMAQ) modeling '
                'system. Applied Mechanics Reviews, 2006, 59(2): 51–77. doi:10.1115/1.2128636',
    'appel2017': 'Appel K W, Napelenok S L, Foley K M, et al. Description and evaluation of the '
                 'Community Multiscale Air Quality (CMAQ) modeling system version 5.1. Geoscientific '
                 'Model Development, 2017, 10(4): 1703–1732. doi:10.5194/gmd-10-1703-2017',
    'pleim2007': 'Pleim J E. A combined local and nonlocal closure model for the atmospheric boundary '
                 'layer. Part I: model description and testing. Journal of Applied Meteorology and '
                 'Climatology, 2007, 46(9): 1383–1395. doi:10.1175/JAM2539.1',
    'janjic1994': 'Janjić Z I. The step-mountain eta coordinate model: further developments of the '
                  'convection, viscous sublayer, and turbulence closure schemes. Monthly Weather '
                  'Review, 1994, 122(5): 927–945. doi:10.1175/1520-0493(1994)122<0927:TSMECM>2.0.CO;2',
    'hersbach2020': 'Hersbach H, Bell B, Berrisford P, et al. The ERA5 global reanalysis. Quarterly '
                    'Journal of the Royal Meteorological Society, 2020, 146(730): 1999–2049. '
                    'doi:10.1002/qj.3803',
    'li2017': 'Li M, Liu H, Geng G, et al. Anthropogenic emission inventories in China: a review. '
              'National Science Review, 2017, 4(6): 834–866. doi:10.1093/nsr/nwx150',
    'kim2026': 'Kim S M, Kwon E, Choi J H, et al. Application of machine learning-based wind '
               'corrections to coupled WRF–CMAQ simulations: a comparison of dynamic assimilation and '
               'static replacement. Atmospheric Environment, 2026, 384: 122324. '
               'doi:10.1016/j.atmosenv.2026.122324',
    'campbell2022': 'Campbell P C, Tang Y, Lee P, et al. Development and evaluation of an advanced '
                    'National Air Quality Forecasting Capability using the NOAA Global Forecast System '
                    'version 16. Geoscientific Model Development, 2022, 15(8): 3281–3313. '
                    'doi:10.5194/gmd-15-3281-2022',
    'tang2022': 'Tang Y, Campbell P C, Lee P, et al. Evaluation of the NAQFC driven by the NOAA Global '
                'Forecast System (version 16): comparison with the WRF-CMAQ during the summer 2019 '
                'FIREX-AQ campaign. Geoscientific Model Development, 2022, 15(21): 7977–8004. '
                'doi:10.5194/gmd-15-7977-2022',
    'gu2026': 'Gu H, Xu Y, Pan H, et al. A new framework for medium- to long-term PM2.5 predictions '
              'using AI-based high-resolution meteorological forecasts. Chemical & Bio Engineering, '
              '2026, 3(2): 219–230. doi:10.1021/cbe.5c00074',
    'zhu2024': '朱恩达, 王亚强, 赵妍, 李斌. 东亚区域人工智能气象大模型预报技巧评估[J]. 应用气象学报, '
               '2024, 35(6): 641–653. doi:10.11898/1001-7313.20240601',
    'zhanggb2024': '张国斌, 曹靖原, 邱雄辉, 彭林. 基于过程分析的京津冀地区气象条件变化对PM2.5浓度改善的影响[J]. '
                   '环境科学, 2024, 45(11): 6219–6228.',
    'libw2024': '李博文, 张凯, 高健, 等. 京津冀及周边地区夏季和初秋气象条件对PM2.5和O3双高影响[J]. '
                '环境科学, 2024, 45(8): 4375–4384.',
    'songxh2023': '宋小涵, 燕丽, 刘伟, 等. 2015~2021年京津冀及周边地区PM2.5和臭氧复合污染时空特征分析[J]. '
                  '环境科学, 2023, 44(4): 1841–1851.',
}


def fmt(nums):
    """[1,2,3] -> '[1-3]' when consecutive, else '[1,3]'."""
    nums = sorted(nums)
    if len(nums) == 1:
        return '[%d]' % nums[0]
    # 连续段压缩
    segs, start, prev = [], nums[0], nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        segs.append((start, prev))
        start = prev = n
    segs.append((start, prev))
    out = []
    for a, b in segs:
        out.append(str(a) if a == b else ('%d-%d' % (a, b) if b > a + 1 else '%d,%d' % (a, b)))
    return '[' + ','.join(out) + ']'


def main():
    src = open(MD, encoding='utf-8').read()

    order = []

    def repl(m):
        keys = [k.strip() for k in m.group(1).split(',')]
        nums = []
        for k in keys:
            if k not in REFS:
                raise KeyError('未定义的文献键: %s' % k)
            if k not in order:
                order.append(k)
            nums.append(order.index(k) + 1)
        return fmt(nums)

    src = re.sub(r'\[@([^\]]+)\]', repl, src)

    # 重建参考文献表
    lines = ['## 参考文献', '']
    for i, k in enumerate(order, 1):
        lines.append('%d. %s' % (i, REFS[k]))
    reflist = '\n'.join(lines) + '\n'

    i = src.index('## 参考文献')
    src = src[:i] + reflist
    open(MD, 'w', encoding='utf-8').write(src)
    print('引用文献 %d 条：' % len(order))
    for i, k in enumerate(order, 1):
        print('  [%d] %s' % (i, k))
    unused = [k for k in REFS if k not in order]
    if unused:
        print('未引用（已剔除）：', unused)


if __name__ == '__main__':
    main()
