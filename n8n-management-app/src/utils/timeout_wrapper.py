"""
Timeout wrapper utilities for preventing hanging operations
"""

import threading
import time
import signal
from typing import Any, Callable, Optional, Tuple
from functools import wraps

from core.logger import get_logger


class TimeoutError(Exception):
    """Raised when an operation times out"""
    pass


class TimeoutWrapper:
    """Wrapper for adding timeout functionality to operations"""
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.logger = get_logger()
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to add timeout to a function"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.run_with_timeout(func, args, kwargs)
        return wrapper
    
    def run_with_timeout(self, func: Callable, args: tuple = (), kwargs: dict = None) -> Any:
        """Run a function with timeout protection"""
        if kwargs is None:
            kwargs = {}
        
        result = [None]
        exception = [None]
        
        def target():
            try:
                result[0] = func(*args, **kwargs)
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout)
        
        if thread.is_alive():
            self.logger.warning(f"Operation {func.__name__} timed out after {self.timeout} seconds")
            raise TimeoutError(f"Operation timed out after {self.timeout} seconds")
        
        if exception[0]:
            raise exception[0]
        
        return result[0]


def with_timeout(timeout: float = 30.0):
    """Decorator factory for adding timeout to functions"""
    return TimeoutWrapper(timeout)


def run_with_timeout(func: Callable, timeout: float = 30.0, *args, **kwargs) -> Any:
    """Run a function with timeout protection"""
    wrapper = TimeoutWrapper(timeout)
    return wrapper.run_with_timeout(func, args, kwargs)


class DockerOperationTimeout:
    """Specialized timeout wrapper for Docker operations"""
    
    def __init__(self, default_timeout: float = 30.0):
        self.default_timeout = default_timeout
        self.logger = get_logger()
        
        # Different timeouts for different operations
        self.operation_timeouts = {
            'create_container': 60.0,
            'start_container': 30.0,
            'stop_container': 30.0,
            'restart_container': 45.0,
            'remove_container': 30.0,
            'get_container_status': 10.0,
            'get_container_logs': 15.0,
            'get_container_stats': 10.0,
            'pull_image': 300.0,  # 5 minutes for image pulls
            'list_containers': 10.0,
            'list_images': 10.0,
            'cleanup_resources': 120.0,  # 2 minutes for cleanup
            'ping': 5.0,
            'info': 10.0,
        }
    
    def get_timeout(self, operation: str) -> float:
        """Get timeout for specific operation"""
        return self.operation_timeouts.get(operation, self.default_timeout)
    
    def wrap_operation(self, operation: str, func: Callable, *args, **kwargs) -> Any:
        """Wrap a Docker operation with appropriate timeout"""
        timeout = self.get_timeout(operation)
        
        try:
            return run_with_timeout(func, timeout, *args, **kwargs)
        except TimeoutError as e:
            self.logger.error(f"Docker operation '{operation}' timed out: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Docker operation '{operation}' failed: {e}")
            raise


# Global instance for Docker operations
docker_timeout = DockerOperationTimeout()