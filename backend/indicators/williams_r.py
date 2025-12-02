# -*- coding: utf-8 -*-
"""
威廉指标（Williams %R）计算
"""

import numpy as np


def calculate_williams_r(closes, highs, lows, period=14):
    """
    计算威廉指标（Williams %R）
    """
    p = min(period, len(closes))
    highest_high = float(np.max(highs[-p:]))
    lowest_low = float(np.min(lows[-p:]))
    
    if highest_high == lowest_low:
        return -50.0
    
    wr = ((highest_high - closes[-1]) / (highest_high - lowest_low)) * -100
    return float(wr)

