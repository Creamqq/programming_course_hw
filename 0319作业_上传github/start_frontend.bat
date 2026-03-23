@echo off
echo 安装前端依赖...
cd frontend
npm install
echo.
echo 启动前端开发服务器...
echo 前端服务运行在 http://localhost:5173
echo.
npm run dev
pause
