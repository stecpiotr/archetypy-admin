@echo off
chcp 65001 >nul
setlocal EnableExtensions

set "ROOT=%~dp0"
cd /d "%ROOT%"

REM --- 0) Kontrola: Python dost?pny?
where python >nul 2>&1
if errorlevel 1 (
  echo.
  echo BRAK PYTHONA w PATH.
  echo Zainstaluj Python 3 i zaznacz opcje "Add python.exe to PATH".
  echo.
  pause
  exit /b 1
)

REM --- 1) Kontrola: data.csv
if not exist "%ROOT%data.csv" (
  echo.
  echo BRAK PLIKU data.csv w folderze:
  echo %ROOT%
  echo.
  echo Wgraj eksport CAWI jako: data.csv
  echo i uruchom ponownie.
  echo.
  pause
  exit /b 1
)

REM --- 2) Virtualenv (.venv)
if not exist "%ROOT%.venv\Scripts\python.exe" (
  echo.
  echo [1/3] Tworze srodowisko .venv ...
  python -m venv "%ROOT%.venv"
  if errorlevel 1 (
    echo.
    echo BLAD: nie udalo sie utworzyc .venv
    echo.
    pause
    exit /b 1
  )
)

set "PY=%ROOT%.venv\Scripts\python.exe"

echo.
echo [1/3] Instalacja bibliotek (moze potrwac chwile, tylko za pierwszym razem)...
"%PY%" -m pip install --upgrade pip >nul
"%PY%" -m pip install -r "%ROOT%requirements.txt"
if errorlevel 1 (
  echo.
  echo BLAD: instalacja bibliotek nie powiodla sie.
  echo.
  pause
  exit /b 1
)

echo.
echo [2/3] Uruchamiam analize...
"%PY%" "%ROOT%analyze_poznan_archetypes.py"
if errorlevel 1 (
  echo.
  echo BLAD: analiza zakonczona bledem.
  echo.
  pause
  exit /b 1
)

echo.
echo [3/3] Gotowe. Otwieram folder WYNIKI...
start "" "%ROOT%WYNIKI"
echo.
exit /b 0
