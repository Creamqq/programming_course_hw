"""因子引擎 - 截面因子计算"""
import logging

import pandas as pd
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)


class FactorEngine:
    """截面因子计算引擎"""

    @staticmethod
    def momentum(df: pd.DataFrame, window: int = 20) -> pd.Series:
        """
        动量因子：过去N日收益率
        df: 单合约K线，需包含 close 列
        """
        return df["close"].pct_change(window)

    @staticmethod
    def volatility(df: pd.DataFrame, window: int = 20) -> pd.Series:
        """
        波动率因子：过去N日收益率标准差
        """
        returns = df["close"].pct_change()
        return returns.rolling(window).std()

    @staticmethod
    def volume_ratio(df: pd.DataFrame, window: int = 20) -> pd.Series:
        """
        成交量比因子：当日成交量 / 过去N日平均成交量
        """
        avg_vol = df["volume"].rolling(window).mean()
        return df["volume"] / avg_vol

    @staticmethod
    def open_interest_change(df: pd.DataFrame, window: int = 5) -> pd.Series:
        """
        持仓变化因子：持仓量N日变化率
        """
        oi_col = "close_interest" if "close_interest" in df.columns else "open_interest"
        return df[oi_col].pct_change(window)

    @staticmethod
    def price_oi_divergence(df: pd.DataFrame, window: int = 10) -> pd.Series:
        """
        量价背离因子：价格变化与持仓量变化的相关性
        正值表示同向（量价齐升/齐跌），负值表示背离
        """
        price_chg = df["close"].pct_change()
        oi_col = "close_interest" if "close_interest" in df.columns else "open_interest"
        oi_chg = df[oi_col].pct_change()
        corr = price_chg.rolling(window).corr(oi_chg)
        return corr

    @staticmethod
    def high_low_range(df: pd.DataFrame, window: int = 20) -> pd.Series:
        """
        振幅因子：过去N日最高价与最低价的差 / 均价
        """
        highest = df["high"].rolling(window).max()
        lowest = df["low"].rolling(window).min()
        avg = df["close"].rolling(window).mean()
        return (highest - lowest) / avg

    def compute_factor(
        self,
        df: pd.DataFrame,
        factor_name: str,
        **kwargs,
    ) -> pd.Series:
        """根据名称计算因子"""
        factor_map = {
            "momentum": self.momentum,
            "volatility": self.volatility,
            "volume_ratio": self.volume_ratio,
            "open_interest_change": self.open_interest_change,
            "price_oi_divergence": self.price_oi_divergence,
            "high_low_range": self.high_low_range,
        }
        if factor_name not in factor_map:
            raise ValueError(f"未知因子: {factor_name}, 可选: {list(factor_map.keys())}")
        return factor_map[factor_name](df, **kwargs)

    @staticmethod
    def winsorize(series: pd.Series, n_sigma: float = 3.0) -> pd.Series:
        """去极值：MAD法"""
        median = series.median()
        mad = (series - median).abs().median()
        lower = median - n_sigma * 1.4826 * mad
        upper = median + n_sigma * 1.4826 * mad
        return series.clip(lower, upper)

    @staticmethod
    def standardize(series: pd.Series) -> pd.Series:
        """标准化：Z-score"""
        return (series - series.mean()) / series.std()

    @staticmethod
    def neutralize(series: pd.Series, group: pd.Series) -> pd.Series:
        """
        组中性化：减去组内均值
        series: 因子值
        group: 分组标签（如品种、交易所）
        """
        group_mean = series.groupby(group).transform("mean")
        return series - group_mean

    def compute_cross_section(
        self,
        data_dict: dict[str, pd.DataFrame],
        factor_name: str,
        date: Optional[str] = None,
        preprocess: bool = True,
        **factor_kwargs,
    ) -> pd.DataFrame:
        """
        计算截面因子值
        data_dict: {symbol: kline_df}
        返回: DataFrame with columns [symbol, factor_value, rank]
        """
        logger.info("计算截面因子: factor=%s, 合约数=%d, date=%s", factor_name, len(data_dict), date)
        results = []
        nan_count = 0
        for symbol, df in data_dict.items():
            if df.empty:
                logger.debug("  %s: K线数据为空，跳过", symbol)
                continue
            factor_series = self.compute_factor(df, factor_name, **factor_kwargs)
            if date:
                # 取指定日期的因子值
                mask = df["date"].astype(str).str[:10] == date
                if mask.any():
                    idx = df.loc[mask].index[-1]
                    val = factor_series.loc[idx]
                    if not np.isnan(val):
                        results.append({"symbol": symbol, "factor_value": val})
                    else:
                        nan_count += 1
                else:
                    logger.debug("  %s: 指定日期 %s 无数据", symbol, date)
            else:
                # 取最新值
                val = factor_series.iloc[-1]
                if not np.isnan(val):
                    results.append({"symbol": symbol, "factor_value": val})
                else:
                    nan_count += 1

        logger.info("截面因子结果: 有效=%d, NaN=%d, 空数据=%d", len(results), nan_count, len(data_dict) - len(results) - nan_count)

        if not results:
            logger.warning("截面因子计算无有效结果！data_dict keys=%s", list(data_dict.keys()))
            return pd.DataFrame(columns=["symbol", "factor_value", "rank"])

        result_df = pd.DataFrame(results)
        if preprocess:
            result_df["factor_value"] = self.winsorize(result_df["factor_value"])
            result_df["factor_value"] = self.standardize(result_df["factor_value"])
        result_df["rank"] = result_df["factor_value"].rank(ascending=False).astype(int)
        # 丢弃因子值为 NaN 的行，避免 JSON 序列化报错
        result_df = result_df.dropna(subset=["factor_value"])
        return result_df.sort_values("rank")


# 全局单例
factor_engine = FactorEngine()
