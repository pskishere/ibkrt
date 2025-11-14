# -*- coding: utf-8 -*-
"""
移动平均线 (MA) 指标计算
"""

import numpy as np


def calculate_ma(closes):
    """
    计算移动平均线
    """
    result = {}
    
    if len(closes) >= 5:
        result['ma5'] = float(np.mean(closes[-5:]))
    if len(closes) >= 10:
        result['ma10'] = float(np.mean(closes[-10:]))
    if len(closes) >= 20:
        result['ma20'] = float(np.mean(closes[-20:]))
    if len(closes) >= 50:
        result['ma50'] = float(np.mean(closes[-50:]))
    
    return result

