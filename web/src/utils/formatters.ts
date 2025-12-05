/**
 * 格式化工具函数
 */

/**
 * 格式化数值
 */
export const formatValue = (value: number | undefined, decimals: number = 2): string => {
  if (value === undefined || value === null) return 'N/A';
  return typeof value === 'number' ? value.toFixed(decimals) : String(value);
};

/**
 * 格式化大数字(市值、营收等)
 */
export const formatLargeNumber = (value: number): string => {
  const absValue = Math.abs(value);
  if (absValue >= 1e12) {
    return `$${(value / 1e12).toFixed(2)}T`;
  } else if (absValue >= 1e9) {
    return `$${(value / 1e9).toFixed(2)}B`;
  } else if (absValue >= 1e6) {
    return `$${(value / 1e6).toFixed(2)}M`;
  }
  return `$${value.toFixed(2)}`;
};

/**
 * 获取RSI状态
 */
export const getRSIStatus = (rsi: number | undefined): { color: string; text: string } => {
  if (!rsi) return { color: 'default', text: '中性' };
  if (rsi < 30) return { color: 'success', text: '超卖' };
  if (rsi > 70) return { color: 'error', text: '超买' };
  return { color: 'default', text: '中性' };
};

/**
 * 状态映射配置
 */
export const statusMaps = {
  order: {
    'Filled': { color: 'success', text: '已成交' },
    'Cancelled': { color: 'default', text: '已取消' },
    'Submitted': { color: 'processing', text: '已提交' },
    'PreSubmitted': { color: 'warning', text: '预提交' },
  },
  trend: {
    'up': { color: 'success', text: '上涨' },
    'down': { color: 'error', text: '下跌' },
    'neutral': { color: 'default', text: '震荡' },
  },
  risk: {
    'very_low': { color: 'success', text: '很低风险' },
    'low': { color: 'success', text: '低风险' },
    'medium': { color: 'warning', text: '中等风险' },
    'high': { color: 'error', text: '高风险' },
    'very_high': { color: 'error', text: '极高风险' },
  },
  consensus: {
    '1': { text: '强烈买入', color: 'success' },
    '2': { text: '买入', color: 'success' },
    '3': { text: '持有', color: 'default' },
    '4': { text: '卖出', color: 'error' },
    '5': { text: '强烈卖出', color: 'error' },
  },
};
