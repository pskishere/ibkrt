# -*- coding: utf-8 -*-
"""
移动平均线 (MA) 指标计算
包括: SMA (简单移动平均), EMA (指数移动平均), WMA (加权移动平均)
"""

import numpy as np


def calculate_sma_series(data, period):
    """计算SMA序列"""
    return np.convolve(data, np.ones(period), 'valid') / period


def calculate_ema_series(data, period):
    """计算EMA序列"""
    alpha = 2 / (period + 1)
    ema = np.zeros_like(data)
    ema[0] = data[0]
    for i in range(1, len(data)):
        ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
    return ema


def calculate_wma_series(data, period):
    """计算WMA序列"""
    weights = np.arange(1, period + 1)
    wma = []
    for i in range(period - 1, len(data)):
        window = data[i - period + 1:i + 1]
        wma.append(np.dot(window, weights) / weights.sum())
    return np.array(wma)


def calculate_ma(closes):
    """
    计算移动平均线 (SMA, EMA)
    """
    result = {}
    
    # 1. SMA (简单移动平均)
    if len(closes) >= 5:
        result['ma5'] = float(np.mean(closes[-5:]))
    if len(closes) >= 10:
        result['ma10'] = float(np.mean(closes[-10:]))
    if len(closes) >= 20:
        result['ma20'] = float(np.mean(closes[-20:]))
    if len(closes) >= 50:
        result['ma50'] = float(np.mean(closes[-50:]))
    if len(closes) >= 120:
        result['ma120'] = float(np.mean(closes[-120:]))
    if len(closes) >= 200:
        result['ma200'] = float(np.mean(closes[-200:]))
        
    # 2. EMA (指数移动平均) - 对近期价格更敏感
    if len(closes) >= 5:
        ema5 = calculate_ema_series(closes, 5)
        result['ema5'] = float(ema5[-1])
        
    if len(closes) >= 12:
        ema12 = calculate_ema_series(closes, 12)
        result['ema12'] = float(ema12[-1])
        
    if len(closes) >= 20:
        ema20 = calculate_ema_series(closes, 20)
        result['ema20'] = float(ema20[-1])
        
    if len(closes) >= 26:
        ema26 = calculate_ema_series(closes, 26)
        result['ema26'] = float(ema26[-1])
        
    if len(closes) >= 50:
        ema50 = calculate_ema_series(closes, 50)
        result['ema50'] = float(ema50[-1])
    
    # 3. 均线系统状态判断
    if 'ma5' in result and 'ma10' in result and 'ma20' in result:
        ma5, ma10, ma20 = result['ma5'], result['ma10'], result['ma20']
        if ma5 > ma10 > ma20:
            result['ma_trend'] = 'bullish_alignment'  # 多头排列
        elif ma5 < ma10 < ma20:
            result['ma_trend'] = 'bearish_alignment'  # 空头排列
        else:
            result['ma_trend'] = 'entangled'  # 纠缠
            
    return result

