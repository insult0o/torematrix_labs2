#!/usr/bin/env python3
"""
Health check script for TORE Matrix services.

Verifies that all required services are running and accessible
before running tests.
"""

import asyncio
import aiohttp
import redis.asyncio as redis
import psycopg2
import time
import sys
import os
from typing import Dict, Any


async def check_redis():
    """Check Redis connection."""
    try:
        redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
        client = await redis.from_url(redis_url)
        await client.ping()
        await client.close()
        return True, "Redis is healthy"
    except Exception as e:
        return False, f"Redis check failed: {e}"


async def check_postgres():
    """Check PostgreSQL connection."""
    try:
        database_url = os.getenv('DATABASE_URL', 
            'postgresql://torematrix:testpass123@postgres:5432/torematrix_test')
        
        # Extract connection parameters
        from urllib.parse import urlparse
        parsed = urlparse(database_url)
        
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],  # Remove leading /
            user=parsed.username,
            password=parsed.password
        )
        
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.close()
        conn.close()
        
        return True, "PostgreSQL is healthy"
    except Exception as e:
        return False, f"PostgreSQL check failed: {e}"


async def check_minio():
    """Check MinIO S3 service."""
    try:
        endpoint = os.getenv('S3_ENDPOINT', 'http://minio:9000')
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{endpoint}/minio/health/live") as resp:
                if resp.status == 200:
                    return True, "MinIO is healthy"
                else:
                    return False, f"MinIO returned status {resp.status}"
    except Exception as e:
        return False, f"MinIO check failed: {e}"


async def check_unstructured():
    """Check Unstructured.io API service."""
    try:
        api_url = os.getenv('UNSTRUCTURED_API_URL', 'http://unstructured:8000')
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{api_url}/general/docs") as resp:
                if resp.status == 200:
                    return True, "Unstructured.io API is healthy"
                else:
                    return False, f"Unstructured.io API returned status {resp.status}"
    except Exception as e:
        return False, f"Unstructured.io API check failed: {e}"


async def check_torematrix_api():
    """Check TORE Matrix API service."""
    try:
        api_url = os.getenv('TEST_API_BASE_URL', 'http://torematrix-api:8080')
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{api_url}/health") as resp:
                if resp.status == 200:
                    return True, "TORE Matrix API is healthy"
                else:
                    return False, f"TORE Matrix API returned status {resp.status}"
    except Exception as e:
        return False, f"TORE Matrix API check failed: {e}"


async def run_health_checks():
    """Run all health checks."""
    checks = {
        'Redis': check_redis,
        'PostgreSQL': check_postgres,
        'MinIO': check_minio,
        'Unstructured.io': check_unstructured,
        'TORE Matrix API': check_torematrix_api
    }
    
    print("Running health checks...")
    print("=" * 50)
    
    results = {}
    all_healthy = True
    
    for service_name, check_func in checks.items():
        print(f"Checking {service_name}...", end=" ")
        
        try:
            healthy, message = await check_func()
            results[service_name] = {'healthy': healthy, 'message': message}
            
            if healthy:
                print("✅ HEALTHY")
            else:
                print("❌ UNHEALTHY")
                all_healthy = False
                
            print(f"  {message}")
            
        except Exception as e:
            print("❌ ERROR")
            print(f"  Unexpected error: {e}")
            results[service_name] = {'healthy': False, 'message': f"Error: {e}"}
            all_healthy = False
        
        print()
    
    print("=" * 50)
    
    if all_healthy:
        print("🎉 All services are healthy!")
        return 0
    else:
        print("⚠️  Some services are unhealthy:")
        for service, result in results.items():
            if not result['healthy']:
                print(f"  - {service}: {result['message']}")
        return 1


async def wait_for_services(timeout: int = 120):
    """Wait for all services to become healthy."""
    print(f"Waiting for services to become healthy (timeout: {timeout}s)...")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        result = await run_health_checks()
        
        if result == 0:
            return 0
        
        print(f"Retrying in 10 seconds... ({int(time.time() - start_time)}s elapsed)")
        await asyncio.sleep(10)
    
    print(f"❌ Timeout after {timeout}s waiting for services")
    return 1


async def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Health check for TORE Matrix services')
    parser.add_argument('--wait', action='store_true', 
                      help='Wait for services to become healthy')
    parser.add_argument('--timeout', type=int, default=120,
                      help='Timeout in seconds when waiting (default: 120)')
    
    args = parser.parse_args()
    
    if args.wait:
        result = await wait_for_services(args.timeout)
    else:
        result = await run_health_checks()
    
    sys.exit(result)


if __name__ == '__main__':
    asyncio.run(main())