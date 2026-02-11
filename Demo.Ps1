# demo.ps1 - Complete demonstration
Write-Host "=== M-Pesa Analytics Demo ===" -ForegroundColor Cyan
Write-Host "=" * 40 -ForegroundColor DarkGray

# Configuration
$config = @{
    BaseUrl = "http://127.0.0.1:8000"
    Username = "test@example.com"
    Password = "test123"
}

# Helper function to add transaction
function Add-Tx {
    param($Id, $Amount, $Type, $Counterparty)
    
    Write-Host "Adding: $Id" -ForegroundColor Cyan
    
    # Get token
    $body = @{
        username = $config.Username
        password = $config.Password
        grant_type = "password"
    }
    
    $token = (Invoke-RestMethod `
        -Uri "$($config.BaseUrl)/auth/login" `
        -Method Post `
        -Body $body `
        -ContentType "application/x-www-form-urlencoded").access_token
    
    # Create transaction
    $tx = @{
        transaction_id = $Id
        amount = $Amount
        transaction_type = $Type
        counterparty = $Counterparty
        timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
    }
    
    # THE FIX: Wrap in array brackets
    $json = $tx | ConvertTo-Json
    $jsonBody = "[$json]"
    
    $headers = @{
        Authorization = "Bearer $token"
        "Content-Type" = "application/json"
    }
    
    $result = Invoke-RestMethod `
        -Uri "$($config.BaseUrl)/transactions" `
        -Method Post `
        -Headers $headers `
        -Body $jsonBody
    
    Write-Host "  ✅ Added: $$Amount - $Type" -ForegroundColor Green
    return $result
}

# Demo transactions
Write-Host "`n📈 Adding demo transactions..." -ForegroundColor Yellow

$demoTx = @(
    @{Id="DEMO_1"; Amount=1500.75; Type="Payment"; Counterparty="Customer A"},
    @{Id="DEMO_2"; Amount=2500.00; Type="Withdrawal"; Counterparty="Customer B"},
    @{Id="DEMO_3"; Amount=3500.25; Type="Deposit"; Counterparty="Customer C"}
)

foreach ($tx in $demoTx) {
    Add-Tx -Id $tx.Id -Amount $tx.Amount -Type $tx.Type -Counterparty $tx.Counterparty
}

# Get final analytics
Write-Host "`n📊 Getting final analytics..." -ForegroundColor Yellow

# Get token for analytics
$body = @{
    username = $config.Username
    password = $config.Password
    grant_type = "password"
}

$token = (Invoke-RestMethod `
    -Uri "$($config.BaseUrl)/auth/login" `
    -Method Post `
    -Body $body `
    -ContentType "application/x-www-form-urlencoded").access_token

$headers = @{
    Authorization = "Bearer $token"
    "Content-Type" = "application/json"
}

$analytics = Invoke-RestMethod `
    -Uri "$($config.BaseUrl)/analytics" `
    -Method Get `
    -Headers $headers

Write-Host "`n📈 Final Results:" -ForegroundColor Green
Write-Host "  Total transactions: $($analytics.transaction_count)" -ForegroundColor White
Write-Host "  Total sent: $$($analytics.total_sent)" -ForegroundColor White
Write-Host "  Total received: $$($analytics.total_received)" -ForegroundColor White

Write-Host "`n" + ("=" * 40) -ForegroundColor DarkGray
Write-Host "✅ Demo completed successfully!" -ForegroundColor Green
