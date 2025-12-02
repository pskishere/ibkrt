# -*- coding: utf-8 -*-
"""
支撑位和压力位计算
"""

import numpy as np


def calculate_support_resistance(closes, highs, lows):
    """
    计算支撑位和压力位
    使用多种方法：pivot点、历史高低点、聚类分析
    """
    result = {}
    current_price = float(closes[-1])
    
    # 方法1: Pivot Points (枢轴点)
    if len(closes) >= 2:
        high = float(highs[-2])
        low = float(lows[-2])
        close = float(closes[-2])
        
        pivot = (high + low + close) / 3
        r1 = 2 * pivot - low
        r2 = pivot + (high - low)
        r3 = high + 2 * (pivot - low)
        s1 = 2 * pivot - high
        s2 = pivot - (high - low)
        s3 = low - 2 * (high - pivot)
        
        result['pivot'] = float(pivot)
        result['pivot_r1'] = float(r1)
        result['pivot_r2'] = float(r2)
        result['pivot_r3'] = float(r3)
        result['pivot_s1'] = float(s1)
        result['pivot_s2'] = float(s2)
        result['pivot_s3'] = float(s3)
    
    # 方法2: 最近N日的高低点
    if len(closes) >= 20:
        # 最近20日高低点
        recent_high = float(np.max(highs[-20:]))
        recent_low = float(np.min(lows[-20:]))
        
        # 最近50日高低点（如果有足够数据）
        if len(closes) >= 50:
            high_50 = float(np.max(highs[-50:]))
            low_50 = float(np.min(lows[-50:]))
            result['resistance_50d_high'] = high_50
            result['support_50d_low'] = low_50
        
        result['resistance_20d_high'] = recent_high
        result['support_20d_low'] = recent_low
    
    # 方法3: 关键价格聚类（找出价格经常触及的区域）
    if len(closes) >= 30:
        # 合并所有价格点
        all_prices = np.concatenate([highs[-30:], lows[-30:], closes[-30:]])
        
        # 使用简单的价格分组来找关键位
        price_range = np.max(all_prices) - np.min(all_prices)
        if price_range > 0:
            # 将价格分成若干区间，找出触及次数最多的区间
            num_bins = 10
            hist, bin_edges = np.histogram(all_prices, bins=num_bins)
            
            # 找出触及次数最多的前几个区间
            top_indices = np.argsort(hist)[-3:]  # 前3个最常触及的区间
            key_levels = []
            
            for idx in top_indices:
                if hist[idx] > 2:  # 至少触及3次
                    level = float((bin_edges[idx] + bin_edges[idx + 1]) / 2)
                    key_levels.append(level)
            
            # 根据当前价格分类为支撑或压力
            resistances = [lvl for lvl in key_levels if lvl > current_price]
            supports = [lvl for lvl in key_levels if lvl < current_price]
            
            if resistances:
                resistances.sort()
                for i, r in enumerate(resistances[:2], 1):  # 最多2个
                    result[f'key_resistance_{i}'] = float(r)
            
            if supports:
                supports.sort(reverse=True)
                for i, s in enumerate(supports[:2], 1):  # 最多2个
                    result[f'key_support_{i}'] = float(s)
    
    # 方法4: 整数关口（心理价位）
    # 找出最近的整数关口（如100, 150, 200等）
    if current_price > 10:
        # 大于10的股票，找5的倍数或10的倍数
        if current_price > 50:
            step = 10
        else:
            step = 5
            
        lower_round = float(np.floor(current_price / step) * step)
        upper_round = float(np.ceil(current_price / step) * step)
        
        if lower_round != current_price:
            result['psychological_support'] = lower_round
        if upper_round != current_price:
            result['psychological_resistance'] = upper_round
    
    return result

