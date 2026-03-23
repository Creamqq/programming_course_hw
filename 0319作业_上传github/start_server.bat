@echo off
echo 安装后端依赖...
cd server
pip install -r requirements.txt
echo.
echo 启动后端服务器...
echo 后端服务运行在 http://localhost:8000
echo.
python main.py
pause
