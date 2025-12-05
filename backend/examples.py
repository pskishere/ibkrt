#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
YFinance功能使用示例
展示如何使用所有可用的yfinance功能和分析能力
"""

from yfinance import (
    get_stock_info, get_fundamental_data, get_historical_data,
    get_dividends, get_splits, get_institutional_holders,
    get_insider_transactions, get_recommendations, get_earnings,
    get_news, get_options, get_all_data
)
from stock_analyzer import create_comprehensive_analysis


def example_basic_info():
    """示例1: 获取基本股票信息"""
    print("=" * 50)
    print("示例1: 获取基本股票信息")
    print("=" * 50)
    
    symbol = "AAPL"
    info = get_stock_info(symbol)
    
    if info:
        print(f"股票代码: {info['symbol']}")
        print(f"公司名称: {info['longName']}")
        print(f"交易所: {info['exchange']}")
        print(f"市值: ${info['marketCap']:,.0f}")
        print(f"当前价格: ${info['regularMarketPrice']:.2f}")
    print()


def example_fundamental():
    """示例2: 获取基本面数据"""
    print("=" * 50)
    print("示例2: 获取基本面数据")
    print("=" * 50)
    
    symbol = "AAPL"
    fundamental = get_fundamental_data(symbol)
    
    if fundamental:
        print(f"公司: {fundamental['CompanyName']}")
        print(f"行业: {fundamental['Sector']} - {fundamental['Industry']}")
        print(f"市盈率: {fundamental['PE']:.2f}")
        print(f"市净率: {fundamental['PriceToBook']:.2f}")
        print(f"ROE: {fundamental['ROE']*100:.2f}%")
        print(f"净利润率: {fundamental['ProfitMargin']*100:.2f}%")
        print(f"营收增长: {fundamental['RevenueGrowth']*100:.2f}%")
        print(f"债务权益比: {fundamental['DebtToEquity']:.2f}")
    print()


def example_historical():
    """示例3: 获取历史数据"""
    print("=" * 50)
    print("示例3: 获取历史数据")
    print("=" * 50)
    
    symbol = "AAPL"
    hist_data, error = get_historical_data(symbol, duration='1 M', bar_size='1 day')
    
    if hist_data and not error:
        print(f"获取到 {len(hist_data)} 条K线数据")
        if len(hist_data) > 0:
            latest = hist_data[-1]
            print(f"最新日期: {latest['date']}")
            print(f"收盘价: ${latest['close']:.2f}")
            print(f"成交量: {latest['volume']:,}")
    print()


def example_dividends():
    """示例4: 获取股息历史"""
    print("=" * 50)
    print("示例4: 获取股息历史")
    print("=" * 50)
    
    symbol = "AAPL"
    dividends = get_dividends(symbol)
    
    if dividends:
        print(f"共有 {len(dividends)} 次分红记录")
        print("最近5次分红:")
        for div in dividends[-5:]:
            print(f"  {div['date']}: ${div['dividend']:.4f}")
    print()


def example_institutional():
    """示例5: 获取机构持仓"""
    print("=" * 50)
    print("示例5: 获取机构持仓")
    print("=" * 50)
    
    symbol = "AAPL"
    holders = get_institutional_holders(symbol)
    
    if holders:
        print(f"共有 {len(holders)} 个机构持仓")
        print("前5大机构持仓:")
        for i, holder in enumerate(holders[:5], 1):
            holder_name = holder.get('Holder', '未知')
            shares = holder.get('Shares', 0)
            print(f"  {i}. {holder_name}: {shares:,} 股")
    print()


def example_insider():
    """示例6: 获取内部交易"""
    print("=" * 50)
    print("示例6: 获取内部交易")
    print("=" * 50)
    
    symbol = "AAPL"
    transactions = get_insider_transactions(symbol)
    
    if transactions:
        print(f"共有 {len(transactions)} 条内部交易记录")
        print("最近5条交易:")
        for trans in transactions[:5]:
            insider = trans.get('Insider', '未知')
            trans_type = trans.get('Transaction', '未知')
            print(f"  {insider}: {trans_type}")
    print()


def example_analyst():
    """示例7: 获取分析师推荐"""
    print("=" * 50)
    print("示例7: 获取分析师推荐")
    print("=" * 50)
    
    symbol = "AAPL"
    recommendations = get_recommendations(symbol)
    
    if recommendations:
        print(f"共有 {len(recommendations)} 条分析师推荐")
        print("最近5条推荐:")
        for rec in recommendations[:5]:
            firm = rec.get('Firm', '未知')
            grade = rec.get('To Grade', '未知')
            print(f"  {firm}: {grade}")
    print()


def example_earnings():
    """示例8: 获取收益数据"""
    print("=" * 50)
    print("示例8: 获取收益数据")
    print("=" * 50)
    
    symbol = "AAPL"
    earnings = get_earnings(symbol)
    
    if earnings:
        yearly = earnings.get('yearly', [])
        quarterly = earnings.get('quarterly', [])
        
        print(f"年度收益: {len(yearly)} 条")
        print(f"季度收益: {len(quarterly)} 条")
        
        if quarterly:
            print("\n最近季度收益:")
            for q in quarterly[:4]:
                quarter = q.get('quarter', '未知')
                revenue = q.get('Revenue', 0)
                earnings_val = q.get('Earnings', 0)
                print(f"  {quarter}: 营收 ${revenue/1e9:.2f}B, 盈利 ${earnings_val/1e9:.2f}B")
    print()


def example_news():
    """示例9: 获取相关新闻"""
    print("=" * 50)
    print("示例9: 获取相关新闻")
    print("=" * 50)
    
    symbol = "AAPL"
    news = get_news(symbol, limit=5)
    
    if news:
        print(f"获取到 {len(news)} 条新闻")
        for i, item in enumerate(news, 1):
            title = item.get('title', '未知')
            publisher = item.get('publisher', '未知')
            print(f"{i}. {title}")
            print(f"   来源: {publisher}")
    print()


def example_comprehensive():
    """示例10: 全面综合分析"""
    print("=" * 50)
    print("示例10: 全面综合分析")
    print("=" * 50)
    
    symbol = "AAPL"
    
    # 获取所有数据
    all_data = get_all_data(symbol, include_options=False, include_news=True)
    
    if all_data:
        # 执行综合分析
        analysis = create_comprehensive_analysis(symbol, all_data)
        
        if analysis:
            print(f"股票: {symbol}")
            print(f"分析时间: {analysis['timestamp']}")
            print()
            
            # 综合评分
            overall = analysis.get('overall_score', {})
            print(f"综合评分: {overall.get('total_score', 0):.2f}/100")
            print(f"评级: {overall.get('grade', 'N/A')} ({overall.get('rating', '未知')})")
            print()
            
            # 估值分析
            valuation = analysis.get('valuation', {})
            print(f"估值评级: {valuation.get('rating', '未知')}")
            print("估值信号:")
            for signal in valuation.get('signals', []):
                print(f"  {signal}")
            print()
            
            # 财务健康
            health = analysis.get('financial_health', {})
            print(f"财务健康: {health.get('rating', '未知')}")
            print("财务信号:")
            for signal in health.get('signals', [])[:3]:
                print(f"  {signal}")
            print()
            
            # 成长性
            growth = analysis.get('growth', {})
            print(f"成长性: {growth.get('rating', '未知')}")
            print("成长信号:")
            for signal in growth.get('signals', []):
                print(f"  {signal}")
            print()
            
            # 投资建议
            recommendation = analysis.get('recommendation', {})
            print(f"投资建议: {recommendation.get('action', '未知')}")
            print(f"理由: {recommendation.get('reason', '未知')}")
            print("关键要点:")
            for point in recommendation.get('key_points', []):
                print(f"  • {point}")
            print()
            
            # 风险评估
            risk = analysis.get('risk', {})
            print(f"风险等级: {risk.get('level', '未知')}")
            print("风险因素:")
            for factor in risk.get('factors', []):
                print(f"  {factor}")
    
    print()


def main():
    """
    运行所有示例
    """
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "YFinance 功能使用示例" + " " * 24 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    try:
        example_basic_info()
        example_fundamental()
        example_historical()
        example_dividends()
        example_institutional()
        example_insider()
        example_analyst()
        example_earnings()
        example_news()
        example_comprehensive()
        
        print("=" * 50)
        print("所有示例执行完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
