"""tqsdk 数据服务 - 获取期货行情数据

tqsdk 内部管理自己的 asyncio 事件循环，与 uvicorn 的事件循环冲突。
解决方案：将所有 tqsdk 操作放在独立线程中运行，通过 run_in_executor 桥接。
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import numpy as np
from tqsdk import TqApi, TqAuth, TqSim

from app.config import TQ_USER, TQ_PASSWORD, DATA_DIR


# 主力合约映射（常见品种）
DOMINANT_CONTRACTS = {
    "SHFE": ["cu", "al", "zn", "pb", "ni", "sn", "au", "ag", "rb", "wr", "hc", "ss", "bu", "ru", "nr", "sp", "fu", "lu", "bc"],
    "DCE": ["c", "cs", "a", "b", "m", "y", "p", "fb", "bb", "jd", "rr", "l", "v", "pp", "j", "jm", "i", "eg", "eb", "pg"],
    "CZCE": ["WH", "PM", "RI", "RS", "JR", "LR", "SR", "CF", "CY", "AP", "CJ", "TA", "OI", "MA", "FG", "SF", "SM", "SA", "UR", "PF"],
    "CFFEX": ["IF", "IH", "IC", "IM", "TF", "T", "TS", "TL"],
    "INE": ["sc", "lu", "nr", "bc"],
    "GFEX": ["si", "lc"],
}


class DataService:
    """tqsdk 数据服务（线程隔离）"""

    def __init__(self):
        self._api: Optional[TqApi] = None
        self._data_dir = Path(DATA_DIR)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        # 独立线程池，tqsdk 在此线程中运行，避免事件循环冲突
        self._executor = ThreadPoolExecutor(max_workers=1)

    def _get_api(self) -> TqApi:
        """获取或创建 TqApi 实例（在线程池中调用）"""
        if self._api is None:
            auth = TqAuth(TQ_USER, TQ_PASSWORD) if TQ_USER else TqAuth()  # type: ignore[call-arg]
            sim = TqSim()
            self._api = TqApi(sim, auth=auth)
        return self._api

    def close(self):
        """关闭连接"""
        if self._api is not None:
            self._api.close()
            self._api = None

    def _run_sync(self, func, *args, **kwargs):
        """在线程池中运行同步函数"""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(self._executor, func, *args, **kwargs)

    # ---- 同步实现（在线程池中执行） ----

    def _sync_get_dominant_contracts(self, exchange: Optional[str] = None) -> list[str]:
        """同步：获取主力合约列表"""
        api = self._get_api()
        contracts: list[str] = []
        exchanges = [exchange] if exchange else DOMINANT_CONTRACTS.keys()

        for ex in exchanges:
            if ex in DOMINANT_CONTRACTS:
                for product in DOMINANT_CONTRACTS[ex]:
                    symbol = f"KQ.m@{ex}.{product}"
                    try:
                        quote = api.get_quote(symbol)
                        api.wait_update()
                        underlying = quote.underlying_symbol  # type: ignore[union-attr]
                        if underlying:
                            contracts.append(str(underlying))
                    except Exception:
                        continue
        return contracts

    def _sync_get_kline(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        freq: str = "daily",
    ) -> pd.DataFrame:
        """同步：获取K线数据"""
        api = self._get_api()

        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        days = (end_dt - start_dt).days + 1

        if freq == "daily":
            data_length = days + 10
            kline = api.get_kline_serial(symbol, 86400, data_length=data_length)
        elif freq == "hourly":
            data_length = days * 7
            kline = api.get_kline_serial(symbol, 3600, data_length=data_length)
        else:
            data_length = days * 240
            kline = api.get_kline_serial(symbol, 60, data_length=data_length)

        api.wait_update()

        df = kline.to_dataframe()
        df = df[df["datetime"] > 0].copy()
        df["datetime"] = pd.to_datetime(df["datetime"], unit="ns")
        df = df[(df["datetime"] >= start_dt) & (df["datetime"] <= end_dt + timedelta(days=1))]
        df = df.rename(columns={
            "datetime": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
            "amount": "amount",
            "open_oi": "open_interest",
            "close_oi": "close_interest",
        })
        return df

    def _sync_get_quote(self, symbol: str) -> dict:
        """同步：获取实时行情"""
        api = self._get_api()
        quote = api.get_quote(symbol)
        api.wait_update()
        return {
            "symbol": symbol,
            "last_price": float(quote.last_price),  # type: ignore[union-attr]
            "ask_price": float(quote.ask_price1),  # type: ignore[union-attr]
            "bid_price": float(quote.bid_price1),  # type: ignore[union-attr]
            "ask_volume": float(quote.ask_vol1),  # type: ignore[union-attr]
            "bid_volume": float(quote.bid_vol1),  # type: ignore[union-attr]
            "volume": float(quote.volume),  # type: ignore[union-attr]
            "open_interest": float(quote.open_interest),  # type: ignore[union-attr]
            "highest": float(quote.highest),  # type: ignore[union-attr]
            "lowest": float(quote.lowest),  # type: ignore[union-attr]
            "open": float(quote.open),  # type: ignore[union-attr]
            "pre_close": float(quote.pre_close),  # type: ignore[union-attr]
            "pre_settlement": float(quote.pre_settlement),  # type: ignore[union-attr]
            "settlement": float(quote.settlement),  # type: ignore[union-attr]
            "upper_limit": float(quote.upper_limit),  # type: ignore[union-attr]
            "lower_limit": float(quote.lower_limit),  # type: ignore[union-attr]
            "datetime": str(quote.datetime),  # type: ignore[union-attr]
        }

    def _sync_get_multiple_klines(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
        freq: str = "daily",
    ) -> dict[str, pd.DataFrame]:
        """同步：批量获取多合约K线"""
        result: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            try:
                df = self._sync_get_kline(symbol, start_date, end_date, freq)
                if not df.empty:
                    result[symbol] = df
            except Exception as e:
                print(f"获取 {symbol} K线失败: {e}")
        return result

    # ---- 异步接口（供 FastAPI 调用，桥接到线程池） ----

    async def get_dominant_contracts(self, exchange: Optional[str] = None) -> list[str]:
        """获取主力合约列表"""
        return await self._run_sync(self._sync_get_dominant_contracts, exchange)

    async def get_kline(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        freq: str = "daily",
    ) -> pd.DataFrame:
        """获取K线数据"""
        return await self._run_sync(self._sync_get_kline, symbol, start_date, end_date, freq)

    async def get_quote(self, symbol: str) -> dict:
        """获取实时行情"""
        return await self._run_sync(self._sync_get_quote, symbol)

    async def get_multiple_klines(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
        freq: str = "daily",
    ) -> dict[str, pd.DataFrame]:
        """批量获取多合约K线"""
        return await self._run_sync(self._sync_get_multiple_klines, symbols, start_date, end_date, freq)

    # ---- 本地存储 ----

    def save_kline(self, df: pd.DataFrame, symbol: str):
        """保存K线到本地Parquet"""
        path = self._data_dir / f"{symbol.replace('.', '_')}.parquet"
        df.to_parquet(path, index=False)

    def load_kline(self, symbol: str) -> Optional[pd.DataFrame]:
        """从本地加载K线"""
        path = self._data_dir / f"{symbol.replace('.', '_')}.parquet"
        if path.exists():
            return pd.read_parquet(path)
        return None


# 全局单例
data_service = DataService()
