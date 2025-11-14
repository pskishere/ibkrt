# -*- coding: utf-8 -*-
"""
RSI (相对强弱指标) 计算
"""

import numpy as np


def calculate_rsi(closes, period=14):
    """
    计算RSI指标
    """
    result = {}
    
    if len(closes) >= period + 1:
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss != 0:
            rs = avg_gain / avg_loss
            result['rsi'] = float(100 - (100 / (1 + rs)))
        else:
            result['rsi'] = 100.0
    
    return result

