/**
 * 主页面 - 合并持仓、交易订单、分析功能
 */
import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  Table,
  Button,
  Space,
  Tag,
  Form,
  Input,
  InputNumber,
  Select,
  AutoComplete,
  Row,
  Col,
  Statistic,
  Descriptions,
  Alert,
  Spin,
  message,
  Drawer,
  Tabs,
  Collapse,
  FloatButton,
} from 'antd';
import {
  InboxOutlined,
  ReloadOutlined,
  DollarOutlined,
  ShoppingOutlined,
  CloseCircleOutlined,
  BarChartOutlined,
  RobotOutlined,
  RiseOutlined,
  FallOutlined,
  RightOutlined,
} from '@ant-design/icons';
import {
  getPositions,
  buy,
  sell,
  getOrders,
  cancelOrder,
  analyze,
  getHotStocks,
} from '../services/api';
import './Main.css';

const { TabPane } = Tabs;
const { TextArea } = Input;

const MainPage = () => {
  // 持仓相关状态
  const [positions, setPositions] = useState([]);
  const [positionsLoading, setPositionsLoading] = useState(false);

  // 交易订单相关状态
  const [tradeForm] = Form.useForm();
  const [orders, setOrders] = useState([]);
  const [tradeLoading, setTradeLoading] = useState(false);
  const [orderLoading, setOrderLoading] = useState(false);
  const [tradeDrawerVisible, setTradeDrawerVisible] = useState(false);
  const [tradeDrawerTab, setTradeDrawerTab] = useState('trade-form');

  // 分析相关状态
  const [analyzeForm] = Form.useForm();
  const [analysisResult, setAnalysisResult] = useState(null);
  const [aiAnalysisResult, setAiAnalysisResult] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [aiAnalysisDrawerVisible, setAiAnalysisDrawerVisible] = useState(false);
  
  // 热门股票相关状态
  const [hotStocks, setHotStocks] = useState([]);
  const [stockOptions, setStockOptions] = useState([]);

  /**
   * 加载持仓数据
   */
  const loadPositions = async () => {
    setPositionsLoading(true);
    try {
      const result = await getPositions();
      if (result.success) {
        setPositions(result.data || []);
      } else {
        message.error(result.message || '查询失败');
      }
    } catch (err) {
      message.error(err.message);
    } finally {
      setPositionsLoading(false);
    }
  };

  /**
   * 加载订单列表
   */
  const loadOrders = async () => {
    setOrderLoading(true);
    try {
      const result = await getOrders();
      if (result.success) {
        setOrders(result.data || []);
      } else {
        message.error(result.message || '查询失败');
      }
    } catch (error) {
      message.error(error.message);
    } finally {
      setOrderLoading(false);
    }
  };

  /**
   * 提交订单
   */
  const handleTradeSubmit = async (values) => {
    setTradeLoading(true);
    try {
      const { symbol, action, quantity, orderType, limitPrice } = values;
      const price = orderType === 'LMT' ? limitPrice : null;

      const result = action === 'BUY' 
        ? await buy(symbol, quantity, price)
        : await sell(symbol, quantity, price);

      if (result.success) {
        const orderTypeText = orderType === 'LMT' ? '限价' : '市价';
        const actionText = action === 'BUY' ? '买单' : '卖单';
        message.success(`${actionText}已提交: #${result.order_id} (${orderTypeText})`);
        tradeForm.resetFields();
        await loadOrders();
        await loadPositions();
      } else {
        message.error(result.message || '提交失败');
      }
    } catch (error) {
      message.error(error.message);
    } finally {
      setTradeLoading(false);
    }
  };

  /**
   * 撤销订单
   */
  const handleCancelOrder = async (orderId) => {
    try {
      const result = await cancelOrder(orderId);
      if (result.success) {
        message.success('订单已撤销');
        await loadOrders();
        await loadPositions();
      } else {
        message.error(result.message || '撤销失败');
      }
    } catch (error) {
      message.error(error.message);
    }
  };

  /**
   * 执行分析 - 使用合并后的接口，一次请求同时获取技术分析和AI分析
   */
  const handleAnalyze = async (values) => {
    console.log('handleAnalyze called with values:', values);
    
    if (!values || !values.symbol) {
      message.error('请输入股票代码');
      return;
    }

    setAnalysisLoading(true);
    setAnalysisResult(null);
    setAiAnalysisResult(null);

    try {
      const { symbol, duration, barSize, model } = values;
      const durationValue = duration || '3 M';
      const barSizeValue = barSize || '1 day';
      const modelValue = model || 'deepseek-v3.1:671b-cloud';

      console.log('Starting analysis request:', { symbol, durationValue, barSizeValue, modelValue });

      // 调用统一接口，后端会自动检测 Ollama 并执行AI分析
      const result = await analyze(symbol, durationValue, barSizeValue, modelValue);

      console.log('Analysis result:', result);

      // 处理分析结果
      if (result && result.success) {
        // 设置技术分析结果（包含 indicators 和 signals）
        setAnalysisResult(result);
        
        // 如果有AI分析结果，设置AI分析结果
        if (result.ai_analysis) {
          setAiAnalysisResult(result);
          setAiAnalysisDrawerVisible(true);
        }
      } else {
        const errorMsg = result?.message || '分析失败';
        message.error(errorMsg);
      }
    } catch (error) {
      message.error(error.message || '分析失败');
    } finally {
      setAnalysisLoading(false);
    }
  };

  /**
   * 加载热门股票列表
   */
  const loadHotStocks = async () => {
    try {
      const result = await getHotStocks(30);
      if (result.success && result.stocks) {
        setHotStocks(result.stocks);
        // 转换为 AutoComplete 需要的格式
        const options = result.stocks.map(stock => ({
          value: stock.symbol,
          label: `${stock.symbol} - ${stock.name}`,
        }));
        setStockOptions(options);
      }
    } catch (error) {
      console.error('加载热门股票失败:', error);
      // 失败时不影响使用，只是没有下拉提示
    }
  };

  useEffect(() => {
    // 只在组件挂载时加载一次，不自动刷新
    loadPositions();
    loadOrders();
    loadHotStocks();
  }, []);

  /**
   * 持仓表格列定义
   */
  const positionColumns = [
    {
      title: '代码',
      dataIndex: 'symbol',
      key: 'symbol',
      render: (text) => <strong>{text}</strong>,
    },
    {
      title: '数量',
      dataIndex: 'position',
      key: 'position',
      render: (value) => value?.toFixed(0) || 0,
    },
    {
      title: '市价',
      dataIndex: 'marketPrice',
      key: 'marketPrice',
      render: (value) => `$${value?.toFixed(2) || '0.00'}`,
    },
    {
      title: '市值',
      dataIndex: 'marketValue',
      key: 'marketValue',
      render: (value) => `$${value?.toFixed(2) || '0.00'}`,
    },
    {
      title: '成本',
      dataIndex: 'averageCost',
      key: 'averageCost',
      render: (value) => `$${value?.toFixed(2) || '0.00'}`,
    },
    {
      title: '盈亏',
      dataIndex: 'unrealizedPNL',
      key: 'unrealizedPNL',
      render: (value) => {
        const pnl = value || 0;
        return (
          <Tag color={pnl >= 0 ? 'success' : 'error'}>
            ${pnl.toFixed(2)}
          </Tag>
        );
      },
    },
  ];

  /**
   * 订单表格列定义
   */
  const orderColumns = [
    {
      title: '订单ID',
      dataIndex: 'orderId',
      key: 'orderId',
      render: (id) => `#${id}`,
    },
    {
      title: '代码',
      dataIndex: 'symbol',
      key: 'symbol',
    },
    {
      title: '方向',
      dataIndex: 'action',
      key: 'action',
      render: (action) => (
        <Tag color={action === 'BUY' ? 'green' : 'red'}>
          {action === 'BUY' ? '买入' : '卖出'}
        </Tag>
      ),
    },
    {
      title: '数量',
      dataIndex: 'totalQuantity',
      key: 'totalQuantity',
      render: (qty) => qty?.toFixed(0) || 0,
    },
    {
      title: '类型',
      dataIndex: 'orderType',
      key: 'orderType',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const statusMap = {
          'Filled': { color: 'success', text: '已成交' },
          'Cancelled': { color: 'default', text: '已取消' },
          'Submitted': { color: 'processing', text: '已提交' },
          'PreSubmitted': { color: 'warning', text: '预提交' },
        };
        const config = statusMap[status] || { color: 'default', text: status };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '已成交',
      dataIndex: 'filled',
      key: 'filled',
      render: (filled) => filled?.toFixed(0) || 0,
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        record.status !== 'Filled' && record.status !== 'Cancelled' ? (
          <Button
            type="link"
            danger
            icon={<CloseCircleOutlined />}
            onClick={() => handleCancelOrder(record.orderId)}
          >
            撤销
          </Button>
        ) : null
      ),
    },
  ];

  /**
   * 格式化数值
   */
  const formatValue = (value, decimals = 2) => {
    if (value === undefined || value === null) return 'N/A';
    return typeof value === 'number' ? value.toFixed(decimals) : value;
  };

  /**
   * 获取趋势标签
   */
  const getTrendTag = (direction) => {
    const trendMap = {
      'up': { color: 'success', text: '上涨', icon: <RiseOutlined /> },
      'down': { color: 'error', text: '下跌', icon: <FallOutlined /> },
      'neutral': { color: 'default', text: '震荡', icon: <RightOutlined /> },
    };
    const config = trendMap[direction] || { color: 'default', text: direction, icon: null };
    return (
      <Tag color={config.color}>
        {config.icon} {config.text}
      </Tag>
    );
  };

  /**
   * 获取RSI状态
   */
  const getRSIStatus = (rsi) => {
    if (rsi < 30) return { color: 'success', text: '超卖' };
    if (rsi > 70) return { color: 'error', text: '超买' };
    return { color: 'default', text: '中性' };
  };

  return (
    <div className="main-page">
      {/* 固定顶部区域：持仓和股票输入框 */}
      <div className="fixed-top">
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* 持仓部分 - 可折叠 */}
          <Collapse
            ghost
            items={[
              {
                key: 'positions',
                label: (
                  <span style={{ fontSize: 16, fontWeight: 500 }}>
                    <InboxOutlined style={{ marginRight: 8 }} />
                    持仓 ({positions.length})
                  </span>
                ),
                extra: (
                  <Space onClick={(e) => e.stopPropagation()}>
                    <Button 
                      type="primary" 
                      icon={<DollarOutlined />} 
                      onClick={() => {
                        setTradeDrawerVisible(true);
                        setTradeDrawerTab('trade-form');
                      }}
                    >
                      交易
                    </Button>
                    <Button 
                      icon={<ReloadOutlined />} 
                      onClick={loadPositions} 
                      loading={positionsLoading}
                    >
                      刷新
                    </Button>
                  </Space>
                ),
                children: (
                  <Table
                    columns={positionColumns}
                    dataSource={positions}
                    rowKey={(record, index) => record.symbol || index}
                    loading={positionsLoading}
                    pagination={{ pageSize: 5 }}
                    locale={{ emptyText: '暂无持仓' }}
                    size="small"
                  />
                ),
              },
            ]}
          />

          {/* 股票输入框 */}
          <div>
            <Form
              form={analyzeForm}
              layout="inline"
              onFinish={handleAnalyze}
              initialValues={{
                duration: '3 M',
                barSize: '1 day',
                model: 'deepseek-v3.1:671b-cloud',
              }}
              style={{ marginBottom: 0 }}
            >
              <Form.Item
                label="股票代码"
                name="symbol"
                rules={[{ required: true, message: '请输入股票代码' }]}
                style={{ marginBottom: 0 }}
              >
                <AutoComplete
                  options={stockOptions}
                  placeholder="例如: AAPL"
                  style={{ width: 200 }}
                  filterOption={(inputValue, option) =>
                    option.value.toUpperCase().indexOf(inputValue.toUpperCase()) !== -1 ||
                    option.label.toUpperCase().indexOf(inputValue.toUpperCase()) !== -1
                  }
                  onSelect={(value) => {
                    analyzeForm.setFieldsValue({ symbol: value });
                  }}
                  onChange={(value) => {
                    analyzeForm.setFieldsValue({ symbol: value.toUpperCase() });
                  }}
                />
              </Form.Item>
              <Form.Item style={{ marginBottom: 0 }}>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  loading={analysisLoading}
                >
                  开始分析
                </Button>
              </Form.Item>
            </Form>
          </div>
        </Space>
      </div>

      {/* 分析结果区域 */}
      <div style={{ padding: '0 16px', background: '#fff' }}>

            {analysisLoading && (
              <div style={{ textAlign: 'center', padding: '40px 0' }}>
                <Spin size="large" tip="分析中，请稍候..." />
              </div>
            )}

            {(analysisResult || aiAnalysisResult) && !analysisLoading && (
              <div style={{ marginTop: 24 }}>
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  {/* 技术分析 */}
                  {analysisResult && analysisResult.indicators && (
                    <div>
                        {/* 价格概览 */}
                        <div>
                          <Descriptions 
                            title={
                              <span>
                            <BarChartOutlined style={{ marginRight: 8 }} />
                            价格信息
                              </span>
                            }
                            bordered 
                            column={4}
                            size="middle"
                            layout="vertical"
                            items={[
                              {
                                label: '当前价格',
                                span: 1,
                                children: (
                              <span style={{ fontSize: 20, fontWeight: 600 }}>
                                ${formatValue(analysisResult.indicators.current_price)}
                              </span>
                                ),
                              },
                              {
                                label: '价格变化',
                                span: 1,
                                children: (
                              <Space>
                                {analysisResult.indicators.price_change_pct >= 0 ? (
                                  <RiseOutlined style={{ color: '#3f8600' }} />
                                ) : (
                                  <FallOutlined style={{ color: '#cf1322' }} />
                                )}
                                <span style={{
                                  fontSize: 18,
                                  fontWeight: 600,
                                  color: analysisResult.indicators.price_change_pct >= 0 ? '#3f8600' : '#cf1322',
                                }}>
                                  {formatValue(analysisResult.indicators.price_change_pct)}%
                                </span>
                              </Space>
                                ),
                              },
                              {
                                label: '数据点数',
                                span: 1,
                                children: `${analysisResult.indicators.data_points || 0}根K线`,
                              },
                              {
                                label: '趋势方向',
                                span: 1,
                                children: getTrendTag(analysisResult.indicators.trend_direction),
                              },
                            ]}
                          />
                        </div>

                        {/* 移动平均线 */}
                        {[5, 10, 20, 50].some(p => analysisResult.indicators[`ma${p}`] !== undefined) && (
                          <div style={{ marginTop: 24 }}>
                            <Descriptions 
                              title={
                                <span>
                              <BarChartOutlined style={{ marginRight: 8 }} />
                              移动平均线
                                </span>
                              }
                              bordered 
                              column={4}
                              size="middle"
                              layout="vertical"
                              items={[5, 10, 20, 50]
                                .map((period) => {
                                const key = `ma${period}`;
                                const value = analysisResult.indicators[key];
                                if (value === undefined) return null;
                                const currentPrice = analysisResult.indicators.current_price || 0;
                                const diff = ((currentPrice - value) / value * 100);
                                  return {
                                    label: `MA${period}`,
                                    span: 1,
                                    children: (
                                    <Space>
                                      <span style={{
                                        fontSize: 16,
                                        fontWeight: 600,
                                        color: diff >= 0 ? '#3f8600' : '#cf1322',
                                      }}>
                                        ${formatValue(value)}
                                      </span>
                                      <span style={{
                                        fontSize: 14,
                                        color: diff >= 0 ? '#3f8600' : '#cf1322',
                                      }}>
                                        ({diff >= 0 ? '+' : ''}{diff.toFixed(1)}%)
                                      </span>
                                    </Space>
                                    ),
                                  };
                                })
                                .filter(item => item !== null)}
                            />
                          </div>
                        )}

                        {/* 技术指标 */}
                        <div style={{ marginTop: 24 }}>
                          <Descriptions 
                            title={
                              <span>
                            <BarChartOutlined style={{ marginRight: 8 }} />
                            技术指标
                              </span>
                            }
                            bordered 
                            column={4}
                            size="middle"
                            layout="vertical"
                            items={(() => {
                              const items = [];
                              const indicators = analysisResult.indicators;
                              
                              if (indicators.rsi !== undefined) {
                                items.push({
                                  label: 'RSI(14)',
                                  children: (
                                <Space>
                                  <span style={{ fontSize: 16, fontWeight: 600 }}>
                                        {formatValue(indicators.rsi, 1)}
                                  </span>
                                      <Tag color={getRSIStatus(indicators.rsi).color}>
                                        {getRSIStatus(indicators.rsi).text}
                                  </Tag>
                                </Space>
                                  ),
                                });
                              }
                              
                              if (indicators.macd !== undefined) {
                                items.push({
                                  label: 'MACD',
                                  children: (
                                <Space>
                                      <span>{formatValue(indicators.macd, 3)}</span>
                                      {indicators.macd > indicators.macd_signal ? (
                                    <Tag color="success" size="small">金叉</Tag>
                                  ) : (
                                    <Tag color="error" size="small">死叉</Tag>
                                  )}
                                </Space>
                                  ),
                                });
                              }
                              
                              if (indicators.macd_signal !== undefined) {
                                items.push({
                                  label: 'MACD信号线',
                                  children: formatValue(indicators.macd_signal, 3),
                                });
                              }
                              
                              if (indicators.macd_histogram !== undefined) {
                                items.push({
                                  label: 'MACD柱状图',
                                  children: formatValue(indicators.macd_histogram, 3),
                                });
                              }
                              
                              if (indicators.bb_upper) {
                                items.push({
                                  label: '布林带上轨',
                                  children: `$${formatValue(indicators.bb_upper)}`,
                                });
                              }
                              
                              if (indicators.bb_middle) {
                                items.push({
                                  label: '布林带中轨',
                                  children: `$${formatValue(indicators.bb_middle)}`,
                                });
                              }
                              
                              if (indicators.bb_lower) {
                                items.push({
                                  label: '布林带下轨',
                                  children: `$${formatValue(indicators.bb_lower)}`,
                                });
                              }
                              
                              if (indicators.volume_ratio !== undefined) {
                                items.push({
                                  label: '成交量比率',
                                  children: (
                                <Space>
                                  <span style={{ fontSize: 16, fontWeight: 600 }}>
                                        {formatValue(indicators.volume_ratio, 2)}x
                                  </span>
                                      {indicators.volume_ratio > 1.5 ? (
                                    <Tag color="orange">放量</Tag>
                                      ) : indicators.volume_ratio < 0.7 ? (
                                    <Tag color="default">缩量</Tag>
                                  ) : (
                                    <Tag color="success">正常</Tag>
                                  )}
                                </Space>
                                  ),
                                });
                              }
                              
                              if (indicators.volatility_20 !== undefined) {
                                items.push({
                                  label: '波动率',
                                  children: (
                                <Space>
                                      <span>{formatValue(indicators.volatility_20)}%</span>
                                      {indicators.volatility_20 > 5 ? (
                                    <Tag color="error" size="small">极高</Tag>
                                      ) : indicators.volatility_20 > 3 ? (
                                    <Tag color="warning" size="small">高</Tag>
                                      ) : indicators.volatility_20 > 2 ? (
                                    <Tag color="default" size="small">中</Tag>
                                  ) : (
                                    <Tag color="success" size="small">低</Tag>
                                  )}
                                </Space>
                                  ),
                                });
                              }
                              
                              if (indicators.atr !== undefined) {
                                items.push({
                                  label: 'ATR',
                                  children: `$${formatValue(indicators.atr)} (${formatValue(indicators.atr_percent, 1)}%)`,
                                });
                              }
                              
                              if (indicators.kdj_k !== undefined) {
                                items.push({
                                  label: 'KDJ',
                                  children: (
                                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                                  <div>
                                        K={formatValue(indicators.kdj_k, 1)} D={formatValue(indicators.kdj_d, 1)} J={formatValue(indicators.kdj_j, 1)}
                                  </div>
                                  <Space>
                                        {indicators.kdj_j < 20 ? (
                                      <Tag color="success" size="small">超卖</Tag>
                                        ) : indicators.kdj_j > 80 ? (
                                      <Tag color="error" size="small">超买</Tag>
                                    ) : (
                                      <Tag color="default" size="small">中性</Tag>
                                    )}
                                        {indicators.kdj_k > indicators.kdj_d ? (
                                      <Tag color="success" size="small">多头</Tag>
                                    ) : (
                                      <Tag color="error" size="small">空头</Tag>
                                    )}
                                  </Space>
                                </Space>
                                  ),
                                });
                              }
                              
                              if (indicators.williams_r !== undefined) {
                                items.push({
                                  label: '威廉%R',
                                  children: (
                                <Space>
                                      <span>{formatValue(indicators.williams_r, 1)}</span>
                                  <Tag 
                                    color={
                                          indicators.williams_r < -80 ? 'success' : 
                                          indicators.williams_r > -20 ? 'error' : 'default'
                                    }
                                    size="small"
                                  >
                                        {indicators.williams_r < -80 ? '超卖' : 
                                         indicators.williams_r > -20 ? '超买' : '中性'}
                                  </Tag>
                                </Space>
                                  ),
                                });
                              }
                              
                              if (indicators.obv_trend) {
                                items.push({
                                  label: 'OBV趋势',
                                  children: indicators.obv_trend === 'up' ? (
                                    indicators.price_change_pct > 0 ? (
                                    <Tag color="success">量价齐升</Tag>
                                  ) : (
                                    <Tag color="warning">量价背离(可能见底)</Tag>
                                  )
                                  ) : indicators.obv_trend === 'down' ? (
                                    indicators.price_change_pct < 0 ? (
                                    <Tag color="error">量价齐跌</Tag>
                                  ) : (
                                    <Tag color="warning">量价背离(可能见顶)</Tag>
                                  )
                                ) : (
                                  <Tag color="default">平稳</Tag>
                                  ),
                                });
                              }
                              
                              if (indicators.trend_strength !== undefined) {
                                items.push({
                                  label: '趋势强度',
                                  children: (
                                <Space>
                                      {getTrendTag(indicators.trend_direction)}
                                  <span style={{ fontSize: 16, fontWeight: 600 }}>
                                        {formatValue(indicators.trend_strength, 0)}%
                                  </span>
                                      {indicators.trend_strength > 50 ? (
                                    <Tag color="success" size="small">强</Tag>
                                      ) : indicators.trend_strength > 25 ? (
                                    <Tag color="default" size="small">中</Tag>
                                  ) : (
                                    <Tag color="warning" size="small">弱</Tag>
                                  )}
                                </Space>
                                  ),
                                });
                              }
                              
                              if (indicators.consecutive_up_days > 0 || indicators.consecutive_down_days > 0) {
                                items.push({
                                  label: '连续涨跌',
                                  span: 4,
                                  children: (
                                <Space>
                                      {indicators.consecutive_up_days > 0 ? (
                                    <>
                                      <RiseOutlined style={{ color: '#3f8600' }} />
                                          <span>连续{indicators.consecutive_up_days}天上涨</span>
                                          {indicators.consecutive_up_days >= 5 && (
                                        <Tag color="warning" size="small">注意</Tag>
                                      )}
                                    </>
                                  ) : (
                                    <>
                                      <FallOutlined style={{ color: '#cf1322' }} />
                                          <span>连续{indicators.consecutive_down_days}天下跌</span>
                                          {indicators.consecutive_down_days >= 5 && (
                                        <Tag color="success" size="small">关注</Tag>
                                      )}
                                    </>
                                  )}
                                </Space>
                                  ),
                                });
                              }
                              
                              return items;
                            })()}
                          />
                        </div>

                        {/* 基本面数据 */}
                        {analysisResult.indicators.fundamental_data && 
                         typeof analysisResult.indicators.fundamental_data === 'object' &&
                         !analysisResult.indicators.fundamental_data.raw_xml &&
                         Object.keys(analysisResult.indicators.fundamental_data).length > 0 && (
                          <div style={{ marginTop: 24 }}>
                            <Descriptions 
                              title={
                                <span>
                                  <BarChartOutlined style={{ marginRight: 8 }} />
                                  基本面数据
                                </span>
                              }
                              bordered 
                              column={4}
                              size="middle"
                              layout="vertical"
                              items={(() => {
                                const items = [];
                                const fd = analysisResult.indicators.fundamental_data;
                                
                                // 基本信息
                                if (fd.CompanyName) {
                                  items.push({
                                    label: '公司名称',
                                    span: 2,
                                    children: fd.CompanyName,
                                  });
                                }
                                
                                if (fd.Exchange) {
                                  items.push({
                                    label: '交易所',
                                    span: 1,
                                    children: fd.Exchange,
                                  });
                                }
                                
                                if (fd.Employees) {
                                  items.push({
                                    label: '员工数',
                                    span: 1,
                                    children: `${fd.Employees}人`,
                                  });
                                }
                                
                                if (fd.SharesOutstanding) {
                                  const shares = parseFloat(fd.SharesOutstanding);
                                  let sharesText = '';
                                  if (shares >= 1e9) {
                                    sharesText = `${(shares / 1e9).toFixed(2)}B`;
                                  } else if (shares >= 1e6) {
                                    sharesText = `${(shares / 1e6).toFixed(2)}M`;
                                  } else {
                                    sharesText = shares.toFixed(0);
                                  }
                                  items.push({
                                    label: '流通股数',
                                    span: 1,
                                    children: sharesText,
                                  });
                                }
                                
                                // 市值与价格
                                if (fd.MarketCap) {
                                  const mcap = parseFloat(fd.MarketCap);
                                  let mcapText = '';
                                  if (mcap >= 1e12) {
                                    mcapText = `$${(mcap / 1e12).toFixed(2)}T`;
                                  } else if (mcap >= 1e9) {
                                    mcapText = `$${(mcap / 1e9).toFixed(2)}B`;
                                  } else if (mcap >= 1e6) {
                                    mcapText = `$${(mcap / 1e6).toFixed(2)}M`;
                                  } else {
                                    mcapText = `$${mcap.toFixed(2)}`;
                                  }
                                  items.push({
                                    label: '市值',
                                    span: 1,
                                    children: mcapText,
                                  });
                                }
                                
                                if (fd.Price) {
                                  items.push({
                                    label: '当前价',
                                    span: 1,
                                    children: `$${formatValue(fd.Price, 2)}`,
                                  });
                                }
                                
                                if (fd['52WeekHigh'] && fd['52WeekLow']) {
                                  items.push({
                                    label: '52周区间',
                                    span: 2,
                                    children: `$${formatValue(fd['52WeekLow'], 2)} - $${formatValue(fd['52WeekHigh'], 2)}`,
                                  });
                                }
                                
                                // 财务指标
                                if (fd.RevenueTTM) {
                                  const revenue = parseFloat(fd.RevenueTTM);
                                  let revenueText = '';
                                  if (revenue >= 1e9) {
                                    revenueText = `$${(revenue / 1e9).toFixed(2)}B`;
                                  } else if (revenue >= 1e6) {
                                    revenueText = `$${(revenue / 1e6).toFixed(2)}M`;
                                  } else {
                                    revenueText = `$${revenue.toFixed(2)}`;
                                  }
                                  items.push({
                                    label: '营收(TTM)',
                                    span: 1,
                                    children: revenueText,
                                  });
                                }
                                
                                if (fd.NetIncomeTTM) {
                                  const income = parseFloat(fd.NetIncomeTTM);
                                  let incomeText = '';
                                  if (income >= 1e9) {
                                    incomeText = `$${(income / 1e9).toFixed(2)}B`;
                                  } else if (income >= 1e6) {
                                    incomeText = `$${(income / 1e6).toFixed(2)}M`;
                                  } else {
                                    incomeText = `$${income.toFixed(2)}`;
                                  }
                                  items.push({
                                    label: '净利润(TTM)',
                                    span: 1,
                                    children: incomeText,
                                  });
                                }
                                
                                if (fd.EBITDATTM) {
                                  const ebitda = parseFloat(fd.EBITDATTM);
                                  let ebitdaText = '';
                                  if (ebitda >= 1e9) {
                                    ebitdaText = `$${(ebitda / 1e9).toFixed(2)}B`;
                                  } else if (ebitda >= 1e6) {
                                    ebitdaText = `$${(ebitda / 1e6).toFixed(2)}M`;
                                  } else {
                                    ebitdaText = `$${ebitda.toFixed(2)}`;
                                  }
                                  items.push({
                                    label: 'EBITDA(TTM)',
                                    span: 1,
                                    children: ebitdaText,
                                  });
                                }
                                
                                if (fd.ProfitMargin) {
                                  items.push({
                                    label: '利润率',
                                    span: 1,
                                    children: `${formatValue(parseFloat(fd.ProfitMargin) * 100, 2)}%`,
                                  });
                                }
                                
                                if (fd.GrossMargin) {
                                  items.push({
                                    label: '毛利率',
                                    span: 1,
                                    children: `${formatValue(parseFloat(fd.GrossMargin) * 100, 2)}%`,
                                  });
                                }
                                
                                // 每股数据
                                if (fd.EPS) {
                                  items.push({
                                    label: '每股收益(EPS)',
                                    span: 1,
                                    children: `$${formatValue(fd.EPS, 2)}`,
                                  });
                                }
                                
                                if (fd.BookValuePerShare) {
                                  items.push({
                                    label: '每股净资产',
                                    span: 1,
                                    children: `$${formatValue(fd.BookValuePerShare, 2)}`,
                                  });
                                }
                                
                                if (fd.CashPerShare) {
                                  items.push({
                                    label: '每股现金',
                                    span: 1,
                                    children: `$${formatValue(fd.CashPerShare, 2)}`,
                                  });
                                }
                                
                                if (fd.DividendPerShare) {
                                  items.push({
                                    label: '每股股息',
                                    span: 1,
                                    children: `$${formatValue(fd.DividendPerShare, 3)}`,
                                  });
                                }
                                
                                // 估值指标
                                if (fd.PE) {
                                  const pe = parseFloat(fd.PE);
                                  items.push({
                                    label: '市盈率(PE)',
                                    span: 1,
                                    children: (
                                      <Space>
                                        <span>{formatValue(pe, 2)}</span>
                                        {pe < 15 ? (
                                          <Tag color="success" size="small">低估</Tag>
                                        ) : pe > 25 ? (
                                          <Tag color="warning" size="small">高估</Tag>
                                        ) : (
                                          <Tag color="default" size="small">合理</Tag>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }
                                
                                if (fd.PriceToBook) {
                                  const pb = parseFloat(fd.PriceToBook);
                                  items.push({
                                    label: '市净率(PB)',
                                    span: 1,
                                    children: (
                                      <Space>
                                        <span>{formatValue(pb, 2)}</span>
                                        {pb < 1 ? (
                                          <Tag color="success" size="small">低估</Tag>
                                        ) : pb > 3 ? (
                                          <Tag color="warning" size="small">高估</Tag>
                                        ) : (
                                          <Tag color="default" size="small">合理</Tag>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }
                                
                                if (fd.ROE) {
                                  const roe = parseFloat(fd.ROE) * 100;
                                  items.push({
                                    label: '净资产收益率(ROE)',
                                    span: 1,
                                    children: (
                                      <Space>
                                        <span>{formatValue(roe, 2)}%</span>
                                        {roe > 15 ? (
                                          <Tag color="success" size="small">优秀</Tag>
                                        ) : roe > 10 ? (
                                          <Tag color="default" size="small">良好</Tag>
                                        ) : (
                                          <Tag color="warning" size="small">一般</Tag>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }
                                
                                // 分析师预测
                                if (fd.TargetPrice) {
                                  const target = parseFloat(fd.TargetPrice);
                                  const currentPrice = parseFloat(fd.Price || analysisResult.indicators.current_price || 0);
                                  const upside = currentPrice > 0 ? ((target - currentPrice) / currentPrice * 100) : 0;
                                  items.push({
                                    label: '目标价',
                                    span: 1,
                                    children: (
                                      <Space>
                                        <span>${formatValue(target, 2)}</span>
                                        {upside > 0 ? (
                                          <Tag color="success" size="small">+{formatValue(upside, 1)}%</Tag>
                                        ) : (
                                          <Tag color="error" size="small">{formatValue(upside, 1)}%</Tag>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }
                                
                                if (fd.ConsensusRecommendation) {
                                  const consensus = fd.ConsensusRecommendation;
                                  const consensusMap = {
                                    '1': { text: '强烈买入', color: 'success' },
                                    '2': { text: '买入', color: 'success' },
                                    '3': { text: '持有', color: 'default' },
                                    '4': { text: '卖出', color: 'error' },
                                    '5': { text: '强烈卖出', color: 'error' },
                                  };
                                  const config = consensusMap[consensus] || { text: consensus, color: 'default' };
                                  items.push({
                                    label: '共识评级',
                                    span: 1,
                                    children: <Tag color={config.color}>{config.text}</Tag>,
                                  });
                                }
                                
                                if (fd.ProjectedEPS) {
                                  items.push({
                                    label: '预测EPS',
                                    span: 1,
                                    children: `$${formatValue(fd.ProjectedEPS, 2)}`,
                                  });
                                }
                                
                                if (fd.ProjectedGrowthRate) {
                                  items.push({
                                    label: '预测增长率',
                                    span: 1,
                                    children: `${formatValue(parseFloat(fd.ProjectedGrowthRate) * 100, 2)}%`,
                                  });
                                }
                                
                                return items;
                              })()}
                            />
                        </div>
                        )}

                        {/* 缠论分析 */}
                        {(analysisResult.indicators.fractals || analysisResult.indicators.strokes || analysisResult.indicators.segments || analysisResult.indicators.central_banks) && (
                          <div style={{ marginTop: 24 }}>
                            <Descriptions 
                              title={
                                <span>
                                  <BarChartOutlined style={{ marginRight: 8 }} />
                                  缠论分析
                                </span>
                              }
                              bordered 
                              column={4}
                              size="middle"
                              layout="vertical"
                              items={(() => {
                                const items = [];
                                const indicators = analysisResult.indicators;
                                
                                if (indicators.trend_type) {
                                  items.push({
                                    label: '走势类型',
                                    span: 1,
                                    children: (
                                      <Tag color={
                                        indicators.trend_type === 'up' ? 'success' :
                                        indicators.trend_type === 'down' ? 'error' : 'default'
                                      }>
                                        {indicators.trend_type === 'up' ? '上涨' :
                                         indicators.trend_type === 'down' ? '下跌' : '盘整'}
                                      </Tag>
                                    ),
                                  });
                                }
                                
                                if (indicators.fractal_count) {
                                  items.push({
                                    label: '分型数量',
                                    span: 1,
                                    children: (
                                      <Space>
                                        <span>顶分型: {indicators.fractal_count.top || 0}</span>
                                        <span>底分型: {indicators.fractal_count.bottom || 0}</span>
                                      </Space>
                                    ),
                                  });
                                }
                                
                                if (indicators.stroke_count !== undefined) {
                                  items.push({
                                    label: '笔数量',
                                    span: 1,
                                    children: indicators.stroke_count,
                                  });
                                }
                                
                                if (indicators.segment_count !== undefined) {
                                  items.push({
                                    label: '线段数量',
                                    span: 1,
                                    children: indicators.segment_count,
                                  });
                                }
                                
                                if (indicators.central_bank_count !== undefined) {
                                  items.push({
                                    label: '中枢数量',
                                    span: 1,
                                    children: indicators.central_bank_count,
                                  });
                                }
                                
                                if (indicators.latest_stroke) {
                                  items.push({
                                    label: '最新笔',
                                    span: 2,
                                    children: (
                                      <Space>
                                        <Tag color={indicators.latest_stroke.type === 'up' ? 'success' : 'error'}>
                                          {indicators.latest_stroke.type === 'up' ? '上涨笔' : '下跌笔'}
                                        </Tag>
                                        <span>
                                          ${formatValue(indicators.latest_stroke.start_price)} → ${formatValue(indicators.latest_stroke.end_price)}
                                        </span>
                                        <span style={{
                                          color: indicators.latest_stroke.price_change_pct >= 0 ? '#3f8600' : '#cf1322'
                                        }}>
                                          ({indicators.latest_stroke.price_change_pct >= 0 ? '+' : ''}{formatValue(indicators.latest_stroke.price_change_pct)}%)
                                        </span>
                                      </Space>
                                    ),
                                  });
                                }
                                
                                if (indicators.latest_segment) {
                                  items.push({
                                    label: '最新线段',
                                    span: 2,
                                    children: (
                                      <Space>
                                        <Tag color={indicators.latest_segment.type === 'up' ? 'success' : 'error'}>
                                          {indicators.latest_segment.type === 'up' ? '上涨线段' : '下跌线段'}
                                        </Tag>
                                        <span>
                                          ${formatValue(indicators.latest_segment.start_price)} → ${formatValue(indicators.latest_segment.end_price)}
                                        </span>
                                        <span style={{
                                          color: indicators.latest_segment.price_change_pct >= 0 ? '#3f8600' : '#cf1322'
                                        }}>
                                          ({indicators.latest_segment.price_change_pct >= 0 ? '+' : ''}{formatValue(indicators.latest_segment.price_change_pct)}%)
                                        </span>
                                      </Space>
                                    ),
                                  });
                                }
                                
                                if (indicators.latest_central_bank) {
                                  items.push({
                                    label: '最新中枢',
                                    span: 4,
                                    children: (
                                      <Space>
                                        <span>上沿: <strong>${formatValue(indicators.latest_central_bank.high)}</strong></span>
                                        <span>下沿: <strong>${formatValue(indicators.latest_central_bank.low)}</strong></span>
                                        <span>中心: <strong>${formatValue(indicators.latest_central_bank.center)}</strong></span>
                                        <span>宽度: {formatValue(indicators.latest_central_bank.width_pct, 2)}%</span>
                                        <Tag color={
                                          indicators.latest_central_bank.position === 'above' ? 'success' :
                                          indicators.latest_central_bank.position === 'below' ? 'error' : 'default'
                                        }>
                                          {indicators.latest_central_bank.position === 'above' ? '上方' :
                                           indicators.latest_central_bank.position === 'below' ? '下方' : '中枢内'}
                                        </Tag>
                                      </Space>
                                    ),
                                  });
                                }
                                
                                if (indicators.latest_top_fractal) {
                                  items.push({
                                    label: '最新顶分型',
                                    span: 2,
                                    children: (
                                      <Space>
                                        <span style={{ fontSize: 16, fontWeight: 600, color: '#fa8c16' }}>
                                          ${formatValue(indicators.latest_top_fractal.price)}
                                        </span>
                                        <span style={{ color: '#666' }}>
                                          距离: {formatValue(indicators.latest_top_fractal.distance_pct, 2)}%
                                        </span>
                                      </Space>
                                    ),
                                  });
                                }
                                
                                if (indicators.latest_bottom_fractal) {
                                  items.push({
                                    label: '最新底分型',
                                    span: 2,
                                    children: (
                                      <Space>
                                        <span style={{ fontSize: 16, fontWeight: 600, color: '#52c41a' }}>
                                          ${formatValue(indicators.latest_bottom_fractal.price)}
                                        </span>
                                        <span style={{ color: '#666' }}>
                                          距离: {formatValue(indicators.latest_bottom_fractal.distance_pct, 2)}%
                                        </span>
                                      </Space>
                                    ),
                                  });
                                }
                                
                                if (indicators.trading_points) {
                                  items.push({
                                    label: '买卖点',
                                    span: 4,
                                    children: (
                                      <Space wrap>
                                        {indicators.trading_points.buy_points && indicators.trading_points.buy_points.length > 0 && (
                                          <>
                                            {indicators.trading_points.buy_points.map((point, index) => (
                                              <Tag key={`buy-${index}`} color="success">
                                                {point.type}: ${formatValue(point.price)}
                                              </Tag>
                                            ))}
                                          </>
                                        )}
                                        {indicators.trading_points.sell_points && indicators.trading_points.sell_points.length > 0 && (
                                          <>
                                            {indicators.trading_points.sell_points.map((point, index) => (
                                              <Tag key={`sell-${index}`} color="error">
                                                {point.type}: ${formatValue(point.price)}
                                              </Tag>
                                            ))}
                                          </>
                                        )}
                                        {(!indicators.trading_points.buy_points || indicators.trading_points.buy_points.length === 0) &&
                                         (!indicators.trading_points.sell_points || indicators.trading_points.sell_points.length === 0) && (
                                          <span style={{ color: '#999' }}>暂无买卖点信号</span>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }
                                
                                return items;
                              })()}
                            />
                        </div>
                        )}

                        {/* 关键价位 */}
                        {(analysisResult.indicators.pivot || analysisResult.indicators.pivot_r1 || analysisResult.indicators.resistance_20d_high) && (
                          <div style={{ marginTop: 24 }}>
                            <Descriptions 
                              title={
                                <span>
                              <BarChartOutlined style={{ marginRight: 8 }} />
                              关键价位
                                </span>
                              }
                            bordered 
                            column={4}
                            size="middle"
                              layout="vertical"
                              items={(() => {
                                const items = [];
                                const indicators = analysisResult.indicators;
                                
                                if (indicators.pivot) {
                                  items.push({
                                    label: '枢轴点',
                                    children: (
                                  <span style={{ fontSize: 16, fontWeight: 600 }}>
                                        ${formatValue(indicators.pivot)}
                                  </span>
                                    ),
                                  });
                                }
                                
                                if (indicators.pivot_r1) {
                                  items.push({
                                    label: '压力位R1',
                                    children: (
                                  <span style={{ fontSize: 16, fontWeight: 600, color: '#fa8c16' }}>
                                        ${formatValue(indicators.pivot_r1)}
                                  </span>
                                    ),
                                  });
                                }
                                
                                if (indicators.pivot_r2) {
                                  items.push({
                                    label: '压力位R2',
                                    children: (
                                  <span style={{ fontSize: 16, fontWeight: 600, color: '#fa8c16' }}>
                                        ${formatValue(indicators.pivot_r2)}
                                  </span>
                                    ),
                                  });
                                }
                                
                                if (indicators.pivot_r3) {
                                  items.push({
                                    label: '压力位R3',
                                    children: (
                                  <span style={{ fontSize: 16, fontWeight: 600, color: '#fa8c16' }}>
                                        ${formatValue(indicators.pivot_r3)}
                                  </span>
                                    ),
                                  });
                                }
                                
                                if (indicators.pivot_s1) {
                                  items.push({
                                    label: '支撑位S1',
                                    children: (
                                  <span style={{ fontSize: 16, fontWeight: 600, color: '#52c41a' }}>
                                        ${formatValue(indicators.pivot_s1)}
                                  </span>
                                    ),
                                  });
                                }
                                
                                if (indicators.pivot_s2) {
                                  items.push({
                                    label: '支撑位S2',
                                    children: (
                                  <span style={{ fontSize: 16, fontWeight: 600, color: '#52c41a' }}>
                                        ${formatValue(indicators.pivot_s2)}
                                  </span>
                                    ),
                                  });
                                }
                                
                                if (indicators.pivot_s3) {
                                  items.push({
                                    label: '支撑位S3',
                                    children: (
                                  <span style={{ fontSize: 16, fontWeight: 600, color: '#52c41a' }}>
                                        ${formatValue(indicators.pivot_s3)}
                                  </span>
                                    ),
                                  });
                                }
                                
                                if (indicators.resistance_20d_high) {
                                  items.push({
                                    label: '20日高点',
                                    children: (
                                  <span style={{ fontSize: 16, fontWeight: 600, color: '#fa8c16' }}>
                                        ${formatValue(indicators.resistance_20d_high)}
                                  </span>
                                    ),
                                  });
                                }
                                
                                if (indicators.support_20d_low) {
                                  items.push({
                                    label: '20日低点',
                                    children: (
                                  <span style={{ fontSize: 16, fontWeight: 600, color: '#52c41a' }}>
                                        ${formatValue(indicators.support_20d_low)}
                                  </span>
                                    ),
                                  });
                                }
                                
                                return items;
                              })()}
                            />
                          </div>
                        )}

                        {/* 交易信号 */}
                        {analysisResult.signals && (
                          <div style={{ marginTop: 24 }}>
                            <Descriptions 
                              title={
                                <span>
                              <BarChartOutlined style={{ marginRight: 8 }} />
                              交易信号
                                </span>
                              }
                              bordered 
                              column={{ xxl: 3, xl: 3, lg: 2, md: 2, sm: 1, xs: 1 }} 
                              size="middle"
                              layout="vertical"
                              items={(() => {
                                const items = [];
                                const signals = analysisResult.signals;
                                const indicators = analysisResult.indicators;
                                
                                items.push({
                                  label: '综合评分',
                                  span: 1,
                                  children: (
                                <div style={{ textAlign: 'center' }}>
                                  <Space align="baseline">
                                    <span style={{
                                      fontSize: 16,
                                      fontWeight: 600,
                                          color: (signals.score || 0) >= 50 ? '#3f8600' : '#cf1322',
                                    }}>
                                          {signals.score || 0}
                                    </span>
                                    <span style={{
                                      fontSize: 16,
                                      fontWeight: 600,
                                          color: (signals.score || 0) >= 50 ? '#3f8600' : '#cf1322',
                                    }}>
                                      /100
                                    </span>
                                  </Space>
                                </div>
                                  ),
                                });
                                
                                items.push({
                                  label: '交易建议',
                                  span: 1,
                                  children: (
                                <span style={{ fontSize: 16, fontWeight: 600 }}>
                                      {signals.recommendation || 'N/A'}
                                </span>
                                  ),
                                });
                                
                                if (signals.risk) {
                                  const riskLevel = signals.risk.level || 'unknown';
                                    const riskMap = {
                                      'very_low': { color: 'success', text: '很低风险' },
                                      'low': { color: 'success', text: '低风险' },
                                      'medium': { color: 'warning', text: '中等风险' },
                                      'high': { color: 'error', text: '高风险' },
                                      'very_high': { color: 'error', text: '极高风险' },
                                    };
                                    const config = riskMap[riskLevel] || { color: 'default', text: '未知' };
                                  items.push({
                                    label: '风险等级',
                                    span: 1,
                                    children: <Tag color={config.color}>{config.text}</Tag>,
                                  });
                                }
                                
                                if (signals.stop_loss) {
                                  items.push({
                                    label: '建议止损',
                                    children: (
                                  <span style={{ fontSize: 16, fontWeight: 600, color: '#cf1322' }}>
                                        ${formatValue(signals.stop_loss)}
                                  </span>
                                    ),
                                  });
                                }
                                
                                if (signals.take_profit) {
                                  items.push({
                                    label: '建议止盈',
                                    children: (
                                  <span style={{ fontSize: 16, fontWeight: 600, color: '#3f8600' }}>
                                        ${formatValue(signals.take_profit)}
                                  </span>
                                    ),
                                  });
                                }
                                
                                if (signals.stop_loss && signals.take_profit && indicators.current_price > 0) {
                                  items.push({
                                    label: '风险回报比',
                                    span: 3,
                                    children: (
                                  <Tag color="blue" style={{ fontSize: 14 }}>
                                    1:{formatValue(
                                      Math.abs(
                                            ((signals.take_profit - indicators.current_price) / indicators.current_price) /
                                            ((signals.stop_loss - indicators.current_price) / indicators.current_price)
                                      ), 1
                                    )}
                                  </Tag>
                                    ),
                                  });
                                }
                                
                                if (signals.signals && signals.signals.length > 0) {
                                  items.push({
                                    label: '信号列表',
                                    span: 3,
                                    children: (
                                  <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                                        {signals.signals.map((signal, index) => (
                                      <li key={index} style={{ marginBottom: 4, fontSize: 14 }}>{signal}</li>
                                    ))}
                                  </ul>
                                    ),
                                  });
                                }
                                
                                return items;
                              })()}
                            />
                          </div>
                        )}
                    </div>
                  )}

                </Space>
              </div>
            )}
      </div>

      {/* 交易抽屉 */}
      <Drawer
        title={
          <span>
            <DollarOutlined style={{ marginRight: 8 }} />
            交易
          </span>
        }
        placement="right"
        width={600}
        onClose={() => setTradeDrawerVisible(false)}
        open={tradeDrawerVisible}
      >
        <Tabs activeKey={tradeDrawerTab} onChange={setTradeDrawerTab}>
          <TabPane
            tab={
              <span>
                <DollarOutlined />
                下单
              </span>
            }
            key="trade-form"
          >
            <Form
              form={tradeForm}
              layout="vertical"
              onFinish={async (values) => {
                await handleTradeSubmit(values);
                setTradeDrawerTab('orders');
              }}
              initialValues={{
                action: 'BUY',
                orderType: 'MKT',
              }}
            >
              <Form.Item
                label="交易方向"
                name="action"
                rules={[{ required: true, message: '请选择交易方向' }]}
              >
                <Select>
                  <Select.Option value="BUY">买入</Select.Option>
                  <Select.Option value="SELL">卖出</Select.Option>
                </Select>
              </Form.Item>

              <Form.Item
                label="股票代码"
                name="symbol"
                rules={[{ required: true, message: '请输入股票代码' }]}
              >
                <Input placeholder="例如: AAPL" style={{ textTransform: 'uppercase' }} />
              </Form.Item>

              <Form.Item
                label="数量"
                name="quantity"
                rules={[{ required: true, message: '请输入数量' }]}
              >
                <InputNumber
                  min={1}
                  step={1}
                  placeholder="例如: 10"
                  style={{ width: '100%' }}
                />
              </Form.Item>

              <Form.Item
                label="订单类型"
                name="orderType"
                rules={[{ required: true, message: '请选择订单类型' }]}
              >
                <Select>
                  <Select.Option value="MKT">市价单</Select.Option>
                  <Select.Option value="LMT">限价单</Select.Option>
                </Select>
              </Form.Item>

              <Form.Item
                noStyle
                shouldUpdate={(prevValues, currentValues) =>
                  prevValues.orderType !== currentValues.orderType
                }
              >
                {({ getFieldValue }) =>
                  getFieldValue('orderType') === 'LMT' ? (
                    <Form.Item
                      label="限价"
                      name="limitPrice"
                      rules={[{ required: true, message: '请输入限价' }]}
                    >
                      <InputNumber
                        min={0}
                        step={0.01}
                        placeholder="例如: 175.50"
                        style={{ width: '100%' }}
                      />
                    </Form.Item>
                  ) : null
                }
              </Form.Item>

              <Form.Item>
                <Button type="primary" htmlType="submit" loading={tradeLoading} block>
                  提交订单
                </Button>
              </Form.Item>
            </Form>
          </TabPane>

          <TabPane
            tab={
              <span>
                <ShoppingOutlined />
                订单列表
              </span>
            }
            key="orders"
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Button icon={<ReloadOutlined />} onClick={loadOrders} loading={orderLoading}>
                  刷新
                </Button>
                <span style={{ marginLeft: 16, color: '#666' }}>
                  共 {orders.length} 个订单
                </span>
              </div>
              <Table
                columns={orderColumns}
                dataSource={orders}
                rowKey="orderId"
                loading={orderLoading}
                pagination={{ pageSize: 10 }}
                scroll={{ y: 400 }}
              />
            </Space>
          </TabPane>
        </Tabs>
      </Drawer>

      {/* AI分析报告抽屉 */}
      <Drawer
        title={
          <span>
            <RobotOutlined style={{ marginRight: 8 }} />
            AI 分析报告
          </span>
        }
        placement="right"
        width={800}
        onClose={() => setAiAnalysisDrawerVisible(false)}
        open={aiAnalysisDrawerVisible}
      >
        {aiAnalysisResult && aiAnalysisResult.ai_analysis && (
          <div style={{ 
            fontSize: 14,
            lineHeight: '1.8',
            padding: '8px',
          }}>
            <ReactMarkdown>{aiAnalysisResult.ai_analysis}</ReactMarkdown>
          </div>
        )}
      </Drawer>

      {/* AI分析拨号按钮 */}
      {aiAnalysisResult && (
        <FloatButton
          icon={<RobotOutlined />}
          type="primary"
          tooltip="AI 分析报告"
          onClick={() => setAiAnalysisDrawerVisible(!aiAnalysisDrawerVisible)}
          style={{
            right: 24,
            bottom: 24,
          }}
        />
      )}
    </div>
  );
};

export default MainPage;

