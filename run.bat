@echo off
setlocal
cd /d %~dp0

if not exist backend\requirements.txt (
echo backend not found.
exit /b 1
)

pushd backend
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo Starting backend on http://127.0.0.1:8000 ...
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
popd
