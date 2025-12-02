# -*- coding: utf-8 -*-
"""
RSI (相对强弱指标) 计算
"""

import numpy as np


def calculate_rsi(closes, period=14):
    """
    计算RSI指标
    使用Wilder平滑法（指数移动平均）
    """
    result = {}
    
    if len(closes) >= period + 1:
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # 使用Wilder平滑法（类似于EMA，但用period而非2/(period+1)）
        # 第一个RS使用简单平均
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        # 如果有更多数据，使用Wilder平滑
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss != 0:
            rs = avg_gain / avg_loss
            result['rsi'] = float(100 - (100 / (1 + rs)))
        else:
            result['rsi'] = 100.0
    
    return result

