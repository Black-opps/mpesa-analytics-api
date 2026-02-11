# ================================================
# M-PESA ANALYTICS API - USAGE EXAMPLES
# ================================================

# 1. CONNECT TO API
$connection = @{
    BaseUrl = "http://localhost:8000"
    Headers = @{
        "Authorization" = "Bearer YOUR_TOKEN_HERE"
        "Content-Type" = "application/json"
    }
}

# 2. ADD SINGLE TRANSACTION
$transaction = @(
    @{
        transaction_id = "MPE123456789"
        amount = 1500.00
        transaction_type = "Pay Bill"
        counterparty = "123456"
        timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
    }
) | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "$($connection.BaseUrl)/transactions" `
    -Method Post `
    -Headers $connection.Headers `
    -Body $transaction

# 3. GET ANALYTICS
$analytics = Invoke-RestMethod -Uri "$($connection.BaseUrl)/analytics" `
    -Method Get `
    -Headers $connection.Headers

# Analytics returns:
# {
#   "total_sent": 0,
#   "total_received": 0,
#   "transaction_count": 0
#   // Additional fields may be present
# }

# 4. GET USER INFO
$userInfo = Invoke-RestMethod -Uri "$($connection.BaseUrl)/me" `
    -Method Get `
    -Headers $connection.Headers

# ================================================
# BULK IMPORT FROM CSV
# ================================================

function Import-MpesaFromCsv {
    param(
        [string]$CsvPath,
        [hashtable]$Connection
    )
    
    $data = Import-Csv -Path $CsvPath
    
    foreach ($row in $data) {
        $transaction = @(
            @{
                transaction_id = $row.ReceiptNo
                amount = [double]$row.Amount
                transaction_type = $row.'Transaction Type'
                counterparty = $row.'Counter Party Number'
                timestamp = [datetime]::ParseExact(
                    "$($row.Date) $($row.Time)",
                    "M/d/yyyy HH:mm:ss",
                    $null
                ).ToString("yyyy-MM-ddTHH:mm:ss")
            }
        ) | ConvertTo-Json -Depth 3
        
        try {
            Invoke-RestMethod -Uri "$($connection.BaseUrl)/transactions" `
                -Method Post `
                -Headers $connection.Headers `
                -Body $transaction
            
            Write-Host "Imported: $($row.ReceiptNo)" -ForegroundColor Green
        } catch {
            Write-Host "Failed: $($row.ReceiptNo) - $($_.Exception.Message)" -ForegroundColor Red
        }
        
        Start-Sleep -Milliseconds 100
    }
}

# ================================================
# DASHBOARD REPORT
# ================================================

function Get-MpesaDashboard {
    param([hashtable]$Connection)
    
    $analytics = Invoke-RestMethod -Uri "$($connection.BaseUrl)/analytics" `
        -Method Get `
        -Headers $connection.Headers
    
    $report = @"
    M-PESA ANALYTICS DASHBOARD
    ==========================
    Total Transactions: $($analytics.transaction_count)
    Total Sent: KES $($analytics.total_sent.ToString('N2'))
    Total Received: KES $($analytics.total_received.ToString('N2'))
    Net Balance: KES $(($analytics.total_received - $analytics.total_sent).ToString('N2'))
    
    Transaction Types:
    $(if ($analytics.transactions_by_type) {
        $analytics.transactions_by_type.PSObject.Properties | ForEach-Object {
            "  - $($_.Name): $($_.Value)"
        } -join "`n"
    })
"@
    
    return $report
}
