# -*- coding: utf-8 -*-
"""
斐波那契回撤位计算
"""

import numpy as np


def calculate_fibonacci_retracement(highs, lows):
    """
    计算斐波那契回撤位
    """
    result = {}
    
    # 确保有足够的数据点
    if len(highs) < 2 or len(lows) < 2:
        return result
        
    # 找到最近的高点和低点
    recent_high = float(np.max(highs[-20:]))
    recent_low = float(np.min(lows[-20:]))
    
    # 计算价格范围
    price_range = recent_high - recent_low
    
    # 斐波那契回撤水平 (23.6%, 38.2%, 50%, 61.8%, 78.6%)
    fib_levels = {
        'fib_23.6': recent_high - (price_range * 0.236),
        'fib_38.2': recent_high - (price_range * 0.382),
        'fib_50.0': recent_high - (price_range * 0.5),
        'fib_61.8': recent_high - (price_range * 0.618),
        'fib_78.6': recent_high - (price_range * 0.786)
    }
    
    # 转换为浮点数
    for key, value in fib_levels.items():
        result[key] = float(value)
        
    # 添加最近高低点信息
    result['fib_recent_high'] = recent_high
    result['fib_recent_low'] = recent_low
    
    return result

