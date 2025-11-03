#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
IB Trading Gateway 交互式命令行客户端
通过命令行对接API后端服务
"""

import requests
import json
import shlex
from typing import Optional
import readline  # 启用命令行历史和编辑

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
        import re
        duration = re.sub(r'(\d+)([SDWMY])', r'\1 \2', duration, flags=re.IGNORECASE)
        bar_size = bar_size.replace('min', ' min').replace('hour', ' hour').replace('day', ' day')
        bar_size = re.sub(r'\s+', ' ', bar_size).strip()
        if 'min' in bar_size and not bar_size.endswith('mins'):
            bar_size = bar_size.replace('min', 'mins')
        
        import urllib.parse
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
    
    def analyze(self, symbol: str, duration: str = '3 M', bar_size: str = '1 day'):
        """
        技术分析 - 生成买卖信号（默认3个月日K线）
        """
        print(f"分析 {symbol.upper()}...")
        
        # 标准化参数
        import re
        duration = re.sub(r'(\d+)([SDWMY])', r'\1 \2', duration, flags=re.IGNORECASE)
        bar_size = bar_size.replace('min', ' min').replace('hour', ' hour').replace('day', ' day')
        bar_size = re.sub(r'\s+', ' ', bar_size).strip()
        if 'min' in bar_size and not bar_size.endswith('mins'):
            bar_size = bar_size.replace('min', 'mins')
        
        import urllib.parse
        params = f"?duration={urllib.parse.quote(duration)}&bar_size={urllib.parse.quote(bar_size)}"
        result = self._request('GET', f'/api/analyze/{symbol.upper()}{params}')
        
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
            
            # RSI
            if 'rsi' in indicators:
                rsi = indicators['rsi']
                if rsi < 30:
                    status = "🟢 超卖(可能反弹)"
                elif rsi > 70:
                    status = "🔴 超买(可能回调)"
                else:
                    status = "⚪ 中性"
                print(f"\n📊 RSI(14日): {rsi:.1f} {status} [需14天数据]")
            
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
                
                print(f"\n📏 布林带(20日):{position} [需20天数据]")
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
                
                print(f"\n📈 MACD: {macd_val:.3f} | 信号: {signal:.3f} | {trend} [需26天数据]")
            
            # 成交量
            if 'volume_ratio' in indicators:
                ratio = indicators['volume_ratio']
                if ratio > 1.5:
                    desc = "放量"
                elif ratio < 0.7:
                    desc = "缩量"
                else:
                    desc = "正常"
                print(f"\n📊 成交量: {ratio:.2f}x ({desc})")
            
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
                    print(f"\n⚡ {' | '.join(parts)}")
            
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
                print(f"\n📊 KDJ(9日): K={k:.1f} D={d:.1f} J={j:.1f} | {status} {trend} [需9天数据]")
            
            # 威廉指标
            if 'williams_r' in indicators:
                wr = indicators['williams_r']
                if wr < -80:
                    wr_status = "🟢超卖"
                elif wr > -20:
                    wr_status = "🔴超买"
                else:
                    wr_status = "⚪中性"
                print(f"\n📉 威廉%R: {wr:.1f} {wr_status}")
            
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
                
                print(f"\n📊 OBV: {obv_desc}")
            
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
                
                print(f"\n🎯 趋势: {dir_icon} | 强度: {strength:.0f}%({strength_desc})")
            
            # 连续涨跌
            if 'consecutive_up_days' in indicators or 'consecutive_down_days' in indicators:
                up = indicators.get('consecutive_up_days', 0)
                down = indicators.get('consecutive_down_days', 0)
                
                if up > 0:
                    warning = " ⚠️" if up >= 5 else ""
                    print(f"\n📈 连续{up}天上涨{warning}")
                elif down > 0:
                    warning = " 🟢" if down >= 5 else ""
                    print(f"\n📉 连续{down}天下跌{warning}")
            
            # 支撑位和压力位
            print(f"\n🎯 关键价位:")
            
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
            
            # 买卖信号
            if signals:
                print(f"\n" + "=" * 70)
                print(f"💡 交易信号:")
                print(f"=" * 70)
                
                for signal in signals.get('signals', []):
                    print(f"  {signal}")
                
                print(f"\n" + "=" * 70)
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
                
        else:
            msg = result.get('message', '未知错误') if result else '分析失败'
            print(f"❌ {msg}")
    
    def history(self, symbol: str, duration: str = '1 D', bar_size: str = '5 mins'):
        """
        查询历史数据
        """
        # 标准化参数格式（处理如 "1D" -> "1 D", "5mins" -> "5 mins"）
        import re
        
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
        import urllib.parse
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
    
    def kline(self, symbol: str, duration: str = '1 M', bar_size: str = '1 day', show_volume: bool = False):
        """
        绘制K线图
        """
        # 标准化参数格式
        import re
        duration = re.sub(r'(\d+)([SDWMY])', r'\1 \2', duration, flags=re.IGNORECASE)
        bar_size = bar_size.replace('min', ' min').replace('hour', ' hour').replace('day', ' day')
        bar_size = re.sub(r'\s+', ' ', bar_size).strip()
        if 'min' in bar_size and not bar_size.endswith('mins'):
            bar_size = bar_size.replace('min', 'mins')
        
        print(f"加载 {symbol.upper()} K线数据...")
        
        # 获取历史数据
        import urllib.parse
        params = f"?duration={urllib.parse.quote(duration)}&bar_size={urllib.parse.quote(bar_size)}"
        result = self._request('GET', f'/api/history/{symbol.upper()}{params}')
        
        if result and result.get('success'):
            data = result.get('data', [])
            
            if not data:
                print("⚠️  无数据")
                return
            
            # 提取数据
            dates = [bar.get('date', '') for bar in data]
            opens = [bar.get('open', 0) for bar in data]
            highs = [bar.get('high', 0) for bar in data]
            lows = [bar.get('low', 0) for bar in data]
            closes = [bar.get('close', 0) for bar in data]
            volumes = [bar.get('volume', 0) for bar in data]
            
            # 绘制K线图
            try:
                import plotext as plt
                from datetime import datetime
                
                # 清除之前的图表
                plt.clear_figure()
                
                # 转换日期格式：20251024 -> 24/10/2025
                formatted_dates = []
                for date_str in dates:
                    try:
                        # 如果是 YYYYMMDD 格式
                        if len(date_str) == 8 and date_str.isdigit():
                            dt = datetime.strptime(date_str, '%Y%m%d')
                            formatted_dates.append(dt.strftime('%d/%m/%Y'))
                        # 如果已经是其他格式，尝试解析
                        elif ' ' in date_str:
                            dt = datetime.strptime(date_str.split()[0], '%Y%m%d')
                            formatted_dates.append(dt.strftime('%d/%m/%Y'))
                        else:
                            formatted_dates.append(date_str)
                    except:
                        formatted_dates.append(date_str)
                
                # 准备K线数据（plotext需要字典格式）
                ohlc_data = {
                    'Open': opens,
                    'Close': closes,
                    'High': highs,
                    'Low': lows
                }
                
                # 设置日期格式
                plt.date_form('d/m/Y')
                
                if show_volume:
                    # 创建子图：K线 + 成交量
                    plt.subplots(2, 1)
                    
                    # 上图：K线
                    plt.subplot(1, 1)
                    plt.candlestick(formatted_dates, ohlc_data)
                    plt.plotsize(None, 20)
                    plt.title(f"{symbol.upper()} K线图 ({duration})")
                    plt.ylabel("价格 ($)")
                    
                    # 下图：成交量
                    plt.subplot(2, 1)
                    plt.bar(formatted_dates, volumes)
                    plt.plotsize(None, 8)
                    plt.xlabel("日期")
                    plt.ylabel("成交量")
                    
                else:
                    # 只显示K线
                    plt.candlestick(formatted_dates, ohlc_data)
                    plt.plotsize(None, 25)
                    plt.title(f"{symbol.upper()} K线图 ({duration})")
                    plt.xlabel("日期")
                    plt.ylabel("价格 ($)")
                
                # 显示图表
                plt.show()
                
                # 显示统计信息
                current = closes[-1]
                prev = closes[0]
                change = current - prev
                change_pct = (change / prev * 100) if prev > 0 else 0
                icon = "📈" if change >= 0 else "📉"
                
                print(f"\n📊 区间统计:")
                print(f"   当前价: ${current:.2f}")
                print(f"   区间涨跌: {icon} ${change:+.2f} ({change_pct:+.2f}%)")
                print(f"   最高: ${max(highs):.2f}")
                print(f"   最低: ${min(lows):.2f}")
                print(f"   数据点: {len(data)}根K线")
                
                if show_volume:
                    avg_vol = sum(volumes) / len(volumes) if volumes else 0
                    print(f"   平均成交量: {int(avg_vol):,}")
                
            except ImportError:
                print("❌ 需要安装 plotext: pip install plotext")
            except Exception as e:
                print(f"❌ 绘图失败: {e}")
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
  i  AAPL        详情        an AAPL        技术分析

📊 交易:
  b AAPL 10      市价买      b AAPL 10 175  限价买
  s AAPL 10      市价卖      s AAPL 10 180  限价卖
  x 123          撤单

📈 数据:
  hi AAPL        历史数据    k  AAPL        K线图
  k  AAPL 1M     月K线图     k  AAPL 3M v   带成交量

🤖 AI分析:
  ai AAPL        AI技术分析⭐  (需要Ollama)
  ai AAPL 3M     自定义周期
  ai AAPL 3M 1day deepseek-v3.1:671b-cloud  指定模型

⚙️  系统:
  c              连接        d              断开
  st             状态        clear          清屏
  ?              帮助        exit           退出

💡 提示:
  • AI分析需要先安装Ollama: brew install ollama
  • 启动Ollama服务: ollama serve
  • 拉取模型: ollama pull deepseek-v3.1:671b-cloud
  • K线图支持任意周期: k AAPL 1W/1M/3M/1Y
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
                    print("❌ 用法: an <symbol> [duration] [bar_size]")
                else:
                    symbol = args[0]
                    duration = args[1] if len(args) > 1 else '3 M'
                    bar_size = args[2] if len(args) > 2 else '1 day'
                    cli.analyze(symbol, duration, bar_size)
                    
            elif cmd in ['history', 'hi']:
                if len(args) < 1:
                    print("❌ 用法: hi <symbol> [duration] [bar_size]")
                else:
                    symbol = args[0]
                    duration = args[1] if len(args) > 1 else '1 D'
                    bar_size = args[2] if len(args) > 2 else '5 mins'
                    cli.history(symbol, duration, bar_size)
            
            elif cmd in ['kline', 'k', 'chart']:
                if len(args) < 1:
                    print("❌ 用法: k <symbol> [duration] [bar_size] [volume]")
                else:
                    symbol = args[0]
                    duration = args[1] if len(args) > 1 else '1 M'
                    bar_size = args[2] if len(args) > 2 else '1 day'
                    # 检查是否有 volume 参数
                    show_volume = len(args) > 3 and args[3].lower() in ['v', 'vol', 'volume']
                    cli.kline(symbol, duration, bar_size, show_volume)
                
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

