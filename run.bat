@echo off
REM StoryFrame 启动脚本 - 使用项目专用 venv
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python main.py
pause
