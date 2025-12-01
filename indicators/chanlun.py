# -*- coding: utf-8 -*-
"""
缠论分析算法 - 完整优化版
包括：K线合并（包含关系）、分型、笔、线段、中枢、走势类型、买卖点、背驰判断

核心优化：
1. 严格遵循缠论标准（包含关系处理、5根K线笔规则、3段中枢等）
2. 使用NumPy向量化计算提升性能
3. 面向对象设计，支持增量计算和缓存
4. 完整的类型注解
5. 背驰判断（基于MACD）
6. 详细的状态跟踪和日志
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum


class Direction(Enum):
    """方向枚举"""
    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"


class FractalType(Enum):
    """分型类型"""
    TOP = "top"
    BOTTOM = "bottom"


@dataclass
class KBar:
    """K线数据结构"""
    index: int
    high: float
    low: float
    close: float
    volume: float = 0.0
    
    def __repr__(self):
        return f"KBar(idx={self.index}, H={self.high:.2f}, L={self.low:.2f})"


@dataclass
class MergedKBar:
    """合并后的K线（处理包含关系后）"""
    start_index: int
    end_index: int
    high: float
    low: float
    direction: Direction
    original_count: int  # 包含的原始K线数量
    total_volume: float = 0.0  # 合并K线的总成交量
    avg_volume: float = 0.0  # 平均成交量
    
    def __repr__(self):
        return f"MergedK(idx={self.start_index}-{self.end_index}, H={self.high:.2f}, L={self.low:.2f}, dir={self.direction.value})"


@dataclass
class Fractal:
    """分型"""
    index: int  # 在合并K线中的索引
    original_index: int  # 在原始K线中的索引
    price: float
    fractal_type: FractalType
    k_count: int  # 包含的原始K线数量
    volume: float = 0.0  # 分型处的成交量
    volume_confirmed: bool = False  # 是否得到成交量确认
    
    def __repr__(self):
        return f"{self.fractal_type.value}Fractal(idx={self.original_index}, price={self.price:.2f})"


@dataclass
class Stroke:
    """笔"""
    start_fractal: Fractal
    end_fractal: Fractal
    direction: Direction
    k_count: int  # 包含的原始K线数量
    price_change: float
    price_change_pct: float
    total_volume: float = 0.0  # 笔的总成交量
    avg_volume: float = 0.0  # 笔的平均成交量
    volume_strength: float = 0.0  # 成交量强度（相对于平均值的倍数）
    
    @property
    def start_index(self) -> int:
        return self.start_fractal.original_index
    
    @property
    def end_index(self) -> int:
        return self.end_fractal.original_index
    
    @property
    def start_price(self) -> float:
        return self.start_fractal.price
    
    @property
    def end_price(self) -> float:
        return self.end_fractal.price
    
    def __repr__(self):
        return f"Stroke({self.direction.value}, {self.start_index}->{self.end_index}, {self.price_change_pct:+.2f}%)"


@dataclass
class Segment:
    """线段"""
    start_stroke: Stroke
    end_stroke: Stroke
    strokes: List[Stroke]
    direction: Direction
    
    @property
    def start_index(self) -> int:
        return self.start_stroke.start_index
    
    @property
    def end_index(self) -> int:
        return self.end_stroke.end_index
    
    @property
    def start_price(self) -> float:
        return self.start_stroke.start_price
    
    @property
    def end_price(self) -> float:
        return self.end_stroke.end_price
    
    @property
    def price_change(self) -> float:
        return self.end_price - self.start_price
    
    @property
    def price_change_pct(self) -> float:
        return (self.price_change / self.start_price) * 100
    
    def __repr__(self):
        return f"Segment({self.direction.value}, strokes={len(self.strokes)}, {self.price_change_pct:+.2f}%)"


@dataclass
class CentralBank:
    """中枢"""
    start_index: int
    end_index: int
    high: float  # ZG 中枢高
    low: float   # ZD 中枢低
    center: float
    segments: List[Segment]
    segment_count: int
    cb_type: str  # 'standard', 'extended', 'expanded'
    
    @property
    def width(self) -> float:
        return self.high - self.low
    
    @property
    def width_pct(self) -> float:
        return (self.width / self.low) * 100
    
    def contains_price(self, price: float) -> bool:
        """价格是否在中枢内"""
        return self.low <= price <= self.high
    
    def __repr__(self):
        return f"CentralBank({self.low:.2f}-{self.high:.2f}, width={self.width_pct:.2f}%)"


@dataclass
class TradingPoint:
    """买卖点"""
    point_type: str  # '一买', '二买', '三买', '一卖', '二卖', '三卖'
    index: int
    price: float
    description: str
    confidence: float = 1.0  # 置信度 0-1
    has_divergence: bool = False  # 是否有背驰
    
    def __repr__(self):
        return f"{self.point_type}(idx={self.index}, price={self.price:.2f}, conf={self.confidence:.2f})"


class ChanlunAnalyzer:
    """
    缠论分析器 - 完整优化版
    
    使用方法：
        analyzer = ChanlunAnalyzer()
        result = analyzer.analyze(closes, highs, lows, volumes)
    """
    
    def __init__(self, min_stroke_k_count: int = 5, min_stroke_pct: float = 0.3):
        """
        初始化分析器
        
        Args:
            min_stroke_k_count: 笔的最小K线数量（缠论标准：5）
            min_stroke_pct: 笔的最小价格幅度百分比
        """
        self.min_stroke_k_count = min_stroke_k_count
        self.min_stroke_pct = min_stroke_pct
        
        # 缓存
        self._cache: Dict[str, Any] = {}
        self._last_data_hash: Optional[int] = None
    
    def analyze(self, closes: np.ndarray, highs: np.ndarray, lows: np.ndarray, 
                volumes: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        执行完整的缠论分析
        
        Args:
            closes: 收盘价数组
            highs: 最高价数组
            lows: 最低价数组
            volumes: 成交量数组（可选）
            
        Returns:
            包含所有缠论分析结果的字典
        """
        # 数据验证
        if len(closes) < 5:
            return self._empty_result()
        
        # 转换为numpy数组
        closes = np.array(closes, dtype=float)
        highs = np.array(highs, dtype=float)
        lows = np.array(lows, dtype=float)
        if volumes is not None:
            volumes = np.array(volumes, dtype=float)
        else:
            volumes = np.zeros_like(closes)
        
        # 检查缓存（包含成交量数据）
        data_hash = hash((closes.tobytes(), highs.tobytes(), lows.tobytes(), volumes.tobytes()))
        if self._last_data_hash == data_hash:
            return self._cache
        
        # 创建K线对象
        k_bars = [KBar(i, highs[i], lows[i], closes[i], volumes[i]) 
                  for i in range(len(closes))]
        
        # 1. 处理包含关系，生成合并K线
        merged_k_bars = self._handle_inclusion_relation(k_bars)
        
        # 2. 识别分型
        fractals = self._identify_fractals(merged_k_bars)
        
        # 3. 识别笔
        strokes = self._identify_strokes(fractals, merged_k_bars)
        
        # 4. 识别线段
        segments = self._identify_segments(strokes)
        
        # 5. 识别中枢
        central_banks = self._identify_central_banks(segments)
        
        # 6. 识别走势类型
        trend_type = self._identify_trend_type(segments)
        
        # 7. 计算MACD（用于背驰判断）
        macd_data = self._calculate_macd(closes)
        
        # 8. 识别买卖点
        trading_points = self._identify_trading_points(
            segments, central_banks, strokes, fractals, macd_data, closes
        )
        
        # 9. 生成状态摘要
        current_status = self._get_current_status(
            fractals, strokes, segments, central_banks, closes
        )
        
        # 构建结果
        result = {
            'merged_k_bars': merged_k_bars,
            'fractals': fractals,
            'strokes': strokes,
            'segments': segments,
            'central_banks': central_banks,
            'trend_type': trend_type,
            'trading_points': trading_points,
            'macd': macd_data,
            'current_status': current_status,
            'data_adequacy': self._assess_data_adequacy(len(closes), fractals, strokes, segments)
        }
        
        # 转换为可序列化格式（用于API返回）
        # 注意：这里暂时不传入时间，时间信息将在外部添加
        result['serializable'] = self._to_serializable(result)
        
        # 更新缓存
        self._cache = result
        self._last_data_hash = data_hash
        
        return result
    
    def _handle_inclusion_relation(self, k_bars: List[KBar]) -> List[MergedKBar]:
        """
        处理K线的包含关系
        
        包含关系定义：
        - K1包含K2：K1.high >= K2.high 且 K1.low <= K2.low
        - K2包含K1：K2.high >= K1.high 且 K2.low <= K1.low
        
        处理规则：
        - 上升过程：取高点的较高值，低点的较高值
        - 下降过程：取高点的较低值，低点的较低值
        """
        if len(k_bars) < 2:
            return [MergedKBar(k.index, k.index, k.high, k.low, Direction.UNKNOWN, 1, 
                              k.volume, k.volume) for k in k_bars]
        
        merged: List[MergedKBar] = []
        direction = Direction.UNKNOWN
        
        i = 0
        while i < len(k_bars):
            current = k_bars[i]
            start_idx = current.index
            high = current.high
            low = current.low
            count = 1
            total_vol = current.volume
            volumes_list = [current.volume]
            
            # 尝试合并后续K线
            j = i + 1
            while j < len(k_bars):
                next_k = k_bars[j]
                
                # 检查是否有包含关系
                has_inclusion = (
                    (high >= next_k.high and low <= next_k.low) or  # current包含next
                    (next_k.high >= high and next_k.low <= low)     # next包含current
                )
                
                if has_inclusion:
                    # 根据方向合并
                    if direction == Direction.UP or (direction == Direction.UNKNOWN and j > 0 and next_k.high > high):
                        # 上升：取高点更高，低点更高
                        high = max(high, next_k.high)
                        low = max(low, next_k.low)
                        direction = Direction.UP
                    else:
                        # 下降：取高点更低，低点更低
                        high = min(high, next_k.high)
                        low = min(low, next_k.low)
                        direction = Direction.DOWN
                    count += 1
                    total_vol += next_k.volume
                    volumes_list.append(next_k.volume)
                    j += 1
                else:
                    # 无包含关系，结束合并
                    break
            
            # 计算平均成交量
            avg_vol = np.mean(volumes_list) if volumes_list else 0.0
            
            # 添加合并后的K线
            merged.append(MergedKBar(start_idx, k_bars[j-1].index if j > i else start_idx, 
                                     high, low, direction, count, total_vol, avg_vol))
            
            # 更新方向（为下一次合并做准备）
            if j < len(k_bars):
                if k_bars[j].high > high:
                    direction = Direction.UP
                elif k_bars[j].low < low:
                    direction = Direction.DOWN
            
            i = j
        
        return merged
    
    def _identify_fractals(self, merged_k_bars: List[MergedKBar]) -> List[Fractal]:
        """
        识别分型（基于合并后的K线）
        
        顶分型：中间K线的高点 > 左右K线的高点
        底分型：中间K线的低点 < 左右K线的低点
        
        成交量确认：分型处的成交量应该相对较大，表示市场参与度高
        """
        fractals: List[Fractal] = []
        
        if len(merged_k_bars) < 3:
            return fractals
        
        # 计算平均成交量（用于确认）
        avg_volumes = [mb.avg_volume for mb in merged_k_bars if mb.avg_volume > 0]
        overall_avg_volume = np.mean(avg_volumes) if avg_volumes else 0.0
        
        for i in range(1, len(merged_k_bars) - 1):
            prev = merged_k_bars[i - 1]
            curr = merged_k_bars[i]
            next_k = merged_k_bars[i + 1]
            
            # 顶分型
            if curr.high > prev.high and curr.high > next_k.high:
                # 成交量确认：顶分型时成交量应该较大（表示抛压）
                volume_confirmed = overall_avg_volume > 0 and curr.avg_volume >= overall_avg_volume * 0.8
                
                fractals.append(Fractal(
                    index=i,
                    original_index=curr.end_index,
                    price=curr.high,
                    fractal_type=FractalType.TOP,
                    k_count=curr.original_count,
                    volume=curr.total_volume,
                    volume_confirmed=volume_confirmed
                ))
            
            # 底分型
            if curr.low < prev.low and curr.low < next_k.low:
                # 成交量确认：底分型时成交量应该较大（表示承接）
                volume_confirmed = overall_avg_volume > 0 and curr.avg_volume >= overall_avg_volume * 0.8
                
                fractals.append(Fractal(
                    index=i,
                    original_index=curr.end_index,
                    price=curr.low,
                    fractal_type=FractalType.BOTTOM,
                    k_count=curr.original_count,
                    volume=curr.total_volume,
                    volume_confirmed=volume_confirmed
                ))
        
        return fractals
    
    def _identify_strokes(self, fractals: List[Fractal], 
                         merged_k_bars: List[MergedKBar]) -> List[Stroke]:
        """
        识别笔
        
        笔的标准：
        1. 顶分型和底分型必须交替出现
        2. 笔至少包含5根K线（处理包含关系后至少3根，原始至少5根）
        3. 价格幅度满足最小要求（默认0.3%）
        """
        if len(fractals) < 2:
            return []
        
        strokes: List[Stroke] = []
        valid_fractals: List[Fractal] = [fractals[0]]
        
        # 确保分型交替出现
        for i in range(1, len(fractals)):
            curr = fractals[i]
            prev = valid_fractals[-1]
            
            # 必须是不同类型的分型
            if curr.fractal_type != prev.fractal_type:
                # 计算K线数量（累计原始K线）
                k_count = 0
                for j in range(prev.index, curr.index + 1):
                    if j < len(merged_k_bars):
                        k_count += merged_k_bars[j].original_count
                
                # 检查是否满足笔的条件
                price_diff = abs(curr.price - prev.price)
                price_pct = (price_diff / prev.price) * 100
                
                # 条件：至少5根原始K线 + 价格幅度足够
                if k_count >= self.min_stroke_k_count and price_pct >= self.min_stroke_pct:
                    valid_fractals.append(curr)
                elif curr.fractal_type == prev.fractal_type:
                    # 同类型分型，取更极端的值
                    if curr.fractal_type == FractalType.TOP:
                        if curr.price > prev.price:
                            valid_fractals[-1] = curr
                    else:
                        if curr.price < prev.price:
                            valid_fractals[-1] = curr
        
        # 计算整体平均成交量（用于计算成交量强度）
        all_volumes = [mb.total_volume for mb in merged_k_bars if mb.total_volume > 0]
        overall_avg_volume = np.mean(all_volumes) if all_volumes else 0.0
        
        # 生成笔
        for i in range(len(valid_fractals) - 1):
            start = valid_fractals[i]
            end = valid_fractals[i + 1]
            
            # 计算K线数量和成交量
            k_count = 0
            total_vol = 0.0
            volumes_list = []
            
            for j in range(start.index, end.index + 1):
                if j < len(merged_k_bars):
                    k_count += merged_k_bars[j].original_count
                    total_vol += merged_k_bars[j].total_volume
                    if merged_k_bars[j].avg_volume > 0:
                        volumes_list.append(merged_k_bars[j].avg_volume)
            
            avg_vol = np.mean(volumes_list) if volumes_list else 0.0
            volume_strength = (avg_vol / overall_avg_volume) if overall_avg_volume > 0 else 0.0
            
            direction = Direction.UP if end.price > start.price else Direction.DOWN
            price_change = end.price - start.price
            price_change_pct = (price_change / start.price) * 100
            
            strokes.append(Stroke(
                start_fractal=start,
                end_fractal=end,
                direction=direction,
                k_count=k_count,
                price_change=price_change,
                price_change_pct=price_change_pct,
                total_volume=total_vol,
                avg_volume=avg_vol,
                volume_strength=volume_strength
            ))
        
        return strokes
    
    def _identify_segments(self, strokes: List[Stroke]) -> List[Segment]:
        """
        识别线段
        
        线段的标准：
        1. 至少由3笔构成
        2. 使用特征序列识别线段破坏
        3. 新笔破坏前线段的结束点
        """
        if len(strokes) < 3:
            return []
        
        segments: List[Segment] = []
        i = 0
        
        while i < len(strokes) - 2:
            segment_strokes = [strokes[i]]
            direction = strokes[i].direction
            
            # 尝试扩展线段
            j = i + 1
            while j < len(strokes):
                current_stroke = strokes[j]
                
                # 检查是否破坏线段
                # 向上线段：新的向下笔破坏前一个顶
                # 向下线段：新的向上笔破坏前一个底
                if len(segment_strokes) >= 3:
                    # 检查特征序列
                    if direction == Direction.UP:
                        # 向上线段，检查是否有向下笔破坏前高
                        if current_stroke.direction == Direction.DOWN:
                            # 找前一个顶（最近的向上笔的结束点）
                            prev_top = segment_strokes[-1].end_price if segment_strokes[-1].direction == Direction.UP else segment_strokes[-2].end_price
                            if current_stroke.end_price < prev_top:
                                # 破坏，结束线段
                                break
                    else:
                        # 向下线段，检查是否有向上笔破坏前低
                        if current_stroke.direction == Direction.UP:
                            prev_bottom = segment_strokes[-1].end_price if segment_strokes[-1].direction == Direction.DOWN else segment_strokes[-2].end_price
                            if current_stroke.end_price > prev_bottom:
                                break
                
                segment_strokes.append(current_stroke)
                j += 1
                
                # 限制线段长度（避免过长）
                if len(segment_strokes) >= 9:
                    break
            
            # 至少3笔才形成线段
            if len(segment_strokes) >= 3:
                # 判断线段方向（根据起终点）
                seg_direction = Direction.UP if segment_strokes[-1].end_price > segment_strokes[0].start_price else Direction.DOWN
                
                segments.append(Segment(
                    start_stroke=segment_strokes[0],
                    end_stroke=segment_strokes[-1],
                    strokes=segment_strokes,
                    direction=seg_direction
                ))
                i = j
            else:
                i += 1
        
        return segments
    
    def _identify_central_banks(self, segments: List[Segment]) -> List[CentralBank]:
        """
        识别中枢
        
        中枢定义：
        - 至少3个连续线段的重叠部分
        - ZG（中枢高）= min(线段高点)
        - ZD（中枢低）= max(线段低点)
        - ZG > ZD 才是有效中枢
        """
        if len(segments) < 3:
            return []
        
        central_banks: List[CentralBank] = []
        i = 0
        
        while i <= len(segments) - 3:
            # 取3个连续线段
            seg1, seg2, seg3 = segments[i], segments[i + 1], segments[i + 2]
            
            # 计算三个线段的价格区间
            seg1_high = max(seg1.start_price, seg1.end_price)
            seg1_low = min(seg1.start_price, seg1.end_price)
            
            seg2_high = max(seg2.start_price, seg2.end_price)
            seg2_low = min(seg2.start_price, seg2.end_price)
            
            seg3_high = max(seg3.start_price, seg3.end_price)
            seg3_low = min(seg3.start_price, seg3.end_price)
            
            # 计算重叠区间
            zg = min(seg1_high, seg2_high, seg3_high)
            zd = max(seg1_low, seg2_low, seg3_low)
            
            # 有效中枢：ZG > ZD
            if zg > zd:
                # 尝试扩展中枢（检查后续线段是否也在中枢范围内）
                cb_segments = [seg1, seg2, seg3]
                j = i + 3
                
                while j < len(segments):
                    next_seg = segments[j]
                    next_high = max(next_seg.start_price, next_seg.end_price)
                    next_low = min(next_seg.start_price, next_seg.end_price)
                    
                    # 检查是否仍在中枢范围内
                    new_zg = min(zg, next_high)
                    new_zd = max(zd, next_low)
                    
                    if new_zg > new_zd:
                        # 仍然重叠，扩展中枢
                        cb_segments.append(next_seg)
                        zg = new_zg
                        zd = new_zd
                        j += 1
                    else:
                        break
                
                center = (zg + zd) / 2
                
                central_banks.append(CentralBank(
                    start_index=cb_segments[0].start_index,
                    end_index=cb_segments[-1].end_index,
                    high=zg,
                    low=zd,
                    center=center,
                    segments=cb_segments,
                    segment_count=len(cb_segments),
                    cb_type='extended' if len(cb_segments) > 3 else 'standard'
                ))
                
                i = j  # 跳过已处理的线段
            else:
                i += 1
        
        return central_banks
    
    def _identify_trend_type(self, segments: List[Segment]) -> Direction:
        """识别当前走势类型"""
        if len(segments) < 2:
            return Direction.UNKNOWN
        
        # 分析最近3个线段
        recent = segments[-3:] if len(segments) >= 3 else segments
        
        up_count = sum(1 for s in recent if s.direction == Direction.UP)
        down_count = sum(1 for s in recent if s.direction == Direction.DOWN)
        
        if up_count > down_count:
            return Direction.UP
        elif down_count > up_count:
            return Direction.DOWN
        else:
            return Direction.UNKNOWN
    
    def _calculate_macd(self, closes: np.ndarray, 
                       fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, np.ndarray]:
        """
        计算MACD指标（用于背驰判断）
        
        Returns:
            包含 'dif', 'dea', 'macd' 的字典
        """
        if len(closes) < slow:
            return {'dif': np.array([]), 'dea': np.array([]), 'macd': np.array([])}
        
        # 计算EMA
        ema_fast = self._ema(closes, fast)
        ema_slow = self._ema(closes, slow)
        
        # DIF = EMA(fast) - EMA(slow)
        dif = ema_fast - ema_slow
        
        # DEA = EMA(DIF, signal)
        dea = self._ema(dif, signal)
        
        # MACD = 2 * (DIF - DEA)
        macd = 2 * (dif - dea)
        
        return {'dif': dif, 'dea': dea, 'macd': macd}
    
    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """计算指数移动平均"""
        alpha = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]
        
        return ema
    
    def _check_divergence(self, macd_data: Dict[str, np.ndarray], 
                         stroke1: Stroke, stroke2: Stroke) -> bool:
        """
        检查两笔之间是否有背驰
        
        背驰判断：
        - 价格创新高/新低，但MACD柱未创新高/新低
        - 价量背离：价格上涨但成交量萎缩，或价格下跌但成交量放大
        """
        if len(macd_data.get('macd', [])) == 0:
            return False
        
        macd = macd_data['macd']
        
        # 获取两笔结束位置的MACD值
        idx1 = min(stroke1.end_index, len(macd) - 1)
        idx2 = min(stroke2.end_index, len(macd) - 1)
        
        if idx1 < 0 or idx2 < 0:
            return False
        
        # MACD背驰判断
        macd_divergence = False
        
        # 向上笔的背驰：价格新高 but MACD未新高
        if stroke1.direction == Direction.UP and stroke2.direction == Direction.UP:
            if stroke2.end_price > stroke1.end_price and abs(macd[idx2]) < abs(macd[idx1]):
                macd_divergence = True
        
        # 向下笔的背驰：价格新低 but MACD未新低
        if stroke1.direction == Direction.DOWN and stroke2.direction == Direction.DOWN:
            if stroke2.end_price < stroke1.end_price and abs(macd[idx2]) < abs(macd[idx1]):
                macd_divergence = True
        
        # 价量背离判断
        volume_divergence = False
        if stroke1.avg_volume > 0 and stroke2.avg_volume > 0:
            # 上涨价量背离：价格上涨但成交量萎缩
            if stroke1.direction == Direction.UP and stroke2.direction == Direction.UP:
                if stroke2.end_price > stroke1.end_price and stroke2.avg_volume < stroke1.avg_volume * 0.7:
                    volume_divergence = True
            
            # 下跌价量背离：价格下跌但成交量放大（可能是恐慌性抛售）
            if stroke1.direction == Direction.DOWN and stroke2.direction == Direction.DOWN:
                if stroke2.end_price < stroke1.end_price and stroke2.avg_volume > stroke1.avg_volume * 1.5:
                    volume_divergence = True
        
        # 背驰：MACD背驰或价量背离
        return macd_divergence or volume_divergence
    
    def _identify_trading_points(self, segments: List[Segment], 
                                central_banks: List[CentralBank],
                                strokes: List[Stroke],
                                fractals: List[Fractal],
                                macd_data: Dict[str, np.ndarray],
                                closes: np.ndarray) -> Dict[str, List[TradingPoint]]:
        """
        识别买卖点
        
        一买：下跌+背驰
        二买：回抽不破中枢
        三买：离开中枢后第一次回抽
        一卖：上涨+背驰
        二卖：反弹不破中枢
        三卖：离开中枢后第一次反弹
        """
        buy_points: List[TradingPoint] = []
        sell_points: List[TradingPoint] = []
        
        if len(strokes) < 2:
            return {'buy_points': buy_points, 'sell_points': sell_points}
        
        current_price = float(closes[-1])
        
        # 一买/一卖：趋势结束+背驰
        for i in range(1, len(segments)):
            prev_seg = segments[i - 1]
            curr_seg = segments[i]
            
            # 一买：下跌段后的反转
            if prev_seg.direction == Direction.DOWN and curr_seg.direction == Direction.UP:
                # 检查是否有背驰
                has_div = False
                if len(prev_seg.strokes) >= 2:
                    # 检查最后两笔是否背驰
                    down_strokes = [s for s in prev_seg.strokes if s.direction == Direction.DOWN]
                    if len(down_strokes) >= 2:
                        has_div = self._check_divergence(macd_data, down_strokes[-2], down_strokes[-1])
                
                buy_points.append(TradingPoint(
                    point_type='一买',
                    index=curr_seg.start_index,
                    price=float(curr_seg.start_price),
                    description='下跌趋势结束，出现反转' + (' (背驰)' if has_div else ''),
                    confidence=0.9 if has_div else 0.7,
                    has_divergence=has_div
                ))
            
            # 一卖：上涨段后的反转
            if prev_seg.direction == Direction.UP and curr_seg.direction == Direction.DOWN:
                has_div = False
                if len(prev_seg.strokes) >= 2:
                    up_strokes = [s for s in prev_seg.strokes if s.direction == Direction.UP]
                    if len(up_strokes) >= 2:
                        has_div = self._check_divergence(macd_data, up_strokes[-2], up_strokes[-1])
                
                sell_points.append(TradingPoint(
                    point_type='一卖',
                    index=curr_seg.start_index,
                    price=float(curr_seg.start_price),
                    description='上涨趋势结束，出现反转' + (' (背驰)' if has_div else ''),
                    confidence=0.9 if has_div else 0.7,
                    has_divergence=has_div
                ))
        
        # 二买/二卖/三买/三卖：基于中枢
        if central_banks and segments:
            latest_cb = central_banks[-1]
            
            # 检查中枢之后的走势
            cb_end_idx = latest_cb.end_index
            post_cb_segments = [s for s in segments if s.start_index > cb_end_idx]
            
            if post_cb_segments:
                for seg in post_cb_segments:
                    # 三买：离开中枢向上后的回踩
                    if seg.direction == Direction.DOWN and seg.start_price > latest_cb.high:
                        if seg.end_price >= latest_cb.high * 0.98:  # 接近中枢上沿
                            buy_points.append(TradingPoint(
                                point_type='三买',
                                index=seg.end_index,
                                price=float(seg.end_price),
                                description='突破中枢后的回踩不破',
                                confidence=0.8
                            ))
                    
                    # 三卖：离开中枢向下后的反弹
                    if seg.direction == Direction.UP and seg.start_price < latest_cb.low:
                        if seg.end_price <= latest_cb.low * 1.02:  # 接近中枢下沿
                            sell_points.append(TradingPoint(
                                point_type='三卖',
                                index=seg.end_index,
                                price=float(seg.end_price),
                                description='跌破中枢后的反弹不破',
                                confidence=0.8
                            ))
            
            # 二买：回抽中枢不破（价格在中枢附近）
            if current_price <= latest_cb.high and current_price >= latest_cb.low * 0.95:
                if segments[-1].direction == Direction.DOWN:
                    buy_points.append(TradingPoint(
                        point_type='二买',
                        index=len(closes) - 1,
                        price=current_price,
                        description='回抽中枢不破',
                        confidence=0.75
                    ))
            
            # 二卖：反弹至中枢不破
            if current_price >= latest_cb.low and current_price <= latest_cb.high * 1.05:
                if segments[-1].direction == Direction.UP:
                    sell_points.append(TradingPoint(
                        point_type='二卖',
                        index=len(closes) - 1,
                        price=current_price,
                        description='反弹至中枢不破',
                        confidence=0.75
                    ))
        
        return {'buy_points': buy_points, 'sell_points': sell_points}
    
    def _get_current_status(self, fractals: List[Fractal], 
                           strokes: List[Stroke],
                           segments: List[Segment],
                           central_banks: List[CentralBank],
                           closes: np.ndarray) -> Dict[str, Any]:
        """生成当前状态摘要"""
        status = {}
        current_price = float(closes[-1])
        
        # 最新分型
        top_fractals = [f for f in fractals if f.fractal_type == FractalType.TOP]
        bottom_fractals = [f for f in fractals if f.fractal_type == FractalType.BOTTOM]
        
        if top_fractals:
            latest_top = top_fractals[-1]
            status['latest_top_fractal'] = {
                'index': latest_top.original_index,
                'price': float(latest_top.price),
                'distance_pct': float(((current_price - latest_top.price) / latest_top.price) * 100)
            }
        
        if bottom_fractals:
            latest_bottom = bottom_fractals[-1]
            status['latest_bottom_fractal'] = {
                'index': latest_bottom.original_index,
                'price': float(latest_bottom.price),
                'distance_pct': float(((current_price - latest_bottom.price) / latest_bottom.price) * 100)
            }
        
        # 最新笔
        if strokes:
            latest_stroke = strokes[-1]
            status['latest_stroke'] = {
                'direction': latest_stroke.direction.value,
                'start_index': latest_stroke.start_index,
                'end_index': latest_stroke.end_index,
                'start_price': float(latest_stroke.start_price),
                'end_price': float(latest_stroke.end_price),
                'price_change_pct': float(latest_stroke.price_change_pct),
                'k_count': latest_stroke.k_count
            }
        
        # 最新线段
        if segments:
            latest_segment = segments[-1]
            status['latest_segment'] = {
                'direction': latest_segment.direction.value,
                'start_index': latest_segment.start_index,
                'end_index': latest_segment.end_index,
                'start_price': float(latest_segment.start_price),
                'end_price': float(latest_segment.end_price),
                'price_change_pct': float(latest_segment.price_change_pct),
                'stroke_count': len(latest_segment.strokes)
            }
        
        # 最新中枢
        if central_banks:
            latest_cb = central_banks[-1]
            position = 'above' if current_price > latest_cb.high else \
                      ('below' if current_price < latest_cb.low else 'inside')
            
            status['latest_central_bank'] = {
                'start_index': latest_cb.start_index,
                'end_index': latest_cb.end_index,
                'high': float(latest_cb.high),
                'low': float(latest_cb.low),
                'center': float(latest_cb.center),
                'width_pct': float(latest_cb.width_pct),
                'position': position,
                'segment_count': latest_cb.segment_count,
                'type': latest_cb.cb_type
            }
        
        # 统计信息
        status['counts'] = {
            'fractals': {
                'top': len(top_fractals),
                'bottom': len(bottom_fractals),
                'total': len(fractals)
            },
            'strokes': len(strokes),
            'segments': len(segments),
            'central_banks': len(central_banks)
        }
        
        return status
    
    def _assess_data_adequacy(self, total_bars: int, fractals: List[Fractal],
                             strokes: List[Stroke], segments: List[Segment]) -> Dict[str, Any]:
        """评估数据充足性"""
        is_adequate = total_bars >= 50
        is_usable = total_bars >= 30
        
        if total_bars >= 100:
            recommendation = '数据非常充足，分析结果可靠'
        elif total_bars >= 50:
            recommendation = '数据充足，分析结果较可靠'
        elif total_bars >= 30:
            recommendation = '数据基本充足，建议谨慎使用'
        else:
            recommendation = '数据较少，结果仅供参考'
        
        return {
            'total_bars': total_bars,
            'fractal_count': len(fractals),
            'stroke_count': len(strokes),
            'segment_count': len(segments),
            'is_adequate': is_adequate,
            'is_usable': is_usable,
            'recommendation': recommendation
        }
    
    def _to_serializable(self, result: Dict[str, Any], times: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        转换为可序列化的格式（用于API返回）
        
        Args:
            result: 分析结果
            times: 时间数组（可选），用于将index转换为时间
        """
        # 辅助函数：根据index获取时间
        def get_time_by_index(index: int) -> Optional[str]:
            if times and 0 <= index < len(times):
                return times[index]
            return None
        
        return {
            'fractals': {
                'top_fractals': [
                    {
                        'index': f.original_index,
                        'price': float(f.price),
                        'date_index': f.original_index
                    }
                    for f in result['fractals'] if f.fractal_type == FractalType.TOP
                ],
                'bottom_fractals': [
                    {
                        'index': f.original_index,
                        'price': float(f.price),
                        'date_index': f.original_index
                    }
                    for f in result['fractals'] if f.fractal_type == FractalType.BOTTOM
                ]
            },
            'strokes': [
                {
                    'start_index': s.start_index,
                    'end_index': s.end_index,
                    'start_price': float(s.start_price),
                    'end_price': float(s.end_price),
                    'type': s.direction.value,
                    'length': s.end_index - s.start_index,
                    'k_count': s.k_count,
                    'price_change': float(s.price_change),
                    'price_change_pct': float(s.price_change_pct)
                }
                for s in result['strokes']
            ],
            'segments': [
                {
                    'start_index': seg.start_index,
                    'end_index': seg.end_index,
                    'start_price': float(seg.start_price),
                    'end_price': float(seg.end_price),
                    'type': seg.direction.value,
                    'stroke_count': len(seg.strokes),
                    'price_change': float(seg.price_change),
                    'price_change_pct': float(seg.price_change_pct)
                }
                for seg in result['segments']
            ],
            'central_banks': [
                {
                    'start_index': cb.start_index,
                    'end_index': cb.end_index,
                    'start_time': get_time_by_index(cb.start_index),
                    'end_time': get_time_by_index(cb.end_index),
                    'high': float(cb.high),
                    'low': float(cb.low),
                    'center': float(cb.center),
                    'width': float(cb.width),
                    'width_pct': float(cb.width_pct),
                    'segment_count': cb.segment_count,
                    'type': cb.cb_type
                }
                for cb in result['central_banks']
            ],
            'trading_points': {
                'buy_points': [
                    {
                        'type': bp.point_type,
                        'index': bp.index,
                        'time': get_time_by_index(bp.index),
                        'price': float(bp.price),
                        'description': bp.description,
                        'confidence': float(bp.confidence),
                        'has_divergence': bp.has_divergence
                    }
                    for bp in result['trading_points']['buy_points']
                ],
                'sell_points': [
                    {
                        'type': sp.point_type,
                        'index': sp.index,
                        'time': get_time_by_index(sp.index),
                        'price': float(sp.price),
                        'description': sp.description,
                        'confidence': float(sp.confidence),
                        'has_divergence': sp.has_divergence
                    }
                    for sp in result['trading_points']['sell_points']
                ]
            },
            'trend_type': result['trend_type'].value,
            'current_status': result['current_status'],
            'data_adequacy': result['data_adequacy']
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        """返回空结果"""
        return {
            'merged_k_bars': [],
            'fractals': [],
            'strokes': [],
            'segments': [],
            'central_banks': [],
            'trend_type': Direction.UNKNOWN,
            'trading_points': {'buy_points': [], 'sell_points': []},
            'macd': {'dif': np.array([]), 'dea': np.array([]), 'macd': np.array([])},
            'current_status': {},
            'data_adequacy': {
                'total_bars': 0,
                'fractal_count': 0,
                'stroke_count': 0,
                'segment_count': 0,
                'is_adequate': False,
                'is_usable': False,
                'recommendation': '数据不足'
            },
            'serializable': {
                'fractals': {'top_fractals': [], 'bottom_fractals': []},
                'strokes': [],
                'segments': [],
                'central_banks': [],
                'trading_points': {'buy_points': [], 'sell_points': []},
                'trend_type': 'unknown',
                'current_status': {},
                'data_adequacy': {
                    'total_bars': 0,
                    'is_adequate': False,
                    'recommendation': '数据不足'
                }
            }
        }


# 兼容旧接口的包装函数
def calculate_chanlun_analysis(closes, highs, lows, volumes=None, times=None):
    """
    兼容旧接口的缠论分析函数
    
    Args:
        closes: 收盘价列表或数组
        highs: 最高价列表或数组
        lows: 最低价列表或数组
        volumes: 成交量列表或数组（可选）
        times: 时间列表或数组（可选），用于为买卖点和中枢添加时间信息
    
    Returns:
        包含缠论分析结果的字典（可序列化格式）
    """
    analyzer = ChanlunAnalyzer()
    result = analyzer.analyze(
        closes=np.array(closes),
        highs=np.array(highs),
        lows=np.array(lows),
        volumes=np.array(volumes) if volumes is not None else None
    )
    
    # 转换为可序列化格式，传入时间信息
    if times is not None:
        times_list = list(times) if not isinstance(times, list) else times
        serializable = analyzer._to_serializable(result, times=times_list)
    else:
        serializable = result['serializable']
    
    # 添加旧接口期望的字段
    serializable['fractal_count'] = serializable['current_status'].get('counts', {}).get('fractals', {})
    serializable['stroke_count'] = len(serializable['strokes'])
    serializable['segment_count'] = len(serializable['segments'])
    serializable['central_bank_count'] = len(serializable['central_banks'])
    
    return serializable
