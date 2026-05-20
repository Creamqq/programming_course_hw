from flask import Flask, jsonify, request
from flask_cors import CORS
import numpy as np
from greeks import OptionGreeks
from volatility_surface import VolatilitySurface
from data_fetcher import TqsdkDataFetcher

app = Flask(__name__)
CORS(app)

data_fetcher = TqsdkDataFetcher()


@app.route('/api/option-info/<symbol>', methods=['GET'])
def get_option_info(symbol):
    """
    通过合约代码获取期权信息
    
    Args:
        symbol: 期权合约代码（如 SHFE.cu2610C126000）
    
    Returns:
        期权信息：标的价格、行权价、到期时间、市场价格等
    """
    try:
        if not data_fetcher.api:
            data_fetcher.connect()
        
        quote = data_fetcher.get_option_quote(symbol)
        
        if not quote:
            return jsonify({
                'success': False,
                'error': '无法获取期权报价'
            }), 400
        
        underlying_symbol = quote.get('underlying', '')
        if underlying_symbol:
            underlying_price = data_fetcher.get_underlying_price(underlying_symbol)
        else:
            underlying_price = None
        
        return jsonify({
            'success': True,
            'data': {
                'symbol': symbol,
                'last_price': quote['last_price'],
                'bid_price': quote['bid_price'],
                'ask_price': quote['ask_price'],
                'strike': quote['strike'],
                'underlying_price': underlying_price,
                'volume': quote['volume'],
                'open_interest': quote['open_interest'],
                'days_to_expiry': quote.get('days_to_expiry'),
                'expire_datetime': quote.get('expire_datetime')
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/calculate-greeks-by-symbol', methods=['POST'])
def calculate_greeks_by_symbol():
    """
    通过合约代码计算希腊字母
    
    Args:
        symbol: 期权合约代码
        risk_free_rate: 无风险利率（默认0.03）
    """
    try:
        data = request.json
        symbol = data['symbol']
        r = float(data.get('risk_free_rate', 0.03))
        
        if not data_fetcher.api:
            data_fetcher.connect()
        
        quote = data_fetcher.get_option_quote(symbol)
        
        if not quote:
            return jsonify({
                'success': False,
                'error': '无法获取期权报价'
            }), 400
        
        K = quote['strike']
        market_price = quote['last_price']
        days_to_expiry = quote.get('days_to_expiry')
        
        underlying_symbol = quote.get('underlying', '')
        if underlying_symbol:
            S = data_fetcher.get_underlying_price(underlying_symbol)
        else:
            return jsonify({
                'success': False,
                'error': '无法获取标的价格'
            }), 400
        
        if 'C' in symbol.upper():
            option_type = 'call'
        else:
            option_type = 'put'
        
        if days_to_expiry and days_to_expiry > 0:
            T = float(days_to_expiry) / 365.0
        else:
            T = 30 / 365.0
        
        option = OptionGreeks(S, K, T, r, 0.2, option_type)
        
        iv = option.implied_volatility(market_price)
        
        if iv is not None:
            option.sigma = iv
        
        greeks = option.calculate_all_greeks()
        greeks['implied_volatility'] = float(iv) if iv is not None else None
        greeks['symbol'] = symbol
        greeks['underlying_price'] = float(S)
        greeks['strike'] = float(K)
        greeks['market_price'] = float(market_price)
        greeks['option_type'] = option_type
        greeks['days_to_expiry'] = days_to_expiry
        
        return jsonify({
            'success': True,
            'data': greeks
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/option-chain-greeks', methods=['POST'])
def calculate_option_chain_greeks():
    try:
        data = request.json
        underlying = data.get('underlying', 'CU')
        exchange = data.get('exchange', 'SHFE')
        r = float(data.get('risk_free_rate', 0.03))
        
        if not data_fetcher.api:
            data_fetcher.connect()
        
        option_chain = data_fetcher.get_real_time_option_chain(underlying, exchange)
        
        if not option_chain:
            return jsonify({
                'success': False,
                'error': '无法获取期权链数据'
            }), 400
        
        underlying_price = option_chain['underlying_price']
        options = option_chain['options']
        
        results = []
        for opt in options:
            K = float(opt['strike'])
            T = float(opt['days_to_expiry']) / 365.0
            option_type = opt['type']
            market_price = float(opt['price'])
            
            option = OptionGreeks(underlying_price, K, T, r, 0.2, option_type)
            iv = option.implied_volatility(market_price)
            
            if iv is not None:
                option.sigma = iv
                greeks = option.calculate_all_greeks()
                greeks['implied_volatility'] = float(iv)
                greeks['symbol'] = opt['symbol']
                greeks['strike'] = K
                greeks['type'] = option_type
                greeks['market_price'] = market_price
                greeks['days_to_expiry'] = opt['days_to_expiry']
                results.append(greeks)
        
        return jsonify({
            'success': True,
            'data': {
                'underlying_price': underlying_price,
                'underlying': underlying,
                'options': results
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/option-chain-greeks-by-symbol', methods=['POST'])
def calculate_option_chain_greeks_by_symbol():
    try:
        data = request.json
        symbol = data['symbol']
        r = float(data.get('risk_free_rate', 0.03))
        
        if not data_fetcher.api:
            data_fetcher.connect()
        
        option_chain = data_fetcher.get_option_chain_by_symbol(symbol)
        
        if not option_chain:
            return jsonify({
                'success': False,
                'error': '无法获取期权链数据'
            }), 400
        
        underlying_price = option_chain['underlying_price']
        options = option_chain['options']
        
        results = []
        for opt in options:
            K = float(opt['strike'])
            days = opt.get('days_to_expiry')
            if days and days > 0:
                T = float(days) / 365.0
            else:
                T = 30 / 365.0
            option_type = opt['type']
            market_price = float(opt['price'])
            
            option = OptionGreeks(underlying_price, K, T, r, 0.2, option_type)
            iv = option.implied_volatility(market_price)
            
            if iv is not None:
                option.sigma = iv
                greeks = option.calculate_all_greeks()
                greeks['implied_volatility'] = float(iv)
                greeks['symbol'] = opt['symbol']
                greeks['strike'] = K
                greeks['type'] = option_type
                greeks['market_price'] = market_price
                greeks['days_to_expiry'] = opt.get('days_to_expiry')
                results.append(greeks)
        
        return jsonify({
            'success': True,
            'data': {
                'underlying_price': underlying_price,
                'symbol': symbol,
                'options': results
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/volatility-surface', methods=['POST'])
def calculate_volatility_surface():
    try:
        data = request.json
        underlying = data.get('underlying', 'CU')
        exchange = data.get('exchange', 'SHFE')
        
        if not data_fetcher.api:
            data_fetcher.connect()
        
        option_chain = data_fetcher.get_real_time_option_chain(underlying, exchange)
        
        if not option_chain:
            return jsonify({
                'success': False,
                'error': '无法获取期权链数据'
            }), 400
        
        underlying_price = option_chain['underlying_price']
        options = option_chain['options']
        
        strikes = []
        maturities = []
        implied_vols = []
        
        for opt in options:
            K = float(opt['strike'])
            T = float(opt['days_to_expiry'])
            market_price = float(opt['price'])
            option_type = opt['type']
            
            from greeks import OptionGreeks
            option = OptionGreeks(underlying_price, K, T/365.0, 0.03, 0.2, option_type)
            iv = option.implied_volatility(market_price)
            
            if iv is not None:
                strikes.append(K)
                maturities.append(T)
                implied_vols.append(float(iv))
        
        if len(strikes) < 4:
            return jsonify({
                'success': False,
                'error': '数据点不足，至少需要4个期权数据'
            }), 400
        
        vs = VolatilitySurface()
        vs.fit_surface(strikes, maturities, implied_vols, method='polynomial')
        
        surface_data = vs.to_json(num_points=30)
        
        return jsonify({
            'success': True,
            'data': surface_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/volatility-surface-by-symbol', methods=['POST'])
def calculate_volatility_surface_by_symbol():
    try:
        data = request.json
        symbol = data['symbol']
        
        if not data_fetcher.api:
            data_fetcher.connect()
        
        option_chain = data_fetcher.get_option_chain_by_symbol(symbol)
        
        if not option_chain:
            return jsonify({
                'success': False,
                'error': '无法获取期权链数据'
            }), 400
        
        underlying_price = option_chain['underlying_price']
        options = option_chain['options']
        
        strikes = []
        maturities = []
        implied_vols = []
        
        for opt in options:
            K = float(opt['strike'])
            days = opt.get('days_to_expiry')
            if days and days > 0:
                T = float(days)
            else:
                T = 30
            market_price = float(opt['price'])
            option_type = opt['type']
            
            from greeks import OptionGreeks
            option = OptionGreeks(underlying_price, K, T/365.0, 0.03, 0.2, option_type)
            iv = option.implied_volatility(market_price)
            
            if iv is not None:
                strikes.append(K)
                maturities.append(T)
                implied_vols.append(float(iv))
        
        if len(strikes) < 4:
            return jsonify({
                'success': False,
                'error': '数据点不足，至少需要4个期权数据'
            }), 400
        
        vs = VolatilitySurface()
        vs.fit_surface(strikes, maturities, implied_vols, method='polynomial')
        
        surface_data = vs.to_json(num_points=30)
        
        return jsonify({
            'success': True,
            'data': surface_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/greeks-sensitivity', methods=['POST'])
def calculate_greeks_sensitivity():
    try:
        data = request.json
        symbol = data['symbol']
        parameter = data.get('parameter', 'underlying_price')
        range_start = data.get('range_start')
        range_end = data.get('range_end')
        num_points = int(data.get('num_points', 50))
        
        if not data_fetcher.api:
            data_fetcher.connect()
        
        quote = data_fetcher.get_option_quote(symbol)
        
        if not quote:
            return jsonify({
                'success': False,
                'error': '无法获取期权报价'
            }), 400
        
        K = quote['strike']
        market_price = quote['last_price']
        days_to_expiry = quote.get('days_to_expiry')
        
        underlying_symbol = quote.get('underlying', '')
        if underlying_symbol:
            S = data_fetcher.get_underlying_price(underlying_symbol)
        else:
            return jsonify({
                'success': False,
                'error': '无法获取标的价格'
            }), 400
        
        if 'C' in symbol.upper():
            option_type = 'call'
        else:
            option_type = 'put'
        
        if days_to_expiry and days_to_expiry > 0:
            T = float(days_to_expiry) / 365.0
        else:
            T = 30 / 365.0
        
        r = 0.03
        
        option = OptionGreeks(S, K, T, r, 0.2, option_type)
        iv = option.implied_volatility(market_price)
        sigma = iv if iv is not None else 0.2
        
        if parameter == 'underlying_price':
            if not range_start:
                range_start = S * 0.8
            if not range_end:
                range_end = S * 1.2
        elif parameter == 'volatility':
            if not range_start:
                range_start = max(0.05, sigma * 0.5)
            if not range_end:
                range_end = sigma * 1.5
        elif parameter == 'strike':
            if not range_start:
                range_start = K * 0.8
            if not range_end:
                range_end = K * 1.2
        else:
            range_start = S * 0.8
            range_end = S * 1.2
        
        values = np.linspace(range_start, range_end, num_points)
        greeks_values = {'delta': [], 'gamma': [], 'theta': [], 'vega': [], 'rho': []}
        
        for val in values:
            if parameter == 'underlying_price':
                option = OptionGreeks(val, K, T, r, sigma, option_type)
            elif parameter == 'volatility':
                option = OptionGreeks(S, K, T, r, val, option_type)
            elif parameter == 'strike':
                option = OptionGreeks(S, val, T, r, sigma, option_type)
            else:
                option = OptionGreeks(S, K, T, r, sigma, option_type)
            
            greeks = option.calculate_all_greeks()
            for key in greeks_values.keys():
                greeks_values[key].append(greeks[key])
        
        return jsonify({
            'success': True,
            'data': {
                'parameter_values': values.tolist(),
                'parameter_name': parameter,
                'greeks': greeks_values,
                'symbol': symbol,
                'current_value': S if parameter == 'underlying_price' else (sigma if parameter == 'volatility' else K)
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/historical-volatility', methods=['POST'])
def get_historical_volatility():
    """
    获取历史波动率
    
    参数:
        symbol: 合约代码
        days: 历史天数（默认30天）
    """
    try:
        data = request.json
        symbol = data.get('symbol', 'KQ.m@SHFE.cu')
        days = int(data.get('days', 30))
        
        volatility = data_fetcher.calculate_historical_volatility(symbol, days)
        
        if volatility is not None:
            return jsonify({
                'success': True,
                'data': {
                    'symbol': symbol,
                    'days': days,
                    'historical_volatility': float(volatility),
                    'annualized': True
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '无法计算历史波动率'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/real-time-options', methods=['POST'])
def get_real_time_options():
    """
    获取实时期权链数据
    
    参数:
        underlying: 标的代码（如 CU, AU）
        exchange: 交易所（默认 SHFE）
    """
    try:
        data = request.json
        underlying = data.get('underlying', 'CU')
        exchange = data.get('exchange', 'SHFE')
        
        option_chain = data_fetcher.get_real_time_option_chain(underlying, exchange)
        
        if option_chain:
            return jsonify({
                'success': True,
                'data': option_chain
            })
        else:
            return jsonify({
                'success': False,
                'error': '无法获取实时期权数据'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/historical-klines', methods=['POST'])
def get_historical_klines():
    """
    获取历史K线数据
    
    参数:
        symbol: 合约代码
        days: 历史天数（默认30天）
    """
    try:
        data = request.json
        symbol = data.get('symbol', 'KQ.m@SHFE.cu')
        days = int(data.get('days', 30))
        
        df = data_fetcher.get_historical_klines(symbol, days)
        
        if df is not None and len(df) > 0:
            klines = df.to_dict('records')
            return jsonify({
                'success': True,
                'data': {
                    'symbol': symbol,
                    'days': days,
                    'klines': klines,
                    'count': len(klines)
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '无法获取历史K线数据'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
