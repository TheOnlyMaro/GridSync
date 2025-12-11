# Run server and 4 clients in separate terminals

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Start server in a new terminal
Write-Host "Starting server..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; python server.py"

# Wait a moment for server to start
Start-Sleep -Seconds 2

# Start 4 clients in separate terminals
for ($i = 1; $i -le 4; $i++) {
    Write-Host "Starting client $i..."
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; python ui.py"
    Start-Sleep -Seconds 0.5
}

Write-Host "All processes started!"
