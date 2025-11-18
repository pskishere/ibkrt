
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基于IBAPI的实盘交易网关 - RESTful API服务
提供账户信息、下单、撤单、持仓查询等HTTP接口
"""

# 标准库导入
import logging
import threading
import time
import sqlite3
import json
import os
from datetime import datetime, date

# 第三方库导入
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.wrapper import EWrapper

# 技术指标模块导入
from indicators import (
    calculate_ma, calculate_rsi, calculate_bollinger, calculate_macd,
    calculate_volume, calculate_price_change, calculate_volatility,
    calculate_support_resistance, calculate_kdj, calculate_atr,
    calculate_williams_r, calculate_obv, analyze_trend_strength,
    calculate_fibonacci_retracement, calculate_chanlun_analysis, get_trend,
    calculate_cci, calculate_adx, calculate_vwap, calculate_sar
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局网关实例
gateway = None

# SQLite 数据库路径
DB_PATH = 'stock_cache.db'

def init_database():
    """
    初始化SQLite数据库，创建分析结果缓存表和股票信息表
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
    
    # 创建索引以提高查询速度
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_symbol_duration_bar_date 
        ON analysis_cache(symbol, duration, bar_size, query_date)
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
            json.dumps(result.get('indicators', {})),
            json.dumps(result.get('signals', {})),
            json.dumps(result.get('candles', [])),
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


class IBGateway(EWrapper, EClient):
    """
    Interactive Brokers 交易网关
    继承EWrapper处理回调，继承EClient发送请求
    """
    
    def __init__(self):
        EClient.__init__(self, self)
        
        # 连接状态
        self.connected = False
        self.next_order_id = None
        
        # 数据存储
        self.accounts = []
        self.account_values = {}
        self.positions = {}
        self.orders = {}
        self.executions = {}
        
        # 行情数据存储
        self.market_data = {}  # 实时报价数据
        self.historical_data = {}  # 历史数据
        self.contract_details = {}  # 合约详情
        self.fundamental_data = {}  # 基本面数据
        self.req_id_counter = 1000  # 请求ID计数器
        self._fundamental_errors = {}  # 基本面数据错误跟踪（用于静默处理430错误）
        self.request_errors = {}  # 记录请求错误: {reqId: {'code': int, 'message': str}}
        
        # 线程锁
        self.lock = threading.Lock()
        
    # ==================== 连接相关回调 ====================
    
    def nextValidId(self, orderId: int):
        """
        接收下一个有效的订单ID
        """
        # 不调用super()以避免打印ANSWER日志
        self.next_order_id = orderId
        
    def connectAck(self):
        """
        连接确认回调
        """
        pass
        
    def connectionClosed(self):
        """
        连接关闭回调
        """
        super().connectionClosed()
        self.connected = False
        logger.warning("连接已关闭")
        
    # ==================== 账户相关回调 ====================
    
    def managedAccounts(self, accountsList: str):
        """
        接收管理的账户列表
        """
        # 不调用super()以避免打印ANSWER日志
        self.accounts = accountsList.split(',')
        
    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):
        """
        接收账户信息更新
        """
        # 不调用super()以避免打印ANSWER日志
        # super().updateAccountValue(key, val, currency, accountName)
        
        if accountName not in self.account_values:
            self.account_values[accountName] = {}
            
        self.account_values[accountName][key] = {
            'value': val,
            'currency': currency
        }
        
    def updatePortfolio(self, contract: Contract, position: float,
                       marketPrice: float, marketValue: float,
                       averageCost: float, unrealizedPNL: float,
                       realizedPNL: float, accountName: str):
        """
        接收持仓更新
        """
        # 不调用super()以避免打印ANSWER日志
        # super().updatePortfolio(contract, position, marketPrice, marketValue,
        #                        averageCost, unrealizedPNL, realizedPNL, accountName)
        
        key = f"{contract.symbol}_{contract.secType}_{contract.exchange}"
        
        with self.lock:
            self.positions[key] = {
                'symbol': contract.symbol,
                'secType': contract.secType,
                'exchange': contract.exchange,
                'position': position,
                'marketPrice': marketPrice,
                'marketValue': marketValue,
                'averageCost': averageCost,
                'unrealizedPNL': unrealizedPNL,
                'realizedPNL': realizedPNL,
                'accountName': accountName
            }
            
    def accountDownloadEnd(self, accountName: str):
        """
        账户数据下载完成
        """
        # 不调用super()以避免打印ANSWER日志
        pass
        
    # ==================== 订单相关回调 ====================
    
    def orderStatus(self, orderId: int, status: str, filled: float,
                   remaining: float, avgFillPrice: float, permId: int,
                   parentId: int, lastFillPrice: float, clientId: int,
                   whyHeld: str, mktCapPrice: float):
        """
        接收订单状态更新
        """
        # 不调用super()以避免打印ANSWER日志
        # super().orderStatus(orderId, status, filled, remaining,
        #                    avgFillPrice, permId, parentId, lastFillPrice,
        #                    clientId, whyHeld, mktCapPrice)
        
        with self.lock:
            if orderId not in self.orders:
                self.orders[orderId] = {}
                
            self.orders[orderId].update({
                'status': status,
                'filled': filled,
                'remaining': remaining,
                'avgFillPrice': avgFillPrice,
                'permId': permId,
                'lastFillPrice': lastFillPrice,
                'timestamp': datetime.now().isoformat()
            })
        
    def openOrder(self, orderId: int, contract: Contract, order: Order,
                 orderState):
        """
        接收订单信息
        """
        # 不调用super()以避免打印ANSWER日志
        # super().openOrder(orderId, contract, order, orderState)
        
        with self.lock:
            if orderId not in self.orders:
                self.orders[orderId] = {}
                
            self.orders[orderId].update({
                'orderId': orderId,
                'symbol': contract.symbol,
                'secType': contract.secType,
                'exchange': contract.exchange,
                'action': order.action,
                'orderType': order.orderType,
                'totalQuantity': order.totalQuantity,
                'lmtPrice': order.lmtPrice,
                'auxPrice': order.auxPrice,
                'status': orderState.status
            })
            
    def execDetails(self, reqId: int, contract: Contract, execution):
        """
        接收成交明细
        """
        # 不调用super()以避免打印ANSWER日志
        # super().execDetails(reqId, contract, execution)
        
        exec_id = execution.execId
        
        with self.lock:
            self.executions[exec_id] = {
                'execId': exec_id,
                'orderId': execution.orderId,
                'symbol': contract.symbol,
                'secType': contract.secType,
                'side': execution.side,
                'shares': execution.shares,
                'price': execution.price,
                'time': execution.time,
                'exchange': execution.exchange,
                'cumQty': execution.cumQty,
                'avgPrice': execution.avgPrice
            }
        
    def error(self, reqId: int, errorCode: int, errorString: str):
        """
        接收错误信息
        """
        # 忽略信息提示和已知的可忽略错误
        ignore_codes = [
            2104, 2106, 2158,  # 连接信息提示
            10148,  # 订单已在撤销中
            10147,  # 订单已撤销
            2119, 2120,  # 行情数据延迟提示
            430,  # 指定证券没有基本面数据（正常情况，静默跳过）
        ]
        
        # 记录基本面数据请求的错误码（用于静默处理）
        if errorCode == 430 and reqId > 0:
            with self.lock:
                self._fundamental_errors[reqId] = errorCode
            # 430错误完全静默处理，不调用super()也不记录日志
            return
        
        # 记录重要错误（如200 - 证券不存在）
        if reqId > 0 and errorCode in [200, 201, 162, 354, 10197]:  # 常见的证券相关错误
            with self.lock:
                self.request_errors[reqId] = {
                    'code': errorCode,
                    'message': errorString
                }
        
        # 对于需要忽略的错误，不调用super()以避免打印日志
        if errorCode in ignore_codes:
            return
        
        # 其他错误才调用super()和记录日志
        super().error(reqId, errorCode, errorString)
        
        # 订单相关错误特别标注
        if reqId > 0 and errorCode >= 100:
            logger.error(f"请求 #{reqId} 错误 [{errorCode}]: {errorString}")
        else:
            logger.error(f"[{errorCode}] {errorString}")
                
    # ==================== 行情数据回调 ====================
    
    def tickPrice(self, reqId: int, tickType: int, price: float, attrib):
        """
        接收实时价格数据
        """
        with self.lock:
            if reqId not in self.market_data:
                self.market_data[reqId] = {}
            
            # tickType: 1=买价, 2=卖价, 4=最新价, 6=最高, 7=最低, 9=收盘价
            tick_names = {
                1: 'bid', 2: 'ask', 4: 'last', 
                6: 'high', 7: 'low', 9: 'close'
            }
            
            if tickType in tick_names:
                self.market_data[reqId][tick_names[tickType]] = price
                
    def tickSize(self, reqId: int, tickType: int, size: int):
        """
        接收实时数量数据
        """
        with self.lock:
            if reqId not in self.market_data:
                self.market_data[reqId] = {}
            
            # tickType: 0=买量, 3=卖量, 5=最新量, 8=成交量
            tick_names = {
                0: 'bid_size', 3: 'ask_size', 
                5: 'last_size', 8: 'volume'
            }
            
            if tickType in tick_names:
                self.market_data[reqId][tick_names[tickType]] = size
                
    def historicalData(self, reqId: int, bar):
        """
        接收历史K线数据
        """
        with self.lock:
            if reqId not in self.historical_data:
                self.historical_data[reqId] = []
            
            self.historical_data[reqId].append({
                'date': bar.date,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume,
                'average': bar.average,
                'barCount': bar.barCount
            })
            
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """
        历史数据接收完成
        """
        logger.info(f"历史数据接收完成: reqId={reqId}")
        
    def contractDetails(self, reqId: int, contractDetails):
        """
        接收合约详情
        """
        with self.lock:
            if reqId not in self.contract_details:
                self.contract_details[reqId] = []
            
            contract = contractDetails.contract
            
            # 安全获取属性，避免AttributeError
            details = {
                'symbol': getattr(contract, 'symbol', ''),
                'secType': getattr(contract, 'secType', ''),
                'exchange': getattr(contract, 'exchange', ''),
                'currency': getattr(contract, 'currency', ''),
                'longName': getattr(contractDetails, 'longName', ''),
                'industry': getattr(contractDetails, 'industry', ''),
                'category': getattr(contractDetails, 'category', ''),
                'subcategory': getattr(contractDetails, 'subcategory', ''),
                'marketName': getattr(contractDetails, 'marketName', ''),
                'tradingClass': getattr(contract, 'tradingClass', ''),
                'minTick': getattr(contractDetails, 'minTick', 0),
                'multiplier': getattr(contract, 'multiplier', ''),
                'timeZoneId': getattr(contractDetails, 'timeZoneId', ''),
                'tradingHours': getattr(contractDetails, 'tradingHours', ''),
                'liquidHours': getattr(contractDetails, 'liquidHours', ''),
                'conId': getattr(contract, 'conId', 0),
                'localSymbol': getattr(contract, 'localSymbol', ''),
            }
            
            self.contract_details[reqId].append(details)
            
    def contractDetailsEnd(self, reqId: int):
        """
        合约详情接收完成
        """
        logger.info(f"合约详情接收完成: reqId={reqId}")
        
    def fundamentalData(self, reqId: int, data: str):
        """
        接收基本面数据（XML格式）
        """
        with self.lock:
            self.fundamental_data[reqId] = data
        logger.info(f"基本面数据接收完成: reqId={reqId}")
            
    # ==================== 网关操作方法 ====================
    
    def connect_gateway(self, host='127.0.0.1', port=7496, client_id=1):
        """
        连接到IB TWS
        """
        logger.info(f"连接 {host}:{port}, ClientId: {client_id}")
        
        try:
            # 先断开已有连接
            if self.isConnected():
                logger.info("检测到已有连接，先断开")
                self.disconnect()
                time.sleep(1)
            
            self.connect(host, port, client_id)
            logger.info("Socket连接已建立，等待响应...")
            
            # 启动消息处理线程
            api_thread = threading.Thread(target=self.run, daemon=True)
            api_thread.start()
            
            # 等待连接建立
            timeout = 15
            start_time = time.time()
            
            while self.next_order_id is None:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    logger.error(f"连接超时({timeout}秒)")
                    logger.error("可能的原因:")
                    logger.error("  1. IB Gateway未完全启动")
                    logger.error("  2. ClientId冲突（尝试修改client_id）")
                    logger.error("  3. API设置未启用")
                    self.disconnect()
                    return False
                    
                # 每3秒打印一次等待信息
                if int(elapsed) > 0 and int(elapsed) % 3 == 0 and elapsed - int(elapsed) < 0.2:
                    logger.info(f"等待中... {int(elapsed)}秒")
                    
                time.sleep(0.1)
                
            self.connected = True
            logger.info(f"连接成功！下一个订单ID: {self.next_order_id}")
            
            # 订阅账户更新
            if self.accounts:
                logger.info(f"订阅账户: {self.accounts}")
                self.reqAccountUpdates(True, self.accounts[0])
            
            # 请求所有未完成订单
            self.reqAllOpenOrders()
                
            return True
            
        except Exception as e:
            logger.error(f"连接异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
    def disconnect_gateway(self):
        """
        断开连接
        """
        if self.connected:
            self.disconnect()
            self.connected = False
            
    def create_stock_contract(self, symbol: str, exchange: str = 'SMART', currency: str = 'USD'):
        """
        创建股票合约
        """
        contract = Contract()
        contract.symbol = symbol
        contract.secType = 'STK'
        contract.exchange = exchange
        contract.currency = currency
        return contract
        
    def create_order(self, action: str, quantity: float, order_type: str = 'MKT',
                    limit_price: float = 0, aux_price: float = 0):
        """
        创建订单对象
        """
        order = Order()
        order.action = action
        order.totalQuantity = quantity
        order.orderType = order_type
        order.eTradeOnly = False
        order.firmQuoteOnly = False
        
        if order_type == 'LMT':
            order.lmtPrice = limit_price
        elif order_type == 'STP':
            order.auxPrice = aux_price
            
        return order
        
    def submit_order(self, contract: Contract, order: Order):
        """
        提交订单
        """
        if not self.connected or self.next_order_id is None:
            return None
            
        order_id = self.next_order_id
        self.placeOrder(order_id, contract, order)
        self.next_order_id += 1
        
        logger.info(f"订单 #{order_id}: {order.action} {contract.symbol} x{order.totalQuantity}")
        
        # 短暂延迟后请求订单更新
        time.sleep(0.5)
        self.reqAllOpenOrders()
        
        return order_id
        
    def cancel_order(self, order_id: int):
        """
        撤销订单
        """
        if not self.connected:
            logger.warning("未连接，无法撤销订单")
            return False
        
        # 检查订单是否存在以及状态
        with self.lock:
            if order_id in self.orders:
                status = self.orders[order_id].get('status', '')
                logger.info(f"订单 #{order_id} 当前状态: {status}")
                if status in ['Cancelled', 'PendingCancel', 'Filled']:
                    logger.warning(f"订单 #{order_id} 状态为 {status}，无需撤销")
                    return False
            else:
                logger.warning(f"订单 #{order_id} 不存在于本地缓存")
            
        self.cancelOrder(order_id)
        logger.info(f"发送撤销请求: 订单 #{order_id}")
        return True
        
    def get_account_summary(self):
        """
        获取账户摘要信息
        """
        if not self.account_values:
            return None
            
        summary = {}
        for account, values in self.account_values.items():
            summary[account] = {
                'netLiquidation': values.get('NetLiquidation', {}).get('value', 'N/A'),
                'availableFunds': values.get('AvailableFunds', {}).get('value', 'N/A'),
                'buyingPower': values.get('BuyingPower', {}).get('value', 'N/A'),
                'totalCash': values.get('TotalCashValue', {}).get('value', 'N/A'),
                'unrealizedPnL': values.get('UnrealizedPnL', {}).get('value', 'N/A'),
                'realizedPnL': values.get('RealizedPnL', {}).get('value', 'N/A')
            }
            
        return summary
        
    def get_positions(self):
        """
        获取持仓列表
        """
        with self.lock:
            return dict(self.positions)
            
    def get_orders(self):
        """
        获取订单列表
        """
        with self.lock:
            return dict(self.orders)
            
    def get_executions(self):
        """
        获取成交列表
        """
        with self.lock:
            return dict(self.executions)
            
    def get_market_data(self, symbol: str, exchange: str = 'SMART', currency: str = 'USD'):
        """
        获取实时行情快照
        """
        if not self.connected:
            return None
            
        # 创建合约
        contract = self.create_stock_contract(symbol, exchange, currency)
        
        # 生成请求ID
        req_id = self.req_id_counter
        self.req_id_counter += 1
        
        # 清空旧数据
        with self.lock:
            self.market_data[req_id] = {'symbol': symbol}
        
        logger.info(f"请求行情数据: {symbol}, reqId={req_id}")
        
        # 请求实时数据（使用快照模式）
        self.reqMktData(req_id, contract, "", True, False, [])
        
        # 等待数据返回，最多等待5秒
        max_wait = 5
        start_time = time.time()
        data_received = False
        
        while time.time() - start_time < max_wait:
            with self.lock:
                data = self.market_data.get(req_id, {})
                # 检查是否有价格数据（至少有一个价格字段）
                if any(key in data for key in ['last', 'bid', 'ask', 'close']):
                    data_received = True
                    break
            time.sleep(0.2)
        
        # 获取最终数据
        with self.lock:
            data = self.market_data.get(req_id, {}).copy()
        
        # 取消订阅
        self.cancelMktData(req_id)
        
        if data_received:
            logger.info(f"行情数据接收成功: {symbol}, 字段数: {len(data)}")
        else:
            logger.warning(f"行情数据接收超时: {symbol}")
        
        return data
        
    def get_historical_data(self, symbol: str, duration: str = '1 D', 
                           bar_size: str = '5 mins', exchange: str = 'SMART', 
                           currency: str = 'USD'):
        """
        获取历史数据
        duration: 数据周期，如 '1 D', '1 W', '1 M'
        bar_size: K线周期，如 '1 min', '5 mins', '1 hour', '1 day'
        """
        if not self.connected:
            return None
            
        # 创建合约
        contract = self.create_stock_contract(symbol, exchange, currency)
        
        # 生成请求ID
        req_id = self.req_id_counter
        self.req_id_counter += 1
        
        # 清空旧数据
        with self.lock:
            self.historical_data[req_id] = []
        
        logger.info(f"请求历史数据: {symbol}, {duration}, {bar_size}, reqId={req_id}")
        
        # 请求历史数据
        end_datetime = ""  # 空字符串表示当前时间
        what_to_show = "TRADES"
        use_rth = 1  # 1=只使用常规交易时间, 0=包含盘前盘后
        format_date = 1  # 1=yyyyMMdd HH:mm:ss格式
        
        self.reqHistoricalData(
            req_id, contract, end_datetime, duration,
            bar_size, what_to_show, use_rth, format_date, False, []
        )
        
        # 等待数据返回（历史数据可能需要更长时间）
        max_wait = 15
        start_time = time.time()
        data_complete = False
        has_error = False
        
        while time.time() - start_time < max_wait:
            # 检查是否有错误
            with self.lock:
                if req_id in self.request_errors:
                    has_error = True
                    break
                    
            with self.lock:
                current_count = len(self.historical_data.get(req_id, []))
                if current_count > 0:
                    # 等待一段时间确保数据接收完整
                    time.sleep(1)
                    new_count = len(self.historical_data.get(req_id, []))
                    # 如果数据不再增加，认为接收完成
                    if new_count == current_count:
                        data_complete = True
                        break
            time.sleep(0.3)
        
        # 检查是否有错误
        error_info = None
        with self.lock:
            if req_id in self.request_errors:
                error_info = self.request_errors[req_id].copy()
                del self.request_errors[req_id]  # 清除错误记录
        
        # 如果有错误，返回None和错误信息
        if error_info:
            logger.warning(f"历史数据请求失败: {symbol}, 错误[{error_info['code']}]: {error_info['message']}")
            return None, error_info
        
        # 获取数据
        with self.lock:
            data = self.historical_data.get(req_id, []).copy()
        
        if data_complete and data:
            logger.info(f"历史数据接收成功: {symbol}, 数据条数: {len(data)}")
        elif data:
            logger.warning(f"历史数据可能不完整: {symbol}, 数据条数: {len(data)}")
        else:
            logger.warning(f"历史数据接收失败: {symbol}")
        
        return data, None  # 返回数据和错误信息（无错误为None）
        
    def get_stock_info(self, symbol: str, exchange: str = 'SMART', currency: str = 'USD'):
        """
        获取股票详细信息（合约详情）
        """
        if not self.connected:
            return None
            
        # 创建合约
        contract = self.create_stock_contract(symbol, exchange, currency)
        
        # 生成请求ID
        req_id = self.req_id_counter
        self.req_id_counter += 1
        
        # 清空旧数据
        with self.lock:
            self.contract_details[req_id] = []
        
        logger.info(f"请求合约详情: {symbol}, reqId={req_id}")
        
        # 请求合约详情
        self.reqContractDetails(req_id, contract)
        
        # 等待数据返回
        max_wait = 5
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            with self.lock:
                if req_id in self.contract_details and len(self.contract_details[req_id]) > 0:
                    break
            time.sleep(0.2)
        
        # 获取数据
        with self.lock:
            data = self.contract_details.get(req_id, [])
            
        if data:
            logger.info(f"合约详情接收成功: {symbol}")
            return data[0] if len(data) == 1 else data
        else:
            logger.warning(f"合约详情接收失败: {symbol}")
            return None
            
    def get_fundamental_data(self, symbol: str, report_type: str = 'ReportsFinSummary'):
        """
        获取基本面数据
        report_type: ReportsFinSummary, ReportSnapshot, ReportsFinStatements, RESC, CalendarReport
        """
        if not self.connected:
            return None
            
        # 创建合约
        contract = self.create_stock_contract(symbol)
        
        # 生成请求ID
        req_id = self.req_id_counter
        self.req_id_counter += 1
        
        # 清空旧数据
        with self.lock:
            self.fundamental_data[req_id] = None
        
        logger.info(f"请求基本面数据: {symbol}, {report_type}, reqId={req_id}")
        
        # 请求基本面数据
        self.reqFundamentalData(req_id, contract, report_type, [])
        
        # 等待数据返回
        max_wait = 10
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            with self.lock:
                # 检查是否收到数据
                if req_id in self.fundamental_data and self.fundamental_data[req_id] is not None:
                    break
                # 检查是否是430错误（没有基本面数据），如果是则立即返回
                if req_id in self._fundamental_errors:
                    break
            time.sleep(0.2)
        
        # 获取数据
        with self.lock:
            data = self.fundamental_data.get(req_id)
            # 检查是否是430错误（没有基本面数据）
            is_no_data_error = req_id in self._fundamental_errors
            if is_no_data_error:
                # 清除错误记录
                del self._fundamental_errors[req_id]
            
        if data:
            logger.info(f"基本面数据接收成功: {symbol}")
            # 简单解析XML数据
            return self._parse_fundamental_data(data)
        else:
            # 如果是430错误（没有基本面数据），静默跳过，不记录警告
            if not is_no_data_error:
                logger.warning(f"基本面数据接收失败: {symbol}")
            return None
            
    def _parse_fundamental_data(self, xml_data: str):
        """
        解析基本面数据XML
        """
        import xml.etree.ElementTree as ET
        
        try:
            root = ET.fromstring(xml_data)
            result = {}
            
            # 1. 提取公司基本信息 (CoIDs)
            co_ids = root.find('.//CoIDs')
            if co_ids is not None:
                for coid in co_ids.findall('CoID'):
                    coid_type = coid.get('Type', '')
                    if coid.text and coid.text.strip():
                        if coid_type == 'CompanyName':
                            result['CompanyName'] = coid.text.strip()
                        elif coid_type == 'CIKNo':
                            result['CIK'] = coid.text.strip()
            
            # 2. 提取公司通用信息 (CoGeneralInfo)
            co_info = root.find('.//CoGeneralInfo')
            if co_info is not None:
                employees = co_info.find('Employees')
                if employees is not None and employees.text:
                    result['Employees'] = employees.text.strip()
                
                shares_out = co_info.find('SharesOut')
                if shares_out is not None and shares_out.text:
                    result['SharesOutstanding'] = shares_out.text.strip()
            
            # 3. 提取交易所信息
            exchange = root.find('.//Exchange')
            if exchange is not None and exchange.text:
                result['Exchange'] = exchange.text.strip()
            
            # 4. 提取财务比率 (Ratios)
            ratios = root.find('.//Ratios')
            if ratios is not None:
                # 价格和成交量
                price_group = ratios.find(".//Group[@ID='Price and Volume']")
                if price_group is not None:
                    for ratio in price_group.findall('Ratio'):
                        field_name = ratio.get('FieldName', '')
                        if ratio.text and ratio.text.strip():
                            if field_name == 'NPRICE':
                                result['Price'] = ratio.text.strip()
                            elif field_name == 'NHIG':
                                result['52WeekHigh'] = ratio.text.strip()
                            elif field_name == 'NLOW':
                                result['52WeekLow'] = ratio.text.strip()
                            elif field_name == 'VOL10DAVG':
                                result['AvgVolume10D'] = ratio.text.strip()
                            elif field_name == 'EV':
                                result['EnterpriseValue'] = ratio.text.strip()
                
                # 利润表数据
                income_group = ratios.find(".//Group[@ID='Income Statement']")
                if income_group is not None:
                    for ratio in income_group.findall('Ratio'):
                        field_name = ratio.get('FieldName', '')
                        if ratio.text and ratio.text.strip():
                            if field_name == 'MKTCAP':
                                result['MarketCap'] = ratio.text.strip()
                            elif field_name == 'TTMREV':
                                result['RevenueTTM'] = ratio.text.strip()
                            elif field_name == 'TTMEBITD':
                                result['EBITDATTM'] = ratio.text.strip()
                            elif field_name == 'TTMNIAC':
                                result['NetIncomeTTM'] = ratio.text.strip()
                
                # 每股数据
                per_share_group = ratios.find(".//Group[@ID='Per share data']")
                if per_share_group is not None:
                    for ratio in per_share_group.findall('Ratio'):
                        field_name = ratio.get('FieldName', '')
                        if ratio.text and ratio.text.strip():
                            if field_name == 'TTMEPSXCLX':
                                result['EPS'] = ratio.text.strip()
                            elif field_name == 'TTMREVPS':
                                result['RevenuePerShare'] = ratio.text.strip()
                            elif field_name == 'QBVPS':
                                result['BookValuePerShare'] = ratio.text.strip()
                            elif field_name == 'QCSHPS':
                                result['CashPerShare'] = ratio.text.strip()
                            elif field_name == 'TTMCFSHR':
                                result['CashFlowPerShare'] = ratio.text.strip()
                            elif field_name == 'TTMDIVSHR':
                                result['DividendPerShare'] = ratio.text.strip()
                
                # 其他比率
                other_group = ratios.find(".//Group[@ID='Other Ratios']")
                if other_group is not None:
                    for ratio in other_group.findall('Ratio'):
                        field_name = ratio.get('FieldName', '')
                        if ratio.text and ratio.text.strip():
                            if field_name == 'TTMGROSMGN':
                                result['GrossMargin'] = ratio.text.strip()
                            elif field_name == 'TTMROEPCT':
                                result['ROE'] = ratio.text.strip()
                            elif field_name == 'TTMPR2REV':
                                result['ProfitMargin'] = ratio.text.strip()
                            elif field_name == 'PEEXCLXOR':
                                result['PE'] = ratio.text.strip()
                            elif field_name == 'PRICE2BK':
                                result['PriceToBook'] = ratio.text.strip()
            
            # 5. 提取预测数据 (ForecastData)
            forecast = root.find('.//ForecastData')
            if forecast is not None:
                target_price = forecast.find(".//Ratio[@FieldName='TargetPrice']/Value")
                if target_price is not None and target_price.text:
                    result['TargetPrice'] = target_price.text.strip()
                
                consensus = forecast.find(".//Ratio[@FieldName='ConsRecom']/Value")
                if consensus is not None and consensus.text:
                    result['ConsensusRecommendation'] = consensus.text.strip()
                
                proj_eps = forecast.find(".//Ratio[@FieldName='ProjEPS']/Value")
                if proj_eps is not None and proj_eps.text:
                    result['ProjectedEPS'] = proj_eps.text.strip()
                
                proj_growth = forecast.find(".//Ratio[@FieldName='ProjLTGrowthRate']/Value")
                if proj_growth is not None and proj_growth.text:
                    result['ProjectedGrowthRate'] = proj_growth.text.strip()
            
            return result if result else {'raw_xml': xml_data}
        except Exception as e:
            logger.error(f"解析基本面数据失败: {e}")
            return {'raw_xml': xml_data}
            
    def calculate_technical_indicators(self, symbol: str, duration: str = '1 M', bar_size: str = '1 day'):
        """
        计算技术指标（基于历史数据）
        返回：移动平均线、RSI、MACD等
        如果证券不存在，返回(None, error_info)
        """
        # 获取历史数据
        hist_data, error = self.get_historical_data(symbol, duration, bar_size)
        
        # 如果有错误，返回错误信息
        if error:
            return None, error
        
        if not hist_data or len(hist_data) < 20:
            logger.warning(f"数据不足，无法计算技术指标: {symbol}")
            return None, None
            
        import numpy as np
        
        # 提取收盘价
        closes = np.array([bar['close'] for bar in hist_data])
        highs = np.array([bar['high'] for bar in hist_data])
        lows = np.array([bar['low'] for bar in hist_data])
        volumes = np.array([bar['volume'] for bar in hist_data])
        
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
            
        # 8. 支撑位和压力位
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

        # 15. 缠论分析（已优化63日数据）
        chanlun_data = calculate_chanlun_analysis(closes, highs, lows, volumes)
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
        if len(closes) >= 1:
            vwap_data = calculate_vwap(closes, highs, lows, volumes)
            result.update(vwap_data)
        
        # 19. SAR（抛物线转向指标）
        if len(closes) >= 10:
            sar_data = calculate_sar(closes, highs, lows)
            result.update(sar_data)

        # 20. IBKR基本面数据
        try:
            fundamental_data = self.get_fundamental_data(symbol, 'ReportSnapshot')
            if fundamental_data:
                result['fundamental_data'] = fundamental_data
                logger.info(f"基本面数据已添加到技术指标: {symbol}")
            # 如果没有基本面数据（如ETF等），静默跳过，不记录警告
        except Exception as e:
            # 只有非预期的异常才记录警告
            logger.warning(f"获取基本面数据异常: {symbol}, 错误: {e}")
            # 基本面数据获取失败不影响技术指标返回
            
        return result, None  # 返回结果和错误信息（无错误为None）
        
    def generate_signals(self, indicators: dict):
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
                
        # 5. 成交量
        if 'volume_ratio' in indicators:
            ratio = indicators['volume_ratio']
            if ratio > 1.5:
                signals['signals'].append(f'📊 成交量放大{ratio:.1f}倍 - 趋势加强')
                signals['score'] += 10
            elif ratio < 0.5:
                signals['signals'].append(f'📊 成交量萎缩 - 趋势减弱')
                
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
                signals['signals'].append(f'🔴 CCI={cci:.1f} 超买区域 - 可能回调')
                signals['score'] -= 15
            elif cci_signal == 'oversold':
                signals['signals'].append(f'🟢 CCI={cci:.1f} 超卖区域 - 可能反弹')
                signals['score'] += 15
        
        # 15. ADX趋势强度
        if 'adx' in indicators:
            adx = indicators['adx']
            adx_signal = indicators.get('adx_signal', 'weak_trend')
            adx_direction = indicators.get('trend_direction', 'neutral')
            
            if adx_signal == 'strong_trend':
                if adx_direction == 'up':
                    signals['signals'].append(f'🚀 ADX={adx:.1f} 强势上涨趋势 - 顺势做多')
                    signals['score'] += 20
                elif adx_direction == 'down':
                    signals['signals'].append(f'⚠️ ADX={adx:.1f} 强势下跌趋势 - 观望或做空')
                    signals['score'] -= 20
            elif adx_signal == 'weak_trend':
                signals['signals'].append(f'📊 ADX={adx:.1f} 趋势不明显 - 震荡行情')
        
        # 16. VWAP价格位置
        if 'vwap' in indicators and 'current_price' in indicators:
            vwap = indicators['vwap']
            current_price = indicators['current_price']
            vwap_signal = indicators.get('vwap_signal', 'at')
            
            if vwap_signal == 'above':
                signals['signals'].append(f'📈 价格在VWAP(${vwap:.2f})之上 - 多头信号')
                signals['score'] += 10
            elif vwap_signal == 'below':
                signals['signals'].append(f'📉 价格在VWAP(${vwap:.2f})之下 - 空头信号')
                signals['score'] -= 10
        
        # 17. SAR转向信号
        if 'sar' in indicators:
            sar = indicators['sar']
            sar_signal = indicators.get('sar_signal', 'hold')
            sar_trend = indicators.get('sar_trend', 'neutral')
            
            if sar_signal == 'buy':
                if sar_trend == 'up':
                    signals['signals'].append(f'🟢 SAR=${sar:.2f} 看涨信号')
                    signals['score'] += 15
                else:
                    signals['signals'].append(f'🟢 SAR=${sar:.2f} 转向看涨')
                    signals['score'] += 18
            elif sar_signal == 'sell':
                if sar_trend == 'down':
                    signals['signals'].append(f'🔴 SAR=${sar:.2f} 看跌信号')
                    signals['score'] -= 15
                else:
                    signals['signals'].append(f'🔴 SAR=${sar:.2f} 转向看跌')
                    signals['score'] -= 18
                
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
        risk_assessment = self._assess_risk(indicators)
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
        stop_loss_profit = self._calculate_stop_loss_profit(indicators)
        signals['stop_loss'] = stop_loss_profit.get('stop_loss')
        signals['take_profit'] = stop_loss_profit.get('take_profit')
            
        return signals
    
    def _assess_risk(self, indicators: dict):
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
    
    def _calculate_stop_loss_profit(self, indicators: dict):
        """
        计算建议的止损和止盈价位
        """
        current_price = indicators.get('current_price')
        if not current_price:
            return {}
        
        result = {}
        
        # 基于ATR的止损止盈
        if 'atr' in indicators:
            atr = indicators['atr']
            
            # 止损：当前价格 - 2倍ATR
            result['stop_loss'] = float(current_price - 2 * atr)
            
            # 止盈：当前价格 + 3倍ATR (风险回报比1.5:1)
            result['take_profit'] = float(current_price + 3 * atr)
            
        # 基于支撑压力位的止损止盈
        elif 'support_20d_low' in indicators and 'resistance_20d_high' in indicators:
            support = indicators['support_20d_low']
            resistance = indicators['resistance_20d_high']
            
            # 止损设在支撑位下方
            result['stop_loss'] = float(support * 0.98)
            
            # 止盈设在压力位
            result['take_profit'] = float(resistance)
        
        # 简单百分比止损止盈
        else:
            result['stop_loss'] = float(current_price * 0.95)  # -5%
            result['take_profit'] = float(current_price * 1.10)  # +10%
        
        # 仓位管理建议
        position_sizing = self._calculate_position_sizing(indicators, result)
        result.update(position_sizing)
        
        return result
    
    def _calculate_position_sizing(self, indicators: dict, stop_loss_data: dict):
        """
        计算建议的仓位大小和风险管理
        """
        result = {}
        
        current_price = indicators.get('current_price')
        stop_loss = stop_loss_data.get('stop_loss')
        
        if not current_price or not stop_loss:
            return result
            
        # 计算每股风险
        risk_per_share = current_price - stop_loss
        
        # 假设账户风险承受能力为总资金的2%
        # 这里我们使用一个示例账户价值，实际应用中应该从账户信息获取
        account_value = 100000  # 假设账户价值为10万美元
        max_risk_amount = account_value * 0.02  # 最大风险金额为账户的2%
        
        # 计算建议仓位大小
        if risk_per_share > 0:
            suggested_position_size = int(max_risk_amount / risk_per_share)
            result['suggested_position_size'] = suggested_position_size
            result['position_risk_amount'] = float(suggested_position_size * risk_per_share)
            
            # 计算仓位价值
            position_value = suggested_position_size * current_price
            result['position_value'] = float(position_value)
            
            # 计算仓位占账户比例
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
            
            # 添加仓位管理建议
            result['position_sizing_advice'] = {
                'max_risk_percent': 2,  # 最大风险百分比
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
        'connected': gateway.connected if gateway else False,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/connect', methods=['POST'])
def connect():
    """
    连接到IB TWS
    请求参数:
    {
        "host": "127.0.0.1",
        "port": 7496,
        "client_id": 1
    }
    """
    global gateway
    
    data = request.get_json() or {}
    host = data.get('host', '127.0.0.1')
    port = data.get('port', 7496)
    client_id = data.get('client_id', 1)
    
    if gateway and gateway.connected:
        return jsonify({
            'success': True,
            'message': '已经连接',
            'accounts': gateway.accounts
        })
    
    gateway = IBGateway()
    success = gateway.connect_gateway(host, port, client_id)
    
    if success:
        # 等待数据加载
        time.sleep(2)
        return jsonify({
            'success': True,
            'message': '连接成功',
            'accounts': gateway.accounts
        })
    else:
        return jsonify({
            'success': False,
            'message': '连接失败'
        }), 500


@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    """
    断开连接
    """
    global gateway
    
    if not gateway or not gateway.connected:
        return jsonify({
            'success': False,
            'message': '未连接'
        }), 400
    
    gateway.disconnect_gateway()
    return jsonify({
        'success': True,
        'message': '已断开连接'
    })


@app.route('/api/account', methods=['GET'])
def get_account():
    """
    获取账户信息
    """
    if not gateway or not gateway.connected:
        return jsonify({
            'success': False,
            'message': '未连接到网关'
        }), 400
    
    summary = gateway.get_account_summary()
    return jsonify({
        'success': True,
        'data': summary
    })


@app.route('/api/positions', methods=['GET'])
def get_positions():
    """
    获取持仓信息
    """
    if not gateway or not gateway.connected:
        return jsonify({
            'success': False,
            'message': '未连接到网关'
        }), 400
    
    positions = gateway.get_positions()
    return jsonify({
        'success': True,
        'data': list(positions.values())
    })


@app.route('/api/orders', methods=['GET'])
def get_orders():
    """
    获取订单列表
    """
    if not gateway or not gateway.connected:
        return jsonify({
            'success': False,
            'message': '未连接到网关'
        }), 400
    
    orders = gateway.get_orders()
    return jsonify({
        'success': True,
        'data': list(orders.values())
    })


@app.route('/api/executions', methods=['GET'])
def get_executions():
    """
    获取成交记录
    """
    if not gateway or not gateway.connected:
        return jsonify({
            'success': False,
            'message': '未连接到网关'
        }), 400
    
    executions = gateway.get_executions()
    return jsonify({
        'success': True,
        'data': list(executions.values())
    })


@app.route('/api/order', methods=['POST'])
def submit_order():
    """
    提交订单
    请求参数:
    {
        "symbol": "AAPL",
        "action": "BUY",
        "quantity": 100,
        "order_type": "MKT",
        "limit_price": 150.0,
        "exchange": "SMART",
        "currency": "USD"
    }
    """
    if not gateway or not gateway.connected:
        return jsonify({
            'success': False,
            'message': '未连接到网关'
        }), 400
    
    data = request.get_json()
    
    # 验证必需参数
    required_fields = ['symbol', 'action', 'quantity']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'message': f'缺少必需参数: {field}'
            }), 400
    
    try:
        # 创建合约
        contract = gateway.create_stock_contract(
            symbol=data['symbol'],
            exchange=data.get('exchange', 'SMART'),
            currency=data.get('currency', 'USD')
        )
        
        # 创建订单
        order = gateway.create_order(
            action=data['action'],
            quantity=data['quantity'],
            order_type=data.get('order_type', 'MKT'),
            limit_price=data.get('limit_price', 0),
            aux_price=data.get('aux_price', 0)
        )
        
        # 提交订单
        order_id = gateway.submit_order(contract, order)
        
        if order_id:
            return jsonify({
                'success': True,
                'message': '订单已提交',
                'order_id': order_id
            })
        else:
            return jsonify({
                'success': False,
                'message': '订单提交失败'
            }), 500
            
    except Exception as e:
        logger.error(f"订单异常: {e}")
        return jsonify({
            'success': False,
            'message': f'订单提交异常: {str(e)}'
        }), 500


@app.route('/api/order/<int:order_id>', methods=['DELETE'])
def cancel_order(order_id):
    """
    撤销订单
    """
    logger.info(f"收到撤单请求: 订单 #{order_id}")
    
    if not gateway or not gateway.connected:
        logger.warning("网关未连接")
        return jsonify({
            'success': False,
            'message': '未连接到网关'
        }), 400
    
    # 检查订单状态
    orders = gateway.get_orders()
    logger.info(f"当前订单列表: {list(orders.keys())}")
    
    if order_id in orders:
        status = orders[order_id].get('status', '')
        logger.info(f"订单 #{order_id} 状态: {status}")
        
        if status in ['Cancelled', 'PendingCancel']:
            logger.warning(f"订单 #{order_id} 已在撤销中或已撤销")
            return jsonify({
                'success': False,
                'message': f'订单已在撤销中或已撤销 (状态: {status})'
            }), 400
        elif status == 'Filled':
            logger.warning(f"订单 #{order_id} 已成交")
            return jsonify({
                'success': False,
                'message': '订单已成交，无法撤销'
            }), 400
    else:
        logger.warning(f"订单 #{order_id} 不在订单列表中")
    
    success = gateway.cancel_order(order_id)
    
    if success:
        logger.info(f"订单 #{order_id} 撤销请求成功")
        return jsonify({
            'success': True,
            'message': f'订单 {order_id} 撤销请求已发送'
        })
    else:
        logger.error(f"订单 #{order_id} 撤销请求失败")
        return jsonify({
            'success': False,
            'message': '撤销订单失败'
        }), 500


@app.route('/api/order/<int:order_id>', methods=['GET'])
def get_order_detail(order_id):
    """
    获取订单详情
    """
    if not gateway or not gateway.connected:
        return jsonify({
            'success': False,
            'message': '未连接到网关'
        }), 400
    
    orders = gateway.get_orders()
    
    if order_id in orders:
        return jsonify({
            'success': True,
            'data': orders[order_id]
        })
    else:
        return jsonify({
            'success': False,
            'message': '订单不存在'
        }), 404


@app.route('/api/quote/<symbol>', methods=['GET'])
def get_quote(symbol):
    """
    获取实时报价
    """
    if not gateway or not gateway.connected:
        return jsonify({
            'success': False,
            'message': '未连接到网关'
        }), 400
    
    exchange = request.args.get('exchange', 'SMART')
    currency = request.args.get('currency', 'USD')
    
    logger.info(f"查询报价: {symbol}")
    data = gateway.get_market_data(symbol.upper(), exchange, currency)
    
    if data and len(data) > 1:  # 至少有symbol和一个价格字段
        return jsonify({
            'success': True,
            'data': data
        })
    else:
        return jsonify({
            'success': False,
            'message': '无法获取报价数据'
        }), 404


@app.route('/api/history/<symbol>', methods=['GET'])
def get_history(symbol):
    """
    获取历史数据
    查询参数:
    - duration: 数据周期 (默认: '1 D')
    - bar_size: K线周期 (默认: '5 mins')
    - exchange: 交易所 (默认: 'SMART')
    - currency: 货币 (默认: 'USD')
    """
    if not gateway or not gateway.connected:
        return jsonify({
            'success': False,
            'message': '未连接到网关'
        }), 400
    
    duration = request.args.get('duration', '1 D')
    bar_size = request.args.get('bar_size', '5 mins')
    exchange = request.args.get('exchange', 'SMART')
    currency = request.args.get('currency', 'USD')
    
    logger.info(f"查询历史数据: {symbol}, {duration}, {bar_size}")
    data, error = gateway.get_historical_data(symbol.upper(), duration, bar_size, exchange, currency)
    
    # 如果有错误，返回错误信息
    if error:
        return jsonify({
            'success': False,
            'error_code': error['code'],
            'message': error['message']
        }), 400
    
    if data:
        return jsonify({
            'success': True,
            'count': len(data),
            'data': data
        })
    else:
        return jsonify({
            'success': False,
            'message': '无法获取历史数据'
        }), 404


@app.route('/api/info/<symbol>', methods=['GET'])
def get_stock_info(symbol):
    """
    获取股票详细信息
    """
    if not gateway or not gateway.connected:
        return jsonify({
            'success': False,
            'message': '未连接到网关'
        }), 400
    
    exchange = request.args.get('exchange', 'SMART')
    currency = request.args.get('currency', 'USD')
    
    logger.info(f"查询股票信息: {symbol}")
    data = gateway.get_stock_info(symbol.upper(), exchange, currency)
    
    if data:
        return jsonify({
            'success': True,
            'data': data
        })
    else:
        return jsonify({
            'success': False,
            'message': '无法获取股票信息'
        }), 404


@app.route('/api/fundamental/<symbol>', methods=['GET'])
def get_fundamental(symbol):
    """
    获取基本面数据
    查询参数:
    - report_type: 报告类型 (默认: ReportsFinSummary)
    """
    if not gateway or not gateway.connected:
        return jsonify({
            'success': False,
            'message': '未连接到网关'
        }), 400
    
    report_type = request.args.get('report_type', 'ReportsFinSummary')
    
    logger.info(f"查询基本面数据: {symbol}, {report_type}")
    data = gateway.get_fundamental_data(symbol.upper(), report_type)
    
    if data:
        return jsonify({
            'success': True,
            'data': data
        })
    else:
        return jsonify({
            'success': False,
            'message': '无法获取基本面数据'
        }), 404


def _check_ollama_available():
    """
    检查 Ollama 是否可用
    """
    try:
        import ollama
        import requests
        
        # 先尝试使用 requests 快速检查服务是否运行
        try:
            response = requests.get('http://localhost:11434/api/tags', timeout=2)
            if response.status_code == 200:
                # 服务运行中，尝试验证 ollama 模块是否可用
                try:
                    client = ollama.Client(host='http://localhost:11434')
                    # 尝试列出模型来验证服务是否可用
                    client.list()
                    return True
                except Exception:
                    # ollama 模块可能有问题，但服务在运行
                    return True
            return False
        except Exception:
            # 服务不可用
            return False
    except ImportError:
        # ollama 模块未安装
        return False


def _perform_ai_analysis(symbol, indicators, signals, duration, model='deepseek-v3.1:671b-cloud'):
    """
    执行AI分析的辅助函数
    """
    try:
        import ollama
        
        # 格式化基本面数据
        fundamental_data = indicators.get('fundamental_data', {})
        has_fundamental = (fundamental_data and 
                          isinstance(fundamental_data, dict) and 
                          'raw_xml' not in fundamental_data and
                          len(fundamental_data) > 0)
        
        if has_fundamental:
            # 格式化基本面数据为易读格式
            fundamental_sections = []
            
            # 基本信息
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

8. 风险评估:
   - 风险等级: {signals.get('risk', {}).get('level', 'unknown') if signals.get('risk') else 'unknown'}
   - 风险评分: {signals.get('risk', {}).get('score', 0) if signals.get('risk') else 0}/100

9. 系统建议:
   - 综合评分: {signals.get('score', 0)}/100
   - 建议操作: {signals.get('recommendation', 'unknown')}

【基本面分析】
{fundamental_text}

请提供以下分析:
1. 技术面分析: 当前市场状态（趋势、动能、波动）、关键技术信号解读
2. 基本面分析: 公司财务状况评估、估值水平分析、盈利能力评价
3. 综合分析: 结合技术面和基本面，给出买入/卖出/观望的具体建议
4. 风险提示: 技术风险和基本面风险的综合评估
5. 操作建议: 建议的止损止盈位、仓位管理建议（重点关注SAR止损位和VWAP价格偏离度）
6. 市场展望: 结合技术指标和基本面数据，分析未来可能的情境（牛市、熊市、震荡市中的不同策略）

请用中文回答，简洁专业，重点突出，将技术分析和基本面分析有机结合。"""
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

        # 调用Ollama（固定使用本机服务）
        try:
            client = ollama.Client(host='http://localhost:11434')
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
    if not gateway or not gateway.connected:
        return jsonify({
            'success': False,
            'message': '未连接到网关'
        }), 400
    
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
    
    # 获取股票信息并保存到数据库
    try:
        stock_info = gateway.get_stock_info(symbol_upper)
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
    hist_data, hist_error = gateway.get_historical_data(symbol_upper, duration, bar_size)
    
    # 计算技术指标
    indicators, ind_error = gateway.calculate_technical_indicators(symbol_upper, duration, bar_size)
    
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
    signals = gateway.generate_signals(indicators)
    
    # 格式化K线数据
    formatted_candles = []
    if hist_data:
        for bar in hist_data:
            date_str = bar.get('date', '')
            try:
                # 解析日期格式 "20250818" -> "2025-08-18"
                if len(date_str) == 8:
                    dt = datetime.strptime(date_str, '%Y%m%d')
                    time_str = dt.strftime('%Y-%m-%d')
                elif ' ' in date_str:
                    # 处理 "20250818 16:00:00" 格式
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
    
    # 构建返回数据
    result = {
        'success': True,
        'indicators': indicators,
        'signals': signals,
        'candles': formatted_candles
    }
    
    # 自动检测 Ollama 是否可用，如果可用则执行AI分析
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


@app.route('/api/ai-analyze/<symbol>', methods=['GET'])
def ai_analyze_stock(symbol):
    """
    AI技术分析 - 兼容接口，重定向到 /api/analyze
    查询参数:
    - duration: 数据周期 (默认: '3 M')
    - bar_size: K线周期 (默认: '1 day')
    - model: Ollama模型 (默认: 'deepseek-v3.1:671b-cloud')
    
    注意: 此接口已合并到 /api/analyze，后端会自动检测 Ollama 并执行AI分析
    """
    # 重定向到统一的 analyze 接口
    return analyze_stock(symbol)


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


@app.route('/api/indicator-info', methods=['GET'])
def get_indicator_info():
    """
    获取技术指标解释和参考范围
    查询参数:
    - indicator: 指标名称（可选），不提供则返回所有指标信息
    """
    indicator_name = request.args.get('indicator', '').lower()
    
    # 定义所有技术指标的解释和参考范围
    indicator_info = {
        'ma': {
            'name': '移动平均线 MA',
            'description': '移动平均线用于平滑价格波动，识别趋势方向',
            'calculation': 'MA = (P1 + P2 + ... + Pn) / n，其中P为收盘价，n为周期',
            'reference_range': {
                'ma5': 'MA5: 5日均线，用于观察短期趋势与支撑/压力',
                'ma10': 'MA10: 10日均线，用于观察中短期趋势与支撑/压力',
                'ma20': 'MA20: 20日均线，用于观察中期趋势与支撑/压力',
                'ma50': 'MA50: 50日均线，用于观察长期趋势与支撑/压力'
            },
            'interpretation': '价格上穿均线常视为偏强，下穿视为偏弱；多均线多头/空头排列用于判断趋势延续',
            'usage': '结合价格与均线位置判断趋势，多均线排列判断趋势强度'
        },
        'rsi': {
            'name': 'RSI 相对强弱指数',
            'description': 'RSI衡量价格动能，反映超买超卖状态',
            'calculation': 'RSI = 100 - (100 / (1 + RS))，其中RS = 平均上涨幅度 / 平均下跌幅度',
            'reference_range': {
                '超卖': '<30 超卖区域，可能反弹',
                '正常': '30-70 正常区间',
                '超买': '>70 超买区域，可能回调'
            },
            'interpretation': 'RSI衡量价格动能，极端值提示可能的反转风险，但需结合趋势',
            'usage': 'RSI<30关注反弹机会，RSI>70注意回调风险，结合趋势方向使用'
        },
        'bb': {
            'name': '布林带 Bollinger Bands',
            'description': '布林带通过标准差衡量价格波动范围',
            'calculation': '中轨=MA(20)，上轨=中轨+2*标准差，下轨=中轨-2*标准差',
            'reference_range': {
                '上轨': '价格接近上轨可能回调',
                '中轨': '价格在中轨附近震荡',
                '下轨': '价格接近下轨可能反弹',
                '带宽': '带宽扩大常伴随波动放大'
            },
            'interpretation': '价格接近上轨可能回调，接近下轨可能反弹；带宽扩大常伴随波动放大',
            'usage': '价格触及上下轨关注反转，带宽变化判断波动率'
        },
        'macd': {
            'name': 'MACD 指标',
            'description': 'MACD通过快慢均线差异判断趋势和动能，是趋势跟踪和动量指标',
            'calculation': 'MACD = EMA(12) - EMA(26)，Signal = EMA(9) of MACD，Histogram = MACD - Signal',
            'reference_range': {
                'MACD线': 'MACD = 短期均线(12日) - 长期均线(26日)。正值表示短期趋势强于长期（上涨动能），负值表示短期趋势弱于长期（下跌动能）。数值越大，趋势越强',
                'Signal线': 'Signal是MACD的9日移动平均，用于平滑MACD信号。Signal线在MACD上方表示趋势可能转弱，在下方表示趋势可能转强',
                'Histogram柱状图': 'Histogram = MACD - Signal。柱状图为正且增大表示上涨动能增强，为负且减小表示下跌动能减弱。柱状图由负转正（零轴上方）是买入信号，由正转负（零轴下方）是卖出信号',
                '金叉': 'MACD线从下方穿越Signal线（MACD > Signal），表示上涨动能增强，通常视为买入信号',
                '死叉': 'MACD线从上方穿越Signal线（MACD < Signal），表示上涨动能减弱，通常视为卖出信号',
                '零轴': 'MACD在零轴上方表示整体趋势向上，在零轴下方表示整体趋势向下。MACD穿越零轴是重要的趋势转换信号'
            },
            'interpretation': 'MACD数值本身没有固定范围，需要结合股票价格来理解。例如：MACD = 0.5 表示12日均线比26日均线高0.5美元。MACD > 0 且持续增大，表示上涨趋势加速；MACD < 0 且持续减小，表示下跌趋势加速。Histogram柱状图的高度表示动能强度，柱状图越高（绝对值越大），动能越强。当MACD和Signal都在零轴上方且MACD > Signal时，是最强的看涨信号；反之，都在零轴下方且MACD < Signal时，是最强的看跌信号',
            'usage': '1) 关注MACD与Signal的交叉点（金叉/死叉）作为买卖信号；2) 观察Histogram柱状图的变化趋势，柱状图增大表示动能增强；3) 结合MACD与零轴的位置判断整体趋势方向；4) 当MACD、Signal和Histogram三者同向时，信号更可靠；5) 在震荡市中MACD可能频繁交叉，需要结合其他指标确认'
        },
        'kdj': {
            'name': 'KDJ 指标',
            'description': 'KDJ通过最高价、最低价和收盘价计算超买超卖',
            'calculation': 'K = (RSV的3日移动平均)，D = (K的3日移动平均)，J = 3K - 2D',
            'reference_range': {
                '超卖': 'J<20 常见超卖，可能反弹',
                '正常': '20-80 正常区间',
                '超买': 'J>80 常见超买，可能回调',
                '金叉': 'K上穿D视为偏强信号',
                '死叉': 'K下穿D视为偏弱信号'
            },
            'interpretation': 'J<20常见超卖，J>80常见超买；K上穿D视为偏强信号',
            'usage': '关注J值极端区域，K与D交叉判断买卖信号'
        },
        'williams_r': {
            'name': 'Williams %R',
            'description': '威廉指标衡量收盘价在最高最低价区间的位置',
            'calculation': '%R = (最高价 - 收盘价) / (最高价 - 最低价) * -100',
            'reference_range': {
                '超卖': '< -80 超卖区域，可能反弹',
                '正常': '-80 到 -20 正常区间',
                '超买': '> -20 超买区域，可能回调'
            },
            'interpretation': '与RSI类似，用于刻画超买超卖区间，宜结合趋势判读',
            'usage': '关注极端值区域，结合趋势方向判断'
        },
        'cci': {
            'name': 'CCI 顺势指标',
            'description': 'CCI通过比较当前价格与平均价格的偏离程度，测量价格是否超买或超卖',
            'calculation': 'CCI = (典型价格 - 典型价格移动平均) / (0.015 * 平均绝对偏差)，其中典型价格 = (最高价 + 最低价 + 收盘价) / 3',
            'reference_range': {
                '超卖': 'CCI < -100 超卖区域，价格可能过低，注意反弹机会',
                '正常': '-100 到 +100 正常波动区间',
                '超买': 'CCI > +100 超买区域，价格可能过高，注意回调风险',
                '极端超卖': 'CCI < -200 极端超卖，强烈反弹信号',
                '极端超买': 'CCI > +200 极端超买，强烈回调信号'
            },
            'interpretation': 'CCI是一个波动指标，主要用于识别超买超卖状态。CCI > +100表示价格高于平均水平较多，可能超买；CCI < -100表示价格低于平均水平较多，可能超卖。CCI穿越零轴也是重要信号：从负转正是看涨信号，从正转负是看跌信号',
            'usage': '1) 关注CCI穿越±100线作为买卖信号；2) CCI > +100且继续上升表示强势，可持有；3) CCI < -100且继续下降表示弱势，需谨慎；4) 结合趋势使用，上升趋势中CCI回落至-100附近是买入机会；5) 注意背离：价格创新高但CCI未创新高是看跌信号'
        },
        'adx': {
            'name': 'ADX 平均趋向指标',
            'description': 'ADX用于衡量趋势的强度，不论趋势方向如何。配合+DI和-DI可以判断趋势方向',
            'calculation': 'ADX是DX的移动平均，其中DX = |(+DI) - (-DI)| / |(+DI) + (-DI)| * 100。+DI和-DI基于价格变动计算',
            'reference_range': {
                '无趋势': 'ADX < 20 趋势不明显，市场处于震荡状态，不适合趋势跟随策略',
                '弱趋势': 'ADX 20-25 趋势较弱，市场可能开始走出趋势',
                '中趋势': 'ADX 25-40 趋势明显，趋势跟随策略有效',
                '强趋势': 'ADX 40-60 趋势强劲，适合趋势跟随',
                '极强趋势': 'ADX > 60 趋势极强，但可能即将反转或调整',
                '+DI > -DI': '+DI在-DI上方表示上升趋势，多头主导',
                '-DI > +DI': '-DI在+DI上方表示下降趋势，空头主导'
            },
            'interpretation': 'ADX只衡量趋势强度，不表示趋势方向。ADX上升表示趋势增强，ADX下降表示趋势减弱。+DI和-DI用于判断趋势方向：+DI > -DI表示上升趋势，-DI > +DI表示下降趋势。当ADX > 25且+DI > -DI时，是强烈的看涨信号；当ADX > 25且-DI > +DI时，是强烈的看跌信号',
            'usage': '1) ADX < 20时避免趋势跟随策略，适合区间交易；2) ADX > 25时采用趋势跟随策略；3) 关注+DI和-DI的交叉：+DI上穿-DI是买入信号，-DI上穿+DI是卖出信号；4) ADX从低位上升表示趋势形成，可跟随趋势；5) ADX > 60后开始下降表示趋势可能衰竭，需谨慎'
        },
        'vwap': {
            'name': 'VWAP 成交量加权平均价',
            'description': 'VWAP是根据成交量加权的平均价格，反映机构投资者的平均成本，常用于判断价格是否合理',
            'calculation': 'VWAP = ∑(价格 × 成交量) / ∑成交量，通常基于当日或近期数据计算',
            'reference_range': {
                '低于VWAP': '价格 < VWAP 价格低于机构成本，可能是买入机会，但需确认下跌动能是否衰竭',
                '高于VWAP': '价格 > VWAP 价格高于机构成本，表示买盘强劲，但需注意回调风险',
                '接近VWAP': '价格接近VWAP 多空力量平衡，可能发生方向选择',
                '支撑作用': '上升趋势中VWAP常作为支撑位，回调至VWAP附近是买入机会',
                '压力作用': '下降趋势中VWAP常作为压力位，反弹至VWAP附近是卖出机会'
            },
            'interpretation': 'VWAP是机构投资者常用的参考指标。价格高于VWAP表示当前买家成本高于市场平均成本，买盘强劲；价格低于VWAP表示当前卖家成本低于市场平均成本，卖盘压力较大。VWAP在日内交易中特别重要，机构常以VWAP作为买卖基准',
            'usage': '1) 价格回落至VWAP附近且获得支撑时，可考虑买入；2) 价格突破VWAP且成交量放大，表示趋势可能持续；3) 日内交易中，价格低于VWAP时买入，高于VWAP时卖出；4) 结合趋势方向，上升趋势中VWAP是支撑，下降趋势中VWAP是压力；5) 关注价格与VWAP的偏离程度，过度偏离可能回归'
        },
        'sar': {
            'name': 'SAR 抛物线转向指标',
            'description': 'SAR是一种趋势跟随指标，通过在价格上下方显示点位来指示止损位和趋势方向',
            'calculation': 'SAR基于加速因子（AF）和极值点（EP）计算，趋势每持续一期AF就增加，使SAR逐渐靠近价格',
            'reference_range': {
                'SAR在下方': 'SAR < 价格 看涨信号，SAR点位可作为止损位，价格跌破SAR则趋势反转',
                'SAR在上方': 'SAR > 价格 看跌信号，SAR点位可作为止损位，价格突破SAR则趋势反转',
                '转向信号': 'SAR从下方转到上方是卖出信号，从SAR上方转到下方是买入信号',
                '距离远近': 'SAR距离价格较远表示趋势刚形成，较近表示趋势持续较久可能反转'
            },
            'interpretation': 'SAR是一种简单有效的趋势跟随工具。SAR在价格下方表示上升趋势，在价格上方表示下降趋势。SAR点位可以直接用作止损位。当价格突破SAR时，趋势发生反转，SAR也从一侧跳到另一侧。SAR在趋势市中非常有效，但在震荡市中可能产生较多假信号',
            'usage': '1) SAR在价格下方时持有多头，以SAR为止损位；2) SAR在价格上方时持有空头或空仓，以SAR为止损位；3) SAR翻转时进行反向操作：从SAR下方转到上方则平多开空，从SAR上方转到下方则平空开多；4) 结合ADX使用，当ADX > 25时SAR信号更可靠；5) 震荡市中谨慎使用，可能产生频繁的假信号'
        },
        'atr': {
            'name': 'ATR 平均真实波幅',
            'description': 'ATR衡量价格波动幅度，用于设置止损和仓位',
            'calculation': 'TR = max(最高价-最低价, |最高价-前收盘|, |最低价-前收盘|)，ATR = TR的N日移动平均',
            'reference_range': {
                '低波动': 'ATR较小，波动率低',
                '高波动': 'ATR较大，波动率高'
            },
            'interpretation': 'ATR反映近段真实波幅，用于设置止损与仓位',
            'usage': 'ATR大时设置更宽止损，ATR小时设置更紧止损'
        },
        'volatility': {
            'name': '波动率',
            'description': '波动率衡量价格变化的幅度',
            'calculation': '波动率 = 标准差 / 平均值 * 100',
            'reference_range': {
                '低': '≤2% 低波动',
                '中': '2-3% 中等波动',
                '高': '3-5% 高波动',
                '极高': '>5% 极高波动'
            },
            'interpretation': '波动大时风险与机会并存',
            'usage': '波动率高时注意风险控制，波动率低时可能酝酿突破'
        },
        'volume_ratio': {
            'name': '成交量比率',
            'description': '成交量比率反映当前成交量与平均成交量的关系',
            'calculation': '成交量比率 = 当前成交量 / 平均成交量',
            'reference_range': {
                '缩量': '<0.7 缩量，市场参与度低',
                '正常': '0.7-1.5 正常成交量',
                '放量': '>1.5 放量，市场参与度高'
            },
            'interpretation': '放量通常伴随价格突破，缩量可能预示趋势减弱',
            'usage': '结合价格变化判断量价关系，放量突破更可靠'
        },
        'obv': {
            'name': 'OBV 能量潮',
            'description': 'OBV通过成交量变化判断资金流向',
            'calculation': '价格上涨时OBV增加，价格下跌时OBV减少',
            'reference_range': {
                '上升': 'OBV上升，资金流入',
                '下降': 'OBV下降，资金流出',
                '量价齐升': 'OBV上升且价格上涨，强势信号',
                '量价背离': 'OBV与价格反向，可能反转'
            },
            'interpretation': 'OBV趋势与价格趋势一致时趋势更可靠，背离时注意反转',
            'usage': '关注OBV趋势方向，结合价格判断量价关系'
        },
        'trend_strength': {
            'name': '趋势强度',
            'description': '趋势强度衡量当前趋势的可靠性',
            'calculation': '基于多个技术指标的综合评估',
            'reference_range': {
                '弱': '0-25% 趋势较弱',
                '中': '25-50% 趋势中等',
                '强': '>50% 趋势较强'
            },
            'interpretation': '趋势强度高时趋势延续概率大，强度低时可能反转',
            'usage': '结合趋势方向，强度高时顺势操作，强度低时谨慎'
        },
        'pivot': {
            'name': '枢轴点 Pivot Point',
            'description': '枢轴点是基于前一交易日的高点、低点和收盘价计算的关键价位，用于预测当日的支撑位和压力位',
            'calculation': 'Pivot = (最高价 + 最低价 + 收盘价) / 3',
            'reference_range': {
                '枢轴点': '枢轴点是多空力量的平衡点，价格在枢轴点上方表示偏强，在下方表示偏弱',
                '支撑位': 'S1、S2、S3是支撑位，价格接近支撑位时可能获得支撑反弹',
                '压力位': 'R1、R2、R3是压力位，价格接近压力位时可能遇到阻力回落'
            },
            'interpretation': '枢轴点系统是日内交易常用的技术工具。价格在枢轴点上方表示多头占优，在下方表示空头占优。支撑位和压力位是重要的参考价位，价格接近这些位置时可能出现反弹或回调',
            'usage': '1) 观察价格与枢轴点的关系：在枢轴点上方看多，在下方看空；2) 在支撑位附近寻找买入机会；3) 在压力位附近注意卖出或减仓；4) 破位需要结合成交量确认'
        },
        'pivot_r1': {
            'name': '压力位R1',
            'description': 'R1是第一阻力位，基于枢轴点计算，是价格可能遇到阻力的第一个关键价位',
            'calculation': 'R1 = 2 × Pivot - 最低价',
            'reference_range': {
                '阻力': '价格接近R1时可能遇到阻力，需要关注是否能够突破',
                '突破': '价格突破R1后，下一个阻力位是R2'
            },
            'interpretation': 'R1是第一个压力位，价格接近R1时可能遇到阻力。如果价格能够突破R1，通常表示上涨动能较强，可能继续上涨至R2',
            'usage': '1) 价格接近R1时注意阻力；2) 突破R1是看涨信号；3) 在R1附近可以考虑减仓或设置止损'
        },
        'pivot_r2': {
            'name': '压力位R2',
            'description': 'R2是第二阻力位，是更强的阻力位，价格突破R1后可能在此遇到阻力',
            'calculation': 'R2 = Pivot + (最高价 - 最低价)',
            'reference_range': {
                '强阻力': 'R2是较强的阻力位，价格突破R2通常表示强势上涨',
                '回调': '价格在R2附近可能回调'
            },
            'interpretation': 'R2是第二个压力位，通常比R1更强。价格突破R2表示上涨动能很强，可能继续上涨至R3',
            'usage': '1) 价格接近R2时注意强阻力；2) 突破R2是强势看涨信号；3) 在R2附近可以考虑大幅减仓'
        },
        'pivot_r3': {
            'name': '压力位R3',
            'description': 'R3是第三阻力位，是最强的阻力位，价格很少能够突破R3',
            'calculation': 'R3 = 最高价 + 2 × (Pivot - 最低价)',
            'reference_range': {
                '极强阻力': 'R3是极强的阻力位，价格很少能够突破',
                '超买': '价格接近R3通常表示超买，可能大幅回调'
            },
            'interpretation': 'R3是最强的压力位，价格很少能够突破R3。价格接近R3通常表示超买，可能出现大幅回调',
            'usage': '1) 价格接近R3时注意极强阻力；2) 在R3附近应该考虑大幅减仓或全部卖出；3) 突破R3是极强势信号，但很少发生'
        },
        'pivot_s1': {
            'name': '支撑位S1',
            'description': 'S1是第一支撑位，基于枢轴点计算，是价格可能获得支撑的第一个关键价位',
            'calculation': 'S1 = 2 × Pivot - 最高价',
            'reference_range': {
                '支撑': '价格接近S1时可能获得支撑，需要关注是否能够守住',
                '跌破': '价格跌破S1后，下一个支撑位是S2'
            },
            'interpretation': 'S1是第一个支撑位，价格接近S1时可能获得支撑。如果价格跌破S1，通常表示下跌动能较强，可能继续下跌至S2',
            'usage': '1) 价格接近S1时注意支撑；2) 在S1附近可以考虑买入或加仓；3) 跌破S1是看跌信号'
        },
        'pivot_s2': {
            'name': '支撑位S2',
            'description': 'S2是第二支撑位，是更强的支撑位，价格跌破S1后可能在此获得支撑',
            'calculation': 'S2 = Pivot - (最高价 - 最低价)',
            'reference_range': {
                '强支撑': 'S2是较强的支撑位，价格在S2附近可能反弹',
                '继续下跌': '价格跌破S2通常表示弱势下跌'
            },
            'interpretation': 'S2是第二个支撑位，通常比S1更强。价格在S2附近可能获得支撑反弹，跌破S2表示下跌动能很强',
            'usage': '1) 价格接近S2时注意强支撑；2) 在S2附近可以考虑买入；3) 跌破S2是弱势看跌信号'
        },
        'pivot_s3': {
            'name': '支撑位S3',
            'description': 'S3是第三支撑位，是最强的支撑位，价格很少能够跌破S3',
            'calculation': 'S3 = 最低价 - 2 × (最高价 - Pivot)',
            'reference_range': {
                '极强支撑': 'S3是极强的支撑位，价格很少能够跌破',
                '超卖': '价格接近S3通常表示超卖，可能大幅反弹'
            },
            'interpretation': 'S3是最强的支撑位，价格很少能够跌破S3。价格接近S3通常表示超卖，可能出现大幅反弹',
            'usage': '1) 价格接近S3时注意极强支撑；2) 在S3附近应该考虑买入；3) 跌破S3是极弱势信号，但很少发生'
        },
        'resistance_20d_high': {
            'name': '20日高点 Resistance',
            'description': '20日高点是最近20个交易日的最高价，是重要的阻力位',
            'calculation': '20日高点 = 最近20个交易日的最高价',
            'reference_range': {
                '阻力': '价格接近20日高点时可能遇到阻力',
                '突破': '价格突破20日高点通常表示上涨趋势延续'
            },
            'interpretation': '20日高点是重要的阻力位。价格接近20日高点时可能遇到阻力，突破20日高点通常表示上涨趋势延续，是看涨信号',
            'usage': '1) 价格接近20日高点时注意阻力；2) 突破20日高点是看涨信号；3) 在20日高点附近可以考虑减仓'
        },
        'support_20d_low': {
            'name': '20日低点 Support',
            'description': '20日低点是最近20个交易日的最低价，是重要的支撑位',
            'calculation': '20日低点 = 最近20个交易日的最低价',
            'reference_range': {
                '支撑': '价格接近20日低点时可能获得支撑',
                '跌破': '价格跌破20日低点通常表示下跌趋势延续'
            },
            'interpretation': '20日低点是重要的支撑位。价格接近20日低点时可能获得支撑，跌破20日低点通常表示下跌趋势延续，是看跌信号',
            'usage': '1) 价格接近20日低点时注意支撑；2) 在20日低点附近可以考虑买入；3) 跌破20日低点是看跌信号'
        },
        'chanlun': {
            'name': '缠论 Chanlun Theory',
            'description': '缠论是一种基于价格走势结构的技术分析方法，通过分型、笔、线段、中枢等结构来识别趋势和买卖点',
            'calculation': '缠论通过识别K线图中的分型点，连接分型形成笔，组合笔形成线段，识别线段重叠形成中枢，最终判断走势类型',
            'reference_range': {
                '分型': '分型是缠论的基础结构。顶分型：中间K线的高点最高且低点也最高，表示可能的顶部；底分型：中间K线的低点最低且高点也最低，表示可能的底部。分型需要至少3根K线才能确认',
                '笔': '笔是连接相邻顶分型和底分型的线段。上涨笔：从底分型到顶分型；下跌笔：从顶分型到底分型。笔必须满足一定的价格幅度（通常至少0.5%）才有效。笔是趋势的基本单位',
                '线段': '线段是由至少3笔组成的更大结构。上涨线段：整体向上，由上涨笔和下跌笔交替组成；下跌线段：整体向下。线段代表更大级别的趋势',
                '中枢': '中枢是价格震荡的区间，由至少3个线段的重叠部分形成。中枢上沿：重叠区间的最高价；中枢下沿：重叠区间的最低价。中枢代表多空力量平衡的区域，是重要的支撑和压力位',
                '走势类型': '上涨：价格整体向上，高点不断抬高，低点也不断抬高；下跌：价格整体向下，高点不断降低，低点也不断降低；盘整：价格在一定区间内震荡，没有明确的趋势方向'
            },
            'interpretation': '缠论通过识别价格走势的结构来判断趋势和买卖点。分型是转折点，笔是基本趋势单位，线段是更大级别的趋势，中枢是重要的支撑压力区域。当价格突破中枢时，通常意味着趋势的延续或反转。上涨走势中，回调不破前低是买入机会；下跌走势中，反弹不破前高是卖出机会。盘整走势中，可以在中枢上下沿进行高抛低吸',
            'usage': '1) 识别分型：寻找顶分型和底分型，这些是潜在的转折点；2) 观察笔的方向：上涨笔和下跌笔的交替可以判断短期趋势；3) 分析线段：线段的方向代表更大级别的趋势，线段结束通常意味着趋势可能反转；4) 关注中枢：中枢是重要的支撑和压力位，价格在中枢内震荡，突破中枢可能意味着趋势延续；5) 判断走势类型：根据走势类型选择操作策略，上涨走势中寻找买入机会，下跌走势中注意风险，盘整走势中高抛低吸；6) 结合其他指标：缠论结构需要结合成交量、MACD等指标来确认信号的有效性'
        },
        'fractals': {
            'name': '缠论-分型 Fractals',
            'description': '分型是缠论的基础结构，用于识别价格的转折点',
            'calculation': '顶分型：中间K线的高点 > 前一根K线的高点 且 > 后一根K线的高点，同时中间K线的低点 > 前一根K线的低点 且 > 后一根K线的低点；底分型：中间K线的低点 < 前一根K线的低点 且 < 后一根K线的低点，同时中间K线的高点 < 前一根K线的高点 且 < 后一根K线的高点',
            'reference_range': {
                '顶分型': '顶分型出现在上涨趋势中，表示可能的顶部。如果后续价格跌破顶分型的最低点，通常确认顶部形成',
                '底分型': '底分型出现在下跌趋势中，表示可能的底部。如果后续价格突破底分型的最高点，通常确认底部形成',
                '确认': '分型需要至少3根K线才能确认，单独的分型可能失效，需要结合后续走势确认'
            },
            'interpretation': '分型是价格转折的潜在信号。顶分型表示上涨动能减弱，可能出现回调或反转；底分型表示下跌动能减弱，可能出现反弹或反转。但分型本身不是买卖信号，需要结合笔、线段等更大结构来判断',
            'usage': '1) 识别分型：在K线图中标记顶分型和底分型；2) 等待确认：分型形成后，等待后续K线确认是否有效；3) 结合笔：分型是笔的起点和终点，通过分型可以识别笔；4) 注意失效：如果后续价格突破分型的高低点，分型可能失效'
        },
        'strokes': {
            'name': '缠论-笔 Strokes',
            'description': '笔是连接相邻顶分型和底分型的线段，是缠论中趋势的基本单位',
            'calculation': '笔由两个相邻的分型连接而成。上涨笔：从底分型到顶分型；下跌笔：从顶分型到底分型。笔必须满足一定的价格幅度（通常至少0.5%）才有效',
            'reference_range': {
                '上涨笔': '上涨笔表示短期上涨趋势，从底分型开始到顶分型结束。上涨笔的结束通常意味着可能出现回调',
                '下跌笔': '下跌笔表示短期下跌趋势，从顶分型开始到底分型结束。下跌笔的结束通常意味着可能出现反弹',
                '笔的长度': '笔的长度（K线数量）和价格幅度可以判断趋势的强度。长笔表示趋势较强，短笔表示趋势较弱'
            },
            'interpretation': '笔是趋势的基本单位。上涨笔和下跌笔的交替可以判断短期趋势。连续的上涨笔表示上涨趋势，连续的下跌笔表示下跌趋势。笔的结束通常意味着趋势可能反转或进入盘整',
            'usage': '1) 识别笔：通过分型连接形成笔；2) 观察笔的方向：上涨笔和下跌笔的交替可以判断短期趋势；3) 判断笔的结束：当新的反向笔形成时，前一笔结束；4) 结合线段：笔是线段的组成部分，通过笔可以识别线段'
        },
        'segments': {
            'name': '缠论-线段 Segments',
            'description': '线段是由至少3笔组成的更大结构，代表更大级别的趋势',
            'calculation': '线段由至少3笔组成。上涨线段：整体向上，由上涨笔和下跌笔交替组成，但整体趋势向上；下跌线段：整体向下，由下跌笔和上涨笔交替组成，但整体趋势向下',
            'reference_range': {
                '上涨线段': '上涨线段表示更大级别的上涨趋势。上涨线段的结束通常意味着可能出现较大级别的回调或反转',
                '下跌线段': '下跌线段表示更大级别的下跌趋势。下跌线段的结束通常意味着可能出现较大级别的反弹或反转',
                '线段结束': '线段的结束通常需要新的反向线段形成来确认。线段结束是重要的趋势转换信号'
            },
            'interpretation': '线段代表更大级别的趋势。上涨线段表示中期或长期上涨趋势，下跌线段表示中期或长期下跌趋势。线段的结束通常意味着趋势可能反转，是重要的买卖信号',
            'usage': '1) 识别线段：通过笔的组合识别线段；2) 判断线段方向：上涨线段和下跌线段的方向代表更大级别的趋势；3) 关注线段结束：线段结束是重要的趋势转换信号，可以寻找买卖机会；4) 结合中枢：线段的重叠可以形成中枢'
        },
        'central_banks': {
            'name': '缠论-中枢 Central Banks',
            'description': '中枢是价格震荡的区间，由至少3个线段的重叠部分形成，是重要的支撑和压力位',
            'calculation': '中枢由至少3个线段的重叠部分形成。中枢上沿：重叠区间的最高价；中枢下沿：重叠区间的最低价；中枢中心：上沿和下沿的平均值；中枢宽度：上沿和下沿的差值',
            'reference_range': {
                '中枢上沿': '中枢上沿是重要的压力位。价格接近或触及上沿时，可能遇到阻力',
                '中枢下沿': '中枢下沿是重要的支撑位。价格接近或触及下沿时，可能获得支撑',
                '中枢中心': '中枢中心是多空力量的平衡点。价格在中枢中心附近震荡，表示多空力量平衡',
                '中枢宽度': '中枢宽度表示震荡的幅度。宽度越大，震荡幅度越大；宽度越小，震荡幅度越小',
                '突破中枢': '价格突破中枢上沿，通常意味着上涨趋势延续；价格跌破中枢下沿，通常意味着下跌趋势延续',
                '回踩中枢': '价格突破中枢后回踩中枢，如果在中枢上沿获得支撑，是买入机会；如果在中枢下沿遇到阻力，是卖出机会'
            },
            'interpretation': '中枢是重要的支撑和压力区域。价格在中枢内震荡，表示多空力量平衡。价格突破中枢，通常意味着趋势的延续或反转。中枢的上下沿是重要的支撑和压力位，可以在这些位置寻找买卖机会',
            'usage': '1) 识别中枢：通过线段的重叠识别中枢；2) 关注中枢上下沿：中枢上下沿是重要的支撑和压力位；3) 观察突破：价格突破中枢可能意味着趋势延续；4) 等待回踩：价格突破中枢后回踩，如果获得支撑或遇到阻力，是买卖机会；5) 结合走势类型：在盘整走势中，可以在中枢上下沿高抛低吸'
        },
        'trend_type': {
            'name': '缠论-走势类型 Trend Type',
            'description': '走势类型是根据缠论结构判断的整体趋势方向，包括上涨、下跌和盘整',
            'calculation': '走势类型通过分析线段的方向和中枢的位置来判断。上涨：高点不断抬高，低点也不断抬高；下跌：高点不断降低，低点也不断降低；盘整：价格在一定区间内震荡，没有明确的趋势方向',
            'reference_range': {
                '上涨': '上涨走势中，价格整体向上，高点不断抬高，低点也不断抬高。上涨走势中，回调不破前低是买入机会',
                '下跌': '下跌走势中，价格整体向下，高点不断降低，低点也不断降低。下跌走势中，反弹不破前高是卖出机会',
                '盘整': '盘整走势中，价格在一定区间内震荡，没有明确的趋势方向。盘整走势中，可以在区间上下沿高抛低吸',
                '转换': '走势类型的转换是重要的信号。从上涨转为下跌，或从下跌转为上涨，通常意味着趋势的反转'
            },
            'interpretation': '走势类型决定了操作策略。上涨走势中，应该寻找买入机会，回调是买入时机；下跌走势中，应该注意风险，反弹是卖出时机；盘整走势中，可以在区间上下沿高抛低吸。走势类型的转换是重要的趋势反转信号',
            'usage': '1) 判断走势类型：根据线段方向和中枢位置判断走势类型；2) 选择操作策略：根据走势类型选择相应的操作策略；3) 关注转换：走势类型的转换是重要的趋势反转信号；4) 结合其他指标：走势类型需要结合成交量、MACD等指标来确认'
        },
        'fundamental': {
            'name': '基本面数据 Fundamental Data',
            'description': '基本面数据反映公司的财务状况、经营业绩和市场估值，用于评估公司的内在价值和投资价值',
            'calculation': '基本面数据来自公司财务报表和市场数据，包括营收、利润、估值指标等',
            'reference_range': {
                '基本信息': '公司名称、交易所、员工数、流通股数等基本信息，用于了解公司的基本概况',
                '市值与价格': '市值反映公司的市场价值，当前价和52周区间反映价格波动范围',
                '财务指标': '营收、净利润、EBITDA等反映公司的盈利能力，利润率反映盈利质量',
                '每股数据': 'EPS、每股净资产、每股现金、每股股息等反映每股股东权益和收益',
                '估值指标': 'PE、PB、ROE等用于评估公司估值水平和盈利能力',
                '分析师预测': '目标价、共识评级、预测EPS等反映市场对公司未来的预期'
            },
            'interpretation': '基本面数据用于评估公司的内在价值。财务指标反映公司盈利能力，估值指标反映市场对公司价值的认可程度，分析师预测反映市场对公司未来的预期。基本面分析需要结合行业对比和历史趋势来判断',
            'usage': '1) 评估盈利能力：关注营收、净利润、利润率等指标；2) 评估估值水平：关注PE、PB等估值指标；3) 评估成长性：关注增长率、预测EPS等指标；4) 结合技术分析：基本面分析需要结合技术分析来做出投资决策'
        },
        'market_cap': {
            'name': '市值 Market Capitalization',
            'description': '市值是公司股票总价值，等于股价乘以流通股数',
            'calculation': '市值 = 当前股价 × 流通股数',
            'reference_range': {
                '大盘股': '市值 > $100亿，通常更稳定，流动性好',
                '中盘股': '市值 $10亿 - $100亿，成长性和稳定性平衡',
                '小盘股': '市值 < $10亿，成长潜力大但风险也高'
            },
            'interpretation': '市值反映公司的市场价值。大盘股通常更稳定，小盘股成长潜力大但风险高。市值需要结合行业和盈利能力来判断',
            'usage': '结合行业对比和盈利能力评估市值是否合理'
        },
        'pe': {
            'name': '市盈率 PE Ratio',
            'description': '市盈率是股价与每股收益的比率，反映投资者愿意为每元收益支付的价格',
            'calculation': 'PE = 股价 / 每股收益(EPS)',
            'reference_range': {
                '低估': 'PE < 15，可能被低估，但需结合成长性判断',
                '合理': 'PE 15-25，估值相对合理',
                '高估': 'PE > 25，可能被高估，需关注成长性是否支撑高估值'
            },
            'interpretation': 'PE反映市场对公司盈利能力的估值。低PE可能表示低估或增长缓慢，高PE可能表示高估或高成长预期。需要结合行业和成长性来判断',
            'usage': '1) 结合行业对比：不同行业的PE水平不同；2) 结合成长性：高成长公司可以支撑更高的PE；3) 结合历史PE：对比历史PE水平判断当前估值'
        },
        'pb': {
            'name': '市净率 PB Ratio',
            'description': '市净率是股价与每股净资产的比率，反映股价相对于账面价值的高低',
            'calculation': 'PB = 股价 / 每股净资产',
            'reference_range': {
                '低估': 'PB < 1，股价低于账面价值，可能被低估',
                '合理': 'PB 1-3，估值相对合理',
                '高估': 'PB > 3，股价远高于账面价值，需关注盈利能力是否支撑'
            },
            'interpretation': 'PB反映市场对公司净资产的估值。PB < 1可能表示低估，PB > 3可能表示高估。需要结合ROE和行业特点来判断',
            'usage': '1) 结合ROE：高ROE可以支撑更高的PB；2) 结合行业：不同行业的PB水平不同；3) 结合资产质量：关注资产的实际价值'
        },
        'roe': {
            'name': '净资产收益率 ROE',
            'description': 'ROE是净利润与净资产的比率，反映公司使用股东资金创造利润的能力',
            'calculation': 'ROE = 净利润 / 净资产 × 100%',
            'reference_range': {
                '优秀': 'ROE > 15%，盈利能力优秀',
                '良好': 'ROE 10-15%，盈利能力良好',
                '一般': 'ROE < 10%，盈利能力一般'
            },
            'interpretation': 'ROE反映公司的盈利能力。高ROE表示公司能够有效使用股东资金创造利润。需要结合行业和可持续性来判断',
            'usage': '1) 结合行业对比：不同行业的ROE水平不同；2) 关注可持续性：持续的高ROE更有价值；3) 结合PB：高ROE可以支撑更高的PB'
        },
        'eps': {
            'name': '每股收益 EPS',
            'description': 'EPS是公司净利润除以流通股数，反映每股股票的盈利能力',
            'calculation': 'EPS = 净利润 / 流通股数',
            'reference_range': {
                '增长': 'EPS持续增长表示盈利能力提升',
                '稳定': 'EPS稳定表示盈利能力稳定',
                '下降': 'EPS下降表示盈利能力下降'
            },
            'interpretation': 'EPS反映每股股票的盈利能力。EPS增长表示公司盈利能力提升，EPS下降表示盈利能力下降。需要结合营收增长来判断',
            'usage': '1) 关注趋势：EPS的增长趋势比绝对值更重要；2) 结合PE：EPS与PE结合可以判断估值；3) 对比预测：实际EPS与预测EPS对比判断业绩'
        },
        'revenue': {
            'name': '营收 Revenue',
            'description': '营收是公司销售产品或提供服务获得的收入，反映公司的经营规模',
            'calculation': '营收 = 销售产品或服务的总收入',
            'reference_range': {
                '增长': '营收持续增长表示业务扩张',
                '稳定': '营收稳定表示业务稳定',
                '下降': '营收下降表示业务收缩'
            },
            'interpretation': '营收反映公司的经营规模。营收增长表示业务扩张，营收下降表示业务收缩。需要结合利润率和行业对比来判断',
            'usage': '1) 关注趋势：营收的增长趋势很重要；2) 结合利润率：高营收不一定意味着高利润；3) 对比行业：营收增长需要对比行业平均水平'
        },
        'profit_margin': {
            'name': '利润率 Profit Margin',
            'description': '利润率是净利润与营收的比率，反映公司的盈利质量',
            'calculation': '利润率 = 净利润 / 营收 × 100%',
            'reference_range': {
                '高': '利润率 > 20%，盈利质量高',
                '中': '利润率 10-20%，盈利质量中等',
                '低': '利润率 < 10%，盈利质量低'
            },
            'interpretation': '利润率反映公司的盈利质量。高利润率表示公司能够将更多营收转化为利润。需要结合行业和成本结构来判断',
            'usage': '1) 结合行业：不同行业的利润率水平不同；2) 关注趋势：利润率的趋势很重要；3) 对比毛利率：利润率与毛利率对比判断成本控制'
        },
        'target_price': {
            'name': '目标价 Target Price',
            'description': '目标价是分析师预测的股票未来价格，反映市场对公司未来的预期',
            'calculation': '目标价基于财务模型和估值方法计算',
            'reference_range': {
                '上涨空间': '目标价 > 当前价，有上涨空间',
                '下跌风险': '目标价 < 当前价，有下跌风险'
            },
            'interpretation': '目标价反映市场对公司未来的预期。目标价高于当前价表示分析师看好，低于当前价表示分析师看空。需要结合多个分析师的目标价来判断',
            'usage': '1) 关注共识：多个分析师的目标价共识更有参考价值；2) 结合评级：目标价与评级结合判断；3) 关注更新：目标价会随业绩更新'
        }
    }
    
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
        'service': 'IB Trading Gateway API',
        'version': '1.0.0',
        'endpoints': {
            'health': 'GET /api/health',
            'connect': 'POST /api/connect',
            'disconnect': 'POST /api/disconnect',
            'account': 'GET /api/account',
            'positions': 'GET /api/positions',
            'orders': 'GET /api/orders',
            'executions': 'GET /api/executions',
            'submit_order': 'POST /api/order',
            'cancel_order': 'DELETE /api/order/<order_id>',
            'order_detail': 'GET /api/order/<order_id>',
            'quote': 'GET /api/quote/<symbol>',
            'history': 'GET /api/history/<symbol>',
            'stock_info': 'GET /api/info/<symbol>',
            'fundamental': 'GET /api/fundamental/<symbol>',
            'analyze': 'GET /api/analyze/<symbol>',
            'ai_analyze': 'GET /api/ai-analyze/<symbol>',
            'hot_stocks': 'GET /api/hot-stocks?limit=20',
            'indicator_info': 'GET /api/indicator-info?indicator=rsi'
        }
    })


def main():
    """
    启动API服务
    """
    global gateway
    import os
    import time as time_module
    
    # 初始化数据库
    init_database()
    
    port = 8080
    logger.info(f"API服务启动 http://0.0.0.0:{port}")
    
    # 自动连接到IB TWS（带重试）
    logger.info("自动连接到IB TWS...")
    
    # 在 Docker 环境中使用 host.docker.internal 连接宿主机
    ib_host = os.getenv('IB_GATEWAY_HOST', 'host.docker.internal')
    ib_port = int(os.getenv('IB_GATEWAY_PORT', '7496'))
    
    logger.info(f"尝试连接 IB Gateway: {ib_host}:{ib_port}")
    
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        logger.info(f"尝试连接 ({attempt}/{max_retries})...")
        gateway = IBGateway()
        
        if gateway.connect_gateway(host=ib_host, port=ib_port, client_id=attempt):
            # 等待数据加载
            time_module.sleep(2)
            if gateway.accounts:
                logger.info(f"✅ 已连接账户: {', '.join(gateway.accounts)}")
            break
        else:
            logger.warning(f"第 {attempt} 次连接失败")
            if attempt < max_retries:
                logger.info("等待5秒后重试...")
                time_module.sleep(5)
            else:
                logger.warning("⚠️  自动连接失败，可通过API手动连接")
                gateway = None
    
    # 启动Flask服务
    logger.info(f"🚀 Flask服务启动在 http://0.0.0.0:{port}")
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )


if __name__ == '__main__':
    main()
