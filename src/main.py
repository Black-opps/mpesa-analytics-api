"""
M-PESA Analytics API Gateway
Unified API Gateway for 10-Microservice M-PESA SaaS Platform
"""
from fastapi import FastAPI, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import logging
import asyncio
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="M-PESA Analytics API Gateway",
    description="Unified API Gateway for 10-Microservice M-PESA SaaS Platform",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
SERVICES = {
    "auth": "http://localhost:8001",
    "tenant": "http://localhost:8002",
    "billing": "http://localhost:8008",
    "payment": "http://localhost:8007",
    "parser": "http://localhost:8004",
    "categorizer": "http://localhost:8009",
    "cashflow": "http://localhost:8005",
    "webhook": "http://localhost:8010",
    "analytics": "http://localhost:8000",
}


async def fetch_service_data(
    client: httpx.AsyncClient, 
    service_name: str, 
    endpoint: str, 
    headers: Dict[str, str]
) -> Optional[Any]:
    """Fetch data from a microservice safely."""
    service_url = SERVICES.get(service_name)
    if not service_url:
        logger.warning(f"Service {service_name} not found in SERVICES")
        return None

    url = f"{service_url}/{endpoint.lstrip('/')}"

    try:
        response = await client.get(url, headers=headers, timeout=5.0)
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Service {service_name} returned {response.status_code} for {endpoint}")
            return None
    except httpx.TimeoutException:
        logger.warning(f"Timeout calling {service_name}/{endpoint}")
        return None
    except Exception as e:
        logger.error(f"Error calling {service_name}/{endpoint}: {e}")
        return None


async def proxy_request(
    request: Optional[Request], 
    service_name: str, 
    path: str, 
    method: str = None
) -> JSONResponse:
    """
    Forward request to the appropriate microservice.
    Handles both real requests and None (for ping/test endpoints).
    """
    service_url = SERVICES.get(service_name)
    if not service_url:
        return JSONResponse(
            status_code=404,
            content={"error": f"Service {service_name} not found"}
        )
    
    target_url = f"{service_url}/{path.lstrip('/')}"
    method = method or (request.method if request else "GET")
    
    # Prepare headers safely
    headers = {}
    if request:
        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in ["host", "content-length"]
        }
    
    # Get request body safely
    body = await request.body() if request else None
    
    # Get query params safely
    params = request.query_params if request else None
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=body,
                params=params
            )
            
            try:
                content = response.json()
            except:
                content = response.text
            
            return JSONResponse(
                status_code=response.status_code,
                content=content
            )
    except httpx.ConnectError:
        return JSONResponse(
            status_code=503,
            content={"error": f"Service {service_name} is unavailable"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# ==================== Root & Health ====================

@app.get("/", tags=["default"], operation_id="root")
async def root():
    return {
        "service": "M-PESA Analytics API Gateway",
        "version": "2.0.0",
        "description": "Unified API Gateway for 10-Microservice M-PESA SaaS Platform",
        "services": list(SERVICES.keys()),
        "docs": "/docs"
    }


@app.get("/health", tags=["default"], operation_id="health_check")
async def health_check():
    return {"status": "healthy", "service": "API Gateway"}


# ==================== Dashboard Aggregator ====================

@app.get("/api/v1/dashboard/overview", operation_id="dashboard_overview")
async def dashboard_overview(request: Request):
    """
    Aggregated dashboard endpoint for the React frontend.
    Returns summary, customers, cashflow, and insights in one request.
    """
    tenant_id = request.headers.get("X-Tenant-ID", "default")
    
    # Prepare headers for downstream services
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ["host", "content-length"]
    }

    async with httpx.AsyncClient( timeout=httpx.Timeout(5.0, connect=2.0)) as client:
        # Fetch all data in parallel
        summary_task = fetch_service_data(
            client, "analytics", f"api/v1/analytics/summary/{tenant_id}", headers
        )
        customers_task = fetch_service_data(
            client, "analytics", f"api/v1/analytics/customers/{tenant_id}", headers
        )
        insights_task = fetch_service_data(
            client, "analytics", f"api/v1/analytics/insights/{tenant_id}", headers
        )
        cashflow_task = fetch_service_data(
            client, "cashflow", "api/v1/cashflow/overview", headers
        )

        # Execute all fetches in parallel
        summary, customers, insights, cashflow = await asyncio.gather(
            summary_task, customers_task, insights_task, cashflow_task
        )

    # Build response with fallbacks
    return JSONResponse(
        content={
            "summary": summary or {
                "total_transactions": 0,
                "total_amount": 0,
                "average_transaction": 0,
                "active_days": 0
            },
            "customers": customers or {
                "total_customers": 0,
                "top_customers": []
            },
            "insights": insights or [],
            "cashflow": cashflow or {
                "total_inflow": 0,
                "total_outflow": 0,
                "net_cashflow": 0,
                "trend": []
            }
        }
    )


# ==================== Authentication ====================

@app.api_route(
    "/api/v1/auth/{path:path}", 
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"], 
    tags=["Authentication"],
    operation_id="proxy_auth"
)
async def proxy_auth(request: Request, path: str):
    # Forward directly to auth service (no extra /api/v1/auth prefix)
    return await proxy_request(request, "auth", path)


@app.api_route(
    "/api/v1/auth", 
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    operation_id="proxy_auth_root"
)
async def proxy_auth_root(request: Request):
    return await proxy_request(request, "auth", "")


# ==================== Tenant Management ====================

@app.api_route(
    "/api/v1/tenants/{path:path}", 
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"], 
    tags=["Tenant Management"],
    operation_id="proxy_tenant"
)
async def proxy_tenant(request: Request, path: str):
    return await proxy_request(request, "tenant", path)


@app.api_route(
    "/api/v1/tenants", 
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    operation_id="proxy_tenant_root"
)
async def proxy_tenant_root(request: Request):
    return await proxy_request(request, "tenant", "")


# ==================== Billing ====================

@app.api_route(
    "/api/v1/billing/{path:path}", 
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"], 
    tags=["Billing"],
    operation_id="proxy_billing"
)
async def proxy_billing(request: Request, path: str):
    return await proxy_request(request, "billing", path)


# ==================== Payments ====================

@app.api_route(
    "/api/v1/payments/{path:path}", 
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"], 
    tags=["Payments"],
    operation_id="proxy_payment"
)
async def proxy_payment(request: Request, path: str):
    return await proxy_request(request, "payment", path)


# ==================== Transaction Parser ====================

@app.post("/api/v1/parser/upload", tags=["Transaction Parser"], operation_id="upload_statement")
async def upload_statement(request: Request, file: UploadFile = File(...)):
    service_url = SERVICES.get("parser")
    target_url = f"{service_url}/api/v1/parser/upload"
    
    auth_header = request.headers.get("Authorization")
    headers = {"Authorization": auth_header} if auth_header else {}
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                target_url,
                files={"file": (file.filename, await file.read(), file.content_type)},
                headers=headers
            )
            return JSONResponse(status_code=response.status_code, content=response.json())
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.api_route(
    "/api/v1/parser/{path:path}", 
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    operation_id="proxy_parser"
)
async def proxy_parser(request: Request, path: str):
    return await proxy_request(request, "parser", path)


# ==================== Transaction Categorizer ====================

@app.post("/api/v1/categorize/", tags=["Transaction Categorizer"], operation_id="categorize_transactions")
async def categorize_transactions(request: Request):
    return await proxy_request(request, "categorizer", "api/v1/categorize/")


@app.post("/api/v1/categorize/single", tags=["Transaction Categorizer"], operation_id="categorize_single")
async def categorize_single(request: Request):
    return await proxy_request(request, "categorizer", "api/v1/categorize/single")


@app.api_route(
    "/api/v1/categorizer/{path:path}", 
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    operation_id="proxy_categorizer"
)
async def proxy_categorizer(request: Request, path: str):
    return await proxy_request(request, "categorizer", path)


# ==================== Cashflow Analytics ====================

@app.get("/api/v1/analytics/summary/{tenant_id}", tags=["Cashflow Analytics"], operation_id="get_analytics_summary")
async def get_analytics_summary(tenant_id: str, request: Request):
    return await proxy_request(request, "cashflow", f"api/v1/analytics/summary/{tenant_id}")


@app.post("/api/v1/analytics/analyze", tags=["Cashflow Analytics"], operation_id="analyze_cashflow")
async def analyze_cashflow(request: Request):
    return await proxy_request(request, "cashflow", "api/v1/analytics/analyze")


@app.post("/api/v1/analytics/patterns", tags=["Cashflow Analytics"], operation_id="detect_patterns")
async def detect_patterns(request: Request):
    return await proxy_request(request, "cashflow", "api/v1/analytics/patterns")


@app.get("/api/v1/analytics/ping", tags=["Cashflow Analytics"], operation_id="analytics_ping")
async def analytics_ping():
    """Ping cashflow analytics service."""
    return await proxy_request(None, "cashflow", "api/v1/analytics/ping")


# ==================== Webhooks ====================

@app.get("/api/v1/webhooks/endpoints", tags=["Webhooks"], operation_id="list_webhooks")
async def list_webhooks(request: Request):
    return await proxy_request(request, "webhook", "api/v1/webhooks/endpoints")


@app.post("/api/v1/webhooks/endpoints", tags=["Webhooks"], operation_id="create_webhook")
async def create_webhook(request: Request):
    return await proxy_request(request, "webhook", "api/v1/webhooks/endpoints")


@app.api_route(
    "/api/v1/webhooks/{path:path}", 
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    operation_id="proxy_webhook"
)
async def proxy_webhook(request: Request, path: str):
    return await proxy_request(request, "webhook", path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)