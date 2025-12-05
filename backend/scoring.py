#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
评分系统模块 - 基于技术指标的多维度加权评分算法
"""

import numpy as np
from typing import Dict, Tuple, Optional


class ScoringSystem:
    """多维度加权评分系统"""
    
    # 各维度权重配置
    WEIGHTS = {
        'trend': 0.25,        # 趋势方向权重
        'momentum': 0.20,     # 动量指标权重
        'volume': 0.15,       # 成交量分析权重
        'volatility': 0.10,   # 波动性权重
        'support_resistance': 0.15,  # 支撑压力权重
        'advanced': 0.15      # 高级指标权重
    }
    
    def __init__(self):
        """初始化评分系统"""
        pass
    
    def _get_adaptive_weights(self, indicators: Dict) -> Dict[str, float]:
        """
        根据股票特征动态调整权重
        
        Args:
            indicators: 技术指标字典
            
        Returns:
            调整后的权重字典
        """
        # 复制基础权重
        weights = self.WEIGHTS.copy()
        
        # 获取关键指标
        volatility = indicators.get('volatility_20', 2.0)
        trend_strength = indicators.get('trend_strength', 0)
        adx = indicators.get('adx', 0)
        volume_ratio = indicators.get('volume_ratio', 1.0)
        
        # 1. 高波动股票：增加风险管理权重，降低趋势权重
        if volatility > 4.0:
            weights['volatility'] *= 1.5
            weights['trend'] *= 0.8
            weights['momentum'] *= 0.9
        # 2. 低波动股票：增加动量权重（寻找突破机会）
        elif volatility < 1.5:
            weights['momentum'] *= 1.3
            weights['volatility'] *= 0.7
        
        # 3. 强趋势股票：增加趋势和动量权重
        if trend_strength > 70 or adx > 40:
            weights['trend'] *= 1.3
            weights['momentum'] *= 1.2
            weights['support_resistance'] *= 0.8
        # 4. 弱趋势/震荡股票：增加支撑压力位权重
        elif trend_strength < 30 or adx < 20:
            weights['support_resistance'] *= 1.4
            weights['trend'] *= 0.7
        
        # 5. 成交量异常：增加成交量权重
        if volume_ratio > 2.0:
            weights['volume'] *= 1.5
        elif volume_ratio < 0.5:
            weights['volume'] *= 0.6
        
        # 归一化权重（确保总和为1.0）
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        return weights
    
    def calculate_score(self, indicators: Dict, apply_risk_adjustment: bool = True, use_adaptive_weights: bool = True) -> Tuple[int, Dict]:
        """
        计算综合评分
        
        Args:
            indicators: 技术指标字典
            apply_risk_adjustment: 是否应用风险调整因子（默认True）
            use_adaptive_weights: 是否使用自适应权重（默认True）
            
        Returns:
            (综合评分, 详细评分字典)
            评分范围: -100 到 100
        """
        if not indicators:
            return 0, {}
        
        # 获取权重（自适应或固定）
        if use_adaptive_weights:
            weights = self._get_adaptive_weights(indicators)
        else:
            weights = self.WEIGHTS
        
        # 各维度评分
        trend_score = self._score_trend(indicators)
        momentum_score = self._score_momentum(indicators)
        volume_score = self._score_volume(indicators)
        volatility_score = self._score_volatility(indicators)
        support_resistance_score = self._score_support_resistance(indicators)
        advanced_score = self._score_advanced(indicators)
        
        # 加权综合评分（使用动态权重）
        base_score = (
            trend_score * weights['trend'] +
            momentum_score * weights['momentum'] +
            volume_score * weights['volume'] +
            volatility_score * weights['volatility'] +
            support_resistance_score * weights['support_resistance'] +
            advanced_score * weights['advanced']
        )
        
        # 风险调整因子
        risk_adjustment_factor = 1.0
        risk_level = indicators.get('risk_level', 'medium')
        
        if apply_risk_adjustment:
            # 根据风险等级调整评分
            risk_adjustment_map = {
                'very_low': 1.15,   # 低风险加成15%
                'low': 1.08,        # 低风险加成8%
                'medium': 1.0,      # 中等风险不调整
                'high': 0.85,       # 高风险惩罚15%
                'very_high': 0.70   # 极高风险惩罚30%
            }
            risk_adjustment_factor = risk_adjustment_map.get(risk_level, 1.0)
        
        # 应用风险调整
        total_score = base_score * risk_adjustment_factor
        
        # 归一化到 -100 到 100 范围
        total_score = max(-100, min(100, int(round(total_score))))
        
        # 详细评分信息
        score_details = {
            'total': total_score,
            'base_score': round(base_score, 1),
            'risk_adjustment_factor': round(risk_adjustment_factor, 3),
            'risk_level': risk_level,
            'adaptive_weights_used': use_adaptive_weights,
            'dimensions': {
                'trend': round(trend_score, 1),
                'momentum': round(momentum_score, 1),
                'volume': round(volume_score, 1),
                'volatility': round(volatility_score, 1),
                'support_resistance': round(support_resistance_score, 1),
                'advanced': round(advanced_score, 1)
            },
            'weights': {k: round(v, 3) for k, v in weights.items()},
            'base_weights': self.WEIGHTS
        }
        
        return total_score, score_details
    
    def _score_trend(self, indicators: Dict) -> float:
        """
        趋势方向评分 (-100 到 100)
        
        考虑因素:
        - MA均线排列
        - ADX趋势强度
        - SuperTrend
        - Ichimoku云层
        """
        score = 0.0
        
        # 1. MA均线排列 (权重30%)
        ma_score = 0.0
        if all(k in indicators for k in ['ma5', 'ma20', 'ma50']):
            ma5 = indicators['ma5']
            ma20 = indicators['ma20']
            ma50 = indicators['ma50']
            current_price = indicators.get('current_price', 0)
            
            if current_price > 0:
                # 多头排列: 价格 > MA5 > MA20 > MA50
                if current_price > ma5 > ma20 > ma50:
                    ma_score = 30
                # 空头排列: 价格 < MA5 < MA20 < MA50
                elif current_price < ma5 < ma20 < ma50:
                    ma_score = -30
                # 部分多头排列
                elif ma5 > ma20:
                    ma_score = 15
                # 部分空头排列
                elif ma5 < ma20:
                    ma_score = -15
        
        score += ma_score * 0.3
        
        # 2. ADX趋势强度 (权重30%)
        adx_score = 0.0
        if 'adx' in indicators:
            adx = indicators['adx']
            adx_signal = indicators.get('adx_signal', 'weak_trend')
            plus_di = indicators.get('plus_di', 0)
            minus_di = indicators.get('minus_di', 0)
            
            if adx_signal == 'strong_trend':
                if plus_di > minus_di:
                    # 强上涨趋势
                    intensity = min(adx / 50.0, 1.0)  # 归一化ADX强度
                    adx_score = 30 * intensity
                else:
                    # 强下跌趋势
                    intensity = min(adx / 50.0, 1.0)
                    adx_score = -30 * intensity
            elif adx_signal == 'trend':
                if plus_di > minus_di:
                    adx_score = 15
                else:
                    adx_score = -15
        
        score += adx_score * 0.3
        
        # 3. SuperTrend (权重20%)
        supertrend_score = 0.0
        if 'supertrend' in indicators and 'supertrend_direction' in indicators:
            st_dir = indicators['supertrend_direction']
            current_price = indicators.get('current_price', 0)
            st_price = indicators.get('supertrend', 0)
            
            if current_price > 0 and st_price > 0:
                if st_dir == 'up' and current_price > st_price:
                    supertrend_score = 20
                elif st_dir == 'down' and current_price < st_price:
                    supertrend_score = -20
        
        score += supertrend_score * 0.2
        
        # 4. Ichimoku云层 (权重20%)
        ichimoku_score = 0.0
        if all(k in indicators for k in ['ichimoku_cloud_top', 'ichimoku_cloud_bottom', 'ichimoku_status']):
            current_price = indicators.get('current_price', 0)
            cloud_top = indicators.get('ichimoku_cloud_top', 0)
            cloud_bottom = indicators.get('ichimoku_cloud_bottom', 0)
            status = indicators.get('ichimoku_status', 'unknown')
            
            if current_price > 0 and cloud_top > 0 and cloud_bottom > 0:
                if status == 'bullish':
                    ichimoku_score = 20
                elif status == 'bearish':
                    ichimoku_score = -20
                elif current_price > cloud_top:
                    ichimoku_score = 10
                elif current_price < cloud_bottom:
                    ichimoku_score = -10
        
        score += ichimoku_score * 0.2
        
        return max(-100, min(100, score))
    
    def _score_momentum(self, indicators: Dict) -> float:
        """
        动量指标评分 (-100 到 100)
        
        考虑因素:
        - RSI
        - MACD
        - KDJ
        - CCI
        - StochRSI
        """
        score = 0.0
        
        # 1. RSI (权重25%)
        rsi_score = 0.0
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            # RSI < 30: 超卖, 正分
            # RSI > 70: 超买, 负分
            if rsi < 30:
                rsi_score = 25 * (30 - rsi) / 30  # 越接近0分数越高
            elif rsi > 70:
                rsi_score = -25 * (rsi - 70) / 30  # 越接近100分数越低
        
        score += rsi_score * 0.25
        
        # 2. MACD (权重25%)
        macd_score = 0.0
        if 'macd' in indicators and 'macd_signal' in indicators:
            macd = indicators['macd']
            signal = indicators['macd_signal']
            histogram = indicators.get('macd_histogram', 0)
            
            # MACD金叉: MACD > Signal
            if macd > signal:
                macd_score = 25 * min(abs(histogram) * 10, 1.0)  # 根据柱状图强度
            else:
                macd_score = -25 * min(abs(histogram) * 10, 1.0)
        
        score += macd_score * 0.25
        
        # 3. KDJ (权重20%)
        kdj_score = 0.0
        if all(k in indicators for k in ['kdj_k', 'kdj_d', 'kdj_j']):
            k = indicators['kdj_k']
            d = indicators['kdj_d']
            j = indicators['kdj_j']
            
            # 超卖区域
            if j < 20:
                kdj_score = 20 * (20 - j) / 20
            # 超买区域
            elif j > 80:
                kdj_score = -20 * (j - 80) / 20
            # 金叉死叉
            elif k > d:
                kdj_score = 10
            elif k < d:
                kdj_score = -10
        
        score += kdj_score * 0.2
        
        # 4. CCI (权重15%)
        cci_score = 0.0
        if 'cci' in indicators:
            cci = indicators['cci']
            if cci < -100:
                cci_score = 15 * min((abs(cci) - 100) / 100, 1.0)
            elif cci > 100:
                cci_score = -15 * min((cci - 100) / 100, 1.0)
        
        score += cci_score * 0.15
        
        # 5. StochRSI (权重15%)
        stoch_rsi_score = 0.0
        if 'stoch_rsi_k' in indicators and 'stoch_rsi_d' in indicators:
            k = indicators['stoch_rsi_k']
            d = indicators['stoch_rsi_d']
            status = indicators.get('stoch_rsi_status', 'neutral')
            
            if status == 'oversold':
                if k > d:  # 金叉
                    stoch_rsi_score = 15
                else:
                    stoch_rsi_score = 8
            elif status == 'overbought':
                if k < d:  # 死叉
                    stoch_rsi_score = -15
                else:
                    stoch_rsi_score = -8
        
        score += stoch_rsi_score * 0.15
        
        return max(-100, min(100, score))
    
    def _score_volume(self, indicators: Dict) -> float:
        """
        成交量分析评分 (-100 到 100)
        
        考虑因素:
        - 价量配合
        - OBV趋势
        - Volume Profile
        - 成交量比率
        """
        score = 0.0
        
        # 1. 价量配合 (权重40%)
        price_volume_score = 0.0
        if 'price_volume_confirmation' in indicators:
            confirmation = indicators['price_volume_confirmation']
            if confirmation == 'bullish':
                price_volume_score = 40
            elif confirmation == 'bearish':
                price_volume_score = -40
            elif confirmation == 'divergence':
                price_volume_score = -20
        
        score += price_volume_score * 0.4
        
        # 2. OBV趋势 (权重30%)
        obv_score = 0.0
        if 'obv_trend' in indicators:
            obv_trend = indicators['obv_trend']
            price_change = indicators.get('price_change_pct', 0)
            
            if obv_trend == 'up' and price_change > 0:
                obv_score = 30  # 量价齐升
            elif obv_trend == 'down' and price_change < 0:
                obv_score = -30  # 量价齐跌
            elif obv_trend == 'up':
                obv_score = 15
            elif obv_trend == 'down':
                obv_score = -15
        
        score += obv_score * 0.3
        
        # 3. Volume Profile (权重20%)
        vp_score = 0.0
        if 'vp_status' in indicators:
            vp_status = indicators['vp_status']
            if vp_status == 'above_va':
                vp_score = 20
            elif vp_status == 'below_va':
                vp_score = -20
        
        score += vp_score * 0.2
        
        # 4. 成交量比率 (权重10%)
        volume_ratio_score = 0.0
        if 'volume_ratio' in indicators:
            ratio = indicators['volume_ratio']
            price_change = indicators.get('price_change_pct', 0)
            
            # 放量上涨
            if ratio > 1.5 and price_change > 0:
                volume_ratio_score = 10
            # 放量下跌
            elif ratio > 1.5 and price_change < 0:
                volume_ratio_score = -10
        
        score += volume_ratio_score * 0.1
        
        return max(-100, min(100, score))
    
    def _score_volatility(self, indicators: Dict) -> float:
        """
        波动性评分 (-100 到 100)
        
        考虑因素:
        - 波动率水平
        - 布林带位置
        - ATR
        """
        score = 0.0
        
        # 1. 布林带位置 (权重50%)
        bb_score = 0.0
        if all(k in indicators for k in ['bb_upper', 'bb_lower', 'bb_middle', 'current_price']):
            price = indicators['current_price']
            upper = indicators['bb_upper']
            lower = indicators['bb_lower']
            middle = indicators['bb_middle']
            
            if upper > lower > 0:
                # 计算价格在布林带中的位置 (0-1)
                band_width = upper - lower
                position = (price - lower) / band_width if band_width > 0 else 0.5
                
                # 接近下轨: 正分 (可能反弹)
                if position < 0.1:
                    bb_score = 50 * (0.1 - position) / 0.1
                # 接近上轨: 负分 (可能回调)
                elif position > 0.9:
                    bb_score = -50 * (position - 0.9) / 0.1
        
        score += bb_score * 0.5
        
        # 2. 波动率 (权重30%)
        # 适中波动最优 (2-3%)，过高或过低都不利于交易
        volatility_score = 0.0
        if 'volatility_20' in indicators:
            vol = indicators['volatility_20']
            # 理想波动率区间: 2-3% (最优交易区间)
            if 2.0 <= vol <= 3.0:
                volatility_score = 30  # 最优区间
            # 次优波动率: 1.5-4.0%
            elif 1.5 <= vol < 2.0 or 3.0 < vol <= 4.0:
                volatility_score = 15  # 次优区间
            # 低波动 (缺乏交易机会)
            elif vol < 1.0:
                volatility_score = -20  # 流动性差、关注度低
            # 高波动 (风险过大)
            elif vol > 5.0:
                volatility_score = -40  # 风险极高
            elif vol > 4.0:
                volatility_score = -25  # 风险较高
        
        score += volatility_score * 0.3
        
        # 3. ATR (权重20%)
        atr_score = 0.0
        if 'atr_percent' in indicators:
            atr_pct = indicators['atr_percent']
            # 低ATR: 正分
            # 高ATR: 负分
            if atr_pct < 1.5:
                atr_score = 20
            elif atr_pct > 5.0:
                atr_score = -30
        
        score += atr_score * 0.2
        
        return max(-100, min(100, score))
    
    def _score_support_resistance(self, indicators: Dict) -> float:
        """
        支撑压力位评分 (-100 到 100)
        
        考虑因素:
        - 距离支撑/压力位的距离
        - 突破关键位
        - SAR位置
        """
        score = 0.0
        current_price = indicators.get('current_price', 0)
        
        if current_price <= 0:
            return 0.0
        
        # 1. 支撑位距离 (权重40%)
        support_score = 0.0
        if 'support_20d_low' in indicators:
            support = indicators['support_20d_low']
            dist_pct = ((current_price - support) / current_price) * 100
            
            # 接近支撑位: 正分
            if 0 < dist_pct < 2:
                support_score = 40 * (2 - dist_pct) / 2
            # 跌破支撑位: 负分
            elif dist_pct < 0:
                support_score = -40
        
        score += support_score * 0.4
        
        # 2. 压力位距离 (权重30%)
        resistance_score = 0.0
        if 'resistance_20d_high' in indicators:
            resistance = indicators['resistance_20d_high']
            dist_pct = ((resistance - current_price) / current_price) * 100
            
            # 接近压力位: 负分
            if 0 < dist_pct < 2:
                resistance_score = -30 * (2 - dist_pct) / 2
            # 突破压力位: 正分
            elif dist_pct < 0:
                resistance_score = 30
        
        score += resistance_score * 0.3
        
        # 3. SAR位置 (权重30%)
        sar_score = 0.0
        if 'sar' in indicators and 'sar_signal' in indicators:
            sar = indicators['sar']
            sar_signal = indicators.get('sar_signal', 'hold')
            sar_trend = indicators.get('sar_trend', 'neutral')
            
            if sar > 0:
                if sar_signal == 'buy':
                    if sar_trend == 'up':
                        sar_score = 25
                    else:
                        sar_score = 30  # 转向买入
                elif sar_signal == 'sell':
                    if sar_trend == 'down':
                        sar_score = -25
                    else:
                        sar_score = -30  # 转向卖出
        
        score += sar_score * 0.3
        
        return max(-100, min(100, score))
    
    def _score_advanced(self, indicators: Dict) -> float:
        """
        高级指标评分 (-100 到 100)
        
        考虑因素:
        - ML预测
        - 连续涨跌天数
        - 趋势强度
        - 威廉指标
        """
        score = 0.0
        
        # 1. ML预测 (权重20%, 降低权重避免过度依赖未验证的AI预测)
        ml_score = 0.0
        if 'ml_trend' in indicators:
            ml_trend = indicators['ml_trend']
            ml_confidence = indicators.get('ml_confidence', 0)
            ml_prediction = indicators.get('ml_prediction', 0)
            
            # 提高置信度门槛：从50提高到70
            if ml_confidence > 70:
                if ml_trend == 'up':
                    ml_score = 20 * (ml_confidence / 100)
                elif ml_trend == 'down':
                    ml_score = -20 * (ml_confidence / 100)
            # 中等置信度降低影响
            elif ml_confidence > 50:
                if ml_trend == 'up':
                    ml_score = 10 * (ml_confidence / 100)
                elif ml_trend == 'down':
                    ml_score = -10 * (ml_confidence / 100)
        
        score += ml_score * 0.2  # 从0.4降至0.2
        
        # 2. 趋势强度 (权重35%, 从30%提升以补偿ML权重降低)
        trend_strength_score = 0.0
        if 'trend_strength' in indicators and 'trend_direction' in indicators:
            strength = indicators['trend_strength']
            direction = indicators['trend_direction']
            
            if strength > 50:
                if direction == 'up':
                    trend_strength_score = 35 * (strength / 100)
                elif direction == 'down':
                    trend_strength_score = -35 * (strength / 100)
        
        score += trend_strength_score * 0.35  # 从0.3提升至0.35
        
        # 3. 连续涨跌天数 (权重25%, 从20%提升)
        consecutive_score = 0.0
        up_days = indicators.get('consecutive_up_days', 0)
        down_days = indicators.get('consecutive_down_days', 0)
        
        # 连续下跌后可能反弹
        if down_days >= 5:
            consecutive_score = 25 * min(down_days / 10, 1.0)
        # 连续上涨后可能回调
        elif up_days >= 5:
            consecutive_score = -25 * min(up_days / 10, 1.0)
        
        score += consecutive_score * 0.25  # 从0.2提升至0.25
        
        # 4. 威廉指标 (权重10%)
        wr_score = 0.0
        if 'williams_r' in indicators:
            wr = indicators['williams_r']
            if wr < -80:
                wr_score = 10 * (abs(wr) - 80) / 20
            elif wr > -20:
                wr_score = -10 * (20 - abs(wr)) / 20
        
        score += wr_score * 0.1
        
        return max(-100, min(100, score))
    
    def get_recommendation(self, score: int) -> Tuple[str, str]:
        """
        根据评分获取建议（更细粒度的阈值划分）
        
        Args:
            score: 综合评分 (-100 到 100)
            
        Returns:
            (建议文字, 操作标识)
        """
        # 更细粒度的阈值：45/25/5/-5/-25/-45
        if score >= 45:
            return '🟢 强烈买入', 'strong_buy'
        elif score >= 25:
            return '🟢 买入', 'buy'
        elif score >= 5:
            return '🟢 轻度买入', 'buy_light'
        elif score >= -5:
            return '⚪ 中性观望', 'hold'
        elif score >= -25:
            return '🔴 轻度卖出', 'sell_light'
        elif score >= -45:
            return '🔴 卖出', 'sell'
        else:
            return '🔴 强烈卖出', 'strong_sell'


# 全局评分系统实例
_scoring_system = ScoringSystem()


def calculate_comprehensive_score(indicators: Dict) -> Tuple[int, Dict]:
    """
    计算综合评分的便捷函数
    
    Args:
        indicators: 技术指标字典
        
    Returns:
        (综合评分, 详细评分字典)
    """
    return _scoring_system.calculate_score(indicators)


def get_recommendation(score: int) -> Tuple[str, str]:
    """
    获取建议的便捷函数
    
    Args:
        score: 综合评分
        
    Returns:
        (建议文字, 操作标识)
    """
    return _scoring_system.get_recommendation(score)

