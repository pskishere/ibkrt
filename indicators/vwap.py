# -*- coding: utf-8 -*-
"""
VWAP（成交量加权平均价）计算
Volume Weighted Average Price
"""

import numpy as np


def calculate_vwap(closes, highs, lows, volumes):
    """
    计算VWAP指标
    VWAP = Σ(典型价格 × 成交量) / Σ(成交量)
    典型价格 = (最高价 + 最低价 + 收盘价) / 3
    
    注意：标准VWAP是当日累计计算，这里计算最近N期的VWAP
    """
    result = {}
    
    if len(closes) < 1:
        return result
    
    # 计算典型价格
    typical_prices = (highs + lows + closes) / 3
    
    # 计算当日VWAP（使用所有可用数据）
    total_pv = np.sum(typical_prices * volumes)
    total_volume = np.sum(volumes)
    
    if total_volume > 0:
        vwap = total_pv / total_volume
        result['vwap'] = float(vwap)
        
        # 当前价格相对VWAP的位置
        current_price = float(closes[-1])
        deviation = ((current_price - vwap) / vwap) * 100
        result['vwap_deviation'] = float(deviation)
        
        # VWAP信号
        if current_price > vwap:
            result['vwap_signal'] = 'above'  # 价格在VWAP之上，多头信号
        elif current_price < vwap:
            result['vwap_signal'] = 'below'  # 价格在VWAP之下，空头信号
        else:
            result['vwap_signal'] = 'at'  # 价格等于VWAP
        
        # 计算最近20期的VWAP（如果数据足够）
        if len(closes) >= 20:
            period = 20
            recent_tp = typical_prices[-period:]
            recent_vol = volumes[-period:]
            vwap_20 = np.sum(recent_tp * recent_vol) / np.sum(recent_vol)
            result['vwap_20'] = float(vwap_20)
    
    return result
