# SchwabGo - 智能美股量化交易分析系统

<div align="center">

**基于 AI 驱动的专业级美股技术分析与交易决策平台**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## 📋 目录

- [技术分析](#技术分析)
- [技术指标说明](#技术指标说明)
- [部署方式](#部署方式)

---

## 📊 技术分析

### 使用步骤

1. **输入股票代码**
   - 在顶部输入框输入代码（如 `AAPL`、`TSLA`、`NVDA`）
   - 支持热门股票自动补全
   - 自动转换为大写

2. **查看分析结果**
   - 点击「开始分析」按钮
   - 自动显示：
     * 价格信息和趋势
     * K线图（TradingView）
     * 移动平均线（MA5/10/20/50）
     * 20+ 技术指标
     * 关键价位（支撑/压力位）
     * 交易信号和综合评分
     * 风险等级和建议

3. **AI分析报告**（需配置Ollama）
   - 如果Ollama可用，自动生成AI分析
   - 点击右下角🤖按钮查看详细报告
   - 包含趋势判断、操作建议等

4. **刷新数据**
   - 点击「刷新」按钮强制更新
   - 跳过缓存，获取最新数据

### 指标说明

- 每个指标标题旁有 **?** 图标
- 点击可查看指标的详细说明：
  - 指标含义
  - 计算方法
  - 参考范围
  - 使用方法
- 帮助理解各项技术指标

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

### Docker Compose 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/schwabgo.git
cd schwabgo

# 2. 启动所有服务
docker-compose up -d

# 3. 访问应用
# 前端: http://localhost:8086
# 后端API: http://localhost:8080

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 本地开发部署

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

### Ollama 配置（可选，用于 AI 分析）

```bash
# 1. 安装 Ollama
# 访问 https://ollama.ai 下载安装

# 2. 拉取推荐模型
ollama pull deepseek-v3.1:671b-cloud

# 3. 启动 Ollama 服务
ollama serve
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

## 📄 许可证

MIT License

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给一个 Star！⭐**

Made with ❤️ by SchwabGo Team

</div>
