"""因子分析 API"""
import logging

import numpy as np
from fastapi import APIRouter, Query
from typing import Optional

from app.services.data_service import data_service
from app.services.factor_engine import factor_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/factor", tags=["因子分析"])

FACTOR_LIST = [
    {"name": "momentum", "label": "动量因子", "description": "过去N日收益率"},
    {"name": "volatility", "label": "波动率因子", "description": "过去N日收益率标准差"},
    {"name": "volume_ratio", "label": "成交量比因子", "description": "当日成交量/过去N日平均成交量"},
    {"name": "open_interest_change", "label": "持仓变化因子", "description": "持仓量N日变化率"},
    {"name": "price_oi_divergence", "label": "量价背离因子", "description": "价格变化与持仓量变化的相关性"},
    {"name": "high_low_range", "label": "振幅因子", "description": "过去N日振幅"},
]


@router.get("/list")
async def list_factors():
    """获取可用因子列表"""
    return {"factors": FACTOR_LIST}


@router.get("/compute")
async def compute_factor(
    symbols: str = Query(..., description="合约列表，逗号分隔"),
    factor_name: str = Query("momentum"),
    start_date: str = Query(...),
    end_date: str = Query(...),
    window: int = Query(20, description="回看窗口"),
    date: Optional[str] = Query(None, description="指定截面日期，不填取最新"),
):
    """计算截面因子值"""
    symbol_list = [s.strip() for s in symbols.split(",")]
    logger.info("计算截面因子: symbols=%s, factor=%s, %s ~ %s, window=%d", symbol_list, factor_name, start_date, end_date, window)
    data_dict = await data_service.get_multiple_klines(symbol_list, start_date, end_date)

    if not data_dict:
        logger.warning("未获取到任何K线数据！symbols=%s", symbol_list)
        return {"error": "未获取到数据"}

    logger.info("获取到K线数据: %d / %d 个合约", len(data_dict), len(symbol_list))
    for sym, df in data_dict.items():
        logger.info("  %s: %d 条K线", sym, len(df))

    factor_df = factor_engine.compute_cross_section(
        data_dict, factor_name, date=date, preprocess=True, window=window
    )
    return {
        "factor_name": factor_name,
        "data": factor_df.to_dict("records"),
        "count": len(factor_df),
    }


@router.get("/ic")
async def compute_ic(
    symbols: str = Query(...),
    factor_name: str = Query("momentum"),
    start_date: str = Query(...),
    end_date: str = Query(...),
    window: int = Query(20),
    forward_period: int = Query(5, description="前瞻收益期数"),
):
    """计算因子IC（信息系数）"""
    symbol_list = [s.strip() for s in symbols.split(",")]
    data_dict = await data_service.get_multiple_klines(symbol_list, start_date, end_date)

    if not data_dict:
        return {"error": "未获取到数据"}

    # 对齐日期
    all_dates = set()
    for df in data_dict.values():
        dates = set(df["date"].astype(str).str[:10].tolist())
        all_dates = all_dates | dates if not all_dates else all_dates & dates
    sorted_dates = sorted(all_dates)

    ic_series = []
    for d in sorted_dates[window + forward_period:]:
        # 计算因子值
        factor_df = factor_engine.compute_cross_section(
            data_dict, factor_name, date=d, preprocess=False, window=window
        )
        if len(factor_df) < 3:
            continue

        # 计算前瞻收益
        forward_returns = {}
        for symbol, df in data_dict.items():
            if symbol not in factor_df["symbol"].values:
                continue
            date_mask = df["date"].astype(str).str[:10] == d
            if not date_mask.any():
                continue
            idx = df[date_mask].index[0]
            if idx + forward_period < len(df):
                ret = (df.iloc[idx + forward_period]["close"] - df.iloc[idx]["close"]) / df.iloc[idx]["close"]
                forward_returns[symbol] = ret

        # 计算相关系数
        common = factor_df[factor_df["symbol"].isin(forward_returns.keys())]
        if len(common) < 3:
            continue

        factor_vals = np.asarray(common["factor_value"].values, dtype=np.float64)
        ret_vals = np.array([forward_returns[s] for s in common["symbol"]], dtype=np.float64)

        corr = float(np.corrcoef(factor_vals, ret_vals)[0, 1])
        if not np.isnan(corr):
            ic_series.append({"date": d, "ic": corr})

    # 统计
    if ic_series:
        ic_values = [x["ic"] for x in ic_series]
        ic_mean = float(np.mean(ic_values))
        ic_std = float(np.std(ic_values))
        ir = ic_mean / max(ic_std, 1e-8)
        ic_positive_rate = sum(1 for x in ic_values if x > 0) / len(ic_values)
    else:
        ic_mean = ic_std = ir = ic_positive_rate = 0

    return {
        "factor_name": factor_name,
        "ic_series": ic_series,
        "summary": {
            "ic_mean": round(ic_mean, 4),
            "ic_std": round(ic_std, 4),
            "ir": round(ir, 4),
            "ic_positive_rate": round(ic_positive_rate, 4),
        },
    }
