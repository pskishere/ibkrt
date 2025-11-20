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
  fundamental_data?: any;
  // 缠论分析（优化版）
  fractals?: {
    top_fractals: Array<{
      index: number;
      price: number;
      date_index: number;
    }>;
    bottom_fractals: Array<{
      index: number;
      price: number;
      date_index: number;
    }>;
  };
  strokes?: Array<{
    start_index: number;
    end_index: number;
    start_price: number;
    end_price: number;
    type: 'up' | 'down';
    length: number;
    k_count: number;  // 包含的原始K线数量
    price_change: number;
    price_change_pct: number;
  }>;
  segments?: Array<{
    start_index: number;
    end_index: number;
    start_price: number;
    end_price: number;
    type: 'up' | 'down';
    stroke_count: number;  // 包含的笔数量
    price_change: number;
    price_change_pct: number;
  }>;
  central_banks?: Array<{
    start_index: number;
    end_index: number;
    high: number;  // ZG 中枢高
    low: number;   // ZD 中枢低
    center: number;
    width: number;
    width_pct: number;
    segment_count: number;  // 包含的线段数量
    type: 'standard' | 'extended' | 'expanded';
  }>;
  trading_points?: {
    buy_points: Array<{
      type: string;  // '一买', '二买', '三买'
      index: number;
      price: number;
      description: string;
      confidence: number;  // 置信度 0-1
      has_divergence: boolean;  // 是否有背驰
    }>;
    sell_points: Array<{
      type: string;  // '一卖', '二卖', '三卖'
      index: number;
      price: number;
      description: string;
      confidence: number;
      has_divergence: boolean;
    }>;
  };
  trend_type?: 'up' | 'down' | 'unknown';  // 缠论走势类型
  data_adequacy?: {
    total_bars: number;
    fractal_count: number;
    stroke_count: number;
    segment_count: number;
    central_bank_count: number;
    is_adequate: boolean;
    recommendation: string;
  };
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
 * 指标信息响应
 */
export interface IndicatorInfoResponse {
  success: boolean;
  indicators?: Record<string, IndicatorInfo>;
  indicator?: string;
  info?: IndicatorInfo;
  message?: string;
}

