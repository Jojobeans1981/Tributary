@echo off
title Tributary — Seed Database
echo.
echo ========================================
echo   TRIBUTARY — Database Seeder
echo ========================================
echo.

set /p COUNT="How many users to create? (default: 20): "
if "%COUNT%"=="" set COUNT=20

set /p DOMAIN="Email domain? (default: tributary-test.org): "
if "%DOMAIN%"=="" set DOMAIN=tributary-test.org

set /p PASSWORD="Shared password? (default: TributaryDemo1!): "
if "%PASSWORD%"=="" set PASSWORD=TributaryDemo1!

echo.
set /p CONNECTIONS="Create connections between users? (y/n, default: y): "
if "%CONNECTIONS%"=="" set CONNECTIONS=y

set /p MESSAGES="Create conversations and messages? (y/n, default: y): "
if "%MESSAGES%"=="" set MESSAGES=y

set /p SCORES="Compute match scores after seeding? (y/n, default: y): "
if "%SCORES%"=="" set SCORES=y

set /p CLEAR="Clear existing seed users from this domain first? (y/n, default: n): "
if "%CLEAR%"=="" set CLEAR=n

set FLAGS=--count %COUNT% --domain %DOMAIN% --password %PASSWORD%

if /i "%CONNECTIONS%"=="y" set FLAGS=%FLAGS% --connections
if /i "%MESSAGES%"=="y" set FLAGS=%FLAGS% --messages
if /i "%SCORES%"=="y" set FLAGS=%FLAGS% --compute-scores
if /i "%CLEAR%"=="y" set FLAGS=%FLAGS% --clear

echo.
echo ----------------------------------------
echo   Seeding %COUNT% users @ %DOMAIN%
echo ----------------------------------------
echo.

cd /d "%~dp0tributary_api"
.\venv\Scripts\python.exe manage.py seed_users %FLAGS%

echo.
pause
