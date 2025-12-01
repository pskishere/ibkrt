
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基于yfinance的股票数据分析服务 - RESTful API服务
提供技术指标分析、AI分析、K线数据缓存等功能
数据来源：Yahoo Finance (yfinance)
"""

# 标准库导入
import logging
import threading
import time
import sqlite3
import json
import os
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np

# 第三方库导入
import requests
import yfinance as yf
from flask import Flask, jsonify, request
from flask_cors import CORS

# 技术指标模块导入
from indicators import (
    calculate_ma, calculate_rsi, calculate_bollinger, calculate_macd,
    calculate_volume, calculate_price_change, calculate_volatility,
    calculate_support_resistance, calculate_kdj, calculate_atr,
    calculate_williams_r, calculate_obv, analyze_trend_strength,
    calculate_fibonacci_retracement, calculate_chanlun_analysis, get_trend,
    calculate_cci, calculate_adx, calculate_vwap, calculate_sar,
    calculate_supertrend, calculate_stoch_rsi, calculate_volume_profile,
    calculate_ichimoku
)
from indicators.ml_predictions import calculate_ml_predictions

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
CORS(app)

DB_PATH = 'stock_cache.db'

def init_database():
    """
    初始化SQLite数据库，创建分析结果缓存表、股票信息表和K线数据表
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建分析结果缓存表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            duration TEXT NOT NULL,
            bar_size TEXT NOT NULL,
            query_date DATE NOT NULL,
            indicators TEXT NOT NULL,
            signals TEXT NOT NULL,
            candles TEXT NOT NULL,
            ai_analysis TEXT,
            model TEXT,
            ai_available INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, duration, bar_size, query_date)
        )
    ''')
    
    # 创建股票信息表，用于缓存股票代码和全名
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_info (
            symbol TEXT PRIMARY KEY,
            name TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创廾K线数据表，用于缓存全量K线数据
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kline_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            interval TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, interval, date)
        )
    ''')
    
    # 创建索引以提高查询速度
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_symbol_duration_bar_date 
        ON analysis_cache(symbol, duration, bar_size, query_date)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_kline_symbol_interval_date 
        ON kline_data(symbol, interval, date DESC)
    ''')
    
    conn.commit()
    conn.close()
    logger.info("数据库初始化完成")

def get_cached_analysis(symbol, duration, bar_size):
    """
    从数据库获取当天的分析结果
    返回: 如果有当天的数据返回结果字典，否则返回None
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        
        cursor.execute('''
            SELECT indicators, signals, candles, ai_analysis, model, ai_available
            FROM analysis_cache
            WHERE symbol = ? AND duration = ? AND bar_size = ? AND query_date = ?
        ''', (symbol.upper(), duration, bar_size, today))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            logger.info(f"从缓存获取数据: {symbol}, {duration}, {bar_size}")
            return {
                'success': True,
                'indicators': json.loads(row[0]),
                'signals': json.loads(row[1]),
                'candles': json.loads(row[2]),
                'ai_analysis': row[3],
                'model': row[4],
                'ai_available': bool(row[5])
            }
        else:
            return None
    except Exception as e:
        logger.error(f"查询缓存失败: {e}")
        return None

class JSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理pandas Timestamp等特殊类型"""
    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, (pd.Series, pd.DataFrame)):
            return obj.to_dict()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        return super().default(obj)

def save_analysis_cache(symbol, duration, bar_size, result):
    """
    保存分析结果到数据库（更新或插入）
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        
        # 使用自定义编码器序列化数据
        indicators_json = json.dumps(result.get('indicators', {}), cls=JSONEncoder, ensure_ascii=False)
        signals_json = json.dumps(result.get('signals', {}), cls=JSONEncoder, ensure_ascii=False)
        candles_json = json.dumps(result.get('candles', []), cls=JSONEncoder, ensure_ascii=False)
        
        # 使用 INSERT OR REPLACE 来更新或插入数据
        cursor.execute('''
            INSERT OR REPLACE INTO analysis_cache 
            (symbol, duration, bar_size, query_date, indicators, signals, candles, 
             ai_analysis, model, ai_available)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            symbol.upper(),
            duration,
            bar_size,
            today,
            indicators_json,
            signals_json,
            candles_json,
            result.get('ai_analysis'),
            result.get('model'),
            1 if result.get('ai_available') else 0
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"分析结果已缓存: {symbol}, {duration}, {bar_size}")
    except Exception as e:
        logger.error(f"保存缓存失败: {e}")

def cleanup_old_cache():
    """
    更新非当天的旧数据（保留历史数据，不再删除）
    """
    # 不再删除旧数据，保留历史记录
    pass

def save_stock_info(symbol, name):
    """
    保存或更新股票信息（代码和全名）
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 使用 INSERT OR REPLACE 来更新或插入
        cursor.execute('''
            INSERT OR REPLACE INTO stock_info (symbol, name, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (symbol.upper(), name))
        
        conn.commit()
        conn.close()
        logger.info(f"股票信息已保存: {symbol} - {name}")
    except Exception as e:
        logger.error(f"保存股票信息失败: {e}")

def get_stock_name(symbol):
    """
    从数据库获取股票全名
    返回: 股票全名，如果不存在则返回None
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name FROM stock_info WHERE symbol = ?
        ''', (symbol.upper(),))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return row[0]
        else:
            return None
    except Exception as e:
        logger.error(f"查询股票名称失败: {e}")
        return None


# ==================== YFinance 数据函数 ====================

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
            'PE': info.get('trailingPE', 0),  # 市盈率
            'ForwardPE': info.get('forwardPE', 0),  # 预期市盈率
            'PriceToBook': info.get('priceToBook', 0),  # 市净率
            'PriceToSales': info.get('priceToSalesTrailing12Months', 0),  # 市销率
            'PEGRatio': info.get('pegRatio', 0),  # PEG比率
            'EVToRevenue': info.get('enterpriseToRevenue', 0),  # 企业价值/营收
            'EVToEBITDA': info.get('enterpriseToEbitda', 0),  # 企业价值/EBITDA
            
            # 盈利能力
            'ProfitMargin': info.get('profitMargins', 0),  # 净利润率
            'OperatingMargin': info.get('operatingMargins', 0),  # 营业利润率
            'GrossMargin': info.get('grossMargins', 0),  # 毛利率
            'ROE': info.get('returnOnEquity', 0),  # ROE
            'ROA': info.get('returnOnAssets', 0),  # ROA
            'ROIC': info.get('returnOnInvestedCapital', 0),  # 投资回报率
            
            # 财务健康
            'RevenueTTM': info.get('totalRevenue', 0),  # 总收入(TTM)
            'RevenuePerShare': info.get('revenuePerShare', 0),  # 每股收入
            'NetIncomeTTM': info.get('netIncomeToCommon', 0),  # 净利润(TTM)
            'EBITDATTM': info.get('ebitda', 0),  # EBITDA(TTM)
            'TotalDebt': info.get('totalDebt', 0),  # 总债务
            'TotalCash': total_cash,  # 总现金
            'CashPerShare': cash_per_share,  # 每股现金
            'DebtToEquity': info.get('debtToEquity', 0),  # 资产负债率
            'CurrentRatio': info.get('currentRatio', 0),  # 流动比率
            'QuickRatio': info.get('quickRatio', 0),  # 速动比率
            'CashFlow': info.get('operatingCashflow', 0),  # 经营现金流
            
            # 每股数据
            'EPS': info.get('trailingEps', 0),  # 每股收益
            'ForwardEPS': info.get('forwardEps', 0),  # 预期每股收益
            'BookValuePerShare': info.get('bookValue', 0),  # 每股净资产
            'DividendPerShare': info.get('dividendRate', 0),  # 每股股息
            
            # 股息
            'DividendRate': info.get('dividendRate', 0),  # 股息率
            'DividendYield': info.get('dividendYield', 0),  # 股息收益率
            'PayoutRatio': info.get('payoutRatio', 0),  # 股息支付率
            'ExDividendDate': info.get('exDividendDate', 0),  # 除息日
            
            # 成长性
            'RevenueGrowth': info.get('revenueGrowth', 0),  # 收入增长率
            'EarningsGrowth': info.get('earningsGrowth', 0),  # 盈利增长率
            'EarningsQuarterlyGrowth': info.get('earningsQuarterlyGrowth', 0),  # 季度盈利增长
            'QuarterlyRevenueGrowth': info.get('quarterlyRevenueGrowth', 0),  # 季度收入增长
            
            # 分析师预期
            'TargetPrice': info.get('targetMeanPrice', 0),  # 目标平均价
            'TargetHighPrice': info.get('targetHighPrice', 0),  # 目标高价
            'TargetLowPrice': info.get('targetLowPrice', 0),  # 目标低价
            'ConsensusRecommendation': info.get('recommendationMean', 0),  # 共识评级（数值）
            'RecommendationKey': info.get('recommendationKey', ''),  # 分析师建议（文字）
            'NumberOfAnalystOpinions': info.get('numberOfAnalystOpinions', 0),  # 分析师数量
            'ProjectedEPS': info.get('forwardEps', 0),  # 预测EPS
            'ProjectedGrowthRate': info.get('earningsQuarterlyGrowth', 0),  # 预测增长率
            
            # 其他指标
            'Beta': info.get('beta', 0),  # Beta值
            'AverageVolume': info.get('averageVolume', 0),  # 平均成交量
            'AverageVolume10days': info.get('averageVolume10days', 0),  # 10日平均成交量
            'FloatShares': info.get('floatShares', 0),  # 流通股数
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

def _get_kline_from_cache(symbol: str, interval: str, start_date: str = None):
        """
        从数据库获取K线数据
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            if start_date:
                cursor.execute('''
                    SELECT date, open, high, low, close, volume
                    FROM kline_data
                    WHERE symbol = ? AND interval = ? AND date >= ?
                    ORDER BY date ASC
                ''', (symbol, interval, start_date))
            else:
                cursor.execute('''
                    SELECT date, open, high, low, close, volume
                    FROM kline_data
                    WHERE symbol = ? AND interval = ?
                    ORDER BY date ASC
                ''', (symbol, interval))
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return None
            
            # 转换为pandas DataFrame
            df = pd.DataFrame(rows, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            
            return df
        except Exception as e:
            logger.error(f"从缓存获取K线数据失败: {e}")
            return None

def _save_kline_to_cache(symbol: str, interval: str, df: pd.DataFrame):
        """
        保存K线数据到数据库（增量更新）
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # 检查是否有 Volume 列，如果没有或为 NaN 则使用 0
            has_volume = 'Volume' in df.columns
            
            for date, row in df.iterrows():
                date_str = date.strftime('%Y-%m-%d')
                # 处理成交量数据：如果不存在或为 NaN，使用 0
                volume = 0
                if has_volume and pd.notna(row.get('Volume')):
                    try:
                        volume = int(row['Volume'])
                    except (ValueError, TypeError):
                        volume = 0
                
                cursor.execute('''
                    INSERT OR REPLACE INTO kline_data 
                    (symbol, interval, date, open, high, low, close, volume, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    symbol,
                    interval,
                    date_str,
                    float(row['Open']),
                    float(row['High']),
                    float(row['Low']),
                    float(row['Close']),
                    volume
                ))
            
            conn.commit()
            conn.close()
            logger.info(f"K线数据已缓存: {symbol}, {interval}, {len(df)}条")
        except Exception as e:
            logger.error(f"保存K线数据失败: {e}")

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
            cached_df = _get_kline_from_cache(symbol, yf_interval)
            
            # 统一时区处理
            # 获取当前本地时间（中国时区）
            now_local = pd.Timestamp.now()
            # 转换为美国东部时间（ET）来判断是否是交易日
            import pytz
            et_tz = pytz.timezone('US/Eastern')
            now_et = now_local.tz_localize('UTC').astimezone(et_tz) if now_local.tzinfo is None else now_local.astimezone(et_tz)
            
            # 美股交易时间：09:30-16:00 ET
            # 如果当前ET时间在收盘后（16:00后），则今天的数据可用
            # 如果当前ET时间在开盘前（09:30前），则使用昨天的数据
            if now_et.hour < 16 or (now_et.hour == 16 and now_et.minute == 0):
                # 市场未收盘或刚收盘，使用昨天作为最新交易日
                expected_latest_date = (now_et.date() - timedelta(days=1))
            else:
                # 市场已收盘，今天的数据应该可用
                expected_latest_date = now_et.date()
            
            # 考虑周末：如果是周六/周日，往前推到周五
            while expected_latest_date.weekday() >= 5:  # 5=周六, 6=周日
                expected_latest_date -= timedelta(days=1)
            
            today = pd.Timestamp.now().normalize().tz_localize(None)
            one_year_ago = today - timedelta(days=365)
            
            # 检查缓存数据的完整性
            need_full_refresh = False
            
            if cached_df is None or cached_df.empty:
                # 无缓存，需要全量获取
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
                
                _save_kline_to_cache(symbol, yf_interval, df)
                
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
                        
                        _save_kline_to_cache(symbol, yf_interval, new_data)
                        
                        logger.info(f"增量更新完成: {symbol}, 新增{len(new_data_filtered)}条, 总计{len(combined_df)}条, 最新: {combined_df.index[-1].date()}")
                        return _format_historical_data(combined_df), None
                    else:
                        # 无新数据，可能是非交易日或时区原因
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

        # 15. 缠论分析（已优化，包含成交量分析）
        # 提取时间数据用于缠论分析（只显示日期，不显示时分秒）
        times = None
        if hist_data:
            times = []
            for bar in hist_data:
                date_str = bar.get('date', '')
                try:
                    # 转换时间格式：YYYYMMDD -> YYYY-MM-DD
                    if len(date_str) == 8:
                        times.append(f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}")
                    elif ' ' in date_str:
                        # 如果有时分秒，只提取日期部分
                        dt = datetime.strptime(date_str, '%Y%m%d %H:%M:%S')
                        times.append(dt.strftime('%Y-%m-%d'))
                    else:
                        times.append(date_str)
                except Exception:
                    times.append(date_str)
        
        chanlun_data = calculate_chanlun_analysis(closes, highs, lows, volumes, times=times)
        
        # 过滤：只保留一个月内的中枢、买入点和卖出点
        one_month_ago = (datetime.now() - timedelta(days=30)).date()
        
        # 过滤中枢
        if 'central_banks' in chanlun_data and chanlun_data['central_banks']:
            filtered_central_banks = []
            for cb in chanlun_data['central_banks']:
                # 检查结束时间是否在一个月内
                if cb.get('end_time'):
                    try:
                        end_date = datetime.strptime(cb['end_time'], '%Y-%m-%d').date()
                        if end_date >= one_month_ago:
                            filtered_central_banks.append(cb)
                    except Exception:
                        # 如果时间解析失败，保留该中枢
                        filtered_central_banks.append(cb)
                else:
                    # 如果没有时间信息，根据索引判断（假设是最近的数据）
                    if cb.get('end_index', 0) >= len(closes) - 30:
                        filtered_central_banks.append(cb)
            chanlun_data['central_banks'] = filtered_central_banks
        
        # 过滤买入点
        if 'trading_points' in chanlun_data and 'buy_points' in chanlun_data['trading_points']:
            filtered_buy_points = []
            for bp in chanlun_data['trading_points']['buy_points']:
                if bp.get('time'):
                    try:
                        point_date = datetime.strptime(bp['time'], '%Y-%m-%d').date()
                        if point_date >= one_month_ago:
                            filtered_buy_points.append(bp)
                    except Exception:
                        # 如果时间解析失败，根据索引判断
                        if bp.get('index', 0) >= len(closes) - 30:
                            filtered_buy_points.append(bp)
                else:
                    # 如果没有时间信息，根据索引判断
                    if bp.get('index', 0) >= len(closes) - 30:
                        filtered_buy_points.append(bp)
            chanlun_data['trading_points']['buy_points'] = filtered_buy_points
        
        # 过滤卖出点
        if 'trading_points' in chanlun_data and 'sell_points' in chanlun_data['trading_points']:
            filtered_sell_points = []
            for sp in chanlun_data['trading_points']['sell_points']:
                if sp.get('time'):
                    try:
                        point_date = datetime.strptime(sp['time'], '%Y-%m-%d').date()
                        if point_date >= one_month_ago:
                            filtered_sell_points.append(sp)
                    except Exception:
                        # 如果时间解析失败，根据索引判断
                        if sp.get('index', 0) >= len(closes) - 30:
                            filtered_sell_points.append(sp)
                else:
                    # 如果没有时间信息，根据索引判断
                    if sp.get('index', 0) >= len(closes) - 30:
                        filtered_sell_points.append(sp)
            chanlun_data['trading_points']['sell_points'] = filtered_sell_points
        
        result.update(chanlun_data)
        
        # 16. CCI（顺势指标）
        if len(closes) >= 14:
            cci_data = calculate_cci(closes, highs, lows)
            result.update(cci_data)
        
        # 17. ADX（平均趋向指标）
        if len(closes) >= 28:  # ADX需要period*2的数据
            adx_data = calculate_adx(closes, highs, lows)
            result.update(adx_data)
        
        # 18. VWAP（成交量加权平均价）
        # 按照 Futu 公式：AVGPRICE=TOTALAMOUNT/TOTALVOL, 否则使用(C+H+L)/3
        # 使用较长周期（80天）以更接近 Futu 的计算结果
        if len(closes) >= 1:
            # 使用80天周期以更接近 Futu，如果数据不足则使用所有可用数据
            vwap_period = min(80, len(closes)) if len(closes) >= 80 else None
            vwap_data = calculate_vwap(closes, highs, lows, volumes, period=vwap_period)
            result.update(vwap_data)
        
        # 19. SAR（抛物线转向指标）
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
        
        # 5.4 VWAP位置确认
        if 'vwap' in indicators and 'current_price' in indicators:
            vwap = indicators['vwap']
            price = indicators['current_price']
            if price > vwap:
                deviation = indicators.get('vwap_deviation', 0)
                signals['signals'].append(f'✅ 价格在VWAP之上(偏离{deviation:.1f}%) - 多头占优')
                signals['score'] += 8
            else:
                deviation = indicators.get('vwap_deviation', 0)
                signals['signals'].append(f'❌ 价格在VWAP之下(偏离{deviation:.1f}%) - 空头占优')
                signals['score'] -= 8
                
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
        
        # 16. VWAP价格位置（机构成本线分析）
        if 'vwap' in indicators and 'current_price' in indicators:
            vwap = indicators['vwap']
            current_price = indicators['current_price']
            vwap_deviation = indicators.get('vwap_deviation', 0)
            vwap_signal = indicators.get('vwap_signal', 'at')
            
            if vwap_signal == 'above':
                if vwap_deviation > 3:
                    signals['signals'].append(f'💰 价格远高于VWAP(${vwap:.2f}, +{vwap_deviation:.1f}%) - 强势多头')
                    signals['score'] += 15
                else:
                    signals['signals'].append(f'📈 价格在VWAP(${vwap:.2f}, +{vwap_deviation:.1f}%)之上 - 多头信号')
                    signals['score'] += 12
            elif vwap_signal == 'below':
                if vwap_deviation < -3:
                    signals['signals'].append(f'📉 价格远低于VWAP(${vwap:.2f}, {vwap_deviation:.1f}%) - 弱势空头')
                    signals['score'] -= 15
                else:
                    signals['signals'].append(f'📉 价格在VWAP(${vwap:.2f}, {vwap_deviation:.1f}%)之下 - 空头信号')
                    signals['score'] -= 12
            else:
                signals['signals'].append(f'⚖️ 价格等于VWAP(${vwap:.2f}) - 平衡状态')
        
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
        risk_assessment = _assess_risk(indicators)
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
        stop_loss_profit = _calculate_stop_loss_profit(indicators)
        signals['stop_loss'] = stop_loss_profit.get('stop_loss')
        signals['take_profit'] = stop_loss_profit.get('take_profit')
            
        return signals

def _assess_risk(indicators: dict):
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

def _calculate_stop_loss_profit(indicators: dict):
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
        
        position_sizing = _calculate_position_sizing(indicators, result)
        result.update(position_sizing)
        
        return result

def _calculate_position_sizing(indicators: dict, stop_loss_data: dict):
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


# ==================== API接口 ====================

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


def _check_ollama_available():
    """
    检查 Ollama 是否可用
    """
    try:
        import ollama
        import requests
        
        ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        
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


def _perform_ai_analysis(symbol, indicators, signals, duration, model='deepseek-v3.1:671b-cloud'):
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
                            financial_parts.append(f"{label}: ${val:.2f}")
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
   - VWAP: ${indicators.get('vwap', 0):.2f}
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
   - VWAP成交量加权平均价: ${indicators.get('vwap', 0):.2f}
   - VWAP偏离度: {indicators.get('vwap_deviation', 0):.2f}%
   - VWAP信号: {indicators.get('vwap_signal', 'neutral')}
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
   - VWAP位置分析：当前价格相对于机构成本线的位置
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
5. 操作建议: 建议的止损止盈位、仓位管理建议（重点关注SAR止损位和VWAP价格偏离度）
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
   - VWAP: ${indicators.get('vwap', 0):.2f}
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
2. 关键技术信号解读（包括CCI、ADX、VWAP、SAR等现代技术指标）
3. 买入/卖出/观望的具体建议（基于纯技术分析）
4. 风险提示和注意事项（重点关注ADX趋势强度和CCI超买超卖）
5. 建议的止损止盈位（参考SAR抛物线和VWAP支撑压力）
6. 市场情绪和可能的情境分析（如牛市、熊市、震荡市中的不同策略）

请用中文回答，简洁专业，重点突出。"""

        # 调用Ollama（使用环境变量配置的服务地址）
        ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
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
        if _check_ollama_available():
            logger.info(f"缓存中有数据但无AI分析，执行AI分析...")
            try:
                ai_analysis = _perform_ai_analysis(
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
    
    if _check_ollama_available():
        logger.info(f"检测到 Ollama 可用，开始AI分析...")
        try:
            ai_analysis = _perform_ai_analysis(symbol_upper, indicators, signals, duration, model)
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
    
    if _check_ollama_available():
        logger.info(f"检测到 Ollama 可用，开始AI分析...")
        try:
            ai_analysis = _perform_ai_analysis(symbol_upper, indicators, signals, duration, model)
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
def get_hot_stocks():
    """
    获取热门股票代码列表（从SQLite数据库查询过的股票中获取）
    查询参数:
    - limit: 返回数量限制 (默认: 20)
    """
    limit = int(request.args.get('limit', 20))
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 从数据库查询所有不同的股票代码，按查询次数和最近查询时间排序
        # 同时关联stock_info表获取股票全名
        cursor.execute('''
            SELECT 
                ac.symbol,
                COUNT(*) as query_count,
                MAX(ac.created_at) as last_query_time,
                si.name
            FROM analysis_cache ac
            LEFT JOIN stock_info si ON ac.symbol = si.symbol
            GROUP BY ac.symbol
            ORDER BY query_count DESC, last_query_time DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # 构建返回结果
        hot_stocks = []
        for row in rows:
            symbol = row[0]
            stock_name = row[3] if row[3] else symbol  # 如果有名称就用名称，否则用代码
            hot_stocks.append({
                'symbol': symbol,
                'name': stock_name,
                'category': '已查询'
            })
        
        # 如果数据库中没有数据，返回空列表
        return jsonify({
            'success': True,
            'market': 'US',
            'count': len(hot_stocks),
            'stocks': hot_stocks
        })
    except Exception as e:
        logger.error(f"查询热门股票失败: {e}")
        # 如果查询失败，返回空列表
        return jsonify({
            'success': True,
            'market': 'US',
            'count': 0,
            'stocks': []
        })


def _load_indicator_info():
    """
    从JSON文件加载技术指标解释和参考范围
    """
    try:
        json_path = os.path.join(os.path.dirname(__file__), 'indicator_info.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"未找到指标信息文件: {json_path}")
        return {}
    except Exception as e:
        logger.error(f"加载指标信息失败: {e}")
        return {}

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
    import os
    
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
