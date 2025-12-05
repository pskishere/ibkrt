#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
信号生成器模块 - 提取重复的信号生成逻辑
"""

from typing import List, Dict, Optional


def add_ma_signals(signals_list: List[str], indicators: Dict):
    """添加MA均线交叉信号"""
    if 'ma5' in indicators and 'ma20' in indicators:
        if indicators['ma5'] > indicators['ma20']:
            signals_list.append('📈 短期均线(MA5)在长期均线(MA20)之上 - 看涨')
        else:
            signals_list.append('📉 短期均线(MA5)在长期均线(MA20)之下 - 看跌')


def add_rsi_signals(signals_list: List[str], indicators: Dict):
    """添加RSI超买超卖信号"""
    if 'rsi' in indicators:
        rsi = indicators['rsi']
        if rsi < 30:
            signals_list.append(f'🟢 RSI={rsi:.1f} 超卖区域 - 可能反弹')
        elif rsi > 70:
            signals_list.append(f'🔴 RSI={rsi:.1f} 超买区域 - 可能回调')
        else:
            signals_list.append(f'⚪ RSI={rsi:.1f} 中性区域')


def add_bollinger_signals(signals_list: List[str], indicators: Dict):
    """添加布林带信号"""
    if all(k in indicators for k in ['bb_upper', 'bb_lower', 'current_price']):
        price = indicators['current_price']
        upper = indicators['bb_upper']
        lower = indicators['bb_lower']
        
        if price <= lower:
            signals_list.append('🟢 价格触及布林带下轨 - 可能反弹')
        elif price >= upper:
            signals_list.append('🔴 价格触及布林带上轨 - 可能回调')


def add_macd_signals(signals_list: List[str], indicators: Dict):
    """添加MACD信号"""
    if 'macd_histogram' in indicators:
        histogram = indicators['macd_histogram']
        if histogram > 0:
            signals_list.append('📈 MACD柱状图为正 - 看涨')
        else:
            signals_list.append('📉 MACD柱状图为负 - 看跌')


def add_volume_signals(signals_list: List[str], indicators: Dict):
    """添加成交量相关信号"""
    # 成交量比率
    if 'volume_ratio' in indicators:
        ratio = indicators['volume_ratio']
        if ratio > 1.5:
            signals_list.append(f'📊 成交量放大{ratio:.1f}倍 - 趋势加强')
        elif ratio < 0.5:
            signals_list.append(f'📊 成交量萎缩 - 趋势减弱')
    
    # 价量配合
    if 'price_volume_confirmation' in indicators:
        confirmation = indicators['price_volume_confirmation']
        if confirmation == 'bullish':
            signals_list.append('✅ 价涨量增 - 看涨确认，趋势健康')
        elif confirmation == 'bearish':
            signals_list.append('❌ 价跌量增 - 看跌确认，下跌动能强')
        elif confirmation == 'divergence':
            signals_list.append('⚠️ 价量背离 - 趋势可能反转，需谨慎')
    
    # 成交量信号
    if 'volume_signal' in indicators:
        vol_signal = indicators['volume_signal']
        if vol_signal == 'high_volume':
            vol_ratio = indicators.get('volume_ratio', 1.0)
            signals_list.append(f'🔥 高成交量信号 - 当前成交量是均量的{vol_ratio:.1f}倍')
        elif vol_signal == 'low_volume':
            signals_list.append('💤 低成交量信号 - 市场观望情绪浓厚')


def add_trend_signals(signals_list: List[str], indicators: Dict):
    """添加趋势相关信号"""
    if 'trend_direction' in indicators:
        direction = indicators['trend_direction']
        strength = indicators.get('trend_strength', 0)
        
        if direction == 'up':
            if strength > 70:
                signals_list.append(f'🚀 强劲上升趋势 - 趋势强度{strength:.0f}%')
            else:
                signals_list.append(f'📈 温和上升趋势 - 趋势强度{strength:.0f}%')
        elif direction == 'down':
            if strength > 70:
                signals_list.append(f'💥 强劲下降趋势 - 趋势强度{strength:.0f}%')
            else:
                signals_list.append(f'📉 温和下降趋势 - 趋势强度{strength:.0f}%')
        else:
            signals_list.append(f'🔄 震荡行情 - 趋势强度{strength:.0f}%')


def add_advanced_indicator_signals(signals_list: List[str], indicators: Dict):
    """添加高级技术指标信号"""
    # ADX趋势强度
    if 'adx' in indicators:
        adx = indicators['adx']
        if adx > 40:
            signals_list.append(f'💪 ADX={adx:.1f} - 强趋势，跟随趋势交易')
        elif adx > 25:
            signals_list.append(f'⚡ ADX={adx:.1f} - 中等趋势')
        elif adx > 20:
            signals_list.append(f'🌤️ ADX={adx:.1f} - 弱趋势')
        else:
            signals_list.append(f'🌫️ ADX={adx:.1f} - 无明显趋势，适合区间交易')
    
    # SAR抛物线
    if 'sar_signal' in indicators:
        sar_signal = indicators['sar_signal']
        sar_distance = indicators.get('sar_distance_pct', 0)
        if sar_signal == 'bullish':
            signals_list.append(f'🔵 SAR看涨 - 止损位距离{abs(sar_distance):.1f}%')
        elif sar_signal == 'bearish':
            signals_list.append(f'🔴 SAR看跌 - 止损位距离{abs(sar_distance):.1f}%')
    
    # Ichimoku一目均衡表
    if 'ichimoku_status' in indicators:
        status = indicators['ichimoku_status']
        if status == 'above_cloud':
            signals_list.append('☁️ 价格在云层上方 - 看涨')
        elif status == 'below_cloud':
            signals_list.append('☁️ 价格在云层下方 - 看跌')
        else:
            signals_list.append('☁️ 价格在云层内 - 盘整')
    
    # SuperTrend
    if 'supertrend_direction' in indicators:
        st_dir = indicators['supertrend_direction']
        if st_dir == 'up':
            signals_list.append('🟢 SuperTrend看涨信号')
        else:
            signals_list.append('🔴 SuperTrend看跌信号')
    
    # StochRSI
    if 'stoch_rsi_status' in indicators:
        status = indicators['stoch_rsi_status']
        if status == 'oversold':
            signals_list.append('🟢 StochRSI超卖 - 短期可能反弹')
        elif status == 'overbought':
            signals_list.append('🔴 StochRSI超买 - 短期可能回调')


def calculate_risk_level(indicators: Dict) -> Dict:
    """
    计算风险等级
    
    Returns:
        包含level和description的字典
    """
    volatility = indicators.get('volatility_20', 2.0)
    volume_ratio = indicators.get('volume_ratio', 1.0)
    adx = indicators.get('adx', 0)
    
    risk_score = 0
    
    # 波动率贡献
    if volatility > 5:
        risk_score += 3
    elif volatility > 3:
        risk_score += 2
    elif volatility > 2:
        risk_score += 1
    
    # 成交量贡献
    if volume_ratio > 2.0:
        risk_score += 1
    elif volume_ratio < 0.5:
        risk_score += 1
    
    # 趋势强度贡献
    if adx < 20:
        risk_score += 1
    
    # 确定风险等级
    if risk_score >= 5:
        level = 'very_high'
        desc = '极高风险 - 建议谨慎或观望'
    elif risk_score >= 4:
        level = 'high'
        desc = '高风险 - 建议小仓位操作'
    elif risk_score >= 2:
        level = 'medium'
        desc = '中等风险 - 正常仓位'
    elif risk_score >= 1:
        level = 'low'
        desc = '低风险 - 可适当加仓'
    else:
        level = 'very_low'
        desc = '很低风险 - 相对稳健'
    
    return {
        'level': level,
        'description': desc,
        'score': risk_score
    }


def calculate_stop_loss_take_profit(indicators: Dict) -> tuple:
    """
    计算止损和止盈价位
    
    Returns:
        (stop_loss, take_profit)
    """
    current_price = indicators.get('current_price', 0)
    atr = indicators.get('atr', 0)
    volatility = indicators.get('volatility_20', 2.0)
    
    if current_price <= 0:
        return None, None
    
    # 使用ATR或波动率计算
    if atr > 0:
        stop_loss = current_price - (atr * 2)
        take_profit = current_price + (atr * 3)
    else:
        # 基于波动率的fallback计算
        risk_range = current_price * (volatility / 100) * 2
        stop_loss = current_price - risk_range
        take_profit = current_price + (risk_range * 1.5)
    
    # 考虑支撑位和压力位
    if 'pivot_s1' in indicators and indicators['pivot_s1'] > 0:
        stop_loss = max(stop_loss, indicators['pivot_s1'])
    
    if 'pivot_r1' in indicators and indicators['pivot_r1'] > 0:
        take_profit = min(take_profit, indicators['pivot_r1'])
    
    return stop_loss, take_profit
