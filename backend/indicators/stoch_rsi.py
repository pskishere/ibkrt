# -*- coding: utf-8 -*-
"""
Stochastic RSI (随机相对强弱指标) 计算
"""

import numpy as np
from .rsi import calculate_rsi

def calculate_stoch_rsi(closes, period=14, smooth_k=3, smooth_d=3):
    """
    计算StochRSI指标
    
    参数:
    - period: RSI周期和Stoch周期 (通常为14)
    - smooth_k: %K平滑周期 (通常为3)
    - smooth_d: %D平滑周期 (通常为3)
    
    返回:
    - stoch_rsi_k: StochRSI的主线
    - stoch_rsi_d: StochRSI的信号线
    """
    result = {}
    
    # 需要足够的数据: RSI周期 + Stoch周期
    if len(closes) < period + period:
        return result
        
    # 1. 计算RSI序列
    # 注意：为了计算准确，我们需要RSI的历史序列
    # 这里我们重新实现一个简单的RSI序列计算，或者修改rsi.py
    # 为了独立性，这里实现RSI序列计算
    
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.zeros_like(closes)
    avg_loss = np.zeros_like(closes)
    rs = np.zeros_like(closes)
    rsi = np.zeros_like(closes)
    
    # 初始平均
    avg_gain[period] = np.mean(gains[:period])
    avg_loss[period] = np.mean(losses[:period])
    
    # Wilder平滑
    for i in range(period + 1, len(closes)):
        avg_gain[i] = (avg_gain[i-1] * (period - 1) + gains[i-1]) / period
        avg_loss[i] = (avg_loss[i-1] * (period - 1) + losses[i-1]) / period
        
    # 计算RSI序列
    # 避免除以零
    with np.errstate(divide='ignore', invalid='ignore'):
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
    # 处理除以零的情况 (loss为0时rsi为100)
    rsi[avg_loss == 0] = 100
    # 前period个数据无效
    rsi[:period] = np.nan
    
    # 2. 计算StochRSI
    # StochRSI = (Current RSI - Lowest Low RSI) / (Highest High RSI - Lowest Low RSI)
    
    stoch_rsi = np.zeros_like(rsi)
    
    for i in range(len(rsi)):
        if i < period + period - 1:
            stoch_rsi[i] = np.nan
            continue
            
        current_rsi = rsi[i]
        # 获取过去period天的RSI窗口
        rsi_window = rsi[i-period+1:i+1]
        
        min_rsi = np.min(rsi_window)
        max_rsi = np.max(rsi_window)
        
        if max_rsi - min_rsi != 0:
            stoch_rsi[i] = (current_rsi - min_rsi) / (max_rsi - min_rsi)
        else:
            stoch_rsi[i] = 0.5 # 如果最大最小相等，取中间值
            
    # 3. 平滑处理得到 %K 和 %D
    # 这里简单使用SMA平滑
    
    # 计算 %K (StochRSI的SMA)
    k_values = np.zeros_like(stoch_rsi)
    for i in range(len(stoch_rsi)):
        if i < period + period + smooth_k - 2:
            k_values[i] = np.nan
            continue
        k_values[i] = np.mean(stoch_rsi[i-smooth_k+1:i+1])
        
    # 计算 %D (%K的SMA)
    d_values = np.zeros_like(k_values)
    for i in range(len(k_values)):
        if i < period + period + smooth_k + smooth_d - 3:
            d_values[i] = np.nan
            continue
        d_values[i] = np.mean(k_values[i-smooth_d+1:i+1])
        
    # 返回最新值 (转换为0-100区间)
    if not np.isnan(k_values[-1]) and not np.isnan(d_values[-1]):
        result['stoch_rsi_k'] = float(k_values[-1] * 100)
        result['stoch_rsi_d'] = float(d_values[-1] * 100)
        
        # 状态判断
        k = result['stoch_rsi_k']
        d = result['stoch_rsi_d']
        
        if k > 80 and d > 80:
            result['stoch_rsi_status'] = 'overbought'
        elif k < 20 and d < 20:
            result['stoch_rsi_status'] = 'oversold'
        else:
            result['stoch_rsi_status'] = 'neutral'
            
    return result
