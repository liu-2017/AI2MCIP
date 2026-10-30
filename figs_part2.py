#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兼容层（deprecated）：图 6—图 10 的实现已拆分到 pics/ 下，每图一个脚本。

新代码请直接使用：

    python3 pics/fig6_met.py ... pics/fig10_runtime.py

或导入：``from pics.fig6_met import fig6``。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from pics.fig6_met import fig6            # noqa: E402,F401
from pics.fig7_profiles import fig7        # noqa: E402,F401
from pics.fig8_attribution import fig8     # noqa: E402,F401
from pics.fig9_sensitivity import fig9     # noqa: E402,F401
from pics.fig10_runtime import fig10       # noqa: E402,F401

if __name__ == '__main__':
    fig6(); print('fig6 ok')
    fig7(); print('fig7 ok')
    fig8(); print('fig8 ok')
    fig9(); print('fig9 ok')
    fig10(); print('fig10 ok')
