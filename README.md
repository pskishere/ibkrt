# IB Trading Gateway 实盘交易系统

基于 Interactive Brokers API (IBAPI) 开发的实盘交易系统，提供 RESTful API 和交互式命令行界面。

## 功能特性

### 核心功能
- ✅ 实时行情查询
- ✅ 账户信息管理
- ✅ 持仓查询
- ✅ 订单管理（下单、撤单、查询）
- ✅ 历史数据获取
- ✅ 技术分析（13个技术指标）
- ✅ 买卖信号生成
- ✅ 风险评估

### 技术指标
- 移动平均线 (MA5/10/20/50)
- RSI 相对强弱指标
- 布林带 (Bollinger Bands)
- MACD 趋势动量
- KDJ 随机指标
- 威廉指标 (Williams %R)
- ATR 真实波幅
- OBV 能量潮
- 支撑压力位分析
- 趋势强度分析

## 安装部署

### 1. 环境要求
- Python 3.10+
- IB Gateway 或 TWS (Trader Workstation)
- macOS / Linux / Windows

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置 IB Gateway
1. 启动 IB Gateway
2. 配置 API 设置：
   - 端口：4001 (Live) 或 4002 (Paper)
   - 启用 ActiveX 和 Socket 客户端
   - 勾选"Enable API"
   - 添加信任的 IP: 127.0.0.1

## 使用说明

### 启动后端服务
```bash
python3 go.py
```

服务将自动：
- 启动 Flask API 服务 (端口 8080)
- 连接到 IB Gateway (端口 4001)
- 准备接收命令

### 启动交互式命令行
```bash
python3 cli.py
```

### 快捷命令

#### 查询命令
```bash
a              # 账户信息
p              # 持仓
o              # 订单列表
q AAPL         # 实时报价
i AAPL         # 股票详情
an AAPL        # 技术分析 ⭐
hi AAPL        # 历史数据
```

#### 交易命令
```bash
b AAPL 10           # 市价买入 10 股
b AAPL 10 175.5     # 限价 175.5 买入 10 股
s AAPL 10           # 市价卖出 10 股
s AAPL 10 180       # 限价 180 卖出 10 股
x 123               # 撤销订单 123
```

#### 系统命令
```bash
c              # 连接 Gateway
d              # 断开连接
st             # 状态检查
?              # 帮助
clear          # 清屏
exit           # 退出
```

### 技术分析示例

```bash
# 默认分析（1个月日K线）
an AAPL

# 自定义周期分析
an AAPL "3 M" "1 day"     # 3个月日K线
an AAPL "1 W" "1 hour"    # 1周时K线
an AAPL "1 D" "5 mins"    # 1天5分钟线
```

## API 接口

### 端点列表

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/` | API 信息 |
| POST | `/api/connect` | 连接 Gateway |
| POST | `/api/disconnect` | 断开连接 |
| GET | `/api/health` | 健康检查 |
| GET | `/api/account` | 账户信息 |
| GET | `/api/positions` | 持仓列表 |
| GET | `/api/orders` | 订单列表 |
| GET | `/api/executions` | 执行记录 |
| POST | `/api/order` | 下单 |
| DELETE | `/api/order/<id>` | 撤单 |
| GET | `/api/order/<id>` | 查询订单 |
| GET | `/api/quote/<symbol>` | 实时报价 |
| GET | `/api/history/<symbol>` | 历史数据 |
| GET | `/api/info/<symbol>` | 股票详情 |
| GET | `/api/analyze/<symbol>` | 技术分析 |

### API 示例

```bash
# 查询实时报价
curl http://localhost:8080/api/quote/AAPL

# 技术分析
curl "http://localhost:8080/api/analyze/AAPL?duration=1%20M&bar_size=1%20day"

# 下单
curl -X POST http://localhost:8080/api/order \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "action": "BUY",
    "quantity": 10,
    "order_type": "LMT",
    "price": 175.5
  }'
```

## 项目结构

```
schwabgo/
├── go.py              # 后端主程序（Flask API + IBAPI）
├── cli.py             # 交互式命令行客户端
├── requirements.txt   # Python 依赖
├── .gitignore        # Git 忽略文件
└── README.md         # 项目说明
```

## 注意事项

### 安全提示
- ⚠️ 此系统连接真实交易账户，请谨慎操作
- ⚠️ 建议先在模拟账户(Paper Trading)测试
- ⚠️ 不要将 API 密钥提交到 Git 仓库

### 交易风险
- 📊 技术分析仅供参考，不构成投资建议
- 📊 市场有风险，投资需谨慎
- 📊 建议结合基本面分析和市场情绪

### 常见问题

**Q: 无法连接到 IB Gateway？**
- 检查 Gateway 是否启动
- 确认端口号（4001 Live / 4002 Paper）
- 检查 API 设置是否启用

**Q: 订单被拒绝？**
- 检查价格是否接近市价
- 确认账户资金充足
- 查看后端日志获取详细错误

**Q: 技术分析数据不足？**
- 增加历史数据周期（如 "3 M"）
- 查看数据点提示和建议

## 开发者信息

- Python 3.10+
- IBAPI 10.19.2
- Flask 3.0.0

## 许可证

本项目仅供学习和研究使用。

