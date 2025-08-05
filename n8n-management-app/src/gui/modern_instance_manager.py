"""
Modern Instance Manager for n8n Management App
Beautiful card-based interface for managing instances
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Dict, List, Optional, Any
import json
import threading

from core.logger import get_logger
from core.config_manager import get_config
from core.n8n_manager import get_n8n_manager


class ModernInstanceManagerFrame(tk.Frame):
    """Modern instance manager with card-based layout"""
    
    def __init__(self, parent, main_window):
        super().__init__(parent, bg=main_window.theme.COLORS['bg_primary'])
        self.main_window = main_window
        self.theme = main_window.theme
        self.logger = get_logger()
        self.config = get_config()
        self.n8n_manager = get_n8n_manager()
        
        self.instances_data = {}
        self.instance_cards = {}
        self.selected_instance_id = None
        
        self._create_layout()
        
        # Defer initial data load
        self.after_idle(self.refresh_instances)
    
    def _create_layout(self):
        """Create the instance manager layout"""
        # Main container
        container = tk.Frame(self, bg=self.theme.COLORS['bg_primary'])
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Header section
        self._create_header(container)
        
        # Filter and search section
        self._create_filter_section(container)
        
        # Instances grid section
        self._create_instances_section(container)
    
    def _create_header(self, parent):
        """Create header section"""
        header_frame = tk.Frame(parent, bg=self.theme.COLORS['bg_primary'])
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Title and description
        title_frame = tk.Frame(header_frame, bg=self.theme.COLORS['bg_primary'])
        title_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        title_label = tk.Label(title_frame,
                              text="n8n Instances",
                              font=self.theme.FONTS['heading_large'],
                              fg=self.theme.COLORS['text_primary'],
                              bg=self.theme.COLORS['bg_primary'])
        title_label.pack(anchor='w')
        
        desc_label = tk.Label(title_frame,
                             text="Manage your n8n workflow automation instances",
                             font=self.theme.FONTS['body_medium'],
                             fg=self.theme.COLORS['text_secondary'],
                             bg=self.theme.COLORS['bg_primary'])
        desc_label.pack(anchor='w', pady=(5, 0))
        
        # Action buttons
        actions_frame = tk.Frame(header_frame, bg=self.theme.COLORS['bg_primary'])
        actions_frame.pack(side=tk.RIGHT)
        
        new_btn = tk.Button(actions_frame,
                           text="+ New Instance",
                           font=self.theme.FONTS['button'],
                           fg=self.theme.COLORS['text_inverse'],
                           bg=self.theme.COLORS['primary'],
                           activebackground=self.theme.COLORS['primary_hover'],
                           relief='flat',
                           padx=20,
                           pady=10,
                           command=self.create_instance_dialog)
        new_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        refresh_btn = tk.Button(actions_frame,
                               text="🔄 Refresh",
                               font=self.theme.FONTS['button'],
                               fg=self.theme.COLORS['text_primary'],
                               bg=self.theme.COLORS['gray_100'],
                               activebackground=self.theme.COLORS['gray_200'],
                               relief='flat',
                               padx=15,
                               pady=10,
                               command=self.refresh_instances)
        refresh_btn.pack(side=tk.RIGHT)
    
    def _create_filter_section(self, parent):
        """Create filter and search section"""
        filter_frame = tk.Frame(parent, bg=self.theme.COLORS['bg_primary'])
        filter_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Search box
        search_frame = tk.Frame(filter_frame, bg=self.theme.COLORS['bg_primary'])
        search_frame.pack(side=tk.LEFT)
        
        search_label = tk.Label(search_frame,
                               text="🔍",
                               font=('Arial', 14),
                               fg=self.theme.COLORS['text_muted'],
                               bg=self.theme.COLORS['bg_primary'])
        search_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame,
                               textvariable=self.search_var,
                               font=self.theme.FONTS['body_medium'],
                               width=30,
                               relief='solid',
                               borderwidth=1)
        search_entry.pack(side=tk.LEFT)
        search_entry.bind('<KeyRelease>', self._on_search_change)
        
        # Status filter
        filter_label = tk.Label(filter_frame,
                               text="Filter:",
                               font=self.theme.FONTS['body_medium'],
                               fg=self.theme.COLORS['text_secondary'],
                               bg=self.theme.COLORS['bg_primary'])
        filter_label.pack(side=tk.LEFT, padx=(30, 5))
        
        self.filter_var = tk.StringVar(value="All")
        filter_combo = ttk.Combobox(filter_frame,
                                   textvariable=self.filter_var,
                                   values=["All", "Running", "Stopped", "Starting", "Error"],
                                   state="readonly",
                                   width=12)
        filter_combo.pack(side=tk.LEFT)
        filter_combo.bind('<<ComboboxSelected>>', self._on_filter_change)
    
    def _create_instances_section(self, parent):
        """Create instances grid section"""
        # Container with scrollbar
        canvas_frame = tk.Frame(parent, bg=self.theme.COLORS['bg_primary'])
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(canvas_frame, 
                               bg=self.theme.COLORS['bg_primary'],
                               highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.theme.COLORS['bg_primary'])
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        
        # Empty state
        self.empty_state_frame = None
        self._show_empty_state()
    
    def _show_empty_state(self):
        """Show empty state when no instances"""
        if self.empty_state_frame:
            self.empty_state_frame.destroy()
        
        self.empty_state_frame = tk.Frame(self.scrollable_frame, bg=self.theme.COLORS['bg_primary'])
        self.empty_state_frame.pack(fill=tk.BOTH, expand=True, pady=50)
        
        # Empty state content
        empty_content = tk.Frame(self.empty_state_frame, bg=self.theme.COLORS['bg_primary'])
        empty_content.pack(expand=True)
        
        # Icon
        icon_label = tk.Label(empty_content,
                             text="🔧",
                             font=('Arial', 48),
                             fg=self.theme.COLORS['text_muted'],
                             bg=self.theme.COLORS['bg_primary'])
        icon_label.pack(pady=(0, 20))
        
        # Title
        title_label = tk.Label(empty_content,
                              text="No n8n Instances Yet",
                              font=self.theme.FONTS['heading_medium'],
                              fg=self.theme.COLORS['text_primary'],
                              bg=self.theme.COLORS['bg_primary'])
        title_label.pack(pady=(0, 10))
        
        # Description
        desc_label = tk.Label(empty_content,
                             text="Create your first n8n instance to start automating workflows",
                             font=self.theme.FONTS['body_medium'],
                             fg=self.theme.COLORS['text_secondary'],
                             bg=self.theme.COLORS['bg_primary'])
        desc_label.pack(pady=(0, 30))
        
        # Create button
        create_btn = tk.Button(empty_content,
                              text="🚀 Create Your First Instance",
                              font=self.theme.FONTS['button'],
                              fg=self.theme.COLORS['text_inverse'],
                              bg=self.theme.COLORS['primary'],
                              activebackground=self.theme.COLORS['primary_hover'],
                              relief='flat',
                              padx=30,
                              pady=15,
                              command=self.create_instance_dialog)
        create_btn.pack()
    
    def _create_instance_card(self, parent, instance):
        """Create a modern instance card"""
        card = tk.Frame(parent,
                       bg=self.theme.COLORS['white'],
                       relief='solid',
                       borderwidth=1,
                       highlightbackground=self.theme.COLORS['border_light'])
        
        # Card content
        content = tk.Frame(card, bg=self.theme.COLORS['white'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header with status
        header_frame = tk.Frame(content, bg=self.theme.COLORS['white'])
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Status indicator
        status = instance.get('current_status', instance.get('status', 'unknown'))
        indicator = self.theme.create_status_indicator(header_frame, status)
        indicator.pack(side=tk.LEFT)
        
        # Instance name
        name_label = tk.Label(header_frame,
                             text=instance['name'],
                             font=self.theme.FONTS['heading_small'],
                             fg=self.theme.COLORS['text_primary'],
                             bg=self.theme.COLORS['white'])
        name_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Status text
        status_text = status.replace('_', ' ').title()
        status_label = tk.Label(header_frame,
                               text=status_text,
                               font=self.theme.FONTS['caption'],
                               fg=self._get_status_color(status),
                               bg=self.theme.COLORS['white'])
        status_label.pack(side=tk.RIGHT)
        
        # Instance details
        details_frame = tk.Frame(content, bg=self.theme.COLORS['white'])
        details_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Port info
        port_text = f"Port: {instance.get('port', 'Not assigned')}"
        port_label = tk.Label(details_frame,
                             text=port_text,
                             font=self.theme.FONTS['body_small'],
                             fg=self.theme.COLORS['text_secondary'],
                             bg=self.theme.COLORS['white'])
        port_label.pack(anchor='w')
        
        # Image info
        image_text = f"Image: {instance.get('image', 'Unknown')}"
        image_label = tk.Label(details_frame,
                              text=image_text,
                              font=self.theme.FONTS['body_small'],
                              fg=self.theme.COLORS['text_secondary'],
                              bg=self.theme.COLORS['white'])
        image_label.pack(anchor='w', pady=(2, 0))
        
        # Created date
        created_text = f"Created: {instance.get('created_at', 'Unknown')[:10]}"
        created_label = tk.Label(details_frame,
                                text=created_text,
                                font=self.theme.FONTS['body_small'],
                                fg=self.theme.COLORS['text_secondary'],
                                bg=self.theme.COLORS['white'])
        created_label.pack(anchor='w', pady=(2, 0))
        
        # Action buttons
        actions_frame = tk.Frame(content, bg=self.theme.COLORS['white'])
        actions_frame.pack(fill=tk.X)
        
        # Primary action button
        if status == 'running':
            primary_btn = tk.Button(actions_frame,
                                   text="🌐 Open n8n",
                                   font=self.theme.FONTS['button'],
                                   fg=self.theme.COLORS['text_inverse'],
                                   bg=self.theme.COLORS['success'],
                                   activebackground=self.theme.COLORS['success'],
                                   relief='flat',
                                   padx=15,
                                   pady=8,
                                   command=lambda: self._open_instance(instance))
            primary_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            stop_btn = tk.Button(actions_frame,
                                text="⏹️ Stop",
                                font=self.theme.FONTS['button'],
                                fg=self.theme.COLORS['text_inverse'],
                                bg=self.theme.COLORS['error'],
                                activebackground=self.theme.COLORS['error'],
                                relief='flat',
                                padx=15,
                                pady=8,
                                command=lambda: self._stop_instance(instance['id']))
            stop_btn.pack(side=tk.LEFT, padx=(0, 10))
            
        elif status in ['stopped', 'created']:
            start_btn = tk.Button(actions_frame,
                                 text="▶️ Start",
                                 font=self.theme.FONTS['button'],
                                 fg=self.theme.COLORS['text_inverse'],
                                 bg=self.theme.COLORS['success'],
                                 activebackground=self.theme.COLORS['success'],
                                 relief='flat',
                                 padx=15,
                                 pady=8,
                                 command=lambda: self._start_instance(instance['id']))
            start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Secondary actions
        more_btn = tk.Button(actions_frame,
                            text="⚙️ Configure",
                            font=self.theme.FONTS['button'],
                            fg=self.theme.COLORS['text_primary'],
                            bg=self.theme.COLORS['gray_100'],
                            activebackground=self.theme.COLORS['gray_200'],
                            relief='flat',
                            padx=15,
                            pady=8,
                            command=lambda: self._configure_instance(instance))
        more_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        delete_btn = tk.Button(actions_frame,
                              text="🗑️ Delete",
                              font=self.theme.FONTS['button'],
                              fg=self.theme.COLORS['error'],
                              bg=self.theme.COLORS['error_light'],
                              activebackground=self.theme.COLORS['error_light'],
                              relief='flat',
                              padx=15,
                              pady=8,
                              command=lambda: self._delete_instance(instance['id']))
        delete_btn.pack(side=tk.RIGHT)
        
        return card
    
    def _create_filter_section(self, parent):
        """Create filter and search section"""
        filter_frame = tk.Frame(parent, bg=self.theme.COLORS['bg_primary'])
        filter_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Search
        search_frame = tk.Frame(filter_frame, bg=self.theme.COLORS['bg_primary'])
        search_frame.pack(side=tk.LEFT)
        
        search_label = tk.Label(search_frame,
                               text="Search instances:",
                               font=self.theme.FONTS['body_medium'],
                               fg=self.theme.COLORS['text_secondary'],
                               bg=self.theme.COLORS['bg_primary'])
        search_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame,
                               textvariable=self.search_var,
                               font=self.theme.FONTS['body_medium'],
                               width=25,
                               relief='solid',
                               borderwidth=1)
        search_entry.pack(side=tk.LEFT)
        search_entry.bind('<KeyRelease>', self._on_search_change)
        
        # Filter
        filter_label = tk.Label(filter_frame,
                               text="Status:",
                               font=self.theme.FONTS['body_medium'],
                               fg=self.theme.COLORS['text_secondary'],
                               bg=self.theme.COLORS['bg_primary'])
        filter_label.pack(side=tk.LEFT, padx=(30, 10))
        
        self.filter_var = tk.StringVar(value="All")
        filter_combo = ttk.Combobox(filter_frame,
                                   textvariable=self.filter_var,
                                   values=["All", "Running", "Stopped", "Starting", "Error"],
                                   state="readonly",
                                   width=12)
        filter_combo.pack(side=tk.LEFT)
        filter_combo.bind('<<ComboboxSelected>>', self._on_filter_change)
    
    def _create_instances_section(self, parent):
        """Create instances grid section"""
        # Container with scrollbar
        canvas_frame = tk.Frame(parent, bg=self.theme.COLORS['bg_primary'])
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(canvas_frame, 
                               bg=self.theme.COLORS['bg_primary'],
                               highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.theme.COLORS['bg_primary'])
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        
        # Empty state
        self.empty_state_frame = None
        self._show_empty_state()
    
    def _show_empty_state(self):
        """Show empty state when no instances"""
        if self.empty_state_frame:
            self.empty_state_frame.destroy()
        
        self.empty_state_frame = tk.Frame(self.scrollable_frame, bg=self.theme.COLORS['bg_primary'])
        self.empty_state_frame.pack(fill=tk.BOTH, expand=True, pady=100)
        
        # Empty state content
        empty_content = tk.Frame(self.empty_state_frame, bg=self.theme.COLORS['bg_primary'])
        empty_content.pack(expand=True)
        
        # Icon
        icon_label = tk.Label(empty_content,
                             text="🔧",
                             font=('Arial', 64),
                             fg=self.theme.COLORS['text_muted'],
                             bg=self.theme.COLORS['bg_primary'])
        icon_label.pack(pady=(0, 20))
        
        # Title
        title_label = tk.Label(empty_content,
                              text="No Instances Found",
                              font=self.theme.FONTS['heading_medium'],
                              fg=self.theme.COLORS['text_primary'],
                              bg=self.theme.COLORS['bg_primary'])
        title_label.pack(pady=(0, 10))
        
        # Description
        desc_label = tk.Label(empty_content,
                             text="Create your first n8n instance to start building workflows",
                             font=self.theme.FONTS['body_medium'],
                             fg=self.theme.COLORS['text_secondary'],
                             bg=self.theme.COLORS['bg_primary'])
        desc_label.pack(pady=(0, 30))
        
        # Create button
        create_btn = tk.Button(empty_content,
                              text="🚀 Create First Instance",
                              font=self.theme.FONTS['button'],
                              fg=self.theme.COLORS['text_inverse'],
                              bg=self.theme.COLORS['primary'],
                              activebackground=self.theme.COLORS['primary_hover'],
                              relief='flat',
                              padx=30,
                              pady=15,
                              command=self.create_instance_dialog)
        create_btn.pack()
    
    def _get_status_color(self, status):
        """Get color for status"""
        status_colors = {
            'running': self.theme.COLORS['success'],
            'stopped': self.theme.COLORS['error'],
            'starting': self.theme.COLORS['warning'],
            'created': self.theme.COLORS['info'],
            'failed': self.theme.COLORS['error'],
            'unknown': self.theme.COLORS['text_muted']
        }
        return status_colors.get(status, self.theme.COLORS['text_muted'])
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _on_search_change(self, event=None):
        """Handle search change"""
        self._filter_instances()
    
    def _on_filter_change(self, event=None):
        """Handle filter change"""
        self._filter_instances()
    
    def _filter_instances(self):
        """Filter instances based on search and filter criteria"""
        search_term = self.search_var.get().lower()
        status_filter = self.filter_var.get()
        
        for instance_id, card in self.instance_cards.items():
            instance = self.instances_data.get(instance_id)
            if not instance:
                continue
            
            # Check search term
            name_match = search_term in instance['name'].lower()
            
            # Check status filter
            current_status = instance.get('current_status', instance.get('status', 'unknown'))
            if status_filter == "All":
                status_match = True
            elif status_filter == "Running":
                status_match = current_status == 'running'
            elif status_filter == "Stopped":
                status_match = current_status in ['stopped', 'created']
            elif status_filter == "Starting":
                status_match = current_status == 'starting'
            elif status_filter == "Error":
                status_match = current_status in ['failed', 'error']
            else:
                status_match = True
            
            # Show/hide card
            if name_match and status_match:
                card.pack(side=tk.LEFT, padx=(0, 20), pady=(0, 20))
            else:
                card.pack_forget()
    
    def refresh_instances(self):
        """Refresh instances display"""
        try:
            # Get instances data
            instances = self.n8n_manager.list_instances()
            self.instances_data = {str(instance['id']): instance for instance in instances}
            
            # Clear existing cards
            for card in self.instance_cards.values():
                card.destroy()
            self.instance_cards.clear()
            
            # Hide empty state
            if self.empty_state_frame:
                self.empty_state_frame.destroy()
                self.empty_state_frame = None
            
            if not instances:
                self._show_empty_state()
                return
            
            # Create grid layout
            grid_frame = tk.Frame(self.scrollable_frame, bg=self.theme.COLORS['bg_primary'])
            grid_frame.pack(fill=tk.BOTH, expand=True, pady=20)
            
            # Create cards in grid (3 columns)
            row = 0
            col = 0
            for instance in instances:
                card = self._create_instance_card(grid_frame, instance)
                card.grid(row=row, column=col, padx=(0, 20), pady=(0, 20), sticky='ew')
                
                self.instance_cards[str(instance['id'])] = card
                
                col += 1
                if col >= 3:  # 3 cards per row
                    col = 0
                    row += 1
            
            # Configure grid weights
            for i in range(3):
                grid_frame.grid_columnconfigure(i, weight=1)
            
            # Apply current filters
            self._filter_instances()
            
        except Exception as e:
            self.logger.error(f"Error refreshing instances: {e}")
            self.main_window.set_status(f"Error refreshing instances: {e}")
    
    def create_instance_dialog(self):
        """Show create instance dialog"""
        dialog = ModernCreateInstanceDialog(self, self.main_window)
        if dialog.result:
            self.refresh_instances()
            self.main_window.set_status(f"Instance '{dialog.result}' created successfully")
    
    def _start_instance(self, instance_id):
        """Start an instance"""
        try:
            instance = self.instances_data.get(str(instance_id))
            if not instance:
                return
            
            self.main_window.set_status(f"Starting {instance['name']}...")
            
            def start_worker():
                success, message = self.n8n_manager.start_instance(instance_id)
                self.after(0, lambda: self._handle_action_result(success, message, "start"))
            
            threading.Thread(target=start_worker, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start instance: {e}")
    
    def _stop_instance(self, instance_id):
        """Stop an instance"""
        try:
            instance = self.instances_data.get(str(instance_id))
            if not instance:
                return
            
            self.main_window.set_status(f"Stopping {instance['name']}...")
            
            def stop_worker():
                success, message = self.n8n_manager.stop_instance(instance_id)
                self.after(0, lambda: self._handle_action_result(success, message, "stop"))
            
            threading.Thread(target=stop_worker, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop instance: {e}")
    
    def _open_instance(self, instance):
        """Open instance in browser"""
        try:
            port = instance.get('port')
            if port:
                import webbrowser
                url = f"http://localhost:{port}"
                webbrowser.open(url)
                self.main_window.set_status(f"Opened {instance['name']} in browser")
            else:
                messagebox.showwarning("No Port", "This instance has no port configured.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open instance: {e}")
    
    def _configure_instance(self, instance):
        """Configure an instance"""
        messagebox.showinfo("Coming Soon", "Instance configuration dialog coming soon!")
    
    def _delete_instance(self, instance_id):
        """Delete an instance"""
        try:
            instance = self.instances_data.get(str(instance_id))
            if not instance:
                return
            
            # Confirm deletion
            result = messagebox.askyesnocancel(
                "Confirm Deletion",
                f"Are you sure you want to delete '{instance['name']}'?\n\n"
                "• Yes: Delete instance but keep data\n"
                "• No: Delete instance and remove all data\n"
                "• Cancel: Don't delete"
            )
            
            if result is None:  # Cancel
                return
            
            remove_data = not result  # No = remove data, Yes = keep data
            
            self.main_window.set_status(f"Deleting {instance['name']}...")
            
            def delete_worker():
                success, message = self.n8n_manager.delete_instance(instance_id, remove_data)
                self.after(0, lambda: self._handle_action_result(success, message, "delete"))
            
            threading.Thread(target=delete_worker, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete instance: {e}")
    
    def _handle_action_result(self, success, message, action):
        """Handle action result"""
        if success:
            self.main_window.set_status(message)
            self.refresh_instances()
        else:
            messagebox.showerror(f"{action.title()} Failed", message)
            self.main_window.set_status(f"Failed to {action} instance")


class ModernCreateInstanceDialog:
    """Modern create instance dialog"""
    
    def __init__(self, parent, main_window):
        self.parent = parent
        self.main_window = main_window
        self.theme = main_window.theme
        self.logger = get_logger()
        self.config = get_config()
        self.n8n_manager = get_n8n_manager()
        
        self.result = None
        self.dialog = None
        
        self._create_dialog()
    
    def _create_dialog(self):
        """Create the modern dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Create New n8n Instance")
        self.dialog.geometry("500x400")
        self.dialog.configure(bg=self.theme.COLORS['bg_primary'])
        self.dialog.transient(self.main_window.root)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 500) // 2
        y = (self.dialog.winfo_screenheight() - 400) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        # Main container
        container = tk.Frame(self.dialog, bg=self.theme.COLORS['bg_primary'])
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Header
        header_label = tk.Label(container,
                               text="Create New Instance",
                               font=self.theme.FONTS['heading_medium'],
                               fg=self.theme.COLORS['text_primary'],
                               bg=self.theme.COLORS['bg_primary'])
        header_label.pack(anchor='w', pady=(0, 20))
        
        # Form
        form_frame = tk.Frame(container, bg=self.theme.COLORS['bg_primary'])
        form_frame.pack(fill=tk.X, pady=(0, 30))
        
        # Instance name
        name_label = tk.Label(form_frame,
                             text="Instance Name",
                             font=self.theme.FONTS['body_medium'],
                             fg=self.theme.COLORS['text_primary'],
                             bg=self.theme.COLORS['bg_primary'])
        name_label.pack(anchor='w', pady=(0, 5))
        
        self.name_var = tk.StringVar()
        name_entry = tk.Entry(form_frame,
                             textvariable=self.name_var,
                             font=self.theme.FONTS['body_medium'],
                             relief='solid',
                             borderwidth=1,
                             width=40)
        name_entry.pack(fill=tk.X, pady=(0, 20))
        name_entry.focus()
        
        # Description
        desc_label = tk.Label(form_frame,
                             text="Choose a descriptive name for your n8n instance (e.g., 'production', 'testing', 'workflows')",
                             font=self.theme.FONTS['caption'],
                             fg=self.theme.COLORS['text_muted'],
                             bg=self.theme.COLORS['bg_primary'],
                             wraplength=400,
                             justify='left')
        desc_label.pack(anchor='w', pady=(0, 20))
        
        # Advanced options (collapsed by default)
        self.show_advanced_var = tk.BooleanVar()
        advanced_check = tk.Checkbutton(form_frame,
                                       text="Show advanced options",
                                       variable=self.show_advanced_var,
                                       font=self.theme.FONTS['body_medium'],
                                       fg=self.theme.COLORS['text_secondary'],
                                       bg=self.theme.COLORS['bg_primary'],
                                       activebackground=self.theme.COLORS['bg_primary'],
                                       command=self._toggle_advanced)
        advanced_check.pack(anchor='w')
        
        # Advanced options frame (hidden by default)
        self.advanced_frame = tk.Frame(form_frame, bg=self.theme.COLORS['bg_primary'])
        
        # Buttons
        buttons_frame = tk.Frame(container, bg=self.theme.COLORS['bg_primary'])
        buttons_frame.pack(fill=tk.X)
        
        cancel_btn = tk.Button(buttons_frame,
                              text="Cancel",
                              font=self.theme.FONTS['button'],
                              fg=self.theme.COLORS['text_primary'],
                              bg=self.theme.COLORS['gray_100'],
                              activebackground=self.theme.COLORS['gray_200'],
                              relief='flat',
                              padx=20,
                              pady=10,
                              command=self._cancel)
        cancel_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        create_btn = tk.Button(buttons_frame,
                              text="Create Instance",
                              font=self.theme.FONTS['button'],
                              fg=self.theme.COLORS['text_inverse'],
                              bg=self.theme.COLORS['primary'],
                              activebackground=self.theme.COLORS['primary_hover'],
                              relief='flat',
                              padx=20,
                              pady=10,
                              command=self._create)
        create_btn.pack(side=tk.RIGHT)
        
        # Bind keys
        self.dialog.bind('<Return>', lambda e: self._create())
        self.dialog.bind('<Escape>', lambda e: self._cancel())
        
        # Wait for dialog
        self.dialog.wait_window()
    
    def _toggle_advanced(self):
        """Toggle advanced options"""
        if self.show_advanced_var.get():
            self.advanced_frame.pack(fill=tk.X, pady=(20, 0))
            # Add advanced options here
        else:
            self.advanced_frame.pack_forget()
    
    def _create(self):
        """Create the instance"""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Please enter an instance name.")
            return
        
        # Validate name
        if not self._validate_name(name):
            messagebox.showerror("Error", 
                               "Invalid instance name.\n\n"
                               "Use only letters, numbers, hyphens, and underscores.\n"
                               "Name must be at least 3 characters long.")
            return
        
        try:
            # Show progress
            self.main_window.set_status(f"Creating instance '{name}'...")
            
            # Create instance in background
            def create_worker():
                success, message, instance_id = self.n8n_manager.create_instance(name)
                self.dialog.after(0, lambda: self._handle_create_result(success, message, name))
            
            threading.Thread(target=create_worker, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create instance: {e}")
    
    def _handle_create_result(self, success, message, name):
        """Handle create result"""
        if success:
            self.result = name
            self.dialog.destroy()
        else:
            messagebox.showerror("Creation Failed", message)
    
    def _cancel(self):
        """Cancel dialog"""
        self.dialog.destroy()
    
    def _validate_name(self, name: str) -> bool:
        """Validate instance name"""
        import re
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', name)) and len(name) >= 3