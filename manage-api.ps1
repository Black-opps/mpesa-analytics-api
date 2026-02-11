# MPesa API Management
Write-Host "MPesa Analytics API Management" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Start API: docker-compose up -d" -ForegroundColor Yellow
Write-Host "2. Stop API: docker-compose down" -ForegroundColor Yellow
Write-Host "3. View logs: docker-compose logs -f" -ForegroundColor Yellow
Write-Host "4. Rebuild: docker-compose up -d --build" -ForegroundColor Yellow
Write-Host "5. Test: curl http://localhost:8000/" -ForegroundColor Yellow
Write-Host ""
Write-Host "API: http://localhost:8000" -ForegroundColor Green
Write-Host "Docs: http://localhost:8000/docs" -ForegroundColor Green
