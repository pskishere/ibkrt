/**
 * API响应基础类型
 */
export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  error_code?: number;  // 错误代码（如200表示证券不存在）
  data?: T;
  [key: string]: any;
}

/**
 * 持仓数据
 */
export interface Position {
  symbol: string;
  position: number;
  avg_cost: number;
  market_price: number;
  market_value: number;
  unrealized_pnl: number;
  realized_pnl: number;
}

/**
 * 订单数据
 */
export interface Order {
  orderId: number;
  symbol: string;
  action: 'BUY' | 'SELL';
  orderType: string;
  totalQuantity: number;
  lmtPrice?: number;
  auxPrice?: number;
  status: string;
  filled?: number;
  remaining?: number;
  avg_fill_price?: number;
  [key: string]: any; // 允许其他字段
}

/**
 * K线数据
 */
export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/**
 * 技术指标
 */
export interface Indicators {
  symbol?: string;
  current_price?: number;
  data_points?: number;
  price_change_pct?: number;
  trend_direction?: string;
  trend_strength?: number;
  rsi?: number;
  macd?: number;
  macd_signal?: number;
  macd_histogram?: number;
  bb_upper?: number;
  bb_middle?: number;
  bb_lower?: number;
  bb_upper_series?: number[];  // 布林带上轨历史数据
  bb_middle_series?: number[]; // 布林带中轨历史数据
  bb_lower_series?: number[];  // 布林带下轨历史数据
  ma5?: number;
  ma10?: number;
  ma20?: number;
  ma50?: number;
  kdj_k?: number;
  kdj_d?: number;
  kdj_j?: number;
  williams_r?: number;
  atr?: number;
  atr_percent?: number;
  // 新增现代指标
  cci?: number;
  cci_signal?: string;  // 'overbought' | 'oversold' | 'neutral'
  adx?: number;
  adx_signal?: string;  // 'strong_trend' | 'trend' | 'weak_trend'
  plus_di?: number;
  minus_di?: number;
  vwap?: number;
  vwap_20?: number;
  vwap_signal?: string;  // 'above' | 'below' | 'at'
  vwap_deviation?: number;
  sar?: number;
  sar_signal?: string;  // 'buy' | 'sell'
  sar_trend?: string;  // 'up' | 'down'
  sar_distance_pct?: number;
  sar_af?: number;
  sar_ep?: number;
  // Ichimoku Cloud
  ichimoku_tenkan_sen?: number;
  ichimoku_kijun_sen?: number;
  ichimoku_senkou_span_a?: number;
  ichimoku_senkou_span_b?: number;
  ichimoku_chikou_span?: number;
  ichimoku_status?: string;
  ichimoku_tk_cross?: string;
  ichimoku_cloud_top?: number;
  ichimoku_cloud_bottom?: number;
  // SuperTrend
  supertrend?: number;
  supertrend_direction?: string; // 'up' | 'down'
  // StochRSI
  stoch_rsi_k?: number;
  stoch_rsi_d?: number;
  stoch_rsi_status?: string; // 'oversold' | 'overbought' | 'neutral'
  // Volume Profile
  vp_poc?: number;
  vp_vah?: number;
  vp_val?: number;
  vp_status?: string; // 'above_va' | 'below_va' | 'inside_va'
  // 其他指标
  volatility_20?: number;
  volume_ratio?: number;
  obv_trend?: string;
  consecutive_up_days?: number;
  consecutive_down_days?: number;
  pivot?: number;
  pivot_r1?: number;
  pivot_r2?: number;
  pivot_r3?: number;
  pivot_s1?: number;
  pivot_s2?: number;
  pivot_s3?: number;
  fundamental_data?: FundamentalData;
  resistance_20d_high?: number;
  support_20d_low?: number;
  [key: string]: any;
}

/**
 * 交易信号
 */
export interface Signals {
  buy?: boolean;
  sell?: boolean;
  score?: number;
  recommendation?: string;
  risk?: {
    level: string;
    score: number;
  };
  [key: string]: any;
}

/**
 * 技术分析结果
 */
export interface AnalysisResult {
  success: boolean;
  message?: string;
  error_code?: number;  // 错误代码（如200表示证券不存在）
  indicators: Indicators;
  signals: Signals;
  candles?: Candle[];
  ai_analysis?: string;
  ai_available?: boolean;
  model?: string;
  ai_error?: string;
  [key: string]: any;
}

/**
 * 热门股票
 */
export interface HotStock {
  symbol: string;
  name: string;
  category: string;
}

/**
 * 指标信息
 */
export interface IndicatorInfo {
  name: string;
  description: string;
  calculation?: string;
  reference_range: Record<string, string>;
  interpretation: string;
  usage: string;
}

/**
 * 基本面数据 - 详细类型定义
 */
export interface FundamentalData {
  // 基本信息
  CompanyName?: string;
  Exchange?: string;
  Employees?: number;
  SharesOutstanding?: number;
  
  // 市值与价格
  MarketCap?: number;
  Price?: number;
  '52WeekHigh'?: number;
  '52WeekLow'?: number;
  
  // 财务指标
  RevenueTTM?: number;
  NetIncomeTTM?: number;
  EBITDATTM?: number;
  ProfitMargin?: number;
  GrossMargin?: number;
  OperatingMargin?: number;
  
  // 每股数据
  EPS?: number;
  ForwardEPS?: number;
  BookValuePerShare?: number;
  CashPerShare?: number;
  DividendPerShare?: number;
  
  // 估值指标
  PE?: number;
  ForwardPE?: number;
  PriceToBook?: number;
  ROE?: number;
  ROA?: number;
  ROIC?: number;
  
  // 分析师预测
  TargetPrice?: number;
  TargetHighPrice?: number;
  TargetLowPrice?: number;
  ConsensusRecommendation?: number | string;
  RecommendationKey?: string;
  NumberOfAnalystOpinions?: number;
  ProjectedEPS?: number;
  ProjectedGrowthRate?: number;
  
  // 详细财务报表（新增）
  Financials?: FinancialRecord[];  // 年度财务报表
  QuarterlyFinancials?: FinancialRecord[];  // 季度财务报表
  BalanceSheet?: BalanceSheetRecord[];  // 年度资产负债表
  QuarterlyBalanceSheet?: BalanceSheetRecord[];  // 季度资产负债表
  Cashflow?: CashflowRecord[];  // 年度现金流量表
  QuarterlyCashflow?: CashflowRecord[];  // 季度现金流量表
  
  // 持有人信息
  MajorHolders?: HolderRecord[];
  InstitutionalHolders?: InstitutionalHolderRecord[];
  
  // 历史数据
  DividendHistory?: Record<string, number>;  // 日期 -> 股息金额
  StockSplits?: Record<string, number>;  // 日期 -> 分割比例
  
  // 其他字段
  [key: string]: any;
}

/**
 * 财务报表记录
 */
export interface FinancialRecord {
  index?: string;
  Date?: string;
  [key: string]: any;  // 动态字段，如 TotalRevenue, NetIncome 等
}

/**
 * 资产负债表记录
 */
export interface BalanceSheetRecord {
  index?: string;
  Date?: string;
  [key: string]: any;  // 动态字段，如 TotalAssets, TotalLiab 等
}

/**
 * 现金流量表记录
 */
export interface CashflowRecord {
  index?: string;
  Date?: string;
  [key: string]: any;  // 动态字段，如 OperatingCashFlow, CapitalExpenditure 等
}

/**
 * 持有人记录
 */
export interface HolderRecord {
  Holder?: string;
  Name?: string;
  Shares?: number | string;
  Value?: number | string;
  '% Out'?: number | string;
  Percent?: number | string;
  [key: string]: any;
}

/**
 * 机构持有人记录
 */
export interface InstitutionalHolderRecord {
  Holder?: string;
  Name?: string;
  Shares?: number | string;
  Value?: number | string;
  '% Out'?: number | string;
  Percent?: number | string;
  DateReported?: string;
  [key: string]: any;
}

/**
 * 指标信息响应
 */
export interface IndicatorInfoResponse {
  success: boolean;
  indicators?: Record<string, IndicatorInfo>;
  indicator?: string;
  info?: IndicatorInfo;
  message?: string;
}