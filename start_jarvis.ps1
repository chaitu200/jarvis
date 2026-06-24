# Kill any existing JARVIS processes to ensure only ONE instance runs at a time
Write-Host "Cleaning up old JARVIS instances..."
Stop-Process -Name "electron" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "node" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue

# Start JARVIS Engine (Python Backend)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd engine; .\venv\Scripts\python.exe -u main.py *>&1 | Tee-Object -FilePath engine.log" -WindowStyle Hidden

# Start JARVIS UI (Electron + Vite)
cd ui
Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm run dev" -WindowStyle Hidden

# Wait for Vite dev server to be ready
Write-Host "Waiting for Vite to start..."
Start-Sleep -Seconds 3

# Launch Electron
npm start
