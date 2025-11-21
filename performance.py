"""
Performance optimization and parallel processing for Cascade REST CLI
"""

import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable, Tuple
import threading
from functools import wraps

from config import PARALLEL_WORKERS, REQUEST_TIMEOUT, CONNECTION_POOL_SIZE
from logging_config import logger


class PerformanceMonitor:
    """Monitor and track performance metrics"""

    def __init__(self):
        self.metrics = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "total_time": 0,
            "average_time": 0,
            "operations_per_second": 0,
        }
        self.start_time = None
        self.lock = threading.Lock()

    def start_timing(self):
        """Start timing an operation"""
        self.start_time = time.time()

    def end_timing(self, success: bool = True):
        """End timing and update metrics"""
        if self.start_time is None:
            return

        duration = time.time() - self.start_time

        with self.lock:
            self.metrics["total_operations"] += 1
            if success:
                self.metrics["successful_operations"] += 1
            else:
                self.metrics["failed_operations"] += 1

            self.metrics["total_time"] += duration
            self.metrics["average_time"] = (
                self.metrics["total_time"] / self.metrics["total_operations"]
            )

            if self.metrics["total_time"] > 0:
                self.metrics["operations_per_second"] = (
                    self.metrics["total_operations"] / self.metrics["total_time"]
                )

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        with self.lock:
            return self.metrics.copy()

    def reset_metrics(self):
        """Reset all metrics"""
        with self.lock:
            self.metrics = {
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "total_time": 0,
                "average_time": 0,
                "operations_per_second": 0,
            }


def performance_timer(operation_name: str):
    """Decorator to time operations and log performance"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor = PerformanceMonitor()
            monitor.start_timing()

            try:
                logger.log_operation_start(operation_name)
                result = func(*args, **kwargs)
                monitor.end_timing(success=True)
                logger.log_operation_end(operation_name, True)
                return result
            except Exception as e:
                monitor.end_timing(success=False)
                logger.log_operation_end(operation_name, False, error=str(e))
                raise

        return wrapper

    return decorator


class ParallelProcessor:
    """Handle parallel processing of batch operations"""

    def __init__(self, max_workers: int = PARALLEL_WORKERS):
        self.max_workers = max_workers
        self.monitor = PerformanceMonitor()

    def process_batch_parallel(
        self, items: List[Any], process_func: Callable, batch_size: Optional[int] = None
    ) -> List[Any]:
        """Process items in parallel batches"""
        if not items:
            return []

        batch_size = batch_size or (len(items) // self.max_workers) or 1
        batches = [items[i : i + batch_size] for i in range(0, len(items), batch_size)]

        results = []

        logger.log_operation_start(
            "parallel_batch_processing",
            total_items=len(items),
            batch_count=len(batches),
            max_workers=self.max_workers,
        )

        self.monitor.start_timing()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(self._process_batch, batch, process_func): batch
                for batch in batches
            }

            # Collect results as they complete
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    batch_results = future.result()
                    results.extend(batch_results)
                    logger.log_batch_progress(
                        "parallel_batch_processing", len(results), len(items)
                    )
                except Exception as e:
                    logger.log_error(e, {"batch": batch})

        self.monitor.end_timing(success=True)

        logger.log_operation_end(
            "parallel_batch_processing",
            True,
            total_processed=len(results),
            metrics=self.monitor.get_metrics(),
        )

        return results

    def _process_batch(self, batch: List[Any], process_func: Callable) -> List[Any]:
        """Process a single batch of items"""
        results = []
        for item in batch:
            try:
                result = process_func(item)
                results.append(result)
            except Exception as e:
                logger.log_error(e, {"item": item})
                results.append(None)
        return results

    async def process_batch_async(
        self,
        items: List[Any],
        process_func: Callable,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> List[Any]:
        """Process items asynchronously"""
        if not items:
            return []

        if session is None:
            connector = aiohttp.TCPConnector(limit=CONNECTION_POOL_SIZE)
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            session = aiohttp.ClientSession(connector=connector, timeout=timeout)

        logger.log_operation_start("async_batch_processing", total_items=len(items))

        self.monitor.start_timing()

        try:
            # Create semaphore to limit concurrent operations
            semaphore = asyncio.Semaphore(self.max_workers)

            async def process_item_with_semaphore(item):
                async with semaphore:
                    return await self._process_item_async(item, process_func, session)

            # Process all items concurrently
            tasks = [process_item_with_semaphore(item) for item in items]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions
            valid_results = [r for r in results if not isinstance(r, Exception)]
            exceptions = [r for r in results if isinstance(r, Exception)]

            for exc in exceptions:
                logger.log_error(exc, {"async_operation": True})

            self.monitor.end_timing(success=True)

            logger.log_operation_end(
                "async_batch_processing",
                True,
                valid_results=len(valid_results),
                exceptions=len(exceptions),
                metrics=self.monitor.get_metrics(),
            )

            return valid_results

        finally:
            if session and not session.closed:
                await session.close()

    async def _process_item_async(
        self, item: Any, process_func: Callable, session: aiohttp.ClientSession
    ) -> Any:
        """Process a single item asynchronously"""
        try:
            # If process_func is async, await it
            if asyncio.iscoroutinefunction(process_func):
                return await process_func(item, session)
            else:
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, process_func, item)
        except Exception as e:
            logger.log_error(e, {"item": item, "async": True})
            raise


class ConnectionPool:
    """Manage HTTP connection pooling for better performance"""

    def __init__(self, max_connections: int = CONNECTION_POOL_SIZE):
        self.max_connections = max_connections
        self.session = None
        self._lock = threading.Lock()

    def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with connection pooling"""
        if self.session is None or self.session.closed:
            with self._lock:
                if self.session is None or self.session.closed:
                    connector = aiohttp.TCPConnector(
                        limit=self.max_connections,
                        limit_per_host=self.max_connections // 2,
                        keepalive_timeout=30,
                        enable_cleanup_closed=True,
                    )
                    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                    self.session = aiohttp.ClientSession(
                        connector=connector, timeout=timeout
                    )
        return self.session

    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()


class CacheManager:
    """Simple in-memory cache for API responses"""

    def __init__(self, ttl: int = 300):  # 5 minutes default
        self.cache = {}
        self.ttl = ttl
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        with self._lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    return value
                else:
                    del self.cache[key]
        return None

    def set(self, key: str, value: Any):
        """Set cached value"""
        with self._lock:
            self.cache[key] = (value, time.time())

    def clear(self):
        """Clear all cached values"""
        with self._lock:
            self.cache.clear()

    def cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        with self._lock:
            expired_keys = [
                key
                for key, (value, timestamp) in self.cache.items()
                if current_time - timestamp >= self.ttl
            ]
            for key in expired_keys:
                del self.cache[key]

        return len(expired_keys)


# Global instances
performance_monitor = PerformanceMonitor()
parallel_processor = ParallelProcessor()
connection_pool = ConnectionPool()
cache_manager = CacheManager()
