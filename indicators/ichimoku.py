# -*- coding: utf-8 -*-
"""
Ichimoku Cloud (一目均衡表) 指标计算
"""

import numpy as np

def calculate_ichimoku(closes, highs, lows):
    """
    计算Ichimoku Cloud指标
    
    参数:
    closes: 收盘价数组
    highs: 最高价数组
    lows: 最低价数组
    
    返回:
    dict: 包含Tenkan-sen, Kijun-sen, Senkou Span A, Senkou Span B, Chikou Span等
    """
    result = {}
    
    # 确保数据长度足够
    # 需要至少52个数据点来计算Senkou Span B
    if len(closes) < 52:
        return result
        
    # 1. Tenkan-sen (转换线): (9日最高 + 9日最低) / 2
    period9_high = np.max(highs[-9:])
    period9_low = np.min(lows[-9:])
    tenkan_sen = (period9_high + period9_low) / 2
    result['ichimoku_tenkan_sen'] = float(tenkan_sen)
    
    # 2. Kijun-sen (基准线): (26日最高 + 26日最低) / 2
    period26_high = np.max(highs[-26:])
    period26_low = np.min(lows[-26:])
    kijun_sen = (period26_high + period26_low) / 2
    result['ichimoku_kijun_sen'] = float(kijun_sen)
    
    # 3. Senkou Span A (先行带A): (转换线 + 基准线) / 2
    # 注意：这是当前时刻计算出的值，但在图表上通常前移26个周期绘制
    # 这里我们返回当前计算出的值，前端绘制时需要注意偏移
    senkou_span_a = (tenkan_sen + kijun_sen) / 2
    result['ichimoku_senkou_span_a'] = float(senkou_span_a)
    
    # 4. Senkou Span B (先行带B): (52日最高 + 52日最低) / 2
    # 同样，图表上通常前移26个周期
    period52_high = np.max(highs[-52:])
    period52_low = np.min(lows[-52:])
    senkou_span_b = (period52_high + period52_low) / 2
    result['ichimoku_senkou_span_b'] = float(senkou_span_b)
    
    # 5. Chikou Span (迟行带): 当前收盘价
    # 在图表上后移26个周期绘制
    # 这里我们返回当前收盘价作为Chikou Span的当前值
    result['ichimoku_chikou_span'] = float(closes[-1])
    
    # 6. 信号判断
    current_price = closes[-1]
    
    # 为了准确判断，我们需要计算26天前的 Span A 和 Span B (即当前的云层)
    if len(closes) >= 52 + 26:
        # 计算26天前的 Tenkan 和 Kijun
        prev26_highs_9 = highs[-9-26:-26]
        prev26_lows_9 = lows[-9-26:-26]
        prev26_tenkan = (np.max(prev26_highs_9) + np.min(prev26_lows_9)) / 2
        
        prev26_highs_26 = highs[-26-26:-26]
        prev26_lows_26 = lows[-26-26:-26]
        prev26_kijun = (np.max(prev26_highs_26) + np.min(prev26_lows_26)) / 2
        
        # 26天前的 Span A (即当前的云层顶/底之一)
        current_cloud_span_a = (prev26_tenkan + prev26_kijun) / 2
        
        # 26天前的 Span B (即当前的云层顶/底之二)
        prev26_highs_52 = highs[-52-26:-26]
        prev26_lows_52 = lows[-52-26:-26]
        current_cloud_span_b = (np.max(prev26_highs_52) + np.min(prev26_lows_52)) / 2
        
        result['ichimoku_cloud_top'] = float(max(current_cloud_span_a, current_cloud_span_b))
        result['ichimoku_cloud_bottom'] = float(min(current_cloud_span_a, current_cloud_span_b))
        
        # 判断位置
        if current_price > result['ichimoku_cloud_top']:
            result['ichimoku_status'] = 'above_cloud' # 云上 (看涨)
        elif current_price < result['ichimoku_cloud_bottom']:
            result['ichimoku_status'] = 'below_cloud' # 云下 (看跌)
        else:
            result['ichimoku_status'] = 'inside_cloud' # 云中 (盘整)
            
    # 转换线与基准线交叉信号
    if tenkan_sen > kijun_sen:
        result['ichimoku_tk_cross'] = 'bullish' # 金叉
    elif tenkan_sen < kijun_sen:
        result['ichimoku_tk_cross'] = 'bearish' # 死叉
    else:
        result['ichimoku_tk_cross'] = 'neutral'
        
    return result
