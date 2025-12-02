# -*- coding: utf-8 -*-
"""
机器学习预测模型
"""

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler


def calculate_ml_predictions(closes, highs, lows, volumes):
    """
    使用机器学习模型进行趋势预测，增强成交量特征
    """
    result = {}
    
    # 确保有足够的数据点
    if len(closes) < 20:
        return result
    
    # 过滤无效成交量数据
    valid_volumes = volumes[volumes > 0]
    if len(valid_volumes) == 0:
        return result
        
    # 准备特征数据
    # 特征1: 过去5天的价格变化率
    price_changes = np.diff(closes) / (closes[:-1] + 1e-8)
    recent_changes = price_changes[-5:] if len(price_changes) >= 5 else price_changes
    
    # 特征2: 过去5天的成交量变化率
    volume_changes = np.diff(volumes) / (volumes[:-1] + 1e-8)
    recent_volume_changes = volume_changes[-5:] if len(volume_changes) >= 5 else volume_changes
    
    # 特征3: 当前价格相对于近期高点和低点的位置
    recent_high = np.max(highs[-10:])
    recent_low = np.min(lows[-10:])
    price_position = (closes[-1] - recent_low) / (recent_high - recent_low + 1e-8)
    
    # 特征4: 波动率
    volatility = np.std(price_changes[-10:]) if len(price_changes) >= 10 else 0
    
    # 特征5: 成交量相关特征（新增）
    # 5.1 成交量移动平均比率
    volume_ma_20 = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
    volume_ratio = volumes[-1] / (volume_ma_20 + 1e-8)
    
    # 5.2 价量关系：价格上涨时的成交量 vs 价格下跌时的成交量
    up_days = closes[-10:] > np.roll(closes[-10:], 1)
    up_days[0] = False  # 第一个元素无效
    down_days = closes[-10:] < np.roll(closes[-10:], 1)
    down_days[0] = False
    
    if np.sum(up_days) > 0 and np.sum(down_days) > 0:
        avg_volume_up = np.mean(volumes[-10:][up_days])
        avg_volume_down = np.mean(volumes[-10:][down_days])
        volume_price_ratio = avg_volume_up / (avg_volume_down + 1e-8)
    else:
        volume_price_ratio = 1.0
    
    # 5.3 成交量趋势（最近5天 vs 前5天）
    if len(volumes) >= 10:
        recent_vol_avg = np.mean(volumes[-5:])
        prev_vol_avg = np.mean(volumes[-10:-5])
        volume_trend = recent_vol_avg / (prev_vol_avg + 1e-8)
    else:
        volume_trend = 1.0
    
    # 5.4 价量背离检测
    price_trend = (closes[-1] - closes[-5]) / (closes[-5] + 1e-8) if len(closes) >= 5 else 0
    volume_trend_change = (volumes[-1] - volumes[-5]) / (volumes[-5] + 1e-8) if len(volumes) >= 5 else 0
    divergence = abs(price_trend) - abs(volume_trend_change)  # 正数表示价量背离
    
    # 创建特征向量
    features = np.concatenate([recent_changes, recent_volume_changes])
    features = np.append(features, [price_position, volatility, volume_ratio, 
                                    volume_price_ratio, volume_trend, divergence])
    
    # 简单的线性回归预测未来1天的价格变化
    # 使用过去10天的数据来训练模型
    if len(closes) >= 10:
        # 创建训练数据
        X = []
        y = []
        
        # 使用过去几天的数据来创建训练样本
        for i in range(10, len(closes)):
            # 特征：过去5天的价格变化和成交量变化
            pc = np.diff(closes[max(0, i-5):i]) / (closes[max(0, i-5):i-1] + 1e-8) if i > 1 else [0]
            vc = np.diff(volumes[max(0, i-5):i]) / (volumes[max(0, i-5):i-1] + 1e-8) if i > 1 else [0]
            
            # 填充到固定长度
            pc = np.pad(pc, (max(0, 5-len(pc)), 0), 'constant')
            vc = np.pad(vc, (max(0, 5-len(vc)), 0), 'constant')
            
            # 成交量相关特征
            vol_ma_20 = np.mean(volumes[max(0, i-20):i]) if i >= 20 else np.mean(volumes[:i])
            vol_ratio = volumes[i-1] / (vol_ma_20 + 1e-8)
            
            # 价量关系
            up_days = closes[max(0, i-10):i] > np.roll(closes[max(0, i-10):i], 1)
            up_days[0] = False
            down_days = closes[max(0, i-10):i] < np.roll(closes[max(0, i-10):i], 1)
            down_days[0] = False
            
            if np.sum(up_days) > 0 and np.sum(down_days) > 0:
                avg_vol_up = np.mean(volumes[max(0, i-10):i][up_days])
                avg_vol_down = np.mean(volumes[max(0, i-10):i][down_days])
                vol_price_ratio = avg_vol_up / (avg_vol_down + 1e-8)
            else:
                vol_price_ratio = 1.0
            
            # 成交量趋势
            if i >= 10:
                recent_vol_avg = np.mean(volumes[i-5:i])
                prev_vol_avg = np.mean(volumes[i-10:i-5])
                vol_trend = recent_vol_avg / (prev_vol_avg + 1e-8)
            else:
                vol_trend = 1.0
            
            # 价量背离
            price_trend = (closes[i-1] - closes[max(0, i-5)]) / (closes[max(0, i-5)] + 1e-8)
            vol_trend_change = (volumes[i-1] - volumes[max(0, i-5)]) / (volumes[max(0, i-5)] + 1e-8)
            divergence = abs(price_trend) - abs(vol_trend_change)
            
            # 价格位置
            recent_high = np.max(highs[max(0, i-10):i])
            recent_low = np.min(lows[max(0, i-10):i])
            price_pos = (closes[i-1] - recent_low) / (recent_high - recent_low + 1e-8)
            
            # 波动率
            vol = np.std(pc) if len(pc) > 0 else 0
            
            # 目标：下一天的价格变化率
            if i < len(closes) - 1:
                target = (closes[i+1] - closes[i]) / (closes[i] + 1e-8)
                feature_vector = np.concatenate([pc, vc, [price_pos, vol, vol_ratio, 
                                                          vol_price_ratio, vol_trend, divergence]])
                X.append(feature_vector)
                y.append(target)
        
        if len(X) > 2:
            # 训练模型
            X = np.array(X)
            y = np.array(y)
            
            # 标准化特征
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # 训练线性回归模型
            model = LinearRegression()
            model.fit(X_scaled, y)
            
            # 预测
            current_features = np.array(features).reshape(1, -1)
            current_features_scaled = scaler.transform(current_features)
            prediction = model.predict(current_features_scaled)[0]
            
            result['ml_prediction'] = float(prediction)
            result['ml_confidence'] = float(min(np.abs(prediction) * 100, 100))  # 置信度限制在100以内
            
            # 预测方向
            if prediction > 0.01:
                result['ml_trend'] = 'up'
            elif prediction < -0.01:
                result['ml_trend'] = 'down'
            else:
                result['ml_trend'] = 'sideways'
            
            # 添加成交量相关分析结果
            result['volume_ratio'] = float(volume_ratio)
            result['volume_price_ratio'] = float(volume_price_ratio)
            result['volume_trend'] = float(volume_trend)
            result['price_volume_divergence'] = float(divergence)
            
            # 价量关系判断
            if volume_ratio > 1.5:
                result['volume_signal'] = 'high_volume'  # 高成交量
            elif volume_ratio < 0.5:
                result['volume_signal'] = 'low_volume'  # 低成交量
            else:
                result['volume_signal'] = 'normal_volume'
            
            # 价量配合判断
            if price_trend > 0 and volume_price_ratio > 1.2:
                result['price_volume_confirmation'] = 'bullish'  # 价涨量增，看涨确认
            elif price_trend < 0 and volume_price_ratio < 0.8:
                result['price_volume_confirmation'] = 'bearish'  # 价跌量增，看跌确认
            elif abs(divergence) > 0.1:
                result['price_volume_confirmation'] = 'divergence'  # 价量背离
            else:
                result['price_volume_confirmation'] = 'neutral'
                
    return result

