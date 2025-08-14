@echo off
title 项目清理工具
echo.
echo ========================================
echo   🧹 项目清理工具
echo ========================================
echo.

echo 正在清理Python缓存文件...
if exist "__pycache__" (
    rmdir /s /q "__pycache__"
    echo ✅ 已删除 __pycache__ 目录
)

echo.
echo 正在清理编译文件...
for /r %%i in (*.pyc) do (
    del "%%i" 2>nul
    echo ✅ 已删除 %%i
)

echo.
echo 正在清理临时文件...
del *.tmp 2>nul
del *.bak 2>nul
del *.log 2>nul

echo.
echo 正在清理数据文件...
if exist "data\*.csv" (
    echo ⚠️  发现CSV数据文件，是否删除? (y/n)
    set /p choice=
    if /i "%choice%"=="y" (
        del "data\*.csv" 2>nul
        echo ✅ 已删除数据文件
    )
)

echo.
echo 正在清理日志文件...
if exist "logs\*.log" (
    echo ⚠️  发现日志文件，是否删除? (y/n)
    set /p choice=
    if /i "%choice%"=="y" (
        del "logs\*.log" 2>nul
        echo ✅ 已删除日志文件
    )
)

echo.
echo 🎉 清理完成！
echo.
echo 当前目录结构:
dir /b

echo.
pause
