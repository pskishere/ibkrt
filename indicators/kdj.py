# -*- coding: utf-8 -*-
"""
KDJ指标（随机指标）计算
按照 Futu 公式实现
"""

import numpy as np


def calculate_kdj(closes, highs, lows, p1=9, p2=3, p3=3):
    """
    计算KDJ指标（随机指标）
    
    标准公式：
    RSV = (CLOSE - LLV(LOW, P1)) / (HHV(HIGH, P1) - LLV(LOW, P1)) * 100
    K = EMA(RSV, P2) = (2/3) * 前一日K值 + (1/3) * 当日RSV
    D = EMA(K, P3) = (2/3) * 前一日D值 + (1/3) * 当日K值
    J = 3*K - 2*D
    
    注意：标准KDJ使用EMA（指数移动平均），不是SMA（简单移动平均）
    EMA的平滑系数 = 2 / (周期 + 1)，对于周期3，系数 = 2/(3+1) = 0.5
    但传统KDJ使用固定系数：K = (2/3)*前K + (1/3)*RSV，相当于周期3的EMA
    
    参数:
        closes: 收盘价数组
        highs: 最高价数组
        lows: 最低价数组
        p1: RSV 计算周期，默认9
        p2: K 值平滑周期（EMA周期），默认3
        p3: D 值平滑周期（EMA周期），默认3
    
    返回:
        dict: 包含 kdj_k, kdj_d, kdj_j
    """
    result = {}
    
    if len(closes) < p1:
        return result
    
    # 计算 RSV 序列
    rsv_list = []
    for i in range(p1 - 1, len(closes)):
        # LLV(LOW, P1) - 最近 P1 期的最低价
        period_lows = lows[i - p1 + 1:i + 1]
        # HHV(HIGH, P1) - 最近 P1 期的最高价
        period_highs = highs[i - p1 + 1:i + 1]
        
        llv = np.min(period_lows)
        hhv = np.max(period_highs)
        
        if hhv == llv:
            rsv = 50.0
        else:
            # RSV = (CLOSE - LLV(LOW, P1)) / (HHV(HIGH, P1) - LLV(LOW, P1)) * 100
            rsv = ((closes[i] - llv) / (hhv - llv)) * 100
        rsv_list.append(rsv)
    
    if len(rsv_list) == 0:
        return result
    
    # 计算 K 序列 - 使用EMA（指数移动平均）
    # 标准KDJ: K = (2/3) * 前一日K值 + (1/3) * 当日RSV
    # 这相当于周期为3的EMA，平滑系数 = 1/3
    k_list = []
    alpha_k = 1.0 / p2  # EMA平滑系数
    
    for i in range(len(rsv_list)):
        if i == 0:
            # 初始值使用RSV
            k = rsv_list[i]
        else:
            # EMA: K = (1-alpha) * 前K + alpha * 当前RSV
            # 标准KDJ使用: K = (2/3) * 前K + (1/3) * RSV
            k = (1 - alpha_k) * k_list[i - 1] + alpha_k * rsv_list[i]
        k_list.append(k)
    
    # 计算 D 序列 - 使用EMA（指数移动平均）
    # 标准KDJ: D = (2/3) * 前一日D值 + (1/3) * 当日K值
    d_list = []
    alpha_d = 1.0 / p3  # EMA平滑系数
    
    for i in range(len(k_list)):
        if i == 0:
            # 初始值使用K值
            d = k_list[i]
        else:
            # EMA: D = (1-alpha) * 前D + alpha * 当前K
            # 标准KDJ使用: D = (2/3) * 前D + (1/3) * K
            d = (1 - alpha_d) * d_list[i - 1] + alpha_d * k_list[i]
        d_list.append(d)
    
    # 计算 J = 3*K - 2*D
    j_list = [3 * k - 2 * d for k, d in zip(k_list, d_list)]
    
    # 返回最新的 KDJ 值
    if len(k_list) > 0 and len(d_list) > 0 and len(j_list) > 0:
        result['kdj_k'] = float(k_list[-1])
        result['kdj_d'] = float(d_list[-1])
        result['kdj_j'] = float(j_list[-1])
    
    return result

