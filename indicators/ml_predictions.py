# -*- coding: utf-8 -*-
"""
机器学习预测模型
"""

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler


def calculate_ml_predictions(closes, highs, lows, volumes):
    """
    使用简单的机器学习模型进行趋势预测
    """
    result = {}
    
    # 确保有足够的数据点
    if len(closes) < 10:
        return result
        
    # 准备特征数据
    # 特征1: 过去5天的价格变化率
    price_changes = np.diff(closes) / closes[:-1]
    recent_changes = price_changes[-5:] if len(price_changes) >= 5 else price_changes
    
    # 特征2: 过去5天的成交量变化率
    volume_changes = np.diff(volumes) / (volumes[:-1] + 1e-8)  # 避免除以零
    recent_volume_changes = volume_changes[-5:] if len(volume_changes) >= 5 else volume_changes
    
    # 特征3: 当前价格相对于近期高点和低点的位置
    recent_high = np.max(highs[-10:])
    recent_low = np.min(lows[-10:])
    price_position = (closes[-1] - recent_low) / (recent_high - recent_low + 1e-8)
    
    # 特征4: 波动率
    volatility = np.std(price_changes[-10:]) if len(price_changes) >= 10 else 0
    
    # 创建特征向量
    features = np.concatenate([recent_changes, recent_volume_changes])
    features = np.append(features, [price_position, volatility])
    
    # 简单的线性回归预测未来1天的价格变化
    # 使用过去10天的数据来训练模型
    if len(closes) >= 10:
        # 创建训练数据
        X = []
        y = []
        
        # 使用过去几天的数据来创建训练样本
        for i in range(5, len(closes)):
            # 特征：过去5天的价格变化和成交量变化
            pc = np.diff(closes[max(0, i-5):i]) / closes[max(0, i-5):i-1] if i > 1 else [0]
            vc = np.diff(volumes[max(0, i-5):i]) / (volumes[max(0, i-5):i-1] + 1e-8) if i > 1 else [0]
            
            # 填充到固定长度
            pc = np.pad(pc, (max(0, 5-len(pc)), 0), 'constant')
            vc = np.pad(vc, (max(0, 5-len(vc)), 0), 'constant')
            
            # 目标：下一天的价格变化率
            if i < len(closes) - 1:
                target = (closes[i+1] - closes[i]) / closes[i]
                X.append(np.concatenate([pc, vc]))
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
            current_features = np.array(features[:10]).reshape(1, -1)
            current_features_scaled = scaler.transform(current_features)
            prediction = model.predict(current_features_scaled)[0]
            
            result['ml_prediction'] = float(prediction)
            result['ml_confidence'] = float(np.abs(prediction) * 100)  # 简单的置信度计算
            
            # 预测方向
            if prediction > 0.01:
                result['ml_trend'] = 'up'
            elif prediction < -0.01:
                result['ml_trend'] = 'down'
            else:
                result['ml_trend'] = 'sideways'
                
    return result

