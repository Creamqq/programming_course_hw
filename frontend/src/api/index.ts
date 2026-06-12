import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// 市场数据
export const marketApi = {
  getContracts: (exchange?: string, forceRefresh = false) =>
    api.get('/market/contracts', { params: { exchange, force_refresh: forceRefresh } }),
  getKline: (symbol: string, startDate: string, endDate: string, freq = 'daily', forceRefresh = false) =>
    api.get(`/market/kline/${symbol}`, { params: { start_date: startDate, end_date: endDate, freq, force_refresh: forceRefresh } }),
  getQuote: (symbol: string) =>
    api.get(`/market/quote/${symbol}`),
  getBatchKline: (symbols: string, startDate: string, endDate: string, freq = 'daily') =>
    api.get('/market/batch-kline', { params: { symbols, start_date: startDate, end_date: endDate, freq } }),
  getCacheStats: () =>
    api.get('/market/cache/stats'),
  prefetchKline: (exchange: string | undefined, startDate: string, endDate: string, freq = 'daily', limit = 20) =>
    api.post('/market/cache/prefetch', null, { params: { exchange: exchange || undefined, start_date: startDate, end_date: endDate, freq, limit } }),
}

// 因子分析
export const factorApi = {
  getFactorList: () =>
    api.get('/factor/list'),
  computeFactor: (symbols: string, factorName: string, startDate: string, endDate: string, window = 20, date?: string) =>
    api.get('/factor/compute', { params: { symbols, factor_name: factorName, start_date: startDate, end_date: endDate, window, date } }),
  computeIC: (symbols: string, factorName: string, startDate: string, endDate: string, window = 20, forwardPeriod = 5) =>
    api.get('/factor/ic', { params: { symbols, factor_name: factorName, start_date: startDate, end_date: endDate, window, forward_period: forwardPeriod } }),
}

// 组合管理
export const portfolioApi = {
  buildPortfolio: (symbols: string, factorName: string, startDate: string, endDate: string, longRatio = 0.3, shortRatio = 0.3, weightMethod = 'equal', window = 20) =>
    api.post('/portfolio/build', null, { params: { symbols, factor_name: factorName, start_date: startDate, end_date: endDate, long_ratio: longRatio, short_ratio: shortRatio, weight_method: weightMethod, window } }),
  getPositions: () =>
    api.get('/portfolio/positions'),
}

// 回测
export const backtestApi = {
  runBacktest: (config: any) =>
    api.post('/backtest/run', config),
  getPresets: () =>
    api.get('/backtest/presets'),
}

// 交易
export const tradeApi = {
  startTrading: () =>
    api.post('/trade/start'),
  stopTrading: () =>
    api.post('/trade/stop'),
  getStatus: () =>
    api.get('/trade/status'),
  executeSignal: (signal: any) =>
    api.post('/trade/signal', signal),
  closeAll: () =>
    api.post('/trade/close-all'),
}

export default api
