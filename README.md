# 期权VIX指数与策略分析系统

基于Python + TqSdk + Vue.js构建的期权分析系统，支持VIX指数计算和多种期权交易策略分析。

## 功能特性

### 1. VIX指数计算
- 支持简化VIX计算方法
- 支持完整CBOE VIX计算方法
- 实时获取原油期权VIX指数

### 2. 期权交易策略
- **双卖（Short Straddle）**: 同时卖出相同执行价的看涨和看跌期权
- **宽跨式双卖（Short Strangle）**: 卖出不同执行价的看涨和看跌期权
- **铁鹰（Iron Condor）**: 限制风险的组合策略
- **日历价差（Calendar Spread）**: 利用时间价值差异获利

### 3. 风险分析
- Greeks计算（Delta, Gamma, Theta, Vega）
- 蒙特卡洛模拟
- VaR（风险价值）计算
- 预期损失（Expected Shortfall）计算
- 盈利概率分析

## 项目结构

```
.
├── vix_calculator.py      # VIX指数计算模块
├── option_strategies.py   # 期权策略构建模块
├── risk_analysis.py       # 风险分析模块
├── tqsdk_option.py        # TqSdk期权交易模块
├── api_server.py          # Flask API服务器
├── requirements.txt       # Python依赖
└── frontend/              # Vue前端
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.js
        ├── App.vue
        ├── api/
        │   └── index.js
        └── components/
            ├── VixCalculator.vue
            ├── StrategyAnalysis.vue
            ├── StrategyCompare.vue
            └── OptionChain.vue
```

## 安装说明

### 后端安装

1. 安装Python依赖：
```bash
pip install -r requirements.txt
```

2. 配置环境变量：
```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑.env文件，填入你的TqSdk账户信息
# TQSDK_ACCOUNT=你的信易账户
# TQSDK_PASSWORD=你的密码
```

3. 启动API服务器：
```bash
python api_server.py
```

服务器将在 `http://localhost:5000` 启动。

### 前端安装

1. 进入前端目录：
```bash
cd frontend
```

2. 安装Node.js依赖：
```bash
npm install
```

3. 启动开发服务器：
```bash
npm run dev
```

前端将在 `http://localhost:3000` 启动。

## API接口文档

### VIX指数相关

#### 计算VIX指数
```
POST /api/vix/calculate
```
请求参数：
```json
{
  "underlying_price": 500.0,
  "options": []
}
```

#### 获取原油VIX
```
GET /api/vix/crude-oil
```

### 策略分析相关

#### 获取策略列表
```
GET /api/strategies/list
```

#### 分析策略
```
POST /api/strategies/analyze
```
请求参数：
```json
{
  "strategy_id": "short_straddle",
  "params": {
    "underlying_price": 500,
    "time_to_expiry": 30,
    "volatility": 0.25,
    "call_premium": 15,
    "put_premium": 12
  }
}
```

#### 策略对比
```
POST /api/strategies/compare
```
请求参数：
```json
{
  "underlying_price": 500,
  "time_to_expiry": 30,
  "volatility": 0.25
}
```

### 期权数据相关

#### 获取原油期权链
```
GET /api/crude-oil/options
```

## 使用示例

### Python后端示例

```python
from option_strategies import StrategyBuilder, create_crude_oil_strategies
from risk_analysis import RiskAnalyzer

# 创建策略
strategies = create_crude_oil_strategies(underlying_price=500.0)

# 分析策略
analyzer = RiskAnalyzer()
for strategy in strategies:
    analysis = analyzer.analyze_strategy(
        strategy, 
        spot_price=500.0, 
        time_to_expiry=30/365, 
        volatility=0.25
    )
    print(f"{strategy.name}: 最大盈利={analysis['max_profit']}, 最大亏损={analysis['max_loss']}")
```

### VIX指数计算示例

```python
from vix_calculator import VIXCalculator

vix_calc = VIXCalculator()

# 简化计算
vix = vix_calc.calculate_simple_vix([], underlying_price=500.0)
print(f"VIX指数: {vix}")
```

## 策略说明

### 1. 双卖（Short Straddle）
- **适用场景**: 预期标的物价格稳定，波动率下降
- **风险**: 无限（价格大幅波动时）
- **收益**: 有限（收取的权利金）

### 2. 宽跨式双卖（Short Strangle）
- **适用场景**: 预期价格在一定范围内波动
- **风险**: 无限
- **收益**: 有限

### 3. 铁鹰（Iron Condor）
- **适用场景**: 震荡市场，限制风险
- **风险**: 有限
- **收益**: 有限

### 4. 日历价差（Calendar Spread）
- **适用场景**: 利用时间价值差异
- **风险**: 有限
- **收益**: 有限

## 风险提示

期权交易具有高风险，可能导致全部本金损失。本系统仅供学习和研究使用，不构成任何投资建议。在实际交易前，请充分了解期权交易的风险，并根据自身风险承受能力谨慎决策。

## 配置说明

### TqSdk账户配置

如需连接实盘交易，请按以下步骤配置：

1. 注册信易账户：访问 [信易官网](https://www.shinnytech.com/) 注册账户
2. 配置环境变量：编辑项目根目录下的 `.env` 文件
3. 填写账户信息：
   ```
   TQSDK_ACCOUNT=你的信易账户
   TQSDK_PASSWORD=你的密码
   ```

**注意**：
- `.env` 文件已添加到 `.gitignore`，不会被提交到版本控制
- 请勿将账户密码硬编码在代码中
- 如不配置账户，系统将使用演示模式运行

## 技术栈

- **后端**: Python 3.8+, Flask, TqSdk, NumPy, SciPy, Pandas
- **前端**: Vue 3, Element Plus, ECharts, Axios
- **构建工具**: Vite

## 许可证

MIT License
