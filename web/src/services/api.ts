/**
 * API服务 - 封装所有后端API调用
 */
import axios, { type AxiosResponse } from 'axios';
import type {
  ApiResponse,
  Position,
  Order,
  AnalysisResult,
  HotStock,
  IndicatorInfoResponse,
} from '../types/index';

// API基础URL - 使用相对路径，通过Nginx反向代理
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

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
const handleResponse = <T = any>(response: AxiosResponse<ApiResponse<T>>): ApiResponse<T> => {
  return response.data;
};

/**
 * 处理API错误
 */
const handleError = (error: any): never => {
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
export const getPositions = async (): Promise<ApiResponse<Position[]>> => {
  try {
    const response = await api.get<ApiResponse<Position[]>>('/api/positions');
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 获取订单列表
 */
export const getOrders = async (): Promise<ApiResponse<Order[]>> => {
  try {
    const response = await api.get<ApiResponse<Order[]>>('/api/orders');
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 买入股票
 */
export const buy = async (
  symbol: string,
  quantity: number,
  limitPrice: number | null = null
): Promise<ApiResponse> => {
  try {
    const orderData: any = {
      symbol: symbol.toUpperCase(),
      action: 'BUY',
      quantity: quantity,
      order_type: limitPrice ? 'LMT' : 'MKT',
    };

    if (limitPrice) {
      orderData.limit_price = limitPrice;
    }

    const response = await api.post<ApiResponse>('/api/order', orderData);
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 卖出股票
 */
export const sell = async (
  symbol: string,
  quantity: number,
  limitPrice: number | null = null
): Promise<ApiResponse> => {
  try {
    const orderData: any = {
      symbol: symbol.toUpperCase(),
      action: 'SELL',
      quantity: quantity,
      order_type: limitPrice ? 'LMT' : 'MKT',
    };

    if (limitPrice) {
      orderData.limit_price = limitPrice;
    }

    const response = await api.post<ApiResponse>('/api/order', orderData);
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 撤销订单
 */
export const cancelOrder = async (orderId: number): Promise<ApiResponse> => {
  try {
    const response = await api.delete<ApiResponse>(`/api/order/${orderId}`);
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 技术分析 - 后端会自动检测 Ollama 并执行AI分析
 * @param symbol - 股票代码
 * @param duration - 数据周期，默认 '3 M'
 * @param barSize - K线周期，默认 '1 day'
 * @param model - AI模型名称，默认 'deepseek-v3.1:671b-cloud'（仅在Ollama可用时使用）
 */
export const analyze = async (
  symbol: string,
  duration: string = '3 M',
  barSize: string = '1 day',
  model: string = 'deepseek-v3.1:671b-cloud'
): Promise<AnalysisResult> => {
  try {
    const params = new URLSearchParams({
      duration: duration,
      bar_size: barSize,
      model: model, // 传递模型参数，后端会在Ollama可用时使用
    });

    const response = await api.get<AnalysisResult>(
      `/api/analyze/${symbol.toUpperCase()}?${params.toString()}`,
      {
        timeout: 60000, // AI分析可能需要更长时间
      }
    );
    return handleResponse<AnalysisResult>(response) as AnalysisResult;
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * AI分析 - 兼容接口，实际调用 analyze 函数
 * @param symbol - 股票代码
 * @param duration - 数据周期，默认 '3 M'
 * @param barSize - K线周期，默认 '1 day'
 * @param model - AI模型名称，默认 'deepseek-v3.1:671b-cloud'
 */
export const aiAnalyze = async (
  symbol: string,
  duration: string = '3 M',
  barSize: string = '1 day',
  model: string = 'deepseek-v3.1:671b-cloud'
): Promise<AnalysisResult> => {
  // 直接调用统一的 analyze 接口，后端会自动检测 Ollama
  return analyze(symbol, duration, barSize, model);
};

/**
 * 获取热门股票列表（仅美股）
 * @param limit - 返回数量限制，默认 20
 */
export const getHotStocks = async (limit: number = 20): Promise<ApiResponse<HotStock[]>> => {
  try {
    const params = new URLSearchParams({
      limit: limit.toString(),
    });

    const response = await api.get<ApiResponse<HotStock[]>>(
      `/api/hot-stocks?${params.toString()}`
    );
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 获取技术指标解释和参考范围
 * @param indicator - 指标名称（可选），不提供则返回所有指标信息
 */
export const getIndicatorInfo = async (indicator: string = ''): Promise<IndicatorInfoResponse> => {
  try {
    const params = new URLSearchParams();
    if (indicator) {
      params.append('indicator', indicator);
    }

    const url = indicator
      ? `/api/indicator-info?${params.toString()}`
      : '/api/indicator-info';

    const response = await api.get<IndicatorInfoResponse>(url);
    return handleResponse(response);
  } catch (error) {
    handleError(error);
    throw error;
  }
};

/**
 * 刷新分析 - 强制重新获取数据，不使用缓存
 * @param symbol - 股票代码
 * @param duration - 数据周期，默认 '3 M'
 * @param barSize - K线周期，默认 '1 day'
 * @param model - AI模型名称，默认 'deepseek-v3.1:671b-cloud'（仅在Ollama可用时使用）
 */
export const refreshAnalyze = async (
  symbol: string,
  duration: string = '3 M',
  barSize: string = '1 day',
  model: string = 'deepseek-v3.1:671b-cloud'
): Promise<AnalysisResult> => {
  try {
    const params = new URLSearchParams({
      duration: duration,
      bar_size: barSize,
      model: model,
    });

    const response = await api.post<AnalysisResult>(
      `/api/refresh-analyze/${symbol.toUpperCase()}?${params.toString()}`,
      {},
      {
        timeout: 60000, // 刷新可能需要更长时间
      }
    );
    return handleResponse<AnalysisResult>(response) as AnalysisResult;
  } catch (error) {
    handleError(error);
    throw error;
  }
};
