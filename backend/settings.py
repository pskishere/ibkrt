#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
设置和数据库模块 - 存放全局配置、常量和数据库操作
"""

import logging
import os
import sqlite3
import json
import pandas as pd
import numpy as np
from datetime import date

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# 数据库路径
DB_PATH = os.getenv('DB_PATH', 'stock_cache.db')

# Ollama配置
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
DEFAULT_AI_MODEL = 'deepseek-v3.1:671b-cloud'


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
    
    # 创建K线数据表，用于缓存全量K线数据
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
    except sqlite3.OperationalError as e:
        # 如果表不存在，尝试初始化数据库后重试
        if 'no such table' in str(e).lower():
            logger.warning(f"数据库表不存在，正在初始化数据库: {e}")
            try:
                init_database()
                # 重试保存
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                today = date.today().isoformat()
                indicators_json = json.dumps(result.get('indicators', {}), cls=JSONEncoder, ensure_ascii=False)
                signals_json = json.dumps(result.get('signals', {}), cls=JSONEncoder, ensure_ascii=False)
                candles_json = json.dumps(result.get('candles', []), cls=JSONEncoder, ensure_ascii=False)
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
                logger.info(f"分析结果已缓存（重试成功）: {symbol}, {duration}, {bar_size}")
            except Exception as retry_error:
                logger.error(f"保存缓存失败（重试后）: {retry_error}")
        else:
            logger.error(f"保存缓存失败: {e}")
    except Exception as e:
        logger.error(f"保存缓存失败: {e}")


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


def get_kline_from_cache(symbol: str, interval: str, start_date: str = None):
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


def save_kline_to_cache(symbol: str, interval: str, df: pd.DataFrame):
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


def get_hot_stocks(limit=20):
    """
    获取热门股票代码列表（从SQLite数据库查询过的股票中获取）
    """
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
        
        return hot_stocks
    except Exception as e:
        logger.error(f"查询热门股票失败: {e}")
        return []

