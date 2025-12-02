# -*- coding: utf-8 -*-
"""
价格变化指标计算
"""

import numpy as np


def calculate_price_change(closes):
    """
    计算价格变化
    """
    result = {}
    
    if len(closes) >= 2:
        result['price_change'] = float(closes[-1] - closes[-2])
        result['price_change_pct'] = float(((closes[-1] - closes[-2]) / closes[-2] * 100)) if closes[-2] != 0 else 0.0
    
    return result

