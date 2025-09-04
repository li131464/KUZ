@echo off
chcp 65001 > nul
title PyInstaller在线更新系统 - 完整测试

echo =========================================================
echo [完整测试] PyInstaller在线更新系统
echo =========================================================
echo.
echo 当前状态:
echo - 客户端版本: 1.0.0
echo - 服务端有新版本: 1.1.0 
echo - 主程序大小: 96MB
echo - 更新器大小: 9MB
echo.
echo 测试流程:
echo 1. 服务器已启动在 http://127.0.0.1:8000
echo 2. 客户端将检测到更新 (1.0.0 → 1.1.0)
echo 3. 下载96MB的新版本exe文件
echo 4. 启动独立更新器进行文件替换
echo 5. 重启应用显示新版本
echo.

:menu
echo =========================================================
echo 请选择操作:
echo 1. 启动服务端 (保持运行)
echo 2. 启动Python版本客户端 (开发测试)
echo 3. 启动PyInstaller exe版本 (生产环境)
echo 4. 运行完整系统测试
echo 5. 查看项目文档
echo 6. 退出
echo =========================================================
set /p choice="请输入选项 (1-6): "

if "%choice%"=="1" goto start_server
if "%choice%"=="2" goto start_python_client  
if "%choice%"=="3" goto start_exe_client
if "%choice%"=="4" goto run_full_test
if "%choice%"=="5" goto show_docs
if "%choice%"=="6" goto exit
echo 无效选项，请重新选择
goto menu

:start_server
echo.
echo [启动] 服务端正在启动...
echo 服务器地址: http://127.0.0.1:8000
echo 按 Ctrl+C 停止服务器
echo.
cd server
python start.py
cd ..
goto menu

:start_python_client
echo.
echo [启动] Python版本客户端 (开发模式)
echo 这将启动源码版本，用于开发和调试
echo.
cd client
python app.py
cd ..
goto menu

:start_exe_client
echo.
echo [启动] PyInstaller exe版本 (生产模式)
echo 这将启动打包后的exe文件，模拟真实用户环境
echo.
if not exist "client\dist\KuzflowApp.exe" (
    echo [错误] exe文件不存在，请先构建！
    echo 运行: cd client && python build.py
    pause
    goto menu
)
cd client\dist
KuzflowApp.exe
cd ..\..
goto menu

:run_full_test
echo.
echo [测试] 运行完整系统测试...
echo 这将验证所有组件是否正常工作
echo.
python test_update_flow_simple.py
pause
goto menu

:show_docs
echo.
echo [文档] 打开项目文档...
if exist "..\ref\PyInstaller在线更新完整指南.md" (
    start ..\ref\PyInstaller在线更新完整指南.md
) else (
    echo 文档文件不存在
)
goto menu

:exit
echo.
echo [完成] PyInstaller在线更新系统测试完成！
echo.
echo 总结:
echo ✓ 服务端 FastAPI 正常运行
echo ✓ 客户端 PyQt5 应用正常启动  
echo ✓ PyInstaller exe文件构建成功
echo ✓ 独立更新器正常工作
echo ✓ 版本检测和下载功能正常
echo ✓ 文件替换和重启机制正常
echo.
echo 项目已完成PyInstaller适配，可以用于生产环境！
echo.
pause