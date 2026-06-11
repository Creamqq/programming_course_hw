"""市场数据 API"""
import logging

from fastapi import APIRouter, Query
from typing import Optional

from app.services.data_service import data_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["市场数据"])


@router.get("/contracts")
async def get_contracts(exchange: Optional[str] = None):
    """获取合约列表"""
    logger.info("API: 获取合约列表, exchange=%s", exchange)
    try:
        contracts = await data_service.get_dominant_contracts(exchange)
        logger.info("API: 返回 %d 个合约", len(contracts))
        return {"contracts": contracts, "count": len(contracts)}
    except Exception as e:
        logger.error("API: 获取合约列表失败: %s", e, exc_info=True)
        return {"contracts": [], "count": 0, "error": str(e)}


@router.get("/kline/{symbol}")
async def get_kline(
    symbol: str,
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    freq: str = Query("daily", description="K线周期: daily/hourly/minute"),
):
    """获取K线数据"""
    df = await data_service.get_kline(symbol, start_date, end_date, freq)
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
