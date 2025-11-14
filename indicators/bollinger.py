# -*- coding: utf-8 -*-
"""
布林带 (Bollinger Bands) 指标计算
"""

import numpy as np


def calculate_bollinger(closes, period=20, num_std=2):
    """
    计算布林带指标
    """
    result = {}
    
    if len(closes) >= period:
        ma = np.mean(closes[-period:])
        std = np.std(closes[-period:])
        result['bb_upper'] = float(ma + num_std * std)
        result['bb_middle'] = float(ma)
        result['bb_lower'] = float(ma - num_std * std)
    
    return result

