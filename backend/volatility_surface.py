import numpy as np
from scipy.interpolate import griddata
from scipy.optimize import curve_fit
import pandas as pd


class VolatilitySurface:
    def __init__(self):
        self.surface_data = None
    
    def polynomial_fit(self, X, Y, Z, degree=2):
        def poly_func(xy, *coeffs):
            x, y = xy
            z = np.zeros_like(x)
            idx = 0
            for i in range(degree + 1):
                for j in range(degree + 1 - i):
                    z += coeffs[idx] * (x ** i) * (y ** j)
                    idx += 1
            return z
        
        num_coeffs = (degree + 1) * (degree + 2) // 2
        initial_guess = np.ones(num_coeffs)
        
        try:
            popt, _ = curve_fit(poly_func, (X.ravel(), Y.ravel()), Z.ravel(), p0=initial_guess)
            return popt, poly_func
        except:
            return None, None
    
    def svr_fit(self, X, Y, Z):
        from sklearn.svm import SVR
        from sklearn.preprocessing import StandardScaler
        
        scaler_X = StandardScaler()
        scaler_Z = StandardScaler()
        
        XY = np.column_stack([X.ravel(), Y.ravel()])
        XY_scaled = scaler_X.fit_transform(XY)
        Z_scaled = scaler_Z.fit_transform(Z.ravel().reshape(-1, 1)).ravel()
        
        svr = SVR(kernel='rbf', C=100, gamma='scale', epsilon=0.01)
        svr.fit(XY_scaled, Z_scaled)
        
        return svr, scaler_X, scaler_Z
    
    def fit_surface(self, strikes, maturities, implied_vols, method='polynomial'):
        strikes = np.array(strikes)
        maturities = np.array(maturities)
        implied_vols = np.array(implied_vols)
        
        K, T = np.meshgrid(strikes, maturities)
        
        if method == 'polynomial':
            coeffs, poly_func = self.polynomial_fit(K, T, implied_vols)
            self.fit_method = 'polynomial'
            self.coeffs = coeffs
            self.poly_func = poly_func
        else:
            self.svr_model, self.scaler_X, self.scaler_Z = self.svr_fit(K, T, implied_vols)
            self.fit_method = 'svr'
        
        self.strikes = strikes
        self.maturities = maturities
        self.implied_vols = implied_vols
        
        return True
    
    def predict_volatility(self, strike, maturity):
        if self.fit_method == 'polynomial':
            return self.poly_func((np.array([strike]), np.array([maturity])), *self.coeffs)[0]
        else:
            XY = np.array([[strike, maturity]])
            XY_scaled = self.scaler_X.transform(XY)
            z_scaled = self.svr_model.predict(XY_scaled)
            return self.scaler_Z.inverse_transform(z_scaled.reshape(-1, 1))[0, 0]
    
    def generate_surface_grid(self, num_points=50):
        K_min, K_max = self.strikes.min(), self.strikes.max()
        T_min, T_max = self.maturities.min(), self.maturities.max()
        
        K_grid = np.linspace(K_min, K_max, num_points)
        T_grid = np.linspace(T_min, T_max, num_points)
        K_mesh, T_mesh = np.meshgrid(K_grid, T_grid)
        
        if self.fit_method == 'polynomial':
            IV_grid = self.poly_func((K_mesh.ravel(), T_mesh.ravel()), *self.coeffs).reshape(K_mesh.shape)
        else:
            XY = np.column_stack([K_mesh.ravel(), T_mesh.ravel()])
            XY_scaled = self.scaler_X.transform(XY)
            IV_scaled = self.svr_model.predict(XY_scaled)
            IV_grid = self.scaler_Z.inverse_transform(IV_scaled.reshape(-1, 1)).reshape(K_mesh.shape)
        
        return K_mesh, T_mesh, IV_grid
    
    def to_json(self, num_points=30):
        K_mesh, T_mesh, IV_grid = self.generate_surface_grid(num_points)
        
        data = {
            'strikes': K_mesh.tolist(),
            'maturities': T_mesh.tolist(),
            'implied_vols': IV_grid.tolist(),
            'original_strikes': self.strikes.tolist(),
            'original_maturities': self.maturities.tolist(),
            'original_ivs': self.implied_vols.tolist()
        }
        
        return data
