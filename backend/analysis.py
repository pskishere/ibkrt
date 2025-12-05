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
from .scoring import calculate_comprehensive_score, get_recommendation
from .signal_generators import (
    add_ma_signals, add_rsi_signals, add_bollinger_signals,
    add_macd_signals, add_volume_signals, add_trend_signals,
    add_advanced_indicator_signals, calculate_risk_level,
    calculate_stop_loss_take_profit
)


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


def generate_signals(indicators: dict, account_value: float = 100000, risk_percent: float = 2.0):
    """
    基于技术指标生成买卖信号
    使用新的多维度加权评分系统
    """
    if not indicators:
        return None
        
    signals = {
        'symbol': indicators.get('symbol'),
        'current_price': indicators.get('current_price'),
        'signals': [],
        'score': 0,
    }
    
    signals_list = signals['signals']
    
    # 生成各类信号
    add_ma_signals(signals_list, indicators)
    add_rsi_signals(signals_list, indicators)
    add_bollinger_signals(signals_list, indicators)
    add_macd_signals(signals_list, indicators)
    add_volume_signals(signals_list, indicators)
    add_trend_signals(signals_list, indicators)
    add_advanced_indicator_signals(signals_list, indicators)
    
    # 支撑位和压力位分析
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
        
        if nearest_resistance and nearest_resistance_dist < 2:
            signals['signals'].append(f'🔴 接近压力位${nearest_resistance:.2f} (距离{nearest_resistance_dist:.1f}%) - 可能回调')
        
        # 突破信号
        if 'resistance_20d_high' in indicators:
            high_20 = indicators['resistance_20d_high']
            if current_price >= high_20 * 0.99:  # 接近或突破20日高点
                signals['signals'].append(f'🚀 突破20日高点${high_20:.2f} - 强势信号')
        
        if 'support_20d_low' in indicators:
            low_20 = indicators['support_20d_low']
            if current_price <= low_20 * 1.01:  # 接近或跌破20日低点
                signals['signals'].append(f'⚠️ 跌破20日低点${low_20:.2f} - 弱势信号')
    
    # Volume Profile信号
    if 'vp_poc' in indicators:
        poc = indicators['vp_poc']
        current_price = indicators.get('current_price', 0)
        vp_status = indicators.get('vp_status', 'inside_va')
        
        dist_pct = (current_price - poc) / poc * 100
        
        if abs(dist_pct) < 0.5:
            signals['signals'].append(f'⚖️ 价格在POC(${poc:.2f})附近 - 筹码密集区平衡')
        elif vp_status == 'above_va':
            signals['signals'].append(f'📈 价格在价值区域上方(POC ${poc:.2f}) - 强势失衡')
        elif vp_status == 'below_va':
            signals['signals'].append(f'📉 价格在价值区域下方(POC ${poc:.2f}) - 弱势失衡')
    
    # 21. ML预测信号
    if 'ml_trend' in indicators:
        ml_trend = indicators['ml_trend']
        ml_confidence = indicators.get('ml_confidence', 0)
        ml_prediction = indicators.get('ml_prediction', 0)
        
        if ml_confidence > 50:
            if ml_trend == 'up':
                signals['signals'].append(f'🤖 ML预测: 看涨趋势(置信度{ml_confidence:.1f}%, 预期涨幅{ml_prediction*100:.2f}%) - AI看多')
            elif ml_trend == 'down':
                signals['signals'].append(f'🤖 ML预测: 看跌趋势(置信度{ml_confidence:.1f}%, 预期跌幅{ml_prediction*100:.2f}%) - AI看空')
            else:
                signals['signals'].append(f'🤖 ML预测: 横盘整理(置信度{ml_confidence:.1f}%) - AI中性')
        elif ml_confidence > 30:
            if ml_trend == 'up':
                signals['signals'].append(f'🤖 ML预测: 轻微看涨(置信度{ml_confidence:.1f}%) - 谨慎乐观')
            elif ml_trend == 'down':
                signals['signals'].append(f'🤖 ML预测: 轻微看跌(置信度{ml_confidence:.1f}%) - 谨慎悲观')
            
    # 使用新的多维度加权评分系统计算综合评分
    score, score_details = calculate_comprehensive_score(indicators)
    signals['score'] = score
    signals['score_details'] = score_details  # 保存详细评分信息
    
    # 根据评分获取建议
    recommendation, action = get_recommendation(score)
    signals['recommendation'] = recommendation
    signals['action'] = action
    
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
    
    # 止损止盈建议（买入场景）
    stop_loss_profit = calculate_stop_loss_profit(indicators, action='buy', account_value=account_value, risk_percent=risk_percent)
    signals['stop_loss'] = stop_loss_profit.get('stop_loss')
    signals['take_profit'] = stop_loss_profit.get('take_profit')
    signals['risk_reward_ratio'] = stop_loss_profit.get('risk_reward_ratio')
    signals['position_sizing'] = stop_loss_profit.get('position_sizing_advice')
        
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


def calculate_stop_loss_profit(indicators: dict, action: str = 'buy', account_value: float = 100000, risk_percent: float = 2.0):
    """
    计算建议的止损和止盈价位
    
    Args:
        indicators: 技术指标字典
        action: 操作类型 'buy' 或 'sell'
        account_value: 账户金额（美元）
        risk_percent: 单笔交易风险百分比（默认2%）
    """
    current_price = indicators.get('current_price')
    if not current_price:
        return {}
    
    result = {}
    volatility = indicators.get('volatility_20', 2.0)
    
    # 根据波动率动态调整ATR倍数
    if volatility > 4:  # 高波动
        atr_stop_multiplier = 2.5
        atr_profit_multiplier = 4.0
    elif volatility > 2.5:  # 中等波动
        atr_stop_multiplier = 2.0
        atr_profit_multiplier = 3.5
    else:  # 低波动
        atr_stop_multiplier = 1.5
        atr_profit_multiplier = 3.0
    
    # 计算止损止盈价位
    if 'atr' in indicators:
        atr = indicators['atr']
        if action == 'buy':
            result['stop_loss'] = float(current_price - atr_stop_multiplier * atr)
            result['take_profit'] = float(current_price + atr_profit_multiplier * atr)
        else:  # sell
            result['stop_loss'] = float(current_price + atr_stop_multiplier * atr)
            result['take_profit'] = float(current_price - atr_profit_multiplier * atr)
    elif 'support_20d_low' in indicators and 'resistance_20d_high' in indicators:
        support = indicators['support_20d_low']
        resistance = indicators['resistance_20d_high']
        if action == 'buy':
            result['stop_loss'] = float(support * 0.98)
            result['take_profit'] = float(resistance)
        else:  # sell
            result['stop_loss'] = float(resistance * 1.02)
            result['take_profit'] = float(support)
    else:
        if action == 'buy':
            result['stop_loss'] = float(current_price * 0.95)
            result['take_profit'] = float(current_price * 1.10)
        else:  # sell
            result['stop_loss'] = float(current_price * 1.05)
            result['take_profit'] = float(current_price * 0.90)
    
    # 计算风险收益比
    if action == 'buy':
        risk = current_price - result['stop_loss']
        reward = result['take_profit'] - current_price
    else:  # sell
        risk = result['stop_loss'] - current_price
        reward = current_price - result['take_profit']
    
    if risk > 0:
        result['risk_reward_ratio'] = float(reward / risk)
    
    position_sizing = calculate_position_sizing(indicators, result, account_value, risk_percent)
    result.update(position_sizing)
    
    return result


def calculate_position_sizing(indicators: dict, stop_loss_data: dict, account_value: float = 100000, risk_percent: float = 2.0):
    """
    计算建议的仓位大小和风险管理
    
    Args:
        indicators: 技术指标字典
        stop_loss_data: 止损数据（包含 stop_loss）
        account_value: 账户金额（美元）
        risk_percent: 单笔交易风险百分比
    """
    result = {}
    
    current_price = indicators.get('current_price')
    stop_loss = stop_loss_data.get('stop_loss')
    
    if not current_price or not stop_loss:
        return result
        
    risk_per_share = abs(current_price - stop_loss)
    max_risk_amount = account_value * (risk_percent / 100.0)
    
    if risk_per_share > 0:
        suggested_position_size = int(max_risk_amount / risk_per_share)
        result['suggested_position_size'] = suggested_position_size
        result['position_risk_amount'] = float(suggested_position_size * risk_per_share)
        
        position_value = suggested_position_size * current_price
        result['position_value'] = float(position_value)
        
        position_ratio = (position_value / account_value) * 100
        result['position_ratio'] = float(position_ratio)
        
        # 根据风险等级调整仓位
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
            'max_risk_percent': float(risk_percent),
            'risk_per_share': float(risk_per_share),
            'suggested_size': suggested_position_size,
            'adjusted_size': adjusted_position_size,
            'position_value': float(position_value),
            'account_value': float(account_value)
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
        
        # 获取评分系统详细信息
        score_details = signals.get('score_details', {})
        dimensions = score_details.get('dimensions', {}) if score_details else {}
        
        # 格式化建议价位（处理可能为None的情况）
        stop_loss_val = signals.get('stop_loss')
        stop_loss_str = f"${stop_loss_val:.2f}" if stop_loss_val is not None else '未计算'
        take_profit_val = signals.get('take_profit')
        take_profit_str = f"${take_profit_val:.2f}" if take_profit_val is not None else '未计算'
        sar_val = indicators.get('sar')
        sar_str = f"${sar_val:.2f}" if sar_val is not None else '未计算'
        atr_val = indicators.get('atr')
        atr_str = f"${atr_val:.2f}" if atr_val is not None else '未计算'
        
        # 根据是否有基本面数据构建不同的提示词
        if has_fundamental:
            # 有基本面数据的完整分析提示词
            prompt = f"""# 分析对象
**股票代码:** {symbol.upper()}  
**当前价格:** ${indicators.get('current_price', 0):.2f}  
**分析周期:** {duration} ({indicators.get('data_points', 0)}个数据点)

# 系统评分结果
**综合评分:** {signals.get('score', 0)}/100  
**操作建议:** {signals.get('recommendation', '未知')}  
**风险等级:** {signals.get('risk', {}).get('level', 'unknown') if signals.get('risk') else 'unknown'}  
**风险评分:** {signals.get('risk', {}).get('score', 0) if signals.get('risk') else 0}/100

**系统建议价位（参考值，需结合技术分析调整）:**
- 当前价格: ${indicators.get('current_price', 0):.2f}
- 系统建议止损位: {stop_loss_str}
- 系统建议止盈位: {take_profit_str}
- SAR止损参考: {sar_str}
- ATR波动参考: {atr_str} ({indicators.get('atr_percent', 0):.1f}%)

**多维度评分详情:**
- 趋势方向维度: {dimensions.get('trend', 0):.1f}/100
- 动量指标维度: {dimensions.get('momentum', 0):.1f}/100
- 成交量分析维度: {dimensions.get('volume', 0):.1f}/100
- 波动性维度: {dimensions.get('volatility', 0):.1f}/100
- 支撑压力维度: {dimensions.get('support_resistance', 0):.1f}/100
- 高级指标维度: {dimensions.get('advanced', 0):.1f}/100

---

# 技术指标数据

## 1. 趋势指标
- 移动平均线: MA5=${indicators.get('ma5', 0):.2f}, MA20=${indicators.get('ma20', 0):.2f}, MA50=${indicators.get('ma50', 0):.2f}
   - 趋势方向: {indicators.get('trend_direction', 'neutral')}
   - 趋势强度: {indicators.get('trend_strength', 0):.0f}%
- ADX: {indicators.get('adx', 0):.1f} (+DI={indicators.get('plus_di', 0):.1f}, -DI={indicators.get('minus_di', 0):.1f})
- SuperTrend: ${indicators.get('supertrend', 0):.2f} (方向: {indicators.get('supertrend_direction', 'neutral')})
- Ichimoku云层: {indicators.get('ichimoku_status', 'unknown')}
- SAR止损位: ${indicators.get('sar', 0):.2f}

## 2. 动量指标
- RSI(14): {indicators.get('rsi', 0):.1f}
- MACD: {indicators.get('macd', 0):.3f} (信号: {indicators.get('macd_signal', 0):.3f}, 柱状图: {indicators.get('macd_histogram', 0):.3f})
- KDJ: K={indicators.get('kdj_k', 0):.1f}, D={indicators.get('kdj_d', 0):.1f}, J={indicators.get('kdj_j', 0):.1f}
- CCI: {indicators.get('cci', 0):.1f}
- StochRSI: K={indicators.get('stoch_rsi_k', 0):.1f}, D={indicators.get('stoch_rsi_d', 0):.1f} (状态: {indicators.get('stoch_rsi_status', 'neutral')})

## 3. 波动性指标
- 布林带: 上轨=${indicators.get('bb_upper', 0):.2f}, 中轨=${indicators.get('bb_middle', 0):.2f}, 下轨=${indicators.get('bb_lower', 0):.2f}
- ATR: ${indicators.get('atr', 0):.2f} ({indicators.get('atr_percent', 0):.1f}%)
- 20日波动率: {indicators.get('volatility_20', 0):.2f}%

## 4. 成交量分析
- 成交量比率: {indicators.get('volume_ratio', 0):.2f}x (当前/20日均量)
- OBV趋势: {indicators.get('obv_trend', 'neutral')}
- 价量关系: {indicators.get('price_volume_confirmation', 'neutral')}
- Volume Profile: POC=${indicators.get('vp_poc', 0):.2f}, 状态={indicators.get('vp_status', 'neutral')}

## 5. 支撑压力位
- 20日高点: ${indicators.get('resistance_20d_high', 0):.2f}
- 20日低点: ${indicators.get('support_20d_low', 0):.2f}
- 枢轴点: ${indicators.get('pivot', 0):.2f}
- 斐波那契回撤: 23.6%=${indicators.get('fib_23.6', 0):.2f}, 38.2%=${indicators.get('fib_38.2', 0):.2f}, 61.8%=${indicators.get('fib_61.8', 0):.2f}

## 6. 其他指标
   - 连续上涨天数: {indicators.get('consecutive_up_days', 0)}
   - 连续下跌天数: {indicators.get('consecutive_down_days', 0)}
- ML预测: {indicators.get('ml_trend', 'unknown')} (置信度: {indicators.get('ml_confidence', 0):.1f}%, 预期: {indicators.get('ml_prediction', 0)*100:.2f}%)

# 基本面数据
{fundamental_text}

---

# 分析任务

请按照以下结构提供全面分析，每个部分都要有深度和洞察：

## 一、多维度评分解读

基于系统提供的多维度评分结果，详细分析：

1. **趋势方向维度** ({dimensions.get('trend', 0):.1f}/100)
   - 解释当前趋势状态（上涨/下跌/横盘）及其强度
   - 分析MA均线排列、ADX趋势强度、SuperTrend和Ichimoku云层的综合指示
   - 判断趋势的可靠性和持续性

2. **动量指标维度** ({dimensions.get('momentum', 0):.1f}/100)
   - 分析RSI、MACD、KDJ等动量指标的综合信号
   - 评估当前市场动能状态（超买/超卖/中性）
   - 识别可能的反转或延续信号

3. **成交量分析维度** ({dimensions.get('volume', 0):.1f}/100)
   - 深入分析价量关系（价涨量增/价跌量增/背离等）
   - 评估成交量的健康度和趋势确认作用
   - 分析OBV和Volume Profile显示的筹码分布情况

4. **波动性维度** ({dimensions.get('volatility', 0):.1f}/100)
   - 评估当前波动率水平对交易的影响
   - 分析布林带位置显示的短期价格区间
   - 给出风险控制和仓位建议

5. **支撑压力维度** ({dimensions.get('support_resistance', 0):.1f}/100)
   - 识别关键支撑位和压力位
   - 评估当前价格位置的优势/劣势
   - 预测可能的突破或反弹点位

6. **高级指标维度** ({dimensions.get('advanced', 0):.1f}/100)
   - 综合ML预测、连续涨跌天数等高级信号
   - 评估市场情绪和极端状态

## 二、技术面深度分析

1. **趋势分析**
   - 当前趋势方向、强度和可持续性
   - 关键均线的支撑/阻力作用
   - ADX显示的 trend strength 和 direction

2. **动量分析**
   - 各项动量指标的共振情况
   - 超买超卖状态及其可能影响
   - 可能的反转时点和信号

3. **成交量验证**
   - 成交量是否支持当前趋势
   - 价量背离的风险提示
   - 资金流向和筹码分布分析

4. **波动性评估**
   - ATR显示的波动风险
   - 布林带宽度和价格位置
   - 止损止盈位设置建议

## 三、基本面分析（如果有数据）

1. **财务状况评估**
   - 盈利能力（净利润、毛利率、净利率等）
   - 现金流健康度
   - 财务稳健性（负债率、流动比率等）

2. **业务趋势分析**
   - 营收和利润的增长趋势
   - 季度和年度对比
   - 行业地位和竞争力

3. **估值水平判断**
   - PE、PB、ROE等估值指标
   - 与行业和历史估值对比
   - 当前估值的合理性

4. **市场认可度**
   - 机构持仓情况
   - 分析师评级和目标价
   - 市场情绪和预期

## 四、综合分析结论

1. **买卖建议**
   - 基于多维度评分系统的综合判断
   - 明确的操作建议（买入/卖出/观望）及理由

2. **具体操作价位（必须明确给出）**
   
   **如果建议买入:**
   - **建议买入价位:** $[具体价格或价格区间，例如: $150.50 或 $149.00-$151.00]
     - 说明：为什么选择这个价位？基于什么技术指标？（如支撑位、均线、布林带等）
   - **建议止损价位:** $[具体价格，例如: $147.00]
     - 说明：基于什么计算？（SAR=${indicators.get('sar', 0):.2f}、ATR=${indicators.get('atr', 0):.2f}、支撑位等）
     - 止损百分比: [X]% （相对于买入价）
   - **建议止盈价位:** $[具体价格，例如: $158.00]
     - 说明：基于什么计算？（压力位、阻力位、目标价等）
     - 止盈百分比: [X]% （相对于买入价）
     - 风险收益比: 1:[X] （止盈空间/止损空间）
   
   **如果建议卖出:**
   - **建议卖出价位:** $[具体价格或价格区间]
     - 说明：为什么选择这个价位？
   - **止损/保护价位:** $[如果卖出后可能上涨，设置保护价位]
   
   **如果建议观望:**
   - **等待的买入价位:** $[如果价格达到这个价位才考虑买入]
   - **等待的卖出价位:** $[如果价格达到这个价位才考虑卖出]

3. **风险提示**
   - 技术风险点（高波动、趋势不明、背离等）
   - 基本面风险点（财务恶化、估值过高、竞争加剧等）
   - 综合风险评估
   - 止损位设置的理由和风险控制说明

4. **仓位和资金管理**
   - 建议仓位大小（根据风险等级和资金情况）
   - 分批建仓建议（如有）
   - 资金管理建议（根据风险等级）

5. **市场展望**
   - 短期（1-2周）价格走势预测
   - 中期（1-3个月）趋势展望
   - 不同市场情境下的应对策略

---

# 输出要求

1. **结构清晰**: 严格按照上述五个部分组织内容，使用明确的标题和分段
2. **数据引用**: 分析时要引用具体的技术指标数值和基本面数据
3. **逻辑严密**: 每个结论都要有数据支撑和逻辑推理
4. **重点突出**: 对于评分高的维度要深入分析，对于风险点要明确警示
5. **语言专业**: 使用专业术语但保持可读性，避免过度复杂
6. **建议明确**: 操作建议要具体可执行，避免模糊表述
7. **价位必须明确**: 在"具体操作价位"部分，必须明确给出具体的买入价位、止损价位和止盈价位，包括具体价格数字、百分比和风险收益比，不能只给建议不给具体价格

请开始分析。"""
        else:
            # 没有基本面数据，只进行技术分析
            prompt = f"""# 分析对象
**股票代码:** {symbol.upper()}  
**当前价格:** ${indicators.get('current_price', 0):.2f}  
**分析周期:** {duration} ({indicators.get('data_points', 0)}个数据点)  
**⚠️ 注意:** 无基本面数据，仅基于技术分析

# 系统评分结果
**综合评分:** {signals.get('score', 0)}/100  
**操作建议:** {signals.get('recommendation', '未知')}  
**风险等级:** {signals.get('risk', {}).get('level', 'unknown') if signals.get('risk') else 'unknown'}  
**风险评分:** {signals.get('risk', {}).get('score', 0) if signals.get('risk') else 0}/100

**系统建议价位（参考值，需结合技术分析调整）:**
- 当前价格: ${indicators.get('current_price', 0):.2f}
- 系统建议止损位: {stop_loss_str}
- 系统建议止盈位: {take_profit_str}
- SAR止损参考: {sar_str}
- ATR波动参考: {atr_str} ({indicators.get('atr_percent', 0):.1f}%)

**多维度评分详情:**
- 趋势方向维度: {dimensions.get('trend', 0):.1f}/100
- 动量指标维度: {dimensions.get('momentum', 0):.1f}/100
- 成交量分析维度: {dimensions.get('volume', 0):.1f}/100
- 波动性维度: {dimensions.get('volatility', 0):.1f}/100
- 支撑压力维度: {dimensions.get('support_resistance', 0):.1f}/100
- 高级指标维度: {dimensions.get('advanced', 0):.1f}/100

---
# 技术指标数据

## 1. 趋势指标
- 移动平均线: MA5=${indicators.get('ma5', 0):.2f}, MA20=${indicators.get('ma20', 0):.2f}, MA50=${indicators.get('ma50', 0):.2f}
   - 趋势方向: {indicators.get('trend_direction', 'neutral')}
   - 趋势强度: {indicators.get('trend_strength', 0):.0f}%
- ADX: {indicators.get('adx', 0):.1f} (+DI={indicators.get('plus_di', 0):.1f}, -DI={indicators.get('minus_di', 0):.1f})
- SuperTrend: ${indicators.get('supertrend', 0):.2f} (方向: {indicators.get('supertrend_direction', 'neutral')})
- Ichimoku云层: {indicators.get('ichimoku_status', 'unknown')}
- SAR止损位: ${indicators.get('sar', 0):.2f}

## 2. 动量指标
- RSI(14): {indicators.get('rsi', 0):.1f}
- MACD: {indicators.get('macd', 0):.3f} (信号: {indicators.get('macd_signal', 0):.3f}, 柱状图: {indicators.get('macd_histogram', 0):.3f})
- KDJ: K={indicators.get('kdj_k', 0):.1f}, D={indicators.get('kdj_d', 0):.1f}, J={indicators.get('kdj_j', 0):.1f}
- CCI: {indicators.get('cci', 0):.1f}
- StochRSI: K={indicators.get('stoch_rsi_k', 0):.1f}, D={indicators.get('stoch_rsi_d', 0):.1f} (状态: {indicators.get('stoch_rsi_status', 'neutral')})
- 威廉指标: {indicators.get('williams_r', 0):.1f}

## 3. 波动性指标
- 布林带: 上轨=${indicators.get('bb_upper', 0):.2f}, 中轨=${indicators.get('bb_middle', 0):.2f}, 下轨=${indicators.get('bb_lower', 0):.2f}
- ATR: ${indicators.get('atr', 0):.2f} ({indicators.get('atr_percent', 0):.1f}%)
- 20日波动率: {indicators.get('volatility_20', 0):.2f}%

## 4. 成交量分析
- 成交量比率: {indicators.get('volume_ratio', 0):.2f}x (当前/20日均量)
- OBV趋势: {indicators.get('obv_trend', 'neutral')}
- 价量关系: {indicators.get('price_volume_confirmation', 'neutral')}
- Volume Profile: POC=${indicators.get('vp_poc', 0):.2f}, 状态={indicators.get('vp_status', 'neutral')}

## 5. 支撑压力位
- 20日高点: ${indicators.get('resistance_20d_high', 0):.2f}
- 20日低点: ${indicators.get('support_20d_low', 0):.2f}
- 枢轴点: ${indicators.get('pivot', 0):.2f}
- 斐波那契回撤: 23.6%=${indicators.get('fib_23.6', 0):.2f}, 38.2%=${indicators.get('fib_38.2', 0):.2f}, 61.8%=${indicators.get('fib_61.8', 0):.2f}

## 6. 其他指标
   - 连续上涨天数: {indicators.get('consecutive_up_days', 0)}
   - 连续下跌天数: {indicators.get('consecutive_down_days', 0)}
- ML预测: {indicators.get('ml_trend', 'unknown')} (置信度: {indicators.get('ml_confidence', 0):.1f}%, 预期: {indicators.get('ml_prediction', 0)*100:.2f}%)

---
# 分析任务

请按照以下结构提供纯技术分析，每个部分都要有深度：

## 一、多维度评分解读

基于系统提供的多维度评分结果，详细分析各维度的技术含义：

1. **趋势方向维度** ({dimensions.get('trend', 0):.1f}/100)
   - 解释当前趋势状态及其强度
   - 分析MA均线排列、ADX、SuperTrend的综合指示
   - 判断趋势的可靠性和持续性

2. **动量指标维度** ({dimensions.get('momentum', 0):.1f}/100)
   - 分析RSI、MACD、KDJ等动量指标的综合信号
   - 评估当前市场动能状态
   - 识别可能的反转或延续信号

3. **成交量分析维度** ({dimensions.get('volume', 0):.1f}/100)
   - 深入分析价量关系
   - 评估成交量的健康度和趋势确认作用
   - 分析筹码分布情况

4. **波动性维度** ({dimensions.get('volatility', 0):.1f}/100)
   - 评估当前波动率水平对交易的影响
   - 分析布林带位置显示的短期价格区间
   - 给出风险控制建议

5. **支撑压力维度** ({dimensions.get('support_resistance', 0):.1f}/100)
   - 识别关键支撑位和压力位
   - 评估当前价格位置
   - 预测可能的突破或反弹点位

## 二、技术面深度分析

1. **趋势分析**
   - 当前趋势方向、强度和可持续性
   - 关键均线的支撑/阻力作用
   - ADX显示的trend strength

2. **动量分析**
   - 各项动量指标的共振情况
   - 超买超卖状态及其可能影响
   - 可能的反转时点和信号

3. **成交量验证**
   - 成交量是否支持当前趋势
   - 价量背离的风险提示
   - 资金流向分析

4. **波动性评估**
   - ATR显示的波动风险
   - 布林带宽度和价格位置
   - 止损止盈位设置建议

## 三、综合分析结论

1. **买卖建议**
   - 基于多维度评分系统的综合判断
   - 明确的操作建议及理由

2. **具体操作价位（必须明确给出）**
   
   **如果建议买入:**
   - **建议买入价位:** $[具体价格或价格区间，例如: $150.50 或 $149.00-$151.00]
     - 说明：为什么选择这个价位？基于什么技术指标？（如支撑位、均线、布林带等）
   - **建议止损价位:** $[具体价格，例如: $147.00]
     - 说明：基于什么计算？（SAR=${indicators.get('sar', 0):.2f}、ATR=${indicators.get('atr', 0):.2f}、支撑位等）
     - 止损百分比: [X]% （相对于买入价）
   - **建议止盈价位:** $[具体价格，例如: $158.00]
     - 说明：基于什么计算？（压力位、阻力位、目标价等）
     - 止盈百分比: [X]% （相对于买入价）
     - 风险收益比: 1:[X] （止盈空间/止损空间）
   
   **如果建议卖出:**
   - **建议卖出价位:** $[具体价格或价格区间]
     - 说明：为什么选择这个价位？
   - **止损/保护价位:** $[如果卖出后可能上涨，设置保护价位]
   
   **如果建议观望:**
   - **等待的买入价位:** $[如果价格达到这个价位才考虑买入]
   - **等待的卖出价位:** $[如果价格达到这个价位才考虑卖出]

3. **风险提示**
   - 技术风险点（高波动、趋势不明、背离等）
   - 纯技术分析的局限性
   - 综合风险评估
   - 止损位设置的理由和风险控制说明

4. **仓位和资金管理**
   - 建议仓位大小（根据风险等级和资金情况）
   - 分批建仓建议（如有）
   - 资金管理建议（根据风险等级）

5. **市场展望**
   - 短期价格走势预测
   - 中期趋势展望
   - 不同市场情境下的应对策略

---
# 输出要求

1. **结构清晰**: 严格按照上述五个部分组织内容，使用明确的标题和分段
2. **数据引用**: 分析时要引用具体的技术指标数值
3. **逻辑严密**: 每个结论都要有数据支撑
4. **重点突出**: 对于评分高的维度要深入分析
5. **语言专业**: 使用专业术语但保持可读性
6. **建议明确**: 操作建议要具体可执行
7. **价位必须明确**: 在"具体操作价位"部分，必须明确给出具体的买入价位、止损价位和止盈价位，包括具体价格数字、百分比和风险收益比，不能只给建议不给具体价格

请开始分析。"""

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

