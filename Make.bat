@echo off

:: Install dependencies
echo Installing dependencies...
pip install --upgrade pip
pip install pymysql
pip install flet
pip install flet-desktop
pip install flet-lottie
pip install cryptography

echo Installation completed successfully!

:: Try running with python
echo Attempting to run script with 'python'...
python src\main.py
if %errorlevel% neq 0 (
    echo 'python' command failed, trying with 'python3'...
    python3 src\main.py
    if %errorlevel% neq 0 (
        echo Both 'python' and 'python3' failed to run the script.
        exit /b 1
    )
)

echo Script executed successfully!
pause
