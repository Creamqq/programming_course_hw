"""交易控制 API"""
from fastapi import APIRouter

from app.models.schemas import TradeSignal
from app.services.trade_service import trade_service

router = APIRouter(prefix="/trade", tags=["交易控制"])


@router.post("/start")
async def start_trading():
    """启动交易"""
    trade_service.start_trading()
    return {"status": "trading", "message": "交易已启动"}


@router.post("/stop")
async def stop_trading():
    """停止交易"""
    trade_service.stop_trading()
    return {"status": "stopped", "message": "交易已停止"}


@router.get("/status")
async def get_status():
    """获取交易状态"""
    return {
        "is_trading": trade_service.is_trading,
    }


@router.post("/signal")
async def execute_signal(signal: TradeSignal):
    """执行交易信号"""
    result = await trade_service.execute_signal(signal)
    return result


@router.post("/close-all")
async def close_all():
    """平掉所有持仓"""
    results = await trade_service.close_all()
    return {"results": results}
