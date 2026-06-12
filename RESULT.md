# 截面多空期货交易系统

## 项目概述

本系统是一个基于**截面因子**的期货多空交易系统，通过计算多个期货合约的截面因子值，对合约进行排名，做多因子值最高的合约、做空因子值最低的合约，构建市场中性的多空组合。

系统采用 **FastAPI + Vue3** 前后端分离架构，行情数据通过 **天勤量化 (tqsdk)** 获取，支持实时行情、因子计算、组合构建、策略回测和模拟交易。

---

## 系统架构

```
┌─────────────────────────────────────────────────────┐
│                    前端 (Vue3)                       │
│  MarketView │ FactorView │ PortfolioView │ BacktestView │ TradeView │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP / WebSocket
┌──────────────────────┴──────────────────────────────┐
│                 后端 (FastAPI)                        │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌────────┐ │
│  │ market   │ │ factor   │ │ portfolio  │ │backtest│ │
│  │   API    │ │   API    │ │    API     │ │  API   │ │
│  └────┬─────┘ └────┬─────┘ └─────┬─────┘ └───┬────┘ │
│       │            │             │            │       │
│  ┌────┴────────────┴─────────────┴────────────┴────┐ │
│  │              DataService (tqsdk)                 │ │
│  │         本地缓存 (JSON + Parquet)                │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## 核心模块

### 1. 数据服务 (`DataService`)

负责与 tqsdk 交互，获取期货行情数据，并提供本地缓存机制。

**数据缓存策略：**

| 数据类型 | 存储格式 | 更新策略 |
|---------|---------|---------|
| 合约列表 | JSON 文件 | 后台自动检查：跨日或超过1小时则刷新 |
| K线数据 | Parquet 文件 | 增量更新：只获取缓存之后的新数据 |
| 实时行情 | 不缓存 | 每次从 tqsdk 获取 |

**关键特性：**
- 线程隔离：tqsdk 操作在独立线程池中运行，避免与 uvicorn 事件循环冲突
- 增量更新：K线数据只获取缺失部分，合并到本地缓存
- 降级容错：tqsdk 调用失败时返回本地缓存数据
- 只返回未下市合约：`expired=False` 过滤已到期合约

### 2. 因子引擎 (`FactorEngine`)

计算截面因子值，支持以下 6 个因子：

| 因子名称 | 说明 | 计算方式 |
|---------|------|---------|
| `momentum` | 动量因子 | 过去N日收益率 |
| `volatility` | 波动率因子 | 过去N日收益率标准差 |
| `volume_ratio` | 成交量比因子 | 当日成交量 / 过去N日平均成交量 |
| `open_interest_change` | 持仓变化因子 | 持仓量N日变化率 |
| `price_oi_divergence` | 量价背离因子 | 价格变化与持仓量变化的滚动相关性 |
| `high_low_range` | 振幅因子 | 过去N日(最高价-最低价)/均价 |

**因子预处理流程：**
1. **去极值**：MAD 法，3 倍中位数绝对偏差截断
2. **标准化**：Z-score 标准化
3. **排名**：按因子值降序排名

### 3. 组合构建 (`PortfolioBuilder`)

根据因子排名构建多空组合：

- **做多**：因子排名前 N% 的合约
- **做空**：因子排名后 N% 的合约
- **权重方式**：
  - `equal`：等权分配
  - `factor`：按因子强度加权

**换仓逻辑**：对比当前持仓与目标持仓，生成开仓/平仓/调仓指令。

### 4. 回测引擎 (`BacktestEngine`)

截面多空策略回测，支持日频/周频/月频调仓。

**回测流程：**
1. 对齐所有合约的交易日
2. 按调仓频率确定调仓日
3. 逐日遍历：
   - 计算当日持仓盈亏
   - 调仓日重新计算截面因子，生成新持仓
4. 计算绩效指标

**绩效指标：**
- 总收益率、年化收益率
- 夏普比率 (Sharpe Ratio)
- 最大回撤 (Max Drawdown)
- Calmar 比率
- 胜率、盈亏比

### 5. 交易服务 (`TradeService`)

通过 tqsdk 执行交易信号，支持开多/开空/平多/平空。

---

## API 接口

### 市场数据

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/market/contracts` | 获取未下市合约列表 |
| GET | `/api/market/kline/{symbol}` | 获取K线数据 |
| GET | `/api/market/quote/{symbol}` | 获取实时行情 |
| GET | `/api/market/batch-kline` | 批量获取K线 |
| GET | `/api/market/cache/stats` | 缓存统计 |
| POST | `/api/market/cache/prefetch` | 预下载K线 |

### 因子分析

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/factor/list` | 获取因子列表 |
| POST | `/api/factor/compute` | 计算截面因子 |

### 组合构建

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/portfolio/build` | 构建多空组合 |

### 回测

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/backtest/run` | 运行回测 |
| GET | `/api/backtest/presets` | 获取预设策略 |

### 交易

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/trade/start` | 启动交易 |
| POST | `/api/trade/stop` | 停止交易 |
| GET | `/api/trade/positions` | 获取持仓 |
| POST | `/api/trade/close-all` | 平掉所有持仓 |

### WebSocket

| 路径 | 说明 |
|------|------|
| `/ws/quote` | 实时行情推送 |

---

## 前端页面

| 页面 | 功能 |
|------|------|
| **行情总览** | 合约列表、K线图表、实时行情 |
| **因子分析** | 选择合约和因子，查看截面因子排名 |
| **组合构建** | 根据因子排名生成多空组合和权重 |
| **策略回测** | 配置参数运行回测，查看净值曲线和绩效指标 |
| **模拟交易** | 启动/停止交易，查看持仓 |

---

## 技术栈

**后端：**
- Python 3.14 + FastAPI
- tqsdk（天勤量化 SDK）
- pandas + numpy（数据处理）
- Uvicorn（ASGI 服务器）

**前端：**
- Vue 3 + TypeScript
- Element Plus（UI 组件库）
- ECharts（图表可视化）
- Pinia（状态管理）
- Axios（HTTP 客户端）

---

## 快速启动

### 后端

```bash
cd backend
pip install -r requirements.txt

# 配置天勤账号（可选，不配置则使用免费版）
cp .env.example .env
# 编辑 .env 填入 TQ_USER 和 TQ_PASSWORD

uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173 即可使用。

---

## 项目目录结构

```
├── backend/
│   ├── app/
│   │   ├── api/              # API 路由
│   │   │   ├── market.py     # 市场数据接口
│   │   │   ├── factor.py     # 因子分析接口
│   │   │   ├── portfolio.py  # 组合构建接口
│   │   │   ├── backtest.py   # 回测接口
│   │   │   └── trade.py      # 交易接口
│   │   ├── services/         # 业务逻辑
│   │   │   ├── data_service.py    # 数据服务（tqsdk + 缓存）
│   │   │   ├── factor_engine.py   # 因子计算引擎
│   │   │   ├── portfolio_builder.py # 组合构建
│   │   │   ├── backtest_engine.py  # 回测引擎
│   │   │   └── trade_service.py    # 交易服务
│   │   ├── models/
│   │   │   └── schemas.py    # Pydantic 数据模型
│   │   ├── config.py         # 配置
│   │   └── main.py           # 入口
│   ├── data/                 # 本地缓存数据
│   │   ├── contracts.json    # 合约列表缓存
│   │   └── kline/            # K线 Parquet 缓存
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/              # API 调用
│   │   ├── views/            # 页面组件
│   │   ├── stores/           # Pinia 状态管理
│   │   ├── router/           # 路由
│   │   └── types/            # TypeScript 类型
│   └── package.json
└── RESULT.md
```
