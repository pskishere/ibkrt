# SchwabGo - 智能美股量化交易分析系统

<div align="center">

**基于 AI 驱动的专业级美股技术分析与交易决策平台**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[功能特性](#功能特性) • [快速开始](#快速开始) • [使用指南](#使用指南) • [API文档](#api文档)

</div>

---

## 📋 目录

- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
- [API文档](#api文档)
- [技术指标说明](#技术指标说明)
- [部署方式](#部署方式)
- [注意事项](#注意事项)

---

## ✨ 功能特性

### 🎯 核心功能

#### 1. **多维度技术分析**
- **20+ 技术指标**：MA、RSI、MACD、KDJ、布林带、ATR、ADX、SAR、SuperTrend、Ichimoku等
- **智能评分系统**：6大维度加权评分（趋势、动量、成交量、波动性、支撑压力、高级指标）
- **自适应权重**：根据股票特性（波动率、趋势强度）动态调整评分权重
- **风险调整评分**：整合风险等级，提供风险调整后的综合评分

#### 2. **AI 交易规划**
- **智能交易规划**：基于关键价位（支撑位、阻力位）生成操作建议
- **动态止损止盈**：根据波动率自动调整ATR倍数
  - 高波动：止损2.5x ATR，止盈4x ATR
  - 中波动：止损2x ATR，止盈3.5x ATR
  - 低波动：止损1.5x ATR，止盈3x ATR
- **风险管理**：可配置账户金额和风险偏好（0.5%-10%）
- **仓位管理**：自动计算建议仓位，支持持仓成本和盈亏追踪

#### 3. **专业回测功能**
- **历史数据回测**：基于指定日期回测交易规划准确性
- **止损止盈模拟**：模拟真实交易中的止损止盈触发
- **交易成本计算**：包含佣金（0.05%）和滑点（0.02%）
- **详细统计分析**：
  - 毛收益 vs 净收益
  - 出场类型（止损/止盈/持有）
  - 持有天数、涨跌天数统计
  - 平均日涨跌幅

#### 4. **可视化图表**
- **TradingView 集成**：专业级 K 线图
- **多指标叠加**：布林带、MA、成交量等指标实时显示
- **响应式设计**：完美适配桌面和移动端

### 🚀 最新优化（v2.0）

#### ✅ 业务合理性增强
1. **仓位管理优化**
   - 移除硬编码账户金额
   - 支持用户自定义账户金额和风险百分比
   - 适用不同资金规模的交易者

2. **止损止盈改进**
   - 根据市场波动性动态调整
   - 分离买入/卖出场景的逻辑
   - 自动计算风险收益比

3. **回测功能升级**
   - 模拟止损止盈真实触发
   - 计算包含交易成本的净收益
   - 提供详细的统计分析

#### ✅ 评分系统优化
1. **波动率评分修复**
   - 适中波动（2-3%）最优，更符合交易实际
   - 过高或过低波动都给予惩罚

2. **ML预测权重调整**
   - 权重从 40% 降至 20%
   - 置信度门槛从 50 提高到 70
   - 避免过度依赖未验证的AI预测

3. **风险调整因子**
   - 低风险股票评分加成（最高15%）
   - 高风险股票评分惩罚（最高30%）
   - 实现真正的"风险调整后收益"评分

4. **自适应权重系统**
   - 高波动股：增加风险权重，降低趋势权重
   - 强趋势股：增加趋势和动量权重
   - 弱趋势股：增加支撑压力位权重

5. **建议阈值细化**
   - 从 5 档增加到 7 档
   - 新增"轻度买入"和"轻度卖出"
   - 提供更精准的操作指引

---

## 🚀 快速开始

### 方式一：Docker Compose（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/schwabgo.git
cd schwabgo

# 2. 启动所有服务
docker-compose up -d

# 3. 访问应用
# 前端: http://localhost:8086
# 后端API: http://localhost:8080
```

### 方式二：本地开发

#### 后端启动

```bash
# 1. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Mac/Linux
# .venv\Scripts\activate   # Windows

# 2. 安装依赖
pip install -r backend/requirements.txt

# 3. 启动后端服务
python -m backend.app
# 服务运行在 http://localhost:8080
```

#### 前端启动

```bash
# 1. 安装依赖
cd web
npm install

# 2. 启动开发服务器
npm run dev
# 服务运行在 http://localhost:5173
```

#### Ollama 配置（可选，用于 AI 分析）

```bash
# 1. 安装 Ollama
# 访问 https://ollama.ai 下载安装

# 2. 拉取推荐模型
ollama pull deepseek-v3.1:671b-cloud

# 3. 启动 Ollama 服务
ollama serve
```

---

## 📖 使用指南

### 1. 技术分析

1. 在顶部输入框输入股票代码（如 `AAPL`、`TSLA`、`NVDA`）
2. 点击「分析」按钮
3. 查看技术指标和评分结果
4. 支持热门股票快速选择

### 2. AI 交易规划

1. 完成技术分析后，点击「交易规划」按钮
2. 配置规划参数：
   - **规划周期**：如"未来2周"
   - **账户金额**：输入实际账户金额（美元）
   - **风险偏好**：选择风险百分比（保守1%，适中2%，激进3-5%）
   - **持仓信息**：如有持仓，输入成本价和数量
   - **日内交易**：是否允许当日买卖
3. 点击「开始规划」，AI 将生成：
   - 关键价位识别（支撑位、阻力位）
   - 具体操作建议（买入/卖出/观望）
   - 止损止盈价位
   - 风险收益比分析
   - 仓位建议

### 3. 回测验证

1. 点击「回测」按钮
2. 选择历史日期作为回测截止点
3. 配置规划参数（同交易规划）
4. 查看回测结果：
   - 预测 vs 实际价格对比
   - 止损止盈模拟结果
   - 毛收益和净收益（扣除成本）
   - 交易统计（持有天数、涨跌天数等）

### 4. 刷新数据

点击「刷新」按钮可强制重新获取最新数据（跳过缓存）。

---

## 📡 API 文档

### 技术分析

```http
GET /api/analyze/<symbol>
```

**查询参数：**
- `duration`: 数据周期，默认 `3 M`（3个月）
- `bar_size`: K线周期，默认 `1 day`
- `model`: AI模型，默认 `deepseek-v3.1:671b-cloud`

**响应示例：**
```json
{
  "success": true,
  "symbol": "AAPL",
  "indicators": {
    "current_price": 178.50,
    "rsi": 62.5,
    "macd": 1.23,
    "score": 45,
    ...
  },
  "signals": {
    "recommendation": "🟢 买入",
    "score": 45,
    "risk_level": "medium",
    ...
  },
  "ai_analysis": "..."
}
```

### 交易规划

```http
POST /api/trading-plan/<symbol>
```

**请求体：**
```json
{
  "planning_period": "未来2周",
  "allow_day_trading": false,
  "current_position_percent": 0,
  "current_position_cost": 0,
  "current_position_quantity": 0,
  "account_value": 100000,
  "risk_percent": 2.0,
  "duration": "3 M",
  "bar_size": "1 day",
  "model": "deepseek-v3.1:671b-cloud"
}
```

### 回测分析

```http
POST /api/backtest-trading-plan/<symbol>
```

**请求体：**
```json
{
  "end_date": "2024-01-15",
  "planning_period": "未来2周",
  "allow_day_trading": false,
  "current_position_percent": 0,
  "account_value": 100000,
  "risk_percent": 2.0,
  "duration": "3 M",
  "bar_size": "1 day",
  "model": "deepseek-v3.1:671b-cloud"
}
```

### 刷新分析

```http
POST /api/refresh-analyze/<symbol>
```

强制重新获取数据，跳过缓存。

---

## 📊 技术指标说明

### 趋势指标

- **MA (Moving Average)**：移动平均线，包括 MA5、MA10、MA20、MA50
- **ADX (Average Directional Index)**：平均趋向指数，衡量趋势强度
- **SuperTrend**：超级趋势指标，判断趋势方向
- **Ichimoku Cloud**：一目均衡表，综合趋势指标

### 动量指标

- **RSI (Relative Strength Index)**：相对强弱指数
  - < 30: 超卖
  - \> 70: 超买
- **MACD**：指数平滑移动平均线
  - MACD线、信号线、柱状图
- **KDJ**：随机指标
- **StochRSI**：随机相对强弱指数

### 波动指标

- **Bollinger Bands**：布林带
  - 上轨、中轨（MA20）、下轨
- **ATR (Average True Range)**：平均真实波幅
- **Volatility**：历史波动率

### 成交量指标

- **Volume Ratio**：成交量比率
- **OBV (On-Balance Volume)**：能量潮指标
- **VWAP (Volume Weighted Average Price)**：成交量加权平均价
- **Volume Profile**：成交量分布

### 支撑压力指标

- **Support/Resistance**：支撑位和压力位
- **Pivot Points**：枢轴点
- **SAR (Parabolic SAR)**：抛物线转向指标
- **Fibonacci Retracement**：斐波那契回撤位

---

## 🐳 部署方式

### Docker Compose 部署

```bash
# 构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 环境变量配置

```bash
# 创建 .env 文件
OLLAMA_HOST=http://localhost:11434
DEFAULT_AI_MODEL=deepseek-v3.1:671b-cloud
```

**注意事项：**
- 如果 Ollama 在宿主机运行：`OLLAMA_HOST=http://host.docker.internal:11434`
- 如果 Ollama 在 Docker 中运行：使用容器网络地址

---

## ⚠️ 注意事项

### 风险提示

- ⚠️ **本系统仅供学习和研究使用**
- ⚠️ **实盘交易有风险，投资需谨慎**
- ⚠️ **AI分析仅供参考，不构成投资建议**
- ⚠️ **使用前请充分测试并理解各项功能**
- ⚠️ **建议先在模拟盘测试**

### 数据说明

- 📊 数据来源：Yahoo Finance (yfinance)
- ⏱️ 数据延迟：15-20分钟
- 💾 数据缓存：有效期为当天
- 🔄 支持增量更新，提高查询效率
- 🚫 部分股票可能因权限限制无法获取

### 评分系统

- 评分范围：-100 到 100
- 建议等级（7档）：
  - \>= 45: 🟢 强烈买入
  - \>= 25: 🟢 买入
  - \>= 5: 🟢 轻度买入
  - -5 ~ 5: ⚪ 中性观望
  - <= -5: 🔴 轻度卖出
  - <= -25: 🔴 卖出
  - <= -45: 🔴 强烈卖出

### 风险管理

- 默认风险百分比：2%（单笔交易）
- 建议风险范围：0.5% - 10%
- 保守型：1%
- 适中型：2%
- 激进型：3-5%

---

## 🎯 性能优化

- ✅ 数据缓存（SQLite）
- ✅ 增量数据更新
- ✅ 异步数据获取
- ✅ 响应式UI设计
- ✅ 移动端优化

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

MIT License

---

## 📞 联系方式

如有问题或建议，欢迎提交 Issue。

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给一个 Star！⭐**

Made with ❤️ by SchwabGo Team

</div>
