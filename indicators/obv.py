# -*- coding: utf-8 -*-
"""
OBV（能量潮指标）计算
"""

import numpy as np


def calculate_obv(closes, volumes):
    """
    计算OBV（能量潮指标）
    """
    obv = [0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]:
            obv.append(obv[-1] + volumes[i])
        elif closes[i] < closes[i-1]:
            obv.append(obv[-1] - volumes[i])
        else:
            obv.append(obv[-1])
    
    return np.array(obv)

