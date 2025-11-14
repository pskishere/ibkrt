# -*- coding: utf-8 -*-
"""
波动率指标计算
"""

import numpy as np


def calculate_volatility(closes, period=20):
    """
    计算波动率
    """
    result = {}
    
    if len(closes) >= period + 1:
        returns = np.diff(closes) / closes[:-1]
        result['volatility_20'] = float(np.std(returns[-period:]) * 100)
    
    return result

