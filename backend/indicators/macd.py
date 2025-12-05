# -*- coding: utf-8 -*-
"""
MACD 指标计算
"""

import numpy as np


def _calculate_ema_series(data, period):
    """
    计算整个序列的EMA
    """
    alpha = 2 / (period + 1)
    ema_values = np.zeros_like(data)
    ema_values[0] = data[0]
    
    for i in range(1, len(data)):
        ema_values[i] = alpha * data[i] + (1 - alpha) * ema_values[i-1]
        
    return ema_values


def calculate_macd(closes, fast_period=12, slow_period=26, signal_period=9):
    """
    计算MACD指标 (优化版)
    """
    result = {}
    
    if len(closes) < slow_period + signal_period:
        return result
        
    # 计算快慢EMA序列
    ema12_series = _calculate_ema_series(closes, fast_period)
    ema26_series = _calculate_ema_series(closes, slow_period)
    
    # 计算DIF (MACD Line)
    macd_line_series = ema12_series - ema26_series
    
    # 计算DEA (Signal Line) - 对DIF进行EMA平滑
    # 注意：Signal Line通常是基于DIF的EMA，而不是价格
    # 我们只关心最后的部分，但为了计算准确，需要足够的历史数据
    signal_line_series = _calculate_ema_series(macd_line_series, signal_period)
    
    # 计算MACD Histogram
    # 中国标准（富途、同花顺等）：MACD = (DIF - DEA) * 2
    # 注：国际标准为 DIF - DEA，中国市场普遍使用 * 2 放大显示效果
    histogram_series = (macd_line_series - signal_line_series) * 2
    
    # 返回最新的值
    result['macd'] = float(macd_line_series[-1])
    result['macd_signal'] = float(signal_line_series[-1])
    result['macd_histogram'] = float(histogram_series[-1])
    
    return result

