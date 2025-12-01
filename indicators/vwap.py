# -*- coding: utf-8 -*-
"""
VWAP（成交量加权平均价）计算
Volume Weighted Average Price
"""

import numpy as np


def calculate_vwap(closes, highs, lows, volumes, amounts=None, period=None):
    """
    计算VWAP指标（成交量加权平均价）
    
    按照 Futu 公式计算：
    AVGPRICE = TOTALAMOUNT / TOTALVOL
    VWAP = IF(AVGPRICE=0, (C+H+L)/3, AVGPRICE)
    
    即：优先使用成交额/成交量，如果没有成交额则使用典型价格
    
    参数:
        closes: 收盘价数组
        highs: 最高价数组
        lows: 最低价数组
        volumes: 成交量数组
        amounts: 成交额数组（可选，yfinance 不提供此数据）
        period: 计算周期，None表示使用所有历史数据（更接近Futu），
                否则使用最近N个交易日
    
    返回:
        dict: 包含 vwap, vwap_deviation, vwap_signal, vwap_20
    """
    result = {}
    
    if len(closes) < 1:
        return result
    
    # 确定计算周期
    # 默认使用所有历史数据以更接近 Futu 的计算结果
    # 如果指定了 period，则使用滚动窗口
    if period is None:
        # 使用所有历史数据（更接近 Futu）
        calc_closes = closes
        calc_highs = highs
        calc_lows = lows
        calc_volumes = volumes
        calc_amounts = amounts
    else:
        # 使用滚动窗口
        period = min(period, len(closes))
        calc_closes = closes[-period:]
        calc_highs = highs[-period:]
        calc_lows = lows[-period:]
        calc_volumes = volumes[-period:]
        if amounts is not None:
            calc_amounts = amounts[-period:]
        else:
            calc_amounts = None
    
    # 计算每期的平均价格
    # 按照 Futu 公式：如果有成交额数据，使用成交额/成交量；否则使用典型价格
    if calc_amounts is not None and len(calc_amounts) == len(calc_closes):
        # AVGPRICE = TOTALAMOUNT / TOTALVOL (每期)
        # 如果 AVGPRICE=0，则使用 (C+H+L)/3
        avg_prices = np.where(
            (calc_volumes > 0) & (calc_amounts > 0),
            calc_amounts / calc_volumes,  # 有成交额时使用成交额/成交量
            (calc_highs + calc_lows + calc_closes) / 3  # 否则使用典型价格
        )
    else:
        # yfinance 没有成交额数据，使用典型价格 (C+H+L)/3
        avg_prices = (calc_highs + calc_lows + calc_closes) / 3
    
    # 计算 VWAP = Σ(平均价格 × 成交量) / Σ(成交量)
    # 等价于：Σ(成交额) / Σ(成交量)，其中成交额 = 平均价格 × 成交量
    total_amount = np.sum(avg_prices * calc_volumes)
    total_volume = np.sum(calc_volumes)
    
    if total_volume > 0:
        vwap = total_amount / total_volume
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
        
        # 计算最近20期的VWAP作为额外参考
        if len(closes) >= 20:
            period_20 = 20
            recent_tp = (highs[-period_20:] + lows[-period_20:] + closes[-period_20:]) / 3
            recent_vol = volumes[-period_20:]
            vwap_20 = np.sum(recent_tp * recent_vol) / np.sum(recent_vol)
            result['vwap_20'] = float(vwap_20)
        else:
            result['vwap_20'] = float(vwap)
    
    return result
