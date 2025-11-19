/**
 * TradingView K线图组件
 * 使用 lightweight-charts 开源库显示股票K线图
 * 支持技术指标和缠论分析的可视化
 */
import React, { useEffect, useRef, useState } from 'react';
import { 
  createChart, 
  type IChartApi, 
  type ISeriesApi, 
  ColorType, 
  type Time, 
  type UTCTimestamp,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
} from 'lightweight-charts';
import type { Indicators, Candle } from '../types/index';

interface TradingViewChartProps {
  symbol: string;
  height?: number;
  width?: string | number;
  theme?: 'light' | 'dark';
  indicators?: Indicators; // 技术指标数据
  candles?: Candle[]; // K线数据
}

const TradingViewChart: React.FC<TradingViewChartProps> = ({
  symbol,
  height = 500,
  theme = 'light',
  indicators,
  candles,
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const maSeriesRefs = useRef<Map<number, ISeriesApi<'Line'>>>(new Map());
  const bbSeriesRefs = useRef<Map<string, ISeriesApi<'Line'>>>(new Map());
  const sarSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const vwapSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const pivotSeriesRefs = useRef<Map<string, ISeriesApi<'Line'>>>(new Map());
  const fractalMarkersRef = useRef<any[]>([]);
  const strokeLinesRef = useRef<ISeriesApi<'Line'>[]>([]);
  const segmentLinesRef = useRef<ISeriesApi<'Line'>[]>([]);
  const centralBankAreasRef = useRef<ISeriesApi<'Line'>[]>([]);

  // 技术指标显示状态
  const [indicatorVisibility, setIndicatorVisibility] = useState({
    ma5: false,
    ma10: false,
    ma20: false,
    ma50: false,
    bb: false,
    sar: false,
    vwap: false,
    pivotPoints: false,
    fractals: false,
    strokes: false,
    segments: false,
    centralBanks: false,
  });

  /**
   * 将时间字符串转换为 lightweight-charts 的时间格式
   */
  const parseTime = (timeStr: string): Time => {
    try {
      const date = new Date(timeStr);
      if (isNaN(date.getTime())) {
        // 尝试解析 "YYYY-MM-DD" 格式
        const parts = timeStr.split('-');
        if (parts.length === 3) {
          const year = parseInt(parts[0]);
          const month = parseInt(parts[1]) - 1;
          const day = parseInt(parts[2]);
          return new Date(year, month, day).getTime() / 1000 as UTCTimestamp;
        }
        return Date.now() / 1000 as UTCTimestamp;
      }
      return (date.getTime() / 1000) as UTCTimestamp;
    } catch {
      return Date.now() / 1000 as UTCTimestamp;
    }
  };

  /**
   * 初始化图表
   */
  useEffect(() => {
    if (!chartContainerRef.current) return;

    // 创建图表 - TradingView 风格配置
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height,
      layout: {
        background: { type: ColorType.Solid, color: theme === 'light' ? '#ffffff' : '#131722' },
        textColor: theme === 'light' ? '#191919' : '#d1d4dc',
        fontSize: 12,
      },
      grid: {
        vertLines: { 
          color: theme === 'light' ? '#e1e3eb' : '#2a2e39',
          style: 0,
          visible: true,
        },
        horzLines: { 
          color: theme === 'light' ? '#e1e3eb' : '#2a2e39',
          style: 0,
          visible: true,
        },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          color: theme === 'light' ? '#9598a1' : '#758696',
          width: 1,
          style: 3,
          labelBackgroundColor: theme === 'light' ? '#4c525e' : '#363c4e',
        },
        horzLine: {
          color: theme === 'light' ? '#9598a1' : '#758696',
          width: 1,
          style: 3,
          labelBackgroundColor: theme === 'light' ? '#4c525e' : '#363c4e',
        },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: theme === 'light' ? '#e1e3eb' : '#2a2e39',
        barSpacing: 6,
        minBarSpacing: 3,
        rightOffset: 12,
        fixLeftEdge: false,
        fixRightEdge: false,
      },
      leftPriceScale: {
        visible: true,
        borderColor: theme === 'light' ? '#e1e3eb' : '#2a2e39',
        scaleMargins: {
          top: 0.1,
          bottom: 0.2,
        },
        autoScale: true,
      },
      rightPriceScale: {
        visible: false,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: true,
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
      },
      kineticScroll: {
        mouse: true,
        touch: true,
      },
    });

    chartRef.current = chart;

    // 创建K线图系列 - TradingView 风格
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
      priceScaleId: 'left',
    });
    candleSeriesRef.current = candleSeries as ISeriesApi<'Candlestick'>;

    // 创建成交量系列 - TradingView 风格
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: '#26a69a',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
      lastValueVisible: false,
      priceLineVisible: false,
    });
    volumeSeriesRef.current = volumeSeries as ISeriesApi<'Histogram'>;
    
    // 设置成交量系列的缩放边距
    chart.priceScale('').applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });

    // 响应式调整
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [height, theme]);

  /**
   * 更新K线数据
   */
  useEffect(() => {
    if (!candleSeriesRef.current || !candles || candles.length === 0) return;

    const formattedData = candles.map(candle => ({
      time: parseTime(candle.time),
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    }));

    candleSeriesRef.current.setData(formattedData);

    // 更新成交量数据
    if (volumeSeriesRef.current) {
      const volumeData = candles.map(candle => ({
        time: parseTime(candle.time),
        value: candle.volume,
        color: candle.close >= candle.open ? '#26a69a26' : '#ef535026',
      }));
      volumeSeriesRef.current.setData(volumeData);
    }

    // 自动调整显示范围以适应数据
    if (chartRef.current && formattedData.length > 0) {
      setTimeout(() => {
        chartRef.current?.timeScale().fitContent();
      }, 100);
    }
  }, [candles]);

  /**
   * 绘制移动平均线
   */
  useEffect(() => {
    if (!chartRef.current || !indicators || !candles || candles.length === 0) return;

    const maPeriods = [
      { period: 5, value: indicators.ma5, color: '#ff9800', visible: indicatorVisibility.ma5 },
      { period: 10, value: indicators.ma10, color: '#2196f3', visible: indicatorVisibility.ma10 },
      { period: 20, value: indicators.ma20, color: '#9c27b0', visible: indicatorVisibility.ma20 },
      { period: 50, value: indicators.ma50, color: '#f44336', visible: indicatorVisibility.ma50 },
    ].filter(ma => ma.value !== undefined);

    // 清理旧的MA线
    maSeriesRefs.current.forEach((series) => {
      if (series && chartRef.current) {
        try {
          chartRef.current.removeSeries(series);
        } catch (e) {
          // 忽略已删除的系列
        }
      }
    });
    maSeriesRefs.current.clear();

    // 计算并绘制MA线
    maPeriods.forEach(({ period, color, visible }) => {
      if (!visible) return;
      
      const maData: { time: Time; value: number }[] = [];
      
      for (let i = period - 1; i < candles.length; i++) {
        const sum = candles.slice(i - period + 1, i + 1).reduce((acc, c) => acc + c.close, 0);
        const avg = sum / period;
        maData.push({
          time: parseTime(candles[i].time),
          value: avg,
        });
      }

      if (maData.length > 0 && chartRef.current) {
        const maSeries = chartRef.current.addSeries(LineSeries, {
          color: color,
          lineWidth: 1,
          title: `MA${period}`,
          priceScaleId: 'left',
          lastValueVisible: false,
          priceLineVisible: false,
        });
        maSeries.setData(maData);
        maSeriesRefs.current.set(period, maSeries as ISeriesApi<'Line'>);
      }
    });
  }, [indicators, candles, indicatorVisibility]);

  /**
   * 绘制布林带
   */
  useEffect(() => {
    if (!chartRef.current || !indicators || !candles || candles.length === 0) return;

    // 清理旧的布林带
    bbSeriesRefs.current.forEach((series) => {
      if (series && chartRef.current) {
        try {
          chartRef.current.removeSeries(series);
        } catch (e) {
          // 忽略已删除的系列
        }
      }
    });
    bbSeriesRefs.current.clear();

    if (!indicatorVisibility.bb) return;

    if (indicators.bb_upper !== undefined && indicators.bb_middle !== undefined && indicators.bb_lower !== undefined) {
      const bbData = candles.map((candle) => ({
        time: parseTime(candle.time),
        upper: indicators.bb_upper!,
        middle: indicators.bb_middle!,
        lower: indicators.bb_lower!,
      }));

      // 绘制上轨
      const upperSeries = chartRef.current.addSeries(LineSeries, {
        color: '#2196f3',
        lineWidth: 1,
        lineStyle: 2, // 虚线
        title: 'BB Upper',
        priceScaleId: 'left',
      });
      upperSeries.setData(bbData.map(d => ({ time: d.time, value: d.upper })));
      bbSeriesRefs.current.set('upper', upperSeries as ISeriesApi<'Line'>);

      // 绘制中轨
      const middleSeries = chartRef.current.addSeries(LineSeries, {
        color: '#9c27b0',
        lineWidth: 1,
        title: 'BB Middle',
        priceScaleId: 'left',
      });
      middleSeries.setData(bbData.map(d => ({ time: d.time, value: d.middle })));
      bbSeriesRefs.current.set('middle', middleSeries as ISeriesApi<'Line'>);

      // 绘制下轨
      const lowerSeries = chartRef.current.addSeries(LineSeries, {
        color: '#2196f3',
        lineWidth: 1,
        lineStyle: 2, // 虚线
        title: 'BB Lower',
        priceScaleId: 'left',
      });
      lowerSeries.setData(bbData.map(d => ({ time: d.time, value: d.lower })));
      bbSeriesRefs.current.set('lower', lowerSeries as ISeriesApi<'Line'>);
    }
  }, [indicators, candles, indicatorVisibility.bb]);

  /**
   * 绘制SAR抛物线点位
   */
  useEffect(() => {
    if (!chartRef.current || !indicators || !candles || candles.length === 0) return;

    // 清理旧的SAR线
    if (sarSeriesRef.current && chartRef.current) {
      try {
        chartRef.current.removeSeries(sarSeriesRef.current);
        sarSeriesRef.current = null;
      } catch (e) {
        // 忽略已删除的系列
      }
    }

    if (!indicatorVisibility.sar || indicators.sar === undefined) return;

    // SAR是单个值，需要显示在所有K线上
    const sarData = candles.map(candle => ({
      time: parseTime(candle.time),
      value: indicators.sar!,
    }));

    const sarSeries = chartRef.current.addSeries(LineSeries, {
      color: indicators.sar_signal === 'bullish' ? '#4caf50' : '#f44336',
      lineWidth: 2,
      lineStyle: 3, // 点状线
      title: 'SAR',
      priceScaleId: 'left',
    });
    sarSeries.setData(sarData);
    sarSeriesRef.current = sarSeries as ISeriesApi<'Line'>;
  }, [indicators, candles, indicatorVisibility.sar]);

  /**
   * 绘制VWAP线
   */
  useEffect(() => {
    if (!chartRef.current || !indicators || !candles || candles.length === 0) return;

    // 清理旧的VWAP线
    if (vwapSeriesRef.current && chartRef.current) {
      try {
        chartRef.current.removeSeries(vwapSeriesRef.current);
        vwapSeriesRef.current = null;
      } catch (e) {
        // 忽略已删除的系列
      }
    }

    if (!indicatorVisibility.vwap || indicators.vwap === undefined) return;

    // VWAP是单个值，显示为水平线
    const vwapData = candles.map(candle => ({
      time: parseTime(candle.time),
      value: indicators.vwap!,
    }));

    const vwapSeries = chartRef.current.addSeries(LineSeries, {
      color: '#ff9800',
      lineWidth: 2,
      lineStyle: 0, // 实线
      title: 'VWAP',
      priceScaleId: 'left',
    });
    vwapSeries.setData(vwapData);
    vwapSeriesRef.current = vwapSeries as ISeriesApi<'Line'>;
  }, [indicators, candles, indicatorVisibility.vwap]);

  /**
   * 绘制枢轴点位线
   */
  useEffect(() => {
    if (!chartRef.current || !indicators || !candles || candles.length === 0) return;

    // 清理旧的枢轴点线
    pivotSeriesRefs.current.forEach((series) => {
      if (series && chartRef.current) {
        try {
          chartRef.current.removeSeries(series);
        } catch (e) {
          // 忽略已删除的系列
        }
      }
    });
    pivotSeriesRefs.current.clear();

    if (!indicatorVisibility.pivotPoints) return;

    const pivotLines = [
      { key: 'pivot', value: indicators.pivot, color: '#9c27b0', name: 'P' },
      { key: 'r1', value: indicators.pivot_r1, color: '#f44336', name: 'R1' },
      { key: 'r2', value: indicators.pivot_r2, color: '#d32f2f', name: 'R2' },
      { key: 'r3', value: indicators.pivot_r3, color: '#b71c1c', name: 'R3' },
      { key: 's1', value: indicators.pivot_s1, color: '#4caf50', name: 'S1' },
      { key: 's2', value: indicators.pivot_s2, color: '#388e3c', name: 'S2' },
      { key: 's3', value: indicators.pivot_s3, color: '#2e7d32', name: 'S3' },
    ].filter(line => line.value !== undefined);

    pivotLines.forEach(({ key, value, color, name }) => {
      const pivotData = candles.map(candle => ({
        time: parseTime(candle.time),
        value: value!,
      }));

      const pivotSeries = chartRef.current?.addSeries(LineSeries, {
        color: color,
        lineWidth: 1,
        lineStyle: 2, // 虚线
        title: name,
        priceScaleId: 'left',
      });

      if (pivotSeries) {
        pivotSeries.setData(pivotData);
        pivotSeriesRefs.current.set(key, pivotSeries as ISeriesApi<'Line'>);
      }
    });
  }, [indicators, candles, indicatorVisibility.pivotPoints]);

  /**
   * 绘制缠论分型
   */
  useEffect(() => {
    if (!candleSeriesRef.current || !indicators || !candles || candles.length === 0) {
      return;
    }

    // 延迟执行，确保数据已设置完成
    const timer = setTimeout(() => {
      const series = candleSeriesRef.current;
      if (!series) return;

      // 检查 setMarkers 方法是否存在
      const seriesAny = series as any;
      if (typeof seriesAny.setMarkers !== 'function') {
        // setMarkers 方法不可用，跳过分型标记绘制
        return;
      }

      // 清理旧的分型标记
      fractalMarkersRef.current = [];

      try {
        if (!indicatorVisibility.fractals) {
          seriesAny.setMarkers([]);
          return;
        }

        if (indicators.fractals && Array.isArray(indicators.fractals)) {
          const markers: any[] = [];
          
          indicators.fractals.forEach((fractal: any) => {
            if (fractal && fractal.index !== undefined && fractal.price !== undefined) {
              const candleIndex = fractal.index;
              if (candleIndex >= 0 && candleIndex < candles.length) {
                const candle = candles[candleIndex];
                markers.push({
                  time: parseTime(candle.time),
                  position: fractal.type === 'top' ? 'aboveBar' : 'belowBar',
                  color: fractal.type === 'top' ? '#f44336' : '#4caf50',
                  shape: fractal.type === 'top' ? 'arrowDown' : 'arrowUp',
                  size: 1,
                  text: fractal.type === 'top' ? '顶' : '底',
                });
              }
            }
          });

          seriesAny.setMarkers(markers);
          fractalMarkersRef.current = markers;
        } else {
          seriesAny.setMarkers([]);
        }
      } catch (error) {
        console.error('Error setting markers:', error);
      }
    }, 50);

    return () => clearTimeout(timer);
  }, [indicators, candles, indicatorVisibility.fractals]);

  /**
   * 绘制缠论笔
   */
  useEffect(() => {
    if (!chartRef.current || !indicators || !candles || candles.length === 0) return;

    // 清理旧的笔线
    strokeLinesRef.current.forEach((series) => {
      if (series && chartRef.current) {
        try {
          chartRef.current.removeSeries(series);
        } catch (e) {
          // 忽略已删除的系列
        }
      }
    });
    strokeLinesRef.current = [];

    if (!indicatorVisibility.strokes) return;

    if (indicators.strokes && Array.isArray(indicators.strokes)) {
      indicators.strokes.forEach((stroke: any) => {
        if (stroke && stroke.start_index !== undefined && stroke.end_index !== undefined) {
          const startIdx = stroke.start_index;
          const endIdx = stroke.end_index;
          
          // 确保开始和结束索引不同，避免重复时间戳
          if (startIdx === endIdx) return;
          
          if (startIdx >= 0 && startIdx < candles.length && 
              endIdx >= 0 && endIdx < candles.length) {
            const startCandle = candles[startIdx];
            const endCandle = candles[endIdx];
            
            const startTime = parseTime(startCandle.time);
            const endTime = parseTime(endCandle.time);
            
            // 再次检查时间是否相同，确保数据有序
            if (startTime >= endTime) return;
            
            const strokeSeries = chartRef.current?.addSeries(LineSeries, {
              color: stroke.type === 'up' ? '#4caf50' : '#f44336',
              lineWidth: 2,
              lineStyle: 0, // 实线
              priceScaleId: 'left',
            });
            
            if (strokeSeries) {
              strokeSeries.setData([
                { time: startTime, value: stroke.start_price || startCandle.close },
                { time: endTime, value: stroke.end_price || endCandle.close },
              ]);
              strokeLinesRef.current.push(strokeSeries as ISeriesApi<'Line'>);
            }
          }
        }
      });
    }
  }, [indicators, candles, indicatorVisibility.strokes]);

  /**
   * 绘制缠论线段
   */
  useEffect(() => {
    if (!chartRef.current || !indicators || !candles || candles.length === 0) return;

    // 清理旧的线段
    segmentLinesRef.current.forEach((series) => {
      if (series && chartRef.current) {
        try {
          chartRef.current.removeSeries(series);
        } catch (e) {
          // 忽略已删除的系列
        }
      }
    });
    segmentLinesRef.current = [];

    if (!indicatorVisibility.segments) return;

    if (indicators.segments && Array.isArray(indicators.segments)) {
      indicators.segments.forEach((segment: any) => {
        if (segment && segment.start_index !== undefined && segment.end_index !== undefined) {
          const startIdx = segment.start_index;
          const endIdx = segment.end_index;
          
          // 确保开始和结束索引不同，避免重复时间戳
          if (startIdx === endIdx) return;
          
          if (startIdx >= 0 && startIdx < candles.length && 
              endIdx >= 0 && endIdx < candles.length) {
            const startCandle = candles[startIdx];
            const endCandle = candles[endIdx];
            
            const startTime = parseTime(startCandle.time);
            const endTime = parseTime(endCandle.time);
            
            // 再次检查时间是否相同，确保数据有序
            if (startTime >= endTime) return;
            
            const segmentSeries = chartRef.current?.addSeries(LineSeries, {
              color: segment.type === 'up' ? '#2196f3' : '#ff9800',
              lineWidth: 3,
              lineStyle: 0, // 实线
              priceScaleId: 'left',
            });
            
            if (segmentSeries) {
              segmentSeries.setData([
                { time: startTime, value: segment.start_price || startCandle.close },
                { time: endTime, value: segment.end_price || endCandle.close },
              ]);
              segmentLinesRef.current.push(segmentSeries as ISeriesApi<'Line'>);
            }
          }
        }
      });
    }
  }, [indicators, candles, indicatorVisibility.segments]);

  /**
   * 绘制缠论中枢
   */
  useEffect(() => {
    if (!chartRef.current || !indicators || !candles || candles.length === 0) return;

    // 清理旧的中枢区域
    centralBankAreasRef.current.forEach((series) => {
      if (series && chartRef.current) {
        try {
          chartRef.current.removeSeries(series);
        } catch (e) {
          // 忽略已删除的系列
        }
      }
    });
    centralBankAreasRef.current = [];

    if (!indicatorVisibility.centralBanks) return;

    if (indicators.central_banks && Array.isArray(indicators.central_banks)) {
      indicators.central_banks.forEach((centralBank: any) => {
        if (centralBank && centralBank.start_index !== undefined && centralBank.end_index !== undefined) {
          const startIdx = centralBank.start_index;
          const endIdx = centralBank.end_index;
          
          if (startIdx >= 0 && startIdx < candles.length && 
              endIdx >= 0 && endIdx < candles.length) {
            // 绘制中枢上沿
            const upperSeries = chartRef.current?.addSeries(LineSeries, {
              color: '#9c27b0',
              lineWidth: 2,
              lineStyle: 2, // 虚线
              priceScaleId: 'left',
            });
            
            // 绘制中枢下沿
            const lowerSeries = chartRef.current?.addSeries(LineSeries, {
              color: '#9c27b0',
              lineWidth: 2,
              lineStyle: 2, // 虚线
              priceScaleId: 'left',
            });
            
            if (upperSeries && lowerSeries && centralBank.high !== undefined && centralBank.low !== undefined) {
              const timeRange = [];
              for (let i = startIdx; i <= endIdx && i < candles.length; i++) {
                timeRange.push(parseTime(candles[i].time));
              }
              
              const upperData = timeRange.map(time => ({ time, value: centralBank.high }));
              const lowerData = timeRange.map(time => ({ time, value: centralBank.low }));
              
              upperSeries.setData(upperData);
              lowerSeries.setData(lowerData);
              
              centralBankAreasRef.current.push(upperSeries as ISeriesApi<'Line'>, lowerSeries as ISeriesApi<'Line'>);
            }
          }
        }
      });
    }
  }, [indicators, candles, indicatorVisibility.centralBanks]);

  /**
   * 检查是否有缠论数据
   */
  const hasChanlunData = (): boolean => {
    if (!indicators) return false;
    return !!(indicators.fractals || indicators.strokes || indicators.segments || 
              indicators.central_banks || indicators.trend_type);
  };

  /**
   * 获取缠论信息摘要
   */
  const getChanlunSummary = (): string[] => {
    if (!indicators) return [];
    
    const summary: string[] = [];
    
    if (indicators.trend_type) {
      const trendText = indicators.trend_type === 'up' ? '上涨' : 
                       indicators.trend_type === 'down' ? '下跌' : '盘整';
      summary.push(`走势类型: ${trendText}`);
    }
    
    if (indicators.fractals) {
      const fractals = Array.isArray(indicators.fractals) ? indicators.fractals : [];
      const topFractals = fractals.filter((f: any) => f?.type === 'top').length;
      const bottomFractals = fractals.filter((f: any) => f?.type === 'bottom').length;
      if (topFractals > 0 || bottomFractals > 0) {
        summary.push(`分型: 顶分型 ${topFractals}个, 底分型 ${bottomFractals}个`);
      }
    }
    
    if (indicators.strokes) {
      const strokes = Array.isArray(indicators.strokes) ? indicators.strokes : [];
      if (strokes.length > 0) {
        summary.push(`笔: ${strokes.length}条`);
      }
    }
    
    if (indicators.segments) {
      const segments = Array.isArray(indicators.segments) ? indicators.segments : [];
      if (segments.length > 0) {
        summary.push(`线段: ${segments.length}条`);
      }
    }
    
    if (indicators.central_banks) {
      const centralBanks = Array.isArray(indicators.central_banks) ? indicators.central_banks : [];
      if (centralBanks.length > 0) {
        summary.push(`中枢: ${centralBanks.length}个`);
      }
    }
    
    return summary;
  };

  if (!symbol) {
    return (
      <div style={{ 
        width: '100%', 
        height: `${height}px`, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        color: '#999',
      }}>
        请输入股票代码
      </div>
    );
  }

  /**
   * 切换指标显示状态
   */
  const toggleIndicator = (key: keyof typeof indicatorVisibility) => {
    setIndicatorVisibility(prev => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const chanlunSummary = getChanlunSummary();
  const showChanlunInfo = hasChanlunData() && chanlunSummary.length > 0;

  return (
    <div style={{ width: '100%' }}>
      {/* 技术指标控制面板 */}
      <div style={{
        marginBottom: '12px',
        padding: '8px 12px',
        backgroundColor: theme === 'light' ? '#f5f5f5' : '#1e1e1e',
        borderRadius: '4px',
        display: 'flex',
        flexWrap: 'wrap',
        gap: '8px',
        alignItems: 'center',
      }}>
        <span style={{
          fontSize: '13px',
          fontWeight: 600,
          color: theme === 'light' ? '#333' : '#fff',
          marginRight: '4px',
        }}>
          技术指标:
        </span>
        <button
          onClick={() => toggleIndicator('ma5')}
          style={{
            padding: '4px 8px',
            fontSize: '12px',
            border: `1px solid ${indicatorVisibility.ma5 ? '#2196f3' : '#ccc'}`,
            backgroundColor: indicatorVisibility.ma5 ? '#2196f3' : 'transparent',
            color: indicatorVisibility.ma5 ? '#fff' : (theme === 'light' ? '#333' : '#ccc'),
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          MA5
        </button>
        <button
          onClick={() => toggleIndicator('ma10')}
          style={{
            padding: '4px 8px',
            fontSize: '12px',
            border: `1px solid ${indicatorVisibility.ma10 ? '#2196f3' : '#ccc'}`,
            backgroundColor: indicatorVisibility.ma10 ? '#2196f3' : 'transparent',
            color: indicatorVisibility.ma10 ? '#fff' : (theme === 'light' ? '#333' : '#ccc'),
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          MA10
        </button>
        <button
          onClick={() => toggleIndicator('ma20')}
          style={{
            padding: '4px 8px',
            fontSize: '12px',
            border: `1px solid ${indicatorVisibility.ma20 ? '#2196f3' : '#ccc'}`,
            backgroundColor: indicatorVisibility.ma20 ? '#2196f3' : 'transparent',
            color: indicatorVisibility.ma20 ? '#fff' : (theme === 'light' ? '#333' : '#ccc'),
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          MA20
        </button>
        <button
          onClick={() => toggleIndicator('ma50')}
          style={{
            padding: '4px 8px',
            fontSize: '12px',
            border: `1px solid ${indicatorVisibility.ma50 ? '#2196f3' : '#ccc'}`,
            backgroundColor: indicatorVisibility.ma50 ? '#2196f3' : 'transparent',
            color: indicatorVisibility.ma50 ? '#fff' : (theme === 'light' ? '#333' : '#ccc'),
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          MA50
        </button>
        <button
          onClick={() => toggleIndicator('bb')}
          style={{
            padding: '4px 8px',
            fontSize: '12px',
            border: `1px solid ${indicatorVisibility.bb ? '#2196f3' : '#ccc'}`,
            backgroundColor: indicatorVisibility.bb ? '#2196f3' : 'transparent',
            color: indicatorVisibility.bb ? '#fff' : (theme === 'light' ? '#333' : '#ccc'),
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          布林带
        </button>
        <button
          onClick={() => toggleIndicator('sar')}
          style={{
            padding: '4px 8px',
            fontSize: '12px',
            border: `1px solid ${indicatorVisibility.sar ? '#2196f3' : '#ccc'}`,
            backgroundColor: indicatorVisibility.sar ? '#2196f3' : 'transparent',
            color: indicatorVisibility.sar ? '#fff' : (theme === 'light' ? '#333' : '#ccc'),
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          SAR
        </button>
        <button
          onClick={() => toggleIndicator('vwap')}
          style={{
            padding: '4px 8px',
            fontSize: '12px',
            border: `1px solid ${indicatorVisibility.vwap ? '#2196f3' : '#ccc'}`,
            backgroundColor: indicatorVisibility.vwap ? '#2196f3' : 'transparent',
            color: indicatorVisibility.vwap ? '#fff' : (theme === 'light' ? '#333' : '#ccc'),
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          VWAP
        </button>
        <button
          onClick={() => toggleIndicator('pivotPoints')}
          style={{
            padding: '4px 8px',
            fontSize: '12px',
            border: `1px solid ${indicatorVisibility.pivotPoints ? '#2196f3' : '#ccc'}`,
            backgroundColor: indicatorVisibility.pivotPoints ? '#2196f3' : 'transparent',
            color: indicatorVisibility.pivotPoints ? '#fff' : (theme === 'light' ? '#333' : '#ccc'),
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          枢轴点
        </button>
        {hasChanlunData() && (
          <>
            <button
              onClick={() => toggleIndicator('fractals')}
              style={{
                padding: '4px 8px',
                fontSize: '12px',
                border: `1px solid ${indicatorVisibility.fractals ? '#2196f3' : '#ccc'}`,
                backgroundColor: indicatorVisibility.fractals ? '#2196f3' : 'transparent',
                color: indicatorVisibility.fractals ? '#fff' : (theme === 'light' ? '#333' : '#ccc'),
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              分型
            </button>
            <button
              onClick={() => toggleIndicator('strokes')}
              style={{
                padding: '4px 8px',
                fontSize: '12px',
                border: `1px solid ${indicatorVisibility.strokes ? '#2196f3' : '#ccc'}`,
                backgroundColor: indicatorVisibility.strokes ? '#2196f3' : 'transparent',
                color: indicatorVisibility.strokes ? '#fff' : (theme === 'light' ? '#333' : '#ccc'),
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              笔
            </button>
            <button
              onClick={() => toggleIndicator('segments')}
              style={{
                padding: '4px 8px',
                fontSize: '12px',
                border: `1px solid ${indicatorVisibility.segments ? '#2196f3' : '#ccc'}`,
                backgroundColor: indicatorVisibility.segments ? '#2196f3' : 'transparent',
                color: indicatorVisibility.segments ? '#fff' : (theme === 'light' ? '#333' : '#ccc'),
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              线段
            </button>
            <button
              onClick={() => toggleIndicator('centralBanks')}
              style={{
                padding: '4px 8px',
                fontSize: '12px',
                border: `1px solid ${indicatorVisibility.centralBanks ? '#2196f3' : '#ccc'}`,
                backgroundColor: indicatorVisibility.centralBanks ? '#2196f3' : 'transparent',
                color: indicatorVisibility.centralBanks ? '#fff' : (theme === 'light' ? '#333' : '#ccc'),
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              中枢
            </button>
          </>
        )}
      </div>
      <div
        ref={chartContainerRef}
        style={{ width: '100%', height: `${height}px` }}
      />
      {showChanlunInfo && (
        <div style={{
          marginTop: '12px',
          padding: '12px',
          backgroundColor: theme === 'light' ? '#f5f5f5' : '#1e1e1e',
          borderRadius: '4px',
          fontSize: '13px',
          color: theme === 'light' ? '#666' : '#ccc',
        }}>
          <div style={{ 
            fontWeight: 600, 
            marginBottom: '8px',
            color: theme === 'light' ? '#333' : '#fff',
          }}>
            缠论分析:
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
            {chanlunSummary.map((item, index) => (
              <span key={index}>{item}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default TradingViewChart;
