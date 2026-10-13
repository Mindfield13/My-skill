@echo off
chcp 65001 >nul
title M Ultra 数模工作台

:: ============================================================
::  Electron + Python FastAPI 桌面应用启动脚本
::  用法：双击运行，或从命令行执行
::  注意：修改 PROJECT_DIR 为你的项目路径
:: ============================================================

set "PROJECT_DIR=E:\Project\M Ultra\M-Ultra-数模"
set "BACKEND_PORT=18113"
set "VENV_PYTHON=.venv\Scripts\python.exe"
set "BACKEND_SCRIPT=src\backend\main.py"

cd /d "%PROJECT_DIR%"

echo [1/2] 启动后端服务 (port %BACKEND_PORT%)...
start "MUltra-Backend" /min cmd /c ^
  "set PYTHONPATH= && set PYTHONHOME= && set VIRTUAL_ENV= && set PYTHONUTF8= && set PYTHONIOENCODING= && set M_ULTRA_PORT=%BACKEND_PORT% && %VENV_PYTHON% %BACKEND_SCRIPT%"

echo 等待后端就绪...
:wait
timeout /t 2 /nobreak >nul
curl -s http://127.0.0.1:%BACKEND_PORT%/api/health >nul 2>&1
if errorlevel 1 goto wait

echo [2/2] 启动前端界面...
start "" "%PROJECT_DIR%\node_modules\electron\dist\electron.exe" "%PROJECT_DIR%"

echo 启动完成！后端端口: %BACKEND_PORT%