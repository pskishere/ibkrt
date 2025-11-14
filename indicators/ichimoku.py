# -*- coding: utf-8 -*-
"""
Ichimoku云图指标计算
"""

import numpy as np


def calculate_ichimoku_cloud(highs, lows, closes):
    """
    计算Ichimoku云图指标
    """
    result = {}
    
    # 确保有足够的数据点
    if len(closes) < 52:
        return result
        
    # 转换线 (Tenkan-sen) - 9日周期 (高+低)/2
    period_9 = 9
    tenkan_sen = (np.max(highs[-period_9:]) + np.min(lows[-period_9:])) / 2
    result['ichimoku_tenkan_sen'] = float(tenkan_sen)
    
    # 基准线 (Kijun-sen) - 26日周期 (高+低)/2
    period_26 = 26
    if len(closes) >= period_26:
        kijun_sen = (np.max(highs[-period_26:]) + np.min(lows[-period_26:])) / 2
        result['ichimoku_kijun_sen'] = float(kijun_sen)
        
        # 先行跨度A (Senkou Span A) - (转换线+基准线)/2，向前推26日
        senkou_span_a = (tenkan_sen + kijun_sen) / 2
        result['ichimoku_senkou_span_a'] = float(senkou_span_a)
        
    # 先行跨度B (Senkou Span B) - 52日周期 (高+低)/2，向前推26日
    period_52 = 52
    if len(closes) >= period_52:
        senkou_span_b = (np.max(highs[-period_52:]) + np.min(lows[-period_52:])) / 2
        result['ichimoku_senkou_span_b'] = float(senkou_span_b)
        
    # 迟行跨度 (Chikou Span) - 当前收盘价，向后推26日
    if len(closes) >= period_26:
        result['ichimoku_chikou_span'] = float(closes[-period_26])
        
    return result

