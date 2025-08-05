"""
Modern Main Window for n8n Management App
Beautiful, intuitive, and user-friendly interface
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from typing import Dict, Any, Optional
from pathlib import Path

from core.logger import get_logger
from core.config_manager import get_config
from core.n8n_manager import get_n8n_manager
from core.docker_manager import get_docker_manager
from gui.modern_theme import apply_modern_theme
from gui.modern_instance_manager import ModernInstanceManagerFrame
from gui.modern_dashboard import ModernDashboardFrame
from utils.gui_utils import DeferredInitializer, safe_gui_operation


class ModernMainWindow:
    """Modern, user-friendly main application window"""
    
    def __init__(self):
        self.logger = get_logger()
        self.config = get_config()
        self.n8n_manager = get_n8n_manager()
        self.docker_manager = get_docker_manager()
        
        self.root = None
        self.theme = None
        self.sidebar = None
        self.main_content = None
        self.current_view = None
        
        # Components
        self.dashboard = None
        self.instance_manager = None
        
        # State
        self.refresh_thread = None
        self.refresh_running = False
        self.sidebar_collapsed = False
        
        self._create_window()
        self._setup_layout()
        self._show_dashboard()
        
        # Defer initialization to prevent blocking
        self.root.after_idle(self._start_auto_refresh)
    
    def _create_window(self):
        """Create the main window with modern styling"""
        self.root = tk.Tk()
        self.root.title("n8n Management Hub")
        
        # Set window properties
        self.root.geometry("1400x900")
        self.root.minsize(1000, 700)
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 1400) // 2
        y = (self.root.winfo_screenheight() - 900) // 2
        self.root.geometry(f"+{x}+{y}")
        
        # Apply modern theme
        self.theme = apply_modern_theme(self.root)
        
        # Configure window
        self.root.configure(bg=self.theme.COLORS['bg_primary'])
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-n>', lambda e: self._new_instance())
        self.root.bind('<Control-r>', lambda e: self._refresh_all())
        self.root.bind('<F5>', lambda e: self._refresh_all())
        self.root.bind('<Control-q>', lambda e: self._on_closing())
    
    def _setup_layout(self):
        """Setup the main layout with sidebar and content area"""
        # Main container
        main_container = tk.Frame(self.root, bg=self.theme.COLORS['bg_primary'])
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create sidebar
        self._create_sidebar(main_container)
        
        # Create main content area
        self._create_main_content(main_container)
        
        # Create status bar
        self._create_status_bar()
    
    def _create_sidebar(self, parent):
        """Create modern sidebar navigation"""
        self.sidebar = tk.Frame(parent, 
                               bg=self.theme.COLORS['bg_secondary'],
                               width=280)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        
        # App header
        header_frame = tk.Frame(self.sidebar, bg=self.theme.COLORS['bg_secondary'])
        header_frame.pack(fill=tk.X, padx=20, pady=(20, 30))
        
        # App logo/title
        title_label = tk.Label(header_frame,
                              text="n8n Hub",
                              font=self.theme.FONTS['heading_large'],
                              fg=self.theme.COLORS['text_primary'],
                              bg=self.theme.COLORS['bg_secondary'])
        title_label.pack(anchor='w')
        
        subtitle_label = tk.Label(header_frame,
                                 text="Workflow Management",
                                 font=self.theme.FONTS['caption'],
                                 fg=self.theme.COLORS['text_muted'],
                                 bg=self.theme.COLORS['bg_secondary'])
        subtitle_label.pack(anchor='w')
        
        # Navigation menu
        nav_frame = tk.Frame(self.sidebar, bg=self.theme.COLORS['bg_secondary'])
        nav_frame.pack(fill=tk.X, padx=10)
        
        # Navigation items
        self.nav_items = [
            {'name': 'Dashboard', 'icon': '📊', 'command': self._show_dashboard},
            {'name': 'Instances', 'icon': '🔧', 'command': self._show_instances},
            {'name': 'Monitoring', 'icon': '📈', 'command': self._show_monitoring},
            {'name': 'Logs', 'icon': '📋', 'command': self._show_logs},
            {'name': 'Settings', 'icon': '⚙️', 'command': self._show_settings},
        ]
        
        self.nav_buttons = {}
        for item in self.nav_items:
            btn = self._create_nav_button(nav_frame, item['name'], item['icon'], item['command'])
            self.nav_buttons[item['name']] = btn
        
        # Quick actions section
        self._create_quick_actions(self.sidebar)
        
        # Docker status
        self._create_docker_status(self.sidebar)
    
    def _create_nav_button(self, parent, name, icon, command):
        """Create a navigation button"""
        btn_frame = tk.Frame(parent, bg=self.theme.COLORS['bg_secondary'])
        btn_frame.pack(fill=tk.X, pady=2)
        
        btn = tk.Button(btn_frame,
                       text=f"{icon}  {name}",
                       font=self.theme.FONTS['body_medium'],
                       fg=self.theme.COLORS['text_secondary'],
                       bg=self.theme.COLORS['bg_secondary'],
                       activebackground=self.theme.COLORS['primary_light'],
                       activeforeground=self.theme.COLORS['primary'],
                       relief='flat',
                       anchor='w',
                       padx=20,
                       pady=12,
                       command=lambda: self._navigate_to(name, command))
        btn.pack(fill=tk.X)
        
        # Hover effects
        def on_enter(e):
            if self.current_view != name:
                btn.configure(bg=self.theme.COLORS['gray_100'])
        
        def on_leave(e):
            if self.current_view != name:
                btn.configure(bg=self.theme.COLORS['bg_secondary'])
        
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)
        
        return btn
    
    def _create_quick_actions(self, parent):
        """Create quick actions section"""
        actions_frame = tk.Frame(parent, bg=self.theme.COLORS['bg_secondary'])
        actions_frame.pack(fill=tk.X, padx=20, pady=(40, 20))
        
        # Section title
        title_label = tk.Label(actions_frame,
                              text="Quick Actions",
                              font=self.theme.FONTS['heading_small'],
                              fg=self.theme.COLORS['text_primary'],
                              bg=self.theme.COLORS['bg_secondary'])
        title_label.pack(anchor='w', pady=(0, 15))
        
        # Action buttons
        new_btn = tk.Button(actions_frame,
                           text="+ New Instance",
                           font=self.theme.FONTS['button'],
                           fg=self.theme.COLORS['text_inverse'],
                           bg=self.theme.COLORS['primary'],
                           activebackground=self.theme.COLORS['primary_hover'],
                           relief='flat',
                           padx=20,
                           pady=10,
                           command=self._new_instance)
        new_btn.pack(fill=tk.X, pady=(0, 8))
        
        refresh_btn = tk.Button(actions_frame,
                               text="🔄 Refresh All",
                               font=self.theme.FONTS['button'],
                               fg=self.theme.COLORS['text_primary'],
                               bg=self.theme.COLORS['gray_100'],
                               activebackground=self.theme.COLORS['gray_200'],
                               relief='flat',
                               padx=20,
                               pady=10,
                               command=self._refresh_all)
        refresh_btn.pack(fill=tk.X)
    
    def _create_docker_status(self, parent):
        """Create Docker status indicator"""
        status_frame = tk.Frame(parent, bg=self.theme.COLORS['bg_secondary'])
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=20)
        
        # Status indicator
        self.docker_status_frame = tk.Frame(status_frame, 
                                           bg=self.theme.COLORS['gray_100'],
                                           relief='flat')
        self.docker_status_frame.pack(fill=tk.X, pady=5)
        
        # Status content
        status_content = tk.Frame(self.docker_status_frame, bg=self.theme.COLORS['gray_100'])
        status_content.pack(fill=tk.X, padx=15, pady=10)
        
        self.docker_status_indicator = self.theme.create_status_indicator(status_content, 'unknown')
        self.docker_status_indicator.pack(side=tk.LEFT)
        
        self.docker_status_label = tk.Label(status_content,
                                           text="Docker: Checking...",
                                           font=self.theme.FONTS['body_small'],
                                           fg=self.theme.COLORS['text_secondary'],
                                           bg=self.theme.COLORS['gray_100'])
        self.docker_status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Defer Docker status check
        self.root.after(1000, self._update_docker_status)
    
    def _create_main_content(self, parent):
        """Create main content area"""
        self.main_content = tk.Frame(parent, bg=self.theme.COLORS['bg_primary'])
        self.main_content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    
    def _create_status_bar(self):
        """Create modern status bar"""
        self.status_bar = tk.Frame(self.root, 
                                  bg=self.theme.COLORS['gray_50'],
                                  height=32)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.pack_propagate(False)
        
        # Status content
        status_content = tk.Frame(self.status_bar, bg=self.theme.COLORS['gray_50'])
        status_content.pack(fill=tk.BOTH, padx=20, pady=6)
        
        # Status message
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_label = tk.Label(status_content,
                                    textvariable=self.status_var,
                                    font=self.theme.FONTS['caption'],
                                    fg=self.theme.COLORS['text_muted'],
                                    bg=self.theme.COLORS['gray_50'])
        self.status_label.pack(side=tk.LEFT)
        
        # Instance count
        self.instance_count_var = tk.StringVar()
        self.instance_count_label = tk.Label(status_content,
                                            textvariable=self.instance_count_var,
                                            font=self.theme.FONTS['caption'],
                                            fg=self.theme.COLORS['text_muted'],
                                            bg=self.theme.COLORS['gray_50'])
        self.instance_count_label.pack(side=tk.RIGHT)
        
        # Defer status update
        self.root.after(500, self._update_status)
    
    def _navigate_to(self, view_name, command):
        """Navigate to a specific view"""
        # Update navigation state
        if self.current_view:
            # Reset previous button
            prev_btn = self.nav_buttons.get(self.current_view)
            if prev_btn:
                prev_btn.configure(bg=self.theme.COLORS['bg_secondary'],
                                 fg=self.theme.COLORS['text_secondary'])
        
        # Highlight current button
        current_btn = self.nav_buttons.get(view_name)
        if current_btn:
            current_btn.configure(bg=self.theme.COLORS['primary_light'],
                                fg=self.theme.COLORS['primary'])
        
        self.current_view = view_name
        
        # Execute command
        if command:
            command()
    
    def _show_dashboard(self):
        """Show dashboard view"""
        self._clear_main_content()
        
        if not self.dashboard:
            self.dashboard = ModernDashboardFrame(self.main_content, self)
        
        self.dashboard.pack(fill=tk.BOTH, expand=True)
        self.set_status("Dashboard loaded")
    
    def _show_instances(self):
        """Show instances view"""
        self._clear_main_content()
        
        if not self.instance_manager:
            self.instance_manager = ModernInstanceManagerFrame(self.main_content, self)
        
        self.instance_manager.pack(fill=tk.BOTH, expand=True)
        self.set_status("Instance manager loaded")
    
    def _show_monitoring(self):
        """Show monitoring view"""
        self._clear_main_content()
        
        # Create monitoring view
        monitoring_frame = tk.Frame(self.main_content, bg=self.theme.COLORS['bg_primary'])
        monitoring_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Header
        header_label = tk.Label(monitoring_frame,
                               text="System Monitoring",
                               font=self.theme.FONTS['heading_large'],
                               fg=self.theme.COLORS['text_primary'],
                               bg=self.theme.COLORS['bg_primary'])
        header_label.pack(anchor='w', pady=(0, 20))
        
        # Coming soon message
        coming_soon = tk.Label(monitoring_frame,
                              text="Advanced monitoring features coming soon...",
                              font=self.theme.FONTS['body_large'],
                              fg=self.theme.COLORS['text_secondary'],
                              bg=self.theme.COLORS['bg_primary'])
        coming_soon.pack(anchor='w')
        
        self.set_status("Monitoring view loaded")
    
    def _show_logs(self):
        """Show logs view"""
        self._clear_main_content()
        
        # Create logs view
        logs_frame = tk.Frame(self.main_content, bg=self.theme.COLORS['bg_primary'])
        logs_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Header
        header_label = tk.Label(logs_frame,
                               text="System Logs",
                               font=self.theme.FONTS['heading_large'],
                               fg=self.theme.COLORS['text_primary'],
                               bg=self.theme.COLORS['bg_primary'])
        header_label.pack(anchor='w', pady=(0, 20))
        
        # Coming soon message
        coming_soon = tk.Label(logs_frame,
                              text="Enhanced log viewer coming soon...",
                              font=self.theme.FONTS['body_large'],
                              fg=self.theme.COLORS['text_secondary'],
                              bg=self.theme.COLORS['bg_primary'])
        coming_soon.pack(anchor='w')
        
        self.set_status("Logs view loaded")
    
    def _show_settings(self):
        """Show settings view"""
        self._clear_main_content()
        
        # Create settings view
        settings_frame = tk.Frame(self.main_content, bg=self.theme.COLORS['bg_primary'])
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Header
        header_label = tk.Label(settings_frame,
                               text="Settings",
                               font=self.theme.FONTS['heading_large'],
                               fg=self.theme.COLORS['text_primary'],
                               bg=self.theme.COLORS['bg_primary'])
        header_label.pack(anchor='w', pady=(0, 20))
        
        # Coming soon message
        coming_soon = tk.Label(settings_frame,
                              text="Settings panel coming soon...",
                              font=self.theme.FONTS['body_large'],
                              fg=self.theme.COLORS['text_secondary'],
                              bg=self.theme.COLORS['bg_primary'])
        coming_soon.pack(anchor='w')
        
        self.set_status("Settings view loaded")
    
    def _clear_main_content(self):
        """Clear main content area"""
        for widget in self.main_content.winfo_children():
            widget.pack_forget()
    
    def _new_instance(self):
        """Create new instance"""
        if self.instance_manager:
            self.instance_manager.create_instance_dialog()
        else:
            # Navigate to instances view first
            self._navigate_to('Instances', self._show_instances)
            self.root.after(100, lambda: self.instance_manager.create_instance_dialog())
    
    def _refresh_all(self):
        """Refresh all data"""
        self.set_status("Refreshing all data...")
        
        # Update status indicators
        self._update_status()
        self._update_docker_status()
        
        # Refresh current view
        if self.current_view == 'Dashboard' and self.dashboard:
            self.dashboard.refresh()
        elif self.current_view == 'Instances' and self.instance_manager:
            self.instance_manager.refresh_instances()
        
        self.set_status("Refresh completed")
    
    def _start_auto_refresh(self):
        """Start automatic refresh thread"""
        self.refresh_running = True
        self.refresh_thread = threading.Thread(target=self._auto_refresh_worker, daemon=True)
        self.refresh_thread.start()
    
    def _auto_refresh_worker(self):
        """Background worker for auto-refresh"""
        interval = self.config.get('ui.auto_refresh_interval', 10)  # Slower refresh for better UX
        
        while self.refresh_running:
            try:
                # Use smaller sleep intervals for responsive shutdown
                for _ in range(int(interval * 10)):
                    if not self.refresh_running:
                        break
                    time.sleep(0.1)
                
                if self.refresh_running:
                    # Schedule GUI updates
                    try:
                        self.root.after(0, self._safe_update_status)
                        self.root.after(0, self._safe_update_docker_status)
                        
                        # Update current view
                        if self.current_view == 'Dashboard' and self.dashboard:
                            self.root.after(0, self._safe_refresh_dashboard)
                    except tk.TclError:
                        break
                        
            except Exception as e:
                self.logger.error(f"Error in auto-refresh worker: {e}")
                # Wait before retrying
                for _ in range(50):
                    if not self.refresh_running:
                        break
                    time.sleep(0.1)
    
    def _update_status(self):
        """Update status bar information"""
        try:
            instances = self.n8n_manager.list_instances()
            total = len(instances)
            running = sum(1 for i in instances if i.get('current_status') == 'running')
            
            self.instance_count_var.set(f"{running}/{total} instances running")
            
        except Exception as e:
            self.logger.error(f"Error updating status: {e}")
            self.instance_count_var.set("Status unavailable")
    
    def _update_docker_status(self):
        """Update Docker status indicator"""
        try:
            if self.docker_manager.is_docker_available():
                # Update indicator color
                self.docker_status_indicator.delete("all")
                self.docker_status_indicator.create_oval(2, 2, 10, 10, 
                                                        fill=self.theme.COLORS['success'], 
                                                        outline=self.theme.COLORS['success'])
                
                # Update label
                self.docker_status_label.configure(text="Docker: Connected",
                                                  fg=self.theme.COLORS['success'])
                
                # Update frame background
                self.docker_status_frame.configure(bg=self.theme.COLORS['success_light'])
                self.docker_status_label.configure(bg=self.theme.COLORS['success_light'])
                
            else:
                # Update indicator color
                self.docker_status_indicator.delete("all")
                self.docker_status_indicator.create_oval(2, 2, 10, 10, 
                                                        fill=self.theme.COLORS['error'], 
                                                        outline=self.theme.COLORS['error'])
                
                # Update label
                self.docker_status_label.configure(text="Docker: Disconnected",
                                                  fg=self.theme.COLORS['error'])
                
                # Update frame background
                self.docker_status_frame.configure(bg=self.theme.COLORS['error_light'])
                self.docker_status_label.configure(bg=self.theme.COLORS['error_light'])
                
        except Exception as e:
            self.logger.error(f"Error checking Docker status: {e}")
            
            # Update indicator color
            self.docker_status_indicator.delete("all")
            self.docker_status_indicator.create_oval(2, 2, 10, 10, 
                                                    fill=self.theme.COLORS['warning'], 
                                                    outline=self.theme.COLORS['warning'])
            
            # Update label
            self.docker_status_label.configure(text="Docker: Error",
                                              fg=self.theme.COLORS['warning'])
            
            # Update frame background
            self.docker_status_frame.configure(bg=self.theme.COLORS['warning_light'])
            self.docker_status_label.configure(bg=self.theme.COLORS['warning_light'])
    
    def _safe_update_status(self):
        """Safe wrapper for updating status"""
        try:
            if self.refresh_running and self.root.winfo_exists():
                self._update_status()
        except (tk.TclError, AttributeError):
            pass
        except Exception as e:
            self.logger.error(f"Error in safe status update: {e}")
    
    def _safe_update_docker_status(self):
        """Safe wrapper for updating Docker status"""
        try:
            if self.refresh_running and self.root.winfo_exists():
                self._update_docker_status()
        except (tk.TclError, AttributeError):
            pass
        except Exception as e:
            self.logger.error(f"Error in safe Docker status update: {e}")
    
    def _safe_refresh_dashboard(self):
        """Safe wrapper for refreshing dashboard"""
        try:
            if self.refresh_running and self.root.winfo_exists() and self.dashboard:
                self.dashboard.refresh()
        except (tk.TclError, AttributeError):
            pass
        except Exception as e:
            self.logger.error(f"Error in safe dashboard refresh: {e}")
    
    def _on_closing(self):
        """Handle window closing"""
        try:
            # Stop auto-refresh
            self.refresh_running = False
            
            # Save window state
            try:
                geometry = self.root.geometry()
                self.config.set('ui.window_geometry', geometry)
                self.config.save()
            except Exception as e:
                self.logger.warning(f"Failed to save window state: {e}")
            
            self.logger.info("Closing application")
            self.root.quit()
            self.root.destroy()
            
        except Exception as e:
            self.logger.error(f"Error during window closing: {e}")
    
    # Public methods
    def set_status(self, message: str):
        """Set status bar message"""
        self.status_var.set(message)
        self.logger.debug(f"Status: {message}")
    
    def run(self):
        """Start the GUI application"""
        try:
            self.logger.info("Starting modern GUI")
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