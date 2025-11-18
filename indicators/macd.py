# -*- coding: utf-8 -*-
"""
MACD 指标计算
"""

import numpy as np


def _ema(data, period):
    """
    计算指数移动平均线
    使用递归公式：EMA_today = α × Price_today + (1-α) × EMA_yesterday
    """
    alpha = 2 / (period + 1)
    ema = data[0]  # 使用第一个值作为初始EMA
    for price in data[1:]:
        ema = alpha * price + (1 - alpha) * ema
    return ema


def calculate_macd(closes, fast_period=12, slow_period=26, signal_period=9):
    """
    计算MACD指标
    """
    result = {}
    
    if len(closes) >= slow_period:
        ema12 = _ema(closes, fast_period)
        ema26 = _ema(closes, slow_period)
        macd_line = ema12 - ema26
        
        # 计算信号线 (MACD的9日EMA)
        if len(closes) >= slow_period + signal_period:
            macd_values = []
            for i in range(slow_period, len(closes)):
                e12 = _ema(closes[:i+1], fast_period)
                e26 = _ema(closes[:i+1], slow_period)
                macd_values.append(e12 - e26)
            
            if len(macd_values) >= signal_period:
                signal_line = _ema(np.array(macd_values), signal_period)
                result['macd'] = float(macd_line)
                result['macd_signal'] = float(signal_line)
                result['macd_histogram'] = float(macd_line - signal_line)
    
    return result

