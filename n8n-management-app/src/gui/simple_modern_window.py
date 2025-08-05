"""
Simple Modern Window for n8n Management App
Clean, working interface that doesn't hang
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
from typing import Dict, Any, Optional

from core.logger import get_logger
from core.config_manager import get_config
from core.n8n_manager import get_n8n_manager
from core.docker_manager import get_docker_manager


class SimpleModernWindow:
    """Simple, reliable main application window"""
    
    def __init__(self):
        self.logger = get_logger()
        self.config = get_config()
        self.n8n_manager = get_n8n_manager()
        self.docker_manager = get_docker_manager()
        
        self.root = None
        self.main_frame = None
        self.status_var = None
        self.instance_count_var = None
        
        # State
        self.refresh_thread = None
        self.refresh_running = False
        
        self._create_window()
        self._create_layout()
        
        # Defer initialization to prevent blocking
        self.root.after_idle(self._start_auto_refresh)
    
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
        """Create new instance"""
        # Simple dialog
        name = tk.simpledialog.askstring("New Instance", "Enter instance name:")
        if name and name.strip():
            try:
                self.set_status(f"Creating instance '{name}'...")
                
                def create_worker():
                    success, message, instance_id = self.n8n_manager.create_instance(name.strip())
                    self.root.after(0, lambda: self._handle_create_result(success, message, name))
                
                threading.Thread(target=create_worker, daemon=True).start()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create instance: {e}")
    
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
        """Start automatic refresh thread"""
        self.refresh_running = True
        self.refresh_thread = threading.Thread(target=self._auto_refresh_worker, daemon=True)
        self.refresh_thread.start()
    
    def _auto_refresh_worker(self):
        """Background worker for auto-refresh"""
        while self.refresh_running:
            try:
                # Sleep in small intervals for responsive shutdown
                for _ in range(100):  # 10 seconds in 0.1s intervals
                    if not self.refresh_running:
                        break
                    time.sleep(0.1)
                
                if self.refresh_running:
                    # Schedule GUI update
                    try:
                        self.root.after(0, self._safe_update_stats)
                    except tk.TclError:
                        break
                        
            except Exception as e:
                self.logger.error(f"Error in auto-refresh worker: {e}")
                # Wait before retrying
                for _ in range(50):
                    if not self.refresh_running:
                        break
                    time.sleep(0.1)
    
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
        """Handle window closing"""
        try:
            # Stop auto-refresh
            self.refresh_running = False
            
            self.logger.info("Closing application")
            self.root.quit()
            self.root.destroy()
            
        except Exception as e:
            self.logger.error(f"Error during window closing: {e}")
    
    def set_status(self, message: str):
        """Set status bar message"""
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
            self.refresh_running = False
            self.root.quit()
            self.root.destroy()