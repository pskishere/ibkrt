#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
回测模块 - 基于历史日期回测AI分析和交易操作规划
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from .settings import logger
from .yfinance import get_historical_data
from .analysis import (
    generate_signals,
    perform_ai_analysis,
    perform_trading_plan_analysis
)
# 导入技术指标计算函数
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


def simulate_stop_loss_take_profit(actual_data, entry_price, stop_loss, take_profit, action='buy', 
                                   commission_rate=0.0005, slippage_rate=0.0002):
    """
    模拟止损止盈触发并计算实际收益
    
    Args:
        actual_data: 实际价格数据列表
        entry_price: 入场价格
        stop_loss: 止损价位
        take_profit: 止盈价位
        action: 操作类型 'buy' 或 'sell'
        commission_rate: 佣金费率（默认0.05%）
        slippage_rate: 滑点费率（默认0.02%）
        
    Returns:
        模拟结果字典
    """
    result = {
        'entry_price': float(entry_price),
        'stop_loss': float(stop_loss),
        'take_profit': float(take_profit),
        'action': action,
        'triggered': False,
        'exit_type': None,  # 'stop_loss', 'take_profit', 'hold'
        'exit_price': None,
        'exit_day': None,
        'holding_days': 0,
        'gross_return_percent': 0.0,
        'net_return_percent': 0.0,
        'total_cost_percent': 0.0
    }
    
    if not actual_data:
        return result
    
    # 计算入场成本（佣金+滑点）
    entry_cost_rate = commission_rate + slippage_rate
    
    for idx, bar in enumerate(actual_data):
        high = bar.get('high', bar.get('close'))
        low = bar.get('low', bar.get('close'))
        close = bar.get('close')
        
        if action == 'buy':
            # 买入场景：检查是否触及止损或止盈
            if low <= stop_loss:
                # 触发止损
                result['triggered'] = True
                result['exit_type'] = 'stop_loss'
                result['exit_price'] = float(stop_loss * (1 - slippage_rate))  # 考虑滑点
                result['exit_day'] = idx + 1
                result['holding_days'] = idx + 1
                gross_return = (result['exit_price'] - entry_price) / entry_price * 100
                exit_cost_rate = commission_rate + slippage_rate
                result['gross_return_percent'] = float(gross_return)
                result['total_cost_percent'] = float((entry_cost_rate + exit_cost_rate) * 100)
                result['net_return_percent'] = float(gross_return - result['total_cost_percent'])
                break
            elif high >= take_profit:
                # 触发止盈
                result['triggered'] = True
                result['exit_type'] = 'take_profit'
                result['exit_price'] = float(take_profit * (1 - slippage_rate))  # 考虑滑点
                result['exit_day'] = idx + 1
                result['holding_days'] = idx + 1
                gross_return = (result['exit_price'] - entry_price) / entry_price * 100
                exit_cost_rate = commission_rate + slippage_rate
                result['gross_return_percent'] = float(gross_return)
                result['total_cost_percent'] = float((entry_cost_rate + exit_cost_rate) * 100)
                result['net_return_percent'] = float(gross_return - result['total_cost_percent'])
                break
        else:  # sell
            # 卖出场景：检查是否触及止损或止盈
            if high >= stop_loss:
                # 触发止损
                result['triggered'] = True
                result['exit_type'] = 'stop_loss'
                result['exit_price'] = float(stop_loss * (1 + slippage_rate))  # 考虑滑点
                result['exit_day'] = idx + 1
                result['holding_days'] = idx + 1
                gross_return = (entry_price - result['exit_price']) / entry_price * 100
                exit_cost_rate = commission_rate + slippage_rate
                result['gross_return_percent'] = float(gross_return)
                result['total_cost_percent'] = float((entry_cost_rate + exit_cost_rate) * 100)
                result['net_return_percent'] = float(gross_return - result['total_cost_percent'])
                break
            elif low <= take_profit:
                # 触发止盈
                result['triggered'] = True
                result['exit_type'] = 'take_profit'
                result['exit_price'] = float(take_profit * (1 + slippage_rate))  # 考虑滑点
                result['exit_day'] = idx + 1
                result['holding_days'] = idx + 1
                gross_return = (entry_price - result['exit_price']) / entry_price * 100
                exit_cost_rate = commission_rate + slippage_rate
                result['gross_return_percent'] = float(gross_return)
                result['total_cost_percent'] = float((entry_cost_rate + exit_cost_rate) * 100)
                result['net_return_percent'] = float(gross_return - result['total_cost_percent'])
                break
    
    # 如果没有触发止损止盈，使用最后价格
    if not result['triggered'] and actual_data:
        last_bar = actual_data[-1]
        last_price = last_bar.get('close')
        result['exit_type'] = 'hold'
        result['exit_price'] = float(last_price)
        result['holding_days'] = len(actual_data)
        
        if action == 'buy':
            gross_return = (last_price - entry_price) / entry_price * 100
        else:
            gross_return = (entry_price - last_price) / entry_price * 100
        
        exit_cost_rate = commission_rate + slippage_rate
        result['gross_return_percent'] = float(gross_return)
        result['total_cost_percent'] = float((entry_cost_rate + exit_cost_rate) * 100)
        result['net_return_percent'] = float(gross_return - result['total_cost_percent'])
    
    return result


def filter_data_by_date(hist_data, end_date_str):
    """
    根据结束日期过滤历史数据
    
    Args:
        hist_data: 历史数据列表，每个元素包含 'date' 字段
        end_date_str: 结束日期字符串，格式 'YYYY-MM-DD' 或 'YYYYMMDD'
        
    Returns:
        过滤后的历史数据列表（只包含end_date之前的数据）
    """
    try:
        # 解析结束日期
        if len(end_date_str) == 8:
            end_date = datetime.strptime(end_date_str, '%Y%m%d').date()
        elif len(end_date_str) == 10:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            logger.error(f"日期格式错误: {end_date_str}")
            return None
        
        # 过滤数据
        filtered_data = []
        for bar in hist_data:
            date_str = bar.get('date', '')
            try:
                if len(date_str) == 8:
                    bar_date = datetime.strptime(date_str, '%Y%m%d').date()
                elif ' ' in date_str:
                    bar_date = datetime.strptime(date_str.split(' ')[0], '%Y%m%d').date()
                else:
                    continue
                
                if bar_date < end_date:
                    filtered_data.append(bar)
            except Exception as e:
                logger.warning(f"解析日期失败: {date_str}, 错误: {e}")
                continue
        
        return filtered_data
    except Exception as e:
        logger.error(f"过滤数据失败: {e}")
        return None


def get_actual_price_data(symbol, end_date_str):
    """
    获取回测结束日期之后的实际价格数据（从结束日期到当前的所有数据）
    
    Args:
        symbol: 股票代码
        end_date_str: 结束日期字符串
        
    Returns:
        实际价格数据字典
    """
    try:
        # 解析结束日期
        if len(end_date_str) == 8:
            end_date = datetime.strptime(end_date_str, '%Y%m%d').date()
        elif len(end_date_str) == 10:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            logger.error(f"日期格式错误: {end_date_str}")
            return None
        
        # 获取实际数据 - 使用较长的周期以确保获取所有后续数据
        hist_data, error = get_historical_data(symbol, '1 Y', '1 day')
        if error or not hist_data:
            return None
        
        # 筛选结束日期之后的所有数据
        actual_data = []
        for bar in hist_data:
            date_str = bar.get('date', '')
            try:
                if len(date_str) == 8:
                    bar_date = datetime.strptime(date_str, '%Y%m%d').date()
                elif ' ' in date_str:
                    bar_date = datetime.strptime(date_str.split(' ')[0], '%Y%m%d').date()
                else:
                    continue
                
                # 获取结束日期之后的所有数据
                if bar_date > end_date:
                    actual_data.append({
                        'date': bar_date.strftime('%Y-%m-%d'),
                        'open': bar.get('open', 0),
                        'high': bar.get('high', 0),
                        'low': bar.get('low', 0),
                        'close': bar.get('close', 0),
                        'volume': bar.get('volume', 0),
                    })
            except Exception as e:
                logger.warning(f"解析日期失败: {date_str}, 错误: {e}")
                continue
        
        return actual_data
    except Exception as e:
        logger.error(f"获取实际价格数据失败: {e}")
        return None


def calculate_indicators_from_data(hist_data, symbol):
    """
    基于历史数据列表计算技术指标（用于回测）
    
    Args:
        hist_data: 历史数据列表
        symbol: 股票代码
        
    Returns:
        技术指标字典
    """
    if not hist_data or len(hist_data) < 20:
        return None
    
    closes = np.array([bar['close'] for bar in hist_data])
    highs = np.array([bar['high'] for bar in hist_data])
    lows = np.array([bar['low'] for bar in hist_data])
    volumes = np.array([bar['volume'] for bar in hist_data])
    
    result = {
        'symbol': symbol,
        'current_price': float(closes[-1]),
        'data_points': int(len(closes)),
    }
    
    # 计算各种技术指标（与 calculate_technical_indicators 相同）
    ma_data = calculate_ma(closes)
    result.update(ma_data)
    
    rsi_data = calculate_rsi(closes)
    result.update(rsi_data)
    
    bb_data = calculate_bollinger(closes)
    result.update(bb_data)
    
    macd_data = calculate_macd(closes)
    result.update(macd_data)
    
    volume_data = calculate_volume(volumes)
    result.update(volume_data)
    
    price_change_data = calculate_price_change(closes)
    result.update(price_change_data)
    
    volatility_data = calculate_volatility(closes)
    result.update(volatility_data)
    
    support_resistance = calculate_support_resistance(closes, highs, lows)
    result.update(support_resistance)
    
    if len(closes) >= 9:
        kdj = calculate_kdj(closes, highs, lows)
        result.update(kdj)
    
    if len(closes) >= 14:
        atr = calculate_atr(closes, highs, lows)
        result['atr'] = atr
        result['atr_percent'] = float((atr / closes[-1]) * 100)
    
    if len(closes) >= 14:
        wr = calculate_williams_r(closes, highs, lows)
        result['williams_r'] = wr
    
    if len(volumes) >= 20:
        obv = calculate_obv(closes, volumes)
        result['obv_current'] = float(obv[-1]) if len(obv) > 0 else 0.0
        result['obv_trend'] = get_trend(obv[-10:]) if len(obv) >= 10 else 'neutral'
    
    trend_info = analyze_trend_strength(closes, highs, lows)
    result.update(trend_info)
    
    fibonacci_levels = calculate_fibonacci_retracement(highs, lows)
    result.update(fibonacci_levels)
    
    if len(closes) >= 14:
        cci_data = calculate_cci(closes, highs, lows)
        result.update(cci_data)
    
    if len(closes) >= 28:
        adx_data = calculate_adx(closes, highs, lows)
        result.update(adx_data)
    
    if len(closes) >= 10:
        sar_data = calculate_sar(closes, highs, lows)
        result.update(sar_data)
    
    if len(closes) >= 11:
        st_data = calculate_supertrend(closes, highs, lows)
        result.update(st_data)
    
    if len(closes) >= 28:
        stoch_rsi_data = calculate_stoch_rsi(closes)
        result.update(stoch_rsi_data)
    
    if len(closes) >= 20:
        vp_data = calculate_volume_profile(closes, highs, lows, volumes)
        result.update(vp_data)
    
    if len(closes) >= 52:
        ichimoku_data = calculate_ichimoku(closes, highs, lows)
        result.update(ichimoku_data)
    
    valid_volumes = volumes[volumes > 0]
    if len(closes) >= 20 and len(valid_volumes) > 0:
        ml_data = calculate_ml_predictions(closes, highs, lows, volumes)
        result.update(ml_data)
    
    return result


def backtest_analysis(symbol, end_date_str, duration='3 M', bar_size='1 day',
                     model='deepseek-v3.1:671b-cloud'):
    """
    回测AI分析 - 基于历史日期进行分析并对比实际结果
    
    Args:
        symbol: 股票代码
        end_date_str: 回测结束日期，格式 'YYYY-MM-DD' 或 'YYYYMMDD'
        duration: 数据周期，默认 '3 M'
        bar_size: K线周期，默认 '1 day'
        model: AI模型名称
        
    Returns:
        回测结果字典，包含预测和实际结果对比
    """
    try:
        logger.info(f"开始回测分析: {symbol}, 结束日期={end_date_str}")
        
        # 1. 获取所有历史数据
        hist_data, error = get_historical_data(symbol, duration, bar_size)
        if error or not hist_data:
            return {
                'success': False,
                'message': f'获取历史数据失败: {error.get("message", "未知错误") if error else "数据为空"}'
            }
        
        # 2. 过滤出结束日期之前的数据
        filtered_data = filter_data_by_date(hist_data, end_date_str)
        if not filtered_data or len(filtered_data) < 20:
            return {
                'success': False,
                'message': f'结束日期{end_date_str}之前的数据不足（需要至少20个数据点，实际{len(filtered_data) if filtered_data else 0}个）'
            }
        
        # 3. 基于过滤后的数据计算技术指标
        indicators = calculate_indicators_from_data(filtered_data, symbol)
        if not indicators:
            return {
                'success': False,
                'message': '计算技术指标失败'
            }
        
        # 4. 生成交易信号
        signals = generate_signals(indicators)
        
        # 5. 执行AI分析（基于历史数据）
        ai_analysis = perform_ai_analysis(symbol, indicators, signals, duration, model)
        
        # 6. 获取实际价格数据（结束日期之后）
        actual_data = get_actual_price_data(symbol, end_date_str)
        
        # 7. 分析实际结果并模拟止损止盈
        actual_result = None
        simulation_result = None
        if actual_data and len(actual_data) > 0:
            # 解析结束日期
            if len(end_date_str) == 8:
                end_date = datetime.strptime(end_date_str, '%Y%m%d').date()
            else:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            # 获取回测日期的价格和止损止盈信息
            backtest_price = indicators.get('current_price', 0)
            stop_loss = signals.get('stop_loss', backtest_price * 0.95)
            take_profit = signals.get('take_profit', backtest_price * 1.10)
            
            # 模拟止损止盈触发（假设买入）
            simulation_result = simulate_stop_loss_take_profit(
                actual_data,
                entry_price=backtest_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                action='buy',
                commission_rate=0.0005,  # 0.05% 佣金
                slippage_rate=0.0002     # 0.02% 滑点
            )
            
            # 获取实际价格走势
            actual_prices = [bar['close'] for bar in actual_data]
            max_price = max(actual_prices) if actual_prices else backtest_price
            min_price = min(actual_prices) if actual_prices else backtest_price
            final_price = actual_prices[-1] if actual_prices else backtest_price
            
            price_change = ((final_price - backtest_price) / backtest_price) * 100 if backtest_price > 0 else 0
            max_change = ((max_price - backtest_price) / backtest_price) * 100 if backtest_price > 0 else 0
            min_change = ((min_price - backtest_price) / backtest_price) * 100 if backtest_price > 0 else 0
            
            # 计算更多统计信息
            today = datetime.now().date()
            days_passed = (today - end_date).days if actual_data else 0
            
            # 分析价格趋势
            if len(actual_prices) > 1:
                # 计算涨跌天数
                up_days = sum(1 for i in range(1, len(actual_prices)) if actual_prices[i] > actual_prices[i-1])
                down_days = sum(1 for i in range(1, len(actual_prices)) if actual_prices[i] < actual_prices[i-1])
                
                # 计算平均日涨跌幅
                daily_changes = []
                for i in range(1, len(actual_prices)):
                    if actual_prices[i-1] > 0:
                        daily_change = ((actual_prices[i] - actual_prices[i-1]) / actual_prices[i-1]) * 100
                        daily_changes.append(daily_change)
                avg_daily_change = sum(daily_changes) / len(daily_changes) if daily_changes else 0
            else:
                up_days = 0
                down_days = 0
                avg_daily_change = 0
            
            actual_result = {
                'backtest_price': backtest_price,
                'final_price': final_price,
                'max_price': max_price,
                'min_price': min_price,
                'price_change_pct': price_change,
                'max_change_pct': max_change,
                'min_change_pct': min_change,
                'days_passed': days_passed,
                'up_days': up_days,
                'down_days': down_days,
                'avg_daily_change': avg_daily_change,
                'actual_data': actual_data,
                'stop_loss_take_profit_simulation': simulation_result
            }
        
        return {
            'success': True,
            'symbol': symbol.upper(),
            'backtest_date': end_date_str,
            'historical_data_points': len(filtered_data),
            'actual_data_points': len(actual_data) if actual_data else 0,
            'indicators': indicators,
            'signals': signals,
            'ai_analysis': ai_analysis,
            'actual_result': actual_result,
            'prediction_price': indicators.get('current_price', 0),
        }
        
    except Exception as e:
        logger.error(f"回测分析失败: {e}", exc_info=True)
        return {
            'success': False,
            'message': f'回测分析失败: {str(e)}'
        }


def backtest_trading_plan(symbol, end_date_str, planning_period='未来2周',
                         allow_day_trading=False, current_position_percent=0.0,
                         duration='3 M', bar_size='1 day',
                         model='deepseek-v3.1:671b-cloud'):
    """
    回测交易操作规划 - 基于历史日期进行规划并对比实际结果
    
    Args:
        symbol: 股票代码
        end_date_str: 回测结束日期
        planning_period: 规划周期描述
        allow_day_trading: 是否允许日内交易
        current_position_percent: 当前持有仓位百分比
        duration: 数据周期
        bar_size: K线周期
        model: AI模型名称
        
    Returns:
        回测结果字典
    """
    try:
        logger.info(f"开始回测交易操作规划: {symbol}, 结束日期={end_date_str}")
        
        # 1. 获取所有历史数据
        hist_data, error = get_historical_data(symbol, duration, bar_size)
        if error or not hist_data:
            return {
                'success': False,
                'message': f'获取历史数据失败: {error.get("message", "未知错误") if error else "数据为空"}'
            }
        
        # 2. 过滤出结束日期之前的数据
        filtered_data = filter_data_by_date(hist_data, end_date_str)
        if not filtered_data or len(filtered_data) < 20:
            return {
                'success': False,
                'message': f'结束日期{end_date_str}之前的数据不足（需要至少20个数据点，实际{len(filtered_data) if filtered_data else 0}个）'
            }
        
        # 3. 基于过滤后的数据计算技术指标
        indicators = calculate_indicators_from_data(filtered_data, symbol)
        if not indicators:
            return {
                'success': False,
                'message': '计算技术指标失败'
            }
        
        # 4. 生成交易信号
        signals = generate_signals(indicators)
        
        # 5. 执行交易操作规划分析（基于历史数据）
        trading_plan = perform_trading_plan_analysis(
            symbol,
            indicators,
            signals,
            planning_period=planning_period,
            allow_day_trading=allow_day_trading,
            current_position_percent=current_position_percent,
            model=model
        )
        
        # 6. 获取实际价格数据（结束日期之后）
        actual_data = get_actual_price_data(symbol, end_date_str)
        
        # 7. 分析实际结果并模拟止损止盈
        actual_result = None
        simulation_result = None
        if actual_data and len(actual_data) > 0:
            # 解析结束日期
            if len(end_date_str) == 8:
                end_date = datetime.strptime(end_date_str, '%Y%m%d').date()
            else:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            # 获取回测日期的价格和止损止盈信息
            backtest_price = indicators.get('current_price', 0)
            stop_loss = signals.get('stop_loss', backtest_price * 0.95)
            take_profit = signals.get('take_profit', backtest_price * 1.10)
            
            # 模拟止损止盈触发（假设买入）
            simulation_result = simulate_stop_loss_take_profit(
                actual_data,
                entry_price=backtest_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                action='buy',
                commission_rate=0.0005,  # 0.05% 佣金
                slippage_rate=0.0002     # 0.02% 滑点
            )
            
            # 获取实际价格走势
            actual_prices = [bar['close'] for bar in actual_data]
            max_price = max(actual_prices) if actual_prices else backtest_price
            min_price = min(actual_prices) if actual_prices else backtest_price
            final_price = actual_prices[-1] if actual_prices else backtest_price
            
            price_change = ((final_price - backtest_price) / backtest_price) * 100 if backtest_price > 0 else 0
            max_change = ((max_price - backtest_price) / backtest_price) * 100 if backtest_price > 0 else 0
            min_change = ((min_price - backtest_price) / backtest_price) * 100 if backtest_price > 0 else 0
            
            # 计算更多统计信息
            today = datetime.now().date()
            days_passed = (today - end_date).days if end_date and actual_data else 0
            
            # 分析价格趋势
            if len(actual_prices) > 1:
                # 计算涨跌天数
                up_days = sum(1 for i in range(1, len(actual_prices)) if actual_prices[i] > actual_prices[i-1])
                down_days = sum(1 for i in range(1, len(actual_prices)) if actual_prices[i] < actual_prices[i-1])
                
                # 计算平均日涨跌幅
                daily_changes = []
                for i in range(1, len(actual_prices)):
                    if actual_prices[i-1] > 0:
                        daily_change = ((actual_prices[i] - actual_prices[i-1]) / actual_prices[i-1]) * 100
                        daily_changes.append(daily_change)
                avg_daily_change = sum(daily_changes) / len(daily_changes) if daily_changes else 0
            else:
                up_days = 0
                down_days = 0
                avg_daily_change = 0
            
            actual_result = {
                'backtest_price': backtest_price,
                'final_price': final_price,
                'max_price': max_price,
                'min_price': min_price,
                'price_change_pct': price_change,
                'max_change_pct': max_change,
                'min_change_pct': min_change,
                'days_passed': days_passed,
                'up_days': up_days,
                'down_days': down_days,
                'avg_daily_change': avg_daily_change,
                'actual_data': actual_data,
                'stop_loss_take_profit_simulation': simulation_result
            }
        
        return {
            'success': True,
            'symbol': symbol.upper(),
            'backtest_date': end_date_str,
            'planning_period': planning_period,
            'historical_data_points': len(filtered_data),
            'actual_data_points': len(actual_data) if actual_data else 0,
            'indicators': indicators,
            'signals': signals,
            'trading_plan': trading_plan,
            'actual_result': actual_result,
            'prediction_price': indicators.get('current_price', 0),
        }
        
    except Exception as e:
        logger.error(f"回测交易操作规划失败: {e}", exc_info=True)
        return {
            'success': False,
            'message': f'回测失败: {str(e)}'
        }

