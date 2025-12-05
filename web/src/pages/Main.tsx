/**
 * 主页面 - 股票分析功能
 */
import React, { useState, useEffect, useRef } from 'react';
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
  Descriptions,
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
  getIndicatorInfo,
  refreshAnalyze,
} from '../services/api';
import type {
  Position,
  Order,
  AnalysisResult,
  HotStock,
  IndicatorInfo,
} from '../types/index';
import TradingViewChart from '../components/TradingViewChart';
import { IndicatorLabel } from '../components/IndicatorLabel';
import { FinancialTable } from '../components/FinancialTable';
import { getPositionColumns, getOrderColumns } from '../config/tableColumns';
import { formatValue, formatLargeNumber, getRSIStatus, statusMaps } from '../utils/formatters';
import './Main.css';

const { TabPane } = Tabs;

interface StockOption {
  value: string;
  label: string;
}

const MainPage: React.FC = () => {
  // 持仓相关状态
  const [positions, setPositions] = useState<Position[]>([]);
  const [positionsLoading, setPositionsLoading] = useState<boolean>(false);

  // 交易订单相关状态
  const [tradeForm] = Form.useForm();
  const [orders, setOrders] = useState<Order[]>([]);
  const [tradeLoading, setTradeLoading] = useState<boolean>(false);
  const [orderLoading, setOrderLoading] = useState<boolean>(false);
  const [tradeDrawerVisible, setTradeDrawerVisible] = useState<boolean>(false);
  const [tradeDrawerTab, setTradeDrawerTab] = useState<string>('trade-form');

  // 分析相关状态
  const [analyzeForm] = Form.useForm();
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [aiAnalysisResult, setAiAnalysisResult] = useState<AnalysisResult | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState<boolean>(false);
  const [aiAnalysisDrawerVisible, setAiAnalysisDrawerVisible] = useState<boolean>(false);
  const [currentSymbol, setCurrentSymbol] = useState<string>('');

  // 热门股票相关状态
  const [, setHotStocks] = useState<HotStock[]>([]);
  const [stockOptions, setStockOptions] = useState<StockOption[]>([]);

  // 防抖定时器引用
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 技术指标解释信息
  const [indicatorInfoMap, setIndicatorInfoMap] = useState<Record<string, IndicatorInfo>>({});

  // 响应式状态：检测是否为移动端
  const [isMobile, setIsMobile] = useState<boolean>(typeof window !== 'undefined' && window.innerWidth <= 768);

  /**
   * 加载持仓数据
   */
  const loadPositions = async (): Promise<void> => {
    setPositionsLoading(true);
    try {
      const result = await getPositions();
      if (result.success) {
        setPositions(result.data || []);
      } else {
        message.error(result.message || '查询失败');
      }
    } catch (err: any) {
      message.error(err.message);
    } finally {
      setPositionsLoading(false);
    }
  };

  /**
   * 加载订单列表
   */
  const loadOrders = async (): Promise<void> => {
    setOrderLoading(true);
    try {
      const result = await getOrders();
      if (result.success) {
        setOrders(result.data || []);
      } else {
        message.error(result.message || '查询失败');
      }
    } catch (error: any) {
      message.error(error.message);
    } finally {
      setOrderLoading(false);
    }
  };

  /**
   * 提交订单
   */
  const handleTradeSubmit = async (values: any): Promise<void> => {
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
    } catch (error: any) {
      message.error(error.message);
    } finally {
      setTradeLoading(false);
    }
  };

  /**
   * 撤销订单
   */
  const handleCancelOrder = async (orderId: number): Promise<void> => {
    try {
      const result = await cancelOrder(orderId);
      if (result.success) {
        message.success('订单已撤销');
        await loadOrders();
        await loadPositions();
      } else {
        message.error(result.message || '撤销失败');
      }
    } catch (error: any) {
      message.error(error.message);
    }
  };

  /**
   * 执行分析 - 使用合并后的接口，一次请求同时获取技术分析和AI分析
   */
  const handleAnalyze = async (values: any): Promise<void> => {
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

      const result = await analyze(symbol, durationValue, barSizeValue, modelValue);

      if (result && result.success) {
        setAnalysisResult(result);
        setCurrentSymbol(symbol);

        if (result.ai_analysis) {
          setAiAnalysisResult(result);
          setAiAnalysisDrawerVisible(true);
        }
      } else {
        let errorMsg = result?.message || '分析失败';
        if (result?.error_code === 200) {
          errorMsg = `股票代码 "${symbol}" 不存在或无权限查询，请检查代码是否正确`;
        } else if (result?.error_code) {
          errorMsg = `错误[${result.error_code}]: ${result.message}`;
        }
        message.error(errorMsg, 5);
      }
    } catch (error: any) {
      message.error(error.message || '分析失败');
    } finally {
      setAnalysisLoading(false);
    }
  };

  /**
   * 刷新分析 - 强制重新获取数据，不使用缓存
   */
  const handleRefreshAnalyze = async (): Promise<void> => {
    if (!currentSymbol) {
      message.warning('请先进行一次分析');
      return;
    }

    const formValues = analyzeForm.getFieldsValue();
    const duration = formValues.duration || '3 M';
    const barSize = formValues.barSize || '1 day';
    const model = formValues.model || 'deepseek-v3.1:671b-cloud';

    setAnalysisLoading(true);
    setAnalysisResult(null);
    setAiAnalysisResult(null);

    try {
      const result = await refreshAnalyze(currentSymbol, duration, barSize, model);

      if (result && result.success) {
        setAnalysisResult(result);
        if (result.ai_analysis) {
          setAiAnalysisResult(result);
          setAiAnalysisDrawerVisible(true);
        }
        message.success('数据已刷新');
      } else {
        let errorMsg = result?.message || '刷新失败';
        if (result?.error_code === 200) {
          errorMsg = `股票代码 "${currentSymbol}" 不存在或无权限查询，请检查代码是否正确`;
        } else if (result?.error_code) {
          errorMsg = `错误[${result.error_code}]: ${result.message}`;
        }
        message.error(errorMsg, 5);
      }
    } catch (error: any) {
      message.error(error.message || '刷新失败');
    } finally {
      setAnalysisLoading(false);
    }
  };

  /**
   * 加载热门股票列表
   */
  const loadHotStocks = async (): Promise<void> => {
    try {
      const result = await getHotStocks(30);
      if (result.success && result.stocks) {
        setHotStocks(result.stocks);
        // 转换为 AutoComplete 需要的格式
        const options = result.stocks.map((stock: HotStock) => ({
          value: stock.symbol,
          label: `${stock.symbol} - ${stock.name}`,
        }));
        setStockOptions(options);
      }
    } catch (error: any) {
      console.error('加载热门股票失败:', error);
      // 失败时不影响使用，只是没有下拉提示
    }
  };

  /**
   * 防抖刷新热门股票列表
   */
  const debouncedRefreshHotStocks = (): void => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }
    refreshTimerRef.current = setTimeout(() => loadHotStocks(), 300);
  };

  /**
   * 加载技术指标解释信息
   */
  const loadIndicatorInfo = async (): Promise<void> => {
    try {
      const result = await getIndicatorInfo();
      if (result.success && result.indicators) {
        setIndicatorInfoMap(result.indicators);
      }
    } catch (error: any) {
      console.error('加载指标解释失败:', error);
    }
  };

  /**
   * 创建带知识讲解的指标标签
   */
  const createIndicatorLabel = (label: string, indicatorKey: string): React.ReactNode => {
    return <IndicatorLabel label={label} indicatorKey={indicatorKey} indicatorInfoMap={indicatorInfoMap} />;
  };

  useEffect(() => {
    loadHotStocks();
    loadIndicatorInfo();

    const handleResize = () => {
      const width = window.innerWidth;
      setIsMobile(width <= 768);
      
      if (width <= 768) {
        const viewport = document.querySelector('meta[name="viewport"]');
        if (viewport) {
          viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover');
        }
      }
    };
    
    handleResize();
    window.addEventListener('resize', handleResize);

    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  /**
   * 获取趋势标签
   */
  const getTrendTag = (direction: string | undefined): React.ReactNode => {
    const config = direction && statusMaps.trend[direction as keyof typeof statusMaps.trend]
      ? statusMaps.trend[direction as keyof typeof statusMaps.trend]
      : { color: 'default', text: direction || '未知' };
    
    const icon = direction === 'up' ? <RiseOutlined /> :
                 direction === 'down' ? <FallOutlined /> :
                 direction === 'neutral' ? <RightOutlined /> : null;
    
    return (
      <Tag color={config.color}>
        {icon} {config.text}
      </Tag>
    );
  };

  const positionColumns = getPositionColumns();
  const orderColumns = getOrderColumns(handleCancelOrder);

  return (
    <div className="main-page">
      {/* 固定顶部区域：持仓和股票输入框 */}
      <div className="fixed-top">
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* 持仓部分 - 已隐藏 */}
          {false && (
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
                      rowKey={(record, index) => record.symbol || String(index || 0)}
                      loading={positionsLoading}
                      pagination={{ pageSize: 5 }}
                      locale={{ emptyText: '暂无持仓' }}
                      size="small"
                    />
                  ),
                },
              ]}
            />
          )}

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
              style={{ marginBottom: 0, width: '100%' }}
            >
              <Form.Item
                label="股票代码"
                name="symbol"
                rules={[{ required: true, message: '请输入股票代码' }]}
                style={{ marginBottom: 0, flex: 1, minWidth: 200 }}
              >
                <AutoComplete
                  options={stockOptions}
                  placeholder="例如: AAPL"
                  style={{ width: '100%', maxWidth: 350 }}
                  filterOption={(inputValue, option) =>
                    option?.value?.toUpperCase().indexOf(inputValue.toUpperCase()) !== -1 ||
                    option?.label?.toUpperCase().indexOf(inputValue.toUpperCase()) !== -1
                  }
                  onSelect={(value) => {
                    analyzeForm.setFieldsValue({ symbol: value });
                  }}
                  onChange={(value) => {
                    analyzeForm.setFieldsValue({ symbol: value.toUpperCase() });
                    // 每次输入时防抖刷新热门股票列表
                    debouncedRefreshHotStocks();
                  }}
                  onFocus={() => {
                    // 获得焦点时立即刷新一次列表
                    loadHotStocks();
                  }}
                />
              </Form.Item>
              <Form.Item style={{ marginBottom: 0 }}>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={analysisLoading}
                  style={{ width: '100%', minWidth: 100 }}
                >
                  开始分析
                </Button>
              </Form.Item>
            </Form>
          </div>
        </Space>
      </div>

      {/* 分析结果区域 */}
      <div style={{ padding: '0 16px', background: '#fff' }} className="analysis-content">

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
                    {/* 操作按钮区域 */}
                    <Space style={{ marginBottom: 16 }}>
                          <Button
                            type="default"
                            size="small"
                            icon={<ReloadOutlined />}
                            onClick={handleRefreshAnalyze}
                            loading={analysisLoading}
                          >
                        刷新
                          </Button>
                    </Space>
                    
                    <Descriptions
                      title={
                        <span>
                          <BarChartOutlined style={{ marginRight: 8 }} />
                          价格信息
                        </span>
                      }
                      bordered
                      column={{ xxl: 4, xl: 4, lg: 3, md: 2, sm: 2, xs: 1 }}
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
                              {(analysisResult.indicators.price_change_pct ?? 0) >= 0 ? (
                                <RiseOutlined style={{ color: '#3f8600' }} />
                              ) : (
                                <FallOutlined style={{ color: '#cf1322' }} />
                              )}
                              <span style={{
                                fontSize: 18,
                                fontWeight: 600,
                                color: (analysisResult.indicators.price_change_pct ?? 0) >= 0 ? '#3f8600' : '#cf1322',
                              }}>
                                {formatValue(analysisResult.indicators.price_change_pct)}%
                              </span>
                            </Space>
                          ),
                        },
                        {
                          label: '数据点数',
                          span: 1,
                          children: `${analysisResult.indicators.data_points || 0}条数据`,
                        },
                        {
                          label: '趋势方向',
                          span: 1,
                          children: getTrendTag(analysisResult.indicators.trend_direction),
                        },
                      ]}
                    />
                  </div>

                  {/* K线图 */}
                  {currentSymbol && (
                    <div style={{ marginTop: 24, overflowX: 'auto' }}>
                      <div style={{
                        fontSize: '16px',
                        fontWeight: 500,
                        marginBottom: '16px',
                        display: 'flex',
                        alignItems: 'center',
                      }}>
                        <BarChartOutlined style={{ marginRight: 8 }} />
                        K线图 - {currentSymbol}
                      </div>
                      <div style={{ minWidth: '100%', width: '100%' }}>
                        <TradingViewChart
                          symbol={currentSymbol}
                          height={isMobile ? 300 : 500}
                          theme="light"
                          indicators={analysisResult?.indicators}
                          candles={analysisResult?.candles}
                        />
                      </div>
                    </div>
                  )}

                  {/* 移动平均线 */}
                  {[5, 10, 20, 50].some(p => analysisResult.indicators[`ma${p}`] !== undefined) && (
                    <Collapse
                      ghost
                      defaultActiveKey={['ma']}
                      items={[{
                        key: 'ma',
                        label: (
                          <span>
                            <BarChartOutlined style={{ marginRight: 8 }} />
                            {createIndicatorLabel('移动平均线', 'ma')}
                          </span>
                        ),
                        children: (
                          <Descriptions
                            bordered
                            column={{ xxl: 4, xl: 4, lg: 3, md: 2, sm: 2, xs: 1 }}
                            size="middle"
                            layout="vertical"
                            items={[5, 10, 20, 50]
                              .map((period) => {
                                const key = `ma${period}`;
                                const value = analysisResult.indicators[key];
                                if (value === undefined) return null as any;
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
                        ),
                      }]}
                      style={{ marginTop: 24 }}
                    />
                  )}

                  {/* 技术指标 */}
                  <Collapse
                    ghost
                    defaultActiveKey={['indicators']}
                    items={[{
                      key: 'indicators',
                      label: (
                        <span>
                          <BarChartOutlined style={{ marginRight: 8 }} />
                          技术指标
                        </span>
                      ),
                      children: (
                        <Descriptions
                          bordered
                          column={{ xxl: 4, xl: 3, lg: 3, md: 2, sm: 1, xs: 1 }}
                          size="middle"
                          layout="vertical"
                          items={(() => {
                            const items = [];
                            const indicators = analysisResult.indicators;

                            if (indicators.rsi !== undefined) {
                              items.push({
                                label: createIndicatorLabel('RSI(14)', 'rsi'),
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
                                label: createIndicatorLabel('MACD', 'macd'),
                                children: (
                                  <Space>
                                    <span>{formatValue(indicators.macd, 3)}</span>
                                    {indicators.macd !== undefined && indicators.macd_signal !== undefined && indicators.macd > indicators.macd_signal ? (
                                      <Tag color="success">金叉</Tag>
                                    ) : (
                                      <Tag color="error">死叉</Tag>
                                    )}
                                  </Space>
                                ),
                              });
                            }

                            if (indicators.macd_signal !== undefined) {
                              items.push({
                                label: createIndicatorLabel('MACD信号线', 'macd'),
                                children: formatValue(indicators.macd_signal, 3),
                              });
                            }

                            if (indicators.macd_histogram !== undefined) {
                              items.push({
                                label: createIndicatorLabel('MACD柱状图', 'macd'),
                                children: formatValue(indicators.macd_histogram, 3),
                              });
                            }

                            if (indicators.bb_upper) {
                              items.push({
                                label: createIndicatorLabel('布林带上轨', 'bb'),
                                children: `$${formatValue(indicators.bb_upper)}`,
                              });
                            }

                            if (indicators.bb_middle) {
                              items.push({
                                label: createIndicatorLabel('布林带中轨', 'bb'),
                                children: `$${formatValue(indicators.bb_middle)}`,
                              });
                            }

                            if (indicators.bb_lower) {
                              items.push({
                                label: createIndicatorLabel('布林带下轨', 'bb'),
                                children: `$${formatValue(indicators.bb_lower)}`,
                              });
                            }

                            if (indicators.volume_ratio !== undefined) {
                              items.push({
                                label: createIndicatorLabel('成交量比率', 'volume_ratio'),
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
                                label: createIndicatorLabel('波动率', 'volatility'),
                                children: (
                                  <Space>
                                    <span>{formatValue(indicators.volatility_20)}%</span>
                                    {indicators.volatility_20 > 5 ? (
                                      <Tag color="error">极高</Tag>
                                    ) : indicators.volatility_20 > 3 ? (
                                      <Tag color="warning">高</Tag>
                                    ) : indicators.volatility_20 > 2 ? (
                                      <Tag color="default">中</Tag>
                                    ) : (
                                      <Tag color="success">低</Tag>
                                    )}
                                  </Space>
                                ),
                              });
                            }

                            if (indicators.atr !== undefined) {
                              items.push({
                                label: createIndicatorLabel('ATR', 'atr'),
                                children: `$${formatValue(indicators.atr)} (${formatValue(indicators.atr_percent, 1)}%)`,
                              });
                            }

                            if (indicators.kdj_k !== undefined) {
                              items.push({
                                label: createIndicatorLabel('KDJ', 'kdj'),
                                children: (
                                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                                    <div>
                                      K={formatValue(indicators.kdj_k, 1)} D={formatValue(indicators.kdj_d, 1)} J={formatValue(indicators.kdj_j, 1)}
                                    </div>
                                    <Space>
                                      {indicators.kdj_j !== undefined && indicators.kdj_j < 20 ? (
                                        <Tag color="success">超卖</Tag>
                                      ) : indicators.kdj_j !== undefined && indicators.kdj_j > 80 ? (
                                        <Tag color="error">超买</Tag>
                                      ) : (
                                        <Tag color="default">中性</Tag>
                                      )}
                                      {indicators.kdj_k !== undefined && indicators.kdj_d !== undefined && indicators.kdj_k > indicators.kdj_d ? (
                                        <Tag color="success">多头</Tag>
                                      ) : (
                                        <Tag color="error">空头</Tag>
                                      )}
                                    </Space>
                                  </Space>
                                ),
                              });
                            }

                            if (indicators.williams_r !== undefined) {
                              items.push({
                                label: createIndicatorLabel('威廉%R', 'williams_r'),
                                children: (
                                  <Space>
                                    <span>{formatValue(indicators.williams_r, 1)}</span>
                                    <Tag
                                      color={
                                        indicators.williams_r < -80 ? 'success' :
                                          indicators.williams_r > -20 ? 'error' : 'default'
                                      }
                                    >
                                      {indicators.williams_r < -80 ? '超卖' :
                                        indicators.williams_r > -20 ? '超买' : '中性'}
                                    </Tag>
                                  </Space>
                                ),
                              });
                            }

                            // CCI顺势指标
                            if (indicators.cci !== undefined) {
                              items.push({
                                label: createIndicatorLabel('CCI', 'cci'),
                                children: (
                                  <Space>
                                    <span style={{ fontSize: 16, fontWeight: 600 }}>{formatValue(indicators.cci, 1)}</span>
                                    <Tag
                                      color={
                                        indicators.cci_signal === 'overbought' ? 'error' :
                                          indicators.cci_signal === 'oversold' ? 'success' : 'default'
                                      }
                                    >
                                      {indicators.cci_signal === 'overbought' ? '超买(>100)' :
                                        indicators.cci_signal === 'oversold' ? '超卖(<-100)' : '中性'}
                                    </Tag>
                                  </Space>
                                ),
                              });
                            }

                            // ADX趋势强度指标
                            if (indicators.adx !== undefined) {
                              items.push({
                                label: createIndicatorLabel('ADX', 'adx'),
                                children: (
                                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                                    <div>
                                      <span style={{ fontSize: 16, fontWeight: 600 }}>{formatValue(indicators.adx, 1)}</span>
                                      <Tag
                                        color={
                                          indicators.adx > 40 ? 'success' :
                                            indicators.adx > 25 ? 'default' : 'warning'
                                        }
                                        style={{ marginLeft: 8 }}
                                      >
                                        {indicators.adx > 40 ? '强趋势' :
                                          indicators.adx > 25 ? '中趋势' :
                                            indicators.adx > 20 ? '弱趋势' : '无趋势'}
                                      </Tag>
                                    </div>
                                    {indicators.plus_di !== undefined && indicators.minus_di !== undefined && (
                                      <div>
                                        <span>+DI={formatValue(indicators.plus_di, 1)} -DI={formatValue(indicators.minus_di, 1)}</span>
                                        <Tag color={indicators.plus_di > indicators.minus_di ? 'success' : 'error'} style={{ marginLeft: 8 }}>
                                          {indicators.plus_di > indicators.minus_di ? '多头' : '空头'}
                                        </Tag>
                                      </div>
                                    )}
                                  </Space>
                                ),
                              });
                            }


                            // SAR抛物线转向指标
                            if (indicators.sar !== undefined) {
                              items.push({
                                label: createIndicatorLabel('SAR', 'sar'),
                                children: (
                                  <Space>
                                    <span style={{ fontSize: 16, fontWeight: 600 }}>${formatValue(indicators.sar)}</span>
                                    <Tag
                                      color={
                                        indicators.sar_signal === 'bullish' ? 'success' :
                                          indicators.sar_signal === 'bearish' ? 'error' : 'default'
                                      }
                                    >
                                      {indicators.sar_signal === 'bullish' ? '看涨' :
                                        indicators.sar_signal === 'bearish' ? '看跌' : '中性'}
                                    </Tag>
                                    {indicators.sar_distance_pct !== undefined && (
                                      <span style={{ fontSize: 14 }}>
                                        (距离{Math.abs(indicators.sar_distance_pct).toFixed(1)}%)
                                      </span>
                                    )}
                                  </Space>
                                ),
                              });
                            }

                            // Ichimoku Cloud
                            if (indicators.ichimoku_tenkan_sen !== undefined) {
                              items.push({
                                label: createIndicatorLabel('一目均衡表', 'ichimoku'),
                                children: (
                                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                                    <Space>
                                      <Tag
                                        color={
                                          indicators.ichimoku_status === 'above_cloud' ? 'success' :
                                            indicators.ichimoku_status === 'below_cloud' ? 'error' : 'default'
                                        }
                                      >
                                        {indicators.ichimoku_status === 'above_cloud' ? '云上(看涨)' :
                                          indicators.ichimoku_status === 'below_cloud' ? '云下(看跌)' : '云中(盘整)'}
                                      </Tag>
                                      {indicators.ichimoku_tk_cross === 'bullish' && <Tag color="success">金叉</Tag>}
                                      {indicators.ichimoku_tk_cross === 'bearish' && <Tag color="error">死叉</Tag>}
                                    </Space>
                                    <div style={{ fontSize: 12 }}>
                                      转折: ${formatValue(indicators.ichimoku_tenkan_sen)} 基准: ${formatValue(indicators.ichimoku_kijun_sen)}
                                    </div>
                                    <div style={{ fontSize: 12 }}>
                                      云层: ${formatValue(indicators.ichimoku_cloud_bottom ?? Math.min(indicators.ichimoku_senkou_span_a || 0, indicators.ichimoku_senkou_span_b || 0))} - ${formatValue(indicators.ichimoku_cloud_top ?? Math.max(indicators.ichimoku_senkou_span_a || 0, indicators.ichimoku_senkou_span_b || 0))}
                                    </div>
                                  </Space>
                                ),
                              });
                            }

                            // SuperTrend
                            if (indicators.supertrend !== undefined) {
                              items.push({
                                label: createIndicatorLabel('SuperTrend', 'supertrend'),
                                children: (
                                  <Space>
                                    <span style={{ fontSize: 16, fontWeight: 600 }}>${formatValue(indicators.supertrend)}</span>
                                    <Tag color={indicators.supertrend_direction === 'up' ? 'success' : 'error'}>
                                      {indicators.supertrend_direction === 'up' ? '看涨支撑' : '看跌阻力'}
                                    </Tag>
                                  </Space>
                                ),
                              });
                            }

                            // StochRSI
                            if (indicators.stoch_rsi_k !== undefined) {
                              items.push({
                                label: createIndicatorLabel('StochRSI', 'stoch_rsi'),
                                children: (
                                  <Space>
                                    <span>K: {formatValue(indicators.stoch_rsi_k, 1)}</span>
                                    <span>D: {formatValue(indicators.stoch_rsi_d, 1)}</span>
                                    <Tag
                                      color={
                                        indicators.stoch_rsi_status === 'oversold' ? 'success' :
                                          indicators.stoch_rsi_status === 'overbought' ? 'error' : 'default'
                                      }
                                    >
                                      {indicators.stoch_rsi_status === 'oversold' ? '超卖' :
                                        indicators.stoch_rsi_status === 'overbought' ? '超买' : '中性'}
                                    </Tag>
                                  </Space>
                                ),
                              });
                            }

                            // Volume Profile
                            if (indicators.vp_poc !== undefined) {
                              items.push({
                                label: createIndicatorLabel('筹码分布', 'volume_profile'),
                                children: (
                                  <Space direction="vertical" size="small">
                                    <Space>
                                      <span>POC: ${formatValue(indicators.vp_poc)}</span>
                                      <Tag
                                        color={
                                          indicators.vp_status === 'above_va' ? 'success' :
                                            indicators.vp_status === 'below_va' ? 'error' : 'default'
                                        }
                                      >
                                        {indicators.vp_status === 'above_va' ? '上方失衡(看涨)' :
                                          indicators.vp_status === 'below_va' ? '下方失衡(看跌)' : '价值区平衡'}
                                      </Tag>
                                    </Space>
                                    <span style={{ fontSize: 12 }}>
                                      价值区: ${formatValue(indicators.vp_val)} - ${formatValue(indicators.vp_vah)}
                                    </span>
                                  </Space>
                                ),
                              });
                            }

                            if (indicators.obv_trend) {
                              items.push({
                                label: createIndicatorLabel('OBV趋势', 'obv'),
                                children: indicators.obv_trend === 'up' ? (
                                  (indicators.price_change_pct ?? 0) > 0 ? (
                                    <Tag color="success">量价齐升</Tag>
                                  ) : (
                                    <Tag color="warning">量价背离(可能见底)</Tag>
                                  )
                                ) : indicators.obv_trend === 'down' ? (
                                  (indicators.price_change_pct ?? 0) < 0 ? (
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
                                label: createIndicatorLabel('趋势强度', 'trend_strength'),
                                children: (
                                  <Space>
                                    {getTrendTag(indicators.trend_direction)}
                                    <span style={{ fontSize: 16, fontWeight: 600 }}>
                                      {formatValue(indicators.trend_strength, 0)}%
                                    </span>
                                    {indicators.trend_strength > 50 ? (
                                      <Tag color="success">强</Tag>
                                    ) : indicators.trend_strength > 25 ? (
                                      <Tag color="default">中</Tag>
                                    ) : (
                                      <Tag color="warning">弱</Tag>
                                    )}
                                  </Space>
                                ),
                              });
                            }

                            if ((indicators.consecutive_up_days ?? 0) > 0 || (indicators.consecutive_down_days ?? 0) > 0) {
                              items.push({
                                label: '连续涨跌',
                                span: 4,
                                children: (
                                  <Space>
                                    {(indicators.consecutive_up_days ?? 0) > 0 ? (
                                      <>
                                        <RiseOutlined style={{ color: '#3f8600' }} />
                                        <span>连续{indicators.consecutive_up_days}天上涨</span>
                                        {(indicators.consecutive_up_days ?? 0) >= 5 && (
                                          <Tag color="warning">注意</Tag>
                                        )}
                                      </>
                                    ) : (
                                      <>
                                        <FallOutlined style={{ color: '#cf1322' }} />
                                        <span>连续{indicators.consecutive_down_days}天下跌</span>
                                        {(indicators.consecutive_down_days ?? 0) >= 5 && (
                                          <Tag color="success">关注</Tag>
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
                      ),
                    }]}
                    style={{ marginTop: 24 }}
                  />






                  {/* 关键价位 */}
                  {(analysisResult.indicators.pivot || analysisResult.indicators.pivot_r1 || analysisResult.indicators.resistance_20d_high) && (
                    <Collapse
                      ghost
                      defaultActiveKey={['pivot']}
                      items={[{
                        key: 'pivot',
                        label: (
                          <span>
                            <BarChartOutlined style={{ marginRight: 8 }} />
                            关键价位
                          </span>
                        ),
                        children: (
                          <Descriptions
                            bordered
                            column={{ xxl: 4, xl: 4, lg: 3, md: 2, sm: 2, xs: 1 }}
                            size="middle"
                            layout="vertical"
                            items={(() => {
                              const items = [];
                              const indicators = analysisResult.indicators;

                              if (indicators.pivot) {
                                items.push({
                                  label: createIndicatorLabel('枢轴点', 'pivot'),
                                  children: (
                                    <span style={{ fontSize: 16, fontWeight: 600 }}>
                                      ${formatValue(indicators.pivot)}
                                    </span>
                                  ),
                                });
                              }

                              if (indicators.pivot_r1) {
                                items.push({
                                  label: createIndicatorLabel('压力位R1', 'pivot_r1'),
                                  children: (
                                    <span style={{ fontSize: 16, fontWeight: 600, color: '#fa8c16' }}>
                                      ${formatValue(indicators.pivot_r1)}
                                    </span>
                                  ),
                                });
                              }

                              if (indicators.pivot_r2) {
                                items.push({
                                  label: createIndicatorLabel('压力位R2', 'pivot_r2'),
                                  children: (
                                    <span style={{ fontSize: 16, fontWeight: 600, color: '#fa8c16' }}>
                                      ${formatValue(indicators.pivot_r2)}
                                    </span>
                                  ),
                                });
                              }

                              if (indicators.pivot_r3) {
                                items.push({
                                  label: createIndicatorLabel('压力位R3', 'pivot_r3'),
                                  children: (
                                    <span style={{ fontSize: 16, fontWeight: 600, color: '#fa8c16' }}>
                                      ${formatValue(indicators.pivot_r3)}
                                    </span>
                                  ),
                                });
                              }

                              if (indicators.pivot_s1) {
                                items.push({
                                  label: createIndicatorLabel('支撑位S1', 'pivot_s1'),
                                  children: (
                                    <span style={{ fontSize: 16, fontWeight: 600, color: '#52c41a' }}>
                                      ${formatValue(indicators.pivot_s1)}
                                    </span>
                                  ),
                                });
                              }

                              if (indicators.pivot_s2) {
                                items.push({
                                  label: createIndicatorLabel('支撑位S2', 'pivot_s2'),
                                  children: (
                                    <span style={{ fontSize: 16, fontWeight: 600, color: '#52c41a' }}>
                                      ${formatValue(indicators.pivot_s2)}
                                    </span>
                                  ),
                                });
                              }

                              if (indicators.pivot_s3) {
                                items.push({
                                  label: createIndicatorLabel('支撑位S3', 'pivot_s3'),
                                  children: (
                                    <span style={{ fontSize: 16, fontWeight: 600, color: '#52c41a' }}>
                                      ${formatValue(indicators.pivot_s3)}
                                    </span>
                                  ),
                                });
                              }

                              if (indicators.resistance_20d_high) {
                                items.push({
                                  label: createIndicatorLabel('20日高点', 'resistance_20d_high'),
                                  children: (
                                    <span style={{ fontSize: 16, fontWeight: 600, color: '#fa8c16' }}>
                                      ${formatValue(indicators.resistance_20d_high)}
                                    </span>
                                  ),
                                });
                              }

                              if (indicators.support_20d_low) {
                                items.push({
                                  label: createIndicatorLabel('20日低点', 'support_20d_low'),
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
                        ),
                      }]}
                      style={{ marginTop: 24 }}
                    />
                  )}

                  {/* 交易信号 */}
                  {analysisResult.signals && (
                    <Collapse
                      ghost
                      defaultActiveKey={['signals']}
                      items={[{
                        key: 'signals',
                        label: (
                          <span>
                            <BarChartOutlined style={{ marginRight: 8 }} />
                            交易信号
                          </span>
                        ),
                        children: (
                          <Descriptions
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
                                const riskLevel = String(signals.risk.level || 'unknown');
                                const config = statusMaps.risk[riskLevel as keyof typeof statusMaps.risk] || 
                                  { color: 'default', text: '未知' };
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

                              if (signals.stop_loss && signals.take_profit && indicators.current_price && indicators.current_price > 0) {
                                const currentPrice = indicators.current_price;
                                items.push({
                                  label: '风险回报比',
                                  span: 3,
                                  children: (
                                    <Tag color="blue" style={{ fontSize: 14 }}>
                                      1:{formatValue(
                                        Math.abs(
                                          ((signals.take_profit - currentPrice) / currentPrice) /
                                          ((signals.stop_loss - currentPrice) / currentPrice)
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
                                      {signals.signals.map((signal: string, index: number) => (
                                        <li key={index} style={{ marginBottom: 4, fontSize: 14 }}>{signal}</li>
                                      ))}
                                    </ul>
                                  ),
                                });
                              }

                              return items;
                            })()}
                          />
                        ),
                      }]}
                      style={{ marginTop: 24 }}
                    />
                  )}

                  {/* 基本面数据 */}
                  {analysisResult.indicators.fundamental_data &&
                    typeof analysisResult.indicators.fundamental_data === 'object' &&
                    !analysisResult.indicators.fundamental_data.raw_xml &&
                    Object.keys(analysisResult.indicators.fundamental_data).length > 0 && (
                      <Collapse
                        ghost
                        defaultActiveKey={[]}
                        items={[{
                          key: 'fundamental',
                          label: (
                            <span>
                              <BarChartOutlined style={{ marginRight: 8 }} />
                              基本面数据
                            </span>
                          ),
                          children: (
                            <Descriptions
                              bordered
                              column={{ xxl: 4, xl: 4, lg: 3, md: 2, sm: 2, xs: 1 }}
                              size="middle"
                              layout="vertical"
                              items={(() => {
                                const items = [];
                                const fd = analysisResult.indicators.fundamental_data;

                                // 基本信息
                                if (fd.CompanyName) {
                                  items.push({
                                    label: createIndicatorLabel('公司名称', 'fundamental'),
                                    span: 2,
                                    children: fd.CompanyName,
                                  });
                                }

                                if (fd.Exchange) {
                                  items.push({
                                    label: createIndicatorLabel('交易所', 'fundamental'),
                                    span: 1,
                                    children: fd.Exchange,
                                  });
                                }

                                if (fd.Employees) {
                                  items.push({
                                    label: createIndicatorLabel('员工数', 'fundamental'),
                                    span: 1,
                                    children: `${String(fd.Employees)}人`,
                                  });
                                }

                                if (fd.SharesOutstanding) {
                                  const shares = parseFloat(String(fd.SharesOutstanding));
                                  items.push({
                                    label: createIndicatorLabel('流通股数', 'fundamental'),
                                    span: 1,
                                    children: formatLargeNumber(shares).replace('$', ''),
                                  });
                                }

                                if (fd.MarketCap) {
                                  items.push({
                                    label: createIndicatorLabel('市值', 'market_cap'),
                                    span: 1,
                                    children: formatLargeNumber(parseFloat(String(fd.MarketCap))),
                                  });
                                }

                                if (fd.Price) {
                                  items.push({
                                    label: createIndicatorLabel('当前价', 'fundamental'),
                                    span: 1,
                                    children: `$${formatValue(parseFloat(String(fd.Price || 0)), 2)}`,
                                  });
                                }

                                if (fd['52WeekHigh'] && fd['52WeekLow']) {
                                  items.push({
                                    label: createIndicatorLabel('52周区间', 'fundamental'),
                                    span: 2,
                                    children: `$${formatValue(parseFloat(String(fd['52WeekLow'] || 0)), 2)} - $${formatValue(parseFloat(String(fd['52WeekHigh'] || 0)), 2)}`,
                                  });
                                }

                                if (fd.RevenueTTM) {
                                  items.push({
                                    label: createIndicatorLabel('营收(TTM)', 'revenue'),
                                    span: 1,
                                    children: formatLargeNumber(parseFloat(String(fd.RevenueTTM))),
                                  });
                                }

                                if (fd.NetIncomeTTM) {
                                  items.push({
                                    label: createIndicatorLabel('净利润(TTM)', 'fundamental'),
                                    span: 1,
                                    children: formatLargeNumber(parseFloat(String(fd.NetIncomeTTM))),
                                  });
                                }

                                if (fd.EBITDATTM) {
                                  items.push({
                                    label: createIndicatorLabel('EBITDA(TTM)', 'fundamental'),
                                    span: 1,
                                    children: formatLargeNumber(parseFloat(String(fd.EBITDATTM))),
                                  });
                                }

                                if (fd.ProfitMargin) {
                                  items.push({
                                    label: createIndicatorLabel('利润率', 'profit_margin'),
                                    span: 1,
                                    children: `${formatValue(parseFloat(String(fd.ProfitMargin || 0)) * 100, 2)}%`,
                                  });
                                }

                                if (fd.GrossMargin) {
                                  items.push({
                                    label: createIndicatorLabel('毛利率', 'profit_margin'),
                                    span: 1,
                                    children: `${formatValue(parseFloat(String(fd.GrossMargin || 0)) * 100, 2)}%`,
                                  });
                                }

                                // 每股数据
                                if (fd.EPS) {
                                  items.push({
                                    label: createIndicatorLabel('每股收益(EPS)', 'eps'),
                                    span: 1,
                                    children: `$${formatValue(parseFloat(String(fd.EPS || 0)), 2)}`,
                                  });
                                }

                                if (fd.BookValuePerShare) {
                                  items.push({
                                    label: createIndicatorLabel('每股净资产', 'fundamental'),
                                    span: 1,
                                    children: `$${formatValue(parseFloat(String(fd.BookValuePerShare || 0)), 2)}`,
                                  });
                                }

                                if (fd.CashPerShare) {
                                  items.push({
                                    label: createIndicatorLabel('每股现金', 'fundamental'),
                                    span: 1,
                                    children: `$${formatValue(parseFloat(String(fd.CashPerShare || 0)), 2)}`,
                                  });
                                }

                                if (fd.DividendPerShare) {
                                  items.push({
                                    label: createIndicatorLabel('每股股息', 'fundamental'),
                                    span: 1,
                                    children: `$${formatValue(parseFloat(String(fd.DividendPerShare || 0)), 3)}`,
                                  });
                                }

                                // 估值指标
                                if (fd.PE) {
                                  const pe = parseFloat(String(fd.PE));
                                  items.push({
                                    label: createIndicatorLabel('市盈率(PE)', 'pe'),
                                    span: 1,
                                    children: (
                                      <Space>
                                        <span>{formatValue(parseFloat(String(pe)), 2)}</span>
                                        {pe < 15 ? (
                                          <Tag color="success">低估</Tag>
                                        ) : pe > 25 ? (
                                          <Tag color="warning">高估</Tag>
                                        ) : (
                                          <Tag color="default">合理</Tag>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }

                                if (fd.PriceToBook) {
                                  const pb = parseFloat(String(fd.PriceToBook));
                                  items.push({
                                    label: createIndicatorLabel('市净率(PB)', 'pb'),
                                    span: 1,
                                    children: (
                                      <Space>
                                        <span>{formatValue(parseFloat(String(pb)), 2)}</span>
                                        {pb < 1 ? (
                                          <Tag color="success">低估</Tag>
                                        ) : pb > 3 ? (
                                          <Tag color="warning">高估</Tag>
                                        ) : (
                                          <Tag color="default">合理</Tag>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }

                                if (fd.ROE) {
                                  const roe = parseFloat(String(fd.ROE)) * 100;
                                  items.push({
                                    label: createIndicatorLabel('净资产收益率(ROE)', 'roe'),
                                    span: 1,
                                    children: (
                                      <Space>
                                        <span>{formatValue(parseFloat(String(roe)), 2)}%</span>
                                        {roe > 15 ? (
                                          <Tag color="success">优秀</Tag>
                                        ) : roe > 10 ? (
                                          <Tag color="default">良好</Tag>
                                        ) : (
                                          <Tag color="warning">一般</Tag>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }

                                // 分析师预测
                                if (fd.TargetPrice) {
                                  const target = parseFloat(String(fd.TargetPrice));
                                  const currentPrice = parseFloat(String(fd.Price || analysisResult.indicators.current_price || 0));
                                  const upside = currentPrice > 0 ? ((target - currentPrice) / currentPrice * 100) : 0;
                                  items.push({
                                    label: createIndicatorLabel('目标价', 'target_price'),
                                    span: 1,
                                    children: (
                                      <Space>
                                        <span>${formatValue(parseFloat(String(target)), 2)}</span>
                                        {upside > 0 ? (
                                          <Tag color="success">+{formatValue(upside, 1)}%</Tag>
                                        ) : (
                                          <Tag color="error">{formatValue(upside, 1)}%</Tag>
                                        )}
                                      </Space>
                                    ),
                                  });
                                }

                                if (fd.ConsensusRecommendation) {
                                  const config = statusMaps.consensus[String(fd.ConsensusRecommendation) as keyof typeof statusMaps.consensus] || 
                                    { text: String(fd.ConsensusRecommendation), color: 'default' };
                                  items.push({
                                    label: createIndicatorLabel('共识评级', 'fundamental'),
                                    span: 1,
                                    children: <Tag color={config.color}>{config.text}</Tag>,
                                  });
                                }

                                if (fd.ProjectedEPS) {
                                  items.push({
                                    label: createIndicatorLabel('预测EPS', 'eps'),
                                    span: 1,
                                    children: `$${formatValue(parseFloat(String(fd.ProjectedEPS || 0)), 2)}`,
                                  });
                                }

                                if (fd.ProjectedGrowthRate) {
                                  items.push({
                                    label: createIndicatorLabel('预测增长率', 'fundamental'),
                                    span: 1,
                                    children: `${formatValue(parseFloat(String(fd.ProjectedGrowthRate || 0)) * 100, 2)}%`,
                                  });
                                }

                                return items;
                              })()}
                            />
                          ),
                        },
                        // 详细财务报表
                        ...(analysisResult.indicators.fundamental_data?.Financials ||
                          analysisResult.indicators.fundamental_data?.QuarterlyFinancials ||
                          analysisResult.indicators.fundamental_data?.BalanceSheet ||
                          analysisResult.indicators.fundamental_data?.Cashflow ? [{
                            key: 'financial-statements',
                            label: (
                              <span>
                                <BarChartOutlined style={{ marginRight: 8 }} />
                                详细财务报表
                              </span>
                            ),
                            children: (
                              <Tabs
                                defaultActiveKey="annual-financials"
                                items={[
                                  analysisResult.indicators.fundamental_data?.Financials && 
                                  Array.isArray(analysisResult.indicators.fundamental_data.Financials) &&
                                  analysisResult.indicators.fundamental_data.Financials.length > 0 ? {
                                    key: 'annual-financials',
                                    label: '年度财务报表',
                                    children: <FinancialTable data={analysisResult.indicators.fundamental_data.Financials} />,
                                  } : null,
                                  analysisResult.indicators.fundamental_data?.QuarterlyFinancials && 
                                  Array.isArray(analysisResult.indicators.fundamental_data.QuarterlyFinancials) &&
                                  analysisResult.indicators.fundamental_data.QuarterlyFinancials.length > 0 ? {
                                    key: 'quarterly-financials',
                                    label: '季度财务报表',
                                    children: <FinancialTable data={analysisResult.indicators.fundamental_data.QuarterlyFinancials} />,
                                  } : null,
                                  analysisResult.indicators.fundamental_data?.BalanceSheet && 
                                  Array.isArray(analysisResult.indicators.fundamental_data.BalanceSheet) &&
                                  analysisResult.indicators.fundamental_data.BalanceSheet.length > 0 ? {
                                    key: 'balance-sheet',
                                    label: '资产负债表',
                                    children: <FinancialTable data={analysisResult.indicators.fundamental_data.BalanceSheet} />,
                                  } : null,
                                  analysisResult.indicators.fundamental_data?.Cashflow && 
                                  Array.isArray(analysisResult.indicators.fundamental_data.Cashflow) &&
                                  analysisResult.indicators.fundamental_data.Cashflow.length > 0 ? {
                                    key: 'cashflow',
                                    label: '现金流量表',
                                    children: <FinancialTable data={analysisResult.indicators.fundamental_data.Cashflow} />,
                                  } : null,
                                ].filter((item): item is NonNullable<typeof item> => item !== null)}
                              />
                            ),
                          }] : []),
                      ]}
                      style={{ marginTop: 24 }}
                    />
                    )}

                </div>
              )
              }

            </Space>
          </div>
        )}
      </div>

      {/* 交易抽屉 - 已隐藏 */}
      {false && (
        <Drawer
          title={
            <span>
              <DollarOutlined style={{ marginRight: 8 }} />
              交易
            </span>
          }
          placement="right"
          width={isMobile ? '100%' : 600}
          onClose={() => setTradeDrawerVisible(false)}
          open={tradeDrawerVisible}
          styles={{
            body: {
              padding: isMobile ? '12px' : '24px',
            },
          }}
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
      )}

      {/* AI分析报告抽屉 */}
      <Drawer
        title={
          <span>
            <RobotOutlined style={{ marginRight: 8 }} />
            AI 分析报告
          </span>
        }
        placement="right"
        width={isMobile ? '100%' : 800}
        onClose={() => setAiAnalysisDrawerVisible(false)}
        open={aiAnalysisDrawerVisible}
        styles={{
          body: {
            padding: isMobile ? '12px' : '24px',
          },
        }}
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
