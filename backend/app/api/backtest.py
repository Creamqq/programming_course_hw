"""回测 API"""
from fastapi import APIRouter

from app.models.schemas import BacktestConfig
from app.services.data_service import data_service
from app.services.backtest_engine import backtest_engine

router = APIRouter(prefix="/backtest", tags=["回测"])


@router.post("/run")
async def run_backtest(config: BacktestConfig):
    """运行回测"""
    # 获取数据
    if config.universe:
        symbols = config.universe
    else:
        symbols = await data_service.get_contracts()

    data_dict = await data_service.get_multiple_klines(
        symbols, config.start_date, config.end_date
    )

    if not data_dict:
        return {"error": "未获取到数据，请检查日期范围和合约列表"}

    # 运行回测
    result = backtest_engine.run(data_dict, config)
    return result


@router.get("/presets")
async def get_presets():
    """获取预设回测参数"""
    return {
        "presets": [
            {
                "name": "动量策略-日频",
                "config": {
                    "factor_name": "momentum",
                    "rebalance_freq": "daily",
                    "long_ratio": 0.3,
                    "short_ratio": 0.3,
                    "window": 20,
                },
            },
            {
                "name": "波动率策略-周频",
                "config": {
                    "factor_name": "volatility",
                    "rebalance_freq": "weekly",
                    "long_ratio": 0.3,
                    "short_ratio": 0.3,
                    "window": 20,
                },
            },
            {
                "name": "持仓变化策略-月频",
                "config": {
                    "factor_name": "open_interest_change",
                    "rebalance_freq": "monthly",
                    "long_ratio": 0.2,
                    "short_ratio": 0.2,
                    "window": 5,
                },
            },
        ]
    }
