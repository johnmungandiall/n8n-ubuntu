"""
GUI utility functions for safe operations and deferred initialization
"""

import tkinter as tk
from typing import Callable, Any
import threading
import time
from functools import wraps

from core.logger import get_logger


class DeferredInitializer:
    """Handles deferred initialization of GUI components to prevent blocking"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.logger = get_logger()
        self.initialization_queue = []
        self.initialized = False
    
    def add_deferred_task(self, task: Callable, delay_ms: int = 100):
        """Add a task to be executed after GUI is fully initialized"""
        self.initialization_queue.append((task, delay_ms))
    
    def start_initialization(self):
        """Start the deferred initialization process"""
        if self.initialized:
            return
        
        self.initialized = True
        self.logger.debug("Starting deferred GUI initialization")
        
        # Schedule tasks with increasing delays to prevent blocking
        current_delay = 100
        for task, delay_ms in self.initialization_queue:
            self.root.after(current_delay, self._safe_execute_task, task)
            current_delay += delay_ms
    
    def _safe_execute_task(self, task: Callable):
        """Safely execute a deferred task with error handling"""
        try:
            if self.root.winfo_exists():
                task()
        except tk.TclError:
            # Widget destroyed
            pass
        except Exception as e:
            self.logger.error(f"Error in deferred task: {e}")


def safe_gui_operation(func: Callable) -> Callable:
    """Decorator to make GUI operations safe from widget destruction"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            if hasattr(self, 'winfo_exists') and self.winfo_exists():
                return func(self, *args, **kwargs)
            elif hasattr(self, 'root') and hasattr(self.root, 'winfo_exists') and self.root.winfo_exists():
                return func(self, *args, **kwargs)
        except tk.TclError:
            # Widget has been destroyed
            pass
        except Exception as e:
            logger = get_logger()
            logger.error(f"Error in GUI operation {func.__name__}: {e}")
    return wrapper


def create_loading_placeholder(parent: tk.Widget, text: str = "Loading...") -> tk.Label:
    """Create a loading placeholder widget"""
    placeholder = tk.Label(parent, text=text, fg="gray", font=("Arial", 10, "italic"))
    return placeholder


class ResponsiveThread:
    """A thread wrapper that can be interrupted more responsively"""
    
    def __init__(self, target: Callable, daemon: bool = True):
        self.target = target
        self.daemon = daemon
        self.thread = None
        self.running = False
        self.logger = get_logger()
    
    def start(self):
        """Start the thread"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_wrapper, daemon=self.daemon)
        self.thread.start()
    
    def stop(self):
        """Stop the thread"""
        self.running = False
    
    def _run_wrapper(self):
        """Wrapper that handles the thread execution"""
        try:
            self.target()
        except Exception as e:
            self.logger.error(f"Error in responsive thread: {e}")
        finally:
            self.running = False
    
    def is_running(self) -> bool:
        """Check if thread is running"""
        return self.running and self.thread and self.thread.is_alive()


def responsive_sleep(duration: float, check_interval: float = 0.1, stop_condition: Callable = None):
    """Sleep that can be interrupted by a stop condition"""
    elapsed = 0.0
    while elapsed < duration:
        if stop_condition and stop_condition():
            break
        time.sleep(min(check_interval, duration - elapsed))
        elapsed += check_interval