
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基于IBAPI的实盘交易网关 - RESTful API服务
提供账户信息、下单、撤单、持仓查询等HTTP接口
"""

import logging
import time
import threading
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order

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
        super().error(reqId, errorCode, errorString)
        
        # 忽略信息提示和已知的可忽略错误
        ignore_codes = [
            2104, 2106, 2158,  # 连接信息提示
            10148,  # 订单已在撤销中
            10147,  # 订单已撤销
            2119, 2120,  # 行情数据延迟提示
        ]
        
        if errorCode not in ignore_codes:
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
    
    def connect_gateway(self, host='127.0.0.1', port=4001, client_id=1):
        """
        连接到IB Gateway或TWS
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
                if req_id in self.fundamental_data and self.fundamental_data[req_id] is not None:
                    break
            time.sleep(0.2)
        
        # 获取数据
        with self.lock:
            data = self.fundamental_data.get(req_id)
            
        if data:
            logger.info(f"基本面数据接收成功: {symbol}")
            # 简单解析XML数据
            return self._parse_fundamental_data(data)
        else:
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
            
            # 提取财务摘要信息
            for elem in root.iter():
                if elem.text and elem.text.strip():
                    result[elem.tag] = elem.text.strip()
                    
            return result
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
        if len(closes) >= 5:
            result['ma5'] = float(np.mean(closes[-5:]))
        if len(closes) >= 10:
            result['ma10'] = float(np.mean(closes[-10:]))
        if len(closes) >= 20:
            result['ma20'] = float(np.mean(closes[-20:]))
        if len(closes) >= 50:
            result['ma50'] = float(np.mean(closes[-50:]))
            
        # 2. RSI (相对强弱指标)
        if len(closes) >= 15:
            period = 14
            deltas = np.diff(closes)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])
            
            if avg_loss != 0:
                rs = avg_gain / avg_loss
                result['rsi'] = float(100 - (100 / (1 + rs)))
            else:
                result['rsi'] = 100.0
                
        # 3. 布林带 (Bollinger Bands)
        if len(closes) >= 20:
            period = 20
            ma = np.mean(closes[-period:])
            std = np.std(closes[-period:])
            result['bb_upper'] = float(ma + 2 * std)
            result['bb_middle'] = float(ma)
            result['bb_lower'] = float(ma - 2 * std)
            
        # 4. MACD
        if len(closes) >= 26:
            # 计算EMA
            def ema(data, period):
                alpha = 2 / (period + 1)
                ema_vals = [data[0]]
                for price in data[1:]:
                    ema_vals.append(alpha * price + (1 - alpha) * ema_vals[-1])
                return ema_vals[-1]
            
            ema12 = ema(closes, 12)
            ema26 = ema(closes, 26)
            macd_line = ema12 - ema26
            
            # 计算信号线 (MACD的9日EMA)
            if len(closes) >= 35:
                macd_values = []
                for i in range(26, len(closes)):
                    e12 = ema(closes[:i+1], 12)
                    e26 = ema(closes[:i+1], 26)
                    macd_values.append(e12 - e26)
                
                if len(macd_values) >= 9:
                    signal_line = ema(np.array(macd_values), 9)
                    result['macd'] = float(macd_line)
                    result['macd_signal'] = float(signal_line)
                    result['macd_histogram'] = float(macd_line - signal_line)
                    
        # 5. 成交量分析
        if len(volumes) >= 20:
            result['avg_volume_20'] = float(np.mean(volumes[-20:]))
            result['current_volume'] = float(volumes[-1])
            avg_vol = np.mean(volumes[-20:])
            result['volume_ratio'] = float(volumes[-1] / avg_vol) if avg_vol > 0 else 0.0
            
        # 6. 价格变化
        if len(closes) >= 2:
            result['price_change'] = float(closes[-1] - closes[-2])
            result['price_change_pct'] = float(((closes[-1] - closes[-2]) / closes[-2] * 100)) if closes[-2] != 0 else 0.0
            
        # 7. 波动率
        if len(closes) >= 20:
            returns = np.diff(closes) / closes[:-1]
            result['volatility_20'] = float(np.std(returns[-20:]) * 100)
            
        # 8. 支撑位和压力位
        support_resistance = self._calculate_support_resistance(closes, highs, lows)
        result.update(support_resistance)
        
        # 9. KDJ指标（随机指标）
        if len(closes) >= 9:
            kdj = self._calculate_kdj(closes, highs, lows)
            result.update(kdj)
        
        # 10. ATR（平均真实波幅）
        if len(closes) >= 14:
            atr = self._calculate_atr(closes, highs, lows)
            result['atr'] = atr
            result['atr_percent'] = float((atr / closes[-1]) * 100)
        
        # 11. 威廉指标（Williams %R）
        if len(closes) >= 14:
            wr = self._calculate_williams_r(closes, highs, lows)
            result['williams_r'] = wr
        
        # 12. OBV（能量潮指标）
        if len(volumes) >= 20:
            obv = self._calculate_obv(closes, volumes)
            result['obv_current'] = float(obv[-1]) if len(obv) > 0 else 0.0
            result['obv_trend'] = self._get_trend(obv[-10:]) if len(obv) >= 10 else 'neutral'
        
        # 13. 趋势强度
        trend_info = self._analyze_trend_strength(closes, highs, lows)
        result.update(trend_info)
            
        return result
    
    def _calculate_support_resistance(self, closes, highs, lows):
        """
        计算支撑位和压力位
        使用多种方法：pivot点、历史高低点、聚类分析
        """
        import numpy as np
        
        result = {}
        current_price = float(closes[-1])
        
        # 方法1: Pivot Points (枢轴点)
        if len(closes) >= 2:
            high = float(highs[-2])
            low = float(lows[-2])
            close = float(closes[-2])
            
            pivot = (high + low + close) / 3
            r1 = 2 * pivot - low
            r2 = pivot + (high - low)
            r3 = high + 2 * (pivot - low)
            s1 = 2 * pivot - high
            s2 = pivot - (high - low)
            s3 = low - 2 * (high - pivot)
            
            result['pivot'] = float(pivot)
            result['pivot_r1'] = float(r1)
            result['pivot_r2'] = float(r2)
            result['pivot_r3'] = float(r3)
            result['pivot_s1'] = float(s1)
            result['pivot_s2'] = float(s2)
            result['pivot_s3'] = float(s3)
        
        # 方法2: 最近N日的高低点
        if len(closes) >= 20:
            # 最近20日高低点
            recent_high = float(np.max(highs[-20:]))
            recent_low = float(np.min(lows[-20:]))
            
            # 最近50日高低点（如果有足够数据）
            if len(closes) >= 50:
                high_50 = float(np.max(highs[-50:]))
                low_50 = float(np.min(lows[-50:]))
                result['resistance_50d_high'] = high_50
                result['support_50d_low'] = low_50
            
            result['resistance_20d_high'] = recent_high
            result['support_20d_low'] = recent_low
        
        # 方法3: 关键价格聚类（找出价格经常触及的区域）
        if len(closes) >= 30:
            # 合并所有价格点
            all_prices = np.concatenate([highs[-30:], lows[-30:], closes[-30:]])
            
            # 使用简单的价格分组来找关键位
            price_range = np.max(all_prices) - np.min(all_prices)
            if price_range > 0:
                # 将价格分成若干区间，找出触及次数最多的区间
                num_bins = 10
                hist, bin_edges = np.histogram(all_prices, bins=num_bins)
                
                # 找出触及次数最多的前几个区间
                top_indices = np.argsort(hist)[-3:]  # 前3个最常触及的区间
                key_levels = []
                
                for idx in top_indices:
                    if hist[idx] > 2:  # 至少触及3次
                        level = float((bin_edges[idx] + bin_edges[idx + 1]) / 2)
                        key_levels.append(level)
                
                # 根据当前价格分类为支撑或压力
                resistances = [lvl for lvl in key_levels if lvl > current_price]
                supports = [lvl for lvl in key_levels if lvl < current_price]
                
                if resistances:
                    resistances.sort()
                    for i, r in enumerate(resistances[:2], 1):  # 最多2个
                        result[f'key_resistance_{i}'] = float(r)
                
                if supports:
                    supports.sort(reverse=True)
                    for i, s in enumerate(supports[:2], 1):  # 最多2个
                        result[f'key_support_{i}'] = float(s)
        
        # 方法4: 整数关口（心理价位）
        # 找出最近的整数关口（如100, 150, 200等）
        if current_price > 10:
            # 大于10的股票，找5的倍数或10的倍数
            if current_price > 50:
                step = 10
            else:
                step = 5
                
            lower_round = float(np.floor(current_price / step) * step)
            upper_round = float(np.ceil(current_price / step) * step)
            
            if lower_round != current_price:
                result['psychological_support'] = lower_round
            if upper_round != current_price:
                result['psychological_resistance'] = upper_round
        
        return result
    
    def _calculate_kdj(self, closes, highs, lows, n=9):
        """
        计算KDJ指标（随机指标）
        """
        import numpy as np
        
        # 计算RSV（未成熟随机值）
        period = min(n, len(closes))
        lowest_low = float(np.min(lows[-period:]))
        highest_high = float(np.max(highs[-period:]))
        
        if highest_high == lowest_low:
            rsv = 50.0
        else:
            rsv = ((closes[-1] - lowest_low) / (highest_high - lowest_low)) * 100
        
        # 简化计算：使用最近的RSV
        # 完整版需要历史K、D值，这里使用简化版本
        k = float(rsv)
        d = float((2 * k + rsv) / 3)
        j = float(3 * k - 2 * d)
        
        return {
            'kdj_k': k,
            'kdj_d': d,
            'kdj_j': j
        }
    
    def _calculate_atr(self, closes, highs, lows, period=14):
        """
        计算ATR（平均真实波幅）
        """
        import numpy as np
        
        # 计算真实波幅TR
        tr_list = []
        for i in range(1, min(period + 1, len(closes))):
            high_low = highs[-i] - lows[-i]
            high_close = abs(highs[-i] - closes[-i-1])
            low_close = abs(lows[-i] - closes[-i-1])
            tr = max(high_low, high_close, low_close)
            tr_list.append(tr)
        
        atr = float(np.mean(tr_list))
        return atr
    
    def _calculate_williams_r(self, closes, highs, lows, period=14):
        """
        计算威廉指标（Williams %R）
        """
        import numpy as np
        
        p = min(period, len(closes))
        highest_high = float(np.max(highs[-p:]))
        lowest_low = float(np.min(lows[-p:]))
        
        if highest_high == lowest_low:
            return -50.0
        
        wr = ((highest_high - closes[-1]) / (highest_high - lowest_low)) * -100
        return float(wr)
    
    def _calculate_obv(self, closes, volumes):
        """
        计算OBV（能量潮指标）
        """
        import numpy as np
        
        obv = [0]
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                obv.append(obv[-1] + volumes[i])
            elif closes[i] < closes[i-1]:
                obv.append(obv[-1] - volumes[i])
            else:
                obv.append(obv[-1])
        
        return np.array(obv)
    
    def _get_trend(self, data):
        """
        判断数据趋势方向
        """
        import numpy as np
        
        if len(data) < 3:
            return 'neutral'
        
        # 简单线性回归判断趋势
        x = np.arange(len(data))
        slope = np.polyfit(x, data, 1)[0]
        
        if slope > np.std(data) * 0.1:
            return 'up'
        elif slope < -np.std(data) * 0.1:
            return 'down'
        else:
            return 'neutral'
    
    def _analyze_trend_strength(self, closes, highs, lows):
        """
        分析趋势强度
        """
        import numpy as np
        
        result = {}
        
        # 1. ADX简化版（趋势强度指标）
        if len(closes) >= 14:
            # 计算DM+ 和 DM-
            dm_plus = []
            dm_minus = []
            
            for i in range(1, min(14, len(closes))):
                high_diff = highs[-i] - highs[-i-1]
                low_diff = lows[-i-1] - lows[-i]
                
                if high_diff > low_diff and high_diff > 0:
                    dm_plus.append(high_diff)
                else:
                    dm_plus.append(0)
                
                if low_diff > high_diff and low_diff > 0:
                    dm_minus.append(low_diff)
                else:
                    dm_minus.append(0)
            
            avg_dm_plus = np.mean(dm_plus) if dm_plus else 0
            avg_dm_minus = np.mean(dm_minus) if dm_minus else 0
            
            # 简化的趋势强度
            total_dm = avg_dm_plus + avg_dm_minus
            if total_dm > 0:
                trend_strength = float((abs(avg_dm_plus - avg_dm_minus) / total_dm) * 100)
            else:
                trend_strength = 0.0
            
            result['trend_strength'] = trend_strength
            
            if avg_dm_plus > avg_dm_minus:
                result['trend_direction'] = 'up'
            elif avg_dm_minus > avg_dm_plus:
                result['trend_direction'] = 'down'
            else:
                result['trend_direction'] = 'neutral'
        
        # 2. 连续上涨/下跌天数
        consecutive_up = 0
        consecutive_down = 0
        
        for i in range(1, min(10, len(closes))):
            if closes[-i] > closes[-i-1]:
                consecutive_up += 1
                if consecutive_down > 0:
                    break
            elif closes[-i] < closes[-i-1]:
                consecutive_down += 1
                if consecutive_up > 0:
                    break
            else:
                break
        
        result['consecutive_up_days'] = int(consecutive_up)
        result['consecutive_down_days'] = int(consecutive_down)
        
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
    连接到IB Gateway
    请求参数:
    {
        "host": "127.0.0.1",
        "port": 4001,
        "client_id": 1
    }
    """
    global gateway
    
    data = request.get_json() or {}
    host = data.get('host', '127.0.0.1')
    port = data.get('port', 4001)
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


@app.route('/api/analyze/<symbol>', methods=['GET'])
def analyze_stock(symbol):
    """
    技术分析 - 计算技术指标并生成买卖信号
    查询参数:
    - duration: 数据周期 (默认: '1 M')
    - bar_size: K线周期 (默认: '1 day')
    """
    if not gateway or not gateway.connected:
        return jsonify({
            'success': False,
            'message': '未连接到网关'
        }), 400
    
    duration = request.args.get('duration', '1 M')
    bar_size = request.args.get('bar_size', '1 day')
    
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
    
    return jsonify({
        'success': True,
        'indicators': indicators,
        'signals': signals
    })


@app.route('/api/ai-analyze/<symbol>', methods=['GET'])
def ai_analyze_stock(symbol):
    """
    AI技术分析 - 使用Ollama分析技术指标并给出专业建议
    查询参数:
    - duration: 数据周期 (默认: '3 M')
    - bar_size: K线周期 (默认: '1 day')
    - model: Ollama模型 (默认: 'deepseek-v3.1:671b-cloud')
    """
    if not gateway or not gateway.connected:
        return jsonify({
            'success': False,
            'message': '未连接到网关'
        }), 400
    
    duration = request.args.get('duration', '3 M')
    bar_size = request.args.get('bar_size', '1 day')
    model = request.args.get('model', 'deepseek-v3.1:671b-cloud')
    
    logger.info(f"AI分析: {symbol}, {duration}, {bar_size}, model={model}")
    
    # 计算技术指标
    indicators = gateway.calculate_technical_indicators(symbol.upper(), duration, bar_size)
    
    if not indicators:
        return jsonify({
            'success': False,
            'message': '数据不足，无法计算技术指标'
        }), 404
    
    # 生成买卖信号
    signals = gateway.generate_signals(indicators)
    
    # 使用AI分析
    try:
        import ollama
        
        # 构建提示词
        prompt = f"""你是一位专业的股票技术分析师。请基于以下技术指标数据，给出详细的交易分析和建议。

股票代码: {symbol.upper()}
当前价格: ${indicators.get('current_price', 0):.2f}
数据周期: {duration} ({indicators.get('data_points', 0)}个数据点)

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

7. 风险评估:
   - 风险等级: {signals.get('risk', {}).get('level', 'unknown')}
   - 风险评分: {signals.get('risk', {}).get('score', 0)}/100

8. 系统建议:
   - 综合评分: {signals.get('score', 0)}/100
   - 建议操作: {signals.get('recommendation', 'unknown')}

请提供:
1. 当前市场状态分析（趋势、动能、波动）
2. 关键技术信号解读
3. 买入/卖出/观望的具体建议
4. 风险提示和注意事项
5. 建议的止损止盈位

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
        
        ai_analysis = response['message']['content']
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'indicators': indicators,
            'signals': signals,
            'ai_analysis': ai_analysis,
            'model': model
        })
        
    except Exception as ai_error:
        logger.error(f"AI分析失败: {ai_error}")
        # AI失败时仍返回技术指标
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'indicators': indicators,
            'signals': signals,
            'ai_analysis': f'AI分析不可用: {str(ai_error)}\n\n请确保Ollama已安装并运行: ollama serve',
            'model': model
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
            'ai_analyze': 'GET /api/ai-analyze/<symbol>'
        }
    })


def main():
    """
    启动API服务
    """
    global gateway
    
    port = 8080
    logger.info(f"API服务启动 http://0.0.0.0:{port}")
    
    # 自动连接到IB Gateway（带重试）
    logger.info("自动连接到IB Gateway...")
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        logger.info(f"尝试连接 ({attempt}/{max_retries})...")
        gateway = IBGateway()
        
        if gateway.connect_gateway(host='127.0.0.1', port=4001, client_id=attempt):
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
