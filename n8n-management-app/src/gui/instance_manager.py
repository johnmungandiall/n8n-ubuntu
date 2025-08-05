"""
Instance Manager GUI Component
Provides interface for managing n8n instances
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Dict, List, Optional, Any
import json

from core.logger import get_logger
from core.config_manager import get_config
from core.n8n_manager import get_n8n_manager


class InstanceManagerFrame(ttk.Frame):
    """Frame for managing n8n instances"""
    
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.logger = get_logger()
        self.config = get_config()
        self.n8n_manager = get_n8n_manager()
        
        self.instance_tree = None
        self.selected_instance = None
        self.instance_data = {}
        
        self._create_widgets()
        self.refresh_instances()
    
    def _create_widgets(self):
        """Create the instance manager widgets"""
        # Main container with paned window
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Instance list
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=2)
        
        # Instance list header
        list_header = ttk.Frame(left_frame)
        list_header.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(list_header, text="n8n Instances", style='Title.TLabel').pack(side=tk.LEFT)
        
        # Instance list buttons
        button_frame = ttk.Frame(list_header)
        button_frame.pack(side=tk.RIGHT)
        
        ttk.Button(button_frame, text="New", command=self.create_instance_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Clone", command=self.clone_selected_instance).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Delete", command=self.delete_selected_instance).pack(side=tk.LEFT, padx=2)
        
        # Instance tree view
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview with scrollbars
        self.instance_tree = ttk.Treeview(tree_frame, columns=('status', 'port', 'health'), show='tree headings')
        
        # Configure columns
        self.instance_tree.heading('#0', text='Name')
        self.instance_tree.heading('status', text='Status')
        self.instance_tree.heading('port', text='Port')
        self.instance_tree.heading('health', text='Health')
        
        self.instance_tree.column('#0', width=200, minwidth=150)
        self.instance_tree.column('status', width=100, minwidth=80)
        self.instance_tree.column('port', width=80, minwidth=60)
        self.instance_tree.column('health', width=100, minwidth=80)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.instance_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.instance_tree.xview)
        self.instance_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.instance_tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bind events
        self.instance_tree.bind('<<TreeviewSelect>>', self._on_instance_select)
        self.instance_tree.bind('<Double-1>', self._on_instance_double_click)
        self.instance_tree.bind('<Button-3>', self._on_instance_right_click)
        
        # Right panel - Instance details and controls
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        # Instance details
        details_frame = ttk.LabelFrame(right_frame, text="Instance Details")
        details_frame.pack(fill=tk.BOTH, expand=True, padx=(5, 0), pady=(0, 5))
        
        # Details content
        self.details_text = tk.Text(details_frame, wrap=tk.WORD, height=15)
        details_scrollbar = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=details_scrollbar.set)
        
        self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        details_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Control buttons
        control_frame = ttk.LabelFrame(right_frame, text="Instance Controls")
        control_frame.pack(fill=tk.X, padx=(5, 0))
        
        # Control buttons grid
        control_grid = ttk.Frame(control_frame)
        control_grid.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(control_grid, text="Start", command=self.start_selected_instance).grid(row=0, column=0, padx=2, pady=2, sticky='ew')
        ttk.Button(control_grid, text="Stop", command=self.stop_selected_instance).grid(row=0, column=1, padx=2, pady=2, sticky='ew')
        ttk.Button(control_grid, text="Restart", command=self.restart_selected_instance).grid(row=0, column=2, padx=2, pady=2, sticky='ew')
        
        ttk.Button(control_grid, text="View Logs", command=self.view_instance_logs).grid(row=1, column=0, padx=2, pady=2, sticky='ew')
        ttk.Button(control_grid, text="Open n8n", command=self.open_instance_url).grid(row=1, column=1, padx=2, pady=2, sticky='ew')
        ttk.Button(control_grid, text="Configure", command=self.configure_instance).grid(row=1, column=2, padx=2, pady=2, sticky='ew')
        
        # Configure grid weights
        for i in range(3):
            control_grid.grid_columnconfigure(i, weight=1)
        
        # Create context menu
        self._create_context_menu()
    
    def _create_context_menu(self):
        """Create context menu for instance tree"""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Start", command=self.start_selected_instance)
        self.context_menu.add_command(label="Stop", command=self.stop_selected_instance)
        self.context_menu.add_command(label="Restart", command=self.restart_selected_instance)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="View Logs", command=self.view_instance_logs)
        self.context_menu.add_command(label="Open n8n", command=self.open_instance_url)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Clone", command=self.clone_selected_instance)
        self.context_menu.add_command(label="Configure", command=self.configure_instance)
        self.context_menu.add_command(label="Delete", command=self.delete_selected_instance)
    
    def refresh_instances(self):
        """Refresh the instance list"""
        try:
            # Clear existing items
            for item in self.instance_tree.get_children():
                self.instance_tree.delete(item)
            
            # Get instances from manager
            instances = self.n8n_manager.list_instances()
            self.instance_data = {str(instance['id']): instance for instance in instances}
            
            # Populate tree
            for instance in instances:
                instance_id = str(instance['id'])
                name = instance['name']
                status = instance.get('current_status', instance['status'])
                port = instance.get('port', 'N/A')
                health = instance.get('health_status', 'unknown')
                
                # Determine status color/icon
                status_display = self._format_status(status)
                health_display = self._format_health(health)
                
                self.instance_tree.insert('', 'end', iid=instance_id, text=name,
                                        values=(status_display, port, health_display))
            
            # Update details if an instance is selected
            if self.selected_instance:
                self._update_instance_details()
                
        except Exception as e:
            self.logger.error(f"Error refreshing instances: {e}")
            self.main_window.set_status(f"Error refreshing instances: {e}")
    
    def _format_status(self, status: str) -> str:
        """Format status for display"""
        status_map = {
            'running': '🟢 Running',
            'stopped': '🔴 Stopped',
            'paused': '🟡 Paused',
            'created': '🔵 Created',
            'failed': '❌ Failed',
            'unknown': '❓ Unknown'
        }
        return status_map.get(status, f"❓ {status}")
    
    def _format_health(self, health: str) -> str:
        """Format health status for display"""
        health_map = {
            'healthy': '✅ Healthy',
            'unhealthy': '❌ Unhealthy',
            'starting': '🔄 Starting',
            'stopped': '⏹️ Stopped',
            'unknown': '❓ Unknown'
        }
        return health_map.get(health, f"❓ {health}")
    
    def _on_instance_select(self, event):
        """Handle instance selection"""
        selection = self.instance_tree.selection()
        if selection:
            self.selected_instance = selection[0]
            self._update_instance_details()
        else:
            self.selected_instance = None
            self.details_text.delete(1.0, tk.END)
    
    def _on_instance_double_click(self, event):
        """Handle double-click on instance"""
        if self.selected_instance:
            self.open_instance_url()
    
    def _on_instance_right_click(self, event):
        """Handle right-click on instance"""
        # Select the item under cursor
        item = self.instance_tree.identify_row(event.y)
        if item:
            self.instance_tree.selection_set(item)
            self.selected_instance = item
            self._update_instance_details()
            
            # Show context menu
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()
    
    def _update_instance_details(self):
        """Update the instance details panel"""
        if not self.selected_instance or self.selected_instance not in self.instance_data:
            self.details_text.delete(1.0, tk.END)
            return
        
        instance = self.instance_data[self.selected_instance]
        
        # Get detailed status
        detailed_status = self.n8n_manager.get_instance_status(int(self.selected_instance))
        
        # Format details
        details = f"""Instance: {instance['name']}
ID: {instance['id']}
Image: {instance['image']}
Port: {instance.get('port', 'N/A')}
Status: {instance.get('current_status', instance['status'])}
Health: {instance.get('health_status', 'unknown')}
Created: {instance['created_at']}
Updated: {instance['updated_at']}

"""
        
        if 'container' in detailed_status:
            container = detailed_status['container']
            details += f"""Container ID: {container.get('id', 'N/A')[:12]}...
Container Status: {container.get('status', 'N/A')}
Started At: {container.get('started_at', 'N/A')}

"""
            
            if 'resource_usage' in container:
                usage = container['resource_usage']
                details += f"""Resource Usage:
CPU: {usage.get('cpu_percent', 0):.1f}%
Memory: {usage.get('memory_percent', 0):.1f}% ({usage.get('memory_usage', 0) / (1024**2):.1f} MB)
Network RX: {usage.get('network_rx_bytes', 0) / (1024**2):.1f} MB
Network TX: {usage.get('network_tx_bytes', 0) / (1024**2):.1f} MB

"""
        
        # Configuration details
        if instance.get('config'):
            try:
                config = json.loads(instance['config'])
                details += f"Configuration:\n{json.dumps(config, indent=2)}\n\n"
            except:
                details += f"Configuration: {instance['config']}\n\n"
        
        # Environment variables
        if instance.get('environment_vars'):
            try:
                env_vars = json.loads(instance['environment_vars'])
                details += f"Environment Variables:\n{json.dumps(env_vars, indent=2)}\n\n"
            except:
                details += f"Environment Variables: {instance['environment_vars']}\n\n"
        
        # Update text widget
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(1.0, details)
    
    def get_selected_instance(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected instance"""
        if self.selected_instance and self.selected_instance in self.instance_data:
            return self.instance_data[self.selected_instance]
        return None
    
    # Instance management methods
    def create_instance_dialog(self):
        """Show create instance dialog"""
        dialog = CreateInstanceDialog(self, self.main_window)
        if dialog.result:
            self.refresh_instances()
            self.main_window.set_status(f"Instance '{dialog.result}' created successfully")
    
    def start_selected_instance(self):
        """Start the selected instance"""
        if not self.selected_instance:
            messagebox.showwarning("No Selection", "Please select an instance to start.")
            return
        
        instance_id = int(self.selected_instance)
        instance = self.instance_data[self.selected_instance]
        
        try:
            self.main_window.set_status(f"Starting instance '{instance['name']}'...")
            success, message = self.n8n_manager.start_instance(instance_id)
            
            if success:
                self.main_window.set_status(message)
                self.refresh_instances()
            else:
                messagebox.showerror("Start Failed", message)
                self.main_window.set_status(f"Failed to start instance: {message}")
                
        except Exception as e:
            error_msg = f"Error starting instance: {e}"
            messagebox.showerror("Error", error_msg)
            self.main_window.set_status(error_msg)
    
    def stop_selected_instance(self):
        """Stop the selected instance"""
        if not self.selected_instance:
            messagebox.showwarning("No Selection", "Please select an instance to stop.")
            return
        
        instance_id = int(self.selected_instance)
        instance = self.instance_data[self.selected_instance]
        
        try:
            self.main_window.set_status(f"Stopping instance '{instance['name']}'...")
            success, message = self.n8n_manager.stop_instance(instance_id)
            
            if success:
                self.main_window.set_status(message)
                self.refresh_instances()
            else:
                messagebox.showerror("Stop Failed", message)
                self.main_window.set_status(f"Failed to stop instance: {message}")
                
        except Exception as e:
            error_msg = f"Error stopping instance: {e}"
            messagebox.showerror("Error", error_msg)
            self.main_window.set_status(error_msg)
    
    def restart_selected_instance(self):
        """Restart the selected instance"""
        if not self.selected_instance:
            messagebox.showwarning("No Selection", "Please select an instance to restart.")
            return
        
        instance_id = int(self.selected_instance)
        instance = self.instance_data[self.selected_instance]
        
        try:
            self.main_window.set_status(f"Restarting instance '{instance['name']}'...")
            success, message = self.n8n_manager.restart_instance(instance_id)
            
            if success:
                self.main_window.set_status(message)
                self.refresh_instances()
            else:
                messagebox.showerror("Restart Failed", message)
                self.main_window.set_status(f"Failed to restart instance: {message}")
                
        except Exception as e:
            error_msg = f"Error restarting instance: {e}"
            messagebox.showerror("Error", error_msg)
            self.main_window.set_status(error_msg)
    
    def clone_selected_instance(self):
        """Clone the selected instance"""
        if not self.selected_instance:
            messagebox.showwarning("No Selection", "Please select an instance to clone.")
            return
        
        instance = self.instance_data[self.selected_instance]
        
        # Get new name
        new_name = simpledialog.askstring(
            "Clone Instance",
            f"Enter name for cloned instance:",
            initialvalue=f"{instance['name']}_clone"
        )
        
        if not new_name:
            return
        
        # Ask about data cloning
        clone_data = messagebox.askyesno(
            "Clone Data",
            "Do you want to clone the instance data as well?\n\n"
            "Yes: Clone configuration and data\n"
            "No: Clone configuration only"
        )
        
        try:
            instance_id = int(self.selected_instance)
            self.main_window.set_status(f"Cloning instance '{instance['name']}'...")
            
            success, message, new_instance_id = self.n8n_manager.clone_instance(
                instance_id, new_name, clone_data
            )
            
            if success:
                self.main_window.set_status(message)
                self.refresh_instances()
            else:
                messagebox.showerror("Clone Failed", message)
                self.main_window.set_status(f"Failed to clone instance: {message}")
                
        except Exception as e:
            error_msg = f"Error cloning instance: {e}"
            messagebox.showerror("Error", error_msg)
            self.main_window.set_status(error_msg)
    
    def delete_selected_instance(self):
        """Delete the selected instance"""
        if not self.selected_instance:
            messagebox.showwarning("No Selection", "Please select an instance to delete.")
            return
        
        instance = self.instance_data[self.selected_instance]
        
        # Confirm deletion
        result = messagebox.askyesnocancel(
            "Confirm Deletion",
            f"Are you sure you want to delete instance '{instance['name']}'?\n\n"
            "Yes: Delete instance and keep data\n"
            "No: Delete instance and remove all data\n"
            "Cancel: Don't delete"
        )
        
        if result is None:  # Cancel
            return
        
        remove_data = not result  # No = remove data, Yes = keep data
        
        try:
            instance_id = int(self.selected_instance)
            self.main_window.set_status(f"Deleting instance '{instance['name']}'...")
            
            success, message = self.n8n_manager.delete_instance(instance_id, remove_data)
            
            if success:
                self.main_window.set_status(message)
                self.selected_instance = None
                self.refresh_instances()
            else:
                messagebox.showerror("Delete Failed", message)
                self.main_window.set_status(f"Failed to delete instance: {message}")
                
        except Exception as e:
            error_msg = f"Error deleting instance: {e}"
            messagebox.showerror("Error", error_msg)
            self.main_window.set_status(error_msg)
    
    def view_instance_logs(self):
        """View logs for the selected instance"""
        if not self.selected_instance:
            messagebox.showwarning("No Selection", "Please select an instance to view logs.")
            return
        
        # Switch to logs tab and set instance
        self.main_window.notebook.select(1)  # Logs tab
        if hasattr(self.main_window, 'logs_viewer'):
            self.main_window.logs_viewer.set_instance(int(self.selected_instance))
    
    def open_instance_url(self):
        """Open the instance URL in browser"""
        if not self.selected_instance:
            messagebox.showwarning("No Selection", "Please select an instance to open.")
            return
        
        instance = self.instance_data[self.selected_instance]
        port = instance.get('port')
        
        if not port:
            messagebox.showwarning("No Port", "Instance has no port configured.")
            return
        
        url = f"http://localhost:{port}"
        
        try:
            import webbrowser
            webbrowser.open(url)
            self.main_window.set_status(f"Opened {url} in browser")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open URL: {e}")
    
    def configure_instance(self):
        """Configure the selected instance"""
        if not self.selected_instance:
            messagebox.showwarning("No Selection", "Please select an instance to configure.")
            return
        
        # TODO: Implement instance configuration dialog
        messagebox.showinfo("Not Implemented", "Instance configuration dialog not yet implemented.")


class CreateInstanceDialog:
    """Dialog for creating new instances"""
    
    def __init__(self, parent, main_window):
        self.parent = parent
        self.main_window = main_window
        self.logger = get_logger()
        self.config = get_config()
        self.n8n_manager = get_n8n_manager()
        
        self.result = None
        self.dialog = None
        
        self._create_dialog()
    
    def _create_dialog(self):
        """Create the dialog window"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Create New n8n Instance")
        self.dialog.geometry("500x400")
        self.dialog.transient(self.main_window.root)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - self.dialog.winfo_width()) // 2
        y = (self.dialog.winfo_screenheight() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        # Main frame
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Instance name
        ttk.Label(main_frame, text="Instance Name:").grid(row=0, column=0, sticky='w', pady=5)
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=30)
        name_entry.grid(row=0, column=1, sticky='ew', pady=5, padx=(10, 0))
        name_entry.focus()
        
        # Docker image
        ttk.Label(main_frame, text="Docker Image:").grid(row=1, column=0, sticky='w', pady=5)
        self.image_var = tk.StringVar(value=self.config.get('docker.default_image', 'n8nio/n8n:latest'))
        ttk.Entry(main_frame, textvariable=self.image_var, width=30).grid(row=1, column=1, sticky='ew', pady=5, padx=(10, 0))
        
        # Port (auto-assigned by default)
        ttk.Label(main_frame, text="Port:").grid(row=2, column=0, sticky='w', pady=5)
        port_frame = ttk.Frame(main_frame)
        port_frame.grid(row=2, column=1, sticky='ew', pady=5, padx=(10, 0))
        
        self.auto_port_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(port_frame, text="Auto-assign", variable=self.auto_port_var,
                       command=self._toggle_port_entry).pack(side=tk.LEFT)
        
        self.port_var = tk.StringVar()
        self.port_entry = ttk.Entry(port_frame, textvariable=self.port_var, width=10, state='disabled')
        self.port_entry.pack(side=tk.RIGHT)
        
        # Environment variables
        ttk.Label(main_frame, text="Environment Variables:").grid(row=3, column=0, sticky='nw', pady=5)
        env_frame = ttk.Frame(main_frame)
        env_frame.grid(row=3, column=1, sticky='ew', pady=5, padx=(10, 0))
        
        self.env_text = tk.Text(env_frame, height=8, width=40)
        env_scrollbar = ttk.Scrollbar(env_frame, orient=tk.VERTICAL, command=self.env_text.yview)
        self.env_text.configure(yscrollcommand=env_scrollbar.set)
        
        self.env_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        env_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Default environment variables
        default_env = """N8N_HOST=0.0.0.0
N8N_PORT=5678
N8N_PROTOCOL=http
NODE_ENV=production"""
        self.env_text.insert(1.0, default_env)
        
        # Configure grid weights
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(button_frame, text="Cancel", command=self._cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Create", command=self._create).pack(side=tk.RIGHT)
        
        # Bind Enter key
        self.dialog.bind('<Return>', lambda e: self._create())
        self.dialog.bind('<Escape>', lambda e: self._cancel())
        
        # Wait for dialog
        self.dialog.wait_window()
    
    def _toggle_port_entry(self):
        """Toggle port entry based on auto-assign checkbox"""
        if self.auto_port_var.get():
            self.port_entry.config(state='disabled')
        else:
            self.port_entry.config(state='normal')
    
    def _create(self):
        """Create the instance"""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Instance name is required.")
            return
        
        # Validate name
        if not self._validate_name(name):
            messagebox.showerror("Error", 
                               "Invalid instance name. Use only letters, numbers, hyphens, and underscores.")
            return
        
        # Prepare configuration
        config = {
            'image': self.image_var.get().strip(),
            'environment_vars': self._parse_environment_vars()
        }
        
        # Add port if specified
        if not self.auto_port_var.get():
            try:
                port = int(self.port_var.get())
                if port < 1 or port > 65535:
                    raise ValueError("Port must be between 1 and 65535")
                config['port'] = port
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid port: {e}")
                return
        
        try:
            success, message, instance_id = self.n8n_manager.create_instance(name, config)
            
            if success:
                self.result = name
                self.dialog.destroy()
            else:
                messagebox.showerror("Creation Failed", message)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create instance: {e}")
    
    def _cancel(self):
        """Cancel dialog"""
        self.dialog.destroy()
    
    def _validate_name(self, name: str) -> bool:
        """Validate instance name"""
        import re
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', name)) and len(name) >= 3
    
    def _parse_environment_vars(self) -> Dict[str, str]:
        """Parse environment variables from text"""
        env_vars = {}
        text = self.env_text.get(1.0, tk.END).strip()
        
        for line in text.split('\n'):
            line = line.strip()
            if line and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
        
        return env_vars