#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
分析模块 - 技术指标计算、交易信号生成和AI分析
"""

import numpy as np
from datetime import datetime, timedelta
import os
from .settings import logger, OLLAMA_HOST, DEFAULT_AI_MODEL
from .yfinance import get_historical_data, get_fundamental_data

# 技术指标模块导入
from .indicators import (
    calculate_ma, calculate_rsi, calculate_bollinger, calculate_macd,
    calculate_volume, calculate_price_change, calculate_volatility,
    calculate_support_resistance, calculate_kdj, calculate_atr,
    calculate_williams_r, calculate_obv, analyze_trend_strength,
    calculate_fibonacci_retracement, get_trend,
    calculate_cci, calculate_adx, calculate_sar,
    calculate_supertrend, calculate_stoch_rsi, calculate_volume_profile,
    calculate_ichimoku
)
from .indicators.ml_predictions import calculate_ml_predictions


def calculate_technical_indicators(symbol: str, duration: str = '1 M', bar_size: str = '1 day'):
    """
    计算技术指标（基于历史数据）
    返回：移动平均线、RSI、MACD等
    如果证券不存在，返回(None, error_info)
    """
    hist_data, error = get_historical_data(symbol, duration, bar_size)
    
    if error:
        return None, error
    
    if not hist_data or len(hist_data) < 20:
        logger.warning(f"数据不足，无法计算技术指标: {symbol}")
        return None, None
    
    closes = np.array([bar['close'] for bar in hist_data])
    highs = np.array([bar['high'] for bar in hist_data])
    lows = np.array([bar['low'] for bar in hist_data])
    volumes = np.array([bar['volume'] for bar in hist_data])
    
    valid_volumes = volumes[volumes > 0]
    if len(valid_volumes) == 0:
        logger.warning(f"警告: {symbol} 所有成交量数据为 0，成交量相关指标将无法正常计算")
    
    result = {
        'symbol': symbol,
        'current_price': float(closes[-1]),
        'data_points': int(len(closes)),
    }
    
    # 1. 移动平均线 (MA)
    ma_data = calculate_ma(closes)
    result.update(ma_data)
        
    # 2. RSI (相对强弱指标)
    rsi_data = calculate_rsi(closes)
    result.update(rsi_data)
            
    # 3. 布林带 (Bollinger Bands)
    bb_data = calculate_bollinger(closes)
    result.update(bb_data)
        
    # 4. MACD
    macd_data = calculate_macd(closes)
    result.update(macd_data)
                
    # 5. 成交量分析
    volume_data = calculate_volume(volumes)
    result.update(volume_data)
        
    # 6. 价格变化
    price_change_data = calculate_price_change(closes)
    result.update(price_change_data)
        
    # 7. 波动率
    volatility_data = calculate_volatility(closes)
    result.update(volatility_data)
        
    # 8. 支持位和压力位
    support_resistance = calculate_support_resistance(closes, highs, lows)
    result.update(support_resistance)
    
    # 9. KDJ指标（随机指标）
    if len(closes) >= 9:
        kdj = calculate_kdj(closes, highs, lows)
        result.update(kdj)
    
    # 10. ATR（平均真实波幅）
    if len(closes) >= 14:
        atr = calculate_atr(closes, highs, lows)
        result['atr'] = atr
        result['atr_percent'] = float((atr / closes[-1]) * 100)
    
    # 11. 威廉指标（Williams %R）
    if len(closes) >= 14:
        wr = calculate_williams_r(closes, highs, lows)
        result['williams_r'] = wr
    
    # 12. OBV（能量潮指标）
    if len(volumes) >= 20:
        obv = calculate_obv(closes, volumes)
        result['obv_current'] = float(obv[-1]) if len(obv) > 0 else 0.0
        result['obv_trend'] = get_trend(obv[-10:]) if len(obv) >= 10 else 'neutral'
    
    # 13. 趋势强度
    trend_info = analyze_trend_strength(closes, highs, lows)
    result.update(trend_info)

    # 14. 斐波那契回撤位
    fibonacci_levels = calculate_fibonacci_retracement(highs, lows)
    result.update(fibonacci_levels)

    # 16. CCI（顺势指标）
    if len(closes) >= 14:
        cci_data = calculate_cci(closes, highs, lows)
        result.update(cci_data)
    
    # 17. ADX（平均趋向指标）
    if len(closes) >= 28:  # ADX需要period*2的数据
        adx_data = calculate_adx(closes, highs, lows)
        result.update(adx_data)
    
    # 18. SAR（抛物线转向指标）
    if len(closes) >= 10:
        sar_data = calculate_sar(closes, highs, lows)
        result.update(sar_data)

    # 21. SuperTrend (超级趋势)
    if len(closes) >= 11:
        st_data = calculate_supertrend(closes, highs, lows)
        result.update(st_data)
        
    # 22. StochRSI (随机相对强弱指标)
    if len(closes) >= 28:
        stoch_rsi_data = calculate_stoch_rsi(closes)
        result.update(stoch_rsi_data)
        
    # 23. Volume Profile (成交量分布)
    if len(closes) >= 20:
        vp_data = calculate_volume_profile(closes, highs, lows, volumes)
        result.update(vp_data)

    # 24. Ichimoku Cloud (一目均衡表)
    if len(closes) >= 52:
        ichimoku_data = calculate_ichimoku(closes, highs, lows)
        result.update(ichimoku_data)

    # 25. ML预测（机器学习预测，包含成交量分析）
    if len(closes) >= 20 and len(valid_volumes) > 0:
        ml_data = calculate_ml_predictions(closes, highs, lows, volumes)
        result.update(ml_data)

    # 26. 获取基本面数据
    try:
        fundamental_data = get_fundamental_data(symbol)
        if fundamental_data:
            result['fundamental_data'] = fundamental_data
            logger.info(f"已获取基本面数据: {symbol}")
    except Exception as e:
        logger.warning(f"获取基本面数据失败: {symbol}, 错误: {e}")
        result['fundamental_data'] = None
        
    return result, None  # 返回结果和错误信息（无错误为None）


def generate_signals(indicators: dict):
    """
    基于技术指标生成买卖信号
    """
    if not indicators:
        return None
        
    signals = {
        'symbol': indicators.get('symbol'),
        'current_price': indicators.get('current_price'),
        'signals': [],
        'score': 0,  # 综合评分 (-100 to 100)
    }
    
    # 1. MA交叉信号
    if 'ma5' in indicators and 'ma20' in indicators:
        if indicators['ma5'] > indicators['ma20']:
            signals['signals'].append('📈 短期均线(MA5)在长期均线(MA20)之上 - 看涨')
            signals['score'] += 15
        else:
            signals['signals'].append('📉 短期均线(MA5)在长期均线(MA20)之下 - 看跌')
            signals['score'] -= 15
            
    # 2. RSI超买超卖
    if 'rsi' in indicators:
        rsi = indicators['rsi']
        if rsi < 30:
            signals['signals'].append(f'🟢 RSI={rsi:.1f} 超卖区域 - 可能反弹')
            signals['score'] += 25
        elif rsi > 70:
            signals['signals'].append(f'🔴 RSI={rsi:.1f} 超买区域 - 可能回调')
            signals['score'] -= 25
        else:
            signals['signals'].append(f'⚪ RSI={rsi:.1f} 中性区域')
            
    # 3. 布林带
    if all(k in indicators for k in ['bb_upper', 'bb_lower', 'current_price']):
        price = indicators['current_price']
        upper = indicators['bb_upper']
        lower = indicators['bb_lower']
        
        if price <= lower:
            signals['signals'].append('🟢 价格触及布林带下轨 - 可能反弹')
            signals['score'] += 20
        elif price >= upper:
            signals['signals'].append('🔴 价格触及布林带上轨 - 可能回调')
            signals['score'] -= 20
            
    # 4. MACD
    if 'macd_histogram' in indicators:
        histogram = indicators['macd_histogram']
        if histogram > 0:
            signals['signals'].append('📈 MACD柱状图为正 - 看涨')
            signals['score'] += 10
        else:
            signals['signals'].append('📉 MACD柱状图为负 - 看跌')
            signals['score'] -= 10
            
    # 5. 成交量分析（增强版）
    if 'volume_ratio' in indicators:
        ratio = indicators['volume_ratio']
        if ratio > 1.5:
            signals['signals'].append(f'📊 成交量放大{ratio:.1f}倍 - 趋势加强')
            signals['score'] += 10
        elif ratio < 0.5:
            signals['signals'].append(f'📊 成交量萎缩 - 趋势减弱')
    
    # 5.1 价量配合分析
    if 'price_volume_confirmation' in indicators:
        confirmation = indicators['price_volume_confirmation']
        if confirmation == 'bullish':
            signals['signals'].append('✅ 价涨量增 - 看涨确认，趋势健康')
            signals['score'] += 15
        elif confirmation == 'bearish':
            signals['signals'].append('❌ 价跌量增 - 看跌确认，下跌动能强')
            signals['score'] -= 15
        elif confirmation == 'divergence':
            signals['signals'].append('⚠️ 价量背离 - 趋势可能反转，需谨慎')
            signals['score'] -= 10
    
    # 5.2 成交量信号
    if 'volume_signal' in indicators:
        vol_signal = indicators['volume_signal']
        if vol_signal == 'high_volume':
            vol_ratio = indicators.get('volume_ratio', 1.0)
            signals['signals'].append(f'🔥 高成交量信号 - 当前成交量是均量的{vol_ratio:.1f}倍')
        elif vol_signal == 'low_volume':
            signals['signals'].append('💤 低成交量信号 - 市场参与度低，趋势可能不稳固')
    
    # 5.3 OBV趋势确认
    if 'obv_trend' in indicators:
        obv_trend = indicators['obv_trend']
        if obv_trend == 'up':
            signals['signals'].append('📈 OBV上升趋势 - 资金流入，看涨')
            signals['score'] += 10
        elif obv_trend == 'down':
            signals['signals'].append('📉 OBV下降趋势 - 资金流出，看跌')
            signals['score'] -= 10
    
    # 6. 波动率
    if 'volatility_20' in indicators:
        vol = indicators['volatility_20']
        if vol > 3:
            signals['signals'].append(f'⚠️ 高波动率{vol:.1f}% - 风险较大')
        elif vol < 1:
            signals['signals'].append(f'✅ 低波动率{vol:.1f}% - 相对稳定')
    
    # 7. 支撑位和压力位分析
    current_price = indicators.get('current_price')
    if current_price:
        # 检查是否接近关键支撑位
        support_keys = [k for k in indicators.keys() if 'support' in k.lower()]
        resistance_keys = [k for k in indicators.keys() if 'resistance' in k.lower()]
        
        # 找最近的支撑位
        nearest_support = None
        nearest_support_dist = float('inf')
        for key in support_keys:
            support = indicators[key]
            if support < current_price:
                dist = current_price - support
                dist_pct = (dist / current_price) * 100
                if dist_pct < nearest_support_dist:
                    nearest_support = support
                    nearest_support_dist = dist_pct
        
        # 找最近的压力位
        nearest_resistance = None
        nearest_resistance_dist = float('inf')
        for key in resistance_keys:
            resistance = indicators[key]
            if resistance > current_price:
                dist = resistance - current_price
                dist_pct = (dist / current_price) * 100
                if dist_pct < nearest_resistance_dist:
                    nearest_resistance = resistance
                    nearest_resistance_dist = dist_pct
        
        # 根据支撑压力位置给出信号
        if nearest_support and nearest_support_dist < 2:
            signals['signals'].append(f'🟢 接近支撑位${nearest_support:.2f} (距离{nearest_support_dist:.1f}%) - 可能反弹')
            signals['score'] += 15
        
        if nearest_resistance and nearest_resistance_dist < 2:
            signals['signals'].append(f'🔴 接近压力位${nearest_resistance:.2f} (距离{nearest_resistance_dist:.1f}%) - 可能回调')
            signals['score'] -= 15
        
        # 突破信号
        if 'resistance_20d_high' in indicators:
            high_20 = indicators['resistance_20d_high']
            if current_price >= high_20 * 0.99:  # 接近或突破20日高点
                signals['signals'].append(f'🚀 突破20日高点${high_20:.2f} - 强势信号')
                signals['score'] += 20
        
        if 'support_20d_low' in indicators:
            low_20 = indicators['support_20d_low']
            if current_price <= low_20 * 1.01:  # 接近或跌破20日低点
                signals['signals'].append(f'⚠️ 跌破20日低点${low_20:.2f} - 弱势信号')
                signals['score'] -= 20
    
    # 8. KDJ指标
    if all(k in indicators for k in ['kdj_k', 'kdj_d', 'kdj_j']):
        k_val = indicators['kdj_k']
        d_val = indicators['kdj_d']
        j_val = indicators['kdj_j']
        
        if j_val < 20:
            signals['signals'].append(f'🟢 KDJ超卖(J={j_val:.1f}) - 短线买入机会')
            signals['score'] += 15
        elif j_val > 80:
            signals['signals'].append(f'🔴 KDJ超买(J={j_val:.1f}) - 短线卖出信号')
            signals['score'] -= 15
        
        # 金叉死叉
        if k_val > d_val and k_val < 50:
            signals['signals'].append(f'📈 KDJ金叉 - 看涨')
            signals['score'] += 10
        elif k_val < d_val and k_val > 50:
            signals['signals'].append(f'📉 KDJ死叉 - 看跌')
            signals['score'] -= 10
    
    # 9. 威廉指标
    if 'williams_r' in indicators:
        wr = indicators['williams_r']
        if wr < -80:
            signals['signals'].append(f'🟢 威廉指标超卖(WR={wr:.1f}) - 反弹概率大')
            signals['score'] += 12
        elif wr > -20:
            signals['signals'].append(f'🔴 威廉指标超买(WR={wr:.1f}) - 回调概率大')
            signals['score'] -= 12
    
    # 10. OBV趋势
    if 'obv_trend' in indicators:
        obv_trend = indicators['obv_trend']
        price_change = indicators.get('price_change_pct', 0)
        
        if obv_trend == 'up' and price_change > 0:
            signals['signals'].append('📊 量价齐升 - 强势上涨信号')
            signals['score'] += 15
        elif obv_trend == 'down' and price_change < 0:
            signals['signals'].append('📊 量价齐跌 - 弱势下跌信号')
            signals['score'] -= 15
        elif obv_trend == 'up' and price_change < 0:
            signals['signals'].append('⚠️ 量价背离(价跌量升) - 可能见底')
            signals['score'] += 8
        elif obv_trend == 'down' and price_change > 0:
            signals['signals'].append('⚠️ 量价背离(价涨量跌) - 可能见顶')
            signals['score'] -= 8
    
    # 11. 趋势强度分析
    if 'trend_strength' in indicators:
        strength = indicators['trend_strength']
        direction = indicators.get('trend_direction', 'neutral')
        
        if strength > 50:
            if direction == 'up':
                signals['signals'].append(f'🚀 强势上涨趋势(强度{strength:.0f}%) - 顺势做多')
                signals['score'] += 18
            elif direction == 'down':
                signals['signals'].append(f'⚠️ 强势下跌趋势(强度{strength:.0f}%) - 观望或做空')
                signals['score'] -= 18
        elif strength < 25:
            signals['signals'].append(f'📊 趋势不明显(强度{strength:.0f}%) - 震荡行情')
    
    # 12. 连续涨跌分析
    if 'consecutive_up_days' in indicators and 'consecutive_down_days' in indicators:
        up_days = indicators['consecutive_up_days']
        down_days = indicators['consecutive_down_days']
        
        if up_days >= 5:
            signals['signals'].append(f'⚠️ 连续上涨{up_days}天 - 注意获利回吐风险')
            signals['score'] -= 10
        elif down_days >= 5:
            signals['signals'].append(f'🟢 连续下跌{down_days}天 - 可能出现反弹')
            signals['score'] += 10
        elif up_days >= 3:
            signals['signals'].append(f'📈 连续上涨{up_days}天 - 短期强势')
        elif down_days >= 3:
            signals['signals'].append(f'📉 连续下跌{down_days}天 - 短期弱势')
    
    # 13. ATR风险提示
    if 'atr_percent' in indicators:
        atr_pct = indicators['atr_percent']
        if atr_pct > 5:
            signals['signals'].append(f'⚡ 高波动(ATR {atr_pct:.1f}%) - 建议缩小仓位')
        elif atr_pct < 1.5:
            signals['signals'].append(f'✅ 低波动(ATR {atr_pct:.1f}%) - 适合持仓')
    
    # 14. CCI顺势指标
    if 'cci' in indicators:
        cci = indicators['cci']
        cci_signal = indicators.get('cci_signal', 'neutral')
        if cci_signal == 'overbought':
            if cci > 200:
                signals['signals'].append(f'🔴 CCI={cci:.1f} 极度超买 - 强烈回调信号')
                signals['score'] -= 22
            else:
                signals['signals'].append(f'🔴 CCI={cci:.1f} 超买区域 - 可能回调')
                signals['score'] -= 18
        elif cci_signal == 'oversold':
            if cci < -200:
                signals['signals'].append(f'🟢 CCI={cci:.1f} 极度超卖 - 强烈反弹信号')
                signals['score'] += 22
            else:
                signals['signals'].append(f'🟢 CCI={cci:.1f} 超卖区域 - 可能反弹')
                signals['score'] += 18
    
    # 15. ADX趋势强度
    if 'adx' in indicators:
        adx = indicators['adx']
        adx_signal = indicators.get('adx_signal', 'weak_trend')
        plus_di = indicators.get('plus_di', 0)
        minus_di = indicators.get('minus_di', 0)
        
        if adx_signal == 'strong_trend':
            if plus_di > minus_di:
                if adx > 40:
                    signals['signals'].append(f'🚀 ADX={adx:.1f} 极强上涨趋势(+DI={plus_di:.1f}) - 强烈看多')
                    signals['score'] += 25
                else:
                    signals['signals'].append(f'📈 ADX={adx:.1f} 强势上涨趋势(+DI={plus_di:.1f}) - 顺势做多')
                    signals['score'] += 20
            else:
                if adx > 40:
                    signals['signals'].append(f'⚠️ ADX={adx:.1f} 极强下跌趋势(-DI={minus_di:.1f}) - 强烈看空')
                    signals['score'] -= 25
                else:
                    signals['signals'].append(f'📉 ADX={adx:.1f} 强势下跌趋势(-DI={minus_di:.1f}) - 观望或做空')
                    signals['score'] -= 20
        elif adx_signal == 'trend':
            if plus_di > minus_di:
                signals['signals'].append(f'📈 ADX={adx:.1f} 中等上涨趋势 - 可关注')
                signals['score'] += 8
            else:
                signals['signals'].append(f'📉 ADX={adx:.1f} 中等下跌趋势 - 谨慎')
                signals['score'] -= 8
        else:
            signals['signals'].append(f'📊 ADX={adx:.1f} 无明显趋势 - 震荡行情')
    
    # 17. SAR转向信号（抛物线止损）
    if 'sar' in indicators:
        sar = indicators['sar']
        sar_signal = indicators.get('sar_signal', 'hold')
        sar_trend = indicators.get('sar_trend', 'neutral')
        sar_distance = indicators.get('sar_distance_pct', 0)
        
        if sar_signal == 'buy':
            if sar_trend == 'up':
                signals['signals'].append(f'🟢 SAR=${sar:.2f}({sar_distance:.1f}%) 持续看涨')
                signals['score'] += 15
            else:
                signals['signals'].append(f'🚀 SAR=${sar:.2f}({sar_distance:.1f}%) 转向看涨 - 关键买入信号')
                signals['score'] += 20
        elif sar_signal == 'sell':
            if sar_trend == 'down':
                signals['signals'].append(f'🔴 SAR=${sar:.2f}({sar_distance:.1f}%) 持续看跌')
                signals['score'] -= 15
            else:
                signals['signals'].append(f'⚠️ SAR=${sar:.2f}({sar_distance:.1f}%) 转向看跌 - 关键卖出信号')
                signals['score'] -= 20
    
    # 18. SuperTrend信号
    if 'supertrend' in indicators:
        st = indicators['supertrend']
        st_dir = indicators.get('supertrend_direction', 'up')
        current_price = indicators.get('current_price', 0)
        
        if st_dir == 'up':
            if current_price > st:
                signals['signals'].append(f'🟢 SuperTrend支撑(${st:.2f}) - 趋势看涨')
                signals['score'] += 20
        else:
            if current_price < st:
                signals['signals'].append(f'🔴 SuperTrend阻力(${st:.2f}) - 趋势看跌')
                signals['score'] -= 20
                
    # 19. StochRSI信号
    if 'stoch_rsi_k' in indicators and 'stoch_rsi_d' in indicators:
        k = indicators['stoch_rsi_k']
        d = indicators['stoch_rsi_d']
        status = indicators.get('stoch_rsi_status', 'neutral')
        
        if status == 'oversold':
            if k > d: # 金叉
                signals['signals'].append(f'🚀 StochRSI超卖金叉(K={k:.1f}) - 强烈反弹信号')
                signals['score'] += 18
            else:
                signals['signals'].append(f'🟢 StochRSI超卖(K={k:.1f}) - 等待反弹')
                signals['score'] += 10
        elif status == 'overbought':
            if k < d: # 死叉
                signals['signals'].append(f'⚠️ StochRSI超买死叉(K={k:.1f}) - 回调风险大')
                signals['score'] -= 18
            else:
                signals['signals'].append(f'🔴 StochRSI超买(K={k:.1f}) - 警惕回调')
                signals['score'] -= 10
                
    # 20. Volume Profile信号
    if 'vp_poc' in indicators:
        poc = indicators['vp_poc']
        current_price = indicators.get('current_price', 0)
        vp_status = indicators.get('vp_status', 'inside_va')
        
        dist_pct = (current_price - poc) / poc * 100
        
        if abs(dist_pct) < 0.5:
            signals['signals'].append(f'⚖️ 价格在POC(${poc:.2f})附近 - 筹码密集区平衡')
        elif vp_status == 'above_va':
            signals['signals'].append(f'📈 价格在价值区域上方(POC ${poc:.2f}) - 强势失衡')
            signals['score'] += 12
        elif vp_status == 'below_va':
            signals['signals'].append(f'📉 价格在价值区域下方(POC ${poc:.2f}) - 弱势失衡')
            signals['score'] -= 12
    
    # 21. ML预测信号
    if 'ml_trend' in indicators:
        ml_trend = indicators['ml_trend']
        ml_confidence = indicators.get('ml_confidence', 0)
        ml_prediction = indicators.get('ml_prediction', 0)
        
        if ml_confidence > 50:
            if ml_trend == 'up':
                signals['signals'].append(f'🤖 ML预测: 看涨趋势(置信度{ml_confidence:.1f}%, 预期涨幅{ml_prediction*100:.2f}%) - AI看多')
                signals['score'] += 15
            elif ml_trend == 'down':
                signals['signals'].append(f'🤖 ML预测: 看跌趋势(置信度{ml_confidence:.1f}%, 预期跌幅{ml_prediction*100:.2f}%) - AI看空')
                signals['score'] -= 15
            else:
                signals['signals'].append(f'🤖 ML预测: 横盘整理(置信度{ml_confidence:.1f}%) - AI中性')
        elif ml_confidence > 30:
            if ml_trend == 'up':
                signals['signals'].append(f'🤖 ML预测: 轻微看涨(置信度{ml_confidence:.1f}%) - 谨慎乐观')
                signals['score'] += 8
            elif ml_trend == 'down':
                signals['signals'].append(f'🤖 ML预测: 轻微看跌(置信度{ml_confidence:.1f}%) - 谨慎悲观')
                signals['score'] -= 8
            
    # 综合建议
    score = signals['score']
    if score >= 40:
        signals['recommendation'] = '🟢 强烈买入'
        signals['action'] = 'strong_buy'
    elif score >= 20:
        signals['recommendation'] = '🟢 买入'
        signals['action'] = 'buy'
    elif score >= 0:
        signals['recommendation'] = '⚪ 中性偏多'
        signals['action'] = 'hold_bullish'
    elif score >= -20:
        signals['recommendation'] = '⚪ 中性偏空'
        signals['action'] = 'hold_bearish'
    elif score >= -40:
        signals['recommendation'] = '🔴 卖出'
        signals['action'] = 'sell'
    else:
        signals['recommendation'] = '🔴 强烈卖出'
        signals['action'] = 'strong_sell'
    
    # 风险评估
    risk_assessment = assess_risk(indicators)
    signals['risk'] = {
        'level': risk_assessment['level'],
        'score': risk_assessment['score'],
        'factors': risk_assessment['factors']
    }
    # 保留顶级字段以兼容旧代码
    signals['risk_level'] = risk_assessment['level']
    signals['risk_score'] = risk_assessment['score']
    signals['risk_factors'] = risk_assessment['factors']
    
    # 止损止盈建议
    stop_loss_profit = calculate_stop_loss_profit(indicators)
    signals['stop_loss'] = stop_loss_profit.get('stop_loss')
    signals['take_profit'] = stop_loss_profit.get('take_profit')
        
    return signals


def assess_risk(indicators: dict):
    """
    评估投资风险等级
    """
    risk_score = 0
    risk_factors = []
    
    # 1. 波动率风险
    if 'volatility_20' in indicators:
        vol = indicators['volatility_20']
        if vol > 5:
            risk_score += 30
            risk_factors.append(f'极高波动率({vol:.1f}%)')
        elif vol > 3:
            risk_score += 20
            risk_factors.append(f'高波动率({vol:.1f}%)')
        elif vol > 2:
            risk_score += 10
            risk_factors.append(f'中等波动率({vol:.1f}%)')
    
    # 2. RSI极端值
    if 'rsi' in indicators:
        rsi = indicators['rsi']
        if rsi > 85 or rsi < 15:
            risk_score += 20
            risk_factors.append(f'RSI极端值({rsi:.1f})')
    
    # 3. 连续涨跌风险
    if 'consecutive_up_days' in indicators:
        up_days = indicators['consecutive_up_days']
        if up_days >= 7:
            risk_score += 25
            risk_factors.append(f'连续上涨{up_days}天(回调风险)')
        elif up_days >= 5:
            risk_score += 15
            risk_factors.append(f'连续上涨{up_days}天')
    
    if 'consecutive_down_days' in indicators:
        down_days = indicators['consecutive_down_days']
        if down_days >= 7:
            risk_score += 25
            risk_factors.append(f'连续下跌{down_days}天(继续下跌风险)')
        elif down_days >= 5:
            risk_score += 15
            risk_factors.append(f'连续下跌{down_days}天')
    
    # 4. 距离支撑/压力位
    current_price = indicators.get('current_price')
    if current_price and 'support_20d_low' in indicators:
        support = indicators['support_20d_low']
        dist_to_support = ((current_price - support) / current_price) * 100
        if dist_to_support < 2:
            risk_score += 15
            risk_factors.append('接近重要支撑位')
    
    if current_price and 'resistance_20d_high' in indicators:
        resistance = indicators['resistance_20d_high']
        dist_to_resistance = ((resistance - current_price) / current_price) * 100
        if dist_to_resistance < 2:
            risk_score += 15
            risk_factors.append('接近重要压力位')
    
    # 5. 趋势不明确
    if 'trend_strength' in indicators:
        strength = indicators['trend_strength']
        if strength < 15:
            risk_score += 10
            risk_factors.append('趋势不明确')
    
    # 6. 量价背离
    if 'obv_trend' in indicators:
        obv_trend = indicators['obv_trend']
        price_change = indicators.get('price_change_pct', 0)
        
        if (obv_trend == 'up' and price_change < -1) or (obv_trend == 'down' and price_change > 1):
            risk_score += 15
            risk_factors.append('量价背离')
    
    # 7. ADX趋势强度风险
    if 'adx' in indicators:
        adx = indicators['adx']
        # ADX低于20表示趋势不明确，增加交易风险
        if adx < 20:
            risk_score += 10
            risk_factors.append(f'ADX({adx:.1f})趋势不明确')
        # ADX高于60表示趋势过强，可能反转
        elif adx > 60:
            risk_score += 15
            risk_factors.append(f'ADX({adx:.1f})趋势过强可能反转')
    
    # 判断风险等级（返回英文标识符，前端负责显示）
    if risk_score >= 70:
        level = 'very_high'
    elif risk_score >= 50:
        level = 'high'
    elif risk_score >= 30:
        level = 'medium'
    elif risk_score >= 15:
        level = 'low'
    else:
        level = 'very_low'
    
    return {
        'level': level,
        'score': int(risk_score),
        'factors': risk_factors
    }


def calculate_stop_loss_profit(indicators: dict):
    """
    计算建议的止损和止盈价位
    """
    current_price = indicators.get('current_price')
    if not current_price:
        return {}
    
    result = {}
    
    if 'atr' in indicators:
        atr = indicators['atr']
        result['stop_loss'] = float(current_price - 2 * atr)
        result['take_profit'] = float(current_price + 3 * atr)
    elif 'support_20d_low' in indicators and 'resistance_20d_high' in indicators:
        support = indicators['support_20d_low']
        resistance = indicators['resistance_20d_high']
        result['stop_loss'] = float(support * 0.98)
        result['take_profit'] = float(resistance)
    else:
        result['stop_loss'] = float(current_price * 0.95)
        result['take_profit'] = float(current_price * 1.10)
    
    position_sizing = calculate_position_sizing(indicators, result)
    result.update(position_sizing)
    
    return result


def calculate_position_sizing(indicators: dict, stop_loss_data: dict):
    """
    计算建议的仓位大小和风险管理
    """
    result = {}
    
    current_price = indicators.get('current_price')
    stop_loss = stop_loss_data.get('stop_loss')
    
    if not current_price or not stop_loss:
        return result
        
    risk_per_share = current_price - stop_loss
    account_value = 100000
    max_risk_amount = account_value * 0.02
    
    if risk_per_share > 0:
        suggested_position_size = int(max_risk_amount / risk_per_share)
        result['suggested_position_size'] = suggested_position_size
        result['position_risk_amount'] = float(suggested_position_size * risk_per_share)
        
        position_value = suggested_position_size * current_price
        result['position_value'] = float(position_value)
        
        position_ratio = (position_value / account_value) * 100
        result['position_ratio'] = float(position_ratio)
        
        risk_level = indicators.get('risk_level', 'medium')
        risk_multiplier = {
            'very_low': 1.5,
            'low': 1.2,
            'medium': 1.0,
            'high': 0.7,
            'very_high': 0.5
        }
        
        adjusted_position_size = int(suggested_position_size * risk_multiplier.get(risk_level, 1.0))
        result['adjusted_position_size'] = adjusted_position_size
        
        result['position_sizing_advice'] = {
            'max_risk_percent': 2,
            'risk_per_share': float(risk_per_share),
            'suggested_size': suggested_position_size,
            'adjusted_size': adjusted_position_size,
            'position_value': float(position_value),
            'account_value': account_value
        }
    
    return result


def check_ollama_available():
    """
    检查 Ollama 是否可用
    """
    try:
        import ollama
        import requests
        
        ollama_host = os.getenv('OLLAMA_HOST', OLLAMA_HOST)
        
        try:
            response = requests.get(f'{ollama_host}/api/tags', timeout=2)
            if response.status_code == 200:
                try:
                    client = ollama.Client(host=ollama_host)
                    client.list()
                    return True
                except Exception:
                    return True
            return False
        except Exception:
            return False
    except ImportError:
        return False


def perform_ai_analysis(symbol, indicators, signals, duration, model=DEFAULT_AI_MODEL):
    """
    执行AI分析的辅助函数
    """
    try:
        import ollama
        
        fundamental_data = indicators.get('fundamental_data', {})
        has_fundamental = (fundamental_data and 
                          isinstance(fundamental_data, dict) and 
                          'raw_xml' not in fundamental_data and
                          len(fundamental_data) > 0)
        
        if has_fundamental:
            fundamental_sections = []
            
            if 'CompanyName' in fundamental_data:
                info_parts = [f"公司名称: {fundamental_data['CompanyName']}"]
                if 'Exchange' in fundamental_data:
                    info_parts.append(f"交易所: {fundamental_data['Exchange']}")
                if 'Employees' in fundamental_data:
                    info_parts.append(f"员工数: {fundamental_data['Employees']}人")
                if 'SharesOutstanding' in fundamental_data:
                    shares = fundamental_data['SharesOutstanding']
                    try:
                        shares_val = float(shares)
                        if shares_val >= 1e9:
                            shares_str = f"{shares_val/1e9:.2f}B股"
                        elif shares_val >= 1e6:
                            shares_str = f"{shares_val/1e6:.2f}M股"
                        else:
                            shares_str = f"{int(shares_val):,}股"
                        info_parts.append(f"流通股数: {shares_str}")
                    except:
                        info_parts.append(f"流通股数: {shares}")
                if info_parts:
                    fundamental_sections.append("基本信息:\n" + "\n".join([f"   - {p}" for p in info_parts]))
            
            # 市值和价格
            price_parts = []
            if 'MarketCap' in fundamental_data:
                try:
                    mcap = float(fundamental_data['MarketCap'])
                    if mcap >= 1e9:
                        price_parts.append(f"市值: ${mcap/1e9:.2f}B")
                    elif mcap >= 1e6:
                        price_parts.append(f"市值: ${mcap/1e6:.2f}M")
                    else:
                        price_parts.append(f"市值: ${mcap:.2f}")
                except:
                    price_parts.append(f"市值: {fundamental_data['MarketCap']}")
            if 'Price' in fundamental_data:
                price_parts.append(f"当前价: ${fundamental_data['Price']}")
            if '52WeekHigh' in fundamental_data and '52WeekLow' in fundamental_data:
                price_parts.append(f"52周区间: ${fundamental_data['52WeekLow']} - ${fundamental_data['52WeekHigh']}")
            if price_parts:
                fundamental_sections.append("市值与价格:\n" + "\n".join([f"   - {p}" for p in price_parts]))
            
            # 财务指标
            financial_parts = []
            for key, label in [('RevenueTTM', '营收(TTM)'), ('NetIncomeTTM', '净利润(TTM)'), 
                              ('EBITDATTM', 'EBITDA(TTM)'), ('ProfitMargin', '利润率'), 
                              ('GrossMargin', '毛利率')]:
                if key in fundamental_data:
                    value = fundamental_data[key]
                    try:
                        val = float(value)
                        if 'Margin' in key:
                            financial_parts.append(f"{label}: {val:.2f}%")
                        elif val >= 1e9:
                            financial_parts.append(f"{label}: ${val/1e9:.2f}B")
                        elif val >= 1e6:
                            financial_parts.append(f"{label}: ${val/1e6:.2f}M")
                        else:
                            financial_parts.append(f"{label}: {val:.2f}")
                    except:
                        financial_parts.append(f"{label}: {value}")
            if financial_parts:
                fundamental_sections.append("财务指标:\n" + "\n".join([f"   - {p}" for p in financial_parts]))
            
            # 每股数据
            per_share_parts = []
            for key, label in [('EPS', '每股收益(EPS)'), ('BookValuePerShare', '每股净资产'), 
                              ('CashPerShare', '每股现金'), ('DividendPerShare', '每股股息')]:
                if key in fundamental_data:
                    value = fundamental_data[key]
                    try:
                        val = float(value)
                        per_share_parts.append(f"{label}: ${val:.2f}")
                    except:
                        per_share_parts.append(f"{label}: {value}")
            if per_share_parts:
                fundamental_sections.append("每股数据:\n" + "\n".join([f"   - {p}" for p in per_share_parts]))
            
            # 估值指标
            valuation_parts = []
            for key, label in [('PE', '市盈率(PE)'), ('PriceToBook', '市净率(PB)'), ('ROE', '净资产收益率(ROE)')]:
                if key in fundamental_data:
                    value = fundamental_data[key]
                    try:
                        val = float(value)
                        if key == 'ROE':
                            valuation_parts.append(f"{label}: {val:.2f}%")
                        else:
                            valuation_parts.append(f"{label}: {val:.2f}")
                    except:
                        valuation_parts.append(f"{label}: {value}")
            if valuation_parts:
                fundamental_sections.append("估值指标:\n" + "\n".join([f"   - {p}" for p in valuation_parts]))
            
            # 预测数据
            forecast_parts = []
            if 'TargetPrice' in fundamental_data:
                try:
                    target = float(fundamental_data['TargetPrice'])
                    forecast_parts.append(f"目标价: ${target:.2f}")
                except:
                    forecast_parts.append(f"目标价: {fundamental_data['TargetPrice']}")
            if 'ConsensusRecommendation' in fundamental_data:
                try:
                    consensus = float(fundamental_data['ConsensusRecommendation'])
                    if consensus <= 1.5:
                        rec = "强烈买入"
                    elif consensus <= 2.5:
                        rec = "买入"
                    elif consensus <= 3.5:
                        rec = "持有"
                    elif consensus <= 4.5:
                        rec = "卖出"
                    else:
                        rec = "强烈卖出"
                    forecast_parts.append(f"共识评级: {rec} ({consensus:.2f})")
                except:
                    forecast_parts.append(f"共识评级: {fundamental_data['ConsensusRecommendation']}")
            if 'ProjectedEPS' in fundamental_data:
                try:
                    proj_eps = float(fundamental_data['ProjectedEPS'])
                    forecast_parts.append(f"预测EPS: ${proj_eps:.2f}")
                except:
                    forecast_parts.append(f"预测EPS: {fundamental_data['ProjectedEPS']}")
            if 'ProjectedGrowthRate' in fundamental_data:
                try:
                    growth = float(fundamental_data['ProjectedGrowthRate'])
                    forecast_parts.append(f"预测增长率: {growth:.2f}%")
                except:
                    forecast_parts.append(f"预测增长率: {fundamental_data['ProjectedGrowthRate']}")
            if forecast_parts:
                fundamental_sections.append("分析师预测:\n" + "\n".join([f"   - {p}" for p in forecast_parts]))
            
            # 详细财务报表数据
            if fundamental_data.get('Financials'):
                try:
                    financials = fundamental_data['Financials']
                    if isinstance(financials, list) and len(financials) > 0:
                        financials_text = "年度财务报表:\n"
                        for record in financials[:5]:  # 最近5年
                            if isinstance(record, dict):
                                date = record.get('index', record.get('Date', 'N/A'))
                                financials_text += f"   {date}:\n"
                                for key, value in record.items():
                                    if key not in ['index', 'Date'] and value:
                                        try:
                                            val = float(value)
                                            if abs(val) >= 1e9:
                                                financials_text += f"     - {key}: ${val/1e9:.2f}B\n"
                                            elif abs(val) >= 1e6:
                                                financials_text += f"     - {key}: ${val/1e6:.2f}M\n"
                                            else:
                                                financials_text += f"     - {key}: ${val:.2f}\n"
                                        except:
                                            financials_text += f"     - {key}: {value}\n"
                        fundamental_sections.append(financials_text)
                except Exception as e:
                    logger.warning(f"格式化年度财务报表失败: {e}")
            
            if fundamental_data.get('QuarterlyFinancials'):
                try:
                    quarterly = fundamental_data['QuarterlyFinancials']
                    if isinstance(quarterly, list) and len(quarterly) > 0:
                        quarterly_text = "季度财务报表:\n"
                        for record in quarterly[:4]:  # 最近4个季度
                            if isinstance(record, dict):
                                date = record.get('index', record.get('Date', 'N/A'))
                                quarterly_text += f"   {date}:\n"
                                for key, value in record.items():
                                    if key not in ['index', 'Date'] and value:
                                        try:
                                            val = float(value)
                                            if abs(val) >= 1e9:
                                                quarterly_text += f"     - {key}: ${val/1e9:.2f}B\n"
                                            elif abs(val) >= 1e6:
                                                quarterly_text += f"     - {key}: ${val/1e6:.2f}M\n"
                                            else:
                                                quarterly_text += f"     - {key}: ${val:.2f}\n"
                                        except:
                                            quarterly_text += f"     - {key}: {value}\n"
                        fundamental_sections.append(quarterly_text)
                except Exception as e:
                    logger.warning(f"格式化季度财务报表失败: {e}")
            
            if fundamental_data.get('BalanceSheet'):
                try:
                    balance = fundamental_data['BalanceSheet']
                    if isinstance(balance, list) and len(balance) > 0:
                        balance_text = "年度资产负债表:\n"
                        for record in balance[:3]:  # 最近3年
                            if isinstance(record, dict):
                                date = record.get('index', record.get('Date', 'N/A'))
                                balance_text += f"   {date}:\n"
                                for key, value in record.items():
                                    if key not in ['index', 'Date'] and value:
                                        try:
                                            val = float(value)
                                            if abs(val) >= 1e9:
                                                balance_text += f"     - {key}: ${val/1e9:.2f}B\n"
                                            elif abs(val) >= 1e6:
                                                balance_text += f"     - {key}: ${val/1e6:.2f}M\n"
                                            else:
                                                balance_text += f"     - {key}: ${val:.2f}\n"
                                        except:
                                            balance_text += f"     - {key}: {value}\n"
                        fundamental_sections.append(balance_text)
                except Exception as e:
                    logger.warning(f"格式化资产负债表失败: {e}")
            
            if fundamental_data.get('Cashflow'):
                try:
                    cashflow = fundamental_data['Cashflow']
                    if isinstance(cashflow, list) and len(cashflow) > 0:
                        cashflow_text = "年度现金流量表:\n"
                        for record in cashflow[:3]:  # 最近3年
                            if isinstance(record, dict):
                                date = record.get('index', record.get('Date', 'N/A'))
                                cashflow_text += f"   {date}:\n"
                                for key, value in record.items():
                                    if key not in ['index', 'Date'] and value:
                                        try:
                                            val = float(value)
                                            if abs(val) >= 1e9:
                                                cashflow_text += f"     - {key}: ${val/1e9:.2f}B\n"
                                            elif abs(val) >= 1e6:
                                                cashflow_text += f"     - {key}: ${val/1e6:.2f}M\n"
                                            else:
                                                cashflow_text += f"     - {key}: ${val:.2f}\n"
                                        except:
                                            cashflow_text += f"     - {key}: {value}\n"
                        fundamental_sections.append(cashflow_text)
                except Exception as e:
                    logger.warning(f"格式化现金流量表失败: {e}")
            
            fundamental_text = "\n\n".join(fundamental_sections) if fundamental_sections else "无可用数据"
        else:
            fundamental_text = None
        
        # 根据是否有基本面数据构建不同的提示词
        if has_fundamental:
            # 有基本面数据的完整分析提示词
            prompt = f"""你是一位专业的股票分析师，擅长结合技术分析和基本面分析。请基于以下技术指标和基本面数据，给出全面的投资分析和建议。

股票代码: {symbol.upper()}
当前价格: ${indicators.get('current_price', 0):.2f}
数据周期: {duration} ({indicators.get('data_points', 0)}个数据点)

【技术指标分析】
1. 移动平均线:
   - MA5: ${indicators.get('ma5', 0):.2f}
   - MA20: ${indicators.get('ma20', 0):.2f}
   - MA50: ${indicators.get('ma50', 0):.2f}

2. 动量指标:
   - RSI(14): {indicators.get('rsi', 0):.1f}
   - MACD: {indicators.get('macd', 0):.3f}
   - 信号线: {indicators.get('macd_signal', 0):.3f}

3. 波动指标:
   - 布林带上轨: ${indicators.get('bb_upper', 0):.2f}
   - 布林带中轨: ${indicators.get('bb_middle', 0):.2f}
   - 布林带下轨: ${indicators.get('bb_lower', 0):.2f}
   - ATR: ${indicators.get('atr', 0):.2f}

4. KDJ指标:
   - K: {indicators.get('kdj_k', 0):.1f}
   - D: {indicators.get('kdj_d', 0):.1f}
   - J: {indicators.get('kdj_j', 0):.1f}

5. 趋势分析:
   - 趋势方向: {indicators.get('trend_direction', 'neutral')}
   - 趋势强度: {indicators.get('trend_strength', 0):.0f}%
   - 连续上涨天数: {indicators.get('consecutive_up_days', 0)}
   - 连续下跌天数: {indicators.get('consecutive_down_days', 0)}

6. 支撑压力位:
   - 枢轴点: ${indicators.get('pivot', 0):.2f}
   - 压力位R1: ${indicators.get('pivot_r1', 0):.2f}
   - 支撑位S1: ${indicators.get('pivot_s1', 0):.2f}

7. 现代技术指标:
   - CCI(顺势指标): {indicators.get('cci', 0):.1f}
   - ADX(趋势强度):
     * ADX: {indicators.get('adx', 0):.1f}
     * +DI: {indicators.get('plus_di', 0):.1f}
     * -DI: {indicators.get('minus_di', 0):.1f}
   - SAR(抛物线): ${indicators.get('sar', 0):.2f}
   - 斐波那契回撤位:
     * 23.6%: ${indicators.get('fib_23.6', 0):.2f}
     * 38.2%: ${indicators.get('fib_38.2', 0):.2f}
     * 50.0%: ${indicators.get('fib_50.0', 0):.2f}
     * 61.8%: ${indicators.get('fib_61.8', 0):.2f}
     * 78.6%: ${indicators.get('fib_78.6', 0):.2f}
   - 一目均衡表 (Ichimoku Cloud):
     * 转折线 (Tenkan): ${indicators.get('ichimoku_tenkan_sen', 0):.2f}
     * 基准线 (Kijun): ${indicators.get('ichimoku_kijun_sen', 0):.2f}
     * 云层上沿: ${indicators.get('ichimoku_cloud_top', 0):.2f}
     * 云层下沿: ${indicators.get('ichimoku_cloud_bottom', 0):.2f}
     * 状态: {indicators.get('ichimoku_status', 'unknown')}
     * 交叉信号: {indicators.get('ichimoku_tk_cross', 'neutral')}
   - SuperTrend:
     * 价格: ${indicators.get('supertrend', 0):.2f}
     * 方向: {indicators.get('supertrend_direction', 'neutral')}
   - StochRSI:
     * K: {indicators.get('stoch_rsi_k', 0):.1f}
     * D: {indicators.get('stoch_rsi_d', 0):.1f}
     * 状态: {indicators.get('stoch_rsi_status', 'neutral')}
   - 筹码分布 (Volume Profile):
     * POC (控制点): ${indicators.get('vp_poc', 0):.2f}
     * 价值区上沿 (VAH): ${indicators.get('vp_vah', 0):.2f}
     * 价值区下沿 (VAL): ${indicators.get('vp_val', 0):.2f}
     * 状态: {indicators.get('vp_status', 'neutral')}

8. 成交量分析（重要）:
   - 成交量比率: {indicators.get('volume_ratio', 0):.2f} (当前成交量/20日均量)
   - 当前成交量: {indicators.get('current_volume', 0):,.0f}
   - 20日平均成交量: {indicators.get('avg_volume_20', 0):,.0f}
   - OBV能量潮: {indicators.get('obv_current', 0):,.0f}
   - OBV趋势: {indicators.get('obv_trend', 'neutral')}
   - ML预测价量关系:
     * 价量配合: {indicators.get('price_volume_confirmation', 'neutral')}
     * 成交量信号: {indicators.get('volume_signal', 'normal')}
     * 成交量比率: {indicators.get('volume_ratio', 1.0):.2f}
     * 价量背离度: {indicators.get('price_volume_divergence', 0):.3f}

9. ML预测（机器学习）:
   - 预测趋势: {indicators.get('ml_trend', 'unknown')}
   - 预测置信度: {indicators.get('ml_confidence', 0):.1f}%
   - 预期价格变化: {indicators.get('ml_prediction', 0)*100:.2f}%

10. 风险评估:
   - 风险等级: {signals.get('risk', {}).get('level', 'unknown') if signals.get('risk') else 'unknown'}
   - 风险评分: {signals.get('risk', {}).get('score', 0) if signals.get('risk') else 0}/100

11. 系统建议:
   - 综合评分: {signals.get('score', 0)}/100
   - 建议操作: {signals.get('recommendation', 'unknown')}

【基本面分析】
{fundamental_text}

请提供以下分析:
1. 技术面分析: 当前市场状态（趋势、动能、波动）、关键技术信号解读
2. 成交量分析（重要）:
   - 分析当前成交量水平（与历史平均成交量对比）
   - 价量关系分析：价格上涨/下跌时成交量的配合情况
   - 价量背离检测：是否存在价涨量缩或价跌量增的背离现象
   - OBV能量潮趋势分析：资金流向判断
   - Volume Profile分析：筹码分布情况，POC和价值区域的意义
   - ML预测的价量关系：机器学习模型对价量配合的判断
   - 成交量对趋势的确认或否定作用
3. 基本面分析: 
   - 基于财务指标和财务报表数据，分析公司财务状况、盈利能力、现金流健康度
   - 通过对比年度和季度财务报表，识别营收、利润、现金流的变化趋势
   - 分析资产负债表，评估公司资产结构、负债水平和财务稳健性
   - 结合机构持有人信息，评估市场对公司前景的认可度
   - 估值水平分析：结合PE、PB、ROE等指标，判断当前估值是否合理
3. 综合分析: 结合技术面和基本面，给出买入/卖出/观望的具体建议
4. 风险提示: 技术风险和基本面风险的综合评估（重点关注财务报表中的风险信号）
5. 操作建议: 建议的止损止盈位、仓位管理建议（重点关注SAR止损位）
6. 市场展望: 结合技术指标和基本面数据，分析未来可能的情境（牛市、熊市、震荡市中的不同策略）

请用中文回答，简洁专业，重点突出，将技术分析和基本面分析有机结合。在基本面分析中，请充分利用提供的财务报表、资产负债表、现金流量表等详细数据，进行深入分析。"""
        else:
            # 没有基本面数据，只进行技术分析
            prompt = f"""你是一位专业的股票技术分析师。请基于以下技术指标数据，给出详细的技术分析和交易建议。

股票代码: {symbol.upper()}
当前价格: ${indicators.get('current_price', 0):.2f}
数据周期: {duration} ({indicators.get('data_points', 0)}个数据点)

【注意】该股票暂无基本面数据（可能是ETF或特殊证券），请仅基于技术指标进行分析。

技术指标:
1. 移动平均线:
   - MA5: ${indicators.get('ma5', 0):.2f}
   - MA20: ${indicators.get('ma20', 0):.2f}
   - MA50: ${indicators.get('ma50', 0):.2f}

2. 动量指标:
   - RSI(14): {indicators.get('rsi', 0):.1f}
   - MACD: {indicators.get('macd', 0):.3f}
   - 信号线: {indicators.get('macd_signal', 0):.3f}

3. 波动指标:
   - 布林带上轨: ${indicators.get('bb_upper', 0):.2f}
   - 布林带中轨: ${indicators.get('bb_middle', 0):.2f}
   - 布林带下轨: ${indicators.get('bb_lower', 0):.2f}
   - ATR: ${indicators.get('atr', 0):.2f}

4. KDJ指标:
   - K: {indicators.get('kdj_k', 0):.1f}
   - D: {indicators.get('kdj_d', 0):.1f}
   - J: {indicators.get('kdj_j', 0):.1f}

5. 趋势分析:
   - 趋势方向: {indicators.get('trend_direction', 'neutral')}
   - 趋势强度: {indicators.get('trend_strength', 0):.0f}%
   - 连续上涨天数: {indicators.get('consecutive_up_days', 0)}
   - 连续下跌天数: {indicators.get('consecutive_down_days', 0)}

6. 支撑压力位:
   - 枢轴点: ${indicators.get('pivot', 0):.2f}
   - 压力位R1: ${indicators.get('pivot_r1', 0):.2f}
   - 支撑位S1: ${indicators.get('pivot_s1', 0):.2f}

7. 现代技术指标:
   - CCI(顺势指标): {indicators.get('cci', 0):.1f}
   - ADX(趋势强度):
     * ADX: {indicators.get('adx', 0):.1f}
     * +DI: {indicators.get('plus_di', 0):.1f}
     * -DI: {indicators.get('minus_di', 0):.1f}
   - SAR(抛物线): ${indicators.get('sar', 0):.2f}
   - 斐波那契回撤位:
     * 23.6%: ${indicators.get('fib_23.6', 0):.2f}
     * 38.2%: ${indicators.get('fib_38.2', 0):.2f}
     * 50.0%: ${indicators.get('fib_50.0', 0):.2f}
     * 61.8%: ${indicators.get('fib_61.8', 0):.2f}
     * 78.6%: ${indicators.get('fib_78.6', 0):.2f}
   - 一目均衡表 (Ichimoku Cloud):
     * 转折线 (Tenkan): ${indicators.get('ichimoku_tenkan_sen', 0):.2f}
     * 基准线 (Kijun): ${indicators.get('ichimoku_kijun_sen', 0):.2f}
     * 云层上沿: ${indicators.get('ichimoku_cloud_top', 0):.2f}
     * 云层下沿: ${indicators.get('ichimoku_cloud_bottom', 0):.2f}
     * 状态: {indicators.get('ichimoku_status', 'unknown')}
     * 交叉信号: {indicators.get('ichimoku_tk_cross', 'neutral')}

8. 风险评估:
   - 风险等级: {signals.get('risk', {}).get('level', 'unknown') if signals.get('risk') else 'unknown'}
   - 风险评分: {signals.get('risk', {}).get('score', 0) if signals.get('risk') else 0}/100

9. 系统建议:
   - 综合评分: {signals.get('score', 0)}/100
   - 建议操作: {signals.get('recommendation', 'unknown')}

请提供:
1. 当前市场状态分析（趋势、动能、波动）
2. 关键技术信号解读（包括CCI、ADX、SAR等现代技术指标）
3. 买入/卖出/观望的具体建议（基于纯技术分析）
4. 风险提示和注意事项（重点关注ADX趋势强度和CCI超买超卖）
5. 建议的止损止盈位（参考SAR抛物线）
6. 市场情绪和可能的情境分析（如牛市、熊市、震荡市中的不同策略）

请用中文回答，简洁专业，重点突出。"""

        # 调用Ollama（使用环境变量配置的服务地址）
        ollama_host = os.getenv('OLLAMA_HOST', OLLAMA_HOST)
        try:
            client = ollama.Client(host=ollama_host)
        except Exception:
            client = None
        response = (client.chat if client else ollama.chat)(
            model=model,
            messages=[{
                'role': 'user',
                'content': prompt
            }]
        )
        
        return response['message']['content']
        
    except Exception as ai_error:
        logger.error(f"AI分析失败: {ai_error}")
        return f'AI分析不可用: {str(ai_error)}\n\n请确保Ollama已安装并运行: ollama serve'

