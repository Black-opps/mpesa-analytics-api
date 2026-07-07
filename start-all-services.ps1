# start-all-services.ps1
# M-PESA Analytics Platform - Service Orchestrator

param(
    [switch]$StopAll = $false
)

if ($StopAll) {
    Write-Host "Stopping all services..." -ForegroundColor Yellow
    Get-Process uvicorn -ErrorAction SilentlyContinue | Stop-Process -Force
    Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Host "All services stopped" -ForegroundColor Green
    exit 0
}

Write-Host "Starting M-PESA Analytics Platform..." -ForegroundColor Cyan

$Services = @(
    @{ Name = "Auth Service"; Path = "services\auth-service"; Port = 8001; HealthEndpoint = "/health"; Command = "uvicorn src.main:app --port 8001 --host 0.0.0.0"; Dependencies = @(); Critical = $true; Color = "Green" }
    @{ Name = "Tenant Service"; Path = "services\tenant-service"; Port = 8002; HealthEndpoint = "/health"; Command = "uvicorn src.main:app --port 8002 --host 0.0.0.0"; Dependencies = @(); Critical = $true; Color = "Blue" }
    @{ Name = "Transaction Parser"; Path = "mpesa-transaction-parser"; Port = 8004; HealthEndpoint = "/health"; Command = "uvicorn src.main:app --port 8004 --host 0.0.0.0"; Dependencies = @(); Critical = $false; Color = "Yellow" }
    @{ Name = "Transaction Categorizer"; Path = "transaction-categorizer"; Port = 8009; HealthEndpoint = "/health"; Command = "uvicorn src.main:app --port 8009 --host 0.0.0.0"; Dependencies = @(); Critical = $false; Color = "DarkCyan" }
    @{ Name = "Cashflow Analyzer"; Path = "cashflow-analyzer"; Port = 8005; HealthEndpoint = "/health"; Command = "uvicorn src.main:app --port 8005 --host 0.0.0.0"; Dependencies = @(); Critical = $false; Color = "Magenta" }
    @{ Name = "Payment Service"; Path = "services\payment-service"; Port = 8007; HealthEndpoint = "/health"; Command = "uvicorn src.main:app --port 8007 --host 0.0.0.0"; Dependencies = @(); Critical = $false; Color = "Cyan" }
    @{ Name = "Billing Service"; Path = "services\billing-service"; Port = 8008; HealthEndpoint = "/health"; Command = "uvicorn src.main:app --port 8008 --host 0.0.0.0"; Dependencies = @(); Critical = $false; Color = "DarkYellow" }
    @{ Name = "Webhook Service"; Path = "services\webhook-service"; Port = 8010; HealthEndpoint = "/health"; Command = "uvicorn src.main:app --port 8010 --host 0.0.0.0"; Dependencies = @(); Critical = $false; Color = "DarkMagenta" }
    @{ Name = "Analytics Service"; Path = "mpesa-analytics-api"; Port = 8000; HealthEndpoint = "/health"; Command = "python -m uvicorn src.main:app --port 8000 --host 0.0.0.0"; Dependencies = @("Auth Service"); Critical = $true; Color = "Red" }
    @{ Name = "API Gateway"; Path = "services\dashboard-service"; Port = 9000; HealthEndpoint = "/health"; Command = "uvicorn src.main:app --port 9000 --host 0.0.0.0"; Dependencies = @("Auth Service", "Analytics Service"); Critical = $true; Color = "White" }
    @{ Name = "Dashboard UI"; Path = "mpesa-analytics-dashboard"; Port = 3000; HealthEndpoint = "/"; Command = "npm start"; IsReact = $true; Dependencies = @("API Gateway"); Critical = $true; Color = "White" }
)

$BaseDir = Get-Location
$HealthyServices = @()
$Processes = @()

function Test-ServiceHealth {
    param($Port, $ServiceName, $HealthEndpoint = "/health", $IsReact = $false)
    
    if ($IsReact) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$Port$HealthEndpoint" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "  ✓ $ServiceName is healthy" -ForegroundColor Green
                return $true
            }
        } catch { return $false }
        return $false
    }
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$Port$HealthEndpoint" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "  ✓ $ServiceName is healthy" -ForegroundColor Green
            return $true
        }
    } catch {
        Write-Host "  ⚠ $ServiceName not ready yet" -ForegroundColor Yellow
        return $false
    }
    return $false
}

function Wait-ForService {
    param($Port, $ServiceName, $HealthEndpoint = "/health", $IsReact = $false, $MaxRetries = 20)
    
    Write-Host "  Waiting for $ServiceName on port $Port..." -ForegroundColor Gray
    for ($i = 1; $i -le $MaxRetries; $i++) {
        if (Test-ServiceHealth -Port $Port -ServiceName $ServiceName -HealthEndpoint $HealthEndpoint -IsReact $IsReact) {
            return $true
        }
        Start-Sleep -Seconds 2
    }
    Write-Host "  ✗ $ServiceName failed to start" -ForegroundColor Red
    return $false
}

function Start-ServiceWindow {
    param($Service)
    
    $servicePath = Join-Path $BaseDir $Service.Path
    $logFile = Join-Path $BaseDir "logs\$($Service.Name -replace ' ', '_')_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
    
    $logDir = Join-Path $BaseDir "logs"
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    
    if (-not (Test-Path $servicePath)) {
        Write-Host "  ✗ Service directory not found: $servicePath" -ForegroundColor Red
        return $null
    }
    
    if ($Service.IsReact) {
        $scriptContent = @"
cd '$servicePath'
Write-Host '========================================' -ForegroundColor $($Service.Color)
Write-Host '  $($Service.Name) - Starting...' -ForegroundColor $($Service.Color)
Write-Host '  Port: $($Service.Port)' -ForegroundColor Gray
Write-Host '========================================' -ForegroundColor $($Service.Color)
npm start
"@
    } else {
        $venvPath = Join-Path $servicePath "venv\Scripts\Activate.ps1"
        $activateCmd = if (Test-Path $venvPath) { "& '.\venv\Scripts\Activate.ps1'" } else { "" }
        
        $scriptContent = @"
cd '$servicePath'
$activateCmd
Write-Host '========================================' -ForegroundColor $($Service.Color)
Write-Host '  $($Service.Name) - Starting...' -ForegroundColor $($Service.Color)
Write-Host '  Port: $($Service.Port)' -ForegroundColor Gray
Write-Host '========================================' -ForegroundColor $($Service.Color)
$($Service.Command) 2>&1 | Tee-Object -FilePath '$logFile'
"@
    }
    
    $tempScript = Join-Path $env:TEMP "start_$($Service.Name -replace ' ', '_')_$(Get-Random).ps1"
    $scriptContent | Out-File -FilePath $tempScript -Encoding UTF8
    
    $process = Start-Process powershell.exe -ArgumentList "-NoExit -File `"$tempScript`"" -PassThru
    
    Start-Job -ScriptBlock {
        Start-Sleep -Seconds 10
        Remove-Item $using:tempScript -Force -ErrorAction SilentlyContinue
    } | Out-Null
    
    return $process
}

Write-Host "`n📦 Starting Core Services:" -ForegroundColor Cyan
$coreServices = $Services | Where-Object { $_.Dependencies.Count -eq 0 }
foreach ($service in $coreServices) {
    Write-Host "`nStarting $($service.Name)..." -ForegroundColor $service.Color
    $process = Start-ServiceWindow -Service $service
    if ($process) {
        $Processes[$service.Name] = $process
        $ready = Wait-ForService -Port $service.Port -ServiceName $service.Name -HealthEndpoint $service.HealthEndpoint -IsReact ($service.IsReact -eq $true)
        if ($ready) { $HealthyServices += $service.Name }
    }
    Start-Sleep -Seconds 2
}

Write-Host "`n📦 Starting Dependent Services:" -ForegroundColor Cyan
$dependentServices = $Services | Where-Object { $_.Dependencies.Count -gt 0 }
foreach ($service in $dependentServices) {
    $depsMet = $true
    foreach ($dep in $service.Dependencies) {
        if ($dep -notin $HealthyServices) {
            Write-Host "  ⚠ Dependency '$dep' not ready. Skipping $($service.Name)" -ForegroundColor Red
            $depsMet = $false
            break
        }
    }
    if (-not $depsMet) { continue }
    
    Write-Host "`nStarting $($service.Name)..." -ForegroundColor $service.Color
    $process = Start-ServiceWindow -Service $service
    if ($process) {
        $Processes[$service.Name] = $process
        $ready = Wait-ForService -Port $service.Port -ServiceName $service.Name -HealthEndpoint $service.HealthEndpoint -IsReact ($service.IsReact -eq $true)
        if ($ready) { $HealthyServices += $service.Name }
    }
    Start-Sleep -Seconds 2
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "✅ Started: $($HealthyServices.Count)/$($Services.Count) services" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host "`n🌐 Access Points:" -ForegroundColor Yellow
Write-Host "  • API Gateway: http://localhost:9000/docs"
Write-Host "  • React Dashboard: http://localhost:3000"
Write-Host "  • Analytics API: http://localhost:8000/docs"

Write-Host "`nPress any key to stop all services..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Write-Host "`n🛑 Stopping all services..." -ForegroundColor Red
foreach ($process in $Processes.Values) {
    try { $process.CloseMainWindow() } catch {}
    Start-Sleep -Milliseconds 500
    try { $process.Kill() } catch {}
}
Write-Host "✅ All services stopped" -ForegroundColor Green
