# -*- coding: utf-8 -*-
"""
KDJ指标（随机指标）计算
"""

import numpy as np


def calculate_kdj(closes, highs, lows, n=9):
    """
    计算KDJ指标（随机指标）
    """
    # 计算RSV（未成熟随机值）
    period = min(n, len(closes))
    lowest_low = float(np.min(lows[-period:]))
    highest_high = float(np.max(highs[-period:]))
    
    if highest_high == lowest_low:
        rsv = 50.0
    else:
        rsv = ((closes[-1] - lowest_low) / (highest_high - lowest_low)) * 100
    
    # 简化计算：使用最近的RSV
    # 完整版需要历史K、D值，这里使用简化版本
    k = float(rsv)
    d = float((2 * k + rsv) / 3)
    j = float(3 * k - 2 * d)
    
    return {
        'kdj_k': k,
        'kdj_d': d,
        'kdj_j': j
    }

