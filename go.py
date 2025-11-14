
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
from datetime import datetime

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
    calculate_ichimoku_cloud, calculate_fibonacci_retracement,
    calculate_ml_predictions, calculate_chanlun_analysis, get_trend
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
        
        while time.time() - start_time < max_wait:
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
        
        # 获取数据
        with self.lock:
            data = self.historical_data.get(req_id, []).copy()
        
        if data_complete and data:
            logger.info(f"历史数据接收成功: {symbol}, 数据条数: {len(data)}")
        elif data:
            logger.warning(f"历史数据可能不完整: {symbol}, 数据条数: {len(data)}")
        else:
            logger.warning(f"历史数据接收失败: {symbol}")
        
        return data
        
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
        """
        # 获取历史数据
        hist_data = self.get_historical_data(symbol, duration, bar_size)
        
        if not hist_data or len(hist_data) < 20:
            logger.warning(f"数据不足，无法计算技术指标: {symbol}")
            return None
            
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

        # 14. Ichimoku云图指标
        ichimoku_data = calculate_ichimoku_cloud(highs, lows, closes)
        result.update(ichimoku_data)

        # 15. 斐波那契回撤位
        fibonacci_levels = calculate_fibonacci_retracement(highs, lows)
        result.update(fibonacci_levels)

        # 16. 机器学习预测模型
        ml_predictions = calculate_ml_predictions(closes, highs, lows, volumes)
        result.update(ml_predictions)

        # 17. 缠论分析
        chanlun_data = calculate_chanlun_analysis(closes, highs, lows, volumes)
        result.update(chanlun_data)

        # 18. IBKR基本面数据
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
            
        return result
        
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
        
        # 7. 机器学习预测风险
        if 'ml_trend' in indicators:
            ml_trend = indicators['ml_trend']
            ml_confidence = indicators.get('ml_confidence', 0)
            
            # 如果机器学习模型预测趋势与当前趋势相反，增加风险
            current_trend = indicators.get('trend_direction', 'neutral')
            if (ml_trend == 'up' and current_trend == 'down') or (ml_trend == 'down' and current_trend == 'up'):
                risk_score += 10
                risk_factors.append('ML模型预测与当前趋势相反')
            
            # 如果机器学习模型置信度低，增加风险
            if ml_confidence < 30:
                risk_score += 5
                risk_factors.append('ML模型置信度低')
        
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
    data = gateway.get_historical_data(symbol.upper(), duration, bar_size, exchange, currency)
    
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
   - Ichimoku云图:
     * 转换线: ${indicators.get('ichimoku_tenkan_sen', 0):.2f}
     * 基准线: ${indicators.get('ichimoku_kijun_sen', 0):.2f}
     * 先行跨度A: ${indicators.get('ichimoku_senkou_span_a', 0):.2f}
     * 先行跨度B: ${indicators.get('ichimoku_senkou_span_b', 0):.2f}
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
5. 操作建议: 建议的止损止盈位、仓位管理建议
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
   - Ichimoku云图:
     * 转换线: ${indicators.get('ichimoku_tenkan_sen', 0):.2f}
     * 基准线: ${indicators.get('ichimoku_kijun_sen', 0):.2f}
     * 先行跨度A: ${indicators.get('ichimoku_senkou_span_a', 0):.2f}
     * 先行跨度B: ${indicators.get('ichimoku_senkou_span_b', 0):.2f}
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
2. 关键技术信号解读（包括Ichimoku云图、斐波那契回撤位等现代技术指标）
3. 买入/卖出/观望的具体建议（基于纯技术分析）
4. 风险提示和注意事项
5. 建议的止损止盈位
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
    
    logger.info(f"技术分析: {symbol}, {duration}, {bar_size}")
    
    # 计算技术指标
    indicators = gateway.calculate_technical_indicators(symbol.upper(), duration, bar_size)
    
    if not indicators:
        return jsonify({
            'success': False,
            'message': '数据不足，无法计算技术指标'
        }), 404
    
    # 生成买卖信号
    signals = gateway.generate_signals(indicators)
    
    # 构建返回数据
    result = {
        'success': True,
        'indicators': indicators,
        'signals': signals
    }
    
    # 自动检测 Ollama 是否可用，如果可用则执行AI分析
    if _check_ollama_available():
        logger.info(f"检测到 Ollama 可用，开始AI分析...")
        try:
            ai_analysis = _perform_ai_analysis(symbol, indicators, signals, duration, model)
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
    获取热门股票代码列表
    查询参数:
    - market: 市场类型 (默认: 'US')，可选: 'US', 'HK', 'CN'
    - limit: 返回数量限制 (默认: 20)
    """
    market = request.args.get('market', 'US').upper()
    limit = int(request.args.get('limit', 20))
    
    # 定义热门股票列表
    hot_stocks = {
        'US': [
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'category': '科技'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'category': '科技'},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'category': '科技'},
            {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'category': '电商'},
            {'symbol': 'NVDA', 'name': 'NVIDIA Corporation', 'category': '半导体'},
            {'symbol': 'META', 'name': 'Meta Platforms Inc.', 'category': '科技'},
            {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'category': '汽车'},
            {'symbol': 'BRK.B', 'name': 'Berkshire Hathaway Inc.', 'category': '金融'},
            {'symbol': 'V', 'name': 'Visa Inc.', 'category': '金融'},
            {'symbol': 'JNJ', 'name': 'Johnson & Johnson', 'category': '医疗'},
            {'symbol': 'WMT', 'name': 'Walmart Inc.', 'category': '零售'},
            {'symbol': 'JPM', 'name': 'JPMorgan Chase & Co.', 'category': '金融'},
            {'symbol': 'MA', 'name': 'Mastercard Inc.', 'category': '金融'},
            {'symbol': 'PG', 'name': 'Procter & Gamble Co.', 'category': '消费品'},
            {'symbol': 'UNH', 'name': 'UnitedHealth Group Inc.', 'category': '医疗'},
            {'symbol': 'HD', 'name': 'The Home Depot Inc.', 'category': '零售'},
            {'symbol': 'DIS', 'name': 'The Walt Disney Company', 'category': '娱乐'},
            {'symbol': 'BAC', 'name': 'Bank of America Corp.', 'category': '金融'},
            {'symbol': 'ADBE', 'name': 'Adobe Inc.', 'category': '科技'},
            {'symbol': 'NFLX', 'name': 'Netflix Inc.', 'category': '娱乐'},
            {'symbol': 'CRM', 'name': 'Salesforce.com Inc.', 'category': '科技'},
            {'symbol': 'PYPL', 'name': 'PayPal Holdings Inc.', 'category': '金融'},
            {'symbol': 'INTC', 'name': 'Intel Corporation', 'category': '半导体'},
            {'symbol': 'CMCSA', 'name': 'Comcast Corporation', 'category': '媒体'},
            {'symbol': 'PFE', 'name': 'Pfizer Inc.', 'category': '医疗'},
            {'symbol': 'COST', 'name': 'Costco Wholesale Corporation', 'category': '零售'},
            {'symbol': 'TMO', 'name': 'Thermo Fisher Scientific Inc.', 'category': '医疗'},
            {'symbol': 'AVGO', 'name': 'Broadcom Inc.', 'category': '半导体'},
            {'symbol': 'CSCO', 'name': 'Cisco Systems Inc.', 'category': '科技'},
            {'symbol': 'ABBV', 'name': 'AbbVie Inc.', 'category': '医疗'},
        ],
        'HK': [
            {'symbol': '0700', 'name': '腾讯控股', 'category': '科技'},
            {'symbol': '0941', 'name': '中国移动', 'category': '电信'},
            {'symbol': '1299', 'name': '友邦保险', 'category': '保险'},
            {'symbol': '0388', 'name': '香港交易所', 'category': '金融'},
            {'symbol': '0005', 'name': '汇丰控股', 'category': '银行'},
            {'symbol': '2318', 'name': '中国平安', 'category': '保险'},
            {'symbol': '1398', 'name': '工商银行', 'category': '银行'},
            {'symbol': '3988', 'name': '中国银行', 'category': '银行'},
            {'symbol': '9988', 'name': '阿里巴巴-SW', 'category': '电商'},
            {'symbol': '3690', 'name': '美团-W', 'category': '科技'},
        ],
        'CN': [
            {'symbol': '000001', 'name': '平安银行', 'category': '银行'},
            {'symbol': '000002', 'name': '万科A', 'category': '地产'},
            {'symbol': '600000', 'name': '浦发银行', 'category': '银行'},
            {'symbol': '600036', 'name': '招商银行', 'category': '银行'},
            {'symbol': '600519', 'name': '贵州茅台', 'category': '消费'},
            {'symbol': '000858', 'name': '五粮液', 'category': '消费'},
            {'symbol': '002415', 'name': '海康威视', 'category': '科技'},
            {'symbol': '300059', 'name': '东方财富', 'category': '金融'},
            {'symbol': '002594', 'name': '比亚迪', 'category': '汽车'},
            {'symbol': '300750', 'name': '宁德时代', 'category': '新能源'},
        ],
    }
    
    stocks = hot_stocks.get(market, hot_stocks['US'])
    
    # 限制返回数量
    result = stocks[:limit] if limit > 0 else stocks
    
    return jsonify({
        'success': True,
        'market': market,
        'count': len(result),
        'stocks': result
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
            'hot_stocks': 'GET /api/hot-stocks?market=US&limit=20'
        }
    })


def main():
    """
    启动API服务
    """
    global gateway
    
    port = 8080
    logger.info(f"API服务启动 http://0.0.0.0:{port}")
    
    # 自动连接到IB TWS（带重试）
    logger.info("自动连接到IB TWS...")
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        logger.info(f"尝试连接 ({attempt}/{max_retries})...")
        gateway = IBGateway()
        
        if gateway.connect_gateway(host='127.0.0.1', port=7496, client_id=attempt):
            # 等待数据加载
            import time
            time.sleep(2)
            if gateway.accounts:
                logger.info(f"✅ 已连接账户: {', '.join(gateway.accounts)}")
            break
        else:
            logger.warning(f"第 {attempt} 次连接失败")
            if attempt < max_retries:
                logger.info("等待5秒后重试...")
                time.sleep(5)
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
