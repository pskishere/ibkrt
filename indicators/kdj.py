# -*- coding: utf-8 -*-
"""
KDJ指标（随机指标）计算
"""

import numpy as np


def calculate_kdj(closes, highs, lows, n=9, m1=3, m2=3):
    """
    计算KDJ指标（随机指标）
    n: RSV周期，默认9
    m1: K值平滑周期，默认3
    m2: D值平滑周期，默认3
    标准公式：
    K = 2/3 × K_prev + 1/3 × RSV
    D = 2/3 × D_prev + 1/3 × K
    J = 3 × K - 2 × D
    """
    result = {}
    
    if len(closes) < n:
        return result
    
    # 计算RSV（未成熟随机值）
    period = min(n, len(closes))
    lowest_low = float(np.min(lows[-period:]))
    highest_high = float(np.max(highs[-period:]))
    
    if highest_high == lowest_low:
        rsv = 50.0
    else:
        rsv = ((closes[-1] - lowest_low) / (highest_high - lowest_low)) * 100
    
    # 使用标准平滑公式
    # 如果没有历史值，初始化K=D=50
    # 这里为简化，使用RSV作为初始值
    k_prev = rsv  # 第一次计算时使用RSV作为初始值
    d_prev = rsv
    
    # K = (m1-1)/m1 × K_prev + 1/m1 × RSV
    k = ((m1 - 1) / m1) * k_prev + (1 / m1) * rsv
    
    # D = (m2-1)/m2 × D_prev + 1/m2 × K
    d = ((m2 - 1) / m2) * d_prev + (1 / m2) * k
    
    # J = 3K - 2D
    j = 3 * k - 2 * d
    
    result['kdj_k'] = float(k)
    result['kdj_d'] = float(d)
    result['kdj_j'] = float(j)
    
    return result

