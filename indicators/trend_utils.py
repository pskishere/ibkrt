# -*- coding: utf-8 -*-
"""
趋势工具函数
"""

import numpy as np


def get_trend(data):
    """
    判断数据趋势方向
    """
    if len(data) < 3:
        return 'neutral'
    
    # 简单线性回归判断趋势
    x = np.arange(len(data))
    slope = np.polyfit(x, data, 1)[0]
    
    if slope > np.std(data) * 0.1:
        return 'up'
    elif slope < -np.std(data) * 0.1:
        return 'down'
    else:
        return 'neutral'

