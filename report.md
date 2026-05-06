# WiseCoin 期权分析程序

## 一、项目整体架构

```
run.py (入口)
  ├── cli/oneclick.py (一键执行编排器)
  │   ├── data/backup.py          → 数据备份
  │   ├── data/openctp.py         → OpenCTP行情获取
  │   ├── data/option_quotes.py   → 期权行情获取
  │   ├── cli/option_analyzer.py  → 期权综合分析
  │   ├── cli/futures_analyzer.py → 期货联动分析
  │   ├── data/live_symbol.py     → 实时监控配置
  │   └── data/klines.py          → 期货K线获取
  └── cli/live_gui.py             → 实时监控GUI
```

---

## 二、数据下载逻辑

### 2.1 TqSDK 客户端封装

**文件**: `data/tqsdk_client.py`

TqSdkClient 是统一的数据源接入层，封装了 TqApi 的生命周期管理：

- **8种运行模式**: 回测(TqSim)、快期模拟(TqKq)、Simnow模拟、以及6家期货公司实盘
- **异步上下文管理**: 通过 `async with` 管理 API 连接的生命周期
- **自动重建机制**: `rebuild_api()` 防止连接超时
- **认证管理**: 从环境变量或配置文件读取 TqAuth 认证信息

### 2.2 期权行情获取流程

**文件**: `data/option_quotes.py`

**核心类**: `OptionQuotesManager`

#### 2.2.1 获取期权合约列表

```
get_all_option_symbols()
  ├── 有 live_symbols 配置 → _get_options_by_underlying() (高效模式)
  │     ├── 遍历每个标的，调用 api.query_quotes(underlying_symbol=xxx)
  │     ├── 过滤股票期权(SSE/SZSE)
  │     └── 额外获取 CFFEX 股指期权
  └── 无配置 → _get_all_options_full() (全市场模式)
        ├── api.query_quotes(ins_class='OPTION', expired=False)
        └── 过滤股票期权
```

**两种模式的区别**:
- **高效模式**: 根据 `wisecoin-symbol-live.json` 中配置的标的合约，直接查询对应期权，避免全市场扫描
- **全市场模式**: 获取所有期权后再过滤，耗时较长但覆盖全面

#### 2.2.2 获取期权实时行情

```
get_option_quotes_from_excel()
  ├── 从 Excel 读取期权合约列表(按sheet分组)
  ├── 断点续传逻辑
  │     ├── 检查已有的 CSV/XLSX 行情文件
  │     ├── 加载已获取的合约数据
  │     └── 只获取尚未获取的合约
  ├── 分批获取(每批 batch_size 个)
  │     ├── api.get_quote() 获取实时行情
  │     ├── 每 save_interval 个保存一次
  │     └── 每 api_rebuild_interval 个重建 API 连接
  └── 按产品分类导出到 Excel(每个产品一个sheet)
```

**断点续传机制**:
- 检测已存在的行情文件
- 识别 `last_price` 有效的合约视为已获取
- 只获取剩余未完成的合约
- 支持 CSV 和 XLSX 两种格式

#### 2.2.3 期货K线获取

**文件**: `data/klines.py`

**核心类**: `FuturesKlineFetcher`

```
fetch_and_save()
  ├── _extract_underlyings() → 从期权行情文件中提取标的期货合约
  ├── _fetch_all_klines() → 批量获取K线
  │     └── api.get_kline_serial(symbol, duration=86400, data_length=250)
  └── _export_to_csv/_export_to_excel() → 导出
```

- 默认获取250根日K线
- 每个标的合约一个sheet(Excel)或合并CSV
- 包含Summary汇总表(最新K线数据)

### 2.3 历史波动率获取

**文件**: `cli/option_analyzer.py`

```
_get_historical_volatility(underlyings)
  ├── 连接 TqSDK 获取日K线(65根)
  ├── 计算 HV5/HV20/HV60
  │     └── log_returns = log(close[1:]/close[:-1])
  │     └── HV = std(returns, window) * sqrt(252)
  └── 失败时使用默认值 0.25
```

### 2.4 数据文件格式

| 文件名 | 格式 | 内容 |
|--------|------|------|
| wisecoin-期权品种.xlsx | XLSX(多sheet) | 期权合约列表，按产品分组 |
| wisecoin-期权行情.csv | CSV | 期权实时行情数据 |
| wisecoin-期货行情.xlsx | XLSX | 期货行情(Summary) |
| wisecoin-期货K线.csv | CSV | 期货日K线数据 |
| wisecoin-symbol-live.json | JSON | 实时监控标的配置 |
| wisecoin-symbol-params.json | JSON | 品种参数(保证金率等) |

---

## 三、观点形成逻辑

### 3.1 期权基础指标计算

**文件**: `core/analyzer.py`

**核心类**: `OptionAnalyzer`

#### 3.1.1 虚实度分析

```
_calc_intrinsic_degree()
  ├── CALL: (标的价 - 行权价) / 标的价 × 100
  ├── PUT:  (行权价 - 标的价) / 标的价 × 100
  └── 档位分类:
        > 20%  → 深度实值
        > 10%  → 中度实值
        -10%~10% → 平值附近
        < -10% → 中度虚值
        < -20% → 深度虚值
```

#### 3.1.2 价值分解

```
_calc_value_decomposition()
  ├── 内在价值 = max(标的价 - 行权价, 0)  [CALL]
  ├── 时间价值 = 期权价 - 内在价值
  ├── 时间价值占比 = 时间价值 / 期权价 × 100
  └── 溢价率 = (行权价 + 期权价 - 标的价) / 标的价 × 100  [CALL]
```

#### 3.1.3 杠杆收益分析

```
_calc_leverage_profit()
  ├── 杠杆倍数 = 标的价 / 期权价
  ├── 收益率 = 期权价 / 标的价 × 100
  ├── 年化收益率 = 收益率 / 剩余天数 × 365
  ├── 杠杆收益 = 期权价 × 乘数 / 保证金 × 100
  └── 杠杆年化 = 杠杆收益 / 剩余天数 × 365
```

#### 3.1.4 保证金计算

```
_calc_margin()
  ├── 标的期货保证金 = 标的价 × 乘数 × 保证金率
  ├── 虚值额 = max(行权价 - 标的价, 0) × 乘数  [CALL]
  └── 卖方保证金 = 期权价×乘数 + max(标的保证金 - 虚值额/2, 标的保证金/2)
```

### 3.2 隐含波动率计算

**文件**: `core/iv_calculator.py`

**核心类**: `IVCalculator`

#### 3.2.1 Black-Scholes 定价模型

```
bs_price(S, K, r, sigma, T, option_type)
  ├── d1 = (ln(S/K) + (r + σ²/2)T) / (σ√T)
  ├── d2 = d1 - σ√T
  ├── CALL = S×N(d1) - K×e^(-rT)×N(d2)
  └── PUT  = K×e^(-rT)×N(-d2) - S×N(-d1)
```

#### 3.2.2 隐含波动率求解

```
implied_volatility(price, S, K, T, option_type)
  ├── Newton-Raphson 迭代法
  │     └── σ(n+1) = σ(n) - (BS_price(σ(n)) - market_price) / vega
  ├── 特殊处理:
  │     ├── 深度实值期权 → 返回最小波动率
  │     ├── 价格 < 内在价值 → 返回NaN(套利机会)
  │     └── 时间价值极低 → 使用二分法兜底
  └── 收敛条件: |BS_price - market_price| < tolerance
```

#### 3.2.3 Greeks 计算

| Greek | 公式 | 含义 |
|-------|------|------|
| Delta | CALL: N(d1), PUT: N(d1)-1 | 标的价格变动1单位，期权价格变动量 |
| Gamma | N'(d1) / (S×σ×√T) | Delta对标的价格的敏感度 |
| Theta | -S×N'(d1)×σ/(2√T) - rK×e^(-rT)×N(d2) | 时间衰减(每日) |
| Vega | S×√T×N'(d1) | 波动率变动1%，期权价格变动量 |
| Rho | K×T×e^(-rT)×N(d2) | 利率变动1%，期权价格变动量 |

### 3.3 PCR 分析 (Put/Call Ratio)

**核心类**: `PCRAnalyzer`

```
PCR(持仓) = PUT持仓量 / CALL持仓量
PCR(成交) = PUT成交量 / CALL成交量
PCR(资金) = PUT沉淀资金 / CALL沉淀资金

情绪判断:
  PCR < 0.5  → 极度看多
  PCR < 0.8  → 看多
  0.8~1.2    → 中性
  PCR > 1.2  → 看空
  PCR > 1.5  → 极度看空
```

### 3.4 最大痛点分析

**核心类**: `MaxPainCalculator`

```
calculate_max_pain(strikes, call_oi_map, put_oi_map)
  ├── 遍历每个行权价
  ├── 计算卖方总损失:
  │     call_pain = max(0, 标的价 - 行权价) × CALL持仓
  │     put_pain  = max(0, 行权价 - 标的价) × PUT持仓
  │     total_pain = call_pain + put_pain
  └── 选择使卖方损失最小的行权价 → 最大痛点
```

**交易含义**: 期权卖方(通常是机构)有动机将标的价格推向最大痛点，使期权买方损失最大化。

### 3.5 交易类型分类

**核心类**: `OptionTradingClassifier`

```
classify(call_oi_change, put_oi_change, pcr, volume_ratio)
  ├── 波动率型:
  │     ├── CALL和PUT同时增仓
  │     ├── PCR接近1 (0.8~1.2)
  │     └── 成交量放大 (ratio >= 1.2)
  │     → 跨式/宽跨式建仓
  │
  ├── 方向型看多:
  │     ├── PCR < 0.5 (极度看多)
  │     └── CALL增仓 > PUT增仓
  │
  ├── 方向型看空:
  │     ├── PCR > 1.5 (极度看空)
  │     └── PUT增仓 > CALL增仓
  │
  └── 混合型:
        └── 双向增仓但PCR偏离中性
```

### 3.6 多因子评分系统

**核心类**: `OptionScorer`

```
score(analyzed_options)
  ├── 杠杆评分 (0-30分)
  │     ├── 5~20倍 → 30分 (适中为佳)
  │     ├── 3~5倍 或 20~30倍 → 20分
  │     └── > 30倍 → 10分
  │
  ├── 时间价值评分 (0-20分)
  │     ├── 30%~60% → 20分
  │     ├── 20%~30% 或 60%~80% → 15分
  │     └── 其他 → 10分
  │
  ├── 流动性评分 (0-30分)
  │     ├── 成交量>1000 且 持仓>1000 → 30分
  │     ├── 成交量>500 且 持仓>500 → 20分
  │     └── 成交量>100 且 持仓>100 → 10分
  │
  └── 实值程度评分 (0-20分)
        ├── 实值 → 20分
        ├── 轻微虚值 (价值度>0.9) → 15分
        └── 其他虚值 → 10分

生成信号:
  score >= 70 → BUY
  score <= 30 → SELL
  其他 → HOLD
```

### 3.7 期货趋势分析

**文件**: `cli/futures_analyzer.py`

**核心类**: `FuturesAnalysisRunner`

#### 3.7.1 资金流向判断

```
if 增仓 + 上涨 → 增仓上涨 (信号+2, 多头强势)
if 增仓 + 下跌 → 增仓下跌 (信号-2, 空头强势)
if 减仓 + 上涨 → 减仓上涨 (信号+1, 空头平仓)
if 减仓 + 下跌 → 减仓下跌 (信号-1, 多头平仓)
```

#### 3.7.2 趋势状态分类

```
if 涨跌>2% 且 增仓>5% → 强势多头
if 涨跌>1% 且 增仓>2% → 温和多头
if 涨跌>0% 且 增仓>0% → 弱势多头
if 涨跌<-2% 且 增仓>5% → 强势空头
... (对称)
if 涨跌>0% 且 减仓 → 减仓反弹
if 涨跌<0% 且 减仓 → 减仓回调
else → 震荡
```

#### 3.7.3 杠杆涨跌计算

```
实际涨跌% = (现价 - 昨收) / 昨收 × 100
杠杆涨跌% = 实际涨跌% × 杠杆倍数
杠杆倍数 = 1 / 保证金率
```

### 3.8 货权联动分析

**核心逻辑**: 将期货趋势与期权情绪进行共振分析

```
联动状态判断:
  ├── 期货多头 + 期权CALL主导 → 多头共振
  ├── 期货空头 + 期权PUT主导 → 空头共振
  ├── 期货多头 + 期权PUT主导 → 多头背离
  ├── 期货空头 + 期权CALL主导 → 空头背离
  └── 其他 → 中性震荡

共振评分:
  ├── 期货与期权信号同向 → +2分
  ├── 期货与期权信号反向 → -1分
  ├── 价格上涨 + PCR<0.8 → +1分
  └── 价格下跌 + PCR>1.2 → +1分

策略建议:
  ├── 多头共振 + 共振评分>=2 → 看多
  ├── 空头共振 + 共振评分>=2 → 看空
  ├── 多头背离 → 谨慎看多
  └── 空头背离 → 谨慎看空
```

---

## 四、输出文件体系

| 文件名 | 生成模块 | 内容 |
|--------|----------|------|
| wisecoin-期权排行.xlsx | cli/option_analyzer.py | 按标的汇总: PCR、最大痛点、情绪倾向、交易类型 |
| wisecoin-期权参考.xlsx | cli/option_analyzer.py | 每个期权的详细指标: IV、Greeks、评分、信号 |
| wisecoin-货权联动.xlsx | cli/futures_analyzer.py | 期货期权共振分析: 联动状态、共振评分、策略建议 |
| wisecoin-市场概览.xlsx | cli/futures_analyzer.py | 市场整体概览: 资金流向、趋势分布 |
| wisecoin-期货K线.csv | data/klines.py | 标的期货日K线数据 |

---

## 五、关键数据流

```
TqSDK API
  │
  ├──→ OptionQuotesManager → 期权合约列表 + 实时行情 → wisecoin-期权行情.csv
  │                              │
  │                              ├──→ FuturesKlineFetcher → 期货K线 → wisecoin-期货K线.csv
  │                              │
  │                              └──→ OptionAnalysisRunner
  │                                      │
  │                                      ├──→ OptionAnalyzer → 基础指标(杠杆/虚实度/时间价值)
  │                                      ├──→ IVCalculator → 隐含波动率 + Greeks
  │                                      ├──→ PCRAnalyzer → PCR指标 + 情绪评分
  │                                      ├──→ MaxPainCalculator → 最大痛点
  │                                      ├──→ OptionScorer → 多因子评分 + 交易信号
  │                                      ├──→ OptionTradingClassifier → 交易类型分类
  │                                      ├──→ PortfolioGreeksCalculator → 组合策略Greeks
  │                                      └──→ StrategyPnLAnalyzer → 策略盈亏分析
  │                                              │
  │                                              └──→ wisecoin-期权排行.xlsx
  │                                              └──→ wisecoin-期权参考.xlsx
  │
  └──→ FuturesAnalysisRunner
          │
          ├──→ 期货资金流向分析
          ├──→ 货权联动分析(共振/背离)
          └──→ wisecoin-货权联动.xlsx
               └──→ wisecoin-市场概览.xlsx
```

---

## 六、核心观点形成总结

程序的观点形成是一个**多维度交叉验证**的过程:

1. **方向判断**: 通过 PCR 指标、持仓变化、资金流向判断多空倾向
2. **波动率判断**: 通过双向增仓、IV与HV对比判断波动率预期
3. **共振验证**: 期货趋势与期权情绪是否一致，共振评分越高信号越可靠
4. **风险参考**: 最大痛点提供机构可能的目标价位
5. **个券筛选**: 多因子评分系统筛选出杠杆适中、流动性好、价值合理的期权合约
6. **组合分析**: 通过Greeks计算评估组合策略的风险暴露
7. **盈亏评估**: 通过情景分析评估策略在不同市场条件下的盈亏表现

---

## 七、组合策略的希腊字母计算与盈亏分析（新增模块）

### 7.1 组合策略 Greeks 计算

#### 7.1.1 理论基础

**文件**: `core/iv_calculator.py`, `core/portfolio_greeks.py`

所有组合策略的希腊字母计算都基于单个期权的 Greeks 计算（Black-Scholes 模型）：

```python
Delta = ∂V/∂S   # 标的价格变动1单位，期权价格变动量
Gamma = ∂²V/∂S² # Delta对标的价格的敏感度
Theta = ∂V/∂t   # 时间衰减(每日)
Vega  = ∂V/∂σ   # 波动率变动1%，期权价格变动量
Rho   = ∂V/∂r   # 利率变动1%，期权价格变动量
```

组合策略的希腊字母等于各腿(Leg)希腊字母的**加权求和**：

```
组合Delta = Σ(腿i的Delta × 腿i的数量 × 合约乘数)
组合Gamma = Σ(腿i的Gamma × 腿i的数量 × 合约乘数)
组合Theta = Σ(腿i的Theta × 腿i的数量 × 合约乘数)
组合Vega  = Σ(腿i的Vega  × 腿i的数量 × 合约乘数)
组合Rho   = Σ(腿i的Rho   × 腿i的数量 × 合约乘数)
```

**符号规则**:
- 买入期权(多头): 希腊字母取正号
- 卖出期权(空头): 希腊字母取负号

#### 7.1.2 常见组合策略的 Greeks 特征

**垂直价差 (Vertical Spread)**:
```
牛市价差: 买入低行权价CALL + 卖出高行权价CALL
  ├── Delta > 0 (温和看多)
  ├── Gamma 接近0 (两腿Gamma部分抵消)
  ├── Theta 可能为正或负
  └── Vega 接近0 (波动率风险有限)

熊市价差: 买入高行权价PUT + 卖出低行权价PUT
  ├── Delta < 0 (温和看空)
  ├── Gamma 接近0
  ├── Theta 可能为正或负
  └── Vega 接近0
```

**跨式策略 (Straddle)**:
```
买入跨式: 买入平值CALL + 买入平值PUT (同行权价)
  ├── Delta ≈ 0 (方向中性)
  ├── Gamma > 0 (大幅正向暴露)
  ├── Theta < 0 (时间衰减严重)
  └── Vega > 0 (波动率正向暴露)
适用: 预期大幅波动但方向不确定

卖出跨式: 卖出平值CALL + 卖出平值PUT
  ├── Delta ≈ 0
  ├── Gamma < 0 (大幅负向暴露)
  ├── Theta > 0 (时间收益)
  └── Vega < 0 (波动率负向暴露)
适用: 预期窄幅震荡
```

**宽跨式策略 (Strangle)**:
```
买入宽跨式: 买入虚值CALL + 买入虚值PUT (不同行权价)
  ├── Delta ≈ 0
  ├── Gamma > 0 (但比跨式小)
  ├── Theta < 0 (但比跨式小)
  └── Vega > 0
适用: 预期大幅波动，成本比跨式低
```

**蝶式价差 (Butterfly Spread)**:
```
买入蝶式: 买入1低行权价CALL + 卖出2中间行权价CALL + 买入1高行权价CALL
  ├── Delta ≈ 0 (在中间行权价附近)
  ├── Gamma < 0 (在中间行权价附近为负)
  ├── Theta > 0 (时间收益)
  └── Vega < 0 (波动率负向暴露)
适用: 预期标的价格稳定在中间行权价附近
```

**铁鹰式 (Iron Condor)**:
```
构建: 卖出宽跨式 + 买入更虚值的宽跨式保护
  ├── Delta ≈ 0
  ├── Gamma < 0 (有限风险)
  ├── Theta > 0 (时间收益)
  └── Vega < 0 (波动率负向暴露)
适用: 预期窄幅震荡，风险收益比可控
```

**比率价差 (Ratio Spread)**:
```
构建: 买入1腿 + 卖出N腿 (N>1)
  ├── Delta 取决于行权价选择
  ├── Gamma 可能为正或负
  ├── Theta 通常为正 (卖出腿多于买入腿)
  └── Vega 可能为负
适用: 温和方向性观点，同时获取时间价值
```

#### 7.1.3 Greeks 计算示例

```python
# 示例: 买入跨式策略 (Long Straddle)
# 买入1手 CALL @ K=4000, Delta=0.5, Gamma=0.001, Theta=-5, Vega=20
# 买入1手 PUT  @ K=4000, Delta=-0.5, Gamma=0.001, Theta=-5, Vega=20

组合Delta = 1 × 0.5 + 1 × (-0.5) = 0
组合Gamma = 1 × 0.001 + 1 × 0.001 = 0.002
组合Theta = 1 × (-5) + 1 × (-5) = -10 (每日时间衰减)
组合Vega  = 1 × 20 + 1 × 20 = 40 (波动率变动1%，组合价值变动40)

# 示例: 牛市价差 (Bull Call Spread)
# 买入1手 CALL @ K=3900, Delta=0.7, Gamma=0.0008, Theta=-3, Vega=15
# 卖出1手 CALL @ K=4100, Delta=0.3, Gamma=0.0006, Theta=-2, Vega=10

组合Delta = 1 × 0.7 + (-1) × 0.3 = 0.4
组合Gamma = 1 × 0.0008 + (-1) × 0.0006 = 0.0002
组合Theta = 1 × (-3) + (-1) × (-2) = -1
组合Vega  = 1 × 15 + (-1) × 10 = 5
```

#### 7.1.4 Greeks 在组合策略中的应用

| 应用场景 | 说明 |
|----------|------|
| Delta中性 | 通过调整标的期货头寸使组合Delta=0，对冲方向风险 |
| Gamma监控 | Gamma为正，标的大幅波动有利；Gamma为负，标的窄幅震荡有利 |
| Theta管理 | Theta为正，时间流逝有利；Theta为负，需尽快建仓获利 |
| Vega敞口 | Vega为正，波动率上升有利；Vega为负，波动率下降有利 |
| 风险限额 | 设定组合Greeks上限，控制整体风险暴露 |

#### 7.1.5 代码实现

**核心文件**: `core/portfolio_greeks.py`

**核心类**: `PortfolioGreeksCalculator`

```python
class PortfolioGreeksCalculator:
    def calculate_portfolio_greeks(self, strategy, underlying_price, volatilities=None, as_of_date=None):
        """计算组合策略的整体希腊字母"""
        for leg in strategy.legs:
            # 1. 获取该腿的波动率
            iv = self._get_leg_volatility(leg, volatilities)
            
            # 2. 计算剩余时间（年）
            time_to_expiry = leg.option.time_to_expiry(as_of_date)
            
            # 3. 计算单腿希腊字母（调用IVCalculator）
            leg_greeks = self._calculate_leg_greeks(option, underlying_price, iv, time_to_expiry)
            
            # 4. 方向符号（买入=正，卖出=负）
            direction = leg.direction_sign()
            
            # 5. 加权累加（考虑数量和乘数）
            weight = leg.quantity * leg.multiplier * direction
            portfolio_delta += leg_greeks['delta'] * weight
            portfolio_gamma += leg_greeks['gamma'] * weight
            # ... 其他Greeks
```

**主要功能**:

| 方法 | 功能 |
|------|------|
| `calculate_portfolio_greeks()` | 计算组合策略的整体希腊字母 |
| `calculate_greeks_sensitivity()` | 计算希腊字母对标的价格的敏感性 |
| `calculate_delta_hedge()` | 计算Delta对冲所需的标的期货手数 |
| `analyze_greeks_exposure()` | 分析希腊字母的风险暴露 |

---

### 7.2 策略的盈亏分析

#### 7.2.1 理论基础

**单个期权盈亏计算**:

```
CALL买方盈亏 = (到期标的价 - 行权价 - 期权费) × 乘数 × 手数  (当到期价 > 行权价)
             = -期权费 × 乘数 × 手数                          (当到期价 ≤ 行权价)

PUT买方盈亏  = (行权价 - 到期标的价 - 期权费) × 乘数 × 手数  (当到期价 < 行权价)
             = -期权费 × 乘数 × 手数                          (当到期价 ≥ 行权价)

CALL卖方盈亏 = -CALL买方盈亏
PUT卖方盈亏  = -PUT买方盈亏
```

**组合策略盈亏计算**:

```
组合盈亏 = Σ(腿i的盈亏 × 腿i的数量 × 合约乘数)
```

#### 7.2.2 盈亏平衡点计算

**买入跨式 (Long Straddle)**:
```
构建成本 = CALL期权费 + PUT期权费
上行盈亏点 = 行权价 + 构建成本
下行盈亏点 = 行权价 - 构建成本
```

**牛市价差 (Bull Call Spread)**:
```
构建成本 = 低行权价CALL期权费 - 高行权价CALL期权费
最大盈利 = (高行权价 - 低行权价) × 乘数 - 构建成本
最大亏损 = 构建成本
盈亏平衡点 = 低行权价 + 构建成本/乘数
```

**蝶式价差 (Butterfly Spread)**:
```
构建成本 = 低行权价CALL费 - 2×中间行权价CALL费 + 高行权价CALL费
最大盈利 = (中间行权价 - 低行权价) × 乘数 - 构建成本
最大亏损 = 构建成本
上行盈亏点 = 低行权价 + 构建成本/乘数
下行盈亏点 = 高行权价 - 构建成本/乘数
```

#### 7.2.3 盈亏情景分析

程序通过以下维度进行策略盈亏的情景分析：

**标的价格情景**:
```
for 标的价格 in range(现价×0.8, 现价×1.2, step=1%):
    计算组合在该价格下的盈亏
    → 生成盈亏曲线
```

**波动率情景**:
```
for 波动率 in range(IV×0.5, IV×1.5, step=5%):
    使用BS模型重新定价
    计算组合价值变化
    → 生成波动率敏感性曲线
```

**时间衰减情景**:
```
for 剩余天数 in range(当前天数, 0, step=-1):
    计算时间价值衰减
    → 生成Theta衰减曲线
```

#### 7.2.4 风险收益指标

```
最大盈利 = max(所有可能标的价下的盈亏)
最大亏损 = min(所有可能标的价下的盈亏)
盈亏比 = 最大盈利 / 最大亏损
风险收益比 = (预期盈利 - 预期亏损) / 最大亏损
```

#### 7.2.5 代码实现

**核心文件**: `core/strategy_pnl.py`

**核心类**: `StrategyPnLAnalyzer`

```python
class StrategyPnLAnalyzer:
    def analyze_strategy(self, strategy, underlying_price, current_date=None, volatilities=None):
        """全面分析策略盈亏"""
        # 1. 计算初始成本
        initial_cost = strategy.total_cost()
        
        # 2. 生成价格序列
        prices = np.linspace(min_price, max_price, num_points)
        
        # 3. 计算各价格点的盈亏
        for price in prices:
            pnl = self._calculate_strategy_pnl_at_expiry(strategy, price)
            pnl_pct = (pnl / abs(initial_cost) * 100) if initial_cost != 0 else 0
            scenarios.append(PnLScenario(underlying_price=price, pnl=pnl, pnl_pct=pnl_pct))
        
        # 4. 计算最大盈利和最大亏损
        max_profit = max(pnls)
        max_loss = min(pnls)
        
        # 5. 计算盈亏平衡点（线性插值）
        breakeven_points = self._find_breakeven_points(prices, pnls)
        
        return StrategyPnLAnalysis(...)
```

**主要功能**:

| 方法 | 功能 |
|------|------|
| `analyze_strategy()` | 全面分析策略盈亏（到期盈亏、盈亏平衡点、情景分析） |
| `analyze_pnl_with_time_decay()` | 分析时间衰减对策略盈亏的影响 |
| `analyze_pnl_with_volatility()` | 分析波动率变化对策略盈亏的影响 |
| `calculate_risk_metrics()` | 计算风险收益指标（盈亏比、最大回撤等） |
| `generate_pnl_summary()` | 生成盈亏分析摘要报告 |

---

### 7.3 数据模型扩展

在 `core/models.py` 中新增了以下数据模型：

```python
@dataclass
class StrategyLeg:
    """策略腿（单腿期权）"""
    option: OptionQuote           # 期权行情
    position_type: PositionType   # 头寸类型（买入/卖出）
    quantity: int = 1             # 数量（手数）
    entry_price: float = 0.0      # 入场价格
    multiplier: float = 1.0       # 合约乘数

@dataclass
class StrategyGreeks:
    """组合策略的希腊字母"""
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    rho: float = 0.0
    underlying_price: float = 0.0

@dataclass
class OptionStrategy:
    """期权组合策略"""
    name: str = ""
    strategy_type: StrategyType = StrategyType.CUSTOM
    underlying: str = ""
    legs: List[StrategyLeg] = field(default_factory=list)
    multiplier: float = 1.0
    expire_date: Optional[date] = None
    greeks: Optional[StrategyGreeks] = None
    pnl_analysis: Optional[StrategyPnLAnalysis] = None

@dataclass
class PnLScenario:
    """盈亏情景分析结果"""
    underlying_price: float
    pnl: float = 0.0
    pnl_pct: float = 0.0
    days_to_expiry: int = 0
    volatility: float = 0.0

@dataclass
class StrategyPnLAnalysis:
    """策略盈亏分析结果"""
    strategy_name: str = ""
    initial_cost: float = 0.0
    max_profit: float = 0.0
    max_loss: float = 0.0
    profit_ratio: float = 0.0
    breakeven_points: List[float] = field(default_factory=list)
    scenarios: List[PnLScenario] = field(default_factory=list)
    current_pnl: float = 0.0
    current_pnl_pct: float = 0.0
```

新增枚举类型：
- `PositionType`: LONG（买入）、SHORT（卖出）
- `StrategyType`: STRADDLE、STRANGLE、BULL_CALL_SPREAD、BEAR_PUT_SPREAD、BUTTERFLY、IRON_CONDOR、RATIO_SPREAD、CUSTOM

---

### 7.4 策略工厂模块

**核心文件**: `core/strategy_factory.py`

**核心类**: `StrategyFactory`

支持的策略类型：

| 策略 | 方法 | 说明 |
|------|------|------|
| 跨式策略 | `create_straddle()` | 买入平值CALL + 买入平值PUT |
| 卖出跨式 | `create_short_straddle()` | 卖出平值CALL + 卖出平值PUT |
| 宽跨式 | `create_strangle()` | 买入虚值CALL + 买入虚值PUT |
| 牛市价差 | `create_bull_call_spread()` | 买入低行权价CALL + 卖出高行权价CALL |
| 熊市价差 | `create_bear_put_spread()` | 买入高行权价PUT + 卖出低行权价PUT |
| 蝶式价差 | `create_butterfly()` | 买入1低 + 卖出2中 + 买入1高 |
| 铁鹰式 | `create_iron_condor()` | 卖出宽跨式 + 买入更虚值保护 |
| 比率价差 | `create_ratio_spread()` | 买入1腿 + 卖出N腿 |
| 自定义 | `create_custom_strategy()` | 自定义策略腿组合 |

---

### 7.5 模块集成

在 `core/__init__.py` 中更新了导出列表：

```python
from core.models import (
    PositionType,
    StrategyType,
    StrategyLeg,
    StrategyGreeks,
    PnLScenario,
    StrategyPnLAnalysis,
    OptionStrategy,
)
from core.portfolio_greeks import PortfolioGreeksCalculator
from core.strategy_pnl import StrategyPnLAnalyzer
from core.strategy_factory import StrategyFactory
```

新增测试文件：
- `tests/test_portfolio_greeks.py` - 组合策略希腊字母计算器测试
- `tests/test_strategy_pnl.py` - 策略盈亏分析器测试
- `tests/test_strategy_factory.py` - 策略工厂测试

---

### 7.6 完整使用示例

```python
from core.strategy_factory import StrategyFactory
from core.portfolio_greeks import PortfolioGreeksCalculator
from core.strategy_pnl import StrategyPnLAnalyzer
from core.models import OptionQuote, CallOrPut

# 1. 准备期权行情数据
call_atm = OptionQuote(
    symbol="IO2504-C-4000",
    underlying="IO2504",
    exchange_id="CFFEX",
    strike_price=4000.0,
    call_or_put=CallOrPut.CALL,
    last_price=150.0,
    bid_price=148.0,
    ask_price=152.0,
    volume=1000,
    open_interest=5000,
    expire_date=date.today() + timedelta(days=30),
    iv=0.25,
    margin=2000.0,
)

put_atm = OptionQuote(
    symbol="IO2504-P-4000",
    underlying="IO2504",
    exchange_id="CFFEX",
    strike_price=4000.0,
    call_or_put=CallOrPut.PUT,
    last_price=140.0,
    bid_price=138.0,
    ask_price=142.0,
    volume=800,
    open_interest=4000,
    expire_date=date.today() + timedelta(days=30),
    iv=0.26,
    margin=2000.0,
)

# 2. 构建组合策略
straddle = StrategyFactory.create_straddle(
    call_option=call_atm,
    put_option=put_atm,
    underlying="IO2504",
    quantity=1,
)

# 3. 计算组合Greeks
greeks_calc = PortfolioGreeksCalculator(risk_free_rate=0.015)
greeks = greeks_calc.calculate_portfolio_greeks(straddle, underlying_price=4000.0)

print("组合Greeks:")
print(f"  Delta: {greeks.delta:.4f}")
print(f"  Gamma: {greeks.gamma:.4f}")
print(f"  Theta: {greeks.theta:.2f}/日")
print(f"  Vega: {greeks.vega:.2f}")

# 4. 分析风险暴露
exposure = greeks_calc.analyze_greeks_exposure(greeks)
for key, value in exposure.items():
    print(f"  {key}: {value}")

# 5. 盈亏分析
pnl_analyzer = StrategyPnLAnalyzer(risk_free_rate=0.015)
analysis = pnl_analyzer.analyze_strategy(straddle, underlying_price=4000.0)

print("\n盈亏分析:")
print(f"  初始成本: ¥{analysis.initial_cost:.2f}")
print(f"  最大盈利: ¥{analysis.max_profit:.2f}")
print(f"  最大亏损: ¥{analysis.max_loss:.2f}")
print(f"  盈亏平衡点: {analysis.breakeven_points}")

# 6. 风险指标
metrics = pnl_analyzer.calculate_risk_metrics(analysis)
print(f"\n风险指标:")
print(f"  盈亏比: {metrics['profit_ratio']:.2f}")
print(f"  风险收益比: {metrics['risk_reward_ratio']:.2f}")
print(f"  最大回撤: ¥{metrics['max_drawdown']:.2f}")

# 7. 生成报告
summary = pnl_analyzer.generate_pnl_summary(analysis, metrics)
print(summary)
```
