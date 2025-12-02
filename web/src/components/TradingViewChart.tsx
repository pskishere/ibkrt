/**
 * TradingView K线图组件
 * 使用 lightweight-charts 开源库显示股票K线图
 * 支持技术指标的可视化
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

  // 技术指标显示状态
  const [indicatorVisibility, setIndicatorVisibility] = useState({
    ma5: false,
    ma10: false,
    ma20: false,
    ma50: false,
    bb: false,
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
          bottom: 0.35, // 为成交量留出更多底部空间，增加间距
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

    // 设置时间格式化 - 只显示日期，格式为 YYYY-MM-DD
    chart.applyOptions({
      localization: {
        timeFormatter: (businessDayOrTime: Time) => {
          let timestamp: number;
          if (typeof businessDayOrTime === 'number') {
            timestamp = businessDayOrTime * 1000;
          } else if (typeof businessDayOrTime === 'object' && 'year' in businessDayOrTime) {
            // BusinessDay 类型
            const { year, month, day } = businessDayOrTime;
            timestamp = new Date(year, month - 1, day).getTime();
          } else {
            timestamp = Date.now();
          }
          const date = new Date(timestamp);
          const year = date.getFullYear();
          const month = String(date.getMonth() + 1).padStart(2, '0');
          const day = String(date.getDate()).padStart(2, '0');
          return `${year}-${month}-${day}`;
        },
      },
    });

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

    // 创建成交量系列 - 显示在底部独立窗格
    // 使用独立的priceScale，显示在图表底部
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: '#26a69a',
      priceFormat: {
        type: 'volume',
        precision: 0,
      },
      priceScaleId: 'volume', // 使用独立的priceScale
      lastValueVisible: true, // 显示最新值
      priceLineVisible: false,
    });
    volumeSeriesRef.current = volumeSeries as ISeriesApi<'Histogram'>;

    // 设置成交量价格轴（显示在底部，与K线图有明显分隔）
    chart.priceScale('volume').applyOptions({
      scaleMargins: {
        top: 0.7, // 顶部留出70%空间给K线图，增加间距
        bottom: 0.05, // 底部留5%空间
      },
      entireTextOnly: false,
      visible: true,
      borderColor: theme === 'light' ? '#e1e3eb' : '#2a2e39',
      autoScale: true,
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
    if (volumeSeriesRef.current && candles.length > 0) {
      const volumeData = candles.map(candle => ({
        time: parseTime(candle.time),
        value: candle.volume || 0, // 确保有值
        color: candle.close >= candle.open 
          ? '#26a69a80' // 上涨时使用半透明绿色
          : '#ef535080', // 下跌时使用半透明红色
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
   * 绘制布林带趋势线
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

    // 调试：打印布林带数据
    console.log('布林带指标数据:', {
      has_upper_series: !!indicators.bb_upper_series,
      has_middle_series: !!indicators.bb_middle_series,
      has_lower_series: !!indicators.bb_lower_series,
      upper_series_length: indicators.bb_upper_series?.length,
      middle_series_length: indicators.bb_middle_series?.length,
      lower_series_length: indicators.bb_lower_series?.length,
      bb_upper: indicators.bb_upper,
      bb_middle: indicators.bb_middle,
      bb_lower: indicators.bb_lower,
    });

    // 使用历史序列数据绘制趋势线
    if (indicators.bb_upper_series && indicators.bb_middle_series && indicators.bb_lower_series) {
      const upperSeries = indicators.bb_upper_series;
      const middleSeries = indicators.bb_middle_series;
      const lowerSeries = indicators.bb_lower_series;

      // 布林带数据从第20个K线开始（period=20）
      const startIndex = candles.length - upperSeries.length;

      // 绘制上轨趋势线
      const upperData = upperSeries.map((value, idx) => ({
        time: parseTime(candles[startIndex + idx].time),
        value: value,
      }));

      const upperLine = chartRef.current.addSeries(LineSeries, {
        color: '#FF6B6B',
        lineWidth: 1,
        title: 'BB上轨',
        priceScaleId: 'left',
        lastValueVisible: false,
        priceLineVisible: false,
      });
      upperLine.setData(upperData);
      bbSeriesRefs.current.set('upper', upperLine as ISeriesApi<'Line'>);

      // 绘制中轨趋势线
      const middleData = middleSeries.map((value, idx) => ({
        time: parseTime(candles[startIndex + idx].time),
        value: value,
      }));

      const middleLine = chartRef.current.addSeries(LineSeries, {
        color: '#FFD93D',
        lineWidth: 1,
        title: 'BB中轨',
        priceScaleId: 'left',
        lastValueVisible: false,
        priceLineVisible: false,
      });
      middleLine.setData(middleData);
      bbSeriesRefs.current.set('middle', middleLine as ISeriesApi<'Line'>);

      // 绘制下轨趋势线
      const lowerData = lowerSeries.map((value, idx) => ({
        time: parseTime(candles[startIndex + idx].time),
        value: value,
      }));

      const lowerLine = chartRef.current.addSeries(LineSeries, {
        color: '#6BCB77',
        lineWidth: 1,
        title: 'BB下轨',
        priceScaleId: 'left',
        lastValueVisible: false,
        priceLineVisible: false,
      });
      lowerLine.setData(lowerData);
      bbSeriesRefs.current.set('lower', lowerLine as ISeriesApi<'Line'>);
    }
    // 向后兼容：如果没有历史序列，使用旧的静态值方式
    else if (indicators.bb_upper !== undefined && indicators.bb_middle !== undefined && indicators.bb_lower !== undefined) {
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
          布林线
        </button>
      </div>
      <div
        ref={chartContainerRef}
        style={{ width: '100%', height: `${height}px` }}
      />
    </div>
  );
};

export default TradingViewChart;
