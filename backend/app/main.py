"""FastAPI 主入口"""
import asyncio
import json
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.api import market, factor, portfolio, backtest, trade
from app.services.data_service import data_service

# 日志配置放在导入之后，因为 tqsdk 会在导入时覆盖 root logger 配置
# 必须用 force=True 才能夺回控制权
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
# 抑制 tqsdk 的日志噪音
logging.getLogger("tqsdk").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("截面多空交易系统启动...")
    yield
    logger.info("关闭数据服务...")
    data_service.close()


app = FastAPI(
    title="截面多空交易系统",
    description="基于截面因子的期货多空交易系统 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(market.router, prefix="/api")
app.include_router(factor.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(trade.router, prefix="/api")


# WebSocket 实时行情推送
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


@app.websocket("/ws/quote")
async def websocket_quote(websocket: WebSocket):
    """WebSocket 实时行情推送"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            params = json.loads(data)
            symbol = params.get("symbol", "")
            if symbol:
                try:
                    quote = await data_service.get_quote(symbol)
                    await websocket.send_json(quote)
                except Exception as e:
                    await websocket.send_json({"error": str(e)})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/")
async def root():
    return {"message": "截面多空交易系统 API", "docs": "/docs"}


@app.get("/api/health")
async def health():
    """健康检查"""
    return {"status": "ok", "tq_connected": data_service._api is not None}
