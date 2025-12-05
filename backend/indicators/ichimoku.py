# -*- coding: utf-8 -*-
"""
Ichimoku Cloud (一目均衡表) 指标计算
按照富途公式实现：
CL = (HHV(H,SHORT) + LLV(L,SHORT)) / 2
DL = (HHV(H,MID) + LLV(L,MID)) / 2
LL = REFX(C,MID)
A = REF((CL+DL)/2, MID)
B = REF((LLV(L,LONG) + HHV(H,LONG))/2, MID)
"""

import numpy as np

def calculate_ichimoku(closes, highs, lows, short=9, mid=26, long_period=52):
    """
    计算Ichimoku Cloud指标（按照富途公式）
    
    参数:
    closes: 收盘价数组
    highs: 最高价数组
    lows: 最低价数组
    short: 短期周期，默认9
    mid: 中期周期，默认26
    long_period: 长期周期，默认52
    
    返回:
    dict: 包含Tenkan-sen, Kijun-sen, Senkou Span A, Senkou Span B, Chikou Span等
    """
    result = {}
    
    # 确保数据长度足够
    # 需要至少long_period个数据点来计算Senkou Span B
    if len(closes) < long_period:
        return result
    
    n = len(closes)
    
    # 1. CL (转换线/Tenkan-sen): (HHV(H,SHORT) + LLV(L,SHORT)) / 2
    cl_values = []
    for i in range(n):
        if i < short - 1:
            cl_values.append(np.nan)
        else:
            period_highs = highs[i - short + 1:i + 1]
            period_lows = lows[i - short + 1:i + 1]
            hhv = np.max(period_highs)
            llv = np.min(period_lows)
            cl = (hhv + llv) / 2
            cl_values.append(cl)
    
    # 2. DL (基准线/Kijun-sen): (HHV(H,MID) + LLV(L,MID)) / 2
    dl_values = []
    for i in range(n):
        if i < mid - 1:
            dl_values.append(np.nan)
        else:
            period_highs = highs[i - mid + 1:i + 1]
            period_lows = lows[i - mid + 1:i + 1]
            hhv = np.max(period_highs)
            llv = np.min(period_lows)
            dl = (hhv + llv) / 2
            dl_values.append(dl)
    
    # 3. LL (延迟线/Chikou Span): REFX(C,MID) - 未来MID期的收盘价
    # REFX(C, MID)[i] = closes[i + MID]，在图表上向后移动MID期绘制
    ll_values = [np.nan] * n
    for i in range(n - mid):
        ll_values[i] = closes[i + mid]  # 未来MID期的收盘价
    
    # 4. A (先行带A/Senkou Span A): REF((CL+DL)/2, MID)
    # REF((CL+DL)/2, MID)[i] = (CL[i-MID] + DL[i-MID]) / 2，在图表上向前移动MID期绘制
    a_values = [np.nan] * n
    for i in range(mid, n):
        cl_idx = i - mid
        dl_idx = i - mid
        if cl_idx >= 0 and dl_idx >= 0:
            if not (np.isnan(cl_values[cl_idx]) or np.isnan(dl_values[dl_idx])):
                a_values[i] = (cl_values[cl_idx] + dl_values[dl_idx]) / 2
    
    # 5. B (先行带B/Senkou Span B): REF((LLV(L,LONG) + HHV(H,LONG))/2, MID)
    # REF((LLV+HHV)/2, MID)[i] = (LLV[i-MID] + HHV[i-MID]) / 2，在图表上向前移动MID期绘制
    b_values = [np.nan] * n
    for i in range(mid + long_period - 1, n):
        # 计算 i - MID 位置的长期最高最低价
        calc_idx = i - mid
        if calc_idx >= long_period - 1:
            period_highs = highs[calc_idx - long_period + 1:calc_idx + 1]
            period_lows = lows[calc_idx - long_period + 1:calc_idx + 1]
            hhv = np.max(period_highs)
            llv = np.min(period_lows)
            b_values[i] = (hhv + llv) / 2
    
    # 返回最新值（用于API）
    # 转换线和基准线：当前时刻的值
    if not np.isnan(cl_values[-1]):
        result['ichimoku_tenkan_sen'] = float(cl_values[-1])
    if not np.isnan(dl_values[-1]):
        result['ichimoku_kijun_sen'] = float(dl_values[-1])
    
    # Senkou Span A：当前时刻的(CL+DL)/2，在图表上向未来偏移26期显示
    # API返回当前计算值，图表绘制时处理偏移
    if not np.isnan(cl_values[-1]) and not np.isnan(dl_values[-1]):
        result['ichimoku_senkou_span_a'] = float((cl_values[-1] + dl_values[-1]) / 2)
    
    # Senkou Span B：当前时刻的52日最高最低中点，在图表上向未来偏移26期显示
    if n >= long_period:
        period52_high = np.max(highs[-long_period:])
        period52_low = np.min(lows[-long_period:])
        result['ichimoku_senkou_span_b'] = float((period52_high + period52_low) / 2)
    
    # Chikou Span：当前收盘价，在图表上向过去偏移26期显示
    result['ichimoku_chikou_span'] = float(closes[-1])
    
    # 计算当前时刻的云层位置（用于价格相对位置判断）
    # 当前时刻的云层应该是26期前计算的A和B值（因为它们向未来偏移了26期）
    # 所以我们需要取索引为 -26-1 的a_values和b_values（如果存在）
    if n >= long_period + mid * 2:
        # 当前云层 = 26期前计算的Senkou Span值
        cloud_idx = -(mid + 1) if len(a_values) >= mid + 1 else -1
        current_a = a_values[cloud_idx] if cloud_idx < 0 and not np.isnan(a_values[cloud_idx]) else None
        current_b = b_values[cloud_idx] if cloud_idx < 0 and not np.isnan(b_values[cloud_idx]) else None
        
        if current_a is not None and current_b is not None:
            result['ichimoku_cloud_top'] = float(max(current_a, current_b))
            result['ichimoku_cloud_bottom'] = float(min(current_a, current_b))
            
            # 判断当前价格相对于云层的位置
            current_price = closes[-1]
            if current_price > result['ichimoku_cloud_top']:
                result['ichimoku_status'] = 'bullish'  # 云上 (看涨)
            elif current_price < result['ichimoku_cloud_bottom']:
                result['ichimoku_status'] = 'bearish'  # 云下 (看跌)
            else:
                result['ichimoku_status'] = 'neutral'  # 云中 (盘整)
    elif n >= long_period + mid:
        # 数据不足时的备用方案：使用最新的a_values和b_values
        current_a = a_values[-1] if not np.isnan(a_values[-1]) else None
        current_b = b_values[-1] if not np.isnan(b_values[-1]) else None
        
        if current_a is not None and current_b is not None:
            result['ichimoku_cloud_top'] = float(max(current_a, current_b))
            result['ichimoku_cloud_bottom'] = float(min(current_a, current_b))
            
            current_price = closes[-1]
            if current_price > result['ichimoku_cloud_top']:
                result['ichimoku_status'] = 'bullish'
            elif current_price < result['ichimoku_cloud_bottom']:
                result['ichimoku_status'] = 'bearish'
            else:
                result['ichimoku_status'] = 'neutral'
    
    # 转换线与基准线交叉信号
    if not np.isnan(cl_values[-1]) and not np.isnan(dl_values[-1]):
        if cl_values[-1] > dl_values[-1]:
            result['ichimoku_tk_cross'] = 'bullish'  # 金叉
        elif cl_values[-1] < dl_values[-1]:
            result['ichimoku_tk_cross'] = 'bearish'  # 死叉
        else:
            result['ichimoku_tk_cross'] = 'neutral'
    
    # 返回完整序列（用于图表绘制）
    result['ichimoku_tenkan_sen_series'] = [float(x) if not np.isnan(x) else None for x in cl_values]
    result['ichimoku_kijun_sen_series'] = [float(x) if not np.isnan(x) else None for x in dl_values]
    result['ichimoku_senkou_span_a_series'] = [float(x) if not np.isnan(x) else None for x in a_values]
    result['ichimoku_senkou_span_b_series'] = [float(x) if not np.isnan(x) else None for x in b_values]
    result['ichimoku_chikou_span_series'] = [float(x) if not np.isnan(x) else None for x in ll_values]
    
    return result
