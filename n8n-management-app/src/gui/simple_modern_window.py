"""
Simple Modern Window for n8n Management App
Clean, working interface with thread safety and proper resource cleanup
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
import queue
import re
from typing import Dict, Any, Optional

from core.logger import get_logger
from core.config_manager import get_config
from core.n8n_manager import get_n8n_manager
from core.docker_manager import get_docker_manager


class InputValidator:
    """Input validation utility class"""
    
    @staticmethod
    def validate_instance_name(name: str) -> tuple[bool, str]:
        """Validate instance name according to business rules"""
        if not name:
            return False, "Instance name cannot be empty"
        
        name = name.strip()
        
        if len(name) < 3:
            return False, "Instance name must be at least 3 characters long"
        
        if len(name) > 50:
            return False, "Instance name cannot exceed 50 characters"
        
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', name):
            return False, "Instance name can only contain letters, numbers, hyphens, and underscores, and must start with a letter or number"
        
        # Check for reserved names
        reserved_names = {'docker', 'system', 'admin', 'root', 'n8n'}
        if name.lower() in reserved_names:
            return False, f"'{name}' is a reserved name and cannot be used"
        
        return True, "Valid instance name"


class SimpleModernWindow:
    """Simple, reliable main application window with thread safety"""
    
    def __init__(self):
        self.logger = get_logger()
        self.config = get_config()
        self.n8n_manager = get_n8n_manager()
        self.docker_manager = get_docker_manager()
        
        # Thread-safe communication
        self.update_queue = queue.Queue()
        self.shutdown_event = threading.Event()
        self.background_threads = []
        
        # GUI components
        self.root = None
        self.main_frame = None
        self.status_var = None
        self.instance_count_var = None
        
        # State
        self.refresh_thread = None
        self.refresh_running = False
        
        self._create_window()
        self._create_layout()
        
        # Start queue processor
        self.root.after(100, self._process_update_queue)
        
        # Defer initialization to prevent blocking
        self.root.after_idle(self._start_auto_refresh)
    
    def _process_update_queue(self):
        """Process GUI updates from background threads"""
        try:
            while True:
                update_func = self.update_queue.get_nowait()
                update_func()
        except queue.Empty:
            pass
        finally:
            if self.refresh_running:
                self.root.after(100, self._process_update_queue)
    
    def _create_window(self):
        """Create the main window"""
        self.root = tk.Tk()
        self.root.title("n8n Management Hub")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 1200) // 2
        y = (self.root.winfo_screenheight() - 800) // 2
        self.root.geometry(f"+{x}+{y}")
        
        # Configure colors
        self.root.configure(bg='#ffffff')
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-n>', lambda e: self._new_instance())
        self.root.bind('<F5>', lambda e: self._refresh_all())
        self.root.bind('<Control-q>', lambda e: self._on_closing())
    
    def _create_layout(self):
        """Create the main layout"""
        # Header
        header_frame = tk.Frame(self.root, bg='#2563eb', height=80)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        # Title
        title_label = tk.Label(header_frame,
                              text="n8n Management Hub",
                              font=('Arial', 20, 'bold'),
                              fg='white',
                              bg='#2563eb')
        title_label.pack(side=tk.LEFT, padx=30, pady=25)
        
        # Header buttons
        btn_frame = tk.Frame(header_frame, bg='#2563eb')
        btn_frame.pack(side=tk.RIGHT, padx=30, pady=20)
        
        new_btn = tk.Button(btn_frame,
                           text="+ New Instance",
                           font=('Arial', 10, 'bold'),
                           fg='#2563eb',
                           bg='white',
                           relief='flat',
                           padx=20,
                           pady=8,
                           command=self._new_instance)
        new_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        refresh_btn = tk.Button(btn_frame,
                               text="🔄 Refresh",
                               font=('Arial', 10),
                               fg='white',
                               bg='#1d4ed8',
                               relief='flat',
                               padx=15,
                               pady=8,
                               command=self._refresh_all)
        refresh_btn.pack(side=tk.RIGHT)
        
        # Main content area
        self.main_frame = tk.Frame(self.root, bg='#f8fafc')
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create dashboard
        self._create_dashboard()
        
        # Status bar
        self._create_status_bar()
    
    def _create_dashboard(self):
        """Create simple dashboard"""
        # Container
        container = tk.Frame(self.main_frame, bg='#f8fafc')
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Welcome section
        welcome_frame = tk.Frame(container, bg='white', relief='solid', borderwidth=1)
        welcome_frame.pack(fill=tk.X, pady=(0, 20))
        
        welcome_content = tk.Frame(welcome_frame, bg='white')
        welcome_content.pack(fill=tk.X, padx=30, pady=30)
        
        welcome_label = tk.Label(welcome_content,
                                text="Welcome to n8n Management Hub",
                                font=('Arial', 18, 'bold'),
                                fg='#1f2937',
                                bg='white')
        welcome_label.pack(anchor='w')
        
        desc_label = tk.Label(welcome_content,
                             text="Manage your n8n workflow automation instances with ease",
                             font=('Arial', 12),
                             fg='#6b7280',
                             bg='white')
        desc_label.pack(anchor='w', pady=(5, 0))
        
        # Stats section
        stats_frame = tk.Frame(container, bg='#f8fafc')
        stats_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Stats cards
        self.total_card = self._create_stat_card(stats_frame, "Total Instances", "0", "#3b82f6")
        self.running_card = self._create_stat_card(stats_frame, "Running", "0", "#10b981")
        self.docker_card = self._create_stat_card(stats_frame, "Docker Status", "Checking...", "#f59e0b")
        
        self.total_card.pack(side=tk.LEFT, padx=(0, 15))
        self.running_card.pack(side=tk.LEFT, padx=(0, 15))
        self.docker_card.pack(side=tk.LEFT)
        
        # Instances section
        instances_frame = tk.Frame(container, bg='white', relief='solid', borderwidth=1)
        instances_frame.pack(fill=tk.BOTH, expand=True)
        
        instances_header = tk.Frame(instances_frame, bg='white')
        instances_header.pack(fill=tk.X, padx=30, pady=(30, 20))
        
        instances_title = tk.Label(instances_header,
                                  text="Your Instances",
                                  font=('Arial', 16, 'bold'),
                                  fg='#1f2937',
                                  bg='white')
        instances_title.pack(side=tk.LEFT)
        
        # Instances list
        self.instances_content = tk.Frame(instances_frame, bg='white')
        self.instances_content.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0, 30))
        
        # Initial empty state
        self._show_empty_state()
        
        # Defer data loading
        self.root.after(1000, self._load_initial_data)
    
    def _create_stat_card(self, parent, title, value, color):
        """Create a statistics card"""
        card = tk.Frame(parent, bg='white', relief='solid', borderwidth=1, width=200, height=120)
        card.pack_propagate(False)
        
        content = tk.Frame(card, bg='white')
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title_label = tk.Label(content,
                              text=title,
                              font=('Arial', 10),
                              fg='#6b7280',
                              bg='white')
        title_label.pack(anchor='w')
        
        value_var = tk.StringVar()
        value_var.set(value)
        value_label = tk.Label(content,
                              textvariable=value_var,
                              font=('Arial', 24, 'bold'),
                              fg=color,
                              bg='white')
        value_label.pack(anchor='w', pady=(10, 0))
        
        # Store reference to value variable
        card.value_var = value_var
        
        return card
    
    def _show_empty_state(self):
        """Show empty state"""
        # Clear existing content
        for widget in self.instances_content.winfo_children():
            widget.destroy()
        
        empty_frame = tk.Frame(self.instances_content, bg='white')
        empty_frame.pack(expand=True)
        
        icon_label = tk.Label(empty_frame,
                             text="🔧",
                             font=('Arial', 48),
                             fg='#9ca3af',
                             bg='white')
        icon_label.pack(pady=(50, 20))
        
        title_label = tk.Label(empty_frame,
                              text="No Instances Yet",
                              font=('Arial', 16, 'bold'),
                              fg='#1f2937',
                              bg='white')
        title_label.pack(pady=(0, 10))
        
        desc_label = tk.Label(empty_frame,
                             text="Create your first n8n instance to get started",
                             font=('Arial', 12),
                             fg='#6b7280',
                             bg='white')
        desc_label.pack(pady=(0, 30))
        
        create_btn = tk.Button(empty_frame,
                              text="🚀 Create First Instance",
                              font=('Arial', 12, 'bold'),
                              fg='white',
                              bg='#2563eb',
                              relief='flat',
                              padx=30,
                              pady=12,
                              command=self._new_instance)
        create_btn.pack()
    
    def _create_status_bar(self):
        """Create status bar"""
        status_frame = tk.Frame(self.root, bg='#f3f4f6', height=32)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        status_frame.pack_propagate(False)
        
        status_content = tk.Frame(status_frame, bg='#f3f4f6')
        status_content.pack(fill=tk.BOTH, padx=20, pady=6)
        
        # Status message
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_label = tk.Label(status_content,
                               textvariable=self.status_var,
                               font=('Arial', 9),
                               fg='#6b7280',
                               bg='#f3f4f6')
        status_label.pack(side=tk.LEFT)
        
        # Instance count
        self.instance_count_var = tk.StringVar()
        instance_count_label = tk.Label(status_content,
                                       textvariable=self.instance_count_var,
                                       font=('Arial', 9),
                                       fg='#6b7280',
                                       bg='#f3f4f6')
        instance_count_label.pack(side=tk.RIGHT)
    
    def _load_initial_data(self):
        """Load initial data"""
        try:
            self._update_stats()
            self._update_instances_list()
        except Exception as e:
            self.logger.error(f"Error loading initial data: {e}")
    
    def _update_stats(self):
        """Update statistics cards"""
        try:
            # Get instances
            instances = self.n8n_manager.list_instances()
            total = len(instances)
            running = sum(1 for i in instances if i.get('current_status') == 'running')
            
            # Update cards
            self.total_card.value_var.set(str(total))
            self.running_card.value_var.set(str(running))
            
            # Update status bar
            self.instance_count_var.set(f"{running}/{total} instances running")
            
            # Docker status
            try:
                if self.docker_manager.is_docker_available():
                    self.docker_card.value_var.set("Connected")
                else:
                    self.docker_card.value_var.set("Disconnected")
            except:
                self.docker_card.value_var.set("Error")
                
        except Exception as e:
            self.logger.error(f"Error updating stats: {e}")
    
    def _update_instances_list(self):
        """Update instances list"""
        try:
            instances = self.n8n_manager.list_instances()
            
            # Clear existing content
            for widget in self.instances_content.winfo_children():
                widget.destroy()
            
            if not instances:
                self._show_empty_state()
                return
            
            # Show instances
            for instance in instances[:5]:  # Show first 5
                self._create_instance_item(self.instances_content, instance)
            
            if len(instances) > 5:
                more_label = tk.Label(self.instances_content,
                                     text=f"... and {len(instances) - 5} more instances",
                                     font=('Arial', 10),
                                     fg='#6b7280',
                                     bg='white')
                more_label.pack(pady=10)
                
        except Exception as e:
            self.logger.error(f"Error updating instances list: {e}")
    
    def _create_instance_item(self, parent, instance):
        """Create an instance list item"""
        item_frame = tk.Frame(parent, bg='white')
        item_frame.pack(fill=tk.X, pady=5)
        
        # Status indicator
        status = instance.get('current_status', instance.get('status', 'unknown'))
        status_color = '#10b981' if status == 'running' else '#ef4444' if status == 'stopped' else '#f59e0b'
        
        status_canvas = tk.Canvas(item_frame, width=12, height=12, bg='white', highlightthickness=0)
        status_canvas.pack(side=tk.LEFT, padx=(0, 10))
        status_canvas.create_oval(2, 2, 10, 10, fill=status_color, outline=status_color)
        
        # Instance info
        info_frame = tk.Frame(item_frame, bg='white')
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        name_label = tk.Label(info_frame,
                             text=instance['name'],
                             font=('Arial', 12, 'bold'),
                             fg='#1f2937',
                             bg='white')
        name_label.pack(anchor='w')
        
        details_text = f"{status.replace('_', ' ').title()}"
        if instance.get('port'):
            details_text += f" • Port {instance['port']}"
        
        details_label = tk.Label(info_frame,
                                text=details_text,
                                font=('Arial', 10),
                                fg='#6b7280',
                                bg='white')
        details_label.pack(anchor='w')
        
        # Action buttons
        if status == 'running':
            open_btn = tk.Button(item_frame,
                                text="Open",
                                font=('Arial', 9),
                                fg='white',
                                bg='#10b981',
                                relief='flat',
                                padx=12,
                                pady=4,
                                command=lambda: self._open_instance(instance))
            open_btn.pack(side=tk.RIGHT, padx=(5, 0))
    
    def _open_instance(self, instance):
        """Open instance in browser"""
        try:
            port = instance.get('port')
            if port:
                import webbrowser
                url = f"http://localhost:{port}"
                webbrowser.open(url)
                self.set_status(f"Opened {instance['name']} in browser")
            else:
                messagebox.showwarning("No Port", "This instance has no port configured.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open instance: {e}")
    
    def _new_instance(self):
        """Create new instance with proper validation"""
        while True:
            name = tk.simpledialog.askstring(
                "New Instance", 
                "Enter instance name:\n(3-50 characters, letters/numbers/hyphens/underscores only)"
            )
            
            if not name:  # User cancelled
                return
            
            is_valid, message = InputValidator.validate_instance_name(name)
            
            if is_valid:
                # Check if name already exists
                try:
                    existing = self.n8n_manager.db.get_instance_by_name(name.strip())
                    if existing:
                        messagebox.showerror("Name Conflict", f"Instance '{name}' already exists. Please choose a different name.")
                        continue
                except:
                    pass  # If check fails, proceed anyway
                
                try:
                    self.set_status(f"Creating instance '{name}'...")
                    
                    def create_worker():
                        success, message, instance_id = self.n8n_manager.create_instance(name.strip())
                        self.update_queue.put(lambda: self._handle_create_result(success, message, name))
                    
                    thread = threading.Thread(target=create_worker, daemon=False, name=f"CreateInstance-{name}")
                    self.background_threads.append(thread)
                    thread.start()
                    break
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to create instance: {e}")
                    break
            else:
                messagebox.showerror("Invalid Name", message)
    
    def _handle_create_result(self, success, message, name):
        """Handle create result"""
        if success:
            self.set_status(f"Instance '{name}' created successfully")
            self._refresh_all()
        else:
            messagebox.showerror("Creation Failed", message)
            self.set_status("Instance creation failed")
    
    def _refresh_all(self):
        """Refresh all data"""
        self.set_status("Refreshing...")
        self._update_stats()
        self._update_instances_list()
        self.set_status("Refresh completed")
    
    def _start_auto_refresh(self):
        """Start automatic refresh thread with proper tracking"""
        self.refresh_running = True
        self.refresh_thread = threading.Thread(
            target=self._auto_refresh_worker, 
            daemon=False,  # Don't use daemon threads for proper cleanup
            name="AutoRefreshWorker"
        )
        self.background_threads.append(self.refresh_thread)
        self.refresh_thread.start()
    
    def _auto_refresh_worker(self):
        """Background worker with proper shutdown handling"""
        while self.refresh_running and not self.shutdown_event.is_set():
            try:
                # Use event.wait() instead of time.sleep() for responsive shutdown
                if self.shutdown_event.wait(timeout=10):  # 10-second refresh interval
                    break
                
                if self.refresh_running:
                    try:
                        self.update_queue.put(self._safe_update_stats)
                    except Exception as e:
                        self.logger.error(f"Error queuing stats update: {e}")
                        
            except Exception as e:
                self.logger.error(f"Error in auto-refresh worker: {e}")
                # Wait before retrying, but check for shutdown
                if self.shutdown_event.wait(timeout=5):
                    break
        
        self.logger.info("Auto-refresh worker stopped")
    
    def _safe_update_stats(self):
        """Safe wrapper for updating stats"""
        try:
            if self.refresh_running and self.root.winfo_exists():
                self._update_stats()
        except (tk.TclError, AttributeError):
            pass
        except Exception as e:
            self.logger.error(f"Error in safe stats update: {e}")
    
    def _on_closing(self):
        """Handle window closing with proper cleanup"""
        try:
            self.logger.info("Initiating application shutdown...")
            
            # Signal all threads to stop
            self.refresh_running = False
            self.shutdown_event.set()
            
            # Wait for background threads to finish (with timeout)
            for thread in self.background_threads:
                if thread.is_alive():
                    self.logger.info(f"Waiting for thread {thread.name} to finish...")
                    thread.join(timeout=5.0)
                    
                    if thread.is_alive():
                        self.logger.warning(f"Thread {thread.name} did not stop gracefully")
            
            # Close any open resources
            self._cleanup_resources()
            
            self.logger.info("Application shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
        finally:
            # Ensure GUI is destroyed even if cleanup fails
            try:
                self.root.quit()
                self.root.destroy()
            except:
                pass
    
    def _cleanup_resources(self):
        """Clean up application resources"""
        try:
            # Close database connections
            if hasattr(self, 'n8n_manager') and self.n8n_manager:
                if hasattr(self.n8n_manager, 'db') and self.n8n_manager.db:
                    self.n8n_manager.db.close()
            
            # Close Docker connections
            if hasattr(self, 'docker_manager') and self.docker_manager:
                if hasattr(self.docker_manager, 'client') and self.docker_manager.client:
                    self.docker_manager.client.close()
            
        except Exception as e:
            self.logger.error(f"Error cleaning up resources: {e}")
    
    def set_status(self, message: str):
        """Set status bar message"""
        if self.status_var:
            self.status_var.set(message)
        self.logger.debug(f"Status: {message}")
    
    def run(self):
        """Start the GUI application"""
        try:
            self.logger.info("Starting simple modern GUI")
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"Error in GUI main loop: {e}")
            raise
    
    def destroy(self):
        """Destroy the window"""
        if self.root:
            self._on_closing()