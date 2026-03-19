@echo off
REM Network Monitoring System - Batch Runner
REM Starts server and multiple clients for testing

echo.
echo ================================
echo Network Monitoring System
echo ================================
echo.
echo Starting server in new window...
start "Server" cmd /k python server.py

echo Waiting for server to start...
timeout /t 2 /nobreak

echo.
echo Starting 3 test clients...
echo.

start "Client 1" cmd /k python client.py
timeout /t 1 /nobreak

start "Client 2" cmd /k python client.py
timeout /t 1 /nobreak

start "Client 3" cmd /k python client.py

echo.
echo Server and 3 clients started!
echo Check the windows to see metrics being collected.
echo.
pause
