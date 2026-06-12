"""市场数据 API"""
import logging

from fastapi import APIRouter, Query
from typing import Optional

from app.services.data_service import data_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["市场数据"])


@router.get("/contracts")
async def get_contracts(
    exchange: Optional[str] = None,
    force_refresh: bool = Query(False, description="强制从 tqsdk 刷新"),
):
    """获取合约列表（优先本地缓存，后台自动检查更新）
    
    缓存策略：
    - 首次访问：从 tqsdk 获取并保存到本地 JSON 文件
    - 后续访问：从本地缓存读取，同时后台检查是否需要更新
    - 自动更新：如果缓存超过 1 小时或跨日，后台自动刷新
    - 强制刷新：设置 force_refresh=true 立即从 tqsdk 刷新
    """
    logger.info("API: 获取合约列表，exchange=%s, force_refresh=%s", exchange, force_refresh)
    try:
        contracts = await data_service.get_contracts(exchange, force_refresh=force_refresh)
        logger.info("API: 返回 %d 个未下市合约", len(contracts))
        return {"contracts": contracts, "count": len(contracts)}
    except Exception as e:
        logger.error("API: 获取合约列表失败：%s", e, exc_info=True)
        return {"contracts": [], "count": 0, "error": str(e)}


@router.get("/kline/{symbol}")
async def get_kline(
    symbol: str,
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    freq: str = Query("daily", description="K线周期: daily/hourly/minute"),
    force_refresh: bool = Query(False, description="强制从 tqsdk 刷新"),
):
    """获取K线数据（优先本地缓存，增量更新）"""
    df = await data_service.get_kline(symbol, start_date, end_date, freq, force_refresh=force_refresh)
    return {
        "symbol": symbol,
        "data": df.to_dict("records"),
        "count": len(df),
    }


@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """获取实时行情"""
    quote = await data_service.get_quote(symbol)
    return quote


@router.get("/batch-kline")
async def get_batch_kline(
    symbols: str = Query(..., description="合约列表，逗号分隔"),
    start_date: str = Query(...),
    end_date: str = Query(...),
    freq: str = Query("daily"),
):
    """批量获取K线"""
    symbol_list = [s.strip() for s in symbols.split(",")]
    result = await data_service.get_multiple_klines(symbol_list, start_date, end_date, freq)
    return {
        "data": {k: v.to_dict("records") for k, v in result.items()},
        "symbols": list(result.keys()),
        "count": len(result),
    }


@router.get("/cache/stats")
async def get_cache_stats():
    """获取本地缓存统计信息"""
    return await data_service.get_cache_stats()


@router.post("/cache/prefetch")
async def prefetch_kline(
    exchange: Optional[str] = None,
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    freq: str = Query("daily", description="K线周期"),
    limit: int = Query(20, description="最多下载合约数"),
):
    """批量预下载K线数据到本地缓存"""
    logger.info("API: 预下载K线, exchange=%s, %s ~ %s, limit=%d", exchange, start_date, end_date, limit)
    try:
        # 获取合约列表
        contracts = await data_service.get_contracts(exchange)
        # 取前 limit 个合约
        symbols = contracts[:limit]
        # 批量获取K线（会自动缓存）
        result = await data_service.get_multiple_klines(symbols, start_date, end_date, freq)
        return {
            "total_contracts": len(contracts),
            "requested": len(symbols),
            "success": len(result),
            "failed": len(symbols) - len(result),
            "symbols": list(result.keys()),
        }
    except Exception as e:
        logger.error("API: 预下载失败: %s", e, exc_info=True)
        return {"error": str(e)}
