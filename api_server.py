from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import numpy as np
from datetime import datetime
from vix_calculator import VIXCalculator
from option_strategies import (
    StrategyBuilder, OptionStrategy, OptionType, PositionType,
    create_crude_oil_strategies
)
from risk_analysis import RiskAnalyzer
from tqsdk_option import TqsdkOptionTrader

app = Flask(__name__)
CORS(app)

trader = TqsdkOptionTrader()
vix_calculator = VIXCalculator()
risk_analyzer = RiskAnalyzer()


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})


@app.route('/api/crude-oil/options', methods=['GET'])
def get_crude_oil_options():
    try:
        data = trader.get_crude_oil_options()
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/vix/calculate', methods=['POST'])
def calculate_vix():
    try:
        data = request.json
        underlying_price = data.get('underlying_price', 500.0)
        options_data = data.get('options', [])
        
        vix = vix_calculator.calculate_simple_vix(options_data, underlying_price)
        
        return jsonify({
            'success': True,
            'vix': round(vix, 2),
            'underlying_price': underlying_price
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/vix/crude-oil', methods=['GET'])
def calculate_crude_oil_vix():
    try:
        crude_oil_data = trader.get_crude_oil_options()
        underlying_price = crude_oil_data['underlying_price']
        options_chain = crude_oil_data['options_chain']
        
        vix = vix_calculator.calculate_simple_vix(options_chain, underlying_price)
        
        return jsonify({
            'success': True,
            'vix': round(vix, 2),
            'underlying_price': underlying_price,
            'symbol': crude_oil_data['underlying_symbol']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/strategies/list', methods=['GET'])
def list_strategies():
    strategies = [
        {
            'id': 'short_straddle',
            'name': '双卖（Short Straddle）',
            'description': '同时卖出相同执行价的看涨和看跌期权，预期标的物价格稳定',
            'risk_level': '高',
            'params': ['underlying_price', 'call_premium', 'put_premium']
        },
        {
            'id': 'short_strangle',
            'name': '宽跨式双卖（Short Strangle）',
            'description': '卖出不同执行价的看涨和看跌期权，预期价格在一定范围内波动',
            'risk_level': '中高',
            'params': ['underlying_price', 'call_strike', 'put_strike', 'call_premium', 'put_premium']
        },
        {
            'id': 'iron_condor',
            'name': '铁鹰（Iron Condor）',
            'description': '组合策略，限制最大亏损，适合震荡市场',
            'risk_level': '中',
            'params': ['underlying_price', 'strikes', 'premiums']
        },
        {
            'id': 'calendar_spread',
            'name': '日历价差（Calendar Spread）',
            'description': '利用不同到期日期权的时间价值差异获利',
            'risk_level': '中低',
            'params': ['underlying_price', 'strike', 'near_premium', 'far_premium']
        }
    ]
    return jsonify({
        'success': True,
        'strategies': strategies
    })


@app.route('/api/strategies/build', methods=['POST'])
def build_strategy():
    try:
        data = request.json
        strategy_id = data.get('strategy_id')
        params = data.get('params', {})
        
        underlying_price = params.get('underlying_price', 500.0)
        
        if strategy_id == 'short_straddle':
            strategy = StrategyBuilder.build_short_straddle(
                underlying_price=underlying_price,
                call_premium=params.get('call_premium', 15.0),
                put_premium=params.get('put_premium', 12.0)
            )
        elif strategy_id == 'short_strangle':
            strategy = StrategyBuilder.build_short_strangle(
                underlying_price=underlying_price,
                call_strike=params.get('call_strike', 520.0),
                put_strike=params.get('put_strike', 480.0),
                call_premium=params.get('call_premium', 8.0),
                put_premium=params.get('put_premium', 6.0)
            )
        elif strategy_id == 'iron_condor':
            strategy = StrategyBuilder.build_iron_condor(
                underlying_price=underlying_price,
                put_strike_low=params.get('put_strike_low', 460.0),
                put_strike_high=params.get('put_strike_high', 480.0),
                call_strike_low=params.get('call_strike_low', 520.0),
                call_strike_high=params.get('call_strike_high', 540.0),
                put_premium_low=params.get('put_premium_low', 3.0),
                put_premium_high=params.get('put_premium_high', 6.0),
                call_premium_low=params.get('call_premium_low', 8.0),
                call_premium_high=params.get('call_premium_high', 4.0)
            )
        elif strategy_id == 'calendar_spread':
            strategy = StrategyBuilder.build_calendar_spread(
                underlying_price=underlying_price,
                strike=params.get('strike', 500.0),
                near_premium=params.get('near_premium', 10.0),
                far_premium=params.get('far_premium', 18.0)
            )
        else:
            return jsonify({
                'success': False,
                'error': '未知的策略类型'
            }), 400
        
        return jsonify({
            'success': True,
            'strategy': {
                'name': strategy.name,
                'positions': [
                    {
                        'type': pos.option_type.value,
                        'strike': pos.strike,
                        'premium': pos.premium,
                        'position': 'long' if pos.position == PositionType.LONG else 'short'
                    }
                    for pos in strategy.positions
                ]
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/strategies/analyze', methods=['POST'])
def analyze_strategy():
    try:
        data = request.json
        strategy_id = data.get('strategy_id')
        params = data.get('params', {})
        
        underlying_price = params.get('underlying_price', 500.0)
        time_to_expiry = params.get('time_to_expiry', 30) / 365
        volatility = params.get('volatility', 0.25)
        
        if strategy_id == 'short_straddle':
            strategy = StrategyBuilder.build_short_straddle(
                underlying_price=underlying_price,
                call_premium=params.get('call_premium', 15.0),
                put_premium=params.get('put_premium', 12.0)
            )
        elif strategy_id == 'short_strangle':
            strategy = StrategyBuilder.build_short_strangle(
                underlying_price=underlying_price,
                call_strike=params.get('call_strike', 520.0),
                put_strike=params.get('put_strike', 480.0),
                call_premium=params.get('call_premium', 8.0),
                put_premium=params.get('put_premium', 6.0)
            )
        elif strategy_id == 'iron_condor':
            strategy = StrategyBuilder.build_iron_condor(
                underlying_price=underlying_price,
                put_strike_low=params.get('put_strike_low', 460.0),
                put_strike_high=params.get('put_strike_high', 480.0),
                call_strike_low=params.get('call_strike_low', 520.0),
                call_strike_high=params.get('call_strike_high', 540.0),
                put_premium_low=params.get('put_premium_low', 3.0),
                put_premium_high=params.get('put_premium_high', 6.0),
                call_premium_low=params.get('call_premium_low', 8.0),
                call_premium_high=params.get('call_premium_high', 4.0)
            )
        elif strategy_id == 'calendar_spread':
            strategy = StrategyBuilder.build_calendar_spread(
                underlying_price=underlying_price,
                strike=params.get('strike', 500.0),
                near_premium=params.get('near_premium', 10.0),
                far_premium=params.get('far_premium', 18.0)
            )
        else:
            return jsonify({
                'success': False,
                'error': '未知的策略类型'
            }), 400
        
        analysis = risk_analyzer.analyze_strategy(
            strategy, underlying_price, time_to_expiry, volatility
        )
        
        mc_results = risk_analyzer.monte_carlo_simulation(
            strategy, underlying_price, time_to_expiry, volatility
        )
        
        price_range = np.linspace(underlying_price * 0.8, underlying_price * 1.2, 100)
        pnl_profile = strategy.get_pnl_profile(price_range)
        
        return jsonify({
            'success': True,
            'strategy_name': strategy.name,
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
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/strategies/compare', methods=['POST'])
def compare_strategies():
    try:
        data = request.json
        underlying_price = data.get('underlying_price', 500.0)
        time_to_expiry = data.get('time_to_expiry', 30) / 365
        volatility = data.get('volatility', 0.25)
        
        strategies = create_crude_oil_strategies(underlying_price)
        
        results = trader.analyze_strategies(
            strategies, underlying_price, time_to_expiry, volatility
        )
        
        return jsonify({
            'success': True,
            'data': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/risk/greeks', methods=['POST'])
def calculate_greeks():
    try:
        data = request.json
        spot = data.get('spot', 500.0)
        strike = data.get('strike', 500.0)
        time_to_expiry = data.get('time_to_expiry', 30) / 365
        risk_free_rate = data.get('risk_free_rate', 0.03)
        volatility = data.get('volatility', 0.25)
        option_type = data.get('option_type', 'call')
        
        from risk_analysis import OptionGreeks
        
        is_call = option_type == 'call'
        
        greeks = {
            'delta': OptionGreeks.delta(spot, strike, time_to_expiry, risk_free_rate, volatility, is_call),
            'gamma': OptionGreeks.gamma(spot, strike, time_to_expiry, risk_free_rate, volatility),
            'theta': OptionGreeks.theta(spot, strike, time_to_expiry, risk_free_rate, volatility, is_call),
            'vega': OptionGreeks.vega(spot, strike, time_to_expiry, risk_free_rate, volatility)
        }
        
        if is_call:
            price = OptionGreeks.call_price(spot, strike, time_to_expiry, risk_free_rate, volatility)
        else:
            price = OptionGreeks.put_price(spot, strike, time_to_expiry, risk_free_rate, volatility)
        
        greeks['price'] = price
        
        return jsonify({
            'success': True,
            'greeks': {k: round(v, 6) for k, v in greeks.items()}
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("启动期权分析API服务器...")
    print("API文档: http://localhost:5000/api/health")
    app.run(host='0.0.0.0', port=5000, debug=True)
