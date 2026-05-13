import numpy as np
from scipy.stats import norm
from typing import Dict, List, Tuple
import pandas as pd


class OptionGreeks:
    @staticmethod
    def d1(spot: float, strike: float, time_to_expiry: float, risk_free_rate: float, 
           volatility: float) -> float:
        if time_to_expiry <= 0:
            return 0
        d1 = (np.log(spot / strike) + (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / \
             (volatility * np.sqrt(time_to_expiry))
        return d1
    
    @staticmethod
    def d2(d1: float, time_to_expiry: float, volatility: float) -> float:
        if time_to_expiry <= 0:
            return 0
        return d1 - volatility * np.sqrt(time_to_expiry)
    
    @staticmethod
    def call_price(spot: float, strike: float, time_to_expiry: float, 
                   risk_free_rate: float, volatility: float) -> float:
        if time_to_expiry <= 0:
            return max(0, spot - strike)
        d1 = OptionGreeks.d1(spot, strike, time_to_expiry, risk_free_rate, volatility)
        d2 = OptionGreeks.d2(d1, time_to_expiry, volatility)
        call = spot * norm.cdf(d1) - strike * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2)
        return call
    
    @staticmethod
    def put_price(spot: float, strike: float, time_to_expiry: float,
                  risk_free_rate: float, volatility: float) -> float:
        if time_to_expiry <= 0:
            return max(0, strike - spot)
        d1 = OptionGreeks.d1(spot, strike, time_to_expiry, risk_free_rate, volatility)
        d2 = OptionGreeks.d2(d1, time_to_expiry, volatility)
        put = strike * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2) - spot * norm.cdf(-d1)
        return put
    
    @staticmethod
    def delta(spot: float, strike: float, time_to_expiry: float, 
              risk_free_rate: float, volatility: float, is_call: bool = True) -> float:
        if time_to_expiry <= 0:
            if is_call:
                return 1.0 if spot > strike else 0.0
            else:
                return -1.0 if spot < strike else 0.0
        d1 = OptionGreeks.d1(spot, strike, time_to_expiry, risk_free_rate, volatility)
        if is_call:
            return norm.cdf(d1)
        else:
            return norm.cdf(d1) - 1
    
    @staticmethod
    def gamma(spot: float, strike: float, time_to_expiry: float,
              risk_free_rate: float, volatility: float) -> float:
        if time_to_expiry <= 0:
            return 0
        d1 = OptionGreeks.d1(spot, strike, time_to_expiry, risk_free_rate, volatility)
        gamma = norm.pdf(d1) / (spot * volatility * np.sqrt(time_to_expiry))
        return gamma
    
    @staticmethod
    def theta(spot: float, strike: float, time_to_expiry: float,
              risk_free_rate: float, volatility: float, is_call: bool = True) -> float:
        if time_to_expiry <= 0:
            return 0
        d1 = OptionGreeks.d1(spot, strike, time_to_expiry, risk_free_rate, volatility)
        d2 = OptionGreeks.d2(d1, time_to_expiry, volatility)
        
        first_term = -spot * norm.pdf(d1) * volatility / (2 * np.sqrt(time_to_expiry))
        
        if is_call:
            second_term = -risk_free_rate * strike * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2)
            theta = (first_term + second_term) / 365
        else:
            second_term = risk_free_rate * strike * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2)
            theta = (first_term + second_term) / 365
        
        return theta
    
    @staticmethod
    def vega(spot: float, strike: float, time_to_expiry: float,
             risk_free_rate: float, volatility: float) -> float:
        if time_to_expiry <= 0:
            return 0
        d1 = OptionGreeks.d1(spot, strike, time_to_expiry, risk_free_rate, volatility)
        vega = spot * norm.pdf(d1) * np.sqrt(time_to_expiry) / 100
        return vega


class RiskAnalyzer:
    def __init__(self, risk_free_rate: float = 0.03):
        self.risk_free_rate = risk_free_rate
        self.greeks = OptionGreeks()
    
    def analyze_strategy(self, strategy, spot_price: float, time_to_expiry: float,
                        volatility: float = 0.25) -> Dict:
        total_delta = 0
        total_gamma = 0
        total_theta = 0
        total_vega = 0
        
        for pos in strategy.positions:
            is_call = pos.option_type.value == "call"
            position_multiplier = pos.position.value * pos.quantity
            
            delta = self.greeks.delta(spot_price, pos.strike, time_to_expiry,
                                     self.risk_free_rate, volatility, is_call)
            gamma = self.greeks.gamma(spot_price, pos.strike, time_to_expiry,
                                     self.risk_free_rate, volatility)
            theta = self.greeks.theta(spot_price, pos.strike, time_to_expiry,
                                     self.risk_free_rate, volatility, is_call)
            vega = self.greeks.vega(spot_price, pos.strike, time_to_expiry,
                                   self.risk_free_rate, volatility)
            
            total_delta += delta * position_multiplier
            total_gamma += gamma * position_multiplier
            total_theta += theta * position_multiplier
            total_vega += vega * position_multiplier
        
        price_range = np.linspace(spot_price * 0.8, spot_price * 1.2, 100)
        max_profit = strategy.get_max_profit(price_range)
        max_loss = strategy.get_max_loss(price_range)
        breakeven_points = strategy.get_breakeven_points(price_range)
        net_premium = strategy.get_net_premium()
        
        risk_reward_ratio = abs(max_profit / max_loss) if max_loss != 0 else float('inf')
        
        return {
            'strategy_name': strategy.name,
            'delta': round(total_delta, 4),
            'gamma': round(total_gamma, 6),
            'theta': round(total_theta, 4),
            'vega': round(total_vega, 4),
            'max_profit': round(max_profit, 2),
            'max_loss': round(max_loss, 2),
            'breakeven_points': [round(bp, 2) for bp in breakeven_points],
            'net_premium': round(net_premium, 2),
            'risk_reward_ratio': round(risk_reward_ratio, 4)
        }
    
    def calculate_var(self, pnl_distribution: np.ndarray, confidence_level: float = 0.95) -> float:
        return np.percentile(pnl_distribution, (1 - confidence_level) * 100)
    
    def calculate_expected_shortfall(self, pnl_distribution: np.ndarray, 
                                     confidence_level: float = 0.95) -> float:
        var = self.calculate_var(pnl_distribution, confidence_level)
        return np.mean(pnl_distribution[pnl_distribution <= var])
    
    def monte_carlo_simulation(self, strategy, spot_price: float, time_to_expiry: float,
                               volatility: float = 0.25, num_simulations: int = 10000,
                               num_steps: int = 30) -> Dict:
        dt = time_to_expiry / num_steps
        
        price_paths = np.zeros((num_simulations, num_steps + 1))
        price_paths[:, 0] = spot_price
        
        for t in range(1, num_steps + 1):
            z = np.random.standard_normal(num_simulations)
            price_paths[:, t] = price_paths[:, t - 1] * np.exp(
                (self.risk_free_rate - 0.5 * volatility ** 2) * dt +
                volatility * np.sqrt(dt) * z
            )
        
        final_prices = price_paths[:, -1]
        pnl_distribution = np.array([strategy.get_pnl_at_expiry(price) for price in final_prices])
        
        var_95 = self.calculate_var(pnl_distribution, 0.95)
        var_99 = self.calculate_var(pnl_distribution, 0.99)
        es_95 = self.calculate_expected_shortfall(pnl_distribution, 0.95)
        
        return {
            'mean_pnl': round(np.mean(pnl_distribution), 2),
            'std_pnl': round(np.std(pnl_distribution), 2),
            'var_95': round(var_95, 2),
            'var_99': round(var_99, 2),
            'expected_shortfall_95': round(es_95, 2),
            'probability_of_profit': round(np.mean(pnl_distribution > 0) * 100, 2),
            'pnl_distribution': pnl_distribution.tolist()
        }
    
    def generate_risk_report(self, strategies: List, spot_price: float, 
                            time_to_expiry: float, volatility: float = 0.25) -> pd.DataFrame:
        reports = []
        for strategy in strategies:
            analysis = self.analyze_strategy(strategy, spot_price, time_to_expiry, volatility)
            reports.append(analysis)
        
        df = pd.DataFrame(reports)
        return df
