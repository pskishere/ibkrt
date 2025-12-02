# -*- coding: utf-8 -*-
"""
Volume Profile (成交量分布) 指标计算
基于可见范围的K线数据估算筹码分布
"""

import numpy as np

def calculate_volume_profile(closes, highs, lows, volumes, bins=24):
    """
    计算成交量分布 (Volume Profile)
    
    参数:
    - bins: 价格分段数量 (默认24)
    
    返回:
    - poc_price: 控制点价格 (Point of Control) - 成交量最大的价格
    - va_high: 价值区域上沿 (Value Area High) - 70%成交量区域
    - va_low: 价值区域下沿 (Value Area Low)
    - profile: 分布数据列表
    """
    result = {}
    
    if len(closes) < 5:
        return result
        
    # 确定价格范围
    min_price = np.min(lows)
    max_price = np.max(highs)
    
    if min_price == max_price:
        return result
        
    # 创建价格分桶
    price_range = max_price - min_price
    bin_size = price_range / bins
    
    # 初始化分桶体积
    profile_volume = np.zeros(bins)
    
    # 遍历每一根K线，将其成交量分配到对应的价格桶中
    # 假设每根K线的成交量均匀分布在High和Low之间
    for i in range(len(closes)):
        h = highs[i]
        l = lows[i]
        v = volumes[i]
        
        if h == l:
            # 如果最高等于最低（如一字板），全部归入该价格所在的桶
            bin_idx = int((h - min_price) / bin_size)
            bin_idx = min(bin_idx, bins - 1) # 防止越界
            profile_volume[bin_idx] += v
        else:
            # 计算该K线跨越的桶的范围
            start_bin = int((l - min_price) / bin_size)
            end_bin = int((h - min_price) / bin_size)
            
            # 防止越界
            start_bin = min(max(0, start_bin), bins - 1)
            end_bin = min(max(0, end_bin), bins - 1)
            
            # 如果跨越多个桶，平均分配
            # 更精确的做法是计算重叠比例，这里简化处理
            num_bins = end_bin - start_bin + 1
            vol_per_bin = v / num_bins
            
            for b in range(start_bin, end_bin + 1):
                profile_volume[b] += vol_per_bin
                
    # 找到POC (Point of Control)
    max_vol_idx = np.argmax(profile_volume)
    poc_price = min_price + (max_vol_idx + 0.5) * bin_size
    
    # 计算价值区域 (Value Area) - 包含70%成交量的区域
    total_volume = np.sum(profile_volume)
    target_volume = total_volume * 0.70
    
    current_volume = profile_volume[max_vol_idx]
    upper_idx = max_vol_idx
    lower_idx = max_vol_idx
    
    # 从POC向两边扩展，直到达到70%
    while current_volume < target_volume:
        # 尝试向上扩展
        next_upper_vol = 0
        if upper_idx < bins - 1:
            next_upper_vol = profile_volume[upper_idx + 1]
            
        # 尝试向下扩展
        next_lower_vol = 0
        if lower_idx > 0:
            next_lower_vol = profile_volume[lower_idx - 1]
            
        # 选择成交量较大的一边扩展
        if next_upper_vol == 0 and next_lower_vol == 0:
            break
            
        if next_upper_vol >= next_lower_vol:
            upper_idx += 1
            current_volume += next_upper_vol
        else:
            lower_idx -= 1
            current_volume += next_lower_vol
            
    va_high = min_price + (upper_idx + 1) * bin_size
    va_low = min_price + lower_idx * bin_size
    
    result['vp_poc'] = float(poc_price)
    result['vp_val'] = float(va_low) # Value Area Low
    result['vp_vah'] = float(va_high) # Value Area High
    
    # 判断当前价格相对于价值区域的位置
    current_price = closes[-1]
    if current_price > va_high:
        result['vp_status'] = 'above_va' # 上方失衡
    elif current_price < va_low:
        result['vp_status'] = 'below_va' # 下方失衡
    else:
        result['vp_status'] = 'inside_va' # 价值区域内平衡
        
    return result
