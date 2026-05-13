from tqsdk import TqApi, TqAuth
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
from vix_calculator import VIXCalculator
from option_strategies import (
    StrategyBuilder, OptionStrategy, OptionType, PositionType
)
from risk_analysis import RiskAnalyzer

load_dotenv()


class TqsdkOptionTrader:
    def __init__(self, account: str = None, password: str = None):
        self.api = None
        self.account = account or os.getenv('TQSDK_ACCOUNT', '')
        self.password = password or os.getenv('TQSDK_PASSWORD', '')
        self.vix_calculator = VIXCalculator()
        self.risk_analyzer = RiskAnalyzer()
    
    def connect(self):
        if not self.account or not self.password:
            raise ValueError("请先在.env文件中配置TQSDK_ACCOUNT和TQSDK_PASSWORD")
        self.api = TqApi(auth=TqAuth(self.account, self.password))
        print("已连接到TqSdk")
    
    def disconnect(self):
        if self.api:
            self.api.close()
            print("已断开连接")
    
    def get_option_chain(self, underlying_symbol: str, expiry_date: str) -> pd.DataFrame:
        if not self.api:
            raise Exception("未连接到TqSdk")
        
        options_data = []
        
        quote = self.api.get_quote(underlying_symbol)
        underlying_price = quote.last_price
        
        option_symbols = self.api.query_options(underlying_symbol, expiry_date)
        
        for symbol in option_symbols:
            option_quote = self.api.get_quote(symbol)
            options_data.append({
                'symbol': symbol,
                'strike': option_quote.strike_price,
                'type': 'call' if 'C' in symbol else 'put',
                'price': option_quote.last_price,
                'implied_vol': option_quote.implied_volatility,
                'delta': option_quote.delta,
                'gamma': option_quote.gamma,
                'theta': option_quote.theta,
                'vega': option_quote.vega,
                'volume': option_quote.volume,
                'open_interest': option_quote.open_interest
            })
        
        df = pd.DataFrame(options_data)
        return df
    
    def calculate_vix_for_underlying(self, underlying_symbol: str) -> float:
        if not self.api:
            raise Exception("未连接到TqSdk")
        
        quote = self.api.get_quote(underlying_symbol)
        underlying_price = quote.last_price
        
        today = datetime.now()
        near_expiry = today + timedelta(days=7)
        next_expiry = today + timedelta(days=37)
        
        near_options = self.get_option_chain(underlying_symbol, near_expiry.strftime("%Y%m%d"))
        next_options = self.get_option_chain(underlying_symbol, next_expiry.strftime("%Y%m%d"))
        
        if near_options.empty or next_options.empty:
            return self.vix_calculator.calculate_simple_vix([], underlying_price)
        
        vix = self.vix_calculator.calculate_vix(
            near_options, next_options,
            near_expiry, next_expiry, today
        )
        
        return vix
    
    def get_crude_oil_options(self) -> Dict:
        crude_oil_symbol = "SHFE.sc2406"
        
        if not self.api:
            return self._get_demo_crude_oil_data()
        
        try:
            quote = self.api.get_quote(crude_oil_symbol)
            underlying_price = quote.last_price
            
            expiry_date = "20240520"
            options_chain = self.get_option_chain(crude_oil_symbol, expiry_date)
            
            return {
                'underlying_symbol': crude_oil_symbol,
                'underlying_price': underlying_price,
                'options_chain': options_chain.to_dict('records'),
                'expiry_date': expiry_date
            }
        except Exception as e:
            print(f"获取原油期权数据失败: {e}")
            return self._get_demo_crude_oil_data()
    
    def _get_demo_crude_oil_data(self) -> Dict:
        underlying_price = 500.0
        expiry_date = "20240520"
        
        strikes = np.arange(450, 551, 10)
        options_chain = []
        
        for strike in strikes:
            call_price = max(0, underlying_price - strike + 20) * 0.8 + 5
            put_price = max(0, strike - underlying_price + 20) * 0.8 + 5
            
            options_chain.append({
                'symbol': f'sc2406C{strike}',
                'strike': strike,
                'type': 'call',
                'price': round(call_price, 2),
                'implied_vol': 0.25,
                'delta': 0.5,
                'gamma': 0.01,
                'theta': -0.05,
                'vega': 0.8,
                'volume': 1000,
                'open_interest': 5000
            })
            
            options_chain.append({
                'symbol': f'sc2406P{strike}',
                'strike': strike,
                'type': 'put',
                'price': round(put_price, 2),
                'implied_vol': 0.25,
                'delta': -0.5,
                'gamma': 0.01,
                'theta': -0.05,
                'vega': 0.8,
                'volume': 1000,
                'open_interest': 5000
            })
        
        return {
            'underlying_symbol': 'SHFE.sc2406',
            'underlying_price': underlying_price,
            'options_chain': options_chain,
            'expiry_date': expiry_date
        }
    
    def execute_strategy(self, strategy: OptionStrategy) -> Dict:
        if not self.api:
            return {
                'status': 'demo',
                'message': '演示模式 - 未连接实盘',
                'strategy': strategy.name,
                'positions': [
                    {
                        'type': pos.option_type.value,
                        'strike': pos.strike,
                        'position': pos.position.value,
                        'premium': pos.premium
                    }
                    for pos in strategy.positions
                ]
            }
        
        try:
            for pos in strategy.positions:
                symbol = self._generate_option_symbol(pos)
                
                if pos.position == PositionType.LONG:
                    order = self.api.insert_order(symbol, "BUY", "OPEN", 1, pos.premium)
                else:
                    order = self.api.insert_order(symbol, "SELL", "OPEN", 1, pos.premium)
                
                print(f"下单成功: {symbol}, 方向: {pos.position.value}")
            
            return {
                'status': 'success',
                'message': '策略执行成功',
                'strategy': strategy.name
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'strategy': strategy.name
            }
    
    def _generate_option_symbol(self, position) -> str:
        option_type_char = 'C' if position.option_type == OptionType.CALL else 'P'
        return f"sc2406{option_type_char}{int(position.strike)}"
    
    def analyze_strategies(self, strategies: List[OptionStrategy], spot_price: float,
                          time_to_expiry: float, volatility: float = 0.25) -> Dict:
        results = {
            'strategies': [],
            'comparison': {}
        }
        
        for strategy in strategies:
            analysis = self.risk_analyzer.analyze_strategy(
                strategy, spot_price, time_to_expiry, volatility
            )
            
            mc_results = self.risk_analyzer.monte_carlo_simulation(
                strategy, spot_price, time_to_expiry, volatility
            )
            
            price_range = np.linspace(spot_price * 0.8, spot_price * 1.2, 100)
            pnl_profile = strategy.get_pnl_profile(price_range)
            
            results['strategies'].append({
                'name': strategy.name,
                'analysis': analysis,
                'monte_carlo': {
                    'mean_pnl': mc_results['mean_pnl'],
                    'std_pnl': mc_results['std_pnl'],
                    'var_95': mc_results['var_95'],
                    'var_99': mc_results['var_99'],
                    'expected_shortfall_95': mc_results['expected_shortfall_95'],
                    'probability_of_profit': mc_results['probability_of_profit']
                },
                'pnl_profile': {
                    'price_range': price_range.tolist(),
                    'pnl': pnl_profile.tolist()
                }
            })
        
        results['comparison'] = self._compare_strategies(results['strategies'])
        
        return results
    
    def _compare_strategies(self, strategies_data: List) -> Dict:
        comparison = {
            'best_max_profit': None,
            'lowest_max_loss': None,
            'best_risk_reward': None,
            'highest_profit_probability': None
        }
        
        best_profit = float('-inf')
        lowest_loss = float('inf')
        best_ratio = 0
        highest_prob = 0
        
        for strategy in strategies_data:
            analysis = strategy['analysis']
            mc = strategy['monte_carlo']
            
            if analysis['max_profit'] > best_profit:
                best_profit = analysis['max_profit']
                comparison['best_max_profit'] = strategy['name']
            
            if analysis['max_loss'] > lowest_loss:
                lowest_loss = analysis['max_loss']
                comparison['lowest_max_loss'] = strategy['name']
            
            if analysis['risk_reward_ratio'] > best_ratio:
                best_ratio = analysis['risk_reward_ratio']
                comparison['best_risk_reward'] = strategy['name']
            
            if mc['probability_of_profit'] > highest_prob:
                highest_prob = mc['probability_of_profit']
                comparison['highest_profit_probability'] = strategy['name']
        
        return comparison


def run_demo():
    trader = TqsdkOptionTrader()
    
    crude_oil_data = trader.get_crude_oil_options()
    print(f"原油标的物价格: {crude_oil_data['underlying_price']}")
    print(f"期权到期日: {crude_oil_data['expiry_date']}")
    
    strategies = [
        StrategyBuilder.build_short_straddle(500.0, 15.0, 12.0),
        StrategyBuilder.build_short_strangle(500.0, 520.0, 480.0, 8.0, 6.0),
        StrategyBuilder.build_iron_condor(500.0, 460.0, 480.0, 520.0, 540.0, 3.0, 6.0, 8.0, 4.0),
        StrategyBuilder.build_calendar_spread(500.0, 500.0, 10.0, 18.0)
    ]
    
    analysis_results = trader.analyze_strategies(strategies, 500.0, 30/365, 0.25)
    
    for strategy in analysis_results['strategies']:
        print(f"\n策略: {strategy['name']}")
        print(f"最大盈利: {strategy['analysis']['max_profit']}")
        print(f"最大亏损: {strategy['analysis']['max_loss']}")
        print(f"盈亏比: {strategy['analysis']['risk_reward_ratio']}")
        print(f"盈利概率: {strategy['monte_carlo']['probability_of_profit']}%")
        print(f"VaR(95%): {strategy['monte_carlo']['var_95']}")
    
    return analysis_results


if __name__ == "__main__":
    run_demo()
