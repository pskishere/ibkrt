# -*- coding: utf-8 -*-
"""
ATR（平均真实波幅）指标计算
"""

import numpy as np


def calculate_atr(closes, highs, lows, period=14):
    """
    计算ATR（平均真实波幅）
    使用Wilder平滑法（指数移动平均）
    TR = max(high-low, abs(high-prev_close), abs(low-prev_close))
    ATR = Wilder平滑(TR)
    """
    if len(closes) < period + 1:
        return 0.0
    
    # 计算真实波幅TR序列
    tr_list = []
    for i in range(1, len(closes)):
        high_low = highs[i] - lows[i]
        high_close = abs(highs[i] - closes[i-1])
        low_close = abs(lows[i] - closes[i-1])
        tr = max(high_low, high_close, low_close)
        tr_list.append(tr)
    
    if len(tr_list) < period:
        return 0.0
    
    # 第一个ATR使用简单平均
    atr = np.mean(tr_list[:period])
    
    # 如果有更多数据，使用Wilder平滑
    for i in range(period, len(tr_list)):
        atr = (atr * (period - 1) + tr_list[i]) / period
    
    return float(atr)

