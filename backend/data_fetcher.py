from tqsdk import TqApi, TqAuth
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


class TqsdkDataFetcher:
    def __init__(self, account=None, password=None):
        self.account = account or os.getenv('TQ_ACCOUNT')
        self.password = password or os.getenv('TQ_PASSWORD')
        self.api = None
    
    def connect(self):
        try:
            if self.account and self.password:
                self.api = TqApi(auth=TqAuth(self.account, self.password))
            else:
                print("警告: 未配置天勤账户信息，将使用模拟账户")
                self.api = TqApi()
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False
    
    def disconnect(self):
        if self.api:
            self.api.close()
    
    def get_option_chain(self, underlying_symbol, exchange="SHFE"):
        try:
            option_quotes = []
            
            if exchange == "SHFE":
                if "CU" in underlying_symbol.upper():
                    options = self._get_cu_options(underlying_symbol)
                elif "AU" in underlying_symbol.upper():
                    options = self._get_au_options(underlying_symbol)
                else:
                    options = self._get_generic_options(underlying_symbol, exchange)
            else:
                options = self._get_generic_options(underlying_symbol, exchange)
            
            return options
        except Exception as e:
            print(f"获取期权链失败: {e}")
            return []
    
    def _get_cu_options(self, underlying):
        options = []
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        for month_offset in range(1, 4):
            target_month = current_month + month_offset
            target_year = current_year
            if target_month > 12:
                target_month -= 12
                target_year += 1
            
            month_str = f"{target_year}{target_month:02d}"
            
            for strike in range(50000, 80000, 1000):
                call_symbol = f"KQ.m@SHFE.cu{month_str}C{strike}"
                put_symbol = f"KQ.m@SHFE.cu{month_str}P{strike}"
                
                options.append({
                    'symbol': call_symbol,
                    'underlying': underlying,
                    'strike': strike,
                    'type': 'call',
                    'expiry': f"{target_year}-{target_month:02d}"
                })
                options.append({
                    'symbol': put_symbol,
                    'underlying': underlying,
                    'strike': strike,
                    'type': 'put',
                    'expiry': f"{target_year}-{target_month:02d}"
                })
        
        return options
    
    def _get_au_options(self, underlying):
        options = []
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        for month_offset in range(1, 4):
            target_month = current_month + month_offset
            target_year = current_year
            if target_month > 12:
                target_month -= 12
                target_year += 1
            
            month_str = f"{target_year}{target_month:02d}"
            
            for strike in range(400, 500, 2):
                call_symbol = f"KQ.m@SHFE.au{month_str}C{strike}"
                put_symbol = f"KQ.m@SHFE.au{month_str}P{strike}"
                
                options.append({
                    'symbol': call_symbol,
                    'underlying': underlying,
                    'strike': strike,
                    'type': 'call',
                    'expiry': f"{target_year}-{target_month:02d}"
                })
                options.append({
                    'symbol': put_symbol,
                    'underlying': underlying,
                    'strike': strike,
                    'type': 'put',
                    'expiry': f"{target_year}-{target_month:02d}"
                })
        
        return options
    
    def _get_generic_options(self, underlying, exchange):
        return []
    
    def get_option_quote(self, symbol):
        try:
            quote = self.api.get_quote(symbol)
            self.api.wait_update()
            
            days_to_expiry = None
            expire_datetime = None
            if hasattr(quote, 'expire_datetime') and quote.expire_datetime:
                from datetime import datetime
                expire_datetime = quote.expire_datetime
                expire_dt = datetime.fromtimestamp(quote.expire_datetime / 1e9)
                days_to_expiry = max((expire_dt - datetime.now()).days, 0)
            
            exchange = getattr(quote, 'exchange', None)
            product_id = getattr(quote, 'product_id', None)
            instrument_id = getattr(quote, 'instrument_id', None)
            
            return {
                'symbol': symbol,
                'last_price': quote.last_price,
                'bid_price': quote.bid_price1,
                'ask_price': quote.ask_price1,
                'volume': quote.volume,
                'open_interest': quote.open_interest,
                'strike': quote.strike_price,
                'underlying': quote.underlying_symbol,
                'expire_datetime': expire_datetime,
                'days_to_expiry': days_to_expiry,
                'exchange': exchange,
                'product_id': product_id,
                'instrument_id': instrument_id
            }
        except Exception as e:
            print(f"获取期权报价失败: {e}")
            return None
    
    def get_underlying_price(self, symbol):
        try:
            quote = self.api.get_quote(symbol)
            self.api.wait_update()
            return quote.last_price
        except Exception as e:
            print(f"获取标的价格失败: {e}")
            return None
    
    def calculate_days_to_expiry(self, expiry_date):
        expiry = datetime.strptime(expiry_date, "%Y-%m-%d")
        today = datetime.now()
        days = (expiry - today).days
        return max(days, 0)
    
    def get_historical_klines(self, symbol, days=30):
        """
        获取历史K线数据
        
        Args:
            symbol: 合约代码
            days: 历史天数
        
        Returns:
            DataFrame: 历史K线数据
        """
        try:
            if not self.api:
                self.connect()
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            klines = self.api.get_kline_serial(
                symbol,
                24 * 60 * 60,
                data_length=days
            )
            
            self.api.wait_update()
            
            df = klines.to_dataframe()
            df['datetime'] = pd.to_datetime(df['datetime'], unit='ns')
            
            return df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            print(f"获取历史K线失败: {e}")
            return None
    
    def calculate_historical_volatility(self, symbol, days=30):
        """
        计算历史波动率
        
        Args:
            symbol: 合约代码
            days: 历史天数
        
        Returns:
            float: 年化历史波动率
        """
        try:
            df = self.get_historical_klines(symbol, days)
            
            if df is None or len(df) < 2:
                return None
            
            df['returns'] = df['close'].pct_change()
            
            df = df.dropna()
            
            volatility = df['returns'].std() * np.sqrt(252)
            
            return volatility
        except Exception as e:
            print(f"计算历史波动率失败: {e}")
            return None
    
    def get_real_time_option_chain(self, underlying_symbol, exchange="SHFE"):
        """
        获取实时期权链数据
        
        Args:
            underlying_symbol: 标的代码
            exchange: 交易所
        
        Returns:
            dict: 期权链数据
        """
        try:
            if not self.api:
                self.connect()
            
            options = self.get_option_chain(underlying_symbol, exchange)
            
            underlying_price = self.get_underlying_price(f"KQ.m@{exchange}.{underlying_symbol.lower()}")
            
            option_data = []
            for opt in options[:20]:
                quote = self.get_option_quote(opt['symbol'])
                
                if quote and quote['last_price'] > 0:
                    days_to_expiry = self.calculate_days_to_expiry(opt['expiry'])
                    
                    option_data.append({
                        'symbol': opt['symbol'],
                        'strike': opt['strike'],
                        'type': opt['type'],
                        'price': quote['last_price'],
                        'bid': quote['bid_price'],
                        'ask': quote['ask_price'],
                        'volume': quote['volume'],
                        'open_interest': quote['open_interest'],
                        'expiry': opt['expiry'],
                        'days_to_expiry': days_to_expiry
                    })
            
            return {
                'underlying_price': underlying_price,
                'underlying_symbol': underlying_symbol,
                'options': option_data,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"获取实时期权链失败: {e}")
            return None
    
    def get_option_chain_by_symbol(self, symbol):
        """
        根据合约代码获取同系列期权链
        
        Args:
            symbol: 期权合约代码（如 SHFE.cu2610C126000）
        
        Returns:
            dict: 期权链数据
        """
        try:
            if not self.api:
                self.connect()
            
            quote = self.get_option_quote(symbol)
            if not quote:
                return None
            
            underlying_symbol = quote.get('underlying')
            exchange = quote.get('exchange')
            
            if not underlying_symbol:
                return None
            
            underlying_price = self.get_underlying_price(underlying_symbol)
            
            option_symbols = self.api.query_options(underlying_symbol)
            
            self.api.wait_update()
            
            option_data = []
            for opt_symbol in option_symbols:
                opt_quote = self.get_option_quote(opt_symbol)
                
                if opt_quote and opt_quote['last_price'] > 0:
                    option_data.append({
                        'symbol': opt_symbol,
                        'strike': opt_quote['strike'],
                        'type': 'call' if 'C' in opt_symbol.upper() else 'put',
                        'price': opt_quote['last_price'],
                        'bid': opt_quote['bid_price'],
                        'ask': opt_quote['ask_price'],
                        'volume': opt_quote['volume'],
                        'open_interest': opt_quote['open_interest'],
                        'days_to_expiry': opt_quote.get('days_to_expiry'),
                        'expire_datetime': opt_quote.get('expire_datetime')
                    })
            
            return {
                'underlying_price': underlying_price,
                'underlying_symbol': underlying_symbol,
                'exchange': exchange,
                'options': option_data,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"根据合约代码获取期权链失败: {e}")
            return None
    
    def _get_strike_step(self, product):
        """获取不同品种的行权价步长"""
        strike_steps = {
            'cu': 1000,
            'au': 2,
            'al': 50,
            'zn': 100,
            'rb': 50,
            'ru': 100,
            'm': 10,
            'c': 10,
            'p': 10,
            'cf': 100,
            'sr': 100,
            'ta': 50,
            'ma': 25,
            'i': 5,
            'j': 5,
            'jm': 5
        }
        return strike_steps.get(product.lower(), 100)
