# -*- coding: utf-8 -*-
"""
布林带 (Bollinger Bands) 指标计算
"""

import numpy as np


def calculate_bollinger(closes, period=20, num_std=2):
    """
    计算布林带指标
    返回最新值和历史序列
    """
    result = {}
    
    if len(closes) >= period:
        # 计算最新值（保持向后兼容）
        ma = np.mean(closes[-period:])
        std = np.std(closes[-period:])
        result['bb_upper'] = float(ma + num_std * std)
        result['bb_middle'] = float(ma)
        result['bb_lower'] = float(ma - num_std * std)
        
        # 计算历史序列（用于绘制趋势线）
        upper_band = []
        middle_band = []
        lower_band = []
        
        for i in range(period - 1, len(closes)):
            window = closes[i - period + 1:i + 1]
            ma_val = np.mean(window)
            std_val = np.std(window)
            upper_band.append(float(ma_val + num_std * std_val))
            middle_band.append(float(ma_val))
            lower_band.append(float(ma_val - num_std * std_val))
        
        result['bb_upper_series'] = upper_band
        result['bb_middle_series'] = middle_band
        result['bb_lower_series'] = lower_band
    
    return result

