@echo off
chcp 936 >nul
title 工业燃气轮机系统 - 一键停止
echo ============================================================
echo   正在停止后端(5000)与前端(5173)服务 ...
echo ============================================================
set "FOUND=0"
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":5000 :5173"') do (
  echo 结束进程 PID=%%p
  taskkill /F /PID %%p >nul 2>&1
  set "FOUND=1"
)
if "%FOUND%"=="0" echo 未发现正在运行的前后端服务。
echo.
echo 已完成。若仍有残留的黑色服务窗口，手动关闭即可。
echo.
pause
