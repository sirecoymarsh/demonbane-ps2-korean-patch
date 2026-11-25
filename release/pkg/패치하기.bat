@echo off
setlocal
chcp 65001 >nul
set "HERE=%~dp0"
set "XD=%HERE%tools\xdelta3.exe"
set "PATCH=%HERE%KishinHoukou_Demonbane_KR_v3.xdelta"
set "SRC=%~1"
if "%SRC%"=="" (
  echo 기신포효 데몬베인 PS2 원본 ISO 파일을 이 파일 위로 끌어다 놓으세요.
  echo 원본: SLPM-65491, 4,609,081,344바이트
  pause
  exit /b 1
)
if not exist "%SRC%" (
  echo 파일을 찾을 수 없습니다: "%SRC%"
  pause
  exit /b 1
)
set "OUT=%~2"
if "%OUT%"=="" set "OUT=%~dpn1 (Korean v3).iso"
for %%A in ("%SRC%") do set "SIZE=%%~zA"
if not "%SIZE%"=="4609081344" (
  echo [주의] 원본 크기가 예상과 다릅니다: %SIZE% 바이트. 다른 덤프일 수 있지만 그대로 패치합니다.
)
echo 패치하는 중입니다. 1~2분쯤 걸립니다...
"%XD%" -d -f -n -a -s "%SRC%" "%PATCH%" "%OUT%"
if errorlevel 1 (
  echo 패치에 실패했습니다.
  pause
  exit /b 1
)
echo 완료: "%OUT%"
pause
