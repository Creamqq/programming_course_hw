"""配置模块"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# tqsdk 配置
TQ_USER = os.getenv("TQ_USER", "")
TQ_PASSWORD = os.getenv("TQ_PASSWORD", "")

# 数据存储
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "quant.db"))
DATA_DIR = os.getenv("DATA_DIR", str(BASE_DIR / "data" / "parquet"))

# 回测默认参数
DEFAULT_COMMISSION_RATE = 0.0001  # 手续费率
DEFAULT_SLIPPAGE = 1  # 滑点(跳)
DEFAULT_INITIAL_CAPITAL = 1_000_000  # 初始资金

# 服务器配置
API_HOST = "0.0.0.0"
API_PORT = 8000
CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
