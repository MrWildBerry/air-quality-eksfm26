@echo off
setlocal
cd /d "%~dp0"
:menu
cls
echo ==========================================
echo             AIR QUALITY
echo ==========================================
echo 1. Atidaryti galutine ataskaita
echo 2. Pakartoti visa eksperimenta
echo 3. Paleisti prognozes CSV failui
echo 4. Paleisti kodo testus
echo 0. Baigti
set /p "choice=Pasirinkimas: "
if "%choice%"=="1" start "" "results\ataskaita.html"
if "%choice%"=="2" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch.ps1" -Action experiment
if "%choice%"=="3" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch.ps1" -Action predict
if "%choice%"=="4" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch.ps1" -Action test
if "%choice%"=="0" exit /b
if not "%choice%"=="1" pause
goto menu
