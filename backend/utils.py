#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
工具函数模块 - 通用辅助函数
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from .settings import logger


def format_candle_data(hist_data: List[Dict]) -> List[Dict]:
    """
    格式化K线数据
    
    Args:
        hist_data: 历史K线数据列表
        
    Returns:
        格式化后的K线数据列表
    """
    formatted_candles = []
    
    if not hist_data:
        return formatted_candles
    
    for bar in hist_data:
        date_str = bar.get('date', '')
        try:
            if len(date_str) == 8:
                dt = datetime.strptime(date_str, '%Y%m%d')
                time_str = dt.strftime('%Y-%m-%d')
            elif ' ' in date_str:
                dt = datetime.strptime(date_str, '%Y%m%d %H:%M:%S')
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                time_str = date_str
        except Exception as e:
            logger.warning(f"日期解析失败: {date_str}, 错误: {e}")
            time_str = date_str
        
        formatted_candles.append({
            'time': time_str,
            'open': float(bar.get('open', 0)),
            'high': float(bar.get('high', 0)),
            'low': float(bar.get('low', 0)),
            'close': float(bar.get('close', 0)),
            'volume': int(bar.get('volume', 0)),
        })
    
    return formatted_candles


def extract_stock_name(stock_info) -> Optional[str]:
    """
    从股票信息中提取股票名称
    
    Args:
        stock_info: 股票信息（可能是dict或list）
        
    Returns:
        股票名称，如果没有则返回None
    """
    stock_name = None
    
    if isinstance(stock_info, dict):
        stock_name = stock_info.get('longName', '')
    elif isinstance(stock_info, list) and len(stock_info) > 0:
        stock_data = stock_info[0]
        if isinstance(stock_data, dict):
            stock_name = stock_data.get('longName', '')
    
    if stock_name and stock_name.strip():
        return stock_name.strip()
    
    return None


def create_error_response(error_info: Dict) -> Tuple[Dict, int]:
    """
    创建错误响应
    
    Args:
        error_info: 错误信息字典，包含code和message
        
    Returns:
        (响应字典, HTTP状态码)
    """
    return {
        'success': False,
        'error_code': error_info['code'],
        'message': error_info['message']
    }, 400


def create_success_response(
    indicators: Dict,
    signals: Dict,
    candles: List[Dict],
    ai_analysis: Optional[str] = None,
    model: Optional[str] = None
) -> Dict:
    """
    创建成功响应
    
    Args:
        indicators: 技术指标
        signals: 交易信号
        candles: K线数据
        ai_analysis: AI分析结果（可选）
        model: AI模型名称（可选）
        
    Returns:
        响应字典
    """
    result = {
        'success': True,
        'indicators': indicators,
        'signals': signals,
        'candles': candles
    }
    
    if ai_analysis:
        result['ai_analysis'] = ai_analysis
        result['model'] = model
        result['ai_available'] = True
    else:
        result['ai_available'] = False
    
    return result
