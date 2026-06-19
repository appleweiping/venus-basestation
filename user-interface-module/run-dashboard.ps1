# Venus Basestation - connect to the robot and open the mission-control dashboard.
#
# One-time setup:
#   1. Copy .env.example to .env
#   2. Open .env and set VENUS_MQTT_USERNAME (e.g. robot_43_1) and
#      VENUS_MQTT_PASSWORD to your board's MQTT credentials.
# Then just run this script (from a PowerShell terminal):
#   .\run-dashboard.ps1
#
# It connects to mqtt.ics.ele.tue.nl on the username-derived topic and opens
# the live dashboard. With no .env it falls back to simulated demo data and
# tells you how to connect.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:PYTHONPATH = "src"

# Use the project venv if present (Windows or this machine's MSYS layout),
# otherwise the python on PATH.
if (Test-Path ".venv\Scripts\python.exe") {
    $py = ".venv\Scripts\python.exe"
} elseif (Test-Path ".venv\bin\python.exe") {
    $py = ".venv\bin\python.exe"
} else {
    $py = "python"
}

Write-Host "Launching Venus Basestation dashboard with $py ..." -ForegroundColor Cyan
& $py -m venus_basestation --ui tk
