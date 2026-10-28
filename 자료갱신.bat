@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   표준품셈 자료 갱신 (검사 + 판 번호 + 변경 내역)
echo ============================================
echo.
set "PY=python"
where python >nul 2>nul || set "PY=py -3"
%PY% tools\pumsem_check.py --auto
if errorlevel 1 (
    echo.
    echo [실패] 위 메시지를 확인하세요. 이 상태로는 GitHub 에 올리지 마세요.
) else (
    echo.
    echo [완료] GitHub Desktop 에서 CHANGELOG.md 와 manifest.json 변경 내용을 확인한 뒤
    echo        Commit to main -^> Push origin 을 누르세요.
)
echo.
pause
