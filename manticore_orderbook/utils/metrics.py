"""
Metrics utilities for the Manticore OrderBook package.

This module contains utilities for tracking latency and performance metrics.
"""

import statistics
import time
from collections import defaultdict, deque
from typing import Dict, List, DefaultDict, Deque

class LatencyRecorder:
    """
    Records and provides statistics on operation latencies.
    """
    
    def __init__(self, max_records: int = 1000):
        """
        Initialize a new LatencyRecorder.
        
        Args:
            max_records: Maximum number of latency records to keep per operation
        """
        self._latencies: DefaultDict[str, Deque[float]] = defaultdict(
            lambda: deque(maxlen=max_records)
        )
    
    def record_latency(self, operation: str, latency: float) -> None:
        """
        Record a latency measurement for an operation.
        
        Args:
            operation: Name of the operation
            latency: Latency in seconds
        """
        self._latencies[operation].append(latency)
    
    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """
        Get latency statistics for all operations.
        
        Returns:
            Dictionary mapping operation names to latency statistics
        """
        stats = {}
        for operation, latencies in self._latencies.items():
            if not latencies:
                continue
                
            # Convert to milliseconds for more readable values
            latencies_ms = [l * 1000 for l in latencies]
            
            op_stats = {
                "avg_ms": statistics.mean(latencies_ms) if latencies_ms else 0,
                "min_ms": min(latencies_ms) if latencies_ms else 0,
                "max_ms": max(latencies_ms) if latencies_ms else 0,
                "p50_ms": statistics.median(latencies_ms) if latencies_ms else 0,
                "count": len(latencies_ms)
            }
            
            # Calculate p95 if we have enough data
            if len(latencies_ms) >= 20:
                op_stats["p95_ms"] = statistics.quantiles(latencies_ms, n=20)[-1]
            else:
                op_stats["p95_ms"] = max(latencies_ms) if latencies_ms else 0
                
            stats[operation] = op_stats
            
        return stats
    
    def clear(self) -> None:
        """
        Clear all latency records.
        """
        self._latencies.clear()


class PerformanceStats:
    """
    Tracks performance statistics for operations over time.
    """
    
    def __init__(self, window_size: int = 10):
        """
        Initialize a new PerformanceStats instance.
        
        Args:
            window_size: Number of time windows to track
        """
        self._start_time = time.time()
        self._window_size = window_size
        self._operation_counts: DefaultDict[str, List[int]] = defaultdict(
            lambda: [0] * window_size
        )
        self._window_times: List[float] = [0] * window_size
        self._current_window = 0
    
    def increment(self, operation: str, count: int = 1) -> None:
        """
        Increment the counter for an operation.
        
        Args:
            operation: Name of the operation
            count: Amount to increment by
        """
        self._check_window()
        self._operation_counts[operation][self._current_window] += count
    
    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Get performance statistics for all operations.
        
        Returns:
            Dictionary mapping operation names to statistics
        """
        self._check_window()
        stats = {}
        
        current_time = time.time()
        elapsed = current_time - self._start_time
        
        for operation, counts in self._operation_counts.items():
            total_count = sum(counts)
            ops_per_second = total_count / elapsed if elapsed > 0 else 0
            
            op_stats = {
                "total": total_count,
                "ops_per_second": ops_per_second
            }
            
            stats[operation] = op_stats
            
        return stats
    
    def _check_window(self) -> None:
        """
        Check if we need to advance to a new time window.
        """
        current_time = time.time()
        window_duration = 1.0  # 1 second windows
        
        elapsed = current_time - self._start_time
        expected_window = int(elapsed / window_duration) % self._window_size
        
        if expected_window != self._current_window:
            # Move to new window
            self._current_window = expected_window
            
            # Reset counts for the new window
            for counts in self._operation_counts.values():
                counts[self._current_window] = 0
                
            # Record window time
            self._window_times[self._current_window] = current_time
    
    def clear(self) -> None:
        """
        Clear all performance statistics.
        """
        self._start_time = time.time()
        self._current_window = 0
        self._operation_counts.clear()
        self._window_times = [0] * self._window_size 