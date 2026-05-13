import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Tuple
from enum import Enum


class OptionType(Enum):
    CALL = "call"
    PUT = "put"


class PositionType(Enum):
    LONG = 1
    SHORT = -1


@dataclass
class OptionPosition:
    option_type: OptionType
    strike: float
    premium: float
    position: PositionType
    quantity: int = 1
    
    def get_intrinsic_value(self, underlying_price: float) -> float:
        if self.option_type == OptionType.CALL:
            intrinsic = max(0, underlying_price - self.strike)
        else:
            intrinsic = max(0, self.strike - underlying_price)
        return intrinsic * self.position.value * self.quantity
    
    def get_pnl_at_expiry(self, underlying_price: float) -> float:
        intrinsic = self.get_intrinsic_value(underlying_price)
        premium_pnl = -self.premium * self.position.value * self.quantity
        return intrinsic + premium_pnl


class OptionStrategy:
    def __init__(self, name: str, positions: List[OptionPosition]):
        self.name = name
        self.positions = positions
    
    def get_pnl_at_expiry(self, underlying_price: float) -> float:
        total_pnl = 0
        for pos in self.positions:
            total_pnl += pos.get_pnl_at_expiry(underlying_price)
        return total_pnl
    
    def get_pnl_profile(self, price_range: np.ndarray) -> np.ndarray:
        return np.array([self.get_pnl_at_expiry(price) for price in price_range])
    
    def get_breakeven_points(self, price_range: np.ndarray) -> List[float]:
        pnl_profile = self.get_pnl_profile(price_range)
        breakeven_points = []
        
        for i in range(len(pnl_profile) - 1):
            if pnl_profile[i] * pnl_profile[i + 1] < 0:
                x1, x2 = price_range[i], price_range[i + 1]
                y1, y2 = pnl_profile[i], pnl_profile[i + 1]
                breakeven = x1 - y1 * (x2 - x1) / (y2 - y1)
                breakeven_points.append(breakeven)
        
        return breakeven_points
    
    def get_max_profit(self, price_range: np.ndarray) -> float:
        pnl_profile = self.get_pnl_profile(price_range)
        return np.max(pnl_profile)
    
    def get_max_loss(self, price_range: np.ndarray) -> float:
        pnl_profile = self.get_pnl_profile(price_range)
        return np.min(pnl_profile)
    
    def get_net_premium(self) -> float:
        net_premium = 0
        for pos in self.positions:
            net_premium += pos.premium * pos.position.value * pos.quantity
        return net_premium


class StrategyBuilder:
    @staticmethod
    def build_short_straddle(underlying_price: float, call_premium: float, put_premium: float, 
                             quantity: int = 1) -> OptionStrategy:
        atm_strike = round(underlying_price / 100) * 100
        
        positions = [
            OptionPosition(OptionType.CALL, atm_strike, call_premium, PositionType.SHORT, quantity),
            OptionPosition(OptionType.PUT, atm_strike, put_premium, PositionType.SHORT, quantity)
        ]
        return OptionStrategy("双卖（Short Straddle）", positions)
    
    @staticmethod
    def build_short_strangle(underlying_price: float, call_strike: float, put_strike: float,
                            call_premium: float, put_premium: float, quantity: int = 1) -> OptionStrategy:
        positions = [
            OptionPosition(OptionType.CALL, call_strike, call_premium, PositionType.SHORT, quantity),
            OptionPosition(OptionType.PUT, put_strike, put_premium, PositionType.SHORT, quantity)
        ]
        return OptionStrategy("宽跨式双卖（Short Strangle）", positions)
    
    @staticmethod
    def build_iron_condor(underlying_price: float, put_strike_low: float, put_strike_high: float,
                         call_strike_low: float, call_strike_high: float,
                         put_premium_low: float, put_premium_high: float,
                         call_premium_low: float, call_premium_high: float,
                         quantity: int = 1) -> OptionStrategy:
        positions = [
            OptionPosition(OptionType.PUT, put_strike_low, put_premium_low, PositionType.LONG, quantity),
            OptionPosition(OptionType.PUT, put_strike_high, put_premium_high, PositionType.SHORT, quantity),
            OptionPosition(OptionType.CALL, call_strike_low, call_premium_low, PositionType.SHORT, quantity),
            OptionPosition(OptionType.CALL, call_strike_high, call_premium_high, PositionType.LONG, quantity)
        ]
        return OptionStrategy("铁鹰（Iron Condor）", positions)
    
    @staticmethod
    def build_calendar_spread(underlying_price: float, strike: float,
                             near_premium: float, far_premium: float,
                             near_position: PositionType = PositionType.SHORT,
                             far_position: PositionType = PositionType.LONG,
                             option_type: OptionType = OptionType.CALL,
                             quantity: int = 1) -> OptionStrategy:
        positions = [
            OptionPosition(option_type, strike, near_premium, near_position, quantity),
            OptionPosition(option_type, strike, far_premium, far_position, quantity)
        ]
        return OptionStrategy("日历价差（Calendar Spread）", positions)
    
    @staticmethod
    def build_butterfly_spread(underlying_price: float, lower_strike: float, middle_strike: float,
                               upper_strike: float, lower_premium: float, middle_premium: float,
                               upper_premium: float, option_type: OptionType = OptionType.CALL,
                               quantity: int = 1) -> OptionStrategy:
        positions = [
            OptionPosition(option_type, lower_strike, lower_premium, PositionType.LONG, quantity),
            OptionPosition(option_type, middle_strike, middle_premium, PositionType.SHORT, quantity * 2),
            OptionPosition(option_type, upper_strike, upper_premium, PositionType.LONG, quantity)
        ]
        return OptionStrategy("蝶式价差（Butterfly Spread）", positions)


def create_crude_oil_strategies(underlying_price: float = 500.0):
    strategies = []
    
    straddle = StrategyBuilder.build_short_straddle(
        underlying_price=underlying_price,
        call_premium=15.0,
        put_premium=12.0,
        quantity=1
    )
    strategies.append(straddle)
    
    strangle = StrategyBuilder.build_short_strangle(
        underlying_price=underlying_price,
        call_strike=520.0,
        put_strike=480.0,
        call_premium=8.0,
        put_premium=6.0,
        quantity=1
    )
    strategies.append(strangle)
    
    iron_condor = StrategyBuilder.build_iron_condor(
        underlying_price=underlying_price,
        put_strike_low=460.0,
        put_strike_high=480.0,
        call_strike_low=520.0,
        call_strike_high=540.0,
        put_premium_low=3.0,
        put_premium_high=6.0,
        call_premium_low=8.0,
        call_premium_high=4.0,
        quantity=1
    )
    strategies.append(iron_condor)
    
    calendar = StrategyBuilder.build_calendar_spread(
        underlying_price=underlying_price,
        strike=500.0,
        near_premium=10.0,
        far_premium=18.0,
        near_position=PositionType.SHORT,
        far_position=PositionType.LONG,
        option_type=OptionType.CALL,
        quantity=1
    )
    strategies.append(calendar)
    
    return strategies
