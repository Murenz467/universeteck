@echo off
rem  Double-click this file. It does everything in the right order, then starts the website.
cd /d "%~dp0"
if not exist .env (
  echo DEBUG=1> .env
  echo Created .env for local work.
)
echo.
echo === Installing what the site needs (first time can take a minute) ===
python -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo Could not install. Make sure Python is installed and "Add Python to PATH" was ticked.
  pause
  exit /b 1
)
echo.
python manage.py setup_site
if errorlevel 1 (
  echo Something went wrong above. Copy the message and send it to Claude.
  pause
  exit /b 1
)
echo.
echo === Website is starting. Keep this window open. Press Ctrl+C to stop. ===
start "" http://127.0.0.1:8000
python manage.py runserver
pause
