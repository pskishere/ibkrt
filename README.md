# SchwabGo - 美股实盘交易系统

基于 Interactive Brokers (IB) API 的美股实盘交易系统，提供技术分析、智能交易信号和 AI 分析功能。

## 功能特性

### 📊 技术分析
- **移动平均线 (MA)**: MA5, MA10, MA20, MA50
- **动量指标**: RSI, MACD, KDJ, Williams %R
- **波动指标**: 布林线、ATR、波动率
- **趋势指标**: CCI, ADX, SAR
- **成交量指标**: OBV, VWAP, 成交量比率
- **支撑压力位**: 枢轴点、斐波那契回撤位
- **缠论分析**: 分型、笔、线段、中枢

### 📈 K线图可视化
- 基于 lightweight-charts 的专业 K线图
- 支持多种技术指标叠加显示
- 支持缠论分析图形化展示
- 响应式设计，支持移动端

### 🤖 AI 分析
- 集成 Ollama 本地大模型
- 支持 DeepSeek、Qwen 等模型
- 综合技术分析和基本面分析
- 提供交易建议和风险评估

### 💼 交易功能
- 实时持仓查询
- 市价/限价订单
- 订单管理和撤单
- 账户信息查询

## 技术栈

### 后端
- Python 3.x
- Flask (RESTful API)
- IBAPI (Interactive Brokers API)
- NumPy (技术指标计算)
- SQLite (数据缓存)

### 前端
- React 18 + TypeScript
- Vite (构建工具)
- Ant Design (UI 组件)
- lightweight-charts (K线图)
- Axios (HTTP 客户端)

## 项目结构

```
schwabgo/
├── indicators/          # 技术指标计算模块
│   ├── ma.py           # 移动平均线
│   ├── rsi.py          # RSI 指标
│   ├── bollinger.py    # 布林带
│   ├── macd.py         # MACD 指标
│   ├── kdj.py          # KDJ 指标
│   ├── chanlun.py      # 缠论分析
│   └── ...
├── web/                # 前端项目
│   ├── src/
│   │   ├── components/ # React 组件
│   │   ├── pages/      # 页面
│   │   ├── services/   # API 服务
│   │   └── types/      # TypeScript 类型
│   └── package.json
├── go.py               # 主服务程序
├── cli.py              # 命令行工具
├── requirements.txt    # Python 依赖
└── stock_cache.db      # SQLite 缓存数据库
```

## 安装部署

### 1. 后端环境

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 前端环境

```bash
cd web
npm install
```

### 3. 配置 IB Gateway/TWS

1. 下载并安装 IB Gateway 或 Trader Workstation (TWS)
2. 启用 API 连接（配置 → API → 启用 ActiveX 和 Socket 客户端）
3. 设置可信 IP（默认 127.0.0.1）
4. 配置端口（默认 7497 实盘，7496 模拟盘）

### 4. 配置 Ollama（可选）

```bash
# 安装 Ollama
# 访问 https://ollama.ai 下载安装

# 拉取模型
ollama pull deepseek-v3.1:671b-cloud
# 或
ollama pull qwen2.5:32b-instruct-q4_K_M
```

## 使用方法

### 启动后端服务

```bash
# 激活虚拟环境
source .venv/bin/activate

# 启动服务（默认端口 5001）
python go.py

# 或指定端口
python go.py --port 5002
```

### 启动前端

```bash
cd web
npm run dev
```

访问 http://localhost:3000

### 命令行工具

```bash
# 查询持仓
python cli.py positions

# 技术分析
python cli.py analyze AAPL

# AI 分析
python cli.py ai-analyze NVDA --model deepseek-v3.1:671b-cloud

# 买入股票
python cli.py buy TSLA 10

# 卖出股票
python cli.py sell TSLA 5

# 查询订单
python cli.py orders
```

## API 文档

### 技术分析
```
GET /api/analyze/<symbol>
参数:
  - duration: 数据周期 (默认 '3 M')
  - bar_size: K线周期 (默认 '1 day')
  - model: AI模型 (默认 'deepseek-v3.1:671b-cloud')
```

### 持仓查询
```
GET /api/positions
```

### 下单
```
POST /api/orders/buy
POST /api/orders/sell
Body:
  - symbol: 股票代码
  - quantity: 数量
  - price: 价格 (可选，不填为市价单)
```

### 撤单
```
DELETE /api/orders/<order_id>
```

更多 API 详情请查看源代码。

## 技术指标说明

### 布林线 (Bollinger Bands)
- 中轨：20日移动平均线
- 上轨：中轨 + 2倍标准差
- 下轨：中轨 - 2倍标准差
- 用途：判断超买超卖，识别波动区间

### RSI (相对强弱指数)
- 范围：0-100
- 超卖：< 30
- 超买：> 70
- 用途：判断价格动能和反转信号

### MACD
- MACD线：快线 - 慢线
- 信号线：MACD的9日EMA
- 柱状图：MACD - 信号线
- 用途：趋势跟踪和交易信号

### 缠论分析
- 分型：顶分型、底分型
- 笔：相邻分型的连线
- 线段：笔的组合
- 中枢：多个线段的重叠区域
- 用途：识别买卖点和趋势结构

## 注意事项

⚠️ **风险提示**
- 本系统仅供学习和研究使用
- 实盘交易有风险，投资需谨慎
- 使用前请充分测试并理解各项功能
- 建议先在模拟盘测试

⚠️ **数据说明**
- 技术指标基于历史数据计算
- AI分析仅供参考，不构成投资建议
- 实时数据依赖 IB API 连接
- 缓存有效期为当天

## 开发计划

- [ ] 支持更多技术指标
- [ ] 策略回测功能
- [ ] 实时行情推送
- [ ] 多账户管理
- [ ] 移动端 App
- [ ] 自动交易策略

## 许可证

MIT License

## 联系方式

如有问题或建议，欢迎提交 Issue。
