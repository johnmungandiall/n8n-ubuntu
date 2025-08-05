"""
Logs Viewer GUI Component
Provides interface for viewing instance logs and application logs
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, List, Optional, Any
import threading
import time
from datetime import datetime

from core.logger import get_logger
from core.config_manager import get_config
from core.n8n_manager import get_n8n_manager
from core.database import get_database


class LogsViewerFrame(ttk.Frame):
    """Frame for viewing logs"""
    
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.logger = get_logger()
        self.config = get_config()
        self.n8n_manager = get_n8n_manager()
        self.database = get_database()
        
        self.current_instance_id = None
        self.auto_refresh = False
        self.refresh_thread = None
        self.refresh_running = False
        
        self._create_widgets()
        # Defer initial refresh to avoid blocking GUI initialization
        self.after_idle(self.refresh_logs)
    
    def _create_widgets(self):
        """Create the logs viewer widgets"""
        # Control panel
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Instance selection
        ttk.Label(control_frame, text="Instance:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.instance_var = tk.StringVar()
        self.instance_combo = ttk.Combobox(control_frame, textvariable=self.instance_var, 
                                          state='readonly', width=20)
        self.instance_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.instance_combo.bind('<<ComboboxSelected>>', self._on_instance_changed)
        
        # Log type selection
        ttk.Label(control_frame, text="Log Type:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.log_type_var = tk.StringVar(value="container")
        log_type_combo = ttk.Combobox(control_frame, textvariable=self.log_type_var,
                                     values=["container", "application", "audit"], 
                                     state='readonly', width=12)
        log_type_combo.pack(side=tk.LEFT, padx=(0, 10))
        log_type_combo.bind('<<ComboboxSelected>>', self._on_log_type_changed)
        
        # Control buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(side=tk.RIGHT)
        
        self.auto_refresh_var = tk.BooleanVar()
        ttk.Checkbutton(button_frame, text="Auto Refresh", variable=self.auto_refresh_var,
                       command=self._toggle_auto_refresh).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Refresh", command=self.refresh_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Clear", command=self._clear_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Save", command=self._save_logs).pack(side=tk.LEFT, padx=2)
        
        # Log display area
        log_frame = ttk.Frame(self)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        # Create text widget with scrollbars
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, font=('Consolas', 9))
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        h_scrollbar = ttk.Scrollbar(log_frame, orient=tk.HORIZONTAL, command=self.log_text.xview)
        self.log_text.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack text widget and scrollbars
        self.log_text.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        # Configure text tags for different log levels
        self.log_text.tag_configure('ERROR', foreground='red')
        self.log_text.tag_configure('WARNING', foreground='orange')
        self.log_text.tag_configure('INFO', foreground='blue')
        self.log_text.tag_configure('DEBUG', foreground='gray')
        self.log_text.tag_configure('timestamp', foreground='purple')
        
        # Status bar
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, padx=5)
        
        self.log_status_var = tk.StringVar()
        self.log_status_var.set("Ready")
        ttk.Label(status_frame, textvariable=self.log_status_var, 
                 style='Status.TLabel').pack(side=tk.LEFT)
        
        self.log_count_var = tk.StringVar()
        ttk.Label(status_frame, textvariable=self.log_count_var, 
                 style='Status.TLabel').pack(side=tk.RIGHT)
        
        # Initialize instance list
        self._update_instance_list()
    
    def _update_instance_list(self):
        """Update the instance dropdown list"""
        try:
            instances = self.n8n_manager.list_instances()
            instance_names = ["All Instances"] + [f"{inst['name']} (ID: {inst['id']})" for inst in instances]
            
            self.instance_combo['values'] = instance_names
            
            # Set default selection
            if not self.instance_var.get() and instance_names:
                self.instance_var.set(instance_names[0])
                
        except Exception as e:
            self.logger.error(f"Error updating instance list: {e}")
    
    def _on_instance_changed(self, event=None):
        """Handle instance selection change"""
        selection = self.instance_var.get()
        
        if selection == "All Instances":
            self.current_instance_id = None
        else:
            # Extract instance ID from selection
            try:
                # Format: "name (ID: 123)"
                id_part = selection.split("(ID: ")[1].rstrip(")")
                self.current_instance_id = int(id_part)
            except (IndexError, ValueError):
                self.current_instance_id = None
        
        self.refresh_logs()
    
    def _on_log_type_changed(self, event=None):
        """Handle log type selection change"""
        self.refresh_logs()
    
    def _toggle_auto_refresh(self):
        """Toggle auto-refresh functionality"""
        self.auto_refresh = self.auto_refresh_var.get()
        
        if self.auto_refresh:
            self._start_auto_refresh()
        else:
            self._stop_auto_refresh()
    
    def _start_auto_refresh(self):
        """Start auto-refresh thread"""
        if not self.refresh_running:
            self.refresh_running = True
            self.refresh_thread = threading.Thread(target=self._auto_refresh_worker, daemon=True)
            self.refresh_thread.start()
    
    def _stop_auto_refresh(self):
        """Stop auto-refresh thread"""
        self.refresh_running = False
    
    def _auto_refresh_worker(self):
        """Auto-refresh worker thread"""
        while self.refresh_running and self.auto_refresh:
            try:
                # Use smaller sleep intervals for more responsive shutdown
                for _ in range(20):  # 2 seconds in 0.1 second intervals
                    if not self.refresh_running or not self.auto_refresh:
                        break
                    time.sleep(0.1)
                
                if self.refresh_running and self.auto_refresh:
                    try:
                        self.after(0, self._safe_refresh_logs)
                    except tk.TclError:
                        # Widget has been destroyed
                        break
            except Exception as e:
                self.logger.error(f"Error in auto-refresh worker: {e}")
                # Wait before retrying to prevent rapid error loops
                for _ in range(50):  # 5 second wait
                    if not self.refresh_running or not self.auto_refresh:
                        break
                    time.sleep(0.1)
    
    def refresh_logs(self):
        """Refresh the log display"""
        try:
            self.log_status_var.set("Loading logs...")
            
            # Update instance list first
            self._update_instance_list()
            
            log_type = self.log_type_var.get()
            
            if log_type == "container":
                self._load_container_logs()
            elif log_type == "application":
                self._load_application_logs()
            elif log_type == "audit":
                self._load_audit_logs()
            
        except Exception as e:
            self.logger.error(f"Error refreshing logs: {e}")
            self.log_status_var.set(f"Error: {e}")
    
    def _load_container_logs(self):
        """Load container logs"""
        if self.current_instance_id is None:
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, "Select an instance to view container logs.\n")
            self.log_status_var.set("No instance selected")
            self.log_count_var.set("")
            return
        
        try:
            logs = self.n8n_manager.get_instance_logs(self.current_instance_id, tail=500)
            
            self.log_text.delete(1.0, tk.END)
            
            if logs:
                # Parse and format logs
                lines = logs.split('\n')
                for line in lines:
                    if line.strip():
                        self._insert_log_line(line)
                
                # Auto-scroll to bottom
                self.log_text.see(tk.END)
                
                self.log_count_var.set(f"{len([l for l in lines if l.strip()])} lines")
            else:
                self.log_text.insert(tk.END, "No logs available for this instance.\n")
                self.log_count_var.set("0 lines")
            
            self.log_status_var.set("Container logs loaded")
            
        except Exception as e:
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, f"Error loading container logs: {e}\n")
            self.log_status_var.set(f"Error: {e}")
            self.log_count_var.set("")
    
    def _load_application_logs(self):
        """Load application logs"""
        try:
            # Read application log file
            log_file_path = self.config.get('logging.file_path', 'data/logs/app.log')
            
            try:
                with open(log_file_path, 'r') as f:
                    # Read last 1000 lines
                    lines = f.readlines()
                    recent_lines = lines[-1000:] if len(lines) > 1000 else lines
                
                self.log_text.delete(1.0, tk.END)
                
                for line in recent_lines:
                    self._insert_log_line(line.rstrip())
                
                # Auto-scroll to bottom
                self.log_text.see(tk.END)
                
                self.log_count_var.set(f"{len(recent_lines)} lines")
                self.log_status_var.set("Application logs loaded")
                
            except FileNotFoundError:
                self.log_text.delete(1.0, tk.END)
                self.log_text.insert(tk.END, f"Application log file not found: {log_file_path}\n")
                self.log_status_var.set("Log file not found")
                self.log_count_var.set("")
                
        except Exception as e:
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, f"Error loading application logs: {e}\n")
            self.log_status_var.set(f"Error: {e}")
            self.log_count_var.set("")
    
    def _load_audit_logs(self):
        """Load audit logs from database"""
        try:
            # Get audit logs from database
            logs = self.database.get_logs(
                instance_id=self.current_instance_id,
                limit=500
            )
            
            self.log_text.delete(1.0, tk.END)
            
            if logs:
                for log_entry in logs:
                    timestamp = log_entry['timestamp']
                    level = log_entry['level']
                    component = log_entry['component']
                    action = log_entry['action']
                    message = log_entry['message']
                    instance_id = log_entry['instance_id']
                    
                    # Format log line
                    if instance_id:
                        log_line = f"[{timestamp}] {level} - {component}.{action} (Instance {instance_id}): {message}"
                    else:
                        log_line = f"[{timestamp}] {level} - {component}.{action}: {message}"
                    
                    self._insert_log_line(log_line)
                
                # Auto-scroll to bottom
                self.log_text.see(tk.END)
                
                self.log_count_var.set(f"{len(logs)} entries")
            else:
                self.log_text.insert(tk.END, "No audit logs available.\n")
                self.log_count_var.set("0 entries")
            
            self.log_status_var.set("Audit logs loaded")
            
        except Exception as e:
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, f"Error loading audit logs: {e}\n")
            self.log_status_var.set(f"Error: {e}")
            self.log_count_var.set("")
    
    def _insert_log_line(self, line: str):
        """Insert a log line with appropriate formatting"""
        if not line.strip():
            return
        
        # Detect log level and apply appropriate tag
        line_upper = line.upper()
        tag = None
        
        if 'ERROR' in line_upper or 'CRITICAL' in line_upper:
            tag = 'ERROR'
        elif 'WARNING' in line_upper or 'WARN' in line_upper:
            tag = 'WARNING'
        elif 'INFO' in line_upper:
            tag = 'INFO'
        elif 'DEBUG' in line_upper:
            tag = 'DEBUG'
        
        # Insert timestamp with special formatting if present
        if line.startswith('[') or line.startswith('20'):  # Common timestamp patterns
            # Try to extract timestamp
            timestamp_end = -1
            for i, char in enumerate(line):
                if char in [']', ' '] and i > 10:  # Reasonable timestamp length
                    timestamp_end = i
                    break
            
            if timestamp_end > 0:
                timestamp_part = line[:timestamp_end + 1]
                rest_part = line[timestamp_end + 1:]
                
                self.log_text.insert(tk.END, timestamp_part, 'timestamp')
                if tag:
                    self.log_text.insert(tk.END, rest_part + '\n', tag)
                else:
                    self.log_text.insert(tk.END, rest_part + '\n')
            else:
                if tag:
                    self.log_text.insert(tk.END, line + '\n', tag)
                else:
                    self.log_text.insert(tk.END, line + '\n')
        else:
            if tag:
                self.log_text.insert(tk.END, line + '\n', tag)
            else:
                self.log_text.insert(tk.END, line + '\n')
    
    def _clear_logs(self):
        """Clear the log display"""
        self.log_text.delete(1.0, tk.END)
        self.log_count_var.set("0 lines")
        self.log_status_var.set("Logs cleared")
    
    def _save_logs(self):
        """Save current logs to file"""
        try:
            file_path = filedialog.asksaveasfilename(
                title="Save Logs",
                defaultextension=".log",
                filetypes=[
                    ("Log files", "*.log"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ]
            )
            
            if file_path:
                content = self.log_text.get(1.0, tk.END)
                
                with open(file_path, 'w') as f:
                    f.write(content)
                
                self.log_status_var.set(f"Logs saved to {file_path}")
                messagebox.showinfo("Success", f"Logs saved to {file_path}")
                
        except Exception as e:
            error_msg = f"Error saving logs: {e}"
            self.log_status_var.set(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def set_instance(self, instance_id: int):
        """Set the current instance for log viewing"""
        try:
            # Update instance list first
            self._update_instance_list()
            
            # Find and select the instance
            instances = self.n8n_manager.list_instances()
            for instance in instances:
                if instance['id'] == instance_id:
                    selection = f"{instance['name']} (ID: {instance['id']})"
                    self.instance_var.set(selection)
                    self.current_instance_id = instance_id
                    self.refresh_logs()
                    break
            
        except Exception as e:
            self.logger.error(f"Error setting instance {instance_id}: {e}")
    
    def _safe_refresh_logs(self):
        """Safe wrapper for refreshing logs"""
        try:
            if self.refresh_running and self.winfo_exists():
                self.refresh_logs()
        except (tk.TclError, AttributeError):
            # Widget destroyed or not available
            pass
        except Exception as e:
            self.logger.error(f"Error in safe logs refresh: {e}")
    
    def cleanup(self):
        """Cleanup when frame is destroyed"""
        self._stop_auto_refresh()