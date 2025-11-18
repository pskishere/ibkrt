# -*- coding: utf-8 -*-
"""
CCI（顺势指标）计算
Commodity Channel Index
"""

import numpy as np


def calculate_cci(closes, highs, lows, period=14):
    """
    计算CCI指标
    CCI = (TP - MA) / (0.015 * MD)
    其中：
    TP = (最高价 + 最低价 + 收盘价) / 3
    MA = TP的N日简单移动平均
    MD = TP的N日平均绝对偏差
    """
    result = {}
    
    if len(closes) < period:
        return result
    
    # 计算典型价格 Typical Price
    typical_prices = (highs + lows + closes) / 3
    
    # 计算TP的移动平均
    tp_ma = np.mean(typical_prices[-period:])
    
    # 计算平均绝对偏差 Mean Deviation
    mean_deviation = np.mean(np.abs(typical_prices[-period:] - tp_ma))
    
    # 计算CCI
    if mean_deviation != 0:
        cci = (typical_prices[-1] - tp_ma) / (0.015 * mean_deviation)
        result['cci'] = float(cci)
        
        # CCI信号判断
        if cci > 100:
            result['cci_signal'] = 'overbought'  # 超买
        elif cci < -100:
            result['cci_signal'] = 'oversold'  # 超卖
        else:
            result['cci_signal'] = 'neutral'  # 中性
    else:
        result['cci'] = 0.0
        result['cci_signal'] = 'neutral'
    
    return result
