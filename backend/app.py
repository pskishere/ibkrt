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
    check_ollama_available, perform_ai_analysis
)
from .utils import (
    format_candle_data, extract_stock_name,
    create_error_response, create_success_response
)

# 创建Flask应用
app = Flask(__name__)
CORS(app)


def _load_indicator_info():
    """从JSON文件加载技术指标解释和参考范围"""
    try:
        json_path = os.path.join(os.path.dirname(__file__), 'indicators', 'indicator_info.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载指标信息失败: {e}")
        return {}


def _save_stock_info_if_available(symbol: str):
    """获取并保存股票信息"""
    try:
        stock_info = get_stock_info(symbol)
        if stock_info:
            stock_name = extract_stock_name(stock_info)
            if stock_name and stock_name != symbol:
                save_stock_info(symbol, stock_name)
    except Exception as e:
        logger.warning(f"获取股票信息失败: {e}")


def _perform_analysis(symbol: str, duration: str, bar_size: str, model: str, use_cache: bool = True):
    """
    执行技术分析的核心逻辑
    
    Args:
        symbol: 股票代码
        duration: 数据周期
        bar_size: K线周期
        model: AI模型名称
        use_cache: 是否使用缓存
        
    Returns:
        (result_dict, error_response_tuple or None)
    """
    # 如果使用缓存，先检查缓存
    if use_cache:
        cached_result = get_cached_analysis(symbol, duration, bar_size)
        if cached_result:
            if cached_result.get('ai_analysis'):
                return cached_result, None
            if check_ollama_available():
                try:
                    ai_analysis = perform_ai_analysis(
                        symbol, cached_result['indicators'], cached_result['signals'], duration, model
                    )
                    cached_result['ai_analysis'] = ai_analysis
                    cached_result['model'] = model
                    cached_result['ai_available'] = True
                    save_analysis_cache(symbol, duration, bar_size, cached_result)
                except Exception as e:
                    logger.warning(f"AI分析执行失败: {e}")
                    cached_result['ai_available'] = False
                    cached_result['ai_error'] = str(e)
            return cached_result, None
    
    # 获取并保存股票信息
    _save_stock_info_if_available(symbol)
    
    # 获取历史数据和计算指标
    hist_data, _ = get_historical_data(symbol, duration, bar_size)
    indicators, ind_error = calculate_technical_indicators(symbol, duration, bar_size)
    
    if ind_error:
        return None, create_error_response(ind_error)
    
    if not indicators:
        return None, ({'success': False, 'message': '数据不足，无法计算技术指标'}, 404)
    
    # 生成信号和格式化数据
    signals = generate_signals(indicators)
    formatted_candles = format_candle_data(hist_data)
    
    # 执行AI分析
    ai_analysis = None
    if check_ollama_available():
        logger.info("检测到 Ollama 可用，开始AI分析...")
        try:
            ai_analysis = perform_ai_analysis(symbol, indicators, signals, duration, model)
        except Exception as e:
            logger.warning(f"AI分析执行失败: {e}")
    else:
        logger.info("Ollama 不可用，跳过AI分析")
    
    result = create_success_response(indicators, signals, formatted_candles, ai_analysis, model)
    save_analysis_cache(symbol, duration, bar_size, result)
    
    return result, None


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
    - model: AI模型名称 (默认: 'deepseek-v3.1:671b-cloud')
    """
    duration = request.args.get('duration', '3 M')
    bar_size = request.args.get('bar_size', '1 day')
    model = request.args.get('model', 'deepseek-v3.1:671b-cloud')
    
    symbol_upper = symbol.upper()
    logger.info(f"技术分析: {symbol_upper}, {duration}, {bar_size}")
    
    result, error_response = _perform_analysis(symbol_upper, duration, bar_size, model, use_cache=True)
    
    if error_response:
        return jsonify(error_response[0]), error_response[1]
    
    return jsonify(result)


@app.route('/api/refresh-analyze/<symbol>', methods=['POST'])
def refresh_analyze_stock(symbol):
    """
    刷新技术分析 - 强制重新获取数据并分析，不使用缓存
    自动检测 Ollama 是否可用，如果可用则自动执行AI分析
    
    查询参数:
    - duration: 数据周期 (默认: '3 M')
    - bar_size: K线周期 (默认: '1 day')
    - model: AI模型名称 (默认: 'deepseek-v3.1:671b-cloud')
    """
    duration = request.args.get('duration', '3 M')
    bar_size = request.args.get('bar_size', '1 day')
    model = request.args.get('model', 'deepseek-v3.1:671b-cloud')
    
    symbol_upper = symbol.upper()
    logger.info(f"刷新技术分析（强制重新获取）: {symbol_upper}, {duration}, {bar_size}")
    
    result, error_response = _perform_analysis(symbol_upper, duration, bar_size, model, use_cache=False)
    
    if error_response:
        return jsonify(error_response[0]), error_response[1]
    
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
