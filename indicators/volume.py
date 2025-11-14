# -*- coding: utf-8 -*-
"""
成交量分析指标计算
"""

import numpy as np


def calculate_volume(volumes, period=20):
    """
    计算成交量相关指标
    """
    result = {}
    
    if len(volumes) >= period:
        result['avg_volume_20'] = float(np.mean(volumes[-period:]))
        result['current_volume'] = float(volumes[-1])
        avg_vol = np.mean(volumes[-period:])
        result['volume_ratio'] = float(volumes[-1] / avg_vol) if avg_vol > 0 else 0.0
    
    return result

