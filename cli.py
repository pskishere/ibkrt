#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
IB Trading Gateway 交互式命令行客户端
通过命令行对接API后端服务
"""

# 标准库导入
import re
import shlex
import urllib.parse
from typing import Optional

# 第三方库导入
import requests

# 尝试启用命令行历史和编辑（macOS/Linux 可用）
try:
    import readline  # type: ignore
except ModuleNotFoundError:
    readline = None  # 在 Windows 上无此模块，忽略即可

# API配置
API_BASE_URL = "http://localhost:8080"


class TradingCLI:
    """
    交易命令行客户端
    """
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.connected = False
        
    def _request(self, method: str, endpoint: str, data: Optional[dict] = None, timeout: int = None):
        """
        发送HTTP请求
        """
        url = f"{self.base_url}{endpoint}"
        try:
            # 根据请求类型设置不同的超时时间
            if timeout is None:
                timeout = 30 if 'history' in endpoint or 'quote' in endpoint else 10
            
            if method == 'GET':
                response = requests.get(url, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, timeout=timeout)
            else:
                return None
                
            return response.json()
        except requests.exceptions.ConnectionError:
            print("❌ 无法连接到API服务，请确保服务已启动")
            return None
        except requests.exceptions.Timeout:
            print("❌ 请求超时，数据查询时间较长，请稍后重试")
            return None
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return None
            
    def connect(self, host: str = "127.0.0.1", port: int = 4001, client_id: int = 1):
        """
        连接到IB Gateway
        """
        print(f"连接中...")
        result = self._request('POST', '/api/connect', {
            'host': host,
            'port': port,
            'client_id': client_id
        })
        
        if result and result.get('success'):
            self.connected = True
            accounts = result.get('accounts', [])
            print(f"✅ 已连接")
            if accounts:
                print(f"账户: {', '.join(accounts)}")
        else:
            msg = result.get('message', '未知错误') if result else '连接失败'
            print(f"❌ {msg}")
            
    def disconnect(self):
        """
        断开连接
        """
        result = self._request('POST', '/api/disconnect')
        if result and result.get('success'):
            self.connected = False
            print(f"✅ {result.get('message')}")
        else:
            msg = result.get('message', '未知错误') if result else '断开失败'
            print(f"❌ {msg}")
            
    def account(self):
        """
        查看账户信息
        """
        result = self._request('GET', '/api/account')
        if result and result.get('success'):
            data = result.get('data', {})
            if data:
                for account, info in data.items():
                    print(f"\n📊 账户: {account}")
                    print("-" * 50)
                    for key, value in info.items():
                        print(f"  {key:15s}: {value}")
            else:
                print("⚠️  暂无账户数据")
        else:
            msg = result.get('message', '未知错误') if result else '查询失败'
            print(f"❌ {msg}")
            
    def positions(self):
        """
        查看持仓
        """
        result = self._request('GET', '/api/positions')
        if result and result.get('success'):
            data = result.get('data', [])
            if data:
                print(f"\n📦 当前持仓 (共{len(data)}个):")
                print("-" * 80)
                for pos in data:
                    symbol = pos.get('symbol', 'N/A')
                    position = pos.get('position', 0)
                    market_price = pos.get('marketPrice', 0)
                    market_value = pos.get('marketValue', 0)
                    avg_cost = pos.get('averageCost', 0)
                    pnl = pos.get('unrealizedPNL', 0)
                    
                    print(f"  {symbol:10s} | 数量: {position:8.0f} | "
                          f"价格: ${market_price:8.2f} | 市值: ${market_value:12.2f} | "
                          f"成本: ${avg_cost:8.2f} | 盈亏: ${pnl:10.2f}")
            else:
                print("⚠️  无持仓")
        else:
            msg = result.get('message', '未知错误') if result else '查询失败'
            print(f"❌ {msg}")
            
    def orders(self):
        """
        查看订单
        """
        result = self._request('GET', '/api/orders')
        if result and result.get('success'):
            data = result.get('data', [])
            if data:
                print(f"\n📝 订单列表 (共{len(data)}个):")
                print("-" * 80)
                for order in data:
                    order_id = order.get('orderId', 'N/A')
                    symbol = order.get('symbol', 'N/A')
                    action = order.get('action', 'N/A')
                    quantity = order.get('totalQuantity', 0)
                    order_type = order.get('orderType', 'N/A')
                    status = order.get('status', 'N/A')
                    filled = order.get('filled', 0)
                    
                    print(f"  #{order_id:5} | {symbol:10s} | {action:4s} {quantity:6.0f} | "
                          f"类型: {order_type:5s} | 状态: {status:12s} | 已成交: {filled:.0f}")
            else:
                print("⚠️  无订单")
        else:
            msg = result.get('message', '未知错误') if result else '查询失败'
            print(f"❌ {msg}")
            
    def buy(self, symbol: str, quantity: float, price: Optional[float] = None):
        """
        买入
        """
        order_data = {
            'symbol': symbol.upper(),
            'action': 'BUY',
            'quantity': quantity,
            'order_type': 'LMT' if price else 'MKT'
        }
        
        if price:
            order_data['limit_price'] = price
            
        result = self._request('POST', '/api/order', order_data)
        if result and result.get('success'):
            order_id = result.get('order_id')
            order_type = "限价" if price else "市价"
            price_str = f" @${price}" if price else ""
            print(f"✅ 买单已提交: #{order_id} - {symbol.upper()} x{quantity}{price_str} ({order_type})")
            
            # 等待并查看订单状态
            import time
            time.sleep(1.5)
            order_detail = self._request('GET', f'/api/order/{order_id}')
            if order_detail and order_detail.get('success'):
                data = order_detail['data']
                status = data.get('status', 'Unknown')
                filled = data.get('filled', 0)
                remaining = data.get('remaining', quantity)
                print(f"   状态: {status} | 已成交: {filled} | 剩余: {remaining}")
            else:
                print(f"   ⚠️  订单可能被拒绝，请查看后端日志或使用 'orders' 命令")
        else:
            msg = result.get('message', '未知错误') if result else '提交失败'
            print(f"❌ {msg}")
            
    def sell(self, symbol: str, quantity: float, price: Optional[float] = None):
        """
        卖出
        """
        order_data = {
            'symbol': symbol.upper(),
            'action': 'SELL',
            'quantity': quantity,
            'order_type': 'LMT' if price else 'MKT'
        }
        
        if price:
            order_data['limit_price'] = price
            
        result = self._request('POST', '/api/order', order_data)
        if result and result.get('success'):
            order_id = result.get('order_id')
            order_type = "限价" if price else "市价"
            price_str = f" @${price}" if price else ""
            print(f"✅ 卖单已提交: #{order_id} - {symbol.upper()} x{quantity}{price_str} ({order_type})")
            
            # 等待并查看订单状态
            import time
            time.sleep(1.5)
            order_detail = self._request('GET', f'/api/order/{order_id}')
            if order_detail and order_detail.get('success'):
                data = order_detail['data']
                status = data.get('status', 'Unknown')
                filled = data.get('filled', 0)
                remaining = data.get('remaining', quantity)
                print(f"   状态: {status} | 已成交: {filled} | 剩余: {remaining}")
            else:
                print(f"   ⚠️  订单可能被拒绝，请查看后端日志或使用 'orders' 命令")
        else:
            msg = result.get('message', '未知错误') if result else '提交失败'
            print(f"❌ {msg}")
            
    def cancel(self, order_id: int):
        """
        撤销订单
        """
        result = self._request('DELETE', f'/api/order/{order_id}')
        if result and result.get('success'):
            print(f"✅ {result.get('message')}")
            
            # 等待并查看订单状态
            import time
            time.sleep(0.5)
            order_detail = self._request('GET', f'/api/order/{order_id}')
            if order_detail and order_detail.get('success'):
                status = order_detail['data'].get('status', 'Unknown')
                print(f"   当前状态: {status}")
        else:
            msg = result.get('message', '未知错误') if result else '撤销失败'
            print(f"⚠️  {msg}")
            
    def health(self):
        """
        检查服务状态
        """
        result = self._request('GET', '/api/health')
        if result:
            status = result.get('status', 'unknown')
            connected = result.get('connected', False)
            timestamp = result.get('timestamp', 'N/A')
            
            status_icon = "✅" if status == 'ok' else "❌"
            connect_icon = "🟢" if connected else "🔴"
            
            print(f"{status_icon} 服务状态: {status}")
            print(f"{connect_icon} 网关连接: {'已连接' if connected else '未连接'}")
            print(f"⏰ 时间: {timestamp}")
        else:
            print("❌ 服务未响应")
            
    def quote(self, symbol: str):
        """
        查询实时报价
        """
        print(f"查询 {symbol.upper()}...")
        result = self._request('GET', f'/api/quote/{symbol.upper()}')
        if result and result.get('success'):
            data = result.get('data', {})
            symbol_name = data.get('symbol', symbol.upper())
            
            print(f"\n📈 {symbol_name} 实时报价:")
            print("-" * 60)
            
            # 显示价格信息
            if 'last' in data:
                print(f"  最新价: ${data['last']:.2f}")
            if 'bid' in data and 'ask' in data:
                spread = data['ask'] - data['bid']
                print(f"  买价:   ${data['bid']:.2f}  x  {data.get('bid_size', 'N/A')}")
                print(f"  卖价:   ${data['ask']:.2f}  x  {data.get('ask_size', 'N/A')}")
                print(f"  价差:   ${spread:.2f}")
            if 'high' in data:
                print(f"  最高:   ${data['high']:.2f}")
            if 'low' in data:
                print(f"  最低:   ${data['low']:.2f}")
            if 'close' in data:
                print(f"  收盘:   ${data['close']:.2f}")
            if 'volume' in data:
                print(f"  成交量: {data['volume']:,}")
                
            # 计算涨跌幅
            if 'last' in data and 'close' in data and data['close'] > 0:
                change = data['last'] - data['close']
                change_pct = (change / data['close']) * 100
                change_icon = "📈" if change >= 0 else "📉"
                print(f"  {change_icon} 涨跌: ${change:+.2f} ({change_pct:+.2f}%)")
        else:
            msg = result.get('message', '未知错误') if result else '查询失败'
            print(f"❌ {msg}")
            
    def info(self, symbol: str):
        """
        查询股票详细信息
        """
        print(f"查询 {symbol.upper()}...")
        result = self._request('GET', f'/api/info/{symbol.upper()}')
        
        if result and result.get('success'):
            data = result.get('data', {})
            
            print(f"\n📋 {data.get('symbol', symbol.upper())} 详细信息:")
            print("-" * 70)
            
            if 'longName' in data:
                print(f"  公司全称: {data['longName']}")
            if 'industry' in data:
                print(f"  行业: {data['industry']}")
            if 'category' in data:
                print(f"  类别: {data['category']}")
            if 'marketName' in data:
                print(f"  市场: {data['marketName']}")
            if 'exchange' in data:
                print(f"  交易所: {data['exchange']}")
            if 'currency' in data:
                print(f"  货币: {data['currency']}")
            if 'tradingClass' in data:
                print(f"  交易类别: {data['tradingClass']}")
            if 'minTick' in data:
                print(f"  最小变动: {data['minTick']}")
            if 'timeZoneId' in data:
                print(f"  时区: {data['timeZoneId']}")
            if 'tradingHours' in data and data['tradingHours']:
                print(f"  交易时间: {data['tradingHours'][:50]}...")
        else:
            msg = result.get('message', '未知错误') if result else '查询失败'
            print(f"❌ {msg}")
    
    def ai_analyze(self, symbol: str, duration: str = '3 M', bar_size: str = '1 day', model: str = 'deepseek-v3.1:671b-cloud'):
        """
        AI技术分析 - 使用Ollama AI分析技术指标
        """
        print(f"🤖 AI分析 {symbol.upper()}...")
        print(f"使用模型: {model}")
        print(f"请稍候，AI正在分析中...")
        
        # 标准化参数
        duration = re.sub(r'(\d+)([SDWMY])', r'\1 \2', duration, flags=re.IGNORECASE)
        bar_size = bar_size.replace('min', ' min').replace('hour', ' hour').replace('day', ' day')
        bar_size = re.sub(r'\s+', ' ', bar_size).strip()
        if 'min' in bar_size and not bar_size.endswith('mins'):
            bar_size = bar_size.replace('min', 'mins')
        
        params = f"?duration={urllib.parse.quote(duration)}&bar_size={urllib.parse.quote(bar_size)}&model={urllib.parse.quote(model)}"
        result = self._request('GET', f'/api/ai-analyze/{symbol.upper()}{params}', timeout=60)  # AI分析需要更长时间
        
        if result and result.get('success'):
            ai_analysis = result.get('ai_analysis', '')
            
            print(f"\n{'='*70}")
            print(f"🤖 {symbol.upper()} AI技术分析报告")
            print(f"{'='*70}")
            print(f"模型: {result.get('model', 'unknown')}")
            print(f"{'='*70}\n")
            
            # 显示AI分析
            print(ai_analysis)
            print(f"\n{'='*70}")
            
            # 显示技术指标摘要
            indicators = result.get('indicators', {})
            signals = result.get('signals', {})
            
            if indicators:
                print(f"\n📊 技术指标摘要:")
                print(f"   当前价: ${indicators.get('current_price', 0):.2f}")
                print(f"   RSI: {indicators.get('rsi', 0):.1f}")
                print(f"   MACD: {indicators.get('macd', 0):.3f}")
                print(f"   趋势: {indicators.get('trend_direction', 'unknown')}")
                
            if signals:
                score = signals.get('score', 0)
                recommendation = signals.get('recommendation', 'unknown')
                
                # 获取风险信息
                risk_data = signals.get('risk', {})
                if isinstance(risk_data, dict):
                    risk_level = risk_data.get('level', 'unknown')
                    risk_score = risk_data.get('score', 0)
                else:
                    risk_level = 'unknown'
                    risk_score = 0
                
                # 风险等级中文映射
                risk_map = {
                    'very_low': '✅ 很低风险',
                    'low': '🟢 低风险',
                    'medium': '🟡 中等风险',
                    'high': '🔴 高风险',
                    'very_high': '🔴 极高风险',
                    'unknown': '⚪ 未知'
                }
                risk_display = risk_map.get(risk_level, f'⚪ {risk_level}')
                
                print(f"\n💡 系统评分:")
                print(f"   综合评分: {score}/100")
                print(f"   建议操作: {recommendation}")
                print(f"   风险等级: {risk_display}")
                if risk_score > 0:
                    print(f"   风险评分: {risk_score}/100")
                
        else:
            msg = result.get('message', '未知错误') if result else '分析失败'
            print(f"❌ {msg}")
    
    def analyze(self, symbol: str, duration: str = '3 M', bar_size: str = '1 day', model: str = 'deepseek-v3.1:671b-cloud'):
        """
        技术分析 - 生成买卖信号（默认3个月日K线）
        后端会自动检测 Ollama 是否可用，如果可用则自动执行AI分析
        
        参数:
        - symbol: 股票代码
        - duration: 数据周期 (默认: '3 M')
        - bar_size: K线周期 (默认: '1 day')
        - model: AI模型名称 (默认: 'deepseek-v3.1:671b-cloud')，仅在Ollama可用时使用
        """
        print(f"分析 {symbol.upper()}...")
        
        # 标准化参数
        duration = re.sub(r'(\d+)([SDWMY])', r'\1 \2', duration, flags=re.IGNORECASE)
        bar_size = bar_size.replace('min', ' min').replace('hour', ' hour').replace('day', ' day')
        bar_size = re.sub(r'\s+', ' ', bar_size).strip()
        if 'min' in bar_size and not bar_size.endswith('mins'):
            bar_size = bar_size.replace('min', 'mins')
        
        params = f"?duration={urllib.parse.quote(duration)}&bar_size={urllib.parse.quote(bar_size)}&model={urllib.parse.quote(model)}"
        
        result = self._request('GET', f'/api/analyze/{symbol.upper()}{params}', timeout=60)  # AI分析可能需要更长时间
        
        if result and result.get('success'):
            indicators = result.get('indicators', {})
            signals = result.get('signals', {})
            
            print(f"\n📊 {symbol.upper()} 技术分析:")
            print("=" * 70)
            
            # 当前价格和变化
            current = indicators.get('current_price', 0)
            change_pct = indicators.get('price_change_pct', 0)
            data_points = indicators.get('data_points', 0)
            icon = "📈" if change_pct >= 0 else "📉"
            
            # 数据充足性说明
            if data_points >= 50:
                data_status = f"{data_points}根K线 ✅充足"
            elif data_points >= 26:
                data_status = f"{data_points}根K线 ⚠️中等(MA50不可用)"
            elif data_points >= 20:
                data_status = f"{data_points}根K线 ⚠️偏少(仅短中期指标)"
            else:
                data_status = f"{data_points}根K线 ❌不足(仅短期指标)"
            
            print(f"价格: ${current:.2f}  {icon} {change_pct:+.2f}%")
            print(f"数据: {data_status}")
            
            # 数据不足时给出建议
            if data_points < 50:
                if data_points < 20:
                    print(f"💡 建议: an {symbol.upper()} 2M (获取更多数据)")
                elif data_points < 26:
                    print(f"💡 建议: an {symbol.upper()} 3M (获取MACD数据)")
                else:
                    print(f"💡 建议: an {symbol.upper()} 6M (获取MA50数据)")
            
            # 移动平均线
            if any(k in indicators for k in ['ma5', 'ma10', 'ma20', 'ma50']):
                print(f"\n📉 移动平均线 (需要{data_points}天数据):")
                for period in [5, 10, 20, 50]:
                    key = f'ma{period}'
                    if key in indicators:
                        ma = indicators[key]
                        diff = ((current - ma) / ma * 100) if ma > 0 else 0
                        print(f"   MA{period}: ${ma:.2f} ({diff:+.1f}%)", end="")
                        if period == 5:
                            print(" [短期,需5天]")
                        elif period == 10:
                            print(" [需10天]")
                        elif period == 20:
                            print(" [中期,需20天]")
                        elif period == 50:
                            print(" [长期,需50天]")
                        else:
                            print()
                    elif period == 50 and data_points < 50:
                        print(f"   MA50: ❌ 数据不足(需50天,当前{data_points}天)")

            # 指数移动平均线 (EMA)
            if any(k in indicators for k in ['ema12', 'ema26', 'ema50']):
                print(f"   EMA: ", end="")
                ema_parts = []
                for period in [12, 26, 50]:
                    key = f'ema{period}'
                    if key in indicators:
                        ema_parts.append(f"EMA{period}=${indicators[key]:.2f}")
                print(" | ".join(ema_parts))
            
            # RSI
            if 'rsi' in indicators:
                rsi = indicators['rsi']
                if rsi < 30:
                    status = "🟢 超卖(可能反弹)"
                elif rsi > 70:
                    status = "🔴 超买(可能回调)"
                else:
                    status = "⚪ 中性"
                print(f"📊 RSI(14日): {rsi:.1f} {status} [需14天数据]")
            
            # 布林带
            if all(k in indicators for k in ['bb_upper', 'bb_middle', 'bb_lower']):
                upper = indicators['bb_upper']
                lower = indicators['bb_lower']
                middle = indicators['bb_middle']
                
                position = ""
                if current >= upper * 0.99:
                    position = " 📍接近上轨(可能回调)"
                elif current <= lower * 1.01:
                    position = " 📍接近下轨(可能反弹)"
                
                print(f"📏 布林带(20日):{position} [需20天数据]")
                print(f"   上轨: ${upper:.2f} | 中轨: ${middle:.2f} | 下轨: ${lower:.2f}")
            
            # MACD
            if 'macd' in indicators:
                macd_val = indicators['macd']
                signal = indicators.get('macd_signal', 0)
                hist = indicators.get('macd_histogram', 0)
                
                if macd_val > signal:
                    trend = "金叉(看涨)"
                else:
                    trend = "死叉(看跌)"
                
                print(f"📈 MACD: {macd_val:.3f} | 信号: {signal:.3f} | {trend} [需26天数据]")
            
            # 成交量
            if 'volume_ratio' in indicators:
                ratio = indicators['volume_ratio']
                if ratio > 1.5:
                    desc = "放量"
                elif ratio < 0.7:
                    desc = "缩量"
                else:
                    desc = "正常"
                print(f"📊 成交量: {ratio:.2f}x ({desc})")
            
            # 波动率和ATR
            if 'volatility_20' in indicators or 'atr' in indicators:
                parts = []
                if 'volatility_20' in indicators:
                    vol = indicators['volatility_20']
                    if vol > 5:
                        vol_desc = "极高"
                    elif vol > 3:
                        vol_desc = "高"
                    elif vol > 2:
                        vol_desc = "中"
                    else:
                        vol_desc = "低"
                    parts.append(f"波动率: {vol:.2f}%({vol_desc})")
                
                if 'atr' in indicators:
                    atr = indicators['atr']
                    atr_pct = indicators.get('atr_percent', 0)
                    parts.append(f"ATR: ${atr:.2f}({atr_pct:.1f}%)")
                
                if parts:
                    print(f"⚡ {' | '.join(parts)}")
            
            # KDJ指标
            if all(k in indicators for k in ['kdj_k', 'kdj_d', 'kdj_j']):
                k = indicators['kdj_k']
                d = indicators['kdj_d']
                j = indicators['kdj_j']
                
                if j < 20:
                    status = "🟢超卖"
                elif j > 80:
                    status = "🔴超买"
                else:
                    status = "⚪中性"
                
                trend = "多头" if k > d else "空头"
                print(f"📊 KDJ(9日): K={k:.1f} D={d:.1f} J={j:.1f} | {status} {trend} [需9天数据]")
            
            # 威廉指标
            if 'williams_r' in indicators:
                wr = indicators['williams_r']
                if wr < -80:
                    wr_status = "🟢超卖"
                elif wr > -20:
                    wr_status = "🔴超买"
                else:
                    wr_status = "⚪中性"
                print(f"📉 威廉%R: {wr:.1f} {wr_status}")
            
            # CCI顺势指标（增强显示）
            if 'cci' in indicators:
                cci = indicators['cci']
                cci_signal = indicators.get('cci_signal', 'neutral')
                if cci_signal == 'overbought':
                    if cci > 200:
                        cci_status = "🔴极度超买(>200)"
                    else:
                        cci_status = "🔴超买(>100)"
                elif cci_signal == 'oversold':
                    if cci < -200:
                        cci_status = "🟢极度超卖(<-200)"
                    else:
                        cci_status = "🟢超卖(<-100)"
                else:
                    cci_status = "⚪中性"
                print(f"📊 CCI(14日): {cci:.1f} {cci_status} [需14天数据]")
            
            # ADX趋势强度指标（增强显示）
            if 'adx' in indicators:
                adx = indicators['adx']
                plus_di = indicators.get('plus_di', 0)
                minus_di = indicators.get('minus_di', 0)
                
                if adx > 40:
                    adx_status = "💪极强趋势"
                elif adx > 25:
                    adx_status = "📈强趋势"
                elif adx > 20:
                    adx_status = "📈中等趋势"
                else:
                    adx_status = "📊弱趋势/震荡"
                
                di_trend = "🟢多头" if plus_di > minus_di else "🔴空头"
                di_diff = abs(plus_di - minus_di)
                print(f"🎯 ADX(14日): {adx:.1f} {adx_status} | +DI={plus_di:.1f} -DI={minus_di:.1f} ({di_diff:.1f}) {di_trend} [需28天数据]")
            
            # VWAP成交量加权平均价（增强显示）
            if 'vwap' in indicators:
                vwap = indicators['vwap']
                vwap_signal = indicators.get('vwap_signal', 'neutral')
                vwap_deviation = indicators.get('vwap_deviation', 0)
                diff_pct = ((current - vwap) / vwap * 100) if vwap > 0 else 0
                
                if vwap_signal == 'above':
                    if vwap_deviation > 3:
                        vwap_status = f"🟢远高于VWAP ({diff_pct:+.1f}%) 强势多头"
                    else:
                        vwap_status = f"📈高于VWAP ({diff_pct:+.1f}%)"
                elif vwap_signal == 'below':
                    if vwap_deviation < -3:
                        vwap_status = f"🔴远低于VWAP ({diff_pct:+.1f}%) 弱势空头"
                    else:
                        vwap_status = f"📉低于VWAP ({diff_pct:+.1f}%)"
                else:
                    vwap_status = f"⚪等于VWAP"
                
                print(f"💰 VWAP(机构成本线): ${vwap:.2f} {vwap_status}")
            
            # SAR抛物线转向指标（优化显示）
            if 'sar' in indicators:
                sar = indicators['sar']
                sar_signal = indicators.get('sar_signal', 'neutral')
                sar_trend = indicators.get('sar_trend', 'neutral')
                sar_distance = indicators.get('sar_distance_pct', 0)
                
                if sar_signal == 'buy':
                    if sar_trend == 'up':
                        sar_status = f"🟢持续看涨 (SAR在下方 {sar_distance:.1f}%)"
                    else:
                        sar_status = f"🚀转向看涨 (SAR在下方 {sar_distance:.1f}%) 关键买入"
                elif sar_signal == 'sell':
                    if sar_trend == 'down':
                        sar_status = f"🔴持续看跌 (SAR在上方 {sar_distance:.1f}%)"
                    else:
                        sar_status = f"⚠️转向看跌 (SAR在上方 {sar_distance:.1f}%) 关键卖出"
                else:
                    sar_status = "⚪中性"
                
                print(f"🎯 SAR(抛物线止损): ${sar:.2f} {sar_status} [需10天数据]")
            
            # SuperTrend
            if 'supertrend' in indicators:
                st = indicators['supertrend']
                st_dir = indicators.get('supertrend_direction', 'up')
                
                if st_dir == 'up':
                    st_status = "🟢看涨支撑"
                else:
                    st_status = "🔴看跌阻力"
                
                print(f"🚀 SuperTrend: ${st:.2f} {st_status} [需11天数据]")
            
            # StochRSI
            if 'stoch_rsi_k' in indicators:
                k = indicators['stoch_rsi_k']
                d = indicators['stoch_rsi_d']
                status = indicators.get('stoch_rsi_status', 'neutral')
                
                if status == 'oversold':
                    stoch_desc = "🟢超卖"
                elif status == 'overbought':
                    stoch_desc = "🔴超买"
                else:
                    stoch_desc = "⚪中性"
                    
                print(f"📊 StochRSI: K={k:.1f} D={d:.1f} {stoch_desc}")
                
            # Volume Profile
            if 'vp_poc' in indicators:
                poc = indicators['vp_poc']
                vah = indicators.get('vp_vah', 0)
                val = indicators.get('vp_val', 0)
                status = indicators.get('vp_status', 'inside_va')
                
                if status == 'above_va':
                    vp_desc = "📈上方失衡(看涨)"
                elif status == 'below_va':
                    vp_desc = "📉下方失衡(看跌)"
                else:
                    vp_desc = "⚖️价值区平衡"
                    
                print(f"🧱 筹码分布: POC=${poc:.2f} [{val:.2f} - {vah:.2f}] {vp_desc}")
            
            # Ichimoku Cloud
            if 'ichimoku_tenkan_sen' in indicators:
                tenkan = indicators['ichimoku_tenkan_sen']
                kijun = indicators['ichimoku_kijun_sen']
                span_a = indicators['ichimoku_senkou_span_a']
                span_b = indicators['ichimoku_senkou_span_b']
                status = indicators.get('ichimoku_status', 'inside_cloud')
                
                if status == 'above_cloud':
                    cloud_desc = "☁️云上(看涨)"
                elif status == 'below_cloud':
                    cloud_desc = "🌧️云下(看跌)"
                else:
                    cloud_desc = "🌫️云中(盘整)"
                    
                tk_cross = indicators.get('ichimoku_tk_cross', 'neutral')
                if tk_cross == 'bullish':
                    cross_desc = "➕金叉"
                elif tk_cross == 'bearish':
                    cross_desc = "➖死叉"
                else:
                    cross_desc = ""
                
                print(f"☁️ 一目均衡表: {cloud_desc} {cross_desc}")
                print(f"   转折线: ${tenkan:.2f} | 基准线: ${kijun:.2f}")
                print(f"   云层: ${min(span_a, span_b):.2f} - ${max(span_a, span_b):.2f}")
            
            # OBV趋势
            if 'obv_trend' in indicators:
                obv_trend = indicators['obv_trend']
                price_change = indicators.get('price_change_pct', 0)
                
                if obv_trend == 'up':
                    if price_change > 0:
                        obv_desc = "量价齐升"
                    else:
                        obv_desc = "量价背离(可能见底)"
                elif obv_trend == 'down':
                    if price_change < 0:
                        obv_desc = "量价齐跌"
                    else:
                        obv_desc = "量价背离(可能见顶)"
                else:
                    obv_desc = "平稳"
                
                print(f"📊 OBV: {obv_desc}")
            
            # 趋势强度
            if 'trend_strength' in indicators:
                strength = indicators['trend_strength']
                direction = indicators.get('trend_direction', 'neutral')
                
                if direction == 'up':
                    dir_icon = "📈上涨"
                elif direction == 'down':
                    dir_icon = "📉下跌"
                else:
                    dir_icon = "➡️震荡"
                
                if strength > 50:
                    strength_desc = "强"
                elif strength > 25:
                    strength_desc = "中"
                else:
                    strength_desc = "弱"
                
                print(f"🎯 趋势: {dir_icon} | 强度: {strength:.0f}%({strength_desc})")
            
            # 连续涨跌
            if 'consecutive_up_days' in indicators or 'consecutive_down_days' in indicators:
                up = indicators.get('consecutive_up_days', 0)
                down = indicators.get('consecutive_down_days', 0)
                
                if up > 0:
                    warning = " ⚠️" if up >= 5 else ""
                    print(f"📈 连续{up}天上涨{warning}")
                elif down > 0:
                    warning = " 🟢" if down >= 5 else ""
                    print(f"📉 连续{down}天下跌{warning}")
            
            # 支撑位和压力位
            print(f"🎯 关键价位:")
            
            # Pivot Points
            if 'pivot' in indicators:
                print(f"  枢轴: ${indicators['pivot']:.2f}")
                if 'pivot_r1' in indicators:
                    print(f"  压力: R1=${indicators['pivot_r1']:.2f} R2=${indicators['pivot_r2']:.2f} R3=${indicators['pivot_r3']:.2f}")
                if 'pivot_s1' in indicators:
                    print(f"  支撑: S1=${indicators['pivot_s1']:.2f} S2=${indicators['pivot_s2']:.2f} S3=${indicators['pivot_s3']:.2f}")
            
            # 历史高低点 - 简化显示
            high_low_parts = []
            if 'resistance_20d_high' in indicators:
                high_low_parts.append(f"20日高${indicators['resistance_20d_high']:.2f}")
            if 'support_20d_low' in indicators:
                high_low_parts.append(f"低${indicators['support_20d_low']:.2f}")
            if high_low_parts:
                print(f"  {' | '.join(high_low_parts)}")

            # IBKR基本面数据
            fundamental_data = indicators.get('fundamental_data')
            if fundamental_data and isinstance(fundamental_data, dict) and 'raw_xml' not in fundamental_data:
                print("=" * 70)
                print("📋 IBKR基本面数据")
                print("=" * 70)
                
                # 格式化数值的辅助函数
                def format_number(value_str, unit='', decimals=2):
                    """格式化数值显示"""
                    try:
                        value = float(value_str)
                        if abs(value) >= 1e9:
                            return f"${value/1e9:.{decimals}f}B" + unit
                        elif abs(value) >= 1e6:
                            return f"${value/1e6:.{decimals}f}M" + unit
                        elif abs(value) >= 1e3:
                            return f"${value/1e3:.{decimals}f}K" + unit
                        else:
                            return f"${value:.{decimals}f}" + unit
                    except (ValueError, TypeError):
                        return str(value_str) + unit
                
                def format_percent(value_str, decimals=2):
                    """格式化百分比"""
                    try:
                        value = float(value_str)
                        return f"{value:.{decimals}f}%"
                    except (ValueError, TypeError):
                        return str(value_str) + "%"
                
                def format_shares(value_str):
                    """格式化股数"""
                    try:
                        value = float(value_str)
                        if value >= 1e9:
                            return f"{value/1e9:.2f}B股"
                        elif value >= 1e6:
                            return f"{value/1e6:.2f}M股"
                        else:
                            return f"{int(value):,}股"
                    except (ValueError, TypeError):
                        return str(value_str)
                
                # 1. 基本信息
                if 'CompanyName' in fundamental_data:
                    print(f"\n🏢 基本信息:")
                    print(f"  公司名称: {fundamental_data['CompanyName']}")
                    if 'Exchange' in fundamental_data:
                        print(f"  交易所: {fundamental_data['Exchange']}")
                    if 'Employees' in fundamental_data:
                        try:
                            employees = int(fundamental_data['Employees'])
                            print(f"  员工数: {employees:,}人")
                        except (ValueError, TypeError):
                            print(f"  员工数: {fundamental_data['Employees']}人")
                    if 'SharesOutstanding' in fundamental_data:
                        shares = format_shares(fundamental_data['SharesOutstanding'])
                        print(f"  流通股数: {shares}")
                
                # 2. 市值和价格
                price_section = False
                if 'MarketCap' in fundamental_data:
                    if not price_section:
                        print(f"\n💰 市值与价格:")
                        price_section = True
                    market_cap = format_number(fundamental_data['MarketCap'])
                    print(f"  市值: {market_cap}")
                
                if 'Price' in fundamental_data:
                    if not price_section:
                        print(f"\n💰 市值与价格:")
                        price_section = True
                    price = format_number(fundamental_data['Price'], decimals=2)
                    print(f"  当前价: {price}")
                
                if '52WeekHigh' in fundamental_data and '52WeekLow' in fundamental_data:
                    high = format_number(fundamental_data['52WeekHigh'], decimals=2)
                    low = format_number(fundamental_data['52WeekLow'], decimals=2)
                    print(f"  52周区间: {low} - {high}")
                
                # 3. 财务指标
                financial_section = False
                if 'RevenueTTM' in fundamental_data:
                    if not financial_section:
                        print(f"\n📊 财务指标 (TTM):")
                        financial_section = True
                    revenue = format_number(fundamental_data['RevenueTTM'])
                    print(f"  营收: {revenue}")
                
                if 'NetIncomeTTM' in fundamental_data:
                    if not financial_section:
                        print(f"\n📊 财务指标 (TTM):")
                        financial_section = True
                    net_income = format_number(fundamental_data['NetIncomeTTM'])
                    print(f"  净利润: {net_income}")
                
                if 'EBITDATTM' in fundamental_data:
                    if not financial_section:
                        print(f"\n📊 财务指标 (TTM):")
                        financial_section = True
                    ebitda = format_number(fundamental_data['EBITDATTM'])
                    print(f"  EBITDA: {ebitda}")
                
                if 'ProfitMargin' in fundamental_data:
                    if not financial_section:
                        print(f"\n📊 财务指标 (TTM):")
                        financial_section = True
                    margin = format_percent(fundamental_data['ProfitMargin'])
                    print(f"  利润率: {margin}")
                
                if 'GrossMargin' in fundamental_data:
                    if not financial_section:
                        print(f"\n📊 财务指标 (TTM):")
                        financial_section = True
                    gross_margin = format_percent(fundamental_data['GrossMargin'])
                    print(f"  毛利率: {gross_margin}")
                
                # 4. 每股数据
                per_share_section = False
                if 'EPS' in fundamental_data:
                    if not per_share_section:
                        print(f"\n📈 每股数据:")
                        per_share_section = True
                    eps = format_number(fundamental_data['EPS'], decimals=2)
                    print(f"  每股收益(EPS): {eps}")
                
                if 'BookValuePerShare' in fundamental_data:
                    if not per_share_section:
                        print(f"\n📈 每股数据:")
                        per_share_section = True
                    bvps = format_number(fundamental_data['BookValuePerShare'], decimals=2)
                    print(f"  每股净资产: {bvps}")
                
                if 'CashPerShare' in fundamental_data:
                    if not per_share_section:
                        print(f"\n📈 每股数据:")
                        per_share_section = True
                    cps = format_number(fundamental_data['CashPerShare'], decimals=2)
                    print(f"  每股现金: {cps}")
                
                if 'DividendPerShare' in fundamental_data:
                    if not per_share_section:
                        print(f"\n📈 每股数据:")
                        per_share_section = True
                    dps = format_number(fundamental_data['DividendPerShare'], decimals=3)
                    print(f"  每股股息: {dps}")
                
                # 5. 估值指标
                valuation_section = False
                if 'PE' in fundamental_data:
                    if not valuation_section:
                        print(f"\n💎 估值指标:")
                        valuation_section = True
                    pe = fundamental_data['PE']
                    try:
                        pe_val = float(pe)
                        print(f"  市盈率(PE): {pe_val:.2f}")
                    except (ValueError, TypeError):
                        print(f"  市盈率(PE): {pe}")
                
                if 'PriceToBook' in fundamental_data:
                    if not valuation_section:
                        print(f"\n💎 估值指标:")
                        valuation_section = True
                    pb = fundamental_data['PriceToBook']
                    try:
                        pb_val = float(pb)
                        print(f"  市净率(PB): {pb_val:.2f}")
                    except (ValueError, TypeError):
                        print(f"  市净率(PB): {pb}")
                
                if 'ROE' in fundamental_data:
                    if not valuation_section:
                        print(f"\n💎 估值指标:")
                        valuation_section = True
                    roe = format_percent(fundamental_data['ROE'])
                    print(f"  净资产收益率(ROE): {roe}")
                
                # 6. 预测数据
                forecast_section = False
                if 'TargetPrice' in fundamental_data:
                    if not forecast_section:
                        print(f"\n🔮 分析师预测:")
                        forecast_section = True
                    target = format_number(fundamental_data['TargetPrice'], decimals=2)
                    print(f"  目标价: {target}")
                
                if 'ConsensusRecommendation' in fundamental_data:
                    if not forecast_section:
                        print(f"\n🔮 分析师预测:")
                        forecast_section = True
                    consensus = fundamental_data['ConsensusRecommendation']
                    try:
                        consensus_val = float(consensus)
                        if consensus_val <= 1.5:
                            rec = "强烈买入"
                        elif consensus_val <= 2.5:
                            rec = "买入"
                        elif consensus_val <= 3.5:
                            rec = "持有"
                        elif consensus_val <= 4.5:
                            rec = "卖出"
                        else:
                            rec = "强烈卖出"
                        print(f"  共识评级: {rec} ({consensus_val:.2f})")
                    except (ValueError, TypeError):
                        print(f"  共识评级: {consensus}")
                
                if 'ProjectedEPS' in fundamental_data:
                    if not forecast_section:
                        print(f"\n🔮 分析师预测:")
                        forecast_section = True
                    proj_eps = format_number(fundamental_data['ProjectedEPS'], decimals=2)
                    print(f"  预测EPS: {proj_eps}")
                
                if 'ProjectedGrowthRate' in fundamental_data:
                    if not forecast_section:
                        print(f"\n🔮 分析师预测:")
                        forecast_section = True
                    growth = format_percent(fundamental_data['ProjectedGrowthRate'])
                    print(f"  预测增长率: {growth}")
                
                print()
            
            # 买卖信号
            if signals:
                print("=" * 70)
                print(f"💡 交易信号:")
                print(f"=" * 70)
                
                for signal in signals.get('signals', []):
                    print(f"  {signal}")
                
                print("=" * 70)
                score = signals.get('score', 0)
                recommendation = signals.get('recommendation', '未知')
                print(f"📋 综合评分: {score:+d}/100")
                print(f"💼 交易建议: {recommendation}")
                
                # 风险评估
                risk_data = signals.get('risk', {})
                if isinstance(risk_data, dict):
                    risk_level = risk_data.get('level', 'unknown')
                    risk_score = risk_data.get('score', 0)
                    risk_factors = risk_data.get('factors', [])
                else:
                    # 兼容旧格式
                    risk_level = signals.get('risk_level', 'unknown')
                    risk_score = signals.get('risk_score', 0)
                    risk_factors = signals.get('risk_factors', [])
                
                # 风险等级中文映射
                risk_map = {
                    'very_low': '✅ 很低风险',
                    'low': '🟢 低风险',
                    'medium': '🟡 中等风险',
                    'high': '🔴 高风险',
                    'very_high': '🔴 极高风险',
                    'unknown': '⚪ 未知'
                }
                risk_display = risk_map.get(risk_level, f'⚪ {risk_level}')
                
                if risk_level != 'unknown':
                    print(f"⚠️  风险等级: {risk_display} (风险分: {risk_score}/100)")
                    
                    if risk_factors:
                        print(f"   风险因素: {', '.join(risk_factors)}")
                
                # 止损止盈建议
                if 'stop_loss' in signals and 'take_profit' in signals:
                    stop_loss = signals['stop_loss']
                    take_profit = signals['take_profit']
                    current_price = indicators.get('current_price', 0)
                    
                    if current_price > 0:
                        sl_pct = ((stop_loss - current_price) / current_price) * 100
                        tp_pct = ((take_profit - current_price) / current_price) * 100
                        risk_reward = abs(tp_pct / sl_pct) if sl_pct != 0 else 0
                        
                        print(f"\n💰 风险管理:")
                        print(f"   建议止损: ${stop_loss:.2f} ({sl_pct:+.1f}%)")
                        print(f"   建议止盈: ${take_profit:.2f} ({tp_pct:+.1f}%)")
                        print(f"   风险回报比: 1:{risk_reward:.1f}")
                
                print(f"=" * 70)
            
            # 如果后端返回了AI分析结果，显示AI分析
            if 'ai_analysis' in result:
                ai_analysis = result.get('ai_analysis', '')
                ai_model = result.get('model', 'unknown')
                ai_available = result.get('ai_available', False)
                
                if ai_available:
                    print(f"\n{'='*70}")
                    print(f"🤖 {symbol.upper()} AI技术分析报告")
                    print(f"{'='*70}")
                    print(f"模型: {ai_model}")
                    print(f"{'='*70}\n")
                    
                    # 显示AI分析
                    print(ai_analysis)
                    print(f"\n{'='*70}")
                elif 'ai_error' in result:
                    print(f"\n⚠️  AI分析不可用: {result.get('ai_error', '未知错误')}")
                
        else:
            msg = result.get('message', '未知错误') if result else '分析失败'
            print(f"❌ {msg}")
    
    def indicators_info(self, symbol: str, duration: str = '3 M', bar_size: str = '1 day'):
        """
        技术指标解释 - 显示主要技术指标的参考范围与知识解释
        """
        print(f"获取 {symbol.upper()} 指标...")

        # 标准化参数
        duration = re.sub(r'(\d+)([SDWMY])', r'\1 \2', duration, flags=re.IGNORECASE)
        bar_size = bar_size.replace('min', ' min').replace('hour', ' hour').replace('day', ' day')
        bar_size = re.sub(r'\s+', ' ', bar_size).strip()
        if 'min' in bar_size and not bar_size.endswith('mins'):
            bar_size = bar_size.replace('min', 'mins')

        # 获取指标数据
        params = f"?duration={urllib.parse.quote(duration)}&bar_size={urllib.parse.quote(bar_size)}"
        result = self._request('GET', f"/api/analyze/{symbol.upper()}{params}")

        if not (result and result.get('success')):
            msg = result.get('message', '未知错误') if result else '查询失败'
            print(f"❌ {msg}")
            return

        indicators = result.get('indicators', {})
        
        # 获取指标解释信息
        info_result = self._request('GET', '/api/indicator-info')
        indicator_info_map = {}
        if info_result and info_result.get('success'):
            indicator_info_map = info_result.get('indicators', {})

        print("\n📘 技术指标参考与解释:")
        print("=" * 70)

        # 当前价格
        if 'current_price' in indicators:
            print(f"当前价: ${indicators['current_price']:.2f}")

        # 移动平均线
        has_ma = any(k in indicators for k in ['ma5', 'ma10', 'ma20', 'ma50'])
        if has_ma:
            ma_info = indicator_info_map.get('ma', {})
            print(f"\n[{ma_info.get('name', '移动平均线 MA')}]")
            for period in [5, 10, 20, 50]:
                key = f"ma{period}"
                if key in indicators:
                    ref_text = ma_info.get('reference_range', {}).get(key, '')
                    print(f"  MA{period}: ${indicators[key]:.2f}  —  {ref_text}")
            print(f"  解释: {ma_info.get('interpretation', '')}")

        # RSI
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            rsi_info = indicator_info_map.get('rsi', {})
            print(f"\n[{rsi_info.get('name', 'RSI 相对强弱指数')}]")
            ref_ranges = rsi_info.get('reference_range', {})
            ref_text = '；'.join([f"{k}: {v}" for k, v in ref_ranges.items()])
            print(f"  当前: {rsi:.1f}  参考: {ref_text}")
            print(f"  解释: {rsi_info.get('interpretation', '')}")

        # 布林带
        if all(k in indicators for k in ['bb_upper', 'bb_middle', 'bb_lower']):
            bb_info = indicator_info_map.get('bb', {})
            print(f"\n[{bb_info.get('name', '布林带 Bollinger Bands')}]")
            print(f"  上轨: ${indicators['bb_upper']:.2f}  中轨: ${indicators['bb_middle']:.2f}  下轨: ${indicators['bb_lower']:.2f}")
            ref_ranges = bb_info.get('reference_range', {})
            ref_text = '；'.join([f"{k}: {v}" for k, v in ref_ranges.items()])
            print(f"  参考: {ref_text}")

        # MACD
        if 'macd' in indicators:
            macd_val = indicators['macd']
            signal = indicators.get('macd_signal', 0)
            hist = indicators.get('macd_histogram', 0)
            macd_info = indicator_info_map.get('macd', {})
            print(f"\n[{macd_info.get('name', 'MACD 指标')}]")
            print(f"  MACD: {macd_val:.3f}  Signal: {signal:.3f}  Hist: {hist:.3f}")
            ref_ranges = macd_info.get('reference_range', {})
            ref_text = '；'.join([f"{k}: {v}" for k, v in ref_ranges.items()])
            print(f"  参考: {ref_text}")

        # KDJ
        if all(k in indicators for k in ['kdj_k', 'kdj_d', 'kdj_j']):
            kdj_info = indicator_info_map.get('kdj', {})
            print(f"\n[{kdj_info.get('name', 'KDJ 指标')}]")
            print(f"  K={indicators['kdj_k']:.1f}  D={indicators['kdj_d']:.1f}  J={indicators['kdj_j']:.1f}")
            ref_ranges = kdj_info.get('reference_range', {})
            ref_text = '；'.join([f"{k}: {v}" for k, v in ref_ranges.items()])
            print(f"  参考: {ref_text}")

        # 威廉%R
        if 'williams_r' in indicators:
            wr = indicators['williams_r']
            wr_info = indicator_info_map.get('williams_r', {})
            print(f"\n[{wr_info.get('name', 'Williams %R')}]")
            ref_ranges = wr_info.get('reference_range', {})
            ref_text = '；'.join([f"{k}: {v}" for k, v in ref_ranges.items()])
            print(f"  当前: {wr:.1f}  参考: {ref_text}")
            print(f"  解释: {wr_info.get('interpretation', '')}")

        # ATR / 波动率
        if 'atr' in indicators or 'volatility_20' in indicators:
            print("\n[波动与风险]")
            if 'atr' in indicators:
                atr = indicators['atr']
                atr_pct = indicators.get('atr_percent', 0)
                atr_info = indicator_info_map.get('atr', {})
                print(f"  ATR: ${atr:.2f} ({atr_pct:.1f}%)  —  {atr_info.get('interpretation', '')}")
            if 'volatility_20' in indicators:
                vol = indicators['volatility_20']
                vol_info = indicator_info_map.get('volatility', {})
                ref_ranges = vol_info.get('reference_range', {})
                level = '低' if vol <= 2 else '中' if vol <= 3 else '高' if vol <= 5 else '极高'
                level_desc = ref_ranges.get(level, level)
                print(f"  20日波动率: {vol:.2f}% ({level_desc})  —  {vol_info.get('interpretation', '')}")

        # 关键价位
        if 'pivot' in indicators:
            pivot_info = indicator_info_map.get('pivot', {})
            print(f"\n[{pivot_info.get('name', '枢轴与支撑/压力')}]")
            print(f"  Pivot: ${indicators.get('pivot', 0):.2f}")
            if 'pivot_r1' in indicators:
                print(f"  压力: R1=${indicators['pivot_r1']:.2f}  R2=${indicators.get('pivot_r2', 0):.2f}  R3=${indicators.get('pivot_r3', 0):.2f}")
            if 'pivot_s1' in indicators:
                print(f"  支撑: S1=${indicators['pivot_s1']:.2f}  S2=${indicators.get('pivot_s2', 0):.2f}  S3=${indicators.get('pivot_s3', 0):.2f}")
            print(f"  解释: {pivot_info.get('interpretation', '')}")

        # 提示
        print("\n提示: 指标应结合趋势、量能与基本面综合判断，单一信号不可孤立使用。")

    def history(self, symbol: str, duration: str = '1 D', bar_size: str = '5 mins'):
        """
        查询历史数据
        """
        # 标准化参数格式（处理如 "1D" -> "1 D", "5mins" -> "5 mins"）
        # 处理duration: 1D -> 1 D, 1W -> 1 W等
        duration = re.sub(r'(\d+)([SDWMY])', r'\1 \2', duration, flags=re.IGNORECASE)
        
        # 处理bar_size: 5mins -> 5 mins, 1hour -> 1 hour等
        bar_size = bar_size.replace('min', ' min').replace('hour', ' hour').replace('day', ' day')
        bar_size = re.sub(r'\s+', ' ', bar_size).strip()  # 规范化空格
        
        # 添加复数s如果需要
        if 'min' in bar_size and not bar_size.endswith('mins'):
            bar_size = bar_size.replace('min', 'mins')
            
        print(f"查询 {symbol.upper()}...")
        
        # URL编码参数
        params = f"?duration={urllib.parse.quote(duration)}&bar_size={urllib.parse.quote(bar_size)}"
        result = self._request('GET', f'/api/history/{symbol.upper()}{params}')
        
        if result and result.get('success'):
            data = result.get('data', [])
            count = result.get('count', 0)
            
            if data:
                print(f"\n📊 {symbol.upper()} 历史数据 ({duration}, {bar_size}):")
                print("-" * 80)
                print(f"{'时间':<20} {'开盘':>10} {'最高':>10} {'最低':>10} {'收盘':>10} {'成交量':>12}")
                print("-" * 80)
                
                # 只显示最近10条
                for bar in data[-10:]:
                    date = bar.get('date', '')
                    open_price = bar.get('open', 0)
                    high = bar.get('high', 0)
                    low = bar.get('low', 0)
                    close = bar.get('close', 0)
                    volume = bar.get('volume', 0)
                    
                    print(f"{date:<20} {open_price:>10.2f} {high:>10.2f} {low:>10.2f} "
                          f"{close:>10.2f} {volume:>12,}")
                
                if count > 10:
                    print(f"\n显示最近10条，共{count}条数据")
            else:
                print("⚠️  无数据")
        else:
            msg = result.get('message', '未知错误') if result else '查询失败'
            print(f"❌ {msg}")
    
    def hot_stocks(self, limit: int = 20):
        """
        获取热门股票代码列表（仅美股）
        """
        params = f"?limit={limit}"
        result = self._request('GET', f'/api/hot-stocks{params}')
        
        if result and result.get('success'):
            stocks = result.get('stocks', [])
            
            print(f"\n🔥 美股热门股票 (共{len(stocks)}个):")
            print("-" * 80)
            print(f"{'代码':<10} {'名称':<30} {'类别':<15}")
            print("-" * 80)
            
            for stock in stocks:
                symbol = stock.get('symbol', 'N/A')
                name = stock.get('name', 'N/A')
                category = stock.get('category', 'N/A')
                print(f"{symbol:<10} {name:<30} {category:<15}")
        else:
            msg = result.get('message', '未知错误') if result else '查询失败'
            print(f"❌ {msg}")
    
    def help(self):
        """
        显示帮助信息
        """
        print("\n" + "=" * 70)
        print("💡 快捷命令")
        print("=" * 70)
        print("""
🔍 查询:
  a              账户        p              持仓
  o              订单        q  AAPL        报价
  i  AAPL        详情        an AAPL        技术分析(自动AI)
  ti AAPL        指标解释    ti AAPL 3M 1day 自定义周期
  hot            热门股票    hot 20          美股热门(20个)

📊 交易:
  b AAPL 10      市价买      b AAPL 10 175  限价买
  s AAPL 10      市价卖      s AAPL 10 180  限价卖
  x 123          撤单

📈 数据:
  hi AAPL        历史数据

🤖 AI分析:
  ai AAPL        AI技术分析⭐  (需要Ollama)
  ai AAPL 3M     自定义周期
  ai AAPL 3M 1day deepseek-v3.1:671b-cloud  指定模型

⚙️  系统:
  c              连接        d              断开
  st             状态        clear          清屏
  ?              帮助        exit           退出
        """)
        print("=" * 70 + "\n")


def main():
    """
    主函数 - 启动交互式命令行
    """
    cli = TradingCLI()
    
    print("\n" + "=" * 60)
    print("🚀 IB Trading CLI")
    print("=" * 60)
    print(f"服务: {API_BASE_URL}")
    print("输入 '?' 查看帮助")
    print("=" * 60 + "\n")
    
    while True:
        try:
            # 显示提示符
            prompt = "🔌 " if not cli.connected else "✅ "
            cmd_input = input(prompt).strip()
            
            if not cmd_input:
                continue
            
            # 使用shlex正确解析带引号的参数
            try:
                parts = shlex.split(cmd_input)
            except ValueError:
                # 如果解析失败（如引号不匹配），回退到简单分割
                parts = cmd_input.split()
                
            cmd = parts[0].lower()
            args = parts[1:]
            
            # 连接命令
            if cmd in ['connect', 'conn', 'c']:
                host = args[0] if len(args) > 0 else "127.0.0.1"
                port = int(args[1]) if len(args) > 1 else 4001
                client_id = int(args[2]) if len(args) > 2 else 1
                cli.connect(host, port, client_id)
                
            elif cmd in ['disconnect', 'disc', 'd']:
                cli.disconnect()
                
            elif cmd in ['health', 'status', 'st']:
                cli.health()
                
            # 查询命令
            elif cmd in ['account', 'acc', 'a']:
                cli.account()
                
            elif cmd in ['positions', 'pos', 'p']:
                cli.positions()
                
            elif cmd in ['orders', 'ord', 'o']:
                cli.orders()
                
            elif cmd in ['quote', 'q']:
                if len(args) < 1:
                    print("❌ 用法: q <symbol>")
                else:
                    cli.quote(args[0])
                    
            elif cmd in ['info', 'i']:
                if len(args) < 1:
                    print("❌ 用法: i <symbol>")
                else:
                    cli.info(args[0])
                    
            elif cmd in ['ai', 'ai-analyze']:
                if len(args) < 1:
                    print("❌ 用法: ai <symbol> [duration] [bar_size] [model]")
                else:
                    symbol = args[0]
                    duration = args[1] if len(args) > 1 else '3 M'
                    bar_size = args[2] if len(args) > 2 else '1 day'
                    model = args[3] if len(args) > 3 else 'deepseek-v3.1:671b-cloud'
                    cli.ai_analyze(symbol, duration, bar_size, model)
            
            elif cmd in ['analyze', 'an']:
                if len(args) < 1:
                    print("❌ 用法: an <symbol> [duration] [bar_size] [model]")
                    print("   示例: an AAPL")
                    print("   示例: an AAPL 3M 1day")
                    print("   示例: an AAPL 3M 1day deepseek-v3.1:671b-cloud")
                    print("   注意: 后端会自动检测 Ollama，如果可用则自动执行AI分析")
                else:
                    symbol = args[0]
                    duration = args[1] if len(args) > 1 else '3 M'
                    bar_size = args[2] if len(args) > 2 else '1 day'
                    model = args[3] if len(args) > 3 else 'deepseek-v3.1:671b-cloud'
                    
                    cli.analyze(symbol, duration, bar_size, model)

            elif cmd in ['ti', 'ti-info', 'indicators']:
                if len(args) < 1:
                    print("❌ 用法: ti <symbol> [duration] [bar_size]")
                else:
                    symbol = args[0]
                    duration = args[1] if len(args) > 1 else '3 M'
                    bar_size = args[2] if len(args) > 2 else '1 day'
                    cli.indicators_info(symbol, duration, bar_size)
                    
            elif cmd in ['history', 'hi']:
                if len(args) < 1:
                    print("❌ 用法: hi <symbol> [duration] [bar_size]")
                else:
                    symbol = args[0]
                    duration = args[1] if len(args) > 1 else '1 D'
                    bar_size = args[2] if len(args) > 2 else '5 mins'
                    cli.history(symbol, duration, bar_size)
            
            elif cmd in ['hot', 'hot-stocks']:
                limit = int(args[0]) if len(args) > 0 else 20
                cli.hot_stocks(limit)
            
            # 交易命令
            elif cmd in ['buy', 'b']:
                if len(args) < 2:
                    print("❌ 用法: b <symbol> <quantity> [price]")
                else:
                    symbol = args[0]
                    quantity = float(args[1])
                    price = float(args[2]) if len(args) > 2 else None
                    cli.buy(symbol, quantity, price)
                    
            elif cmd in ['sell', 's']:
                if len(args) < 2:
                    print("❌ 用法: s <symbol> <quantity> [price]")
                else:
                    symbol = args[0]
                    quantity = float(args[1])
                    price = float(args[2]) if len(args) > 2 else None
                    cli.sell(symbol, quantity, price)
                    
            elif cmd in ['cancel', 'x']:
                if len(args) < 1:
                    print("❌ 用法: x <order_id>")
                else:
                    order_id = int(args[0])
                    cli.cancel(order_id)
                    
            # 其他命令
            elif cmd in ['help', '?']:
                cli.help()
                
            elif cmd in ['clear', 'cls']:
                import os
                os.system('clear' if os.name != 'nt' else 'cls')
                
            elif cmd in ['exit', 'quit', 'q']:
                if cli.connected:
                    print("断开连接中...")
                    cli.disconnect()
                print("👋 再见!")
                break
                
            else:
                print(f"❌ 未知命令: {cmd}，输入 'help' 查看帮助")
                
        except KeyboardInterrupt:
            print("\n使用 'exit' 退出程序")
        except ValueError as e:
            print(f"❌ 参数错误: {e}")
        except Exception as e:
            print(f"❌ 错误: {e}")


if __name__ == '__main__':
    main()

