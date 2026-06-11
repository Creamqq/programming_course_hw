"""回测引擎 - 截面多空策略回测"""
import pandas as pd
import numpy as np
from typing import Optional
from datetime import datetime

from app.services.factor_engine import factor_engine
from app.services.portfolio_builder import portfolio_builder
from app.models.schemas import BacktestConfig, BacktestResult


class BacktestEngine:
    """截面多空回测引擎"""

    def __init__(self):
        self.trade_log = []

    def run(self, data_dict: dict[str, pd.DataFrame], config: BacktestConfig) -> BacktestResult:
        """
        运行回测
        data_dict: {symbol: kline_df} 每个合约的K线数据
        config: 回测配置
        """
        # 对齐所有合约的日期
        all_dates = self._align_dates(data_dict, config.start_date, config.end_date)
        if len(all_dates) == 0:
            raise ValueError("回测区间内无数据")

        # 确定调仓频率
        rebalance_dates = self._get_rebalance_dates(all_dates, config.rebalance_freq)

        # 逐日回测
        capital = config.initial_capital
        equity_curve = []
        daily_returns = []
        positions = pd.DataFrame()
        all_trades = []

        for i, date in enumerate(all_dates):
            # 获取当日各合约数据（截至当日）
            current_data = self._slice_data(data_dict, date)

            # 计算当日持仓市值和收益
            if not positions.empty and i > 0:
                prev_date = all_dates[i - 1]
                daily_pnl = self._calc_daily_pnl(
                    positions, current_data, prev_date, date, config
                )
                capital += daily_pnl
                daily_ret = daily_pnl / config.initial_capital
            else:
                daily_ret = 0.0

            # 调仓
            if date in rebalance_dates:
                factor_df = factor_engine.compute_cross_section(
                    current_data, config.factor_name, preprocess=True
                )
                if not factor_df.empty:
                    new_positions = portfolio_builder.build_long_short(
                        factor_df, config.long_ratio, config.short_ratio
                    )
                    # 计算手数
                    if not new_positions.empty:
                        new_positions["lots"] = new_positions["weight"].apply(
                            lambda w: max(1, int(capital * w / 100000))  # 简化手数计算
                        )
                    # 记录换仓
                    trades = portfolio_builder.rebalance(positions, new_positions)
                    for t in trades["to_open"]:
                        all_trades.append({
                            "date": date, "symbol": t["symbol"],
                            "direction": t["direction"], "action": "open",
                        })
                    for t in trades["to_close"]:
                        all_trades.append({
                            "date": date, "symbol": t["symbol"],
                            "direction": t["direction"], "action": "close",
                        })
                    positions = new_positions

            equity_curve.append({"date": date, "equity": capital})
            daily_returns.append({"date": date, "return": daily_ret})

        # 计算绩效指标
        result = self._calc_metrics(
            equity_curve, daily_returns, all_trades, config.initial_capital
        )
        return result

    def _align_dates(
        self,
        data_dict: dict[str, pd.DataFrame],
        start_date: str,
        end_date: str,
    ) -> list[str]:
        """对齐所有合约的交易日"""
        all_date_sets = []
        for symbol, df in data_dict.items():
            dates = set(df["date"].astype(str).str[:10].tolist())
            all_date_sets.append(dates)

        if not all_date_sets:
            return []

        # 取交集（所有合约都有的交易日）
        common_dates = all_date_sets[0]
        for ds in all_date_sets[1:]:
            common_dates = common_dates & ds

        sorted_dates = sorted(common_dates)
        return [d for d in sorted_dates if start_date <= d <= end_date]

    def _get_rebalance_dates(self, all_dates: list[str], freq: str) -> set[str]:
        """获取调仓日"""
        if freq == "daily":
            return set(all_dates)
        elif freq == "weekly":
            # 每周第一个交易日
            dates = pd.to_datetime(all_dates)
            rebalance = set()
            for _, group in pd.Series(all_dates).groupby(dates.isocalendar().week):
                rebalance.add(group.iloc[0])
            return rebalance
        elif freq == "monthly":
            dates = pd.to_datetime(all_dates)
            rebalance = set()
            for _, group in pd.Series(all_dates).groupby(dates.to_period("M")):
                rebalance.add(group.iloc[0])
            return rebalance
        return set(all_dates)

    def _slice_data(self, data_dict: dict[str, pd.DataFrame], date: str) -> dict[str, pd.DataFrame]:
        """截取截至date的数据"""
        result = {}
        for symbol, df in data_dict.items():
            mask = df["date"].astype(str).str[:10] <= date
            sliced = df[mask].copy()
            if not sliced.empty:
                result[symbol] = sliced
        return result

    def _calc_daily_pnl(
        self,
        positions: pd.DataFrame,
        current_data: dict[str, pd.DataFrame],
        prev_date: str,
        curr_date: str,
        config: BacktestConfig,
    ) -> float:
        """计算当日盈亏"""
        total_pnl = 0.0
        for _, pos in positions.iterrows():
            symbol = pos["symbol"]
            direction = pos["direction"]
            lots = pos.get("lots", 1)

            if symbol not in current_data:
                continue

            df = current_data[symbol]
            prev_row = df[df["date"].astype(str).str[:10] == prev_date]
            curr_row = df[df["date"].astype(str).str[:10] == curr_date]

            if prev_row.empty or curr_row.empty:
                continue

            prev_close = prev_row.iloc[-1]["close"]
            curr_close = curr_row.iloc[-1]["close"]
            price_change = curr_close - prev_close

            # 扣除手续费
            commission = curr_close * lots * config.commission_rate
            slippage_cost = config.slippage * lots

            if direction == "long":
                pnl = price_change * lots * 10 - commission - slippage_cost  # 10为简化乘数
            else:
                pnl = -price_change * lots * 10 - commission - slippage_cost

            total_pnl += pnl
        return total_pnl

    def _calc_metrics(
        self,
        equity_curve: list[dict],
        daily_returns: list[dict],
        trades: list[dict],
        initial_capital: float,
    ) -> BacktestResult:
        """计算回测绩效指标"""
        eq_df = pd.DataFrame(equity_curve)
        ret_df = pd.DataFrame(daily_returns)

        if ret_df.empty:
            return BacktestResult(
                total_return=0, annual_return=0, sharpe_ratio=0,
                max_drawdown=0, calmar_ratio=0, win_rate=0,
                profit_loss_ratio=0, daily_returns=[], equity_curve=[],
                drawdown_curve=[], trades=[],
            )

        # 总收益
        final_equity = eq_df["equity"].iloc[-1]
        total_return = (final_equity - initial_capital) / initial_capital

        # 年化收益
        n_days = len(eq_df)
        annual_return = (1 + total_return) ** (252 / max(n_days, 1)) - 1

        # Sharpe
        daily_ret: np.ndarray = np.asarray(ret_df["return"].values, dtype=np.float64)
        sharpe = float(daily_ret.mean()) / max(float(daily_ret.std()), 1e-8) * np.sqrt(252)

        # 最大回撤
        equity: np.ndarray = np.asarray(eq_df["equity"].values, dtype=np.float64)
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        max_drawdown = abs(float(drawdown.min()))

        # Calmar
        calmar = annual_return / max(max_drawdown, 1e-8)

        # 胜率
        win_days = int(np.sum(daily_ret > 0))
        win_rate = win_days / max(len(daily_ret), 1)

        # 盈亏比
        avg_win = float(daily_ret[daily_ret > 0].mean()) if np.any(daily_ret > 0) else 0.0
        avg_loss = abs(float(daily_ret[daily_ret < 0].mean())) if np.any(daily_ret < 0) else 1.0
        profit_loss_ratio = avg_win / max(avg_loss, 1e-8)

        # 回撤曲线
        drawdown_curve = [
            {"date": eq_df.iloc[i]["date"], "drawdown": drawdown[i]}
            for i in range(len(drawdown))
        ]

        return BacktestResult(
            total_return=round(total_return, 4),
            annual_return=round(annual_return, 4),
            sharpe_ratio=round(sharpe, 4),
            max_drawdown=round(max_drawdown, 4),
            calmar_ratio=round(calmar, 4),
            win_rate=round(win_rate, 4),
            profit_loss_ratio=round(profit_loss_ratio, 4),
            daily_returns=ret_df.to_dict("records"),
            equity_curve=eq_df.to_dict("records"),
            drawdown_curve=drawdown_curve,
            trades=trades,
        )


# 全局单例
backtest_engine = BacktestEngine()
