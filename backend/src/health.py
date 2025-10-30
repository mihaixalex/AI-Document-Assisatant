"""Health check and monitoring endpoints for the backend.

This module provides:
1. Health check endpoint for container orchestration
2. Readiness checks for dependencies (database, LLM providers)
3. Metrics endpoints for monitoring
4. Version information
"""

import asyncio
import os
import sys
import time
from typing import Any

from langchain_openai import ChatOpenAI

# Version information
VERSION = "1.0.0"
MIGRATION_PHASE = "Phase 4 - Integration & Deployment"


class HealthChecker:
    """Health and readiness checker for the backend."""

    def __init__(self) -> None:
        """Initialize health checker."""
        self.start_time = time.time()

    def get_basic_health(self) -> dict[str, Any]:
        """
        Get basic health status.

        Returns:
            Dict with status, version, and uptime.
        """
        uptime = time.time() - self.start_time

        return {
            "status": "healthy",
            "version": VERSION,
            "migration_phase": MIGRATION_PHASE,
            "uptime_seconds": round(uptime, 2),
            "python_version": sys.version.split()[0],
        }

    async def check_openai_connection(self) -> dict[str, Any]:
        """
        Check OpenAI API connectivity.

        Returns:
            Dict with connection status and latency.
        """
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            return {
                "service": "openai",
                "status": "not_configured",
                "message": "OPENAI_API_KEY not set",
            }

        try:
            start = time.time()

            # Quick test with minimal tokens
            model = ChatOpenAI(model="gpt-4o-mini", max_tokens=1)
            await model.ainvoke("test")

            latency = time.time() - start

            return {
                "service": "openai",
                "status": "connected",
                "latency_ms": round(latency * 1000, 2),
            }
        except Exception as e:
            return {
                "service": "openai",
                "status": "error",
                "message": str(e),
            }

    async def check_supabase_connection(self) -> dict[str, Any]:
        """
        Check Supabase connectivity.

        Returns:
            Dict with connection status.
        """
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            return {
                "service": "supabase",
                "status": "not_configured",
                "message": "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set",
            }

        try:
            from supabase import create_client

            start = time.time()

            # Create client and test connection
            supabase = create_client(supabase_url, supabase_key)

            # Simple health check query
            # Note: This assumes a 'documents' table exists
            result = supabase.table("documents").select("id").limit(1).execute()

            latency = time.time() - start

            return {
                "service": "supabase",
                "status": "connected",
                "latency_ms": round(latency * 1000, 2),
            }
        except Exception as e:
            return {
                "service": "supabase",
                "status": "error",
                "message": str(e),
            }

    async def get_readiness_status(self) -> dict[str, Any]:
        """
        Get comprehensive readiness status.

        Checks all external dependencies.

        Returns:
            Dict with overall readiness and individual service statuses.
        """
        checks = await asyncio.gather(
            self.check_openai_connection(),
            self.check_supabase_connection(),
            return_exceptions=True,
        )

        services = []
        all_ready = True

        for check in checks:
            if isinstance(check, Exception):
                services.append({
                    "service": "unknown",
                    "status": "error",
                    "message": str(check),
                })
                all_ready = False
            else:
                services.append(check)
                if check["status"] != "connected":
                    all_ready = False

        return {
            "ready": all_ready,
            "services": services,
            "timestamp": time.time(),
        }

    def get_metrics(self) -> dict[str, Any]:
        """
        Get basic metrics for monitoring.

        Returns:
            Dict with runtime metrics.
        """
        uptime = time.time() - self.start_time

        return {
            "uptime_seconds": round(uptime, 2),
            "version": VERSION,
            "migration_phase": MIGRATION_PHASE,
            "timestamp": time.time(),
        }


# Global health checker instance
health_checker = HealthChecker()


async def health_check() -> dict[str, Any]:
    """
    Basic health check endpoint.

    Returns:
        Basic health status.
    """
    return health_checker.get_basic_health()


async def readiness_check() -> dict[str, Any]:
    """
    Readiness check endpoint.

    Returns:
        Comprehensive readiness status.
    """
    return await health_checker.get_readiness_status()


async def metrics() -> dict[str, Any]:
    """
    Metrics endpoint.

    Returns:
        Runtime metrics.
    """
    return health_checker.get_metrics()


# Example usage for testing
if __name__ == "__main__":
    import asyncio

    async def main() -> None:
        print("=== Health Check ===")
        health = await health_check()
        print(health)

        print("\n=== Readiness Check ===")
        readiness = await readiness_check()
        print(readiness)

        print("\n=== Metrics ===")
        metrics_data = await metrics()
        print(metrics_data)

    asyncio.run(main())
