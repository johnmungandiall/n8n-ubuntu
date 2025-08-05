"""
Modern Dashboard for n8n Management App
Beautiful overview of system status and quick actions
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, List
import time
from datetime import datetime

from core.logger import get_logger
from core.config_manager import get_config
from core.n8n_manager import get_n8n_manager
from core.docker_manager import get_docker_manager


class ModernDashboardFrame(tk.Frame):
    """Modern dashboard with cards and metrics"""
    
    def __init__(self, parent, main_window):
        super().__init__(parent, bg=main_window.theme.COLORS['bg_primary'])
        self.main_window = main_window
        self.theme = main_window.theme
        self.logger = get_logger()
        self.config = get_config()
        self.n8n_manager = get_n8n_manager()
        self.docker_manager = get_docker_manager()
        
        self._create_dashboard()
        
        # Defer initial data load
        self.after_idle(self.refresh)
    
    def _create_dashboard(self):
        """Create the dashboard layout"""
        # Main container with padding
        container = tk.Frame(self, bg=self.theme.COLORS['bg_primary'])
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Header section
        self._create_header(container)
        
        # Metrics cards section
        self._create_metrics_section(container)
        
        # Recent activity section
        self._create_activity_section(container)
        
        # Quick actions section
        self._create_quick_actions_section(container)
    
    def _create_header(self, parent):
        """Create dashboard header"""
        header_frame = tk.Frame(parent, bg=self.theme.COLORS['bg_primary'])
        header_frame.pack(fill=tk.X, pady=(0, 30))
        
        # Welcome message
        welcome_label = tk.Label(header_frame,
                                text="Welcome to n8n Management Hub",
                                font=self.theme.FONTS['heading_large'],
                                fg=self.theme.COLORS['text_primary'],
                                bg=self.theme.COLORS['bg_primary'])
        welcome_label.pack(anchor='w')
        
        # Subtitle with current time
        self.subtitle_var = tk.StringVar()
        subtitle_label = tk.Label(header_frame,
                                 textvariable=self.subtitle_var,
                                 font=self.theme.FONTS['body_medium'],
                                 fg=self.theme.COLORS['text_secondary'],
                                 bg=self.theme.COLORS['bg_primary'])
        subtitle_label.pack(anchor='w', pady=(5, 0))
        
        self._update_subtitle()
    
    def _create_metrics_section(self, parent):
        """Create metrics cards section"""
        metrics_frame = tk.Frame(parent, bg=self.theme.COLORS['bg_primary'])
        metrics_frame.pack(fill=tk.X, pady=(0, 30))
        
        # Section title
        title_label = tk.Label(metrics_frame,
                              text="System Overview",
                              font=self.theme.FONTS['heading_medium'],
                              fg=self.theme.COLORS['text_primary'],
                              bg=self.theme.COLORS['bg_primary'])
        title_label.pack(anchor='w', pady=(0, 15))
        
        # Cards container
        cards_frame = tk.Frame(metrics_frame, bg=self.theme.COLORS['bg_primary'])
        cards_frame.pack(fill=tk.X)
        
        # Create metric cards
        self.total_instances_card = self._create_metric_card(cards_frame, "Total Instances", "0", "🔧")
        self.running_instances_card = self._create_metric_card(cards_frame, "Running", "0", "🟢")
        self.docker_status_card = self._create_metric_card(cards_frame, "Docker Status", "Checking...", "🐳")
        self.system_health_card = self._create_metric_card(cards_frame, "System Health", "Good", "💚")
        
        # Pack cards
        self.total_instances_card.pack(side=tk.LEFT, padx=(0, 15))
        self.running_instances_card.pack(side=tk.LEFT, padx=(0, 15))
        self.docker_status_card.pack(side=tk.LEFT, padx=(0, 15))
        self.system_health_card.pack(side=tk.LEFT)
    
    def _create_metric_card(self, parent, title, value, icon):
        """Create a metric card"""
        card = tk.Frame(parent,
                       bg=self.theme.COLORS['white'],
                       relief='solid',
                       borderwidth=1,
                       highlightbackground=self.theme.COLORS['border_light'])
        
        # Card content
        content = tk.Frame(card, bg=self.theme.COLORS['white'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Icon and title row
        header_frame = tk.Frame(content, bg=self.theme.COLORS['white'])
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        icon_label = tk.Label(header_frame,
                             text=icon,
                             font=('Arial', 16),
                             bg=self.theme.COLORS['white'])
        icon_label.pack(side=tk.LEFT)
        
        title_label = tk.Label(header_frame,
                              text=title,
                              font=self.theme.FONTS['body_medium'],
                              fg=self.theme.COLORS['text_secondary'],
                              bg=self.theme.COLORS['white'])
        title_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Value
        value_var = tk.StringVar()
        value_var.set(value)
        value_label = tk.Label(content,
                              textvariable=value_var,
                              font=self.theme.FONTS['heading_medium'],
                              fg=self.theme.COLORS['text_primary'],
                              bg=self.theme.COLORS['white'])
        value_label.pack(anchor='w')
        
        # Store reference to value variable
        card.value_var = value_var
        
        return card
    
    def _create_activity_section(self, parent):
        """Create recent activity section"""
        activity_frame = tk.Frame(parent, bg=self.theme.COLORS['bg_primary'])
        activity_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 30))
        
        # Section title
        title_label = tk.Label(activity_frame,
                              text="Recent Activity",
                              font=self.theme.FONTS['heading_medium'],
                              fg=self.theme.COLORS['text_primary'],
                              bg=self.theme.COLORS['bg_primary'])
        title_label.pack(anchor='w', pady=(0, 15))
        
        # Activity card
        activity_card = tk.Frame(activity_frame,
                                bg=self.theme.COLORS['white'],
                                relief='solid',
                                borderwidth=1,
                                highlightbackground=self.theme.COLORS['border_light'])
        activity_card.pack(fill=tk.BOTH, expand=True)
        
        # Activity content
        self.activity_content = tk.Frame(activity_card, bg=self.theme.COLORS['white'])
        self.activity_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Placeholder for activity items
        placeholder_label = tk.Label(self.activity_content,
                                     text="No recent activity",
                                     font=self.theme.FONTS['body_medium'],
                                     fg=self.theme.COLORS['text_muted'],
                                     bg=self.theme.COLORS['white'])
        placeholder_label.pack(anchor='w')
    
    def _create_quick_actions_section(self, parent):
        """Create quick actions section"""
        actions_frame = tk.Frame(parent, bg=self.theme.COLORS['bg_primary'])
        actions_frame.pack(fill=tk.X)
        
        # Section title
        title_label = tk.Label(actions_frame,
                              text="Quick Actions",
                              font=self.theme.FONTS['heading_medium'],
                              fg=self.theme.COLORS['text_primary'],
                              bg=self.theme.COLORS['bg_primary'])
        title_label.pack(anchor='w', pady=(0, 15))
        
        # Actions card
        actions_card = tk.Frame(actions_frame,
                               bg=self.theme.COLORS['white'],
                               relief='solid',
                               borderwidth=1,
                               highlightbackground=self.theme.COLORS['border_light'])
        actions_card.pack(fill=tk.X)
        
        # Actions content
        actions_content = tk.Frame(actions_card, bg=self.theme.COLORS['white'])
        actions_content.pack(fill=tk.X, padx=20, pady=20)
        
        # Action buttons
        buttons_frame = tk.Frame(actions_content, bg=self.theme.COLORS['white'])
        buttons_frame.pack(fill=tk.X)
        
        # Create instance button
        create_btn = tk.Button(buttons_frame,
                              text="🚀 Create New Instance",
                              font=self.theme.FONTS['button'],
                              fg=self.theme.COLORS['text_inverse'],
                              bg=self.theme.COLORS['primary'],
                              activebackground=self.theme.COLORS['primary_hover'],
                              relief='flat',
                              padx=20,
                              pady=12,
                              command=self._create_instance)
        create_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        # View instances button
        view_btn = tk.Button(buttons_frame,
                            text="📋 Manage Instances",
                            font=self.theme.FONTS['button'],
                            fg=self.theme.COLORS['text_primary'],
                            bg=self.theme.COLORS['gray_100'],
                            activebackground=self.theme.COLORS['gray_200'],
                            relief='flat',
                            padx=20,
                            pady=12,
                            command=self._view_instances)
        view_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        # Docker cleanup button
        cleanup_btn = tk.Button(buttons_frame,
                               text="🧹 Cleanup Docker",
                               font=self.theme.FONTS['button'],
                               fg=self.theme.COLORS['text_primary'],
                               bg=self.theme.COLORS['gray_100'],
                               activebackground=self.theme.COLORS['gray_200'],
                               relief='flat',
                               padx=20,
                               pady=12,
                               command=self._cleanup_docker)
        cleanup_btn.pack(side=tk.LEFT)
    
    def _update_subtitle(self):
        """Update subtitle with current time"""
        current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        self.subtitle_var.set(f"Today is {current_time}")
    
    def _create_instance(self):
        """Navigate to create instance"""
        self.main_window._navigate_to('Instances', self.main_window._show_instances)
        self.main_window.root.after(100, self.main_window._new_instance)
    
    def _view_instances(self):
        """Navigate to instances view"""
        self.main_window._navigate_to('Instances', self.main_window._show_instances)
    
    def _cleanup_docker(self):
        """Cleanup Docker resources"""
        if messagebox.askyesno("Confirm Cleanup", 
                              "This will remove unused Docker containers, images, and volumes.\n\n"
                              "This is safe and will not affect running instances.\n\n"
                              "Continue?"):
            try:
                self.main_window.set_status("Cleaning up Docker resources...")
                
                # Run cleanup in background thread
                def cleanup_worker():
                    try:
                        stats = self.docker_manager.cleanup_unused_resources()
                        
                        # Update UI on main thread
                        self.after(0, lambda: self._show_cleanup_results(stats))
                    except Exception as e:
                        self.after(0, lambda: self._show_cleanup_error(str(e)))
                
                cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
                cleanup_thread.start()
                
            except Exception as e:
                messagebox.showerror("Cleanup Error", f"Failed to start cleanup: {e}")
                self.main_window.set_status("Cleanup failed")
    
    def _show_cleanup_results(self, stats):
        """Show cleanup results"""
        message = f"""Cleanup completed successfully!

• Containers removed: {stats['containers_removed']}
• Images removed: {stats['images_removed']}
• Volumes removed: {stats['volumes_removed']}
• Networks removed: {stats['networks_removed']}

Your system is now optimized."""
        
        messagebox.showinfo("Cleanup Complete", message)
        self.main_window.set_status("Docker cleanup completed")
        self.refresh()
    
    def _show_cleanup_error(self, error):
        """Show cleanup error"""
        messagebox.showerror("Cleanup Error", f"Failed to cleanup Docker resources:\n\n{error}")
        self.main_window.set_status("Cleanup failed")
    
    def refresh(self):
        """Refresh dashboard data"""
        try:
            self._update_subtitle()
            self._update_metrics()
            self._update_activity()
        except Exception as e:
            self.logger.error(f"Error refreshing dashboard: {e}")
    
    def _update_metrics(self):
        """Update metric cards"""
        try:
            # Get instances data
            instances = self.n8n_manager.list_instances()
            total_instances = len(instances)
            running_instances = sum(1 for i in instances if i.get('current_status') == 'running')
            
            # Update cards
            self.total_instances_card.value_var.set(str(total_instances))
            self.running_instances_card.value_var.set(str(running_instances))
            
            # Docker status
            try:
                if self.docker_manager.is_docker_available():
                    self.docker_status_card.value_var.set("Connected")
                else:
                    self.docker_status_card.value_var.set("Disconnected")
            except:
                self.docker_status_card.value_var.set("Error")
            
            # System health (simplified)
            if running_instances == total_instances and total_instances > 0:
                health = "Excellent"
            elif running_instances > 0:
                health = "Good"
            elif total_instances > 0:
                health = "Needs Attention"
            else:
                health = "Ready"
            
            self.system_health_card.value_var.set(health)
            
        except Exception as e:
            self.logger.error(f"Error updating metrics: {e}")
    
    def _update_activity(self):
        """Update recent activity"""
        try:
            # Clear existing activity
            for widget in self.activity_content.winfo_children():
                widget.destroy()
            
            # Get recent instances (simplified activity)
            instances = self.n8n_manager.list_instances()
            
            if not instances:
                placeholder_label = tk.Label(self.activity_content,
                                             text="No instances created yet. Create your first instance to get started!",
                                             font=self.theme.FONTS['body_medium'],
                                             fg=self.theme.COLORS['text_muted'],
                                             bg=self.theme.COLORS['white'])
                placeholder_label.pack(anchor='w')
                return
            
            # Show recent instances
            recent_instances = sorted(instances, key=lambda x: x.get('updated_at', ''), reverse=True)[:5]
            
            for instance in recent_instances:
                self._create_activity_item(self.activity_content, instance)
                
        except Exception as e:
            self.logger.error(f"Error updating activity: {e}")
    
    def _create_activity_item(self, parent, instance):
        """Create an activity item"""
        item_frame = tk.Frame(parent, bg=self.theme.COLORS['white'])
        item_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Status indicator
        status = instance.get('current_status', instance.get('status', 'unknown'))
        indicator = self.theme.create_status_indicator(item_frame, status)
        indicator.pack(side=tk.LEFT, padx=(0, 10))
        
        # Instance info
        info_frame = tk.Frame(item_frame, bg=self.theme.COLORS['white'])
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Instance name
        name_label = tk.Label(info_frame,
                             text=instance['name'],
                             font=self.theme.FONTS['body_medium'],
                             fg=self.theme.COLORS['text_primary'],
                             bg=self.theme.COLORS['white'])
        name_label.pack(anchor='w')
        
        # Instance details
        port_text = f"Port {instance.get('port', 'N/A')}" if instance.get('port') else "No port assigned"
        status_text = status.replace('_', ' ').title()
        details_text = f"{status_text} • {port_text}"
        
        details_label = tk.Label(info_frame,
                                text=details_text,
                                font=self.theme.FONTS['caption'],
                                fg=self.theme.COLORS['text_muted'],
                                bg=self.theme.COLORS['white'])
        details_label.pack(anchor='w')
        
        # Action buttons
        actions_frame = tk.Frame(item_frame, bg=self.theme.COLORS['white'])
        actions_frame.pack(side=tk.RIGHT)
        
        if status == 'running':
            stop_btn = tk.Button(actions_frame,
                                text="Stop",
                                font=self.theme.FONTS['caption'],
                                fg=self.theme.COLORS['text_inverse'],
                                bg=self.theme.COLORS['error'],
                                activebackground=self.theme.COLORS['error'],
                                relief='flat',
                                padx=12,
                                pady=4,
                                command=lambda: self._stop_instance(instance['id']))
            stop_btn.pack(side=tk.RIGHT, padx=(5, 0))
            
            open_btn = tk.Button(actions_frame,
                                text="Open",
                                font=self.theme.FONTS['caption'],
                                fg=self.theme.COLORS['text_inverse'],
                                bg=self.theme.COLORS['success'],
                                activebackground=self.theme.COLORS['success'],
                                relief='flat',
                                padx=12,
                                pady=4,
                                command=lambda: self._open_instance(instance))
            open_btn.pack(side=tk.RIGHT, padx=(5, 0))
            
        elif status in ['stopped', 'created']:
            start_btn = tk.Button(actions_frame,
                                 text="Start",
                                 font=self.theme.FONTS['caption'],
                                 fg=self.theme.COLORS['text_inverse'],
                                 bg=self.theme.COLORS['success'],
                                 activebackground=self.theme.COLORS['success'],
                                 relief='flat',
                                 padx=12,
                                 pady=4,
                                 command=lambda: self._start_instance(instance['id']))
            start_btn.pack(side=tk.RIGHT)
    
    def _create_quick_actions_section(self, parent):
        """Create quick actions section"""
        actions_frame = tk.Frame(parent, bg=self.theme.COLORS['bg_primary'])
        actions_frame.pack(fill=tk.X)
        
        # Section title
        title_label = tk.Label(actions_frame,
                              text="Get Started",
                              font=self.theme.FONTS['heading_medium'],
                              fg=self.theme.COLORS['text_primary'],
                              bg=self.theme.COLORS['bg_primary'])
        title_label.pack(anchor='w', pady=(0, 15))
        
        # Actions card
        actions_card = tk.Frame(actions_frame,
                               bg=self.theme.COLORS['white'],
                               relief='solid',
                               borderwidth=1,
                               highlightbackground=self.theme.COLORS['border_light'])
        actions_card.pack(fill=tk.X)
        
        # Actions content
        actions_content = tk.Frame(actions_card, bg=self.theme.COLORS['white'])
        actions_content.pack(fill=tk.X, padx=20, pady=20)
        
        # Help text
        help_label = tk.Label(actions_content,
                             text="New to n8n? Here are some helpful resources:",
                             font=self.theme.FONTS['body_medium'],
                             fg=self.theme.COLORS['text_secondary'],
                             bg=self.theme.COLORS['white'])
        help_label.pack(anchor='w', pady=(0, 15))
        
        # Resource buttons
        resources_frame = tk.Frame(actions_content, bg=self.theme.COLORS['white'])
        resources_frame.pack(fill=tk.X)
        
        docs_btn = tk.Button(resources_frame,
                            text="📚 n8n Documentation",
                            font=self.theme.FONTS['button'],
                            fg=self.theme.COLORS['primary'],
                            bg=self.theme.COLORS['primary_light'],
                            activebackground=self.theme.COLORS['primary_light'],
                            relief='flat',
                            padx=15,
                            pady=8,
                            command=self._open_docs)
        docs_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        community_btn = tk.Button(resources_frame,
                                 text="💬 Community Forum",
                                 font=self.theme.FONTS['button'],
                                 fg=self.theme.COLORS['primary'],
                                 bg=self.theme.COLORS['primary_light'],
                                 activebackground=self.theme.COLORS['primary_light'],
                                 relief='flat',
                                 padx=15,
                                 pady=8,
                                 command=self._open_community)
        community_btn.pack(side=tk.LEFT)
    
    def _start_instance(self, instance_id):
        """Start an instance"""
        try:
            self.main_window.set_status(f"Starting instance...")
            
            def start_worker():
                success, message = self.n8n_manager.start_instance(instance_id)
                self.after(0, lambda: self._handle_instance_action_result(success, message, "start"))
            
            threading.Thread(target=start_worker, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start instance: {e}")
    
    def _stop_instance(self, instance_id):
        """Stop an instance"""
        try:
            self.main_window.set_status(f"Stopping instance...")
            
            def stop_worker():
                success, message = self.n8n_manager.stop_instance(instance_id)
                self.after(0, lambda: self._handle_instance_action_result(success, message, "stop"))
            
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
    
    def _handle_instance_action_result(self, success, message, action):
        """Handle instance action result"""
        if success:
            self.main_window.set_status(message)
            self.refresh()
        else:
            messagebox.showerror(f"{action.title()} Failed", message)
            self.main_window.set_status(f"Failed to {action} instance")
    
    def _open_docs(self):
        """Open n8n documentation"""
        try:
            import webbrowser
            webbrowser.open("https://docs.n8n.io/")
            self.main_window.set_status("Opened n8n documentation")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open documentation: {e}")
    
    def _open_community(self):
        """Open n8n community forum"""
        try:
            import webbrowser
            webbrowser.open("https://community.n8n.io/")
            self.main_window.set_status("Opened n8n community forum")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open community forum: {e}")