@echo off
setlocal

cd /d "%~dp0"

echo SOLOMON_CUSTOMIZER Git updater
echo.

where git >nul 2>nul
if errorlevel 1 (
    echo ERROR: git was not found in PATH.
    echo Install Git for Windows, then run this file again.
    pause
    exit /b 1
)

git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
    echo ERROR: this folder is not a Git working tree.
    pause
    exit /b 1
)

for /f "usebackq delims=" %%B in (`git branch --show-current`) do set "BRANCH=%%B"
if /i not "%BRANCH%"=="main" (
    echo ERROR: current branch is "%BRANCH%".
    echo Switch to main before updating.
    pause
    exit /b 1
)

git diff --quiet
if errorlevel 1 (
    echo ERROR: local file changes exist.
    echo Commit, stash, or discard them before updating.
    pause
    exit /b 1
)

git diff --cached --quiet
if errorlevel 1 (
    echo ERROR: staged local changes exist.
    echo Commit, stash, or unstage them before updating.
    pause
    exit /b 1
)

echo Fetching origin/main...
git fetch --prune origin main
if errorlevel 1 (
    echo ERROR: git fetch failed.
    pause
    exit /b 1
)

for /f "usebackq delims=" %%H in (`git rev-parse HEAD`) do set "LOCAL=%%H"
for /f "usebackq delims=" %%H in (`git rev-parse origin/main`) do set "REMOTE=%%H"
for /f "usebackq delims=" %%H in (`git merge-base HEAD origin/main`) do set "BASE=%%H"

if "%LOCAL%"=="%REMOTE%" (
    echo Already up to date.
    pause
    exit /b 0
)

if "%LOCAL%"=="%BASE%" (
    echo Updating by fast-forward merge...
    git merge --ff-only origin/main
    if errorlevel 1 (
        echo ERROR: update failed.
        pause
        exit /b 1
    )
    echo Update complete.
    pause
    exit /b 0
)

if "%REMOTE%"=="%BASE%" (
    echo No update applied: local main is ahead of origin/main.
    echo Push your commits or reset manually if needed.
    pause
    exit /b 0
)

echo ERROR: local main and origin/main have diverged.
echo Resolve this manually with Git.
pause
exit /b 1
