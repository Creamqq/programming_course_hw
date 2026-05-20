import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq


class OptionGreeks:
    def __init__(self, S, K, T, r, sigma, option_type='call'):
        self.S = S
        self.K = K
        self.T = T
        self.r = r
        self.sigma = sigma
        self.option_type = option_type
    
    def _d1(self):
        d1 = (np.log(self.S / self.K) + (self.r + 0.5 * self.sigma ** 2) * self.T) / (self.sigma * np.sqrt(self.T))
        return d1
    
    def _d2(self):
        d2 = self._d1() - self.sigma * np.sqrt(self.T)
        return d2
    
    def delta(self):
        d1 = self._d1()
        if self.option_type == 'call':
            return norm.cdf(d1)
        else:
            return norm.cdf(d1) - 1
    
    def gamma(self):
        d1 = self._d1()
        return norm.pdf(d1) / (self.S * self.sigma * np.sqrt(self.T))
    
    def theta(self):
        d1 = self._d1()
        d2 = self._d2()
        first_term = -(self.S * norm.pdf(d1) * self.sigma) / (2 * np.sqrt(self.T))
        
        if self.option_type == 'call':
            second_term = -self.r * self.K * np.exp(-self.r * self.T) * norm.cdf(d2)
        else:
            second_term = self.r * self.K * np.exp(-self.r * self.T) * norm.cdf(-d2)
        
        return (first_term + second_term) / 365
    
    def vega(self):
        d1 = self._d1()
        return self.S * norm.pdf(d1) * np.sqrt(self.T) / 100
    
    def rho(self):
        d2 = self._d2()
        if self.option_type == 'call':
            return self.K * self.T * np.exp(-self.r * self.T) * norm.cdf(d2) / 100
        else:
            return -self.K * self.T * np.exp(-self.r * self.T) * norm.cdf(-d2) / 100
    
    def option_price(self):
        d1 = self._d1()
        d2 = self._d2()
        
        if self.option_type == 'call':
            price = self.S * norm.cdf(d1) - self.K * np.exp(-self.r * self.T) * norm.cdf(d2)
        else:
            price = self.K * np.exp(-self.r * self.T) * norm.cdf(-d2) - self.S * norm.cdf(-d1)
        
        return price
    
    def implied_volatility(self, market_price, max_iter=100):
        def objective(sigma):
            self.sigma = sigma
            return self.option_price() - market_price
        
        try:
            iv = brentq(objective, 0.001, 5.0, maxiter=max_iter)
            return iv
        except:
            return None
    
    def calculate_all_greeks(self):
        return {
            'delta': float(self.delta()),
            'gamma': float(self.gamma()),
            'theta': float(self.theta()),
            'vega': float(self.vega()),
            'rho': float(self.rho()),
            'price': float(self.option_price())
        }
