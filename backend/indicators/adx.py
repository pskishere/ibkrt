# -*- coding: utf-8 -*-
"""
ADX（平均趋向指标）计算
Average Directional Index
包括 +DI、-DI、ADX
"""

import numpy as np


def _wilder_smooth(data, period):
    """
    Wilder平滑法（返回最终值）
    """
    if len(data) < period:
        return 0.0
    
    # 第一个值使用简单平均
    smoothed = np.mean(data[:period])
    
    # 后续值使用Wilder平滑
    for i in range(period, len(data)):
        smoothed = (smoothed * (period - 1) + data[i]) / period
    
    return smoothed


def _wilder_smooth_series(data, period):
    """
    Wilder平滑法（返回完整序列）
    用于高效计算ADX，避免重复计算
    """
    if len(data) < period:
        return []
    
    smoothed_series = []
    
    # 第一个值使用简单平均
    smoothed = np.mean(data[:period])
    smoothed_series.append(smoothed)
    
    # 后续值使用Wilder平滑（增量计算）
    for i in range(period, len(data)):
        smoothed = (smoothed * (period - 1) + data[i]) / period
        smoothed_series.append(smoothed)
    
    return smoothed_series


def calculate_adx(closes, highs, lows, period=14):
    """
    计算ADX指标
    +DI: 上升方向指标
    -DI: 下降方向指标
    ADX: 平均趋向指标（趋势强度）
    使用标准的Wilder平滑法计算DX序列的ADX
    """
    result = {}
    
    if len(closes) < period * 2:
        return result
    
    # 计算+DM和-DM
    plus_dm = []
    minus_dm = []
    tr_list = []
    
    for i in range(1, len(closes)):
        high_diff = highs[i] - highs[i-1]
        low_diff = lows[i-1] - lows[i]
        
        # +DM
        if high_diff > low_diff and high_diff > 0:
            plus_dm.append(high_diff)
        else:
            plus_dm.append(0)
        
        # -DM
        if low_diff > high_diff and low_diff > 0:
            minus_dm.append(low_diff)
        else:
            minus_dm.append(0)
        
        # TR (True Range)
        high_low = highs[i] - lows[i]
        high_close = abs(highs[i] - closes[i-1])
        low_close = abs(lows[i] - closes[i-1])
        tr_list.append(max(high_low, high_close, low_close))
    
    if len(tr_list) < period * 2:
        return result
    
    # 使用Wilder平滑
    smoothed_plus_dm = _wilder_smooth(plus_dm, period)
    smoothed_minus_dm = _wilder_smooth(minus_dm, period)
    smoothed_tr = _wilder_smooth(tr_list, period)
    
    # 计算+DI和-DI
    if smoothed_tr != 0:
        plus_di = (smoothed_plus_dm / smoothed_tr) * 100
        minus_di = (smoothed_minus_dm / smoothed_tr) * 100
        
        result['plus_di'] = float(plus_di)
        result['minus_di'] = float(minus_di)
        
        # 计算DX序列（用于计算ADX）- 使用增量计算优化性能
        # 一次性计算所有时刻的平滑值，避免重复计算（O(n)而非O(n²)）
        smoothed_pdm_series = _wilder_smooth_series(plus_dm, period)
        smoothed_mdm_series = _wilder_smooth_series(minus_dm, period)
        smoothed_tr_series = _wilder_smooth_series(tr_list, period)
        
        dx_values = []
        for i in range(len(smoothed_tr_series)):
            smooth_tr_val = smoothed_tr_series[i]
            
            if smooth_tr_val != 0:
                pdi = (smoothed_pdm_series[i] / smooth_tr_val) * 100
                mdi = (smoothed_mdm_series[i] / smooth_tr_val) * 100
                di_sum = pdi + mdi
                
                if di_sum != 0:
                    dx = (abs(pdi - mdi) / di_sum) * 100
                    dx_values.append(dx)
        
        # 对DX序列进行Wilder平滑得到ADX
        if len(dx_values) >= period:
            adx = _wilder_smooth(dx_values, period)
            result['adx'] = float(adx)
            
            # ADX信号判断
            if adx > 25:
                result['adx_signal'] = 'strong_trend'  # 强趋势
            elif adx > 20:
                result['adx_signal'] = 'trend'  # 趋势
            else:
                result['adx_signal'] = 'weak_trend'  # 弱趋势或无趋势
            
            # 趋势方向
            if plus_di > minus_di:
                result['trend_direction'] = 'up'
            else:
                result['trend_direction'] = 'down'
    
    return result
