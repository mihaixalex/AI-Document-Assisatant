"""Monitoring and observability utilities.

This module provides:
1. Request/response logging with timing
2. Error tracking and reporting
3. Performance metrics collection
4. LangSmith integration for tracing
"""

import functools
import logging
import os
import time
from typing import Any, Callable, TypeVar

from langchain_core.tracers.langchain import LangChainTracer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Type variable for decorators
F = TypeVar("F", bound=Callable[..., Any])


class PerformanceMonitor:
    """Monitor and track performance metrics."""

    def __init__(self) -> None:
        """Initialize performance monitor."""
        self.metrics: dict[str, list[float]] = {
            "ingestion_latency": [],
            "retrieval_latency": [],
            "llm_latency": [],
            "vector_search_latency": [],
        }

    def record_metric(self, metric_name: str, value: float) -> None:
        """
        Record a performance metric.

        Args:
            metric_name: Name of the metric.
            value: Value to record (typically latency in seconds).
        """
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []

        self.metrics[metric_name].append(value)

        # Keep only last 1000 measurements to prevent memory growth
        if len(self.metrics[metric_name]) > 1000:
            self.metrics[metric_name] = self.metrics[metric_name][-1000:]

        logger.info(f"[METRIC] {metric_name}: {value:.3f}s")

    def get_stats(self, metric_name: str) -> dict[str, float]:
        """
        Get statistics for a metric.

        Args:
            metric_name: Name of the metric.

        Returns:
            Dict with min, max, avg, and count.
        """
        if metric_name not in self.metrics or not self.metrics[metric_name]:
            return {"min": 0, "max": 0, "avg": 0, "count": 0}

        values = self.metrics[metric_name]

        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "count": len(values),
        }

    def get_all_stats(self) -> dict[str, dict[str, float]]:
        """
        Get statistics for all metrics.

        Returns:
            Dict of metric_name -> stats.
        """
        return {name: self.get_stats(name) for name in self.metrics.keys()}


# Global performance monitor
perf_monitor = PerformanceMonitor()


def track_latency(metric_name: str) -> Callable[[F], F]:
    """
    Decorator to track function execution time.

    Args:
        metric_name: Name of the metric to record.

    Returns:
        Decorator function.

    Example:
        @track_latency("my_function_latency")
        async def my_function():
            pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                latency = time.time() - start_time
                perf_monitor.record_metric(metric_name, latency)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                latency = time.time() - start_time
                perf_monitor.record_metric(metric_name, latency)

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


class ErrorTracker:
    """Track and log errors for monitoring."""

    def __init__(self) -> None:
        """Initialize error tracker."""
        self.errors: list[dict[str, Any]] = []

    def record_error(
        self,
        error: Exception,
        context: str = "",
        extra: dict[str, Any] | None = None,
    ) -> None:
        """
        Record an error for tracking.

        Args:
            error: The exception that occurred.
            context: Context about where the error occurred.
            extra: Additional metadata.
        """
        error_data = {
            "type": type(error).__name__,
            "message": str(error),
            "context": context,
            "timestamp": time.time(),
            "extra": extra or {},
        }

        self.errors.append(error_data)

        # Keep only last 100 errors
        if len(self.errors) > 100:
            self.errors = self.errors[-100:]

        logger.error(
            f"[ERROR] {context}: {type(error).__name__} - {str(error)}",
            exc_info=True,
        )

    def get_recent_errors(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent errors.

        Args:
            limit: Maximum number of errors to return.

        Returns:
            List of recent error records.
        """
        return self.errors[-limit:]

    def get_error_counts(self) -> dict[str, int]:
        """
        Get counts of errors by type.

        Returns:
            Dict of error_type -> count.
        """
        counts: dict[str, int] = {}

        for error in self.errors:
            error_type = error["type"]
            counts[error_type] = counts.get(error_type, 0) + 1

        return counts


# Global error tracker
error_tracker = ErrorTracker()


def get_langsmith_tracer() -> LangChainTracer | None:
    """
    Get LangSmith tracer if configured.

    Returns:
        LangChainTracer instance if configured, None otherwise.
    """
    if os.getenv("LANGCHAIN_TRACING_V2") == "true":
        project_name = os.getenv("LANGCHAIN_PROJECT", "ai-pdf-chatbot-python")

        logger.info(f"LangSmith tracing enabled for project: {project_name}")

        return LangChainTracer(project_name=project_name)

    return None


def log_request(operation: str, details: dict[str, Any]) -> None:
    """
    Log a request for observability.

    Args:
        operation: Name of the operation (e.g., "ingestion", "retrieval").
        details: Additional details about the request.
    """
    logger.info(f"[REQUEST] {operation}: {details}")


def log_response(operation: str, success: bool, duration: float) -> None:
    """
    Log a response for observability.

    Args:
        operation: Name of the operation.
        success: Whether the operation succeeded.
        duration: Duration in seconds.
    """
    status = "SUCCESS" if success else "FAILURE"
    logger.info(f"[RESPONSE] {operation}: {status} ({duration:.3f}s)")


# Example usage
if __name__ == "__main__":
    import asyncio

    # Example: Track latency
    @track_latency("example_function")
    async def example_async_function() -> None:
        await asyncio.sleep(0.1)
        print("Function executed")

    # Example: Track errors
    async def example_with_error() -> None:
        try:
            raise ValueError("Example error")
        except Exception as e:
            error_tracker.record_error(
                e,
                context="example_function",
                extra={"user_id": "test-user"},
            )

    async def main() -> None:
        # Test latency tracking
        await example_async_function()
        print(f"Stats: {perf_monitor.get_stats('example_function')}")

        # Test error tracking
        await example_with_error()
        print(f"Recent errors: {error_tracker.get_recent_errors()}")

    asyncio.run(main())
