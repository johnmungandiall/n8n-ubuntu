"""
Performance Monitor GUI Component
Provides real-time monitoring of system and instance performance metrics
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional, Any
import threading
import time
import psutil
from datetime import datetime, timedelta
import json

from core.logger import get_logger
from core.config_manager import get_config
from core.n8n_manager import get_n8n_manager
from core.database import get_database


class PerformanceMonitorFrame(ttk.Frame):
    """Frame for monitoring performance metrics"""
    
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.logger = get_logger()
        self.config = get_config()
        self.n8n_manager = get_n8n_manager()
        self.database = get_database()
        
        self.monitoring_active = False
        self.monitor_thread = None
        self.metrics_history = {}
        self.max_history_points = 100
        
        self._create_widgets()
        self._start_monitoring()
    
    def _create_widgets(self):
        """Create the performance monitor widgets"""
        # Control panel
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Monitoring controls
        self.monitoring_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Enable Monitoring", 
                       variable=self.monitoring_var,
                       command=self._toggle_monitoring).pack(side=tk.LEFT, padx=5)
        
        # Refresh interval
        ttk.Label(control_frame, text="Refresh Interval:").pack(side=tk.LEFT, padx=(20, 5))
        self.interval_var = tk.StringVar(value="2")
        interval_combo = ttk.Combobox(control_frame, textvariable=self.interval_var,
                                     values=["1", "2", "5", "10"], width=5, state='readonly')
        interval_combo.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(control_frame, text="seconds").pack(side=tk.LEFT)
        
        # Export button
        ttk.Button(control_frame, text="Export Metrics", 
                  command=self._export_metrics).pack(side=tk.RIGHT, padx=5)
        
        # Create notebook for different metric categories
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # System metrics tab
        self._create_system_metrics_tab()
        
        # Instance metrics tab
        self._create_instance_metrics_tab()
        
        # Network metrics tab
        self._create_network_metrics_tab()
        
        # Disk metrics tab
        self._create_disk_metrics_tab()
        
        # Status bar
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, padx=5)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Monitoring active")
        ttk.Label(status_frame, textvariable=self.status_var, 
                 style='Status.TLabel').pack(side=tk.LEFT)
        
        self.last_update_var = tk.StringVar()
        ttk.Label(status_frame, textvariable=self.last_update_var, 
                 style='Status.TLabel').pack(side=tk.RIGHT)
    
    def _create_system_metrics_tab(self):
        """Create system metrics monitoring tab"""
        system_frame = ttk.Frame(self.notebook)
        self.notebook.add(system_frame, text="System")
        
        # CPU metrics
        cpu_frame = ttk.LabelFrame(system_frame, text="CPU Usage", padding=10)
        cpu_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.cpu_overall_var = tk.StringVar()
        ttk.Label(cpu_frame, text="Overall:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(cpu_frame, textvariable=self.cpu_overall_var).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        self.cpu_cores_frame = ttk.Frame(cpu_frame)
        self.cpu_cores_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        # Memory metrics
        memory_frame = ttk.LabelFrame(system_frame, text="Memory Usage", padding=10)
        memory_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.memory_used_var = tk.StringVar()
        self.memory_available_var = tk.StringVar()
        self.memory_percent_var = tk.StringVar()
        
        ttk.Label(memory_frame, text="Used:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(memory_frame, textvariable=self.memory_used_var).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(memory_frame, text="Available:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(memory_frame, textvariable=self.memory_available_var).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(memory_frame, text="Percentage:").grid(row=2, column=0, sticky=tk.W)
        ttk.Label(memory_frame, textvariable=self.memory_percent_var).grid(row=2, column=1, sticky=tk.W, padx=(10, 0))
        
        # System load
        load_frame = ttk.LabelFrame(system_frame, text="System Load", padding=10)
        load_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.load_1min_var = tk.StringVar()
        self.load_5min_var = tk.StringVar()
        self.load_15min_var = tk.StringVar()
        
        ttk.Label(load_frame, text="1 min:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(load_frame, textvariable=self.load_1min_var).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(load_frame, text="5 min:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(load_frame, textvariable=self.load_5min_var).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(load_frame, text="15 min:").grid(row=2, column=0, sticky=tk.W)
        ttk.Label(load_frame, textvariable=self.load_15min_var).grid(row=2, column=1, sticky=tk.W, padx=(10, 0))
    
    def _create_instance_metrics_tab(self):
        """Create instance-specific metrics tab"""
        instance_frame = ttk.Frame(self.notebook)
        self.notebook.add(instance_frame, text="Instances")
        
        # Instance selection
        selection_frame = ttk.Frame(instance_frame)
        selection_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(selection_frame, text="Instance:").pack(side=tk.LEFT)
        self.instance_var = tk.StringVar()
        self.instance_combo = ttk.Combobox(selection_frame, textvariable=self.instance_var,
                                          state='readonly', width=30)
        self.instance_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.instance_combo.bind('<<ComboboxSelected>>', self._on_instance_selected)
        
        # Instance metrics display
        metrics_frame = ttk.Frame(instance_frame)
        metrics_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Container status
        status_frame = ttk.LabelFrame(metrics_frame, text="Container Status", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.container_status_var = tk.StringVar()
        self.container_uptime_var = tk.StringVar()
        self.container_restart_count_var = tk.StringVar()
        
        ttk.Label(status_frame, text="Status:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.container_status_var).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(status_frame, text="Uptime:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.container_uptime_var).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(status_frame, text="Restart Count:").grid(row=2, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.container_restart_count_var).grid(row=2, column=1, sticky=tk.W, padx=(10, 0))
        
        # Resource usage
        resource_frame = ttk.LabelFrame(metrics_frame, text="Resource Usage", padding=10)
        resource_frame.pack(fill=tk.X, pady=5)
        
        self.instance_cpu_var = tk.StringVar()
        self.instance_memory_var = tk.StringVar()
        self.instance_memory_limit_var = tk.StringVar()
        
        ttk.Label(resource_frame, text="CPU:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(resource_frame, textvariable=self.instance_cpu_var).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(resource_frame, text="Memory:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(resource_frame, textvariable=self.instance_memory_var).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(resource_frame, text="Memory Limit:").grid(row=2, column=0, sticky=tk.W)
        ttk.Label(resource_frame, textvariable=self.instance_memory_limit_var).grid(row=2, column=1, sticky=tk.W, padx=(10, 0))
        
        # Network I/O
        network_frame = ttk.LabelFrame(metrics_frame, text="Network I/O", padding=10)
        network_frame.pack(fill=tk.X, pady=5)
        
        self.instance_net_rx_var = tk.StringVar()
        self.instance_net_tx_var = tk.StringVar()
        
        ttk.Label(network_frame, text="RX Bytes:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(network_frame, textvariable=self.instance_net_rx_var).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(network_frame, text="TX Bytes:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(network_frame, textvariable=self.instance_net_tx_var).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
    
    def _create_network_metrics_tab(self):
        """Create network metrics tab"""
        network_frame = ttk.Frame(self.notebook)
        self.notebook.add(network_frame, text="Network")
        
        # Network interfaces
        interfaces_frame = ttk.LabelFrame(network_frame, text="Network Interfaces", padding=10)
        interfaces_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create treeview for network interfaces
        columns = ('Interface', 'Bytes Sent', 'Bytes Recv', 'Packets Sent', 'Packets Recv', 'Errors')
        self.network_tree = ttk.Treeview(interfaces_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.network_tree.heading(col, text=col)
            self.network_tree.column(col, width=120)
        
        # Scrollbar for network tree
        net_scrollbar = ttk.Scrollbar(interfaces_frame, orient=tk.VERTICAL, command=self.network_tree.yview)
        self.network_tree.configure(yscrollcommand=net_scrollbar.set)
        
        self.network_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        net_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Network summary
        summary_frame = ttk.LabelFrame(network_frame, text="Network Summary", padding=10)
        summary_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.total_bytes_sent_var = tk.StringVar()
        self.total_bytes_recv_var = tk.StringVar()
        self.active_connections_var = tk.StringVar()
        
        ttk.Label(summary_frame, text="Total Bytes Sent:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(summary_frame, textvariable=self.total_bytes_sent_var).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(summary_frame, text="Total Bytes Received:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(summary_frame, textvariable=self.total_bytes_recv_var).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(summary_frame, text="Active Connections:").grid(row=2, column=0, sticky=tk.W)
        ttk.Label(summary_frame, textvariable=self.active_connections_var).grid(row=2, column=1, sticky=tk.W, padx=(10, 0))
    
    def _create_disk_metrics_tab(self):
        """Create disk metrics tab"""
        disk_frame = ttk.Frame(self.notebook)
        self.notebook.add(disk_frame, text="Disk")
        
        # Disk usage
        usage_frame = ttk.LabelFrame(disk_frame, text="Disk Usage", padding=10)
        usage_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create treeview for disk usage
        columns = ('Device', 'Mountpoint', 'Total', 'Used', 'Free', 'Percentage')
        self.disk_tree = ttk.Treeview(usage_frame, columns=columns, show='headings', height=6)
        
        for col in columns:
            self.disk_tree.heading(col, text=col)
            self.disk_tree.column(col, width=120)
        
        # Scrollbar for disk tree
        disk_scrollbar = ttk.Scrollbar(usage_frame, orient=tk.VERTICAL, command=self.disk_tree.yview)
        self.disk_tree.configure(yscrollcommand=disk_scrollbar.set)
        
        self.disk_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        disk_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Disk I/O
        io_frame = ttk.LabelFrame(disk_frame, text="Disk I/O", padding=10)
        io_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.disk_read_var = tk.StringVar()
        self.disk_write_var = tk.StringVar()
        self.disk_read_time_var = tk.StringVar()
        self.disk_write_time_var = tk.StringVar()
        
        ttk.Label(io_frame, text="Read Bytes:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(io_frame, textvariable=self.disk_read_var).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(io_frame, text="Write Bytes:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(io_frame, textvariable=self.disk_write_var).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(io_frame, text="Read Time:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        ttk.Label(io_frame, textvariable=self.disk_read_time_var).grid(row=0, column=3, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(io_frame, text="Write Time:").grid(row=1, column=2, sticky=tk.W, padx=(20, 0))
        ttk.Label(io_frame, textvariable=self.disk_write_time_var).grid(row=1, column=3, sticky=tk.W, padx=(10, 0))
    
    def _toggle_monitoring(self):
        """Toggle monitoring on/off"""
        if self.monitoring_var.get():
            self._start_monitoring()
        else:
            self._stop_monitoring()
    
    def _start_monitoring(self):
        """Start the monitoring thread"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_worker, daemon=True)
            self.monitor_thread.start()
            self.status_var.set("Monitoring active")
    
    def _stop_monitoring(self):
        """Stop the monitoring thread"""
        self.monitoring_active = False
        self.status_var.set("Monitoring stopped")
    
    def _monitor_worker(self):
        """Main monitoring worker thread"""
        while self.monitoring_active:
            try:
                # Update metrics
                self.after(0, self._update_metrics)
                
                # Sleep for the specified interval
                interval = float(self.interval_var.get())
                time.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring worker: {e}")
                time.sleep(5)  # Wait before retrying
    
    def _update_metrics(self):
        """Update all metrics displays"""
        try:
            current_time = datetime.now()
            
            # Update system metrics
            self._update_system_metrics()
            
            # Update instance metrics
            self._update_instance_metrics()
            
            # Update network metrics
            self._update_network_metrics()
            
            # Update disk metrics
            self._update_disk_metrics()
            
            # Update instance list
            self._update_instance_list()
            
            # Update last update time
            self.last_update_var.set(f"Last update: {current_time.strftime('%H:%M:%S')}")
            
        except Exception as e:
            self.logger.error(f"Error updating metrics: {e}")
            self.status_var.set(f"Error: {e}")
    
    def _update_system_metrics(self):
        """Update system performance metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            self.cpu_overall_var.set(f"{cpu_percent:.1f}%")
            
            # Per-core CPU usage
            cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
            
            # Clear existing core labels
            for widget in self.cpu_cores_frame.winfo_children():
                widget.destroy()
            
            # Create new core labels
            for i, core_percent in enumerate(cpu_per_core):
                ttk.Label(self.cpu_cores_frame, 
                         text=f"Core {i}: {core_percent:.1f}%").grid(row=i//4, column=i%4, sticky=tk.W, padx=5)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.memory_used_var.set(f"{self._format_bytes(memory.used)}")
            self.memory_available_var.set(f"{self._format_bytes(memory.available)}")
            self.memory_percent_var.set(f"{memory.percent:.1f}%")
            
            # System load (Unix-like systems only)
            try:
                load_avg = psutil.getloadavg()
                self.load_1min_var.set(f"{load_avg[0]:.2f}")
                self.load_5min_var.set(f"{load_avg[1]:.2f}")
                self.load_15min_var.set(f"{load_avg[2]:.2f}")
            except AttributeError:
                # Windows doesn't have load average
                self.load_1min_var.set("N/A")
                self.load_5min_var.set("N/A")
                self.load_15min_var.set("N/A")
            
        except Exception as e:
            self.logger.error(f"Error updating system metrics: {e}")
    
    def _update_instance_metrics(self):
        """Update instance-specific metrics"""
        try:
            selected_instance = self.instance_var.get()
            if not selected_instance or selected_instance == "Select Instance":
                return
            
            # Extract instance ID
            instance_id = int(selected_instance.split("(ID: ")[1].rstrip(")"))
            
            # Get container stats
            stats = self.n8n_manager.get_instance_stats(instance_id)
            
            if stats:
                # Container status
                self.container_status_var.set(stats.get('status', 'Unknown'))
                
                # Uptime
                started_at = stats.get('started_at')
                if started_at:
                    uptime = datetime.now() - datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    self.container_uptime_var.set(str(uptime).split('.')[0])  # Remove microseconds
                else:
                    self.container_uptime_var.set("Unknown")
                
                # Restart count
                self.container_restart_count_var.set(str(stats.get('restart_count', 0)))
                
                # Resource usage
                cpu_usage = stats.get('cpu_usage', 0)
                self.instance_cpu_var.set(f"{cpu_usage:.2f}%")
                
                memory_usage = stats.get('memory_usage', 0)
                memory_limit = stats.get('memory_limit', 0)
                self.instance_memory_var.set(f"{self._format_bytes(memory_usage)}")
                self.instance_memory_limit_var.set(f"{self._format_bytes(memory_limit)}")
                
                # Network I/O
                net_rx = stats.get('network_rx_bytes', 0)
                net_tx = stats.get('network_tx_bytes', 0)
                self.instance_net_rx_var.set(f"{self._format_bytes(net_rx)}")
                self.instance_net_tx_var.set(f"{self._format_bytes(net_tx)}")
            else:
                # Clear metrics if no stats available
                self.container_status_var.set("Not Available")
                self.container_uptime_var.set("N/A")
                self.container_restart_count_var.set("N/A")
                self.instance_cpu_var.set("N/A")
                self.instance_memory_var.set("N/A")
                self.instance_memory_limit_var.set("N/A")
                self.instance_net_rx_var.set("N/A")
                self.instance_net_tx_var.set("N/A")
            
        except Exception as e:
            self.logger.error(f"Error updating instance metrics: {e}")
    
    def _update_network_metrics(self):
        """Update network metrics"""
        try:
            # Clear existing items
            for item in self.network_tree.get_children():
                self.network_tree.delete(item)
            
            # Get network I/O stats
            net_io = psutil.net_io_counters(pernic=True)
            
            total_bytes_sent = 0
            total_bytes_recv = 0
            
            for interface, stats in net_io.items():
                # Skip loopback interfaces
                if interface.startswith('lo'):
                    continue
                
                total_bytes_sent += stats.bytes_sent
                total_bytes_recv += stats.bytes_recv
                
                self.network_tree.insert('', 'end', values=(
                    interface,
                    self._format_bytes(stats.bytes_sent),
                    self._format_bytes(stats.bytes_recv),
                    stats.packets_sent,
                    stats.packets_recv,
                    stats.errin + stats.errout
                ))
            
            # Update totals
            self.total_bytes_sent_var.set(self._format_bytes(total_bytes_sent))
            self.total_bytes_recv_var.set(self._format_bytes(total_bytes_recv))
            
            # Active connections
            try:
                connections = len(psutil.net_connections())
                self.active_connections_var.set(str(connections))
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                self.active_connections_var.set("Access Denied")
            
        except Exception as e:
            self.logger.error(f"Error updating network metrics: {e}")
    
    def _update_disk_metrics(self):
        """Update disk metrics"""
        try:
            # Clear existing items
            for item in self.disk_tree.get_children():
                self.disk_tree.delete(item)
            
            # Get disk usage
            disk_partitions = psutil.disk_partitions()
            
            for partition in disk_partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    self.disk_tree.insert('', 'end', values=(
                        partition.device,
                        partition.mountpoint,
                        self._format_bytes(usage.total),
                        self._format_bytes(usage.used),
                        self._format_bytes(usage.free),
                        f"{usage.percent:.1f}%"
                    ))
                except PermissionError:
                    # Skip inaccessible partitions
                    continue
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            if disk_io:
                self.disk_read_var.set(self._format_bytes(disk_io.read_bytes))
                self.disk_write_var.set(self._format_bytes(disk_io.write_bytes))
                self.disk_read_time_var.set(f"{disk_io.read_time} ms")
                self.disk_write_time_var.set(f"{disk_io.write_time} ms")
            
        except Exception as e:
            self.logger.error(f"Error updating disk metrics: {e}")
    
    def _update_instance_list(self):
        """Update the instance dropdown list"""
        try:
            instances = self.n8n_manager.list_instances()
            instance_names = ["Select Instance"] + [f"{inst['name']} (ID: {inst['id']})" for inst in instances]
            
            current_selection = self.instance_var.get()
            self.instance_combo['values'] = instance_names
            
            # Restore selection if still valid
            if current_selection in instance_names:
                self.instance_var.set(current_selection)
            elif not current_selection or current_selection == "Select Instance":
                self.instance_var.set("Select Instance")
            
        except Exception as e:
            self.logger.error(f"Error updating instance list: {e}")
    
    def _on_instance_selected(self, event=None):
        """Handle instance selection change"""
        # Metrics will be updated in the next monitoring cycle
        pass
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human-readable format"""
        if bytes_value == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        
        while bytes_value >= 1024 and unit_index < len(units) - 1:
            bytes_value /= 1024
            unit_index += 1
        
        return f"{bytes_value:.1f} {units[unit_index]}"
    
    def _export_metrics(self):
        """Export current metrics to JSON file"""
        try:
            from tkinter import filedialog
            
            file_path = filedialog.asksaveasfilename(
                title="Export Metrics",
                defaultextension=".json",
                filetypes=[
                    ("JSON files", "*.json"),
                    ("All files", "*.*")
                ]
            )
            
            if file_path:
                # Collect current metrics
                metrics_data = {
                    'timestamp': datetime.now().isoformat(),
                    'system': {
                        'cpu_overall': self.cpu_overall_var.get(),
                        'memory_used': self.memory_used_var.get(),
                        'memory_available': self.memory_available_var.get(),
                        'memory_percent': self.memory_percent_var.get(),
                        'load_1min': self.load_1min_var.get(),
                        'load_5min': self.load_5min_var.get(),
                        'load_15min': self.load_15min_var.get(),
                    },
                    'network': {
                        'total_bytes_sent': self.total_bytes_sent_var.get(),
                        'total_bytes_recv': self.total_bytes_recv_var.get(),
                        'active_connections': self.active_connections_var.get(),
                    },
                    'disk': {
                        'read_bytes': self.disk_read_var.get(),
                        'write_bytes': self.disk_write_var.get(),
                        'read_time': self.disk_read_time_var.get(),
                        'write_time': self.disk_write_time_var.get(),
                    }
                }
                
                # Add instance metrics if available
                if self.instance_var.get() != "Select Instance":
                    metrics_data['instance'] = {
                        'name': self.instance_var.get(),
                        'status': self.container_status_var.get(),
                        'uptime': self.container_uptime_var.get(),
                        'restart_count': self.container_restart_count_var.get(),
                        'cpu': self.instance_cpu_var.get(),
                        'memory': self.instance_memory_var.get(),
                        'memory_limit': self.instance_memory_limit_var.get(),
                        'network_rx': self.instance_net_rx_var.get(),
                        'network_tx': self.instance_net_tx_var.get(),
                    }
                
                with open(file_path, 'w') as f:
                    json.dump(metrics_data, f, indent=2)
                
                messagebox.showinfo("Success", f"Metrics exported to {file_path}")
                
        except Exception as e:
            error_msg = f"Error exporting metrics: {e}"
            self.logger.error(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def cleanup(self):
        """Cleanup when frame is destroyed"""
        self._stop_monitoring()