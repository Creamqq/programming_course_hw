"""组合管理 API"""
from fastapi import APIRouter, Query
from typing import Optional

from app.services.data_service import data_service
from app.services.portfolio_builder import portfolio_builder

router = APIRouter(prefix="/portfolio", tags=["组合管理"])


@router.post("/build")
async def build_portfolio(
    symbols: str = Query(..., description="合约列表，逗号分隔"),
    factor_name: str = Query("momentum"),
    start_date: str = Query(...),
    end_date: str = Query(...),
    long_ratio: float = Query(0.3),
    short_ratio: float = Query(0.3),
    weight_method: str = Query("equal"),
    window: int = Query(20),
):
    """构建多空组合"""
    symbol_list = [s.strip() for s in symbols.split(",")]
    data_dict = await data_service.get_multiple_klines(symbol_list, start_date, end_date)

    if not data_dict:
        return {"error": "未获取到数据"}

    portfolio = portfolio_builder.build_from_data(
        data_dict, factor_name, long_ratio, short_ratio, weight_method, window=window
    )
    return {
        "portfolio": portfolio.to_dict("records"),
        "long_count": len(portfolio[portfolio["direction"] == "long"]),
        "short_count": len(portfolio[portfolio["direction"] == "short"]),
    }


@router.get("/positions")
async def get_positions():
    """获取当前持仓"""
    from app.services.trade_service import trade_service
    positions = await trade_service.get_positions()
    return {"positions": positions}
