# -*- coding: utf-8 -*-
"""
趋势强度分析
"""

import numpy as np


def analyze_trend_strength(closes, highs, lows):
    """
    分析趋势强度
    """
    result = {}
    
    # 1. ADX简化版（趋势强度指标）
    if len(closes) >= 14:
        # 计算DM+ 和 DM-
        dm_plus = []
        dm_minus = []
        
        for i in range(1, min(14, len(closes))):
            high_diff = highs[-i] - highs[-i-1]
            low_diff = lows[-i-1] - lows[-i]
            
            if high_diff > low_diff and high_diff > 0:
                dm_plus.append(high_diff)
            else:
                dm_plus.append(0)
            
            if low_diff > high_diff and low_diff > 0:
                dm_minus.append(low_diff)
            else:
                dm_minus.append(0)
        
        avg_dm_plus = np.mean(dm_plus) if dm_plus else 0
        avg_dm_minus = np.mean(dm_minus) if dm_minus else 0
        
        # 简化的趋势强度
        total_dm = avg_dm_plus + avg_dm_minus
        if total_dm > 0:
            trend_strength = float((abs(avg_dm_plus - avg_dm_minus) / total_dm) * 100)
        else:
            trend_strength = 0.0
        
        result['trend_strength'] = trend_strength
        
        if avg_dm_plus > avg_dm_minus:
            result['trend_direction'] = 'up'
        elif avg_dm_minus > avg_dm_plus:
            result['trend_direction'] = 'down'
        else:
            result['trend_direction'] = 'neutral'
    
    # 2. 连续上涨/下跌天数
    consecutive_up = 0
    consecutive_down = 0
    
    for i in range(1, min(10, len(closes))):
        if closes[-i] > closes[-i-1]:
            consecutive_up += 1
            if consecutive_down > 0:
                break
        elif closes[-i] < closes[-i-1]:
            consecutive_down += 1
            if consecutive_up > 0:
                break
        else:
            break
    
    result['consecutive_up_days'] = int(consecutive_up)
    result['consecutive_down_days'] = int(consecutive_down)
    
    return result

