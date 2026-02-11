# MpesaWorking.ps1 - COMPLETE ERROR-FREE VERSION
# All braces are properly closed - NO SYNTAX ERRORS

Write-Host "✅ M-Pesa Analytics PowerShell Client v1.0" -ForegroundColor Green
Write-Host "📡 Server: http://127.0.0.1:8000" -ForegroundColor Gray

# Configuration
$global:MpesaConfig = @{
    BaseUrl = "http://127.0.0.1:8000"
    Username = "test@example.com"
    Password = "test123"
    Token = $null
}

function Get-MpesaToken {
    Write-Host "🔐 Getting authentication token..." -ForegroundColor Cyan
    
    $body = @{
        username = $MpesaConfig.Username
        password = $MpesaConfig.Password
        grant_type = "password"
    }
    
    try {
        $response = Invoke-RestMethod `
            -Uri "$($MpesaConfig.BaseUrl)/auth/login" `
            -Method Post `
            -Body $body `
            -ContentType "application/x-www-form-urlencoded"
        
        $global:MpesaConfig.Token = $response.access_token
        Write-Host "✅ Token obtained" -ForegroundColor Green
        return $response.access_token
    } catch {
        Write-Host "❌ Authentication failed: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

function Add-MpesaTransaction {
    param(
        [Parameter(Mandatory=$true)]
        [string]$TransactionId,
        
        [Parameter(Mandatory=$true)]
        [double]$Amount,
        
        [Parameter(Mandatory=$true)]
        [string]$TransactionType,
        
        [Parameter(Mandatory=$true)]
        [string]$Counterparty
    )
    
    Write-Host "➕ Adding transaction: $TransactionId" -ForegroundColor Cyan
    
    # Get token if needed
    if (-not $MpesaConfig.Token) {
        $token = Get-MpesaToken
        if (-not $token) {
            Write-Host "❌ Cannot proceed without authentication" -ForegroundColor Red
            return $null
        }
    }
    
    # Create headers
    $headers = @{
        "Authorization" = "Bearer $($MpesaConfig.Token)"
        "Content-Type" = "application/json"
    }
    
    # Create transaction object
    $transaction = @{
        transaction_id = $TransactionId
        amount = $Amount
        transaction_type = $TransactionType
        counterparty = $Counterparty
        timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
    }
    
    # THE FIX: Manually create JSON array
    $json = $transaction | ConvertTo-Json
    $jsonBody = "[$json]"
    
    Write-Host "📤 Sending JSON:" -ForegroundColor DarkGray
    Write-Host $jsonBody -ForegroundColor Gray
    
    try {
        $response = Invoke-RestMethod `
            -Uri "$($MpesaConfig.BaseUrl)/transactions" `
            -Method Post `
            -Headers $headers `
            -Body $jsonBody `
            -ErrorAction Stop
        
        Write-Host "✅ Transaction added successfully!" -ForegroundColor Green
        Write-Host "   Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor DarkGray
        return $response
    } catch {
        Write-Host "❌ Failed to add transaction: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

function Get-MpesaAnalytics {
    Write-Host "📊 Retrieving analytics..." -ForegroundColor Cyan
    
    # Get token if needed
    if (-not $MpesaConfig.Token) {
        $token = Get-MpesaToken
        if (-not $token) {
            Write-Host "❌ Cannot proceed without authentication" -ForegroundColor Red
            return $null
        }
    }
    
    # Create headers
    $headers = @{
        "Authorization" = "Bearer $($MpesaConfig.Token)"
        "Content-Type" = "application/json"
    }
    
    try {
        $response = Invoke-RestMethod `
            -Uri "$($MpesaConfig.BaseUrl)/analytics" `
            -Method Get `
            -Headers $headers `
            -ErrorAction Stop
        
        Write-Host "✅ Analytics retrieved:" -ForegroundColor Green
        $response.PSObject.Properties | ForEach-Object {
            Write-Host "  $($_.Name): $($_.Value)" -ForegroundColor White
        }
        return $response
    } catch {
        Write-Host "❌ Failed to get analytics: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

function Test-MpesaConnection {
    Write-Host "🧪 Testing M-Pesa API connection..." -ForegroundColor Cyan
    
    try {
        # Test 1: API health
        Write-Host "1. Testing API health..." -ForegroundColor DarkGray
        $health = Invoke-RestMethod -Uri "$($MpesaConfig.BaseUrl)/" -Method Get
        Write-Host "   ✅ API is running: $($health.status)" -ForegroundColor Green
        
        # Test 2: Authentication
        Write-Host "2. Testing authentication..." -ForegroundColor DarkGray
        $token = Get-MpesaToken
        if ($token) {
            Write-Host "   ✅ Authentication successful" -ForegroundColor Green
        } else {
            Write-Host "   ❌ Authentication failed" -ForegroundColor Red
            return $false
        }
        
        # Test 3: Analytics
        Write-Host "3. Testing analytics..." -ForegroundColor DarkGray
        $analytics = Get-MpesaAnalytics
        if ($analytics) {
            Write-Host "   ✅ Analytics working" -ForegroundColor Green
            Write-Host "   Transaction count: $($analytics.transaction_count)" -ForegroundColor Gray
        } else {
            Write-Host "   ❌ Analytics failed" -ForegroundColor Red
            return $false
        }
        
        Write-Host "`n🎉 All tests passed successfully!" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "❌ Connection test failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Display available commands
Write-Host "`n📋 Available commands:" -ForegroundColor Cyan
Write-Host "  Test-MpesaConnection    - Test API connectivity" -ForegroundColor Gray
Write-Host "  Add-MpesaTransaction    - Add a transaction" -ForegroundColor Gray
Write-Host "  Get-MpesaAnalytics      - Get analytics" -ForegroundColor Gray
Write-Host ""
Write-Host "💡 Quick start: Test-MpesaConnection" -ForegroundColor Yellow