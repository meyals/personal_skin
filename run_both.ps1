# הפעלת שרת אימות TCP + שרת Web Flask (שני חלונות)
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "מפעיל שרת אימות TCP (פורט 5050)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; py -3 run_auth_server.py"

Start-Sleep -Seconds 2

Write-Host "מפעיל שרת Web Flask (פורט 5000)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; py -3 run.py"

Write-Host "שני השרתים אמורים לרוץ בחלונות נפרדים."
