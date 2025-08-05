"""
Startup window for n8n Management App
Shows a loading screen while the main application initializes
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Callable

from core.logger import get_logger


class StartupWindow:
    """Startup/loading window"""
    
    def __init__(self, on_complete: Callable = None):
        self.logger = get_logger()
        self.on_complete = on_complete
        self.root = None
        self.progress_var = None
        self.status_var = None
        self.completed = False
        
        self._create_window()
    
    def _create_window(self):
        """Create the startup window"""
        self.root = tk.Tk()
        self.root.title("n8n Management App - Starting...")
        self.root.geometry("400x200")
        self.root.resizable(False, False)
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 400) // 2
        y = (self.root.winfo_screenheight() - 200) // 2
        self.root.geometry(f"+{x}+{y}")
        
        # Remove window decorations for splash effect
        self.root.overrideredirect(True)
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # App title
        title_label = ttk.Label(
            main_frame, 
            text="n8n Management App", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Status message
        self.status_var = tk.StringVar()
        self.status_var.set("Initializing...")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.pack(pady=(0, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            main_frame, 
            variable=self.progress_var, 
            maximum=100,
            length=300
        )
        progress_bar.pack(pady=(0, 10))
        
        # Version info
        version_label = ttk.Label(
            main_frame, 
            text="Version 1.0.0", 
            font=("Arial", 8)
        )
        version_label.pack(side=tk.BOTTOM)
        
        # Start initialization
        self.root.after(100, self._start_initialization)
    
    def _start_initialization(self):
        """Start the initialization process"""
        init_thread = threading.Thread(target=self._initialization_worker, daemon=True)
        init_thread.start()
    
    def _initialization_worker(self):
        """Background initialization worker"""
        try:
            steps = [
                ("Loading configuration...", 20),
                ("Connecting to Docker...", 40),
                ("Initializing database...", 60),
                ("Setting up GUI components...", 80),
                ("Finalizing startup...", 100)
            ]
            
            for status, progress in steps:
                if not self.completed:
                    self.root.after(0, self._update_progress, status, progress)
                    time.sleep(0.5)  # Simulate initialization time
            
            # Complete initialization
            if not self.completed:
                self.root.after(0, self._complete_initialization)
                
        except Exception as e:
            self.logger.error(f"Error during initialization: {e}")
            if not self.completed:
                self.root.after(0, self._show_error, str(e))
    
    def _update_progress(self, status: str, progress: float):
        """Update progress display"""
        try:
            if self.root.winfo_exists():
                self.status_var.set(status)
                self.progress_var.set(progress)
                self.root.update_idletasks()
        except tk.TclError:
            pass
    
    def _complete_initialization(self):
        """Complete the initialization process"""
        try:
            if self.root.winfo_exists():
                self.completed = True
                self.status_var.set("Starting application...")
                self.progress_var.set(100)
                self.root.update_idletasks()
                
                # Close startup window and start main app
                self.root.after(500, self._close_and_start_main)
        except tk.TclError:
            pass
    
    def _show_error(self, error_message: str):
        """Show error message"""
        try:
            if self.root.winfo_exists():
                self.status_var.set(f"Error: {error_message}")
                self.root.update_idletasks()
                
                # Close after showing error
                self.root.after(3000, self.close)
        except tk.TclError:
            pass
    
    def _close_and_start_main(self):
        """Close startup window and start main application"""
        try:
            self.close()
            if self.on_complete:
                self.on_complete()
        except Exception as e:
            self.logger.error(f"Error starting main application: {e}")
    
    def close(self):
        """Close the startup window"""
        try:
            if self.root and self.root.winfo_exists():
                self.root.destroy()
        except tk.TclError:
            pass
    
    def run(self):
        """Run the startup window"""
        try:
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"Error in startup window: {e}")


def show_startup_window(on_complete: Callable = None):
    """Show startup window and return when complete"""
    startup = StartupWindow(on_complete)
    startup.run()