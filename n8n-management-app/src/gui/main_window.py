"""
Main window for n8n Management App
Provides the primary GUI interface with menu, toolbar, and content areas
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
from gui.instance_manager import InstanceManagerFrame
from gui.logs_viewer import LogsViewerFrame
from gui.performance_monitor import PerformanceMonitorFrame
from utils.gui_utils import DeferredInitializer, safe_gui_operation


class MainWindow:
    """Main application window"""
    
    def __init__(self):
        self.logger = get_logger()
        self.config = get_config()
        self.n8n_manager = get_n8n_manager()
        self.docker_manager = get_docker_manager()
        
        self.root = None
        self.notebook = None
        self.status_bar = None
        self.instance_manager = None
        self.logs_viewer = None
        self.performance_monitor = None
        
        self.refresh_thread = None
        self.refresh_running = False
        
        self._create_window()
        self._create_menu()
        self._create_toolbar()
        self._create_content_area()
        self._create_status_bar()
        self._setup_window_state()
        # Defer auto-refresh start to avoid blocking GUI initialization
        self.root.after_idle(self._start_auto_refresh)
    
    def _create_window(self):
        """Create the main window"""
        self.root = tk.Tk()
        self.root.title(self.config.get('app.name', 'n8n Management App'))
        
        # Set window size and position
        width = self.config.get('ui.window_width', 1200)
        height = self.config.get('ui.window_height', 800)
        
        # Center window on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(800, 600)
        
        # Configure style
        self._setup_theme()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _setup_theme(self):
        """Setup application theme"""
        style = ttk.Style()
        
        # Try to use a modern theme
        available_themes = style.theme_names()
        preferred_themes = ['clam', 'alt', 'default']
        
        for theme in preferred_themes:
            if theme in available_themes:
                style.theme_use(theme)
                break
        
        # Configure custom styles
        style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Status.TLabel', font=('Arial', 9))
        style.configure('Success.TLabel', foreground='green')
        style.configure('Error.TLabel', foreground='red')
        style.configure('Warning.TLabel', foreground='orange')
    
    def _create_menu(self):
        """Create application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Instance...", command=self._new_instance, accelerator="Ctrl+N")
        file_menu.add_separator()
        file_menu.add_command(label="Import Configuration...", command=self._import_config)
        file_menu.add_command(label="Export Configuration...", command=self._export_config)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_closing, accelerator="Ctrl+Q")
        
        # Instance menu
        instance_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Instance", menu=instance_menu)
        instance_menu.add_command(label="Start", command=self._start_selected_instance)
        instance_menu.add_command(label="Stop", command=self._stop_selected_instance)
        instance_menu.add_command(label="Restart", command=self._restart_selected_instance)
        instance_menu.add_separator()
        instance_menu.add_command(label="Clone...", command=self._clone_selected_instance)
        instance_menu.add_command(label="Delete...", command=self._delete_selected_instance)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Docker Info", command=self._show_docker_info)
        tools_menu.add_command(label="Cleanup Unused Resources", command=self._cleanup_docker)
        tools_menu.add_separator()
        tools_menu.add_command(label="Refresh All", command=self._refresh_all, accelerator="F5")
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-n>', lambda e: self._new_instance())
        self.root.bind('<Control-q>', lambda e: self._on_closing())
        self.root.bind('<F5>', lambda e: self._refresh_all())
    
    def _create_toolbar(self):
        """Create application toolbar"""
        toolbar_frame = ttk.Frame(self.root)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        
        # Instance management buttons
        ttk.Button(
            toolbar_frame, 
            text="New Instance", 
            command=self._new_instance
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        
        ttk.Button(
            toolbar_frame, 
            text="Start", 
            command=self._start_selected_instance
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar_frame, 
            text="Stop", 
            command=self._stop_selected_instance
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar_frame, 
            text="Restart", 
            command=self._restart_selected_instance
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        
        ttk.Button(
            toolbar_frame, 
            text="Refresh", 
            command=self._refresh_all
        ).pack(side=tk.LEFT, padx=2)
        
        # Docker status indicator
        self.docker_status_label = ttk.Label(
            toolbar_frame, 
            text="Docker: Checking...", 
            style='Status.TLabel'
        )
        self.docker_status_label.pack(side=tk.RIGHT, padx=10)
        
        # Defer Docker status update to avoid blocking
        self.root.after(1000, self._update_docker_status)
    
    def _create_content_area(self):
        """Create main content area with tabs"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Instance Manager tab
        self.instance_manager = InstanceManagerFrame(self.notebook, self)
        self.notebook.add(self.instance_manager, text="Instances")
        
        # Logs Viewer tab
        self.logs_viewer = LogsViewerFrame(self.notebook, self)
        self.notebook.add(self.logs_viewer, text="Logs")
        
        # Performance Monitor tab
        self.performance_monitor = PerformanceMonitorFrame(self.notebook, self)
        self.notebook.add(self.performance_monitor, text="Performance")
        
        # Bind tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
    
    def _create_status_bar(self):
        """Create status bar"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Status message
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_label = ttk.Label(
            status_frame, 
            textvariable=self.status_var, 
            style='Status.TLabel'
        )
        self.status_label.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Instance count
        self.instance_count_var = tk.StringVar()
        self.instance_count_label = ttk.Label(
            status_frame, 
            textvariable=self.instance_count_var, 
            style='Status.TLabel'
        )
        self.instance_count_label.pack(side=tk.RIGHT, padx=5, pady=2)
        
        # Defer status update to avoid blocking
        self.root.after(500, self._update_status)
    
    def _setup_window_state(self):
        """Setup window state persistence"""
        # Load saved window state
        try:
            saved_geometry = self.config.get('ui.window_geometry')
            if saved_geometry:
                self.root.geometry(saved_geometry)
            
            saved_state = self.config.get('ui.window_state')
            if saved_state == 'maximized':
                self.root.state('zoomed')  # Windows/Linux
        except Exception as e:
            self.logger.warning(f"Failed to restore window state: {e}")
    
    def _start_auto_refresh(self):
        """Start automatic refresh thread"""
        self.refresh_running = True
        self.refresh_thread = threading.Thread(target=self._auto_refresh_worker, daemon=True)
        self.refresh_thread.start()
    
    def _auto_refresh_worker(self):
        """Background worker for auto-refresh"""
        interval = self.config.get('ui.auto_refresh_interval', 5)
        
        while self.refresh_running:
            try:
                # Use smaller sleep intervals to allow for more responsive shutdown
                for _ in range(int(interval * 10)):  # Sleep in 0.1 second intervals
                    if not self.refresh_running:
                        break
                    time.sleep(0.1)
                
                if self.refresh_running:
                    # Schedule GUI update on main thread with timeout protection
                    try:
                        self.root.after(0, self._safe_update_status)
                        self.root.after(0, self._safe_update_docker_status)
                        
                        # Update active tab content
                        current_tab = self.notebook.select()
                        if current_tab:
                            tab_text = self.notebook.tab(current_tab, "text")
                            if tab_text == "Instances" and self.instance_manager:
                                self.root.after(0, self._safe_refresh_instances)
                            elif tab_text == "Logs" and self.logs_viewer:
                                self.root.after(0, self._safe_refresh_logs)
                    except tk.TclError:
                        # Window has been destroyed
                        break
                            
            except Exception as e:
                self.logger.error(f"Error in auto-refresh worker: {e}")
                # Wait before retrying to prevent rapid error loops
                for _ in range(50):  # 5 second wait
                    if not self.refresh_running:
                        break
                    time.sleep(0.1)
    
    def _update_status(self):
        """Update status bar information"""
        try:
            instances = self.n8n_manager.list_instances()
            total = len(instances)
            running = sum(1 for i in instances if i.get('current_status') == 'running')
            
            self.instance_count_var.set(f"Instances: {running}/{total} running")
            
        except Exception as e:
            self.logger.error(f"Error updating status: {e}")
            self.instance_count_var.set("Instances: Error")
    
    def _update_docker_status(self):
        """Update Docker status indicator"""
        try:
            if self.docker_manager.is_docker_available():
                self.docker_status_label.config(text="Docker: Connected", style='Success.TLabel')
            else:
                self.docker_status_label.config(text="Docker: Disconnected", style='Error.TLabel')
        except Exception as e:
            self.logger.error(f"Error checking Docker status: {e}")
            self.docker_status_label.config(text="Docker: Error", style='Error.TLabel')
    
    def _safe_update_status(self):
        """Safe wrapper for updating status"""
        try:
            if self.refresh_running and self.root.winfo_exists():
                self._update_status()
        except (tk.TclError, AttributeError):
            # Window destroyed or not available
            pass
        except Exception as e:
            self.logger.error(f"Error in safe status update: {e}")
    
    def _safe_update_docker_status(self):
        """Safe wrapper for updating Docker status"""
        try:
            if self.refresh_running and self.root.winfo_exists():
                self._update_docker_status()
        except (tk.TclError, AttributeError):
            # Window destroyed or not available
            pass
        except Exception as e:
            self.logger.error(f"Error in safe Docker status update: {e}")
    
    def _safe_refresh_instances(self):
        """Safe wrapper for refreshing instances"""
        try:
            if self.refresh_running and self.root.winfo_exists() and self.instance_manager:
                self.instance_manager.refresh_instances()
        except (tk.TclError, AttributeError):
            # Window destroyed or not available
            pass
        except Exception as e:
            self.logger.error(f"Error in safe instance refresh: {e}")
    
    def _safe_refresh_logs(self):
        """Safe wrapper for refreshing logs"""
        try:
            if self.refresh_running and self.root.winfo_exists() and self.logs_viewer:
                self.logs_viewer.refresh_logs()
        except (tk.TclError, AttributeError):
            # Window destroyed or not available
            pass
        except Exception as e:
            self.logger.error(f"Error in safe logs refresh: {e}")
    
    def _on_tab_changed(self, event):
        """Handle tab change events"""
        current_tab = self.notebook.select()
        if current_tab:
            tab_text = self.notebook.tab(current_tab, "text")
            self.set_status(f"Switched to {tab_text} tab")
    
    # Menu and toolbar command handlers
    def _new_instance(self):
        """Create new instance"""
        if self.instance_manager:
            self.instance_manager.create_instance_dialog()
    
    def _start_selected_instance(self):
        """Start selected instance"""
        if self.instance_manager:
            self.instance_manager.start_selected_instance()
    
    def _stop_selected_instance(self):
        """Stop selected instance"""
        if self.instance_manager:
            self.instance_manager.stop_selected_instance()
    
    def _restart_selected_instance(self):
        """Restart selected instance"""
        if self.instance_manager:
            self.instance_manager.restart_selected_instance()
    
    def _clone_selected_instance(self):
        """Clone selected instance"""
        if self.instance_manager:
            self.instance_manager.clone_selected_instance()
    
    def _delete_selected_instance(self):
        """Delete selected instance"""
        if self.instance_manager:
            self.instance_manager.delete_selected_instance()
    
    def _import_config(self):
        """Import configuration"""
        file_path = filedialog.askopenfilename(
            title="Import Configuration",
            filetypes=[("YAML files", "*.yaml"), ("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            try:
                import yaml
                import json
                from pathlib import Path
                
                file_ext = Path(file_path).suffix.lower()
                
                with open(file_path, 'r') as f:
                    if file_ext == '.yaml' or file_ext == '.yml':
                        config_data = yaml.safe_load(f)
                    elif file_ext == '.json':
                        config_data = json.load(f)
                    else:
                        # Try to detect format
                        content = f.read()
                        try:
                            config_data = json.loads(content)
                        except:
                            config_data = yaml.safe_load(content)
                
                # Validate configuration structure
                if not isinstance(config_data, dict):
                    raise ValueError("Configuration must be a dictionary/object")
                
                # Import instances if present
                imported_count = 0
                if 'instances' in config_data:
                    for instance_config in config_data['instances']:
                        try:
                            name = instance_config.get('name')
                            if not name:
                                continue
                            
                            # Check if instance already exists
                            existing = self.n8n_manager.db.get_instance_by_name(name)
                            if existing:
                                result = messagebox.askyesnocancel(
                                    "Instance Exists",
                                    f"Instance '{name}' already exists. Overwrite?",
                                )
                                if result is None:  # Cancel
                                    break
                                elif not result:  # No, skip
                                    continue
                                else:  # Yes, delete existing
                                    self.n8n_manager.delete_instance(existing['id'], True)
                            
                            # Create instance
                            success, message, instance_id = self.n8n_manager.create_instance(
                                name, instance_config
                            )
                            if success:
                                imported_count += 1
                            else:
                                self.logger.warning(f"Failed to import instance '{name}': {message}")
                                
                        except Exception as e:
                            self.logger.error(f"Error importing instance: {e}")
                            continue
                
                # Import application settings if present
                if 'app_settings' in config_data:
                    try:
                        app_settings = config_data['app_settings']
                        # Update configuration manager with new settings
                        for key, value in app_settings.items():
                            self.config.set(key, value)
                        self.config.save()
                    except Exception as e:
                        self.logger.warning(f"Failed to import app settings: {e}")
                
                messagebox.showinfo(
                    "Import Complete",
                    f"Successfully imported {imported_count} instances from {Path(file_path).name}"
                )
                self.set_status(f"Imported {imported_count} instances from configuration")
                self.refresh_instance_list()
                
            except Exception as e:
                error_msg = f"Failed to import configuration: {e}"
                messagebox.showerror("Import Error", error_msg)
                self.set_status(error_msg)
    
    def _export_config(self):
        """Export configuration"""
        file_path = filedialog.asksaveasfilename(
            title="Export Configuration",
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml"), ("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            try:
                import yaml
                import json
                import time
                from pathlib import Path
                
                # Gather configuration data
                config_data = {
                    'export_info': {
                        'app_name': self.config.get('app.name', 'n8n Management App'),
                        'app_version': self.config.get('app.version', '1.0.0'),
                        'export_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'total_instances': 0
                    },
                    'instances': [],
                    'app_settings': {}
                }
                
                # Export instances
                instances = self.n8n_manager.list_instances()
                for instance in instances:
                    instance_config = {
                        'name': instance['name'],
                        'image': instance['image'],
                        'port': instance.get('port'),
                        'status': instance['status'],
                        'health_status': instance.get('health_status'),
                        'created_at': instance['created_at']
                    }
                    
                    # Add configuration details
                    try:
                        if instance.get('config'):
                            instance_config['config'] = json.loads(instance['config'])
                        if instance.get('environment_vars'):
                            instance_config['environment_vars'] = json.loads(instance['environment_vars'])
                        if instance.get('resource_limits'):
                            instance_config['resource_limits'] = json.loads(instance['resource_limits'])
                        if instance.get('volumes'):
                            instance_config['volumes'] = json.loads(instance['volumes'])
                        if instance.get('networks'):
                            instance_config['networks'] = json.loads(instance['networks'])
                    except:
                        pass  # Skip malformed JSON
                    
                    config_data['instances'].append(instance_config)
                
                config_data['export_info']['total_instances'] = len(instances)
                
                # Export application settings
                config_data['app_settings'] = {
                    'docker': {
                        'default_image': self.config.get('docker.default_image'),
                        'default_port_range': self.config.get('docker.default_port_range'),
                        'default_memory_limit': self.config.get('docker.default_memory_limit'),
                        'default_cpu_limit': self.config.get('docker.default_cpu_limit'),
                        'network_name': self.config.get('docker.network_name')
                    },
                    'ui': {
                        'theme': self.config.get('ui.theme'),
                        'auto_refresh_interval': self.config.get('ui.auto_refresh_interval'),
                        'window_width': self.config.get('ui.window_width'),
                        'window_height': self.config.get('ui.window_height')
                    },
                    'logging': {
                        'level': self.config.get('logging.level'),
                        'file_enabled': self.config.get('logging.file_enabled'),
                        'console_enabled': self.config.get('logging.console_enabled')
                    }
                }
                
                # Write configuration file
                file_ext = Path(file_path).suffix.lower()
                
                with open(file_path, 'w') as f:
                    if file_ext == '.yaml' or file_ext == '.yml':
                        yaml.dump(config_data, f, default_flow_style=False, indent=2)
                    else:  # Default to JSON
                        json.dump(config_data, f, indent=2, default=str)
                
                messagebox.showinfo(
                    "Export Complete",
                    f"Successfully exported {len(instances)} instances to {Path(file_path).name}"
                )
                self.set_status(f"Exported {len(instances)} instances to configuration file")
                
            except Exception as e:
                error_msg = f"Failed to export configuration: {e}"
                messagebox.showerror("Export Error", error_msg)
                self.set_status(error_msg)
    
    def _show_docker_info(self):
        """Show Docker information dialog"""
        try:
            docker_info = self.docker_manager.get_docker_info()
            
            info_window = tk.Toplevel(self.root)
            info_window.title("Docker Information")
            info_window.geometry("600x400")
            info_window.transient(self.root)
            info_window.grab_set()
            
            # Create text widget with scrollbar
            text_frame = ttk.Frame(info_window)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            text_widget = tk.Text(text_frame, wrap=tk.WORD)
            scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Display Docker info
            info_text = f"""Docker Daemon Information:

Server Version: {docker_info.get('server_version', 'Unknown')}
Containers Running: {docker_info.get('containers_running', 0)}
Total Containers: {docker_info.get('containers_total', 0)}
Images: {docker_info.get('images_count', 0)}

System Information:
{docker_info.get('daemon_info', {}).get('OperatingSystem', 'Unknown OS')}
Architecture: {docker_info.get('daemon_info', {}).get('Architecture', 'Unknown')}
CPUs: {docker_info.get('daemon_info', {}).get('NCPU', 'Unknown')}
Memory: {docker_info.get('daemon_info', {}).get('MemTotal', 0) / (1024**3):.1f} GB
"""
            
            text_widget.insert(tk.END, info_text)
            text_widget.config(state=tk.DISABLED)
            
            # Close button
            ttk.Button(
                info_window, 
                text="Close", 
                command=info_window.destroy
            ).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get Docker information: {e}")
    
    def _cleanup_docker(self):
        """Cleanup unused Docker resources"""
        if messagebox.askyesno("Confirm Cleanup", 
                              "This will remove unused containers, images, volumes, and networks. Continue?"):
            try:
                self.set_status("Cleaning up Docker resources...")
                stats = self.docker_manager.cleanup_unused_resources()
                
                message = f"""Cleanup completed:
- Containers removed: {stats['containers_removed']}
- Images removed: {stats['images_removed']}
- Volumes removed: {stats['volumes_removed']}
- Networks removed: {stats['networks_removed']}"""
                
                messagebox.showinfo("Cleanup Complete", message)
                self.set_status("Docker cleanup completed")
                
            except Exception as e:
                messagebox.showerror("Cleanup Error", f"Failed to cleanup Docker resources: {e}")
                self.set_status("Docker cleanup failed")
    
    def _refresh_all(self):
        """Refresh all data"""
        self.set_status("Refreshing all data...")
        
        # Update status indicators
        self._update_status()
        self._update_docker_status()
        
        # Refresh active tab
        current_tab = self.notebook.select()
        if current_tab:
            tab_text = self.notebook.tab(current_tab, "text")
            if tab_text == "Instances" and self.instance_manager:
                self.instance_manager.refresh_instances()
            elif tab_text == "Logs" and self.logs_viewer:
                self.logs_viewer.refresh_logs()
        
        self.set_status("Refresh completed")
    
    def _show_about(self):
        """Show about dialog"""
        about_text = f"""{self.config.get('app.name', 'n8n Management App')}
Version: {self.config.get('app.version', '1.0.0')}

A comprehensive desktop application for managing multiple n8n instances using Docker containers.

Features:
• Create and manage multiple n8n instances
• Real-time monitoring and logging
• Instance templates and cloning
• Backup and recovery system
• Advanced configuration management

© 2024 n8n Management App"""
        
        messagebox.showinfo("About", about_text)
    
    def _on_closing(self):
        """Handle window closing"""
        try:
            # Stop auto-refresh
            self.refresh_running = False
            
            # Cleanup components
            if self.logs_viewer:
                self.logs_viewer.cleanup()
            if self.performance_monitor:
                self.performance_monitor.cleanup()
            
            # Save window state
            try:
                geometry = self.root.geometry()
                self.config.set('ui.window_geometry', geometry)
                
                state = self.root.state()
                if state in ['zoomed', 'maximized']:
                    self.config.set('ui.window_state', 'maximized')
                else:
                    self.config.set('ui.window_state', 'normal')
                
                self.config.save()
            except Exception as e:
                self.logger.warning(f"Failed to save window state: {e}")
            
            self.logger.info("Closing application")
            self.root.quit()
            self.root.destroy()
            
        except Exception as e:
            self.logger.error(f"Error during window closing: {e}")
    
    # Public methods for other components
    def set_status(self, message: str):
        """Set status bar message"""
        self.status_var.set(message)
        self.logger.debug(f"Status: {message}")
    
    def get_selected_instance(self) -> Optional[Dict[str, Any]]:
        """Get currently selected instance from instance manager"""
        if self.instance_manager:
            return self.instance_manager.get_selected_instance()
        return None
    
    def refresh_instance_list(self):
        """Refresh the instance list"""
        if self.instance_manager:
            self.instance_manager.refresh_instances()
    
    def run(self):
        """Start the GUI application"""
        try:
            self.logger.info("Starting GUI main loop")
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