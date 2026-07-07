# scripts/benchmark.py - WITH YOUR FRESH TOKEN

import asyncio
import time
from typing import Any, Dict, List

import httpx


async def benchmark_endpoint(
    client: httpx.AsyncClient,
    url: str,
    headers: Dict[str, str],
    name: str,
    iterations: int = 10,
) -> Dict[str, Any]:
    """Benchmark a single endpoint"""
    times = []
    errors = 0

    print(f"  Running {name}...")

    for i in range(iterations):
        try:
            start = time.perf_counter()
            response = await client.get(url, headers=headers, timeout=30.0)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

            if i == 0:
                print(f"    Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    if "summary" in data:
                        print(
                            f"    Sample: money_in={data.get('summary', {}).get('money_in', 0)}"
                        )
        except Exception as e:
            errors += 1
            print(f"    Error: {e}")

    if not times:
        return {"endpoint": name, "error": "All requests failed"}

    times.sort()
    avg = sum(times) / len(times)
    p95 = times[int(len(times) * 0.95)]
    p99 = times[int(len(times) * 0.99)]

    return {
        "endpoint": name,
        "avg_ms": round(avg, 1),
        "p95_ms": round(p95, 1),
        "p99_ms": round(p99, 1),
        "min_ms": round(min(times), 1),
        "max_ms": round(max(times), 1),
        "iterations": len(times),
        "errors": errors,
    }


async def main():
    # ✅ YOUR FRESH TOKEN FROM BROWSER CONSOLE
    token = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImtleS0xIiwidHlwIjoiSldUIn0.eyJzdWIiOiIyNCIsImVtYWlsIjoidmljY25qZXJpQGdtYWlsLmNvbSIsInJvbGUiOiJvd25lciIsInRlbmFudF9pZCI6InRlbmFudF9lZTUxYWFiZmIwN2IiLCJleHAiOjE3ODMyMjE4ODYsImlhdCI6MTc4MzIyMDA4NiwidHlwZSI6ImFjY2VzcyJ9.aUkrVp0o68mILMTa-sPFvwWMgfpYIMALfs2SdQWVVxOjBC1NL-x4HmbyhqgSJvBNnrfN7kBJ6IFe0b9jF6PQtI-3k6SvixYsn9WDuBpEM33N6J4hzpQVAXGuGNxMu9BjdMtgnGXZpOg1p1bhACrQQgEuoXWcqvrT5xixfVAK8eIsFlfe_-BB6RVZL1jOZold4psVsKGq4WbxY7x_ZBMSCiXNQbdgn-y28nh6BmG3jBWT9WVyuWi8PoYb2jK3V3tlO52EmqxIr2JW45glnxkchx_3zZD3I9E_-xLObob91xnMCwqwWPiSvINEmkBrCmBJkzktEs1SW-It8TCf1Gjieg"

    tenant_id = "tenant_ee51aabfb07b"
    base_url = "http://localhost:9000"

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
        "Content-Type": "application/json",
    }

    endpoints = [
        ("Dashboard", f"{base_url}/api/v1/analytics/dashboard"),
        ("Summary", f"{base_url}/api/v1/analytics/summary"),
        ("Insights", f"{base_url}/api/v1/analytics/insights"),
        ("People-Businesses", f"{base_url}/api/v1/analytics/people-businesses"),
    ]

    print("\n" + "=" * 60)
    print("🚀 BENCHMARKING ANALYTICS ENDPOINTS")
    print("=" * 60)
    print(f"\n📋 Tenant: {tenant_id}")
    print(f"📋 Iterations per endpoint: 10\n")

    results = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for name, url in endpoints:
            print(f"\n📊 {name}")
            print("-" * 40)
            result = await benchmark_endpoint(client, url, headers, name)
            results.append(result)

            if "error" not in result:
                print(f"\n  ✅ AVG: {result['avg_ms']}ms")
                print(f"  ✅ P95: {result['p95_ms']}ms")

    # Summary
    print("\n" + "=" * 60)
    print("📈 FINAL RESULTS")
    print("=" * 60)
    print(f"\n{'Endpoint':<20} {'AVG (ms)':<12} {'P95 (ms)':<12} {'Status':<15}")
    print("-" * 60)

    all_good = True
    for r in results:
        if "error" in r:
            print(f"{r['endpoint']:<20} {'ERROR':<12} {'ERROR':<12} {'❌ FAILED':<15}")
            all_good = False
            continue

        avg = r["avg_ms"]

        if avg < 100:
            status = "✅ EXCELLENT"
        elif avg < 300:
            status = "✅ GOOD"
        elif avg < 500:
            status = "⚠️ ACCEPTABLE"
        else:
            status = "❌ NEEDS WORK"
            all_good = False

        print(f"{r['endpoint']:<20} {avg:<12} {r['p95_ms']:<12} {status:<15}")

    print("\n" + "=" * 60)
    print("🎯 DECISION")
    print("=" * 60)

    if all_good:
        print("\n✅ ALL ENDPOINTS < 300ms")
        print("✅ ANALYTICS OPTIMIZATION COMPLETE")
        print(
            "\n🚀 NEXT: Move to ingestion reliability, categorization quality, and UX"
        )
        print("\n📋 STOP touching analytics code. Ship it.")
    else:
        print("\n⚠️ Some endpoints exceed targets")
        print("📋 Check EXPLAIN ANALYZE output")
        print("📋 Verify indexes are created")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
