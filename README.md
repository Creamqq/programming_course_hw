# 期权分析系统

一个基于 Python + Vue 的期权分析网页应用，支持希腊字母拆解和波动率曲面拟合。

**重要：本系统使用天勤SDK获取真实期权数据，需要配置天勤账户才能使用。**

## 功能特性

### 1. 希腊字母分析
- **Delta (δ)**: 标的价格变动1单位，期权价格变动量
- **Gamma (γ)**: 标的价格变动1单位，Delta变动量
- **Theta (θ)**: 每过一天，期权价格变动量
- **Vega (ν)**: 波动率变动1%，期权价格变动量
- **Rho (ρ)**: 利率变动1%，期权价格变动量
- 通过合约代码查询期权信息
- 自动获取标的价格、行权价、到期时间等参数
- 支持隐含波动率计算
- 希腊字母敏感性分析图表

### 2. 波动率曲面拟合
- 基于实时期权链数据生成波动率曲面
- 3D波动率曲面可视化
- 热力图展示
- 多项式拟合方法
- 期权链数据表格展示

## 技术栈

### 后端
- Python 3.8+
- Flask (Web框架)
- NumPy (数值计算)
- SciPy (科学计算)
- tqsdk (天勤SDK，获取真实行情数据)

### 前端
- Vue 3 (前端框架)
- Vite (构建工具)
- Element Plus (UI组件库)
- ECharts + ECharts GL (图表可视化)
- Axios (HTTP请求)

## 项目结构

```
.
├── backend/                # Python后端
│   ├── app.py             # Flask主应用
│   ├── greeks.py          # 希腊字母计算模块
│   ├── volatility_surface.py  # 波动率曲面拟合模块
│   ├── data_fetcher.py    # tqsdk数据获取模块
│   ├── requirements.txt   # Python依赖
│   ├── .env.example       # 环境变量模板
│   └── .env               # 环境变量配置
│
└── frontend/              # Vue前端
    ├── src/
    │   ├── main.js        # 入口文件
    │   ├── App.vue        # 根组件
    │   ├── router/        # 路由配置
    │   └── views/         # 页面组件
    │       ├── GreeksAnalysis.vue    # 希腊字母分析页
    │       └── VolatilitySurface.vue # 波动率曲面页
    ├── index.html
    ├── package.json
    └── vite.config.js
```

## 安装与运行

### 1. 后端安装

```bash
cd backend
pip install -r requirements.txt
```

### 2. 前端安装

```bash
cd frontend
npm install
```

### 3. 配置天勤账户

**必须配置天勤账户才能使用本系统！**

#### 方法一：使用环境变量文件（推荐）

1. 复制配置模板：
```bash
cd backend
cp .env.example .env
```

2. 编辑 `.env` 文件，填入你的信易账户信息：
```env
TQ_ACCOUNT=你的信易账户
TQ_PASSWORD=你的信易密码
```

#### 方法二：代码中直接配置

在 `data_fetcher.py` 中直接传入账户信息：

```python
data_fetcher = TqsdkDataFetcher(account="您的信易账户", password="您的密码")
```

**注意**：
- 如果不配置账户信息，系统将使用天勤模拟账户（数据可能不准确）
- `.env` 文件已添加到 `.gitignore`，不会被提交到版本控制
- 请勿将账户密码提交到公开仓库

### 4. 运行后端

```bash
cd backend
python app.py
```

后端服务将运行在 http://localhost:5000

### 5. 运行前端

```bash
cd frontend
npm run dev
```

前端服务将运行在 http://localhost:3000

## 使用说明

### 希腊字母分析页面

1. 输入期权合约代码：
   - 例如：`KQ.m@SHFE.cu2401C70000`（铜期权看涨）
   - 例如：`KQ.m@SHFE.au2401P400`（黄金期权看跌）

2. 点击"查询"按钮获取期权信息

3. 设置参数：
   - 无风险利率（默认3%）
   - 到期天数（可选，系统会自动从合约代码解析）

4. 点击"计算希腊字母"按钮

5. 查看结果：
   - 希腊字母数值展示
   - 隐含波动率
   - 敏感性分析图表

### 波动率曲面页面

1. 选择标的资产（如CU、AU）

2. 选择交易所（如SHFE）

3. 设置无风险利率

4. 点击"生成波动率曲面"按钮

5. 查看：
   - 3D波动率曲面
   - 热力图
   - 期权链数据表格

## 数据来源

### 所有数据均来自天勤SDK

#### 希腊字母计算
- **标的价格**：通过tqsdk实时获取
- **行权价**：从期权合约信息获取
- **到期时间**：从合约代码解析或手动输入
- **市场价格**：通过tqsdk实时获取
- **隐含波动率**：根据市场价格反推

#### 波动率曲面
- **期权链数据**：通过tqsdk获取实时期权链
- **隐含波动率**：对每个期权计算隐含波动率
- **曲面拟合**：基于多项式拟合方法

## API接口

### 获取期权信息
- **GET** `/api/option-info/<symbol>`
- 参数：symbol（期权合约代码）
- 返回：期权基本信息（价格、行权价、标的价格等）

### 通过合约代码计算希腊字母
- **POST** `/api/calculate-greeks-by-symbol`
- 参数：symbol（合约代码）, risk_free_rate（无风险利率）, days_to_expiry（到期天数，可选）
- 返回：希腊字母值、隐含波动率等

### 获取期权链希腊字母
- **POST** `/api/option-chain-greeks`
- 参数：underlying（标的代码）, exchange（交易所）, risk_free_rate（无风险利率）
- 返回：期权链数据及希腊字母

### 生成波动率曲面
- **POST** `/api/volatility-surface`
- 参数：underlying（标的代码）, exchange（交易所）
- 返回：波动率曲面数据

### 希腊字母敏感性分析
- **POST** `/api/greeks-sensitivity`
- 参数：symbol（合约代码）, parameter（参数类型）, range_start, range_end, num_points
- 返回：敏感性分析数据

### 获取历史波动率
- **POST** `/api/historical-volatility`
- 参数：symbol（合约代码）, days（历史天数）
- 返回：年化历史波动率

### 获取历史K线
- **POST** `/api/historical-klines`
- 参数：symbol（合约代码）, days（历史天数）
- 返回：历史K线数据（OHLCV）

## 注意事项

1. **必须配置天勤账户**：系统使用真实数据，需要有效的天勤账户
2. 波动率曲面拟合至少需要4个期权数据点
3. 隐含波动率计算使用Brent方法求解
4. 3D曲面支持自动旋转查看
5. 建议使用Chrome或Firefox浏览器以获得最佳体验
6. 历史波动率基于日K线数据计算，年化因子为252

## 合约代码格式

### 铜期权
- 看涨：`KQ.m@SHFE.cu2401C70000`（2024年1月到期，行权价70000）
- 看跌：`KQ.m@SHFE.cu2401P70000`（2024年1月到期，行权价70000）

### 黄金期权
- 看涨：`KQ.m@SHFE.au2401C400`（2024年1月到期，行权价400）
- 看跌：`KQ.m@SHFE.au2401P400`（2024年1月到期，行权价400）

## 许可证

MIT License
