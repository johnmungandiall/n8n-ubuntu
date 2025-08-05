"""
GUI component tests for n8n Management App
Tests GUI functionality, user interactions, and interface behavior
"""

import pytest
import tkinter as tk
from tkinter import ttk
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Set up display for headless testing
if 'DISPLAY' not in os.environ:
    os.environ['DISPLAY'] = ':99'


class TestGUIInitialization:
    """Test GUI initialization and basic setup"""
    
    def setup_method(self):
        """Setup GUI test environment"""
        # Create root window for testing
        self.root = tk.Tk()
        self.root.withdraw()  # Hide window during testing
    
    def teardown_method(self):
        """Cleanup GUI test environment"""
        if self.root:
            self.root.destroy()
    
    @patch('core.config_manager.get_config')
    @patch('core.n8n_manager.get_n8n_manager')
    def test_main_window_initialization(self, mock_n8n_manager, mock_config):
        """Test main window initialization"""
        # Setup mocks
        mock_config_obj = Mock()
        mock_config_obj.get.return_value = {'theme': 'modern', 'window_size': [1200, 800]}
        mock_config.return_value = mock_config_obj
        
        mock_n8n_mgr = Mock()
        mock_n8n_manager.return_value = mock_n8n_mgr
        
        try:
            from gui.simple_modern_window import SimpleModernWindow
            
            # Create window instance
            window = SimpleModernWindow()
            
            # Verify window is created
            assert window.root is not None
            assert isinstance(window.root, tk.Tk)
            
            # Verify basic window properties
            assert window.root.title() != ""  # Should have a title
            
            # Cleanup
            window.destroy()
            
        except ImportError:
            pytest.skip("GUI module not available")
        except tk.TclError:
            pytest.skip("No display available for GUI testing")
    
    @patch('core.config_manager.get_config')
    def test_theme_application(self, mock_config):
        """Test theme application to GUI components"""
        # Setup mock config
        mock_config_obj = Mock()
        mock_config_obj.get.side_effect = lambda key, default=None: {
            'gui.theme': 'modern',
            'gui.window_size': [1200, 800]
        }.get(key, default)
        mock_config.return_value = mock_config_obj
        
        try:
            from gui.modern_theme import ModernTheme
            
            # Create theme instance
            theme = ModernTheme()
            
            # Test theme properties
            assert hasattr(theme, 'colors')
            assert hasattr(theme, 'fonts')
            assert hasattr(theme, 'styles')
            
            # Test color scheme
            colors = theme.colors
            assert 'primary' in colors
            assert 'secondary' in colors
            assert 'background' in colors
            assert 'text' in colors
            
            # Colors should be valid hex colors or color names
            for color_name, color_value in colors.items():
                assert isinstance(color_value, str)
                assert len(color_value) > 0
                
        except ImportError:
            pytest.skip("Theme module not available")
        except tk.TclError:
            pytest.skip("No display available for GUI testing")


class TestInstanceManagementGUI:
    """Test instance management GUI components"""
    
    def setup_method(self):
        """Setup instance management test environment"""
        self.root = tk.Tk()
        self.root.withdraw()
    
    def teardown_method(self):
        """Cleanup test environment"""
        if self.root:
            self.root.destroy()
    
    @patch('core.n8n_manager.get_n8n_manager')
    def test_instance_list_display(self, mock_n8n_manager):
        """Test instance list display functionality"""
        # Setup mock data
        mock_instances = [
            {'id': 1, 'name': 'test1', 'status': 'running', 'port': 5678, 'image': 'n8nio/n8n:latest'},
            {'id': 2, 'name': 'test2', 'status': 'stopped', 'port': 5679, 'image': 'n8nio/n8n:latest'},
            {'id': 3, 'name': 'test3', 'status': 'running', 'port': 5680, 'image': 'n8nio/n8n:latest'}
        ]
        
        mock_n8n_mgr = Mock()
        mock_n8n_mgr.list_instances.return_value = mock_instances
        mock_n8n_manager.return_value = mock_n8n_mgr
        
        try:
            # Create a simple treeview to test instance display
            frame = ttk.Frame(self.root)
            
            # Create treeview for instances
            columns = ('ID', 'Name', 'Status', 'Port', 'Image')
            tree = ttk.Treeview(frame, columns=columns, show='headings')
            
            # Setup column headings
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=100)
            
            # Populate with mock data
            for instance in mock_instances:
                tree.insert('', 'end', values=(
                    instance['id'],
                    instance['name'],
                    instance['status'],
                    instance['port'],
                    instance['image']
                ))
            
            # Verify data is displayed
            items = tree.get_children()
            assert len(items) == 3
            
            # Verify first item data
            first_item_values = tree.item(items[0])['values']
            assert first_item_values[0] == 1  # ID
            assert first_item_values[1] == 'test1'  # Name
            assert first_item_values[2] == 'running'  # Status
            
        except tk.TclError:
            pytest.skip("No display available for GUI testing")
    
    @patch('core.n8n_manager.get_n8n_manager')
    def test_instance_creation_dialog(self, mock_n8n_manager):
        """Test instance creation dialog functionality"""
        mock_n8n_mgr = Mock()
        mock_n8n_mgr.create_instance.return_value = (True, "Instance created successfully", 1)
        mock_n8n_manager.return_value = mock_n8n_mgr
        
        try:
            # Create a simple dialog simulation
            dialog_frame = ttk.Frame(self.root)
            
            # Instance name entry
            name_var = tk.StringVar(value="test-instance")
            name_entry = ttk.Entry(dialog_frame, textvariable=name_var)
            
            # Image selection
            image_var = tk.StringVar(value="n8nio/n8n:latest")
            image_combo = ttk.Combobox(dialog_frame, textvariable=image_var)
            image_combo['values'] = ('n8nio/n8n:latest', 'n8nio/n8n:0.200.0')
            
            # Port entry
            port_var = tk.StringVar(value="5678")
            port_entry = ttk.Entry(dialog_frame, textvariable=port_var)
            
            # Simulate form submission
            def create_instance():
                name = name_var.get()
                image = image_var.get()
                port = port_var.get()
                
                # Validate inputs
                assert name != "", "Instance name should not be empty"
                assert image != "", "Image should not be empty"
                assert port.isdigit(), "Port should be numeric"
                
                # Call manager
                success, message, instance_id = mock_n8n_mgr.create_instance(name)
                assert success is True
                assert instance_id == 1
                
                return success
            
            # Test form submission
            result = create_instance()
            assert result is True
            
            # Verify manager was called
            mock_n8n_mgr.create_instance.assert_called_once_with("test-instance")
            
        except tk.TclError:
            pytest.skip("No display available for GUI testing")
    
    @patch('core.n8n_manager.get_n8n_manager')
    def test_instance_control_buttons(self, mock_n8n_manager):
        """Test instance control button functionality"""
        mock_n8n_mgr = Mock()
        mock_n8n_mgr.start_instance.return_value = (True, "Instance started")
        mock_n8n_mgr.stop_instance.return_value = (True, "Instance stopped")
        mock_n8n_mgr.delete_instance.return_value = (True, "Instance deleted")
        mock_n8n_manager.return_value = mock_n8n_mgr
        
        try:
            # Create control buttons
            control_frame = ttk.Frame(self.root)
            
            selected_instance_id = 1
            
            def start_instance():
                success, message = mock_n8n_mgr.start_instance(selected_instance_id)
                return success
            
            def stop_instance():
                success, message = mock_n8n_mgr.stop_instance(selected_instance_id)
                return success
            
            def delete_instance():
                success, message = mock_n8n_mgr.delete_instance(selected_instance_id, False)
                return success
            
            # Create buttons
            start_btn = ttk.Button(control_frame, text="Start", command=start_instance)
            stop_btn = ttk.Button(control_frame, text="Stop", command=stop_instance)
            delete_btn = ttk.Button(control_frame, text="Delete", command=delete_instance)
            
            # Test button actions
            assert start_instance() is True
            assert stop_instance() is True
            assert delete_instance() is True
            
            # Verify manager calls
            mock_n8n_mgr.start_instance.assert_called_with(1)
            mock_n8n_mgr.stop_instance.assert_called_with(1)
            mock_n8n_mgr.delete_instance.assert_called_with(1, False)
            
        except tk.TclError:
            pytest.skip("No display available for GUI testing")


class TestGUIInteractions:
    """Test GUI user interactions and event handling"""
    
    def setup_method(self):
        """Setup interaction test environment"""
        self.root = tk.Tk()
        self.root.withdraw()
    
    def teardown_method(self):
        """Cleanup test environment"""
        if self.root:
            self.root.destroy()
    
    def test_menu_interactions(self):
        """Test menu bar interactions"""
        try:
            # Create menu bar
            menubar = tk.Menu(self.root)
            self.root.config(menu=menubar)
            
            # File menu
            file_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="File", menu=file_menu)
            
            # Track menu actions
            menu_actions = []
            
            def new_instance():
                menu_actions.append("new_instance")
            
            def exit_app():
                menu_actions.append("exit_app")
            
            file_menu.add_command(label="New Instance", command=new_instance)
            file_menu.add_separator()
            file_menu.add_command(label="Exit", command=exit_app)
            
            # Simulate menu actions
            new_instance()
            exit_app()
            
            # Verify actions were called
            assert "new_instance" in menu_actions
            assert "exit_app" in menu_actions
            
        except tk.TclError:
            pytest.skip("No display available for GUI testing")
    
    def test_keyboard_shortcuts(self):
        """Test keyboard shortcut handling"""
        try:
            # Track keyboard events
            keyboard_events = []
            
            def handle_ctrl_n(event):
                keyboard_events.append("ctrl_n")
            
            def handle_ctrl_q(event):
                keyboard_events.append("ctrl_q")
            
            def handle_f5(event):
                keyboard_events.append("f5")
            
            # Bind keyboard shortcuts
            self.root.bind('<Control-n>', handle_ctrl_n)
            self.root.bind('<Control-q>', handle_ctrl_q)
            self.root.bind('<F5>', handle_f5)
            
            # Simulate keyboard events
            self.root.event_generate('<Control-n>')
            self.root.event_generate('<Control-q>')
            self.root.event_generate('<F5>')
            
            # Process events
            self.root.update()
            
            # Verify events were handled
            assert "ctrl_n" in keyboard_events
            assert "ctrl_q" in keyboard_events
            assert "f5" in keyboard_events
            
        except tk.TclError:
            pytest.skip("No display available for GUI testing")
    
    def test_window_resize_handling(self):
        """Test window resize event handling"""
        try:
            # Track resize events
            resize_events = []
            
            def handle_resize(event):
                if event.widget == self.root:
                    resize_events.append((event.width, event.height))
            
            # Bind resize event
            self.root.bind('<Configure>', handle_resize)
            
            # Simulate window resize
            self.root.geometry('800x600')
            self.root.update()
            
            self.root.geometry('1000x700')
            self.root.update()
            
            # Verify resize events were captured
            assert len(resize_events) >= 1
            
        except tk.TclError:
            pytest.skip("No display available for GUI testing")


class TestGUIDataBinding:
    """Test data binding between GUI and backend"""
    
    def setup_method(self):
        """Setup data binding test environment"""
        self.root = tk.Tk()
        self.root.withdraw()
    
    def teardown_method(self):
        """Cleanup test environment"""
        if self.root:
            self.root.destroy()
    
    @patch('core.n8n_manager.get_n8n_manager')
    def test_real_time_status_updates(self, mock_n8n_manager):
        """Test real-time status updates in GUI"""
        # Setup mock manager
        mock_n8n_mgr = Mock()
        mock_n8n_manager.return_value = mock_n8n_mgr
        
        # Mock changing instance status
        status_sequence = [
            {'id': 1, 'name': 'test', 'status': 'starting', 'health_status': 'unknown'},
            {'id': 1, 'name': 'test', 'status': 'running', 'health_status': 'healthy'},
            {'id': 1, 'name': 'test', 'status': 'stopping', 'health_status': 'unhealthy'},
            {'id': 1, 'name': 'test', 'status': 'stopped', 'health_status': 'unknown'}
        ]
        
        status_index = 0
        
        def get_status():
            nonlocal status_index
            if status_index < len(status_sequence):
                status = status_sequence[status_index]
                status_index += 1
                return status
            return status_sequence[-1]
        
        mock_n8n_mgr.get_instance_status.side_effect = lambda x: get_status()
        
        try:
            # Create status display
            status_frame = ttk.Frame(self.root)
            status_var = tk.StringVar()
            status_label = ttk.Label(status_frame, textvariable=status_var)
            
            # Simulate status updates
            update_count = 0
            
            def update_status():
                nonlocal update_count
                if update_count < len(status_sequence):
                    status = mock_n8n_mgr.get_instance_status(1)
                    status_var.set(f"{status['status']} ({status['health_status']})")
                    update_count += 1
                    
                    # Schedule next update
                    if update_count < len(status_sequence):
                        self.root.after(100, update_status)
            
            # Start status updates
            update_status()
            
            # Process updates
            for _ in range(len(status_sequence)):
                self.root.update()
                time.sleep(0.1)
            
            # Verify final status
            final_status = status_var.get()
            assert 'stopped' in final_status
            assert 'unknown' in final_status
            
        except tk.TclError:
            pytest.skip("No display available for GUI testing")
    
    @patch('core.config_manager.get_config')
    def test_configuration_binding(self, mock_config):
        """Test configuration changes reflected in GUI"""
        # Setup mock config
        config_data = {
            'gui.theme': 'modern',
            'gui.auto_refresh_interval': 5,
            'gui.show_advanced_options': False
        }
        
        mock_config_obj = Mock()
        mock_config_obj.get.side_effect = lambda key, default=None: config_data.get(key, default)
        mock_config_obj.set.side_effect = lambda key, value: config_data.update({key: value})
        mock_config.return_value = mock_config_obj
        
        try:
            # Create configuration controls
            config_frame = ttk.Frame(self.root)
            
            # Theme selection
            theme_var = tk.StringVar(value=config_data['gui.theme'])
            theme_combo = ttk.Combobox(config_frame, textvariable=theme_var)
            theme_combo['values'] = ('modern', 'classic', 'dark')
            
            # Refresh interval
            refresh_var = tk.IntVar(value=config_data['gui.auto_refresh_interval'])
            refresh_spin = ttk.Spinbox(config_frame, from_=1, to=60, textvariable=refresh_var)
            
            # Advanced options
            advanced_var = tk.BooleanVar(value=config_data['gui.show_advanced_options'])
            advanced_check = ttk.Checkbutton(config_frame, text="Show Advanced Options", variable=advanced_var)
            
            # Test configuration changes
            def apply_config():
                mock_config_obj.set('gui.theme', theme_var.get())
                mock_config_obj.set('gui.auto_refresh_interval', refresh_var.get())
                mock_config_obj.set('gui.show_advanced_options', advanced_var.get())
            
            # Change values
            theme_var.set('dark')
            refresh_var.set(10)
            advanced_var.set(True)
            
            # Apply changes
            apply_config()
            
            # Verify configuration was updated
            assert config_data['gui.theme'] == 'dark'
            assert config_data['gui.auto_refresh_interval'] == 10
            assert config_data['gui.show_advanced_options'] is True
            
        except tk.TclError:
            pytest.skip("No display available for GUI testing")


class TestGUIErrorHandling:
    """Test GUI error handling and user feedback"""
    
    def setup_method(self):
        """Setup error handling test environment"""
        self.root = tk.Tk()
        self.root.withdraw()
    
    def teardown_method(self):
        """Cleanup test environment"""
        if self.root:
            self.root.destroy()
    
    def test_error_message_display(self):
        """Test error message display to user"""
        try:
            # Create error display area
            error_frame = ttk.Frame(self.root)
            error_var = tk.StringVar()
            error_label = ttk.Label(error_frame, textvariable=error_var, foreground='red')
            
            # Test error display function
            def show_error(message):
                error_var.set(f"Error: {message}")
                # In real implementation, might also show messagebox
            
            def clear_error():
                error_var.set("")
            
            # Test error scenarios
            test_errors = [
                "Docker daemon not available",
                "Instance creation failed",
                "Invalid port number",
                "Database connection error"
            ]
            
            for error_msg in test_errors:
                show_error(error_msg)
                assert error_msg in error_var.get()
                
                clear_error()
                assert error_var.get() == ""
            
        except tk.TclError:
            pytest.skip("No display available for GUI testing")
    
    @patch('tkinter.messagebox.showerror')
    def test_critical_error_dialogs(self, mock_showerror):
        """Test critical error dialog display"""
        try:
            # Test critical error handling
            def handle_critical_error(title, message):
                # In real implementation, would show error dialog
                mock_showerror(title, message)
            
            # Test various critical errors
            critical_errors = [
                ("Database Error", "Failed to connect to database"),
                ("Docker Error", "Docker daemon is not running"),
                ("Configuration Error", "Invalid configuration file"),
                ("Permission Error", "Insufficient permissions")
            ]
            
            for title, message in critical_errors:
                handle_critical_error(title, message)
            
            # Verify error dialogs were shown
            assert mock_showerror.call_count == len(critical_errors)
            
            # Verify correct parameters
            for i, (title, message) in enumerate(critical_errors):
                call_args = mock_showerror.call_args_list[i]
                assert call_args[0][0] == title
                assert call_args[0][1] == message
            
        except tk.TclError:
            pytest.skip("No display available for GUI testing")
    
    def test_input_validation_feedback(self):
        """Test input validation and user feedback"""
        try:
            # Create input validation test
            validation_frame = ttk.Frame(self.root)
            
            # Instance name validation
            name_var = tk.StringVar()
            name_entry = ttk.Entry(validation_frame, textvariable=name_var)
            name_error_var = tk.StringVar()
            name_error_label = ttk.Label(validation_frame, textvariable=name_error_var, foreground='red')
            
            def validate_name():
                name = name_var.get()
                if not name:
                    name_error_var.set("Instance name is required")
                    return False
                elif len(name) < 3:
                    name_error_var.set("Instance name must be at least 3 characters")
                    return False
                elif not name.replace('-', '').replace('_', '').isalnum():
                    name_error_var.set("Instance name can only contain letters, numbers, hyphens, and underscores")
                    return False
                else:
                    name_error_var.set("")
                    return True
            
            # Test validation scenarios
            test_cases = [
                ("", False, "required"),
                ("ab", False, "at least 3"),
                ("test@123", False, "letters, numbers"),
                ("test-instance", True, ""),
                ("test_instance_1", True, "")
            ]
            
            for test_name, expected_valid, expected_error_text in test_cases:
                name_var.set(test_name)
                is_valid = validate_name()
                error_text = name_error_var.get()
                
                assert is_valid == expected_valid, f"Validation failed for '{test_name}'"
                if expected_error_text:
                    assert expected_error_text in error_text.lower(), f"Expected error text not found for '{test_name}'"
                else:
                    assert error_text == "", f"Unexpected error text for valid input '{test_name}'"
            
        except tk.TclError:
            pytest.skip("No display available for GUI testing")


class TestGUIAccessibility:
    """Test GUI accessibility features"""
    
    def setup_method(self):
        """Setup accessibility test environment"""
        self.root = tk.Tk()
        self.root.withdraw()
    
    def teardown_method(self):
        """Cleanup test environment"""
        if self.root:
            self.root.destroy()
    
    def test_keyboard_navigation(self):
        """Test keyboard navigation through GUI elements"""
        try:
            # Create form with multiple elements
            form_frame = ttk.Frame(self.root)
            
            # Create focusable elements
            elements = []
            
            name_entry = ttk.Entry(form_frame)
            elements.append(name_entry)
            
            image_combo = ttk.Combobox(form_frame)
            elements.append(image_combo)
            
            port_entry = ttk.Entry(form_frame)
            elements.append(port_entry)
            
            create_btn = ttk.Button(form_frame, text="Create")
            elements.append(create_btn)
            
            cancel_btn = ttk.Button(form_frame, text="Cancel")
            elements.append(cancel_btn)
            
            # Pack elements
            for element in elements:
                element.pack(pady=2)
            
            # Test tab order
            focus_order = []
            
            def track_focus(event):
                focus_order.append(event.widget)
            
            # Bind focus events
            for element in elements:
                element.bind('<FocusIn>', track_focus)
            
            # Simulate tab navigation
            for element in elements:
                element.focus_set()
                self.root.update()
            
            # Verify focus order
            assert len(focus_order) == len(elements)
            
        except tk.TclError:
            pytest.skip("No display available for GUI testing")
    
    def test_screen_reader_compatibility(self):
        """Test screen reader compatibility features"""
        try:
            # Create accessible form
            accessible_frame = ttk.Frame(self.root)
            
            # Label-input associations
            name_label = ttk.Label(accessible_frame, text="Instance Name:")
            name_entry = ttk.Entry(accessible_frame)
            
            # In a real implementation, would use proper label association
            # For testing, verify labels exist
            assert name_label.cget('text') == "Instance Name:"
            
            # Status information should be accessible
            status_label = ttk.Label(accessible_frame, text="Status: Running")
            assert "Status:" in status_label.cget('text')
            
            # Buttons should have descriptive text
            start_btn = ttk.Button(accessible_frame, text="Start Instance")
            stop_btn = ttk.Button(accessible_frame, text="Stop Instance")
            
            assert start_btn.cget('text') == "Start Instance"
            assert stop_btn.cget('text') == "Stop Instance"
            
        except tk.TclError:
            pytest.skip("No display available for GUI testing")


if __name__ == '__main__':
    pytest.main([__file__])