# -*- coding: utf-8 -*-
"""
缠论分析算法
包括：分型、笔、线段、中枢、买卖点
"""

import numpy as np


def identify_fractals(highs, lows, closes):
    """
    识别分型
    顶分型：中间K线的高点最高，低点也最高
    底分型：中间K线的低点最低，高点也最低
    """
    fractals = {
        'top_fractals': [],  # 顶分型 [(index, price), ...]
        'bottom_fractals': []  # 底分型 [(index, price), ...]
    }
    
    if len(closes) < 3:
        return fractals
    
    # 遍历所有可能的3根K线组合
    for i in range(1, len(closes) - 1):
        prev_high = highs[i-1]
        prev_low = lows[i-1]
        curr_high = highs[i]
        curr_low = lows[i]
        next_high = highs[i+1]
        next_low = lows[i+1]
        
        # 顶分型：中间K线的高点最高
        if curr_high > prev_high and curr_high > next_high:
            fractals['top_fractals'].append({
                'index': i,
                'price': float(curr_high),
                'date_index': i
            })
        
        # 底分型：中间K线的低点最低
        if curr_low < prev_low and curr_low < next_low:
            fractals['bottom_fractals'].append({
                'index': i,
                'price': float(curr_low),
                'date_index': i
            })
    
    return fractals


def identify_strokes(fractals, closes):
    """
    识别笔
    笔：连接相邻的顶分型和底分型
    优化版：降低最小幅度要求，从0.5%降为0.3%
    """
    strokes = []
    
    top_fractals = fractals.get('top_fractals', [])
    bottom_fractals = fractals.get('bottom_fractals', [])
    
    if not top_fractals and not bottom_fractals:
        return strokes
    
    # 合并所有分型并按索引排序
    all_fractals = []
    for tf in top_fractals:
        all_fractals.append({
            'index': tf['index'],
            'price': tf['price'],
            'type': 'top'
        })
    for bf in bottom_fractals:
        all_fractals.append({
            'index': bf['index'],
            'price': bf['price'],
            'type': 'bottom'
        })
    
    # 按索引排序
    all_fractals.sort(key=lambda x: x['index'])
    
    # 确保分型交替出现（顶分型和底分型交替）
    valid_fractals = []
    for i, f in enumerate(all_fractals):
        if i == 0:
            valid_fractals.append(f)
        else:
            # 确保分型类型交替
            if f['type'] != valid_fractals[-1]['type']:
                # 检查价格是否满足笔的条件（降低幅度要求）
                price_diff = abs(f['price'] - valid_fractals[-1]['price'])
                price_pct = (price_diff / valid_fractals[-1]['price']) * 100
                # 从0.5%降低到0.3%的幅度才认为是有效笔（优化：更宽松）
                if price_pct >= 0.3:
                    valid_fractals.append(f)
    
    # 生成笔
    for i in range(len(valid_fractals) - 1):
        start = valid_fractals[i]
        end = valid_fractals[i + 1]
        
        stroke_type = 'up' if end['price'] > start['price'] else 'down'
        
        strokes.append({
            'start_index': start['index'],
            'end_index': end['index'],
            'start_price': float(start['price']),
            'end_price': float(end['price']),
            'type': stroke_type,
            'length': end['index'] - start['index'],
            'price_change': float(end['price'] - start['price']),
            'price_change_pct': float(((end['price'] - start['price']) / start['price']) * 100)
        })
    
    return strokes


def identify_segments(strokes, closes):
    """
    识别线段
    线段：由笔组成的更大结构
    优化版：在数据有限时降低要求，至少2笔即可形成线段
    """
    segments = []
    
    # 降低最小笔数要求：从3笔降为2笔
    if len(strokes) < 2:
        return segments
    
    # 简化的线段识别：寻找连续的同向笔
    i = 0
    while i < len(strokes) - 1:
        # 检查是否有2笔以上的同向或交替结构
        segment_strokes = [strokes[i]]
        
        # 尝试扩展线段
        j = i + 1
        while j < len(strokes):
            # 检查是否满足线段条件（笔的方向变化或延续）
            if len(segment_strokes) >= 2:
                # 检查是否有明显的转折
                prev_type = segment_strokes[-2]['type']
                curr_type = segment_strokes[-1]['type']
                next_type = strokes[j]['type']
                
                # 如果出现明显的反向，可能形成新线段
                if prev_type == curr_type and curr_type != next_type:
                    break
            
            segment_strokes.append(strokes[j])
            j += 1
            
            # 最多包含5笔
            if len(segment_strokes) >= 5:
                break
        
        # 如果至少有2笔，形成线段（优化：从3笔降为2笔）
        if len(segment_strokes) >= 2:
            start_stroke = segment_strokes[0]
            end_stroke = segment_strokes[-1]
            
            # 判断线段方向
            segment_type = 'up' if end_stroke['end_price'] > start_stroke['start_price'] else 'down'
            
            segments.append({
                'start_index': start_stroke['start_index'],
                'end_index': end_stroke['end_index'],
                'start_price': float(start_stroke['start_price']),
                'end_price': float(end_stroke['end_price']),
                'type': segment_type,
                'stroke_count': len(segment_strokes),
                'price_change': float(end_stroke['end_price'] - start_stroke['start_price']),
                'price_change_pct': float(((end_stroke['end_price'] - start_stroke['start_price']) / start_stroke['start_price']) * 100)
            })
        
        i = j
    
    return segments


def identify_central_banks(segments, closes):
    """
    识别中枢
    中枢：价格震荡的区间
    优化版：支持2个线段的重叠（宽松模式），同时保留3个线段的标准模式
    """
    central_banks = []
    
    if len(segments) < 2:
        return central_banks
    
    # 优先使用3线段标准模式
    if len(segments) >= 3:
        for i in range(len(segments) - 2):
            seg1 = segments[i]
            seg2 = segments[i + 1]
            seg3 = segments[i + 2]
            
            # 计算三个线段的价格重叠区间
            seg1_range = (min(seg1['start_price'], seg1['end_price']),
                          max(seg1['start_price'], seg1['end_price']))
            seg2_range = (min(seg2['start_price'], seg2['end_price']),
                          max(seg2['start_price'], seg2['end_price']))
            seg3_range = (min(seg3['start_price'], seg3['end_price']),
                          max(seg3['start_price'], seg3['end_price']))
            
            # 计算重叠区间
            overlap_high = min(seg1_range[1], seg2_range[1], seg3_range[1])
            overlap_low = max(seg1_range[0], seg2_range[0], seg3_range[0])
            
            # 如果有重叠，形成中枢
            if overlap_high > overlap_low:
                start_idx = min(seg1['start_index'], seg2['start_index'], seg3['start_index'])
                end_idx = max(seg1['end_index'], seg2['end_index'], seg3['end_index'])
                
                central_banks.append({
                    'start_index': start_idx,
                    'end_index': end_idx,
                    'high': float(overlap_high),
                    'low': float(overlap_low),
                    'center': float((overlap_high + overlap_low) / 2),
                    'width': float(overlap_high - overlap_low),
                    'width_pct': float(((overlap_high - overlap_low) / overlap_low) * 100),
                    'segment_count': 3,
                    'type': 'standard'  # 标准3线段中枢
                })
    
    # 如果标准模式找不到中枢，使用2线段宽松模式（仅在数据有限时）
    if len(central_banks) == 0 and len(segments) >= 2:
        for i in range(len(segments) - 1):
            seg1 = segments[i]
            seg2 = segments[i + 1]
            
            # 只有当两个线段方向相反时才考虑形成中枢
            if seg1['type'] != seg2['type']:
                seg1_range = (min(seg1['start_price'], seg1['end_price']),
                              max(seg1['start_price'], seg1['end_price']))
                seg2_range = (min(seg2['start_price'], seg2['end_price']),
                              max(seg2['start_price'], seg2['end_price']))
                
                # 计算重叠区间
                overlap_high = min(seg1_range[1], seg2_range[1])
                overlap_low = max(seg1_range[0], seg2_range[0])
                
                # 如果有重叠且幅度足够（至少1%）
                if overlap_high > overlap_low:
                    width_pct = ((overlap_high - overlap_low) / overlap_low) * 100
                    if width_pct >= 1.0:  # 至少1%的宽度才认为是有效中枢
                        start_idx = min(seg1['start_index'], seg2['start_index'])
                        end_idx = max(seg1['end_index'], seg2['end_index'])
                        
                        central_banks.append({
                            'start_index': start_idx,
                            'end_index': end_idx,
                            'high': float(overlap_high),
                            'low': float(overlap_low),
                            'center': float((overlap_high + overlap_low) / 2),
                            'width': float(overlap_high - overlap_low),
                            'width_pct': float(width_pct),
                            'segment_count': 2,
                            'type': 'relaxed'  # 宽松2线段中枢
                        })
    
    return central_banks


def identify_trend_type(segments, closes):
    """
    识别走势类型
    上涨、下跌、盘整
    """
    if len(segments) < 2:
        return 'unknown'
    
    # 分析最近几个线段的方向
    recent_segments = segments[-3:] if len(segments) >= 3 else segments
    
    up_count = sum(1 for s in recent_segments if s['type'] == 'up')
    down_count = sum(1 for s in recent_segments if s['type'] == 'down')
    
    if up_count > down_count:
        return 'up'
    elif down_count > up_count:
        return 'down'
    else:
        return 'consolidation'


def identify_trading_points(segments, central_banks, closes):
    """
    识别买卖点
    一买、二买、三买、一卖、二卖、三卖
    """
    trading_points = {
        'buy_points': [],  # 买入点
        'sell_points': []  # 卖出点
    }
    
    if len(segments) < 2:
        return trading_points
    
    current_price = float(closes[-1])
    
    # 简化的买卖点识别
    if len(segments) >= 2:
        last_segment = segments[-1]
        prev_segment = segments[-2]
        
        # 如果前一段是下跌，当前段是上涨，可能是一买
        if prev_segment['type'] == 'down' and last_segment['type'] == 'up':
            trading_points['buy_points'].append({
                'type': '一买',
                'price': float(last_segment['start_price']),
                'index': last_segment['start_index'],
                'description': '下跌趋势后的第一个底分型'
            })
        
        # 如果前一段是上涨，当前段是下跌，可能是一卖
        if prev_segment['type'] == 'up' and last_segment['type'] == 'down':
            trading_points['sell_points'].append({
                'type': '一卖',
                'price': float(last_segment['start_price']),
                'index': last_segment['start_index'],
                'description': '上涨趋势后的第一个顶分型'
            })
    
    # 检查中枢相关的买卖点
    if central_banks:
        latest_cb = central_banks[-1]
        
        # 如果价格突破中枢上沿，可能是三买
        if current_price > latest_cb['high']:
            trading_points['buy_points'].append({
                'type': '三买',
                'price': float(latest_cb['high']),
                'index': latest_cb['end_index'],
                'description': '突破中枢上沿后的回踩买点'
            })
        
        # 如果价格跌破中枢下沿，可能是三卖
        if current_price < latest_cb['low']:
            trading_points['sell_points'].append({
                'type': '三卖',
                'price': float(latest_cb['low']),
                'index': latest_cb['end_index'],
                'description': '跌破中枢下沿后的反弹卖点'
            })
    
    return trading_points


def get_chanlun_status(fractals, strokes, segments, central_banks, closes):
    """
    获取当前缠论状态摘要
    """
    result = {}
    
    current_price = float(closes[-1])
    
    # 最近的分型
    top_fractals = fractals.get('top_fractals', [])
    bottom_fractals = fractals.get('bottom_fractals', [])
    
    if top_fractals:
        latest_top = top_fractals[-1]
        result['latest_top_fractal'] = {
            'price': latest_top['price'],
            'distance_pct': float(((current_price - latest_top['price']) / latest_top['price']) * 100)
        }
    
    if bottom_fractals:
        latest_bottom = bottom_fractals[-1]
        result['latest_bottom_fractal'] = {
            'price': latest_bottom['price'],
            'distance_pct': float(((current_price - latest_bottom['price']) / latest_bottom['price']) * 100)
        }
    
    # 最近的笔
    if strokes:
        latest_stroke = strokes[-1]
        result['latest_stroke'] = {
            'type': latest_stroke['type'],
            'start_price': latest_stroke['start_price'],
            'end_price': latest_stroke['end_price'],
            'price_change_pct': latest_stroke['price_change_pct']
        }
    
    # 最近的线段
    if segments:
        latest_segment = segments[-1]
        result['latest_segment'] = {
            'type': latest_segment['type'],
            'start_price': latest_segment['start_price'],
            'end_price': latest_segment['end_price'],
            'price_change_pct': latest_segment['price_change_pct']
        }
    
    # 最近的中枢
    if central_banks:
        latest_cb = central_banks[-1]
        position = 'above' if current_price > latest_cb['high'] else ('below' if current_price < latest_cb['low'] else 'inside')
        result['latest_central_bank'] = {
            'high': latest_cb['high'],
            'low': latest_cb['low'],
            'center': latest_cb['center'],
            'width_pct': latest_cb['width_pct'],
            'position': position
        }
    
    # 统计信息
    result['fractal_count'] = {
        'top': len(top_fractals),
        'bottom': len(bottom_fractals),
        'total': len(top_fractals) + len(bottom_fractals)
    }
    result['stroke_count'] = len(strokes)
    result['segment_count'] = len(segments)
    result['central_bank_count'] = len(central_banks)
    
    return result


def calculate_chanlun_analysis(closes, highs, lows, volumes):
    """
    计算缠论分析
    包括：分型、笔、线段、中枢、买卖点
    优化版：针对63日K线数据优化，降低各项最小要求
    """
    result = {}
    
    # 降低最小数据量要求：从10根降为5根
    if len(closes) < 5:
        return result
    
    # 1. 识别分型（顶分型和底分型）
    fractals = identify_fractals(highs, lows, closes)
    result['fractals'] = fractals
    
    # 2. 识别笔（优化：最小幅度0.3%）
    strokes = identify_strokes(fractals, closes)
    result['strokes'] = strokes
    
    # 3. 识别线段（优化：至少2笔）
    segments = identify_segments(strokes, closes)
    result['segments'] = segments
    
    # 4. 识别中枢（优化：支持2线段模式）
    central_banks = identify_central_banks(segments, closes)
    result['central_banks'] = central_banks
    
    # 5. 判断当前走势类型
    trend_type = identify_trend_type(segments, closes)
    result['trend_type'] = trend_type
    
    # 6. 识别买卖点
    trading_points = identify_trading_points(segments, central_banks, closes)
    result['trading_points'] = trading_points
    
    # 7. 当前状态摘要
    current_status = get_chanlun_status(fractals, strokes, segments, central_banks, closes)
    result.update(current_status)
    
    # 8. 添加数据充足性评估
    result['data_adequacy'] = {
        'total_bars': len(closes),
        'fractal_count': len(fractals.get('top_fractals', [])) + len(fractals.get('bottom_fractals', [])),
        'stroke_count': len(strokes),
        'segment_count': len(segments),
        'central_bank_count': len(central_banks),
        'is_adequate': len(closes) >= 30,  # 至少30根K线认为数据充足
        'recommendation': '数据充足' if len(closes) >= 50 else '数据有限，建议谨慎使用' if len(closes) >= 30 else '数据不足，结果仅供参考'
    }
    
    return result

