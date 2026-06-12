"""tqsdk 数据服务 - 获取期货行情数据

数据缓存策略：
- 合约列表：JSON 文件，自动检查更新（跨日或超过1小时）
- K线数据：Parquet 文件，按合约+频率存储，增量更新（只追加新数据）
- 实时行情：不缓存，每次从 tqsdk 获取

tqsdk 内部管理自己的 asyncio 事件循环，与 uvicorn 的事件循环冲突。
解决方案：将所有 tqsdk 操作放在独立线程中运行，通过 run_in_executor 桥接。
"""
import asyncio
import functools
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from tqsdk import TqApi, TqAuth, TqSim

from app.config import TQ_USER, TQ_PASSWORD, DATA_DIR

logger = logging.getLogger(__name__)

# 支持的交易所
EXCHANGES = ["SHFE", "DCE", "CZCE", "CFFEX", "INE", "GFEX"]


class DataService:
    """tqsdk 数据服务（线程隔离 + 本地缓存）"""

    def __init__(self):
        self._api: Optional[TqApi] = None
        self._data_dir = Path(DATA_DIR)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        # 缓存子目录
        self._kline_dir = self._data_dir / "kline"
        self._kline_dir.mkdir(parents=True, exist_ok=True)
        self._contracts_file = self._data_dir / "contracts.json"
        # 合约列表最后检查时间
        self._contracts_last_check: Optional[datetime] = None
        # 独立线程池，tqsdk 在此线程中运行，避免事件循环冲突
        self._executor = ThreadPoolExecutor(max_workers=1)

    def _get_api(self) -> TqApi:
        """获取或创建 TqApi 实例（在线程池中调用）"""
        if self._api is None:
            logger.info("正在初始化 TqApi, user=%s", TQ_USER or "(匿名)")
            auth = TqAuth(TQ_USER, TQ_PASSWORD) if TQ_USER else TqAuth()  # type: ignore[call-arg]
            sim = TqSim()
            self._api = TqApi(sim, auth=auth)
            logger.info("TqApi 初始化完成")
        return self._api

    def close(self):
        """关闭连接"""
        if self._api is not None:
            logger.info("关闭 TqApi 连接")
            self._api.close()
            self._api = None

    async def _run_sync(self, func, *args, **kwargs):
        """在线程池中运行同步函数，使用 functools.partial 传递参数"""
        loop = asyncio.get_running_loop()
        partial_func = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(self._executor, partial_func)

    # ---- 本地缓存 ----

    def _load_contracts_from_file(self) -> Optional[list[str]]:
        """从本地 JSON 文件加载合约列表"""
        if self._contracts_file.exists():
            try:
                data = json.loads(self._contracts_file.read_text(encoding="utf-8"))
                contracts = data.get("contracts", [])
                saved_at = data.get("saved_at", "unknown")
                logger.info("从本地加载合约列表: %d 个, 保存时间: %s", len(contracts), saved_at)
                return contracts
            except Exception as e:
                logger.warning("读取合约缓存失败: %s", e)
        return None

    def _save_contracts_to_file(self, contracts: list[str]):
        """保存合约列表到本地 JSON 文件"""
        data = {
            "contracts": contracts,
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "count": len(contracts),
        }
        self._contracts_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("合约列表已保存到本地：%d 个", len(contracts))

    def _load_contracts_metadata(self) -> dict:
        """从本地文件加载合约元数据（包括保存时间、数量等）"""
        if self._contracts_file.exists():
            try:
                data = json.loads(self._contracts_file.read_text(encoding="utf-8"))
                return {
                    "contracts": data.get("contracts", []),
                    "saved_at": data.get("saved_at", ""),
                    "count": data.get("count", 0),
                }
            except Exception as e:
                logger.warning("读取合约元数据失败：%s", e)
        return {}

    def _should_refresh_contracts(self) -> bool:
        """检查是否需要刷新合约列表
        
        检查策略：
        1. 如果本地没有缓存，需要刷新
        2. 如果距离上次检查超过 1 小时，需要刷新
        3. 如果是新的一天（跨日），需要刷新
        """
        # 1. 检查本地缓存是否存在
        if not self._contracts_file.exists():
            logger.info("合约缓存文件不存在，需要刷新")
            return True
        
        # 2. 检查距离上次检查的时间
        now = datetime.now()
        if self._contracts_last_check is not None:
            time_diff = now - self._contracts_last_check
            if time_diff < timedelta(hours=1):
                logger.info("距离上次检查仅 %d 分钟，跳过刷新", int(time_diff.total_seconds() / 60))
                return False
        
        # 3. 检查是否跨日
        metadata = self._load_contracts_metadata()
        saved_at_str = metadata.get("saved_at", "")
        if saved_at_str:
            try:
                saved_date = datetime.strptime(saved_at_str, "%Y-%m-%d %H:%M:%S").date()
                if saved_date < now.date():
                    logger.info("合约缓存已过期（保存日期：%s），需要刷新", saved_at_str)
                    return True
            except Exception as e:
                logger.warning("解析保存时间失败：%s", e)
                return True
        
        logger.info("合约缓存有效，无需刷新")
        return False

    def _kline_cache_path(self, symbol: str, freq: str) -> Path:
        """K线缓存文件路径"""
        return self._kline_dir / f"{symbol.replace('.', '_')}_{freq}.parquet"

    def _load_kline_from_file(self, symbol: str, freq: str) -> Optional[pd.DataFrame]:
        """从本地 Parquet 文件加载K线"""
        path = self._kline_cache_path(symbol, freq)
        if path.exists():
            try:
                df = pd.read_parquet(path)
                if not df.empty:
                    logger.info("从本地加载K线: %s (%s), %d 条, 日期范围: %s ~ %s",
                                symbol, freq, len(df),
                                str(df["date"].min())[:10], str(df["date"].max())[:10])
                    return df
            except Exception as e:
                logger.warning("读取K线缓存失败 %s: %s", symbol, e)
        return None

    def _save_kline_to_file(self, df: pd.DataFrame, symbol: str, freq: str):
        """保存K线到本地 Parquet 文件（增量合并）"""
        path = self._kline_cache_path(symbol, freq)
        if path.exists() and not df.empty:
            try:
                existing = pd.read_parquet(path)
                if not existing.empty:
                    # 合并：新数据覆盖同日期的旧数据
                    df["date"] = pd.to_datetime(df["date"])
                    existing["date"] = pd.to_datetime(existing["date"])
                    merged = pd.concat([existing, df]).drop_duplicates(subset=["date"], keep="last").sort_values("date")
                    merged.to_parquet(path, index=False)
                    logger.info("K线增量保存: %s (%s), 原有 %d + 新增 %d -> 合并 %d 条",
                                symbol, freq, len(existing), len(df), len(merged))
                    return
            except Exception as e:
                logger.warning("增量合并失败，覆盖保存 %s: %s", symbol, e)

        # 首次保存或合并失败时直接写入
        if not df.empty:
            df.to_parquet(path, index=False)
            logger.info("K线保存: %s (%s), %d 条", symbol, freq, len(df))

    # ---- 同步实现（在线程池中执行） ----

    def _sync_get_contracts(self, exchange: Optional[str] = None, force_refresh: bool = False) -> list[str]:
        """同步：获取合约列表（只返回未下市的合约，自动检查更新）"""
        # 1. 尝试从本地文件读取并检查是否需要后台更新
        if not force_refresh:
            cached = self._load_contracts_from_file()
            if cached:
                # 检查是否需要后台更新
                if self._should_refresh_contracts():
                    logger.info("后台自动刷新合约列表...")
                    self._executor.submit(self._refresh_contracts_background)
                if exchange:
                    return [c for c in cached if c.startswith(f"{exchange}.")]
                return cached

        # 2. 从 tqsdk 获取未下市的合约
        logger.info("从 tqsdk 获取未下市的合约列表, exchange=%s", exchange)
        api = self._get_api()
        try:
            logger.info("调用 query_quotes (expired=False)...")
            if exchange:
                symbols = api.query_quotes(ins_class="FUTURE", exchange_id=exchange, expired=False)
            else:
                symbols = api.query_quotes(ins_class="FUTURE", expired=False)
            logger.info("query_quotes 返回完成")
        except Exception as e:
            logger.error("query_quotes 调用失败: %s", e, exc_info=True)
            # 降级：返回本地缓存（如果有）
            cached = self._load_contracts_from_file()
            if cached:
                logger.info("降级使用本地缓存: %d 个", len(cached))
                return cached
            return []

        contracts = list(symbols) if symbols else []
        logger.info("未下市合约列表获取完成：共 %d 个合约", len(contracts))

        if len(contracts) == 0:
            logger.warning("合约列表为空，可能是 tqsdk 连接未就绪或认证失败")

        # 保存到本地文件
        self._save_contracts_to_file(contracts)
        self._contracts_last_check = datetime.now()

        # 按交易所分组统计
        exchange_stats: dict[str, int] = {}
        for s in contracts:
            ex = s.split(".")[0] if "." in s else "UNKNOWN"
            exchange_stats[ex] = exchange_stats.get(ex, 0) + 1
        for ex, count in sorted(exchange_stats.items()):
            logger.info("  %s: %d 个未下市合约", ex, count)

        if exchange:
            return [c for c in contracts if c.startswith(f"{exchange}.")]
        return contracts

    def _refresh_contracts_background(self):
        """后台刷新合约列表（不阻塞主线程）"""
        try:
            logger.info("后台刷新合约列表开始...")
            api = self._get_api()
            symbols = api.query_quotes(ins_class="FUTURE", expired=False)
            contracts = list(symbols) if symbols else []
            
            if contracts:
                self._save_contracts_to_file(contracts)
                self._contracts_last_check = datetime.now()
                logger.info("后台刷新完成：共 %d 个未下市合约", len(contracts))
            else:
                logger.warning("后台刷新结果为空，保留原缓存")
        except Exception as e:
            logger.error("后台刷新失败：%s", e, exc_info=True)

    def _sync_get_kline(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        freq: str = "daily",
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """同步：获取K线数据（优先本地缓存，增量更新）"""
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        # 1. 尝试从本地缓存读取
        if not force_refresh:
            cached = self._load_kline_from_file(symbol, freq)
            if cached is not None and not cached.empty:
                cached["date"] = pd.to_datetime(cached["date"])
                # 检查缓存是否覆盖了请求的时间范围
                cache_start = cached["date"].min()
                cache_end = cached["date"].max()
                if cache_start <= start_dt and cache_end >= end_dt:
                    # 缓存完全覆盖请求范围，直接返回
                    result = cached[(cached["date"] >= start_dt) & (cached["date"] <= end_dt + timedelta(days=1))].copy()
                    logger.info("K线命中本地缓存: %s (%s), 返回 %d 条", symbol, freq, len(result))
                    return result
                elif cache_end >= end_dt:
                    # 缓存最新数据已够，只是历史数据不够早
                    result = cached[(cached["date"] >= start_dt) & (cached["date"] <= end_dt + timedelta(days=1))].copy()
                    if not result.empty:
                        logger.info("K线部分命中缓存: %s (%s), 返回 %d 条", symbol, freq, len(result))
                        return result

        # 2. 从 tqsdk 获取
        logger.info("从 tqsdk 获取K线: symbol=%s, %s ~ %s, freq=%s", symbol, start_date, end_date, freq)
        api = self._get_api()

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

        # wait_update 带10秒超时，避免非交易时间无限阻塞
        deadline = time.time() + 10
        api.wait_update(deadline=deadline)

        # TqDataFrame 本身就是 DataFrame 子类，直接使用
        df = kline.copy()
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

        # 3. 保存到本地（增量合并）
        if not df.empty:
            self._save_kline_to_file(df, symbol, freq)

        logger.info("K线数据获取完成: %s, %d 条", symbol, len(df))
        return df

    def _sync_get_quote(self, symbol: str) -> dict:
        """同步：获取实时行情（不缓存）"""
        logger.info("获取实时行情: %s", symbol)
        api = self._get_api()
        quote = api.get_quote(symbol)
        deadline = time.time() + 10
        api.wait_update(deadline=deadline)
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
        logger.info("批量获取K线: %d 个合约", len(symbols))
        result: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            try:
                df = self._sync_get_kline(symbol, start_date, end_date, freq)
                if not df.empty:
                    result[symbol] = df
            except Exception as e:
                logger.warning("获取 %s K线失败: %s", symbol, e)
        logger.info("批量K线获取完成: 成功 %d / %d", len(result), len(symbols))
        return result

    def _sync_get_cache_stats(self) -> dict:
        """同步：获取缓存统计信息"""
        contracts_info = {}
        if self._contracts_file.exists():
            try:
                data = json.loads(self._contracts_file.read_text(encoding="utf-8"))
                contracts_info = {
                    "count": data.get("count", 0),
                    "saved_at": data.get("saved_at", ""),
                    "last_check": self._contracts_last_check.strftime("%Y-%m-%d %H:%M:%S") if self._contracts_last_check else None,
                    "need_refresh": self._should_refresh_contracts(),
                }
            except Exception:
                pass

        kline_files = list(self._kline_dir.glob("*.parquet"))
        kline_stats = []
        total_size = 0
        for f in kline_files:
            size = f.stat().st_size
            total_size += size
            kline_stats.append({
                "file": f.name,
                "size_kb": round(size / 1024, 1),
            })

        return {
            "contracts": contracts_info,
            "kline_files": len(kline_files),
            "kline_total_size_mb": round(total_size / 1024 / 1024, 2),
            "kline_details": kline_stats[:20],  # 只显示前 20 个
            "data_dir": str(self._data_dir),
        }

    # ---- 异步接口（供 FastAPI 调用，桥接到线程池） ----

    async def get_contracts(self, exchange: Optional[str] = None, force_refresh: bool = False) -> list[str]:
        """获取合约列表（优先缓存）"""
        return await self._run_sync(self._sync_get_contracts, exchange=exchange, force_refresh=force_refresh)

    async def get_kline(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        freq: str = "daily",
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """获取K线数据（优先缓存，增量更新）"""
        return await self._run_sync(self._sync_get_kline, symbol, start_date, end_date, freq=freq, force_refresh=force_refresh)

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
        return await self._run_sync(self._sync_get_multiple_klines, symbols, start_date, end_date, freq=freq)

    async def get_cache_stats(self) -> dict:
        """获取缓存统计"""
        return await self._run_sync(self._sync_get_cache_stats)


# 全局单例
data_service = DataService()
