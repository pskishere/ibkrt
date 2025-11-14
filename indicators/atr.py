# -*- coding: utf-8 -*-
"""
ATR（平均真实波幅）指标计算
"""

import numpy as np


def calculate_atr(closes, highs, lows, period=14):
    """
    计算ATR（平均真实波幅）
    """
    # 计算真实波幅TR
    tr_list = []
    for i in range(1, min(period + 1, len(closes))):
        high_low = highs[-i] - lows[-i]
        high_close = abs(highs[-i] - closes[-i-1])
        low_close = abs(lows[-i] - closes[-i-1])
        tr = max(high_low, high_close, low_close)
        tr_list.append(tr)
    
    atr = float(np.mean(tr_list))
    return atr

