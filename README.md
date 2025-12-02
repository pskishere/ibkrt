# SchwabGo - 美股数据分析系统

基于 yfinance 的美股数据分析系统，提供技术分析、基本面分析和 AI 分析功能。

## 功能特性

### 📊 技术分析
- **移动平均线 (MA)**: MA5, MA10, MA20, MA50
- **动量指标**: RSI, MACD, KDJ, Williams %R
- **波动指标**: 布林线、ATR、波动率
- **趋势指标**: CCI, ADX, SAR
- **成交量指标**: OBV, VWAP, 成交量比率
- **支撑压力位**: 枢轴点、斐波那契回撤位

### 📈 K线图可视化
- 基于 lightweight-charts 的专业 K线图
- 支持多种技术指标叠加显示
- 响应式设计，支持移动端

### 🤖 AI 分析
- 集成 Ollama 本地大模型
- 支持 DeepSeek、Qwen 等模型
- 综合技术分析和基本面分析
- 提供交易建议和风险评估

### 💰 基本面分析
- 财务报表（年度/季度）
- 资产负债表
- 现金流量表
- 估值指标（PE、PB、ROE等）
- 分析师预测

## 技术栈

### 后端
- Python 3.x
- Flask (RESTful API)
- yfinance (股票数据获取)
- NumPy, Pandas (数据处理和指标计算)
- SQLite (数据缓存)
- Ollama (AI 分析，可选)

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
│   └── ...
├── web/                # 前端项目
│   ├── src/
│   │   ├── components/ # React 组件
│   │   ├── pages/      # 页面
│   │   ├── services/   # API 服务
│   │   └── types/      # TypeScript 类型
│   └── package.json
├── backend/            # 后端服务代码
│   ├── app.py         # Flask应用主文件
│   ├── settings.py    # 配置和常量
│   ├── yfinance.py    # YFinance数据获取
│   ├── database.py    # 数据库操作
│   ├── indicators_calculator.py  # 技术指标计算
│   ├── signals_generator.py      # 信号生成
│   ├── ai_analyzer.py  # AI分析
│   ├── indicator_info.json  # 技术指标说明配置
│   ├── requirements.txt     # Python 依赖
│   └── indicators/    # 技术指标模块
├── cli.py              # 命令行工具
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
pip install -r backend/requirements.txt
```

### 2. 前端环境

```bash
cd web
npm install
```

### 3. 配置 Ollama（可选，用于 AI 分析）

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

# 启动服务（默认端口 8080）
python -m backend.app
```

### 启动前端

```bash
cd web
npm run dev
```

访问 http://localhost:3000

### 命令行工具

```bash
# 技术分析
python cli.py analyze AAPL

# AI 分析
python cli.py ai-analyze NVDA --model deepseek-v3.1:671b-cloud
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

### 刷新分析（强制重新获取数据）
```
POST /api/refresh-analyze/<symbol>
参数:
  - duration: 数据周期 (默认 '3 M')
  - bar_size: K线周期 (默认 '1 day')
  - model: AI模型 (默认 'deepseek-v3.1:671b-cloud')
```

### 获取技术指标说明
```
GET /api/indicator-info
参数:
  - indicator: 指标名称（可选），不提供则返回所有指标信息
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


## 注意事项

⚠️ **风险提示**
- 本系统仅供学习和研究使用
- 实盘交易有风险，投资需谨慎
- 使用前请充分测试并理解各项功能
- 建议先在模拟盘测试

⚠️ **数据说明**
- 数据来源：Yahoo Finance (yfinance)
- 技术指标基于历史数据计算
- AI分析仅供参考，不构成投资建议
- 数据缓存有效期为当天
- 支持增量更新，提高查询效率

## Docker 部署

### 使用 Docker Compose

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

服务将在 http://localhost:8086 访问

### 环境变量配置

- `OLLAMA_HOST`: Ollama 服务地址（可选，默认 http://localhost:11434）
  - 如果 Ollama 运行在宿主机，使用 `http://host.docker.internal:11434`
  - 如果 Ollama 运行在 Docker 中，使用容器网络地址

## 开发计划

- [ ] 支持更多技术指标
- [ ] 策略回测功能
- [ ] 更多基本面数据展示
- [ ] 移动端 App
- [ ] 数据导出功能

## 许可证

MIT License

## 联系方式

如有问题或建议，欢迎提交 Issue。
