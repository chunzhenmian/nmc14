@echo off
chcp 936 >nul
setlocal
title 工业燃气轮机系统 - 一键启动器
cd /d "%~dp0"

echo ============================================================
echo   工业燃气轮机排放预测与运行参数智能优化系统  -  一键启动
echo ============================================================
echo.

REM ---- 1. 选择后端 Python：优先课程专用环境 kecheng，找不到再用系统默认 ----
set "PYEXE=C:\miniconda\envs\kecheng\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"
echo [1/4] 后端 Python: %PYEXE%
echo.

REM ---- 2. 后端依赖缺失则自动按 requirements.txt 安装 ----
"%PYEXE%" -c "import flask,xgboost,pandas,sklearn" 2>nul || (
  echo [初始化] 后端依赖不完整，正在安装 backend\requirements.txt ...
  "%PYEXE%" -m pip install -r "%~dp0backend\requirements.txt"
)

REM ---- 3. 前端依赖缺失则自动 npm install ----
if not exist "%~dp0frontend\node_modules" (
  echo [初始化] 首次运行，安装前端依赖 npm install，可能需要几分钟...
  pushd "%~dp0frontend"
  call npm install
  popd
)

REM ---- 端口占用提示（不阻断） ----
netstat -ano | findstr "LISTENING" | findstr ":5000 " >nul 2>&1 && echo [提示] 5000 端口已被占用，后端可能已在运行，如异常请先运行 一键停止.bat
netstat -ano | findstr "LISTENING" | findstr ":5173 " >nul 2>&1 && echo [提示] 5173 端口已被占用，前端可能已在运行
echo.

REM ---- 4. 各开一个独立窗口启动后端 / 前端（子窗口切 UTF-8 以正常显示中文日志） ----
echo [2/4] 启动后端 Flask  http://127.0.0.1:5000
start "后端 Flask :5000" /D "%~dp0backend" cmd /k "chcp 65001 >nul && %PYEXE% app.py"

echo [3/4] 启动前端 Vite   http://127.0.0.1:5173
start "前端 Vite :5173" /D "%~dp0frontend" cmd /k "chcp 65001 >nul && npm run dev"

echo [4/4] 等待服务就绪，6 秒后自动打开浏览器...
echo.
echo   前端地址(日常使用): http://127.0.0.1:5173
echo   后端健康检查      : http://127.0.0.1:5000/api/health
echo.
timeout /t 6 /nobreak >nul
start "" "http://127.0.0.1:5173"

echo ============================================================
echo  前后端已在两个独立窗口运行。
echo  停止：关闭那两个窗口，或双击本目录的 一键停止.bat
echo  本启动器窗口可以直接关闭。
echo ============================================================
echo.
pause
endlocal
