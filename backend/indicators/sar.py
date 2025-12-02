# -*- coding: utf-8 -*-
"""
SAR（抛物线转向指标）计算
Parabolic Stop and Reverse
"""

import numpy as np


def calculate_sar(closes, highs, lows, af_start=0.02, af_increment=0.02, af_max=0.2):
    """
    计算SAR指标（抛物线转向指标）
    
    参数：
    af_start: 初始加速因子，默认0.02
    af_increment: 加速因子增量，默认0.02
    af_max: 最大加速因子，默认0.2
    
    使用标准算法逐K线计算
    """
    result = {}
    
    if len(closes) < 10:
        return result
    
    # 初始化：判断起始趋势
    if closes[4] > closes[0]:
        is_uptrend = True
        sar = float(np.min(lows[:5]))
        ep = float(np.max(highs[:5]))
    else:
        is_uptrend = False
        sar = float(np.max(highs[:5]))
        ep = float(np.min(lows[:5]))
    
    af = af_start
    
    # 逐K线计算SAR
    for i in range(5, len(closes)):
        # 计算新SAR
        sar = sar + af * (ep - sar)
        
        # 上升趋势
        if is_uptrend:
            # SAR不能高于前两日的低点
            if i >= 2:
                sar = min(sar, lows[i-1], lows[i-2])
            
            # 检查是否转向
            if lows[i] < sar:
                is_uptrend = False
                sar = ep  # 转向后，SAR设为之前的EP
                ep = lows[i]
                af = af_start
            else:
                # 更新EP和AF
                if highs[i] > ep:
                    ep = highs[i]
                    af = min(af + af_increment, af_max)
        
        # 下降趋势
        else:
            # SAR不能低于前两日的高点
            if i >= 2:
                sar = max(sar, highs[i-1], highs[i-2])
            
            # 检查是否转向
            if highs[i] > sar:
                is_uptrend = True
                sar = ep  # 转向后，SAR设为之前的EP
                ep = highs[i]
                af = af_start
            else:
                # 更新EP和AF
                if lows[i] < ep:
                    ep = lows[i]
                    af = min(af + af_increment, af_max)
    
    # 返回最后的SAR值
    result['sar'] = float(sar)
    result['sar_trend'] = 'up' if is_uptrend else 'down'
    result['sar_af'] = float(af)  # 当前加速因子
    result['sar_ep'] = float(ep)  # 当前极值点
    
    # SAR信号判断
    current_price = float(closes[-1])
    if is_uptrend:
        if current_price > sar:
            result['sar_signal'] = 'buy'  # 持续上涨，持有多单
        else:
            result['sar_signal'] = 'sell'  # 跌破SAR，转向信号
    else:
        if current_price < sar:
            result['sar_signal'] = 'sell'  # 持续下跌，持有空单
        else:
            result['sar_signal'] = 'buy'  # 突破SAR，转向信号
    
    # SAR与当前价格的距离（百分比）
    sar_distance = abs((current_price - sar) / current_price) * 100
    result['sar_distance_pct'] = float(sar_distance)
    
    return result
