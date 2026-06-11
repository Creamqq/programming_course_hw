/** 后端API类型定义 */

export interface ContractInfo {
  symbol: string
  name: string
  exchange: string
  product_id: string
  multiplier: number
  margin_ratio: number
}

export interface KlineData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number
  open_interest: number
  close_interest: number
}

export interface QuoteData {
  symbol: string
  last_price: number
  ask_price: number
  bid_price: number
  ask_volume: number
  bid_volume: number
  volume: number
  open_interest: number
  highest: number
  lowest: number
  open: number
  pre_close: number
  pre_settlement: number
  settlement: number
  upper_limit: number
  lower_limit: number
  datetime: string
}

export interface FactorInfo {
  name: string
  label: string
  description: string
}

export interface FactorValue {
  symbol: string
  factor_value: number
  rank: number
}

export interface PortfolioPosition {
  symbol: string
  direction: 'long' | 'short'
  weight: number
  lots?: number
}

export interface BacktestConfig {
  start_date: string
  end_date: string
  initial_capital: number
  commission_rate: number
  slippage: number
  rebalance_freq: 'daily' | 'weekly' | 'monthly'
  long_ratio: number
  short_ratio: number
  factor_name: string
  universe: string[]
}

export interface BacktestResult {
  total_return: number
  annual_return: number
  sharpe_ratio: number
  max_drawdown: number
  calmar_ratio: number
  win_rate: number
  profit_loss_ratio: number
  daily_returns: Array<{ date: string; return: number }>
  equity_curve: Array<{ date: string; equity: number }>
  drawdown_curve: Array<{ date: string; drawdown: number }>
  trades: Array<{
    date: string
    symbol: string
    direction: string
    action: string
  }>
}

export interface TradeSignal {
  symbol: string
  direction: 'buy' | 'sell' | 'close_long' | 'close_short'
  lots: number
  price?: number
  reason?: string
}

export interface ICSummary {
  ic_mean: number
  ic_std: number
  ir: number
  ic_positive_rate: number
}
