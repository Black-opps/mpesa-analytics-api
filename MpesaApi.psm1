# Save these functions in your PowerShell profile or module

function Connect-MpesaApi {
    param(
        [string]$BaseUrl = "http://localhost:8000",
        [string]$Username = "test@example.com",
        [string]$Password = "test123"
    )
    
    $token = Invoke-RestMethod -Uri "$BaseUrl/auth/login" `
        -Method Post `
        -Body @{username=$Username; password=$Password}
    
    return @{
        BaseUrl = $BaseUrl
        Headers = @{
            "Authorization" = "Bearer $($token.access_token)"
            "Content-Type" = "application/json"
        }
    }
}

function Add-MpesaTransaction {
    param(
        [hashtable]$Connection,
        [string]$TransactionId,
        [double]$Amount,
        [string]$TransactionType,
        [string]$Counterparty,
        [datetime]$Timestamp
    )
    
    $tx = @(
        @{
            transaction_id = $TransactionId
            amount = $Amount
            transaction_type = $TransactionType
            counterparty = $Counterparty
            timestamp = $Timestamp.ToString("yyyy-MM-ddTHH:mm:ss")
        }
    ) | ConvertTo-Json -Depth 3
    
    return Invoke-RestMethod -Uri "$($Connection.BaseUrl)/transactions" `
        -Method Post `
        -Headers $Connection.Headers `
        -Body $tx
}

function Get-MpesaAnalytics {
    param(
        [hashtable]$Connection,
        [datetime]$StartDate,
        [datetime]$EndDate
    )
    
    $url = "$($Connection.BaseUrl)/analytics"
    $params = @()
    
    if ($StartDate) { $params += "start_date=$($StartDate.ToString('yyyy-MM-dd'))" }
    if ($EndDate) { $params += "end_date=$($EndDate.ToString('yyyy-MM-dd'))" }
    
    if ($params.Count -gt 0) {
        $url += "?" + ($params -join "&")
    }
    
    return Invoke-RestMethod -Uri $url `
        -Method Get `
        -Headers $Connection.Headers
}

function Get-MpesaUserInfo {
    param([hashtable]$Connection)
    return Invoke-RestMethod -Uri "$($Connection.BaseUrl)/me" `
        -Method Get `
        -Headers $Connection.Headers
}
