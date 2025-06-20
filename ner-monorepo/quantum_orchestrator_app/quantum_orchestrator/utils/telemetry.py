"""
Telemetry: Performance monitoring utilities for the Quantum Orchestrator.

Tracks and reports on system performance metrics.
"""

import time
import threading
from typing import Dict, Any, List


class Telemetry:
    """
    Telemetry class for tracking performance metrics.

    Monitors execution times, success rates, and other performance indicators.
    """

    def __init__(self):
        """Initialize the telemetry system."""
        self.start_time = time.time()
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.execution_times: List[float] = []
        self.max_execution_times = 100  # Keep only the last 100 execution times
        self.lock = threading.RLock()

        # Performance metrics
        self.average_execution_time = 0.0
        self.success_rate = 0.0

    def record_start_execution(self) -> None:
        """Record the start of an execution."""
        with self.lock:
            self.execution_count += 1

    def record_execution_complete(
        self, instruction_type: str, execution_time: float, success: bool
    ) -> None:
        """
        Record the completion of an execution.

        Args:
            instruction_type: Type of instruction executed
            execution_time: Time taken for execution
            success: Whether the execution was successful
        """
        with self.lock:
            # Update success/failure counts
            if success:
                self.success_count += 1
            else:
                self.failure_count += 1

            # Record execution time
            self.execution_times.append(execution_time)

            # Limit the size of execution_times list
            if len(self.execution_times) > self.max_execution_times:
                self.execution_times.pop(0)

            # Update metrics
            self._update_metrics()

    def _update_metrics(self) -> None:
        """Update performance metrics."""
        # Calculate average execution time
        if self.execution_times:
            self.average_execution_time = sum(self.execution_times) / len(
                self.execution_times
            )
        else:
            self.average_execution_time = 0.0

        # Calculate success rate
        total = self.success_count + self.failure_count
        if total > 0:
            self.success_rate = self.success_count / total
        else:
            self.success_rate = 0.0

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.

        Returns:
            Dict containing performance metrics
        """
        with self.lock:
            return {
                "execution_count": self.execution_count,
                "success_count": self.success_count,
                "failure_count": self.failure_count,
                "average_execution_time": self.average_execution_time,
                "success_rate": self.success_rate,
                "uptime": time.time() - self.start_time,
            }

    def reset(self) -> None:
        """Reset all metrics except for start_time."""
        with self.lock:
            self.execution_count = 0
            self.success_count = 0
            self.failure_count = 0
            self.execution_times = []
            self.average_execution_time = 0.0
            self.success_rate = 0.0
