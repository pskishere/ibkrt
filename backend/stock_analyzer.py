#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
股票全面分析模块 - 整合基本面、技术面、财务、机构行为等多维度分析
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import numpy as np
from .settings import logger


class StockAnalyzer:
    """股票全面分析器"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.analysis_results = {}
    
    def analyze_all(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行全面分析
        """
        try:
            results = {
                'symbol': self.symbol,
                'timestamp': datetime.now().isoformat(),
                'valuation': self.analyze_valuation(data.get('fundamental', {})),
                'financial_health': self.analyze_financial_health(data.get('fundamental', {})),
                'growth': self.analyze_growth(data.get('fundamental', {})),
                'profitability': self.analyze_profitability(data.get('fundamental', {})),
                'dividend': self.analyze_dividend(data),
                'institutional': self.analyze_institutional(data),
                'insider': self.analyze_insider(data),
                'analyst': self.analyze_analyst(data),
                'earnings': self.analyze_earnings(data),
                'esg': self.analyze_esg(data.get('sustainability', {})),
                'risk': self.assess_risk(data),
                'overall_score': {}
            }
            
            # 计算综合评分
            results['overall_score'] = self.calculate_overall_score(results)
            
            # 生成投资建议
            results['recommendation'] = self.generate_recommendation(results)
            
            logger.info(f"完成全面分析: {self.symbol}")
            return results
            
        except Exception as e:
            logger.error(f"全面分析失败: {self.symbol}, 错误: {e}")
            return None
    
    def analyze_valuation(self, fundamental: Dict) -> Dict[str, Any]:
        """
        估值分析：评估股票是否被高估或低估
        """
        try:
            pe = fundamental.get('PE', 0)
            forward_pe = fundamental.get('ForwardPE', 0)
            pb = fundamental.get('PriceToBook', 0)
            ps = fundamental.get('PriceToSales', 0)
            peg = fundamental.get('PEGRatio', 0)
            ev_revenue = fundamental.get('EVToRevenue', 0)
            ev_ebitda = fundamental.get('EVToEBITDA', 0)
            
            valuation_score = 0
            signals = []
            
            # PE分析
            if pe > 0:
                if pe < 15:
                    signals.append('✅ 市盈率偏低，可能被低估')
                    valuation_score += 2
                elif pe < 25:
                    signals.append('⚪ 市盈率适中')
                    valuation_score += 1
                elif pe < 40:
                    signals.append('⚠️ 市盈率偏高，需关注')
                else:
                    signals.append('❌ 市盈率过高，可能被高估')
            
            # PEG分析
            if peg > 0:
                if peg < 1:
                    signals.append('✅ PEG<1，价值相对合理')
                    valuation_score += 2
                elif peg < 2:
                    signals.append('⚪ PEG适中')
                    valuation_score += 1
                else:
                    signals.append('⚠️ PEG>2，估值偏高')
            
            # PB分析
            if pb > 0:
                if pb < 1:
                    signals.append('✅ 市净率<1，可能被低估')
                    valuation_score += 2
                elif pb < 3:
                    signals.append('⚪ 市净率正常')
                    valuation_score += 1
                else:
                    signals.append('⚠️ 市净率偏高')
            
            # 评估等级
            if valuation_score >= 5:
                rating = '优秀'
                level = 'excellent'
            elif valuation_score >= 3:
                rating = '良好'
                level = 'good'
            elif valuation_score >= 1:
                rating = '一般'
                level = 'fair'
            else:
                rating = '偏贵'
                level = 'expensive'
            
            return {
                'rating': rating,
                'level': level,
                'score': valuation_score,
                'metrics': {
                    'PE': pe,
                    'Forward_PE': forward_pe,
                    'PB': pb,
                    'PS': ps,
                    'PEG': peg,
                    'EV_Revenue': ev_revenue,
                    'EV_EBITDA': ev_ebitda
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"估值分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def analyze_financial_health(self, fundamental: Dict) -> Dict[str, Any]:
        """
        财务健康度分析：评估公司财务状况
        """
        try:
            current_ratio = fundamental.get('CurrentRatio', 0)
            quick_ratio = fundamental.get('QuickRatio', 0)
            debt_equity = fundamental.get('DebtToEquity', 0)
            total_debt = fundamental.get('TotalDebt', 0)
            total_cash = fundamental.get('TotalCash', 0)
            cash_flow = fundamental.get('CashFlow', 0)
            
            health_score = 0
            signals = []
            
            # 流动比率分析
            if current_ratio > 0:
                if current_ratio >= 2:
                    signals.append('✅ 流动比率优秀，短期偿债能力强')
                    health_score += 2
                elif current_ratio >= 1.5:
                    signals.append('⚪ 流动比率良好')
                    health_score += 1
                elif current_ratio >= 1:
                    signals.append('⚠️ 流动比率偏低')
                else:
                    signals.append('❌ 流动比率过低，短期偿债风险')
            
            # 速动比率分析
            if quick_ratio > 0:
                if quick_ratio >= 1:
                    signals.append('✅ 速动比率健康')
                    health_score += 1
                else:
                    signals.append('⚠️ 速动比率偏低')
            
            # 债务权益比分析
            if debt_equity >= 0:
                if debt_equity < 0.5:
                    signals.append('✅ 低杠杆，财务稳健')
                    health_score += 2
                elif debt_equity < 1:
                    signals.append('⚪ 债务水平适中')
                    health_score += 1
                elif debt_equity < 2:
                    signals.append('⚠️ 杠杆偏高')
                else:
                    signals.append('❌ 高杠杆，财务风险大')
            
            # 现金流分析
            if cash_flow > 0:
                signals.append('✅ 经营现金流为正')
                health_score += 2
            elif cash_flow < 0:
                signals.append('❌ 经营现金流为负，需关注')
            
            # 现金储备分析
            if total_cash > total_debt > 0:
                signals.append('✅ 现金储备充足，超过总债务')
                health_score += 1
            
            # 健康等级
            if health_score >= 7:
                rating = '优秀'
                level = 'excellent'
            elif health_score >= 5:
                rating = '良好'
                level = 'good'
            elif health_score >= 3:
                rating = '一般'
                level = 'fair'
            else:
                rating = '较差'
                level = 'poor'
            
            return {
                'rating': rating,
                'level': level,
                'score': health_score,
                'metrics': {
                    'current_ratio': current_ratio,
                    'quick_ratio': quick_ratio,
                    'debt_to_equity': debt_equity,
                    'total_debt': total_debt,
                    'total_cash': total_cash,
                    'cash_flow': cash_flow
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"财务健康度分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def analyze_growth(self, fundamental: Dict) -> Dict[str, Any]:
        """
        成长性分析：评估公司增长潜力
        """
        try:
            revenue_growth = fundamental.get('RevenueGrowth', 0) * 100
            earnings_growth = fundamental.get('EarningsGrowth', 0) * 100
            quarterly_revenue_growth = fundamental.get('QuarterlyRevenueGrowth', 0) * 100
            earnings_quarterly_growth = fundamental.get('EarningsQuarterlyGrowth', 0) * 100
            
            growth_score = 0
            signals = []
            
            # 营收增长分析
            if revenue_growth > 20:
                signals.append('🚀 营收高增长，增速超过20%')
                growth_score += 3
            elif revenue_growth > 10:
                signals.append('📈 营收稳健增长')
                growth_score += 2
            elif revenue_growth > 0:
                signals.append('⚪ 营收正增长')
                growth_score += 1
            else:
                signals.append('📉 营收负增长，需关注')
            
            # 盈利增长分析
            if earnings_growth > 20:
                signals.append('🚀 盈利高增长')
                growth_score += 3
            elif earnings_growth > 10:
                signals.append('📈 盈利稳健增长')
                growth_score += 2
            elif earnings_growth > 0:
                signals.append('⚪ 盈利正增长')
                growth_score += 1
            else:
                signals.append('📉 盈利负增长')
            
            # 季度增长分析
            if quarterly_revenue_growth > 15:
                signals.append('✅ 季度营收增长强劲')
                growth_score += 1
            
            # 成长等级
            if growth_score >= 6:
                rating = '高成长'
                level = 'high'
            elif growth_score >= 4:
                rating = '稳健增长'
                level = 'moderate'
            elif growth_score >= 2:
                rating = '低速增长'
                level = 'low'
            else:
                rating = '增长乏力'
                level = 'negative'
            
            return {
                'rating': rating,
                'level': level,
                'score': growth_score,
                'metrics': {
                    'revenue_growth': revenue_growth,
                    'earnings_growth': earnings_growth,
                    'quarterly_revenue_growth': quarterly_revenue_growth,
                    'earnings_quarterly_growth': earnings_quarterly_growth
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"成长性分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def analyze_profitability(self, fundamental: Dict) -> Dict[str, Any]:
        """
        盈利能力分析：评估公司赚钱能力
        """
        try:
            profit_margin = fundamental.get('ProfitMargin', 0) * 100
            operating_margin = fundamental.get('OperatingMargin', 0) * 100
            gross_margin = fundamental.get('GrossMargin', 0) * 100
            roe = fundamental.get('ROE', 0) * 100
            roa = fundamental.get('ROA', 0) * 100
            roic = fundamental.get('ROIC', 0) * 100
            
            profit_score = 0
            signals = []
            
            # 净利润率分析
            if profit_margin > 20:
                signals.append('✅ 净利润率优秀，盈利能力强')
                profit_score += 3
            elif profit_margin > 10:
                signals.append('⚪ 净利润率良好')
                profit_score += 2
            elif profit_margin > 5:
                signals.append('⚠️ 净利润率一般')
                profit_score += 1
            else:
                signals.append('❌ 净利润率偏低')
            
            # ROE分析
            if roe > 20:
                signals.append('✅ ROE优秀，股东回报高')
                profit_score += 3
            elif roe > 15:
                signals.append('⚪ ROE良好')
                profit_score += 2
            elif roe > 10:
                signals.append('⚠️ ROE一般')
                profit_score += 1
            else:
                signals.append('❌ ROE偏低')
            
            # 毛利率分析
            if gross_margin > 50:
                signals.append('✅ 毛利率优秀，定价能力强')
                profit_score += 2
            elif gross_margin > 30:
                signals.append('⚪ 毛利率健康')
                profit_score += 1
            
            # 盈利能力等级
            if profit_score >= 7:
                rating = '卓越'
                level = 'excellent'
            elif profit_score >= 5:
                rating = '优秀'
                level = 'good'
            elif profit_score >= 3:
                rating = '一般'
                level = 'fair'
            else:
                rating = '较差'
                level = 'poor'
            
            return {
                'rating': rating,
                'level': level,
                'score': profit_score,
                'metrics': {
                    'profit_margin': profit_margin,
                    'operating_margin': operating_margin,
                    'gross_margin': gross_margin,
                    'roe': roe,
                    'roa': roa,
                    'roic': roic
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"盈利能力分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def analyze_dividend(self, data: Dict) -> Dict[str, Any]:
        """
        股息分析：评估股息稳定性和收益率
        """
        try:
            fundamental = data.get('fundamental', {})
            dividends = data.get('dividends', [])
            
            dividend_yield = fundamental.get('DividendYield', 0) * 100
            payout_ratio = fundamental.get('PayoutRatio', 0) * 100
            dividend_rate = fundamental.get('DividendRate', 0)
            
            div_score = 0
            signals = []
            
            if not dividends or len(dividends) == 0:
                return {
                    'rating': '无股息',
                    'level': 'none',
                    'score': 0,
                    'metrics': {},
                    'signals': ['⚪ 该股票不分红']
                }
            
            # 股息率分析
            if dividend_yield > 4:
                signals.append('✅ 高股息率，超过4%')
                div_score += 3
            elif dividend_yield > 2:
                signals.append('⚪ 适中股息率')
                div_score += 2
            elif dividend_yield > 0:
                signals.append('⚠️ 低股息率')
                div_score += 1
            
            # 派息率分析
            if 0 < payout_ratio < 60:
                signals.append('✅ 派息率健康，可持续')
                div_score += 2
            elif payout_ratio >= 60 and payout_ratio < 80:
                signals.append('⚠️ 派息率偏高')
                div_score += 1
            elif payout_ratio >= 80:
                signals.append('❌ 派息率过高，可持续性存疑')
            
            # 分红历史稳定性
            if len(dividends) >= 5:
                recent_divs = [d['dividend'] for d in dividends[-5:]]
                if all(d > 0 for d in recent_divs):
                    # 检查是否持续增长
                    if all(recent_divs[i] <= recent_divs[i+1] for i in range(len(recent_divs)-1)):
                        signals.append('✅ 连续增长的股息，高度稳定')
                        div_score += 3
                    else:
                        signals.append('⚪ 持续分红，较为稳定')
                        div_score += 2
            
            # 评级
            if div_score >= 7:
                rating = '优秀'
                level = 'excellent'
            elif div_score >= 5:
                rating = '良好'
                level = 'good'
            elif div_score >= 3:
                rating = '一般'
                level = 'fair'
            else:
                rating = '较差'
                level = 'poor'
            
            return {
                'rating': rating,
                'level': level,
                'score': div_score,
                'metrics': {
                    'dividend_yield': dividend_yield,
                    'payout_ratio': payout_ratio,
                    'dividend_rate': dividend_rate,
                    'dividend_history_years': len(dividends)
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"股息分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def analyze_institutional(self, data: Dict) -> Dict[str, Any]:
        """
        机构持仓分析：评估机构投资者行为
        """
        try:
            inst_holders = data.get('institutional_holders', [])
            mutual_holders = data.get('mutualfund_holders', [])
            major_holders = data.get('major_holders', {})
            
            inst_score = 0
            signals = []
            
            if not inst_holders:
                signals.append('⚪ 暂无机构持仓数据')
                return {
                    'rating': '未知',
                    'level': 'unknown',
                    'score': 0,
                    'metrics': {},
                    'signals': signals
                }
            
            # 机构持仓数量分析
            num_institutions = len(inst_holders)
            if num_institutions > 500:
                signals.append('✅ 机构投资者众多，认可度高')
                inst_score += 3
            elif num_institutions > 200:
                signals.append('⚪ 机构投资者较多')
                inst_score += 2
            elif num_institutions > 50:
                signals.append('⚠️ 机构投资者较少')
                inst_score += 1
            
            # 计算机构持股比例
            try:
                shares_held = sum(h.get('Shares', 0) for h in inst_holders if 'Shares' in h)
                if shares_held > 0:
                    signals.append(f'📊 机构持股数量: {shares_held:,.0f}')
            except Exception:
                pass
            
            # 共同基金分析
            if mutual_holders and len(mutual_holders) > 100:
                signals.append('✅ 被大量共同基金持有')
                inst_score += 2
            elif mutual_holders and len(mutual_holders) > 50:
                signals.append('⚪ 有一定共同基金持有')
                inst_score += 1
            
            # 评级
            if inst_score >= 6:
                rating = '优秀'
                level = 'excellent'
            elif inst_score >= 4:
                rating = '良好'
                level = 'good'
            elif inst_score >= 2:
                rating = '一般'
                level = 'fair'
            else:
                rating = '较少'
                level = 'low'
            
            return {
                'rating': rating,
                'level': level,
                'score': inst_score,
                'metrics': {
                    'num_institutions': num_institutions,
                    'num_mutualfunds': len(mutual_holders) if mutual_holders else 0
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"机构持仓分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def analyze_insider(self, data: Dict) -> Dict[str, Any]:
        """
        内部交易分析：评估内部人员买卖行为
        """
        try:
            insider_trans = data.get('insider_transactions', [])
            insider_purchases = data.get('insider_purchases', [])
            
            insider_score = 0
            signals = []
            
            if not insider_trans:
                signals.append('⚪ 暂无内部交易数据')
                return {
                    'rating': '未知',
                    'level': 'unknown',
                    'score': 0,
                    'metrics': {},
                    'signals': signals
                }
            
            # 分析最近的内部交易
            recent_buys = 0
            recent_sells = 0
            
            for trans in insider_trans[:20]:  # 分析最近20笔
                trans_type = trans.get('Transaction', '').lower()
                if 'purchase' in trans_type or 'buy' in trans_type:
                    recent_buys += 1
                elif 'sale' in trans_type or 'sell' in trans_type:
                    recent_sells += 1
            
            # 买卖比例分析
            if recent_buys > recent_sells * 2:
                signals.append('✅ 内部人员大量买入，信心强')
                insider_score += 3
            elif recent_buys > recent_sells:
                signals.append('⚪ 内部人员净买入')
                insider_score += 2
            elif recent_sells > recent_buys * 2:
                signals.append('❌ 内部人员大量卖出，需警惕')
            elif recent_sells > recent_buys:
                signals.append('⚠️ 内部人员净卖出')
                insider_score += 1
            else:
                signals.append('⚪ 内部交易平衡')
                insider_score += 1
            
            # 内部购买分析
            if insider_purchases and len(insider_purchases) > 5:
                signals.append('✅ 近期有多笔内部购买')
                insider_score += 2
            
            # 评级
            if insider_score >= 5:
                rating = '积极'
                level = 'positive'
            elif insider_score >= 3:
                rating = '中性'
                level = 'neutral'
            else:
                rating = '消极'
                level = 'negative'
            
            return {
                'rating': rating,
                'level': level,
                'score': insider_score,
                'metrics': {
                    'recent_buys': recent_buys,
                    'recent_sells': recent_sells,
                    'total_transactions': len(insider_trans)
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"内部交易分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def analyze_analyst(self, data: Dict) -> Dict[str, Any]:
        """
        分析师意见分析：评估分析师评级和目标价
        """
        try:
            fundamental = data.get('fundamental', {})
            recommendations = data.get('recommendations', [])
            upgrades = data.get('upgrades_downgrades', [])
            
            target_mean = fundamental.get('TargetPrice', 0)
            target_high = fundamental.get('TargetHighPrice', 0)
            target_low = fundamental.get('TargetLowPrice', 0)
            current_price = fundamental.get('Price', 0)
            num_analysts = fundamental.get('NumberOfAnalystOpinions', 0)
            recommendation_key = fundamental.get('RecommendationKey', '')
            
            analyst_score = 0
            signals = []
            
            # 分析师数量分析
            if num_analysts > 20:
                signals.append('✅ 大量分析师覆盖')
                analyst_score += 1
            elif num_analysts > 10:
                signals.append('⚪ 适量分析师覆盖')
            
            # 目标价分析
            if target_mean > 0 and current_price > 0:
                upside_pct = ((target_mean - current_price) / current_price) * 100
                if upside_pct > 20:
                    signals.append(f'🚀 目标价上涨空间大: {upside_pct:.1f}%')
                    analyst_score += 3
                elif upside_pct > 10:
                    signals.append(f'📈 目标价有上涨空间: {upside_pct:.1f}%')
                    analyst_score += 2
                elif upside_pct > 0:
                    signals.append(f'⚪ 目标价略高于当前: {upside_pct:.1f}%')
                    analyst_score += 1
                else:
                    signals.append(f'📉 目标价低于当前: {upside_pct:.1f}%')
            
            # 推荐评级分析
            if recommendation_key:
                if recommendation_key in ['strong_buy', 'buy']:
                    signals.append('✅ 分析师推荐买入')
                    analyst_score += 2
                elif recommendation_key == 'hold':
                    signals.append('⚪ 分析师推荐持有')
                    analyst_score += 1
                elif recommendation_key in ['sell', 'strong_sell']:
                    signals.append('❌ 分析师推荐卖出')
            
            # 近期评级变化
            if upgrades:
                recent_upgrades = [u for u in upgrades[:10] if 'upgrade' in str(u.get('ToGrade', '')).lower()]
                recent_downgrades = [d for d in upgrades[:10] if 'downgrade' in str(d.get('ToGrade', '')).lower()]
                
                if len(recent_upgrades) > len(recent_downgrades):
                    signals.append('✅ 近期评级上调较多')
                    analyst_score += 2
                elif len(recent_downgrades) > len(recent_upgrades):
                    signals.append('⚠️ 近期评级下调较多')
            
            # 评级
            if analyst_score >= 7:
                rating = '强烈看好'
                level = 'strong_buy'
            elif analyst_score >= 5:
                rating = '看好'
                level = 'buy'
            elif analyst_score >= 3:
                rating = '中性'
                level = 'hold'
            else:
                rating = '谨慎'
                level = 'cautious'
            
            return {
                'rating': rating,
                'level': level,
                'score': analyst_score,
                'metrics': {
                    'target_mean': target_mean,
                    'target_high': target_high,
                    'target_low': target_low,
                    'current_price': current_price,
                    'num_analysts': num_analysts,
                    'recommendation': recommendation_key
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"分析师意见分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def analyze_earnings(self, data: Dict) -> Dict[str, Any]:
        """
        收益质量分析：评估盈利的稳定性和质量
        """
        try:
            earnings = data.get('earnings', {})
            earnings_history = data.get('earnings_history', [])
            
            earnings_score = 0
            signals = []
            
            if not earnings_history:
                signals.append('⚪ 暂无收益历史数据')
                return {
                    'rating': '未知',
                    'level': 'unknown',
                    'score': 0,
                    'metrics': {},
                    'signals': signals
                }
            
            # 分析实际vs预期
            beat_count = 0
            miss_count = 0
            
            for earning in earnings_history[:8]:  # 分析最近8个季度
                eps_actual = earning.get('epsActual', 0)
                eps_estimate = earning.get('epsEstimate', 0)
                
                if eps_actual and eps_estimate:
                    if eps_actual > eps_estimate:
                        beat_count += 1
                    elif eps_actual < eps_estimate:
                        miss_count += 1
            
            # 超预期比例分析
            if beat_count > 0 or miss_count > 0:
                beat_rate = beat_count / (beat_count + miss_count) * 100
                if beat_rate >= 75:
                    signals.append(f'✅ 经常超预期，超预期率{beat_rate:.0f}%')
                    earnings_score += 3
                elif beat_rate >= 50:
                    signals.append(f'⚪ 超预期表现一般，超预期率{beat_rate:.0f}%')
                    earnings_score += 2
                else:
                    signals.append(f'⚠️ 经常不及预期，超预期率{beat_rate:.0f}%')
                    earnings_score += 1
            
            # 季度收益稳定性
            quarterly_earnings = earnings.get('quarterly', [])
            if quarterly_earnings and len(quarterly_earnings) >= 4:
                recent_earnings = [q.get('Earnings', 0) for q in quarterly_earnings[:4]]
                if all(e > 0 for e in recent_earnings):
                    signals.append('✅ 持续盈利，收益稳定')
                    earnings_score += 2
                    
                    # 检查增长趋势
                    if all(recent_earnings[i] <= recent_earnings[i+1] for i in range(len(recent_earnings)-1)):
                        signals.append('✅ 收益持续增长')
                        earnings_score += 1
            
            # 评级
            if earnings_score >= 5:
                rating = '优秀'
                level = 'excellent'
            elif earnings_score >= 3:
                rating = '良好'
                level = 'good'
            elif earnings_score >= 1:
                rating = '一般'
                level = 'fair'
            else:
                rating = '较差'
                level = 'poor'
            
            return {
                'rating': rating,
                'level': level,
                'score': earnings_score,
                'metrics': {
                    'beat_count': beat_count,
                    'miss_count': miss_count,
                    'total_reports': len(earnings_history)
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"收益质量分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def analyze_esg(self, sustainability: Dict) -> Dict[str, Any]:
        """
        ESG分析：评估环境、社会和治理表现
        """
        try:
            if not sustainability:
                return {
                    'rating': '无数据',
                    'level': 'no_data',
                    'score': 0,
                    'metrics': {},
                    'signals': ['⚪ 暂无ESG数据']
                }
            
            total_esg = sustainability.get('totalEsg', 0)
            environment = sustainability.get('environmentScore', 0)
            social = sustainability.get('socialScore', 0)
            governance = sustainability.get('governanceScore', 0)
            
            signals = []
            
            # ESG总分分析（分数越低越好）
            if total_esg > 0:
                if total_esg < 20:
                    signals.append('✅ ESG评分优秀，可持续性强')
                    rating = '优秀'
                    level = 'excellent'
                elif total_esg < 30:
                    signals.append('⚪ ESG评分良好')
                    rating = '良好'
                    level = 'good'
                elif total_esg < 40:
                    signals.append('⚠️ ESG评分一般')
                    rating = '一般'
                    level = 'fair'
                else:
                    signals.append('❌ ESG评分较差')
                    rating = '较差'
                    level = 'poor'
            else:
                rating = '未评级'
                level = 'unrated'
            
            return {
                'rating': rating,
                'level': level,
                'metrics': {
                    'total_esg': total_esg,
                    'environment': environment,
                    'social': social,
                    'governance': governance
                },
                'signals': signals
            }
            
        except Exception as e:
            logger.error(f"ESG分析失败: {e}")
            return {'rating': '未知', 'level': 'unknown', 'signals': []}
    
    def assess_risk(self, data: Dict) -> Dict[str, Any]:
        """
        风险评估：综合评估投资风险
        """
        try:
            fundamental = data.get('fundamental', {})
            
            beta = fundamental.get('Beta', 1.0)
            debt_equity = fundamental.get('DebtToEquity', 0)
            current_ratio = fundamental.get('CurrentRatio', 0)
            
            risk_score = 0
            risk_factors = []
            
            # Beta风险
            if beta > 1.5:
                risk_factors.append('⚠️ 高Beta，波动性大')
                risk_score += 2
            elif beta > 1.2:
                risk_factors.append('⚠️ Beta偏高')
                risk_score += 1
            elif beta < 0.8:
                risk_factors.append('✅ 低Beta，相对稳定')
            
            # 债务风险
            if debt_equity > 2:
                risk_factors.append('⚠️ 高杠杆风险')
                risk_score += 3
            elif debt_equity > 1:
                risk_factors.append('⚠️ 杠杆偏高')
                risk_score += 2
            elif debt_equity < 0.5:
                risk_factors.append('✅ 低杠杆，财务稳健')
            
            # 流动性风险
            if 0 < current_ratio < 1:
                risk_factors.append('⚠️ 流动性风险')
                risk_score += 2
            elif current_ratio < 1.5:
                risk_factors.append('⚠️ 流动性偏弱')
                risk_score += 1
            
            # 风险等级
            if risk_score >= 6:
                level = '高风险'
                rating = 'high'
            elif risk_score >= 4:
                level = '中高风险'
                rating = 'medium_high'
            elif risk_score >= 2:
                level = '中等风险'
                rating = 'medium'
            else:
                level = '低风险'
                rating = 'low'
            
            return {
                'level': level,
                'rating': rating,
                'score': risk_score,
                'factors': risk_factors,
                'metrics': {
                    'beta': beta,
                    'debt_to_equity': debt_equity,
                    'current_ratio': current_ratio
                }
            }
            
        except Exception as e:
            logger.error(f"风险评估失败: {e}")
            return {'level': '未知', 'rating': 'unknown', 'factors': []}
    
    def calculate_overall_score(self, results: Dict) -> Dict[str, Any]:
        """
        计算综合评分（0-100分）
        """
        try:
            # 权重分配
            weights = {
                'valuation': 0.20,      # 估值 20%
                'financial_health': 0.15, # 财务健康 15%
                'growth': 0.15,         # 成长性 15%
                'profitability': 0.15,  # 盈利能力 15%
                'analyst': 0.10,        # 分析师意见 10%
                'earnings': 0.10,       # 收益质量 10%
                'institutional': 0.05,  # 机构持仓 5%
                'insider': 0.05,        # 内部交易 5%
                'dividend': 0.05        # 股息 5%
            }
            
            total_score = 0
            max_scores = {
                'valuation': 6,
                'financial_health': 9,
                'growth': 9,
                'profitability': 8,
                'analyst': 8,
                'earnings': 6,
                'institutional': 8,
                'insider': 5,
                'dividend': 8
            }
            
            breakdown = {}
            
            for key, weight in weights.items():
                if key in results and 'score' in results[key]:
                    score = results[key]['score']
                    max_score = max_scores[key]
                    normalized = (score / max_score * 100) if max_score > 0 else 0
                    weighted = normalized * weight
                    total_score += weighted
                    breakdown[key] = {
                        'raw_score': score,
                        'normalized': round(normalized, 2),
                        'weighted': round(weighted, 2)
                    }
            
            # 综合评级
            if total_score >= 80:
                grade = 'A'
                rating = '优秀'
            elif total_score >= 70:
                grade = 'B+'
                rating = '良好'
            elif total_score >= 60:
                grade = 'B'
                rating = '中等偏上'
            elif total_score >= 50:
                grade = 'C+'
                rating = '中等'
            elif total_score >= 40:
                grade = 'C'
                rating = '中等偏下'
            else:
                grade = 'D'
                rating = '较差'
            
            return {
                'total_score': round(total_score, 2),
                'grade': grade,
                'rating': rating,
                'breakdown': breakdown
            }
            
        except Exception as e:
            logger.error(f"计算综合评分失败: {e}")
            return {'total_score': 0, 'grade': 'N/A', 'rating': '未知'}
    
    def generate_recommendation(self, results: Dict) -> Dict[str, Any]:
        """
        生成投资建议
        """
        try:
            overall = results.get('overall_score', {})
            score = overall.get('total_score', 0)
            risk = results.get('risk', {})
            valuation = results.get('valuation', {})
            growth = results.get('growth', {})
            
            # 基于综合评分的建议
            if score >= 75:
                action = '强烈推荐买入'
                action_code = 'strong_buy'
                reason = '综合表现优秀，各项指标表现良好'
            elif score >= 65:
                action = '推荐买入'
                action_code = 'buy'
                reason = '综合表现良好，具有投资价值'
            elif score >= 55:
                action = '谨慎买入'
                action_code = 'cautious_buy'
                reason = '综合表现中等偏上，可适量配置'
            elif score >= 45:
                action = '持有观望'
                action_code = 'hold'
                reason = '综合表现一般，建议持有观望'
            else:
                action = '谨慎持有或减仓'
                action_code = 'cautious_hold'
                reason = '综合表现偏弱，建议谨慎'
            
            # 添加风险提示
            risk_level = risk.get('rating', 'medium')
            if risk_level in ['high', 'medium_high']:
                reason += '，但需注意较高风险'
            
            # 投资要点
            key_points = []
            
            # 估值要点
            if valuation.get('level') == 'excellent':
                key_points.append('估值处于合理偏低水平')
            elif valuation.get('level') == 'expensive':
                key_points.append('当前估值偏高，需谨慎')
            
            # 成长要点
            if growth.get('level') == 'high':
                key_points.append('公司保持高速增长')
            elif growth.get('level') == 'negative':
                key_points.append('增长动力不足')
            
            # 机构持仓要点
            inst_level = results.get('institutional', {}).get('level')
            if inst_level == 'excellent':
                key_points.append('机构投资者高度认可')
            
            return {
                'action': action,
                'action_code': action_code,
                'reason': reason,
                'key_points': key_points,
                'confidence': 'high' if score >= 70 or score <= 40 else 'medium'
            }
            
        except Exception as e:
            logger.error(f"生成投资建议失败: {e}")
            return {
                'action': '数据不足，建议进一步研究',
                'action_code': 'research',
                'reason': '无法给出明确建议'
            }


def create_comprehensive_analysis(symbol: str, all_data: Dict) -> Optional[Dict[str, Any]]:
    """
    创建全面的股票分析报告
    """
    try:
        analyzer = StockAnalyzer(symbol)
        analysis = analyzer.analyze_all(all_data)
        
        if not analysis:
            return None
        
        # 添加基础信息
        fundamental = all_data.get('fundamental', {})
        analysis['basic_info'] = {
            'symbol': symbol,
            'name': fundamental.get('CompanyName', ''),
            'sector': fundamental.get('Sector', ''),
            'industry': fundamental.get('Industry', ''),
            'current_price': fundamental.get('Price', 0),
            'market_cap': fundamental.get('MarketCap', 0),
            'currency': fundamental.get('Currency', 'USD')
        }
        
        return analysis
        
    except Exception as e:
        logger.error(f"创建全面分析失败: {symbol}, 错误: {e}")
        return None
