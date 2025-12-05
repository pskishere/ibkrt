#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Flask应用主文件 - RESTful API服务
"""

import os
import json
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

from .settings import (
    logger, init_database, get_cached_analysis, save_analysis_cache,
    save_stock_info, get_hot_stocks
)
from .yfinance import get_stock_info, get_historical_data
from .analysis import (
    calculate_technical_indicators, generate_signals,
    check_ollama_available, perform_ai_analysis,
    perform_trading_plan_analysis
)
from .backtest import backtest_trading_plan

# 创建Flask应用
app = Flask(__name__)
CORS(app)


def _load_indicator_info():
    """
    从JSON文件加载技术指标解释和参考范围
    """
    try:
        json_path = os.path.join(os.path.dirname(__file__), 'indicators', 'indicator_info.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"未找到指标信息文件: {json_path}")
        return {}
    except Exception as e:
        logger.error(f"加载指标信息失败: {e}")
        return {}


@app.route('/api/health', methods=['GET'])
def health():
    """
    健康检查接口
    """
    return jsonify({
        'status': 'ok',
        'gateway': 'yfinance',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/analyze/<symbol>', methods=['GET'])
def analyze_stock(symbol):
    """
    技术分析 - 计算技术指标并生成买卖信号
    自动检测 Ollama 是否可用，如果可用则自动执行AI分析
    使用SQLite缓存当天的查询结果，避免重复查询
    
    查询参数:
    - duration: 数据周期 (默认: '3 M')
    - bar_size: K线周期 (默认: '1 day')
    - model: AI模型名称 (默认: 'deepseek-v3.1:671b-cloud')，仅在Ollama可用时使用
    """
    duration = request.args.get('duration', '3 M')
    bar_size = request.args.get('bar_size', '1 day')
    model = request.args.get('model', 'deepseek-v3.1:671b-cloud')
    
    symbol_upper = symbol.upper()
    
    # 先检查缓存中是否有当天的数据
    cached_result = get_cached_analysis(symbol_upper, duration, bar_size)
    if cached_result:
        # 如果缓存中有AI分析结果，直接返回
        if cached_result.get('ai_analysis'):
            return jsonify(cached_result)
        # 如果缓存中没有AI分析，但Ollama可用，则执行AI分析并更新缓存
        if check_ollama_available():
            logger.info(f"缓存中有数据但无AI分析，执行AI分析...")
            try:
                ai_analysis = perform_ai_analysis(
                    symbol_upper, 
                    cached_result['indicators'], 
                    cached_result['signals'], 
                    duration, 
                    model
                )
                cached_result['ai_analysis'] = ai_analysis
                cached_result['model'] = model
                cached_result['ai_available'] = True
                # 更新缓存
                save_analysis_cache(symbol_upper, duration, bar_size, cached_result)
            except Exception as e:
                logger.warning(f"AI分析执行失败: {e}")
                cached_result['ai_available'] = False
                cached_result['ai_error'] = str(e)
        return jsonify(cached_result)
    
    logger.info(f"技术分析: {symbol_upper}, {duration}, {bar_size}")
    
    try:
        stock_info = get_stock_info(symbol_upper)
        if stock_info:
            stock_name = None
            if isinstance(stock_info, dict):
                stock_name = stock_info.get('longName', '')
            elif isinstance(stock_info, list) and len(stock_info) > 0:
                stock_data = stock_info[0]
                if isinstance(stock_data, dict):
                    stock_name = stock_data.get('longName', '')
            
            if stock_name and stock_name.strip() and stock_name != symbol_upper:
                save_stock_info(symbol_upper, stock_name.strip())
    except Exception as e:
        logger.warning(f"获取股票信息失败: {e}")
    
    hist_data, hist_error = get_historical_data(symbol_upper, duration, bar_size)
    indicators, ind_error = calculate_technical_indicators(symbol_upper, duration, bar_size)
    
    if ind_error:
        return jsonify({
            'success': False,
            'error_code': ind_error['code'],
            'message': ind_error['message']
        }), 400
    
    if not indicators:
        return jsonify({
            'success': False,
            'message': '数据不足，无法计算技术指标'
        }), 404
    
    # 生成买卖信号
    signals = generate_signals(indicators)
    
    # 格式化K线数据
    formatted_candles = []
    if hist_data:
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
    
    result = {
        'success': True,
        'indicators': indicators,
        'signals': signals,
        'candles': formatted_candles
    }
    
    if check_ollama_available():
        logger.info(f"检测到 Ollama 可用，开始AI分析...")
        try:
            ai_analysis = perform_ai_analysis(symbol_upper, indicators, signals, duration, model)
            result['ai_analysis'] = ai_analysis
            result['model'] = model
            result['ai_available'] = True
        except Exception as e:
            logger.warning(f"AI分析执行失败: {e}")
            result['ai_available'] = False
            result['ai_error'] = str(e)
    else:
        logger.info("Ollama 不可用，跳过AI分析")
        result['ai_available'] = False
    
    # 保存到缓存
    save_analysis_cache(symbol_upper, duration, bar_size, result)
    
    return jsonify(result)


@app.route('/api/refresh-analyze/<symbol>', methods=['POST'])
def refresh_analyze_stock(symbol):
    """
    刷新技术分析 - 强制重新获取数据并分析，不使用缓存
    自动检测 Ollama 是否可用，如果可用则自动执行AI分析
    
    查询参数:
    - duration: 数据周期 (默认: '3 M')
    - bar_size: K线周期 (默认: '1 day')
    - model: AI模型名称 (默认: 'deepseek-v3.1:671b-cloud')，仅在Ollama可用时使用
    """
    duration = request.args.get('duration', '3 M')
    bar_size = request.args.get('bar_size', '1 day')
    model = request.args.get('model', 'deepseek-v3.1:671b-cloud')
    
    symbol_upper = symbol.upper()
    
    logger.info(f"刷新技术分析（强制重新获取）: {symbol_upper}, {duration}, {bar_size}")
    
    # 获取股票信息并保存到数据库
    try:
        stock_info = get_stock_info(symbol_upper)
        if stock_info:
            stock_name = None
            # 处理返回的数据结构
            if isinstance(stock_info, dict):
                stock_name = stock_info.get('longName', '')
            elif isinstance(stock_info, list) and len(stock_info) > 0:
                # 如果返回的是列表，取第一个
                stock_data = stock_info[0]
                if isinstance(stock_data, dict):
                    stock_name = stock_data.get('longName', '')
            
            # 如果有有效的股票名称，保存到数据库
            if stock_name and stock_name.strip() and stock_name != symbol_upper:
                save_stock_info(symbol_upper, stock_name.strip())
    except Exception as e:
        logger.warning(f"获取股票信息失败: {e}")
    
    # 获取历史K线数据
    hist_data, hist_error = get_historical_data(symbol_upper, duration, bar_size)
    
    # 计算技术指标
    indicators, ind_error = calculate_technical_indicators(symbol_upper, duration, bar_size)
    
    # 检查是否有错误（如证券不存在）
    if ind_error:
        return jsonify({
            'success': False,
            'error_code': ind_error['code'],
            'message': ind_error['message']
        }), 400
    
    if not indicators:
        return jsonify({
            'success': False,
            'message': '数据不足，无法计算技术指标'
        }), 404
    
    # 生成买卖信号
    signals = generate_signals(indicators)
    
    # 格式化K线数据
    formatted_candles = []
    if hist_data:
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
    
    result = {
        'success': True,
        'indicators': indicators,
        'signals': signals,
        'candles': formatted_candles
    }
    
    if check_ollama_available():
        logger.info(f"检测到 Ollama 可用，开始AI分析...")
        try:
            ai_analysis = perform_ai_analysis(symbol_upper, indicators, signals, duration, model)
            result['ai_analysis'] = ai_analysis
            result['model'] = model
            result['ai_available'] = True
        except Exception as e:
            logger.warning(f"AI分析执行失败: {e}")
            result['ai_available'] = False
            result['ai_error'] = str(e)
    else:
        logger.info("Ollama 不可用，跳过AI分析")
        result['ai_available'] = False
    
    # 保存到缓存（更新缓存）
    save_analysis_cache(symbol_upper, duration, bar_size, result)
    
    return jsonify(result)


@app.route('/api/hot-stocks', methods=['GET'])
def hot_stocks_endpoint():
    """
    获取热门股票代码列表（从SQLite数据库查询过的股票中获取）
    查询参数:
    - limit: 返回数量限制 (默认: 20)
    """
    limit = int(request.args.get('limit', 20))
    
    try:
        hot_stocks = get_hot_stocks(limit)
        return jsonify({
            'success': True,
            'market': 'US',
            'count': len(hot_stocks),
            'stocks': hot_stocks
        })
    except Exception as e:
        logger.error(f"查询热门股票失败: {e}")
        return jsonify({
            'success': True,
            'market': 'US',
            'count': 0,
            'stocks': []
        })


@app.route('/api/indicator-info', methods=['GET'])
def get_indicator_info():
    """
    获取技术指标解释和参考范围
    查询参数:
    - indicator: 指标名称（可选），不提供则返回所有指标信息
    """
    indicator_name = request.args.get('indicator', '').lower()
    
    # 从JSON文件加载技术指标的解释和参考范围
    indicator_info = _load_indicator_info()
    
    if not indicator_info:
        return jsonify({
            'success': False,
            'message': '指标信息文件加载失败'
        }), 500
    
    # 如果指定了指标名称，只返回该指标信息
    if indicator_name:
        if indicator_name in indicator_info:
            return jsonify({
                'success': True,
                'indicator': indicator_name,
                'info': indicator_info[indicator_name]
            })
        else:
            return jsonify({
                'success': False,
                'message': f'未找到指标: {indicator_name}'
            }), 404
    
    # 返回所有指标信息
    return jsonify({
        'success': True,
        'indicators': indicator_info
    })


@app.route('/api/trading-plan/<symbol>', methods=['POST'])
def trading_plan_analysis(symbol):
    """
    AI交易操作规划分析 - 围绕关键价位生成操作规划
    
    请求体 JSON:
    {
        "planning_period": "未来2周",   # 规划周期描述 (默认: "未来2周")
        "allow_day_trading": false,     # 是否允许日内交易 (默认: false)
        "current_position_percent": 0.0,  # 当前持有仓位百分比 (默认: 0.0，表示未持仓)
        "duration": "3 M",              # 数据周期 (默认: '3 M')
        "bar_size": "1 day",            # K线周期 (默认: '1 day')
        "model": "deepseek-v3.1:671b-cloud"  # AI模型名称 (默认: 'deepseek-v3.1:671b-cloud')
    }
    """
    symbol_upper = symbol.upper()
    
    # 获取请求参数
    data = request.get_json() or {}
    planning_period = data.get('planning_period', '未来2周')
    allow_day_trading = bool(data.get('allow_day_trading', False))
    current_position_percent = float(data.get('current_position_percent', 0.0))
    current_position_cost = float(data.get('current_position_cost', 0.0))  # 持仓成本价
    current_position_quantity = int(data.get('current_position_quantity', 0))  # 持仓数量
    account_value = float(data.get('account_value', 100000))  # 账户金额
    risk_percent = float(data.get('risk_percent', 2.0))  # 风险百分比
    duration = data.get('duration', '3 M')
    bar_size = data.get('bar_size', '1 day')
    model = data.get('model', 'deepseek-v3.1:671b-cloud')
    
    # 验证参数
    if not planning_period or len(planning_period.strip()) == 0:
        return jsonify({
            'success': False,
            'message': '规划周期不能为空'
        }), 400
    
    if current_position_percent < 0 or current_position_percent > 100:
        return jsonify({
            'success': False,
            'message': '当前持有仓位百分比必须在0-100之间'
        }), 400
    
    if account_value <= 0:
        return jsonify({
            'success': False,
            'message': '账户金额必须大于0'
        }), 400
    
    if risk_percent <= 0 or risk_percent > 10:
        return jsonify({
            'success': False,
            'message': '风险百分比必须在0-10之间'
        }), 400
    
    logger.info(f"交易操作规划分析: {symbol_upper}, 规划周期={planning_period}, 日内交易={allow_day_trading}, 当前仓位={current_position_percent}%")
    
    # 检查Ollama是否可用
    if not check_ollama_available():
        return jsonify({
            'success': False,
            'message': 'Ollama不可用，无法执行AI分析',
            'ai_available': False
        }), 503
    
    try:
        # 获取技术指标和信号
        indicators, ind_error = calculate_technical_indicators(symbol_upper, duration, bar_size)
        
        if ind_error:
            return jsonify({
                'success': False,
                'error_code': ind_error['code'],
                'message': ind_error['message']
            }), 400
        
        if not indicators:
            return jsonify({
                'success': False,
                'message': '数据不足，无法计算技术指标'
            }), 404
        
        # 生成买卖信号（传入账户和风险参数）
        signals = generate_signals(indicators, account_value=account_value, risk_percent=risk_percent)
        
        # 计算持仓盈亏（如果有持仓）
        position_pnl = None
        if current_position_quantity > 0 and current_position_cost > 0:
            current_price = indicators.get('current_price', 0)
            if current_price > 0:
                position_value = current_position_quantity * current_price
                cost_value = current_position_quantity * current_position_cost
                pnl = position_value - cost_value
                pnl_percent = (pnl / cost_value) * 100 if cost_value > 0 else 0
                position_pnl = {
                    'quantity': current_position_quantity,
                    'cost_price': current_position_cost,
                    'current_price': current_price,
                    'cost_value': cost_value,
                    'current_value': position_value,
                    'pnl': pnl,
                    'pnl_percent': pnl_percent
                }
        
        # 执行交易操作规划分析
        trading_plan = perform_trading_plan_analysis(
            symbol_upper,
            indicators,
            signals,
            planning_period=planning_period,
            allow_day_trading=allow_day_trading,
            current_position_percent=current_position_percent,
            model=model
        )
        
        return jsonify({
            'success': True,
            'symbol': symbol_upper,
            'planning_period': planning_period,
            'allow_day_trading': allow_day_trading,
            'current_position_percent': current_position_percent,
            'account_value': account_value,
            'risk_percent': risk_percent,
            'position_pnl': position_pnl,
            'indicators': indicators,
            'signals': signals,
            'trading_plan': trading_plan,
            'model': model,
            'ai_available': True
        })
        
    except Exception as e:
        logger.error(f"交易操作规划分析失败: {e}")
        return jsonify({
            'success': False,
            'message': f'交易操作规划分析失败: {str(e)}',
            'ai_available': False
        }), 500


@app.route('/api/backtest-trading-plan/<symbol>', methods=['POST'])
def backtest_trading_plan_api(symbol):
    """
    交易操作规划回测 - 基于历史日期回测交易操作规划结果
    
    请求体 JSON:
    {
        "end_date": "2024-01-15",           # 回测结束日期 (格式: YYYY-MM-DD 或 YYYYMMDD)
        "planning_period": "未来2周",        # 规划周期描述 (默认: "未来2周")
        "allow_day_trading": false,          # 是否允许日内交易 (默认: false)
        "current_position_percent": 0.0,     # 当前持有仓位百分比 (默认: 0.0)
        "duration": "3 M",                   # 数据周期 (默认: '3 M')
        "bar_size": "1 day",                 # K线周期 (默认: '1 day')
        "model": "deepseek-v3.1:671b-cloud"  # AI模型名称
    }
    """
    symbol_upper = symbol.upper()
    
    # 获取请求参数
    data = request.get_json() or {}
    end_date_str = data.get('end_date', '')
    planning_period = data.get('planning_period', '未来2周')
    allow_day_trading = bool(data.get('allow_day_trading', False))
    current_position_percent = float(data.get('current_position_percent', 0.0))
    duration = data.get('duration', '3 M')
    bar_size = data.get('bar_size', '1 day')
    model = data.get('model', 'deepseek-v3.1:671b-cloud')
    
    # 验证参数
    if not end_date_str:
        return jsonify({
            'success': False,
            'message': '回测结束日期不能为空'
        }), 400
    
    if current_position_percent < 0 or current_position_percent > 100:
        return jsonify({
            'success': False,
            'message': '当前持有仓位百分比必须在0-100之间'
        }), 400
    
    logger.info(f"交易操作规划回测: {symbol_upper}, 结束日期={end_date_str}")
    
    # 检查Ollama是否可用
    if not check_ollama_available():
        return jsonify({
            'success': False,
            'message': 'Ollama不可用，无法执行AI分析',
            'ai_available': False
        }), 503
    
    try:
        # 执行回测
        result = backtest_trading_plan(
            symbol_upper,
            end_date_str,
            planning_period=planning_period,
            allow_day_trading=allow_day_trading,
            current_position_percent=current_position_percent,
            duration=duration,
            bar_size=bar_size,
            model=model
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"交易操作规划回测失败: {e}")
        return jsonify({
            'success': False,
            'message': f'交易操作规划回测失败: {str(e)}',
            'ai_available': False
        }), 500


@app.route('/', methods=['GET'])
def index():
    """
    API首页
    """
    return jsonify({
        'service': 'YFinance Stock Analysis API',
        'version': '2.0.0',
        'data_source': 'Yahoo Finance',
        'description': '基于yfinance的股票数据分析服务，提供技术指标分析、K线数据查询等功能',
        'endpoints': {
            'health': 'GET /api/health - 健康检查',
            'analyze': 'GET /api/analyze/<symbol>?duration=1Y&bar_size=1day - 技术分析（自动包含AI分析）',
            'refresh_analyze': 'POST /api/refresh-analyze/<symbol>?duration=1Y&bar_size=1day - 强制刷新分析',
            'trading_plan': 'POST /api/trading-plan/<symbol> - AI交易操作规划分析',
            'backtest_trading_plan': 'POST /api/backtest-trading-plan/<symbol> - 回测交易操作规划',
            'hot_stocks': 'GET /api/hot-stocks?limit=20 - 热门股票列表',
            'indicator_info': 'GET /api/indicator-info?indicator=rsi - 指标说明'
        },
        'note': '历史K线、股票信息、基本面数据已整合到analyze接口中，不再提供独立API'
    })


def main():
    """
    启动API服务
    """
    # 初始化数据库
    init_database()
    
    logger.info("✅ YFinance 数据服务就绪")
    
    port = 8080
    logger.info(f"🚀 API服务启动在 http://0.0.0.0:{port}")
    
    # 启动Flask服务
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )


if __name__ == '__main__':
    main()
