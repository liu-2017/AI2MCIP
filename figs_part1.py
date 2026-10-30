#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兼容层（deprecated）：图 1/2/5 的实现已拆分到 pics/ 下，每图一个脚本。

新代码请直接使用：

    python3 pics/fig1_framework.py
    python3 pics/fig2_domain.py
    python3 pics/fig5_scores.py

或导入：``from pics.fig1_framework import fig1``。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from pics.fig1_framework import fig1  # noqa: E402,F401
from pics.fig2_domain import fig2      # noqa: E402,F401
from pics.fig5_scores import fig5      # noqa: E402,F401

if __name__ == '__main__':
    fig1(); print('fig1 ok')
    fig2(); print('fig2 ok')
    fig5(); print('fig5 ok')
