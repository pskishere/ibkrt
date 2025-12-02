#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
YFinance数据获取模块 - 从yfinance获取股票数据
"""

import pandas as pd
import numpy as np
import pytz
from datetime import datetime, timedelta
import yfinance as yf
from .settings import logger, get_kline_from_cache, save_kline_to_cache


def get_stock_info(symbol: str):
    """
    获取股票详细信息
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        if not info:
            return None
        
        return {
            'symbol': symbol,
            'longName': info.get('longName', info.get('shortName', symbol)),
            'shortName': info.get('shortName', ''),
            'exchange': info.get('exchange', ''),
            'currency': info.get('currency', 'USD'),
            'marketCap': info.get('marketCap', 0),
            'regularMarketPrice': info.get('regularMarketPrice', 0),
            'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh', 0),
            'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow', 0),
        }
    except Exception as e:
        logger.error(f"获取股票信息失败: {symbol}, 错误: {e}")
        return None


def _format_financial_dataframe(df):
    """
    格式化财务报表DataFrame为列表格式（字典列表）
    将DataFrame转换为列表，每个元素是一个日期对应的记录
    """
    if df is None or df.empty:
        return []
    
    result = []
    # 转置DataFrame，使日期为键
    df_transposed = df.T
    
    for date in df_transposed.index:
        # 处理日期：转换为字符串
        if hasattr(date, 'strftime'):
            date_str = date.strftime('%Y-%m-%d')
        elif isinstance(date, pd.Timestamp):
            date_str = date.strftime('%Y-%m-%d')
        else:
            date_str = str(date)
        
        record = {'index': date_str, 'Date': date_str}
        for col in df_transposed.columns:
            value = df_transposed.loc[date, col]
            # 处理NaN值
            if pd.notna(value):
                # 处理 Timestamp 对象
                if isinstance(value, pd.Timestamp):
                    record[col] = value.strftime('%Y-%m-%d')
                elif isinstance(value, (int, float, np.number)):
                    record[col] = float(value)
                else:
                    record[col] = str(value)
            else:
                record[col] = None
        
        result.append(record)
    
    return result


def get_fundamental_data(symbol: str):
    """
    获取基本面数据（从yfinance）
    返回公司财务数据、估值指标、财务报表、资产负债表、现金流量表等
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        if not info:
            return None
        
        # 计算每股现金（避免除零错误）
        shares_outstanding = info.get('sharesOutstanding', 0)
        total_cash = info.get('totalCash', 0)
        cash_per_share = (total_cash / shares_outstanding) if shares_outstanding and shares_outstanding > 0 else 0
        
        # 提取基本面关键指标
        fundamental = {
            # 公司信息
            'CompanyName': info.get('longName', info.get('shortName', symbol)),
            'ShortName': info.get('shortName', ''),
            'Exchange': info.get('exchange', ''),
            'Currency': info.get('currency', 'USD'),
            'Sector': info.get('sector', ''),
            'Industry': info.get('industry', ''),
            'Website': info.get('website', ''),
            'Employees': info.get('fullTimeEmployees', 0),
            'BusinessSummary': info.get('longBusinessSummary', ''),
            
            # 市值与价格
            'MarketCap': info.get('marketCap', 0),
            'EnterpriseValue': info.get('enterpriseValue', 0),
            'Price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
            'PreviousClose': info.get('previousClose', 0),
            '52WeekHigh': info.get('fiftyTwoWeekHigh', 0),
            '52WeekLow': info.get('fiftyTwoWeekLow', 0),
            'SharesOutstanding': shares_outstanding,
            
            # 估值指标
            'PE': info.get('trailingPE', 0),
            'ForwardPE': info.get('forwardPE', 0),
            'PriceToBook': info.get('priceToBook', 0),
            'PriceToSales': info.get('priceToSalesTrailing12Months', 0),
            'PEGRatio': info.get('pegRatio', 0),
            'EVToRevenue': info.get('enterpriseToRevenue', 0),
            'EVToEBITDA': info.get('enterpriseToEbitda', 0),
            
            # 盈利能力
            'ProfitMargin': info.get('profitMargins', 0),
            'OperatingMargin': info.get('operatingMargins', 0),
            'GrossMargin': info.get('grossMargins', 0),
            'ROE': info.get('returnOnEquity', 0),
            'ROA': info.get('returnOnAssets', 0),
            'ROIC': info.get('returnOnInvestedCapital', 0),
            
            # 财务健康
            'RevenueTTM': info.get('totalRevenue', 0),
            'RevenuePerShare': info.get('revenuePerShare', 0),
            'NetIncomeTTM': info.get('netIncomeToCommon', 0),
            'EBITDATTM': info.get('ebitda', 0),
            'TotalDebt': info.get('totalDebt', 0),
            'TotalCash': total_cash,
            'CashPerShare': cash_per_share,
            'DebtToEquity': info.get('debtToEquity', 0),
            'CurrentRatio': info.get('currentRatio', 0),
            'QuickRatio': info.get('quickRatio', 0),
            'CashFlow': info.get('operatingCashflow', 0),
            
            # 每股数据
            'EPS': info.get('trailingEps', 0),
            'ForwardEPS': info.get('forwardEps', 0),
            'BookValuePerShare': info.get('bookValue', 0),
            'DividendPerShare': info.get('dividendRate', 0),
            
            # 股息
            'DividendRate': info.get('dividendRate', 0),
            'DividendYield': info.get('dividendYield', 0),
            'PayoutRatio': info.get('payoutRatio', 0),
            'ExDividendDate': info.get('exDividendDate', 0),
            
            # 成长性
            'RevenueGrowth': info.get('revenueGrowth', 0),
            'EarningsGrowth': info.get('earningsGrowth', 0),
            'EarningsQuarterlyGrowth': info.get('earningsQuarterlyGrowth', 0),
            'QuarterlyRevenueGrowth': info.get('quarterlyRevenueGrowth', 0),
            
            # 分析师预期
            'TargetPrice': info.get('targetMeanPrice', 0),
            'TargetHighPrice': info.get('targetHighPrice', 0),
            'TargetLowPrice': info.get('targetLowPrice', 0),
            'ConsensusRecommendation': info.get('recommendationMean', 0),
            'RecommendationKey': info.get('recommendationKey', ''),
            'NumberOfAnalystOpinions': info.get('numberOfAnalystOpinions', 0),
            'ProjectedEPS': info.get('forwardEps', 0),
            'ProjectedGrowthRate': info.get('earningsQuarterlyGrowth', 0),
            
            # 其他指标
            'Beta': info.get('beta', 0),
            'AverageVolume': info.get('averageVolume', 0),
            'AverageVolume10days': info.get('averageVolume10days', 0),
            'FloatShares': info.get('floatShares', 0),
        }
        
        try:
            financials = ticker.financials
            if financials is not None and not financials.empty:
                fundamental['Financials'] = _format_financial_dataframe(financials)
                logger.info(f"已获取财务报表数据: {symbol}")
        except Exception as e:
            logger.warning(f"获取财务报表失败: {symbol}, 错误: {e}")
            fundamental['Financials'] = []
        
        try:
            quarterly_financials = ticker.quarterly_financials
            if quarterly_financials is not None and not quarterly_financials.empty:
                fundamental['QuarterlyFinancials'] = _format_financial_dataframe(quarterly_financials)
                logger.info(f"已获取季度财务报表数据: {symbol}")
        except Exception as e:
            logger.warning(f"获取季度财务报表失败: {symbol}, 错误: {e}")
            fundamental['QuarterlyFinancials'] = []
        
        try:
            balance_sheet = ticker.balance_sheet
            if balance_sheet is not None and not balance_sheet.empty:
                fundamental['BalanceSheet'] = _format_financial_dataframe(balance_sheet)
                logger.info(f"已获取资产负债表数据: {symbol}")
        except Exception as e:
            logger.warning(f"获取资产负债表失败: {symbol}, 错误: {e}")
            fundamental['BalanceSheet'] = []
        
        try:
            quarterly_balance_sheet = ticker.quarterly_balance_sheet
            if quarterly_balance_sheet is not None and not quarterly_balance_sheet.empty:
                fundamental['QuarterlyBalanceSheet'] = _format_financial_dataframe(quarterly_balance_sheet)
                logger.info(f"已获取季度资产负债表数据: {symbol}")
        except Exception as e:
            logger.warning(f"获取季度资产负债表失败: {symbol}, 错误: {e}")
            fundamental['QuarterlyBalanceSheet'] = []
        
        try:
            cashflow = ticker.cashflow
            if cashflow is not None and not cashflow.empty:
                fundamental['Cashflow'] = _format_financial_dataframe(cashflow)
                logger.info(f"已获取现金流量表数据: {symbol}")
        except Exception as e:
            logger.warning(f"获取现金流量表失败: {symbol}, 错误: {e}")
            fundamental['Cashflow'] = []
        
        try:
            quarterly_cashflow = ticker.quarterly_cashflow
            if quarterly_cashflow is not None and not quarterly_cashflow.empty:
                fundamental['QuarterlyCashflow'] = _format_financial_dataframe(quarterly_cashflow)
                logger.info(f"已获取季度现金流量表数据: {symbol}")
        except Exception as e:
            logger.warning(f"获取季度现金流量表失败: {symbol}, 错误: {e}")
            fundamental['QuarterlyCashflow'] = []
        
        return fundamental
        
    except Exception as e:
        logger.error(f"获取基本面数据失败: {symbol}, 错误: {e}")
        return None


def _format_historical_data(df: pd.DataFrame):
    """
    格式化历史数据
    """
    result = []
    # 检查是否有 Volume 列，如果没有或为 NaN 则使用 0
    has_volume = 'Volume' in df.columns
    
    for date, row in df.iterrows():
        date_str = date.strftime('%Y%m%d')
        if pd.notna(date.hour):  # 如果有时间
            date_str = date.strftime('%Y%m%d %H:%M:%S')
        
        # 处理成交量数据：如果不存在或为 NaN，使用 0
        volume = 0
        if has_volume and pd.notna(row.get('Volume')):
            try:
                volume = int(row['Volume'])
            except (ValueError, TypeError):
                volume = 0
        
        result.append({
            'date': date_str,
            'open': float(row['Open']),
            'high': float(row['High']),
            'low': float(row['Low']),
            'close': float(row['Close']),
            'volume': volume,
            'average': float((row['High'] + row['Low'] + row['Close']) / 3),
            'barCount': 1
        })
    
    return result


def get_historical_data(symbol: str, duration: str = '1 D', 
                       bar_size: str = '5 mins', exchange: str = '', 
                       currency: str = 'USD'):
    """
    获取历史数据，支持缓存和增量更新
    默认缓存至少1年以上数据，保证日期连续性和最新日期为当日
    duration: 数据周期，如 '1 D', '1 W', '1 M', '3 M', '1 Y'
    bar_size: K线周期，如 '1 min', '5 mins', '1 hour', '1 day'
    """
    try:
        # 转换bar_size为yfinance格式
        interval_map = {
            '1 min': '1m',
            '2 mins': '2m',
            '5 mins': '5m',
            '15 mins': '15m',
            '30 mins': '30m',
            '1 hour': '1h',
            '1 day': '1d',
            '1 week': '1wk',
            '1 month': '1mo'
        }
        
        yf_interval = interval_map.get(bar_size, '1d')
        
        # 尝试从缓存获取数据
        cached_df = get_kline_from_cache(symbol, yf_interval)
        
        # 统一时区处理
        now_local = pd.Timestamp.now()
        et_tz = pytz.timezone('US/Eastern')
        now_et = now_local.tz_localize('UTC').astimezone(et_tz) if now_local.tzinfo is None else now_local.astimezone(et_tz)
        
        # 美股交易时间：09:30-16:00 ET
        if now_et.hour < 16 or (now_et.hour == 16 and now_et.minute == 0):
            expected_latest_date = (now_et.date() - timedelta(days=1))
        else:
            expected_latest_date = now_et.date()
        
        # 考虑周末：如果是周六/周日，往前推到周五
        while expected_latest_date.weekday() >= 5:  # 5=周六, 6=周日
            expected_latest_date -= timedelta(days=1)
        
        today = pd.Timestamp.now().normalize().tz_localize(None)
        one_year_ago = today - timedelta(days=365)
        
        # 检查缓存数据的完整性
        need_full_refresh = False
        
        if cached_df is None or cached_df.empty:
            need_full_refresh = True
            logger.info(f"无缓存数据，需要全量获取: {symbol}, {yf_interval}")
        else:
            if cached_df.index.tzinfo is not None:
                cached_df.index = cached_df.index.tz_localize(None)
            
            first_date = cached_df.index[0]
            last_date = cached_df.index[-1]
            
            if first_date > one_year_ago:
                logger.info(f"缓存数据不足1年（最早: {first_date}），需要全量刷新")
                need_full_refresh = True
            elif last_date.date() < (today - timedelta(days=7)).date():
                logger.info(f"缓存数据过旧（最新: {last_date}），需要全量刷新")
                need_full_refresh = True
        
        if need_full_refresh:
            logger.info(f"从 yfinance 获取全量数据: {symbol}, 2y, {yf_interval}")
            ticker = yf.Ticker(symbol)
            df = ticker.history(period='2y', interval=yf_interval)
            
            if df.empty:
                logger.warning(f"无法获取历史数据: {symbol}")
                return None, {'code': 200, 'message': f'证券 {symbol} 不存在或没有数据'}
            
            if 'Volume' not in df.columns:
                logger.warning(f"警告: {symbol} 的数据中没有 Volume 列，成交量相关指标将无法计算")
            elif df['Volume'].isna().all():
                logger.warning(f"警告: {symbol} 的成交量数据全部为 NaN，成交量相关指标将无法计算")
            elif df['Volume'].isna().any():
                nan_count = df['Volume'].isna().sum()
                logger.warning(f"警告: {symbol} 有 {nan_count} 条数据的成交量为 NaN，将使用 0 代替")
            
            if df.index.tzinfo is not None:
                df.index = df.index.tz_localize(None)
            
            save_kline_to_cache(symbol, yf_interval, df)
            
            logger.info(f"全量数据已缓存: {symbol}, {yf_interval}, {len(df)}条, 时间范围: {df.index[0]} - {df.index[-1]}")
            return _format_historical_data(df), None
        
        last_cached_date = cached_df.index[-1]
        logger.info(f"使用缓存数据并增量更新: {symbol}, {yf_interval}, 最新: {last_cached_date.date()}")
        
        if last_cached_date.date() >= expected_latest_date:
            logger.info(f"缓存已是最新数据: {symbol}, 缓存日期={last_cached_date.date()}, 预期最新={expected_latest_date}")
            return _format_historical_data(cached_df), None
        
        try:
            ticker = yf.Ticker(symbol)
            new_data = ticker.history(period='10d', interval=yf_interval)
            
            if not new_data.empty:
                if new_data.index.tzinfo is not None:
                    new_data.index = new_data.index.tz_localize(None)
                
                new_data_filtered = new_data[new_data.index > last_cached_date]
                
                if not new_data_filtered.empty:
                    combined_df = pd.concat([cached_df, new_data])
                    combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                    combined_df = combined_df.sort_index()
                    
                    save_kline_to_cache(symbol, yf_interval, new_data)
                    
                    logger.info(f"增量更新完成: {symbol}, 新增{len(new_data_filtered)}条, 总计{len(combined_df)}条, 最新: {combined_df.index[-1].date()}")
                    return _format_historical_data(combined_df), None
                else:
                    logger.info(f"无新数据，返回缓存数据: {symbol}, 缓存最新日期: {last_cached_date.date()}")
                    return _format_historical_data(cached_df), None
            else:
                logger.info(f"获取最新数据为空，返回缓存数据")
                return _format_historical_data(cached_df), None
                
        except Exception as e:
            logger.warning(f"增量更新失败: {e}，返回缓存数据")
        
        return _format_historical_data(cached_df), None
        
    except Exception as e:
        logger.error(f"获取历史数据失败: {symbol}, 错误: {e}")
        return None, {'code': 500, 'message': str(e)}

