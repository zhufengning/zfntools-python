@echo off
setlocal enabledelayedexpansion

if exist ".port" (
    set /p PORT=<.port
    powershell -Command "$udpClient = New-Object System.Net.Sockets.UdpClient; $udpClient.Connect('127.0.0.1', !PORT!); $bytes = [System.Text.Encoding]::UTF8.GetBytes('quit'); $udpClient.Send($bytes, $bytes.Length); $udpClient.Close()"

    timeout /t 2 /nobreak >nul
    
    del ".port"
)

start start_pyinstaller.exe
start pytoolbox.exe --silent