"""交易服务 - tqsdk 下单与持仓管理"""
from app.services.data_service import data_service
from app.models.schemas import TradeSignal


class TradeService:
    """交易服务"""

    def __init__(self):
        self._positions = {}  # symbol -> {direction, lots, entry_price}
        self._is_trading = False

    @property
    def is_trading(self) -> bool:
        return self._is_trading

    def start_trading(self):
        """启动交易"""
        self._is_trading = True

    def stop_trading(self):
        """停止交易"""
        self._is_trading = False

    async def execute_signal(self, signal: TradeSignal) -> dict:
        """
        执行交易信号
        注意：实盘交易需要tqsdk账号和真实账户
        """
        if not self._is_trading:
            return {"status": "error", "message": "交易未启动"}

        api = data_service._get_api()

        try:
            if signal.direction == "buy":
                # 开多
                order = api.insert_order(
                    symbol=signal.symbol,
                    direction="BUY",
                    offset="OPEN",
                    volume=signal.lots,
                    limit_price=signal.price,
                )
            elif signal.direction == "sell":
                # 开空
                order = api.insert_order(
                    symbol=signal.symbol,
                    direction="SELL",
                    offset="OPEN",
                    volume=signal.lots,
                    limit_price=signal.price,
                )
            elif signal.direction == "close_long":
                # 平多
                order = api.insert_order(
                    symbol=signal.symbol,
                    direction="SELL",
                    offset="CLOSE",
                    volume=signal.lots,
                    limit_price=signal.price,
                )
            elif signal.direction == "close_short":
                # 平空
                order = api.insert_order(
                    symbol=signal.symbol,
                    direction="BUY",
                    offset="CLOSE",
                    volume=signal.lots,
                    limit_price=signal.price,
                )
            else:
                return {"status": "error", "message": f"未知方向: {signal.direction}"}

            # 等待订单更新
            while order.status == "ALIVE":
                api.wait_update()

            # 更新本地持仓记录
            self._update_position(signal)

            return {
                "status": "success",
                "order_id": order.order_id,
                "symbol": signal.symbol,
                "direction": signal.direction,
                "lots": signal.lots,
                "traded_price": float(order.traded_price) if hasattr(order, "traded_price") and order.traded_price > 0 else None,  # type: ignore[union-attr]
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _update_position(self, signal: TradeSignal):
        """更新本地持仓记录"""
        key = signal.symbol
        if signal.direction in ("buy", "sell"):
            direction = "long" if signal.direction == "buy" else "short"
            self._positions[key] = {
                "direction": direction,
                "lots": signal.lots,
                "entry_price": signal.price or 0,
            }
        elif signal.direction in ("close_long", "close_short"):
            self._positions.pop(key, None)

    async def get_positions(self) -> list[dict]:
        """获取当前持仓"""
        return [
            {"symbol": k, **v}
            for k, v in self._positions.items()
        ]

    async def close_all(self) -> list[dict]:
        """平掉所有持仓"""
        results = []
        for symbol, pos in list(self._positions.items()):
            if pos["direction"] == "long":
                direction = "close_long"
            else:
                direction = "close_short"
            signal = TradeSignal(
                symbol=symbol,
                direction=direction,
                lots=pos["lots"],
            )
            result = await self.execute_signal(signal)
            results.append(result)
        return results


# 全局单例
trade_service = TradeService()
