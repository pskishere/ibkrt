#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API使用示例 - 通过HTTP请求调用分析服务
"""

import requests
import json


BASE_URL = "http://localhost:8080"


def api_health():
    """检查API健康状态"""
    print("=" * 50)
    print("检查API健康状态")
    print("=" * 50)
    
    response = requests.get(f"{BASE_URL}/api/health")
    data = response.json()
    
    print(f"状态: {data.get('status')}")
    print(f"数据源: {data.get('gateway')}")
    print(f"时间: {data.get('timestamp')}")
    print()


def api_technical_analysis(symbol="AAPL"):
    """技术分析"""
    print("=" * 50)
    print(f"技术分析: {symbol}")
    print("=" * 50)
    
    params = {
        'duration': '3 M',
        'bar_size': '1 day'
    }
    
    response = requests.get(f"{BASE_URL}/api/analyze/{symbol}", params=params)
    data = response.json()
    
    if data.get('success'):
        indicators = data.get('indicators', {})
        signals = data.get('signals', {})
        
        print(f"当前价格: ${indicators.get('current_price', 0):.2f}")
        print(f"MA5: ${indicators.get('ma5', 0):.2f}")
        print(f"MA20: ${indicators.get('ma20', 0):.2f}")
        print(f"RSI: {indicators.get('rsi', 0):.2f}")
        print(f"MACD: {indicators.get('macd', 0):.4f}")
        print()
        
        print("交易信号:")
        for signal in signals.get('signals_list', [])[:5]:
            print(f"  {signal}")
        
        print()
        print(f"总体建议: {signals.get('action_recommendation', '未知')}")
        print(f"风险等级: {signals.get('risk_level', '未知')}")
    
    print()


def api_fundamental(symbol="AAPL"):
    """基本面数据"""
    print("=" * 50)
    print(f"基本面数据: {symbol}")
    print("=" * 50)
    
    response = requests.get(f"{BASE_URL}/api/fundamental/{symbol}")
    data = response.json()
    
    if data.get('success'):
        fundamental = data.get('data', {})
        
        print(f"公司: {fundamental.get('CompanyName')}")
        print(f"行业: {fundamental.get('Sector')} - {fundamental.get('Industry')}")
        print(f"市值: ${fundamental.get('MarketCap', 0):,.0f}")
        print(f"市盈率PE: {fundamental.get('PE', 0):.2f}")
        print(f"市净率PB: {fundamental.get('PriceToBook', 0):.2f}")
        print(f"股息率: {fundamental.get('DividendYield', 0)*100:.2f}%")
        print(f"ROE: {fundamental.get('ROE', 0)*100:.2f}%")
        print(f"营收增长: {fundamental.get('RevenueGrowth', 0)*100:.2f}%")
    
    print()


def api_dividends(symbol="AAPL"):
    """股息历史"""
    print("=" * 50)
    print(f"股息历史: {symbol}")
    print("=" * 50)
    
    response = requests.get(f"{BASE_URL}/api/dividends/{symbol}")
    data = response.json()
    
    if data.get('success'):
        dividends = data.get('data', [])
        
        print(f"共有 {len(dividends)} 次分红")
        print("\n最近5次分红:")
        for div in dividends[-5:]:
            print(f"  {div['date']}: ${div['dividend']:.4f}")
    
    print()


def api_institutional(symbol="AAPL"):
    """机构持仓"""
    print("=" * 50)
    print(f"机构持仓: {symbol}")
    print("=" * 50)
    
    response = requests.get(f"{BASE_URL}/api/institutional/{symbol}")
    data = response.json()
    
    if data.get('success'):
        holders = data.get('data', [])
        
        print(f"共有 {len(holders)} 个机构持仓")
        print("\n前5大机构:")
        for i, holder in enumerate(holders[:5], 1):
            name = holder.get('Holder', '未知')
            shares = holder.get('Shares', 0)
            value = holder.get('Value', 0)
            print(f"  {i}. {name}")
            print(f"     持股: {shares:,}, 市值: ${value:,.0f}")
    
    print()


def api_recommendations(symbol="AAPL"):
    """分析师推荐"""
    print("=" * 50)
    print(f"分析师推荐: {symbol}")
    print("=" * 50)
    
    response = requests.get(f"{BASE_URL}/api/recommendations/{symbol}")
    data = response.json()
    
    if data.get('success'):
        recommendations = data.get('data', [])
        
        print(f"共有 {len(recommendations)} 条推荐")
        print("\n最近5条:")
        for rec in recommendations[:5]:
            firm = rec.get('Firm', '未知')
            to_grade = rec.get('To Grade', '未知')
            action = rec.get('Action', '未知')
            print(f"  {firm}: {to_grade} ({action})")
    
    print()


def api_news(symbol="AAPL", limit=5):
    """相关新闻"""
    print("=" * 50)
    print(f"相关新闻: {symbol}")
    print("=" * 50)
    
    params = {'limit': limit}
    response = requests.get(f"{BASE_URL}/api/news/{symbol}", params=params)
    data = response.json()
    
    if data.get('success'):
        news_list = data.get('data', [])
        
        print(f"获取到 {len(news_list)} 条新闻\n")
        for i, news in enumerate(news_list, 1):
            title = news.get('title', '未知')
            publisher = news.get('publisher', '未知')
            link = news.get('link', '')
            print(f"{i}. {title}")
            print(f"   来源: {publisher}")
            if link:
                print(f"   链接: {link}")
            print()
    
    print()


def api_comprehensive(symbol="AAPL"):
    """全面综合分析"""
    print("=" * 50)
    print(f"全面综合分析: {symbol}")
    print("=" * 50)
    
    params = {
        'include_options': 'false',
        'include_news': 'true',
        'news_limit': 5
    }
    
    response = requests.get(f"{BASE_URL}/api/comprehensive/{symbol}", params=params)
    data = response.json()
    
    if data.get('success'):
        analysis = data.get('analysis', {})
        
        # 基本信息
        basic = analysis.get('basic_info', {})
        print(f"公司: {basic.get('name')}")
        print(f"行业: {basic.get('sector')} - {basic.get('industry')}")
        print(f"当前价格: ${basic.get('current_price', 0):.2f}")
        print(f"市值: ${basic.get('market_cap', 0):,.0f}")
        print()
        
        # 综合评分
        overall = analysis.get('overall_score', {})
        print(f"【综合评分】")
        print(f"评分: {overall.get('total_score', 0):.2f}/100")
        print(f"等级: {overall.get('grade')} - {overall.get('rating')}")
        print()
        
        # 各维度分析
        dimensions = [
            ('估值分析', 'valuation'),
            ('财务健康', 'financial_health'),
            ('成长性', 'growth'),
            ('盈利能力', 'profitability'),
            ('股息质量', 'dividend'),
        ]
        
        for title, key in dimensions:
            section = analysis.get(key, {})
            if section:
                print(f"【{title}】")
                print(f"评级: {section.get('rating')} ({section.get('level')})")
                print(f"得分: {section.get('score')}")
                
                signals = section.get('signals', [])
                if signals:
                    print("信号:")
                    for signal in signals[:3]:
                        print(f"  {signal}")
                print()
        
        # 投资建议
        recommendation = analysis.get('recommendation', {})
        print("【投资建议】")
        print(f"操作: {recommendation.get('action')}")
        print(f"理由: {recommendation.get('reason')}")
        print(f"信心: {recommendation.get('confidence')}")
        
        key_points = recommendation.get('key_points', [])
        if key_points:
            print("关键要点:")
            for point in key_points:
                print(f"  • {point}")
        print()
        
        # 风险评估
        risk = analysis.get('risk', {})
        print("【风险评估】")
        print(f"风险等级: {risk.get('level')}")
        factors = risk.get('factors', [])
        if factors:
            print("风险因素:")
            for factor in factors:
                print(f"  {factor}")
    
    print()


def api_all_data(symbol="AAPL"):
    """获取所有原始数据"""
    print("=" * 50)
    print(f"所有原始数据: {symbol}")
    print("=" * 50)
    
    params = {
        'include_options': 'false',
        'include_news': 'false'
    }
    
    response = requests.get(f"{BASE_URL}/api/all-data/{symbol}", params=params)
    data = response.json()
    
    if data.get('success'):
        all_data = data.get('data', {})
        
        print("可用数据模块:")
        data_modules = [
            ('基本信息', 'info'),
            ('基本面', 'fundamental'),
            ('快速信息', 'fast_info'),
            ('股息', 'dividends'),
            ('拆分', 'splits'),
            ('机构持仓', 'institutional_holders'),
            ('内部交易', 'insider_transactions'),
            ('分析师推荐', 'recommendations'),
            ('收益数据', 'earnings'),
            ('ESG评分', 'sustainability'),
        ]
        
        for name, key in data_modules:
            value = all_data.get(key)
            if value:
                if isinstance(value, list):
                    print(f"  ✓ {name}: {len(value)} 条记录")
                elif isinstance(value, dict):
                    print(f"  ✓ {name}: 已加载")
                else:
                    print(f"  ✓ {name}: 可用")
            else:
                print(f"  ✗ {name}: 无数据")
    
    print()


def main():
    """
    运行所有API示例
    """
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "API 调用示例" + " " * 28 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    print(f"API地址: {BASE_URL}")
    print()
    
    try:
        symbol = "AAPL"
        
        # 健康检查
        api_health()
        
        # 各种数据接口
        api_technical_analysis(symbol)
        api_fundamental(symbol)
        api_dividends(symbol)
        api_institutional(symbol)
        api_recommendations(symbol)
        api_news(symbol, limit=3)
        
        # 全面分析（最重要）
        api_comprehensive(symbol)
        
        # 原始数据
        api_all_data(symbol)
        
        print("=" * 50)
        print("所有API调用示例完成！")
        print("=" * 50)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 错误: 无法连接到API服务器")
        print(f"请确保API服务正在运行: {BASE_URL}")
        print("\n启动命令:")
        print("  cd /Users/k/schwabgo")
        print("  python -m backend.app")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
