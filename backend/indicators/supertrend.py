# -*- coding: utf-8 -*-
"""
SuperTrend 指标计算
"""

import numpy as np

def calculate_supertrend(closes, highs, lows, period=10, multiplier=3.0):
    """
    计算SuperTrend指标
    
    返回:
    - supertrend: 当前SuperTrend值
    - direction: 趋势方向 ('up' 或 'down')
    - lower_band: 下轨
    - upper_band: 上轨
    """
    result = {}
    
    if len(closes) < period + 1:
        return result
        
    # 1. 计算ATR序列
    # 注意：我们需要修改atr.py以支持返回序列，或者在这里重新实现ATR计算
    # 为了独立性，这里简单实现ATR序列计算
    
    tr_list = [0.0]
    for i in range(1, len(closes)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i-1])
        lc = abs(lows[i] - closes[i-1])
        tr_list.append(max(hl, hc, lc))
    
    tr = np.array(tr_list)
    atr = np.zeros_like(tr)
    
    # 初始ATR (简单平均)
    atr[period] = np.mean(tr[1:period+1])
    
    # 平滑ATR (Wilder's Smoothing)
    for i in range(period + 1, len(closes)):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        
    # 2. 计算基本上下轨
    hl2 = (highs + lows) / 2
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr
    
    # 3. 计算最终上下轨
    final_upper = np.zeros_like(basic_upper)
    final_lower = np.zeros_like(basic_lower)
    supertrend = np.zeros_like(basic_upper)
    trend = np.zeros(len(closes), dtype=int) # 1 for up, -1 for down
    
    # 初始化
    final_upper[period] = basic_upper[period]
    final_lower[period] = basic_lower[period]
    
    for i in range(period + 1, len(closes)):
        # 最终上轨
        if basic_upper[i] < final_upper[i-1] or closes[i-1] > final_upper[i-1]:
            final_upper[i] = basic_upper[i]
        else:
            final_upper[i] = final_upper[i-1]
            
        # 最终下轨
        if basic_lower[i] > final_lower[i-1] or closes[i-1] < final_lower[i-1]:
            final_lower[i] = basic_lower[i]
        else:
            final_lower[i] = final_lower[i-1]
            
        # 计算SuperTrend
        if trend[i-1] == 1: # 之前是上涨趋势
            if closes[i] < final_lower[i-1]: # 跌破下轨，转为下跌
                trend[i] = -1
                supertrend[i] = final_upper[i]
            else:
                trend[i] = 1
                supertrend[i] = final_lower[i]
        elif trend[i-1] == -1: # 之前是下跌趋势
            if closes[i] > final_upper[i-1]: # 突破上轨，转为上涨
                trend[i] = 1
                supertrend[i] = final_lower[i]
            else:
                trend[i] = -1
                supertrend[i] = final_upper[i]
        else: # 初始状态
            if closes[i] > final_upper[i]:
                trend[i] = 1
                supertrend[i] = final_lower[i]
            else:
                trend[i] = -1
                supertrend[i] = final_upper[i]
                
    # 结果
    result['supertrend'] = float(supertrend[-1])
    result['supertrend_direction'] = 'up' if trend[-1] == 1 else 'down'
    result['supertrend_upper'] = float(final_upper[-1])
    result['supertrend_lower'] = float(final_lower[-1])
    
    return result
