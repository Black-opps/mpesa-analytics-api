# MpesaFinal.ps1 - COMPLETE WORKING VERSION

# Configuration
$global:MpesaConfig = @{
    BaseUrl = "http://127.0.0.1:8000"
    Username = "test@example.com"
    Password = "test123"
    Token = $null
}

function Get-MpesaToken {
    Write-Host "ðŸ” Getting authentication token..." -ForegroundColor Cyan
    
    $body = @{
        username = $MpesaConfig.Username
        password = $MpesaConfig.Password
        grant_type = "password"
        scope = ""
        client_id = ""
        client_secret = ""
    }
    
    try {
        $response = Invoke-RestMethod `
            -Uri "$($MpesaConfig.BaseUrl)/auth/login" `
            -Method Post `
            -Body $body `
            -ContentType "application/x-www-form-urlencoded"
        
        $global:MpesaConfig.Token = $response.access_token
        Write-Host "âœ… Token obtained" -ForegroundColor Green
        return $response.access_token
    } catch {
        Write-Host "âŒ Authentication failed: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

function New-MpesaConnection {
    Write-Host "ðŸ”Œ Creating API connection..." -ForegroundColor Cyan
    
    if (-not $MpesaConfig.Token) {
        $token = Get-MpesaToken
        if (-not $token) {
            throw "Unable to authenticate"
        }
    }
    
    $headers = @{
        "Authorization" = "Bearer $($MpesaConfig.Token)"
        "Content-Type" = "application/json"
    }
    
    return @{
        BaseUrl = $MpesaConfig.BaseUrl
        Headers = $headers
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
        [string]$Counterparty,
        
        [DateTime]$Timestamp = (Get-Date)
    )
    
    Write-Host "âž• Adding transaction: $TransactionId" -ForegroundColor Cyan
    
    $conn = New-MpesaConnection
    
    # Create transaction object
    $transaction = @{
        transaction_id = $TransactionId
        amount = $Amount
        transaction_type = $TransactionType
        counterparty = $Counterparty
        timestamp = $Timestamp.ToString("yyyy-MM-ddTHH:mm:ss")
    }
    
    # THE FIX: Create JSON array manually
    $transactionJson = $transaction | ConvertTo-Json
    $jsonBody = "[$transactionJson]"
    
    Write-Host "JSON being sent:" -ForegroundColor DarkGray
    Write-Host $jsonBody -ForegroundColor Gray
    
    try {
        $response = Invoke-RestMethod `
            -Uri "$($conn.BaseUrl)/transactions" `
            -Method Post `
            -Headers $conn.Headers `
            -Body $jsonBody `
            -ErrorAction Stop
        
        Write-Host "âœ… Transaction added successfully!" -ForegroundColor Green
        Write-Host "Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor DarkGray
        return $response
    } catch {
        Write-Host "âŒ Failed to add transaction: $($_.Exception.Message)" -ForegroundColor Red
        
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $errorBody = $reader.ReadToEnd()
            Write-Host "Error details: $errorBody" -ForegroundColor Red
        }
        
        throw
    }
}

function Get-MpesaAnalytics {
    Write-Host "ðŸ“Š Retrieving analytics..." -ForegroundColor Cyan
    
    $conn = New-MpesaConnection
    
    try {
        $response = Invoke-RestMethod `
            -Uri "$($conn.BaseUrl)/analytics" `
            -Method Get `
            -Headers $conn.Headers `
            -ErrorAction Stop
        
        Write-Host "âœ… Analytics retrieved:" -ForegroundColor Green
        $response.PSObject.Properties | ForEach-Object {
            Write-Host "  $($_.Name): $($_.Value)" -ForegroundColor White
        }
        return $response
    } catch {
        Write-Host "âŒ Failed to get analytics: $($_.Exception.Message)" -ForegroundColor Red
        throw
    }
}

function Test-MpesaConnection {
    Write-Host "ðŸ§ª Testing M-Pesa API connection..." -ForegroundColor Cyan
    
    try {
        # Test API health
        Write-Host "1. Testing API health..." -ForegroundColor DarkGray
        $health = Invoke-RestMethod -Uri "$($MpesaConfig.BaseUrl)/" -Method Get
        Write-Host "   âœ… API is running: $($health.status)" -ForegroundColor Green
        
        # Test authentication
        Write-Host "2. Testing authentication..." -ForegroundColor DarkGray
        $token = Get-MpesaToken
        if ($token) {
            Write-Host "   âœ… Authentication successful" -ForegroundColor Green
        } else {
            Write-Host "   âŒ Authentication failed" -ForegroundColor Red
            return $false
        }
        
        # Test analytics
        Write-Host "3. Testing analytics..." -ForegroundColor DarkGray
        $analytics = Get-MpesaAnalytics
        Write-Host "   âœ… Analytics working" -ForegroundColor Green
        Write-Host "   Transaction count: $($analytics.transaction_count)" -ForegroundColor Gray
        
        Write-Host "`nâœ… All tests passed!" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "âŒ Test failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Start-MpesaDemo {
    Write-Host "ðŸš€ M-Pesa Analytics Demo" -ForegroundColor Cyan
    Write-Host "=" * 50 -ForegroundColor DarkGray
    
    if (Test-MpesaConnection) {
        Write-Host "`nðŸ“ˆ Adding sample transactions..." -ForegroundColor Yellow
        
        # Add sample transactions
        $sampleTx = @(
            @{Id="DEMO_001"; Amount=1500.75; Type="Payment"; Counterparty="Customer A"},
            @{Id="DEMO_002"; Amount=2500.00; Type="Withdrawal"; Counterparty="Customer B"},
            @{Id="DEMO_003"; Amount=3500.25; Type="Deposit"; Counterparty="Customer C"}
        )
        
        foreach ($tx in $sampleTx) {
            try {
                Add-MpesaTransaction `
                    -TransactionId $tx.Id `
                    -Amount $tx.Amount `
                    -TransactionType $tx.Type `
                    -Counterparty $tx.Counterparty | Out-Null
                
                Write-Host "  âœ… $($tx.Id): $$($tx.Amount)" -ForegroundColor Green
            } catch {
                Write-Host "  âŒ Failed: $($tx.Id)" -ForegroundColor Red
            }
        }
        
        # Show final analytics
        Write-Host "`nðŸ“Š Final Analytics:" -ForegroundColor Yellow
        Get-MpesaAnalytics
    }
    
    Write-Host "`n" + ("=" * 50) -ForegroundColor DarkGray
    Write-Host "ðŸŽ‰ Demo completed!" -ForegroundColor Green
}

# Quick one-liner function for testing
function Quick-AddTransaction {
    param(
        [string]$Id = "QUICK_$(Get-Date -Format 'HHmmss')",
        [double]$Amount = 1000.00,
        [string]$Type = "Payment",
        [string]$Counterparty = "Quick Customer"
    )
    
    Write-Host "âš¡ Quick transaction: $Id" -ForegroundColor Cyan
    
    # Get token
    $body = @{
        username = $MpesaConfig.Username
        password = $MpesaConfig.Password
        grant_type = "password"
    }
    
    $token = (Invoke-RestMethod `
        -Uri "$($MpesaConfig.BaseUrl)/auth/login" `
        -Method Post `
        -Body $body `
        -ContentType "application/x-www-form-urlencoded").access_token
    
    # Create transaction JSON array manually
    $tx = @{
        transaction_id = $Id
        amount = $Amount
        transaction_type = $Type
        counterparty = $Counterparty
        timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
    } | ConvertTo-Json
    
    # THE FIX: Wrap in array brackets
    $jsonBody = "[$tx]"
    
    $headers = @{
        Authorization = "Bearer $token"
        "Content-Type" = "application/json"
    }
    
    Invoke-RestMethod `
        -Uri "$($MpesaConfig.BaseUrl)/transactions" `
        -Method Post `
        -Headers $headers `
        -Body $jsonBody
}

# Initialize
Write-Host "âœ… M-Pesa Analytics PowerShell Client" -ForegroundColor Green
Write-Host "ðŸ“¡ Server: $($MpesaConfig.BaseUrl)" -ForegroundColor Gray
Write-Host "ðŸ‘¤ User: $($MpesaConfig.Username)" -ForegroundColor Gray
Write-Host "" -ForegroundColor Gray
Write-Host "Available commands:" -ForegroundColor Cyan
Write-Host "  Test-MpesaConnection    - Test API connectivity" -ForegroundColor Gray
Write-Host "  Add-MpesaTransaction    - Add a transaction" -ForegroundColor Gray
Write-Host "  Get-MpesaAnalytics      - Get analytics" -ForegroundColor Gray
Write-Host "  Start-MpesaDemo         - Run full demo" -ForegroundColor Gray
Write-Host "  Quick-AddTransaction    - Quick test" -ForegroundColor Gray
