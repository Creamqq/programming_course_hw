from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from datetime import datetime
from tqsdk import TqApi, TqAuth
import os
import base64
from io import BytesIO
import asyncio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    username: str
    password: str

class QueryRequest(BaseModel):
    username: str
    password: str
    contract_input: str
    num_months: int = 12

def parse_contract_prefix(contract: str) -> str:
    parts = contract.split('.')
    if len(parts) >= 2:
        exchange = parts[0]
        code = parts[1]
        if len(code) >= 4:
            product_code = ''
            for char in code:
                if char.isalpha():
                    product_code += char
                else:
                    break
            return f"{exchange}.{product_code}"
    return contract

def parse_contract_year_month(contract: str) -> Optional[Tuple[int, int]]:
    code = contract.split('.')[-1]
    if len(code) >= 4:
        year = 2000 + int(code[2:4])
        month = int(code[4:6])
        return (year, month)
    return None

def get_contract_month(contract: str) -> Tuple[int, int]:
    code = contract.split('.')[-1]
    year = 2000 + int(code[2:4])
    month = int(code[4:6])
    return (year, month)

def generate_chart(df: pd.DataFrame) -> str:
    plt.figure(figsize=(10, 6))
    plt.plot(df["contract"], df["price"], marker='o', linestyle='-', color='b', linewidth=2, markersize=8)
    plt.xticks(rotation=45)
    plt.xlabel("合约", fontsize=12)
    plt.ylabel("收盘价", fontsize=12)
    plt.title("期货期限结构", fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    plt.close()
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')

@app.get("/")
async def read_root():
    return {"message": "期货期限结构分析 API"}

@app.post("/api/login")
async def login(request: LoginRequest):
    def _login():
        api = TqApi(auth=TqAuth(request.username, request.password))
        api.close()
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _login)
        return {"success": True, "message": "登录成功"}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"登录失败: {str(e)}")

@app.post("/api/query")
async def query_data(request: QueryRequest):
    def _query():
        print(f"收到查询请求: username={request.username}, contract={request.contract_input}, months={request.num_months}")
        
        api = TqApi(auth=TqAuth(request.username, request.password))
        
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        
        contract_list = []
        contract_prefix = parse_contract_prefix(request.contract_input)
        print(f"提取的品种前缀: {contract_prefix}")
        
        year_month = parse_contract_year_month(request.contract_input)
        if year_month:
            base_year = year_month[0]
            base_month = year_month[1]
            print(f"从用户输入的合约年月开始: {base_year}-{base_month}")
        else:
            base_year = current_year
            base_month = current_month
            print(f"用户输入的合约无年月信息，使用当前月份: {base_year}-{base_month}")
        
        for i in range(1, request.num_months + 1):
            total_month = base_month + i - 1
            year = base_year + total_month // 12
            month = total_month % 12 + 1
            contract = f"{contract_prefix}{year % 100}{month:02d}"
            contract_list.append(contract)
            print(f"生成合约: {contract}")
        
        prices = {}
        for contract in contract_list:
            try:
                print(f"正在获取 {contract} 的数据...")
                klines = api.get_kline_serial(contract, duration_seconds=24*60*60, data_length=1)
                if len(klines) > 0:
                    close = klines.iloc[-1]["close"]
                    prices[contract] = close
                    print(f"获取 {contract} 收盘价: {close}")
                else:
                    print(f"合约 {contract} 无数据")
            except Exception as e:
                print(f"获取 {contract} 失败: {e}")
                continue
        
        api.close()
        return prices
    
    try:
        loop = asyncio.get_event_loop()
        prices = await loop.run_in_executor(None, _query)
        
        print(f"总共获取到 {len(prices)} 个合约的价格数据")
        
        if not prices:
            raise HTTPException(status_code=404, detail="未获取到价格数据，请检查合约代码是否正确")
        
        df = pd.DataFrame(list(prices.items()), columns=["contract", "price"])
        
        df["month_num"] = df["contract"].apply(lambda x: get_contract_month(x)[0] + (get_contract_month(x)[1] - 1) / 12)
        df = df.sort_values("month_num").reset_index(drop=True)
        
        chart_base64 = generate_chart(df)
        
        near_price = df.iloc[0]["price"]
        far_price = df.iloc[-1]["price"]
        
        prices_array = np.array(df["price"].tolist())
        price_range = float(np.max(prices_array) - np.min(prices_array))
        price_mean = float(np.mean(prices_array))
        price_cv = float(np.std(prices_array) / price_mean) if price_mean != 0 else 0
        
        price_diff_pct = float((far_price - near_price) / near_price * 100) if near_price != 0 else 0
        
        if price_cv < 0.02:
            structure = "平坦 (Flat)"
            strategy = "平坦市场中，各月份价格相差不大，表示市场对未来供需预期稳定。建议关注基本面变化，等待价差扩大后再进行套利操作。"
        elif far_price > near_price and price_diff_pct > 1:
            structure = "升水 (Contango)"
            strategy = "升水市场中，远月价格高于近月，可考虑卖出远月、买入近月的跨期套利，做空价差，预期价差在未来回归。"
        elif far_price < near_price and price_diff_pct > 1:
            structure = "贴水 (Backwardation)"
            strategy = "贴水市场中，近月价格高于远月，可考虑买入远月、卖出近月的跨期套利，做多价差，预期价差在未来回归。"
        elif far_price > near_price:
            structure = "轻微升水 (Mild Contango)"
            strategy = "市场呈现轻微升水，价差较小。可考虑小仓位进行跨期套利，或结合现货库存进行套保操作。"
        else:
            structure = "轻微贴水 (Mild Backwardation)"
            strategy = "市场呈现轻微贴水，价差较小。建议关注供需变化，等待更明显的趋势信号后再操作。"
        
        return {
            "success": True,
            "data": df.to_dict(orient="records"),
            "chart": chart_base64,
            "structure": structure,
            "strategy": strategy,
            "near_price": near_price,
            "far_price": far_price,
            "price_range": round(price_range, 2),
            "price_cv": round(price_cv * 100, 2),
            "price_diff_pct": round(price_diff_pct, 2)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"发生错误: {e}")
        raise HTTPException(status_code=500, detail=f"数据获取失败: {str(e)}")

@app.get("/{path:path}")
async def serve_frontend(path: str):
    index_file = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"error": "File not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
