@echo off
chcp 65001 > nul
title PyInstaller在线更新演示

echo ========================================================
echo 🚀 PyInstaller在线更新演示项目
echo ========================================================
echo.

echo 📋 使用说明:
echo 1. 首先启动服务端（保持运行）
echo 2. 然后启动客户端测试更新功能
echo 3. 客户端会自动检查更新（v1.0.0 → v1.1.0）
echo.

:menu
echo ========================================================
echo 请选择操作:
echo 1. 启动服务端 (FastAPI)
echo 2. 启动客户端 (PyQt5应用)
echo 3. 构建exe版本
echo 4. 查看项目文档
echo 5. 退出
echo ========================================================
set /p choice="请输入选项 (1-5): "

if "%choice%"=="1" goto start_server
if "%choice%"=="2" goto start_client
if "%choice%"=="3" goto build_exe
if "%choice%"=="4" goto show_docs
if "%choice%"=="5" goto exit
echo 无效选项，请重新选择
goto menu

:start_server
echo.
echo 🌐 启动服务端...
echo 服务器地址: http://127.0.0.1:8000
echo 按 Ctrl+C 停止服务器
echo.
cd server
python start.py
cd ..
goto menu

:start_client
echo.
echo 🖥️ 启动客户端...
echo 注意观察更新提示！
echo.
cd client
python app.py
cd ..
goto menu

:build_exe
echo.
echo 🔨 构建exe版本...
echo 这会生成可发布的exe文件
echo.
cd client
python build.py
cd ..
echo.
echo ✅ 构建完成！查看 client/release/ 目录
pause
goto menu

:show_docs
echo.
echo 📖 打开项目文档...
start README_PyInstaller版本.md
goto menu

:exit
echo.
echo 👋 感谢使用PyInstaller在线更新演示项目！
echo 项目地址: E:\Code\code\kuz\demo\update_test
echo.
pause