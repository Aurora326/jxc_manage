@echo off
setlocal
cd /d %~dp0

where npm >nul 2>nul || (
  echo npm not found. Please install Node.js LTS first.
  exit /b 1
)

if not exist frontend\node_modules (
  echo Installing frontend deps...
  pushd frontend
  npm install
  if errorlevel 1 exit /b 1
  popd
)

echo Building frontend...
pushd frontend
npm run build
if errorlevel 1 exit /b 1
popd

echo Installing backend deps...
pushd backend
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo Starting backend on http://127.0.0.1:8000 ...
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
popd
