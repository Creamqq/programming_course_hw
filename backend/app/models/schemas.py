"""数据模型定义"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class Exchange(str, Enum):
    DCE = "DCE"        # 大商所
    SHFE = "SHFE"      # 上期所
    CZCE = "CZCE"      # 郑商所
    CFFEX = "CFFEX"    # 中金所
    INE = "INE"        # 能源中心
    GFEX = "GFEX"      # 广期所


class ContractInfo(BaseModel):
    """合约信息"""
    symbol: str
    name: str
    exchange: Exchange
    product_id: str
    multiplier: float       # 合约乘数
    margin_ratio: float     # 保证金率
    commission: float       # 手续费
    open_date: Optional[str] = None
    expire_date: Optional[str] = None


class KlineData(BaseModel):
    """K线数据"""
    symbol: str
    datetime: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    open_interest: float    # 持仓量


class FactorValue(BaseModel):
    """因子值"""
    symbol: str
    factor_name: str
    value: float
    rank: Optional[int] = None
    date: str


class PortfolioPosition(BaseModel):
    """组合持仓"""
    symbol: str
    direction: str          # long / short
    weight: float
    lots: int
    entry_price: float
    current_price: float
    pnl: float


class BacktestConfig(BaseModel):
    """回测配置"""
    start_date: str
    end_date: str
    initial_capital: float = 1_000_000
    commission_rate: float = 0.0001
    slippage: int = 1
    rebalance_freq: str = "daily"   # daily / weekly / monthly
    long_ratio: float = 0.3         # 做多比例
    short_ratio: float = 0.3        # 做空比例
    factor_name: str = "momentum"
    universe: list[str] = []        # 合约池，空则使用默认


class BacktestResult(BaseModel):
    """回测结果"""
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    calmar_ratio: float
    win_rate: float
    profit_loss_ratio: float
    daily_returns: list[dict]
    equity_curve: list[dict]
    drawdown_curve: list[dict]
    trades: list[dict]


class TradeSignal(BaseModel):
    """交易信号"""
    symbol: str
    direction: str      # buy / sell / close_long / close_short
    lots: int
    price: Optional[float] = None
    reason: str = ""
