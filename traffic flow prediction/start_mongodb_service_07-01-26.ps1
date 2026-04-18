# PowerShell script to start MongoDB as a Windows Service

Write-Host "Checking MongoDB Windows Service..." -ForegroundColor Cyan

# Check if MongoDB service exists
$mongoService = Get-Service -Name "MongoDB" -ErrorAction SilentlyContinue

if (-not $mongoService) {
    Write-Host "❌ MongoDB Windows Service not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "To install MongoDB as a service:" -ForegroundColor Yellow
    Write-Host "1. Install MongoDB Community Server" -ForegroundColor White
    Write-Host "2. Run as Administrator: mongod --install --serviceName MongoDB" -ForegroundColor White
    Write-Host "3. Configure service: mongod --config C:\Program Files\MongoDB\Server\*\bin\mongod.cfg" -ForegroundColor White
    exit 1
}

# Check service status
if ($mongoService.Status -eq 'Running') {
    Write-Host "✅ MongoDB service is already running" -ForegroundColor Green
    Write-Host "   Connection: mongodb://127.0.0.1:27017" -ForegroundColor Gray
    exit 0
}

Write-Host "Starting MongoDB service..." -ForegroundColor Cyan
try {
    Start-Service -Name "MongoDB"
    Start-Sleep -Seconds 2
    
    $mongoService = Get-Service -Name "MongoDB"
    if ($mongoService.Status -eq 'Running') {
        Write-Host "✅ MongoDB service started successfully!" -ForegroundColor Green
        Write-Host "   Connection: mongodb://127.0.0.1:27017" -ForegroundColor Gray
    } else {
        Write-Host "❌ Failed to start MongoDB service" -ForegroundColor Red
        Write-Host "   Status: $($mongoService.Status)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Error starting MongoDB service: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Try running PowerShell as Administrator" -ForegroundColor Yellow
}


