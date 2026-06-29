# Start ChatApp frontend (proxies API/WS to backend on port 9000)
Set-Location $PSScriptRoot\frontend
if (-not (Test-Path .\node_modules)) {
    Write-Host "Installing npm packages..."
    npm install
}
Write-Host "Frontend starting at http://localhost:5173"
npm run dev
