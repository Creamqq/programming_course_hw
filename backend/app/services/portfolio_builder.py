"""组合构建模块 - 多空信号生成与权重分配"""
import pandas as pd
import numpy as np
from typing import Optional

from app.services.factor_engine import factor_engine


class PortfolioBuilder:
    """截面多空组合构建"""

    @staticmethod
    def build_long_short(
        factor_df: pd.DataFrame,
        long_ratio: float = 0.3,
        short_ratio: float = 0.3,
        weight_method: str = "equal",
    ) -> pd.DataFrame:
        """
        根据因子排名构建多空组合
        factor_df: 包含 symbol, factor_value, rank 列
        long_ratio: 做多比例（排名前N%）
        short_ratio: 做空比例（排名后N%）
        weight_method: equal(等权) / factor(因子强度加权)
        返回: DataFrame with columns [symbol, direction, weight]
        """
        n = len(factor_df)
        if n == 0:
            return pd.DataFrame(columns=["symbol", "direction", "weight"])

        n_long = max(1, int(n * long_ratio))
        n_short = max(1, int(n * short_ratio))

        # 排名靠前做多（因子值大），排名靠后做空
        sorted_df = factor_df.sort_values("rank")
        long_symbols = sorted_df.head(n_long)
        short_symbols = sorted_df.tail(n_short)

        # 计算权重
        if weight_method == "equal":
            long_weight = 1.0 / n_long
            short_weight = 1.0 / n_short
            long_symbols = long_symbols.assign(direction="long", weight=long_weight)
            short_symbols = short_symbols.assign(direction="short", weight=short_weight)
        elif weight_method == "factor":
            long_vals = long_symbols["factor_value"].abs()
            short_vals = short_symbols["factor_value"].abs()
            long_symbols = long_symbols.assign(
                direction="long",
                weight=long_vals / long_vals.sum(),
            )
            short_symbols = short_symbols.assign(
                direction="short",
                weight=short_vals / short_vals.sum(),
            )
        else:
            raise ValueError(f"未知权重方法: {weight_method}")

        portfolio = pd.concat([long_symbols[["symbol", "direction", "weight"]]])
        short_port = short_symbols[["symbol", "direction", "weight"]]
        portfolio = pd.concat([portfolio, short_port], ignore_index=True)
        return portfolio

    @staticmethod
    def rebalance(
        current_positions: pd.DataFrame,
        target_positions: pd.DataFrame,
    ) -> dict:
        """
        计算换仓指令
        current_positions: 当前持仓 [symbol, direction, weight, lots]
        target_positions: 目标持仓 [symbol, direction, weight]
        返回: {to_open: [...], to_close: [...], to_adjust: [...]}
        """
        result = {"to_open": [], "to_close": [], "to_adjust": []}

        current_set = set(
            zip(current_positions["symbol"], current_positions["direction"])
        ) if not current_positions.empty else set()
        target_set = set(
            zip(target_positions["symbol"], target_positions["direction"])
        )

        # 需要新开的仓位
        for symbol, direction in target_set - current_set:
            row = target_positions[
                (target_positions["symbol"] == symbol) &
                (target_positions["direction"] == direction)
            ].iloc[0]
            result["to_open"].append({
                "symbol": symbol,
                "direction": direction,
                "weight": row["weight"],
            })

        # 需要平仓的仓位
        for symbol, direction in current_set - target_set:
            result["to_close"].append({
                "symbol": symbol,
                "direction": direction,
            })

        # 需要调整权重的仓位
        for symbol, direction in current_set & target_set:
            curr = current_positions[
                (current_positions["symbol"] == symbol) &
                (current_positions["direction"] == direction)
            ].iloc[0]
            tgt = target_positions[
                (target_positions["symbol"] == symbol) &
                (target_positions["direction"] == direction)
            ].iloc[0]
            if abs(curr["weight"] - tgt["weight"]) > 0.01:
                result["to_adjust"].append({
                    "symbol": symbol,
                    "direction": direction,
                    "old_weight": curr["weight"],
                    "new_weight": tgt["weight"],
                })

        return result

    def build_from_data(
        self,
        data_dict: dict[str, pd.DataFrame],
        factor_name: str = "momentum",
        long_ratio: float = 0.3,
        short_ratio: float = 0.3,
        weight_method: str = "equal",
        preprocess: bool = True,
        **factor_kwargs,
    ) -> pd.DataFrame:
        """一站式：从数据到组合"""
        factor_df = factor_engine.compute_cross_section(
            data_dict, factor_name, preprocess=preprocess, **factor_kwargs
        )
        portfolio = self.build_long_short(
            factor_df, long_ratio, short_ratio, weight_method
        )
        return portfolio


# 全局单例
portfolio_builder = PortfolioBuilder()
