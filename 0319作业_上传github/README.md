# 期货期限结构分析系统

前后端分离的期货期限结构分析网页应用

## 项目结构

```
0319/
├── server/              # 后端 FastAPI 服务
│   ├── main.py         # 主应用文件
│   └── requirements.txt # Python 依赖
├── frontend/           # 前端 Vue 应用
│   ├── index.html      # HTML 模板
│   ├── package.json    # Node.js 依赖
│   └── vite.config.js  # Vite 配置
├── start_server.bat    # 启动后端脚本
├── start_frontend.bat  # 启动前端脚本
└── main.py            # 原始脚本
```

## 功能特点

- 用户登录验证（快期账号密码）
- 选择品种和合约月份数
- 获取期货价格数据
- 生成期限结构图表
- 分析升水/贴水状态
- 提供交易策略建议

## 使用方法

### 方法一：分别启动（推荐）

1. **启动后端服务**
   ```bash
   cd server
   pip install -r requirements.txt
   python main.py
   ```
   后端运行在 http://localhost:8000

2. **启动前端服务**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   前端运行在 http://localhost:5173

### 方法二：使用批处理文件

1. 双击 `start_server.bat` 启动后端
2. 双击 `start_frontend.bat` 启动前端

## API 接口

### POST /api/login
登录验证
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

### POST /api/query
获取期货数据
```json
{
  "username": "your_username",
  "password": "your_password",
  "symbol_prefix": "SHFE.rb",
  "num_months": 12
}
```

返回数据包含：
- `chart`: Base64 编码的 PNG 图片
- `structure`: 升水/贴水状态
- `strategy`: 交易策略建议
- `data`: 价格数据数组

## 技术栈

### 后端
- FastAPI - Python Web 框架
- TqSDK - 天勤量化 API
- Pandas - 数据处理
- Matplotlib - 图表生成

### 前端
- Vue 3 - 前端框架
- Axios - HTTP 客户端
- Vite - 构建工具

## 免责声明

使用本系统前，请知晓并同意天勤量化免责条款：
https://www.shinnytech.com/blog/disclaimer/
