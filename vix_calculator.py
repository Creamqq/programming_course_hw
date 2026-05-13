import numpy as np
from scipy.interpolate import interp1d
from datetime import datetime, timedelta
import pandas as pd


class VIXCalculator:
    def __init__(self, risk_free_rate=0.03):
        self.risk_free_rate = risk_free_rate
    
    def calculate_time_to_expiry(self, expiry_date, current_date):
        delta = (expiry_date - current_date).total_seconds()
        minutes = delta / 60
        days = minutes / (24 * 60)
        years = days / 365
        return days, years
    
    def calculate_forward_price(self, calls_df, puts_df, risk_free_rate, time_to_expiry_years):
        min_diff_idx = None
        min_diff = float('inf')
        
        for idx, call_row in calls_df.iterrows():
            strike = call_row['strike']
            put_row = puts_df[puts_df['strike'] == strike]
            if not put_row.empty:
                diff = abs(call_row['price'] - put_row.iloc[0]['price'])
                if diff < min_diff:
                    min_diff = diff
                    min_diff_idx = strike
        
        if min_diff_idx is None:
            return None
        
        call_price = calls_df[calls_df['strike'] == min_diff_idx]['price'].values[0]
        put_price = puts_df[puts_df['strike'] == min_diff_idx]['price'].values[0]
        
        forward_price = min_diff_idx + np.exp(risk_free_rate * time_to_expiry_years) * (call_price - put_price)
        return forward_price
    
    def calculate_variance(self, options_df, forward_price, risk_free_rate, time_to_expiry_years):
        options_df = options_df.copy()
        options_df['delta_k'] = options_df['strike'].diff().fillna(0)
        
        variance = 0
        for idx, row in options_df.iterrows():
            strike = row['strike']
            option_price = row['price']
            delta_k = row['delta_k']
            
            if delta_k == 0:
                continue
            
            contribution = (delta_k / (strike ** 2)) * np.exp(risk_free_rate * time_to_expiry_years) * option_price
            variance += contribution
        
        variance *= (2 / time_to_expiry_years)
        forward_term = (forward_price / 0.5 - 1) ** 2 / time_to_expiry_years
        variance += forward_term
        
        return variance
    
    def calculate_vix(self, near_term_options, next_term_options, near_expiry, next_expiry, current_date):
        near_days, near_years = self.calculate_time_to_expiry(near_expiry, current_date)
        next_days, next_years = self.calculate_time_to_expiry(next_expiry, current_date)
        
        near_calls = near_term_options[near_term_options['type'] == 'call']
        near_puts = near_term_options[near_term_options['type'] == 'put']
        next_calls = next_term_options[next_term_options['type'] == 'call']
        next_puts = next_term_options[next_term_options['type'] == 'put']
        
        near_forward = self.calculate_forward_price(near_calls, near_puts, self.risk_free_rate, near_years)
        next_forward = self.calculate_forward_price(next_calls, next_puts, self.risk_free_rate, next_years)
        
        near_variance = self.calculate_variance(near_term_options, near_forward, self.risk_free_rate, near_years)
        next_variance = self.calculate_variance(next_term_options, next_forward, self.risk_free_rate, next_years)
        
        t1 = near_days
        t2 = next_days
        t30 = 30
        nt1 = t1 - t30
        nt2 = t30 - t1
        n30 = t2 - t1
        
        if n30 != 0:
            vix_squared = (t1 * near_variance * nt2 + t2 * next_variance * nt1) / n30
        else:
            vix_squared = near_variance
        
        vix = np.sqrt(vix_squared) * 100
        return vix
    
    def calculate_simple_vix(self, options_data, underlying_price, days_to_expiry=30):
        if isinstance(options_data, pd.DataFrame):
            options = options_data
        else:
            options = pd.DataFrame(options_data)
        
        atm_strike = round(underlying_price / 100) * 100
        otm_calls = options[(options['type'] == 'call') & (options['strike'] > atm_strike)]
        otm_puts = options[(options['type'] == 'put') & (options['strike'] < atm_strike)]
        
        all_otm = pd.concat([otm_calls, otm_puts])
        
        if len(all_otm) == 0:
            return 0
        
        implied_vols = all_otm['implied_vol'].values
        weights = 1 / (all_otm['strike'].sub(underlying_price).abs() + 1).values
        
        weighted_vol = np.average(implied_vols, weights=weights)
        vix = weighted_vol * np.sqrt(days_to_expiry / 30)
        
        return vix * 100


def calculate_vix_from_tqsdk(api, option_symbol):
    from tqsdk import TqApi
    from datetime import datetime
    
    vix_calc = VIXCalculator()
    
    quote = api.get_quote(option_symbol)
    underlying_price = quote.last_price
    
    near_expiry = datetime.now() + timedelta(days=7)
    next_expiry = datetime.now() + timedelta(days=37)
    
    vix = vix_calc.calculate_simple_vix([], underlying_price)
    
    return vix
