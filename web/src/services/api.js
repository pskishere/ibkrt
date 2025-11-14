/**
 * API服务 - 封装所有后端API调用
 */
import axios from 'axios';

// API基础URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

// 创建axios实例
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * 处理API响应
 */
const handleResponse = (response) => {
  return response.data;
};

/**
 * 处理API错误
 */
const handleError = (error) => {
  if (error.response) {
    // 服务器返回了错误状态码
    throw new Error(error.response.data?.message || `请求失败: ${error.response.status}`);
  } else if (error.request) {
    // 请求已发出但没有收到响应
    throw new Error('无法连接到服务器，请检查后端服务是否运行');
  } else {
    // 其他错误
    throw new Error(error.message || '请求失败');
  }
};

/**
 * 获取持仓列表
 */
export const getPositions = async () => {
  try {
    const response = await api.get('/api/positions');
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 获取订单列表
 */
export const getOrders = async () => {
  try {
    const response = await api.get('/api/orders');
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 买入股票
 */
export const buy = async (symbol, quantity, limitPrice = null) => {
  try {
    const orderData = {
      symbol: symbol.toUpperCase(),
      action: 'BUY',
      quantity: quantity,
      order_type: limitPrice ? 'LMT' : 'MKT',
    };
    
    if (limitPrice) {
      orderData.limit_price = limitPrice;
    }
    
    const response = await api.post('/api/order', orderData);
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 卖出股票
 */
export const sell = async (symbol, quantity, limitPrice = null) => {
  try {
    const orderData = {
      symbol: symbol.toUpperCase(),
      action: 'SELL',
      quantity: quantity,
      order_type: limitPrice ? 'LMT' : 'MKT',
    };
    
    if (limitPrice) {
      orderData.limit_price = limitPrice;
    }
    
    const response = await api.post('/api/order', orderData);
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 撤销订单
 */
export const cancelOrder = async (orderId) => {
  try {
    const response = await api.delete(`/api/order/${orderId}`);
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 技术分析 - 后端会自动检测 Ollama 并执行AI分析
 * @param {string} symbol - 股票代码
 * @param {string} duration - 数据周期，默认 '3 M'
 * @param {string} barSize - K线周期，默认 '1 day'
 * @param {string} model - AI模型名称，默认 'deepseek-v3.1:671b-cloud'（仅在Ollama可用时使用）
 */
export const analyze = async (symbol, duration = '3 M', barSize = '1 day', model = 'deepseek-v3.1:671b-cloud') => {
  try {
    const params = new URLSearchParams({
      duration: duration,
      bar_size: barSize,
      model: model, // 传递模型参数，后端会在Ollama可用时使用
    });
    
    const response = await api.get(`/api/analyze/${symbol.toUpperCase()}?${params.toString()}`, {
      timeout: 60000, // AI分析可能需要更长时间
    });
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * AI分析 - 兼容接口，实际调用 analyze 函数
 * @param {string} symbol - 股票代码
 * @param {string} duration - 数据周期，默认 '3 M'
 * @param {string} barSize - K线周期，默认 '1 day'
 * @param {string} model - AI模型名称，默认 'deepseek-v3.1:671b-cloud'
 */
export const aiAnalyze = async (symbol, duration = '3 M', barSize = '1 day', model = 'deepseek-v3.1:671b-cloud') => {
  // 直接调用统一的 analyze 接口，后端会自动检测 Ollama
  return analyze(symbol, duration, barSize, model);
};

/**
 * 获取热门股票列表（仅美股）
 * @param {number} limit - 返回数量限制，默认 20
 */
export const getHotStocks = async (limit = 20) => {
  try {
    const params = new URLSearchParams({
      limit: limit.toString(),
    });
    
    const response = await api.get(`/api/hot-stocks?${params.toString()}`);
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

