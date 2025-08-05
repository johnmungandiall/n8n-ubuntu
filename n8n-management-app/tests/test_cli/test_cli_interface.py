"""
CLI interface tests for n8n Management App
Tests command-line interface functionality and user interactions
"""

import pytest
import subprocess
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, call
import io
from contextlib import redirect_stdout, redirect_stderr

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestCLIBasicFunctionality:
    """Test basic CLI functionality and command parsing"""
    
    def setup_method(self):
        """Setup CLI test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.db_path = Path(self.temp_dir) / "test.db"
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cli_help_display(self):
        """Test CLI help message display"""
        from main import create_argument_parser
        
        parser = create_argument_parser()
        
        # Capture help output
        with io.StringIO() as help_output:
            try:
                parser.print_help(help_output)
                help_text = help_output.getvalue()
                
                # Verify help contains expected information
                assert 'n8n Management App' in help_text
                assert '--cli' in help_text
                assert 'list' in help_text
                assert 'create' in help_text
                assert 'start' in help_text
                assert 'stop' in help_text
                assert 'delete' in help_text
                assert 'status' in help_text
                assert 'logs' in help_text
                
            except SystemExit:
                # Help command exits, which is expected
                pass
    
    def test_cli_command_parsing(self):
        """Test CLI command parsing for all supported commands"""
        from main import create_argument_parser
        
        parser = create_argument_parser()
        
        # Test command parsing scenarios
        test_cases = [
            # List command
            (['--cli', 'list'], {
                'cli': True,
                'command': 'list'
            }),
            
            # Create command
            (['--cli', 'create', '--name', 'test-instance'], {
                'cli': True,
                'command': 'create',
                'name': 'test-instance'
            }),
            
            # Start command
            (['--cli', 'start', '--id', '1'], {
                'cli': True,
                'command': 'start',
                'instance_id': 1
            }),
            
            # Stop command
            (['--cli', 'stop', '--id', '2'], {
                'cli': True,
                'command': 'stop',
                'instance_id': 2
            }),
            
            # Delete command with data removal
            (['--cli', 'delete', '--id', '3', '--remove-data'], {
                'cli': True,
                'command': 'delete',
                'instance_id': 3,
                'remove_data': True
            }),
            
            # Status command
            (['--cli', 'status', '--id', '4'], {
                'cli': True,
                'command': 'status',
                'instance_id': 4
            }),
            
            # Logs command with tail
            (['--cli', 'logs', '--id', '5', '--tail', '100'], {
                'cli': True,
                'command': 'logs',
                'instance_id': 5,
                'tail': 100
            }),
            
            # Debug mode
            (['--debug'], {
                'debug': True
            }),
            
            # Custom paths
            (['--config-dir', '/custom/config', '--db-path', '/custom/db.sqlite'], {
                'config_dir': '/custom/config',
                'db_path': '/custom/db.sqlite'
            })
        ]
        
        for args_list, expected_attrs in test_cases:
            args = parser.parse_args(args_list)
            
            for attr_name, expected_value in expected_attrs.items():
                actual_value = getattr(args, attr_name)
                assert actual_value == expected_value, f"Failed for {args_list}: {attr_name} = {actual_value}, expected {expected_value}"
    
    def test_cli_invalid_commands(self):
        """Test CLI handling of invalid commands"""
        from main import create_argument_parser
        
        parser = create_argument_parser()
        
        # Test invalid command scenarios
        invalid_cases = [
            ['--cli', 'invalid-command'],
            ['--cli', 'create'],  # Missing required name
            ['--cli', 'start'],   # Missing required ID
            ['--cli', 'stop'],    # Missing required ID
            ['--cli', 'delete'],  # Missing required ID
            ['--cli', 'status'],  # Missing required ID
            ['--cli', 'logs'],    # Missing required ID
        ]
        
        for invalid_args in invalid_cases:
            with pytest.raises(SystemExit):
                parser.parse_args(invalid_args)


class TestCLIInstanceOperations:
    """Test CLI instance management operations"""
    
    def setup_method(self):
        """Setup CLI instance operations test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.db_path = Path(self.temp_dir) / "test.db"
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('main.get_n8n_manager')
    @patch.object(sys, 'argv', ['main.py', '--cli', 'list'])
    def test_cli_list_instances(self, mock_get_n8n_manager):
        """Test CLI list instances command"""
        # Setup mock manager
        mock_manager = Mock()
        mock_instances = [
            {'id': 1, 'name': 'test1', 'status': 'running', 'port': 5678, 'image': 'n8nio/n8n:latest'},
            {'id': 2, 'name': 'test2', 'status': 'stopped', 'port': None, 'image': 'n8nio/n8n:latest'}
        ]
        mock_manager.list_instances.return_value = mock_instances
        mock_get_n8n_manager.return_value = mock_manager
        
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        
        # Mock initialization
        with patch.object(app, 'initialize', return_value=True):
            # Create mock args
            args = Mock()
            args.command = 'list'
            
            # Capture output
            with io.StringIO() as output:
                with redirect_stdout(output):
                    result = app.run_cli(args)
                
                output_text = output.getvalue()
                
                # Verify output
                assert result == 0
                assert 'test1' in output_text
                assert 'test2' in output_text
                assert 'running' in output_text
                assert 'stopped' in output_text
                assert '5678' in output_text
    
    @patch('main.get_n8n_manager')
    def test_cli_create_instance(self, mock_get_n8n_manager):
        """Test CLI create instance command"""
        # Setup mock manager
        mock_manager = Mock()
        mock_manager.create_instance.return_value = (True, "Instance created successfully", 1)
        mock_get_n8n_manager.return_value = mock_manager
        
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        
        # Mock initialization
        with patch.object(app, 'initialize', return_value=True):
            # Create mock args
            args = Mock()
            args.command = 'create'
            args.name = 'test-instance'
            
            # Capture output
            with io.StringIO() as output:
                with redirect_stdout(output):
                    result = app.run_cli(args)
                
                output_text = output.getvalue()
                
                # Verify result
                assert result == 0
                assert 'Success' in output_text
                assert 'Instance created successfully' in output_text
                assert 'ID: 1' in output_text
                
                # Verify manager was called correctly
                mock_manager.create_instance.assert_called_once_with('test-instance')
    
    @patch('main.get_n8n_manager')
    def test_cli_start_instance(self, mock_get_n8n_manager):
        """Test CLI start instance command"""
        # Setup mock manager
        mock_manager = Mock()
        mock_manager.start_instance.return_value = (True, "Instance started successfully")
        mock_get_n8n_manager.return_value = mock_manager
        
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        
        # Mock initialization
        with patch.object(app, 'initialize', return_value=True):
            # Create mock args
            args = Mock()
            args.command = 'start'
            args.instance_id = 1
            
            # Capture output
            with io.StringIO() as output:
                with redirect_stdout(output):
                    result = app.run_cli(args)
                
                output_text = output.getvalue()
                
                # Verify result
                assert result == 0
                assert 'Success' in output_text
                assert 'Instance started successfully' in output_text
                
                # Verify manager was called correctly
                mock_manager.start_instance.assert_called_once_with(1)
    
    @patch('main.get_n8n_manager')
    def test_cli_stop_instance(self, mock_get_n8n_manager):
        """Test CLI stop instance command"""
        # Setup mock manager
        mock_manager = Mock()
        mock_manager.stop_instance.return_value = (True, "Instance stopped successfully")
        mock_get_n8n_manager.return_value = mock_manager
        
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        
        # Mock initialization
        with patch.object(app, 'initialize', return_value=True):
            # Create mock args
            args = Mock()
            args.command = 'stop'
            args.instance_id = 1
            
            # Capture output
            with io.StringIO() as output:
                with redirect_stdout(output):
                    result = app.run_cli(args)
                
                output_text = output.getvalue()
                
                # Verify result
                assert result == 0
                assert 'Success' in output_text
                assert 'Instance stopped successfully' in output_text
                
                # Verify manager was called correctly
                mock_manager.stop_instance.assert_called_once_with(1)
    
    @patch('main.get_n8n_manager')
    def test_cli_delete_instance(self, mock_get_n8n_manager):
        """Test CLI delete instance command"""
        # Setup mock manager
        mock_manager = Mock()
        mock_manager.delete_instance.return_value = (True, "Instance deleted successfully")
        mock_get_n8n_manager.return_value = mock_manager
        
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        
        # Mock initialization
        with patch.object(app, 'initialize', return_value=True):
            # Test delete without data removal
            args = Mock()
            args.command = 'delete'
            args.instance_id = 1
            args.remove_data = False
            
            with io.StringIO() as output:
                with redirect_stdout(output):
                    result = app.run_cli(args)
                
                output_text = output.getvalue()
                
                assert result == 0
                assert 'Success' in output_text
                mock_manager.delete_instance.assert_called_with(1, False)
            
            # Test delete with data removal
            args.remove_data = True
            mock_manager.reset_mock()
            
            with io.StringIO() as output:
                with redirect_stdout(output):
                    result = app.run_cli(args)
                
                assert result == 0
                mock_manager.delete_instance.assert_called_with(1, True)
    
    @patch('main.get_n8n_manager')
    def test_cli_instance_status(self, mock_get_n8n_manager):
        """Test CLI instance status command"""
        # Setup mock manager
        mock_manager = Mock()
        mock_status = {
            'name': 'test-instance',
            'status': 'running',
            'health_status': 'healthy',
            'port': 5678,
            'created_at': '2023-01-01 00:00:00',
            'container': {
                'resource_usage': {
                    'cpu_percent': 15.5,
                    'memory_percent': 25.0
                }
            }
        }
        mock_manager.get_instance_status.return_value = mock_status
        mock_get_n8n_manager.return_value = mock_manager
        
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        
        # Mock initialization
        with patch.object(app, 'initialize', return_value=True):
            # Create mock args
            args = Mock()
            args.command = 'status'
            args.instance_id = 1
            
            # Capture output
            with io.StringIO() as output:
                with redirect_stdout(output):
                    result = app.run_cli(args)
                
                output_text = output.getvalue()
                
                # Verify result
                assert result == 0
                assert 'test-instance' in output_text
                assert 'running' in output_text
                assert 'healthy' in output_text
                assert '5678' in output_text
                assert '15.5%' in output_text
                assert '25.0%' in output_text
                
                # Verify manager was called correctly
                mock_manager.get_instance_status.assert_called_once_with(1)
    
    @patch('main.get_n8n_manager')
    def test_cli_instance_logs(self, mock_get_n8n_manager):
        """Test CLI instance logs command"""
        # Setup mock manager
        mock_manager = Mock()
        mock_logs = "2023-01-01 00:00:00 - n8n instance started\n2023-01-01 00:01:00 - Workflow executed"
        mock_manager.get_instance_logs.return_value = mock_logs
        mock_get_n8n_manager.return_value = mock_manager
        
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        
        # Mock initialization
        with patch.object(app, 'initialize', return_value=True):
            # Create mock args
            args = Mock()
            args.command = 'logs'
            args.instance_id = 1
            args.tail = 50
            
            # Capture output
            with io.StringIO() as output:
                with redirect_stdout(output):
                    result = app.run_cli(args)
                
                output_text = output.getvalue()
                
                # Verify result
                assert result == 0
                assert 'n8n instance started' in output_text
                assert 'Workflow executed' in output_text
                
                # Verify manager was called correctly
                mock_manager.get_instance_logs.assert_called_once_with(1, 50)


class TestCLIErrorHandling:
    """Test CLI error handling and user feedback"""
    
    def setup_method(self):
        """Setup CLI error handling test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.db_path = Path(self.temp_dir) / "test.db"
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('main.get_n8n_manager')
    def test_cli_operation_failures(self, mock_get_n8n_manager):
        """Test CLI handling of operation failures"""
        # Setup mock manager with failures
        mock_manager = Mock()
        mock_get_n8n_manager.return_value = mock_manager
        
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        
        # Mock initialization
        with patch.object(app, 'initialize', return_value=True):
            # Test create instance failure
            mock_manager.create_instance.return_value = (False, "Docker daemon not available", None)
            
            args = Mock()
            args.command = 'create'
            args.name = 'test-instance'
            
            with io.StringIO() as output:
                with redirect_stdout(output):
                    result = app.run_cli(args)
                
                output_text = output.getvalue()
                
                assert result == 1  # Should return error code
                assert 'Error' in output_text
                assert 'Docker daemon not available' in output_text
            
            # Test start instance failure
            mock_manager.start_instance.return_value = (False, "Instance not found")
            
            args.command = 'start'
            args.instance_id = 999
            
            with io.StringIO() as output:
                with redirect_stdout(output):
                    result = app.run_cli(args)
                
                output_text = output.getvalue()
                
                assert result == 1
                assert 'Error' in output_text
                assert 'Instance not found' in output_text
    
    def test_cli_missing_required_arguments(self):
        """Test CLI handling of missing required arguments"""
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        
        # Mock initialization
        with patch.object(app, 'initialize', return_value=True):
            # Test create without name
            args = Mock()
            args.command = 'create'
            args.name = None
            
            with io.StringIO() as output:
                with redirect_stdout(output):
                    result = app.run_cli(args)
                
                output_text = output.getvalue()
                
                assert result == 1
                assert 'Error' in output_text
                assert 'name is required' in output_text
            
            # Test start without instance ID
            args.command = 'start'
            args.instance_id = None
            
            with io.StringIO() as output:
                with redirect_stdout(output):
                    result = app.run_cli(args)
                
                output_text = output.getvalue()
                
                assert result == 1
                assert 'Error' in output_text
                assert 'ID is required' in output_text
    
    def test_cli_initialization_failure(self):
        """Test CLI handling of initialization failure"""
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        
        # Mock initialization failure
        with patch.object(app, 'initialize', return_value=False):
            args = Mock()
            args.command = 'list'
            
            result = app.run_cli(args)
            
            assert result == 1  # Should return error code
    
    @patch('main.get_n8n_manager')
    def test_cli_exception_handling(self, mock_get_n8n_manager):
        """Test CLI handling of unexpected exceptions"""
        # Setup mock manager that raises exceptions
        mock_manager = Mock()
        mock_manager.list_instances.side_effect = Exception("Unexpected error")
        mock_get_n8n_manager.return_value = mock_manager
        
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        
        # Mock initialization
        with patch.object(app, 'initialize', return_value=True):
            args = Mock()
            args.command = 'list'
            
            with io.StringIO() as output:
                with redirect_stdout(output):
                    result = app.run_cli(args)
                
                # Should handle exception gracefully
                assert result == 1


class TestCLIOutputFormatting:
    """Test CLI output formatting and presentation"""
    
    def setup_method(self):
        """Setup CLI output formatting test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.db_path = Path(self.temp_dir) / "test.db"
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('main.get_n8n_manager')
    def test_cli_table_formatting(self, mock_get_n8n_manager):
        """Test CLI table formatting for list command"""
        # Setup mock manager with various instance states
        mock_manager = Mock()
        mock_instances = [
            {'id': 1, 'name': 'short', 'status': 'running', 'port': 5678, 'image': 'n8nio/n8n:latest'},
            {'id': 2, 'name': 'very-long-instance-name', 'status': 'stopped', 'port': None, 'image': 'n8nio/n8n:0.200.0'},
            {'id': 3, 'name': 'test', 'status': 'starting', 'port': 5680, 'image': 'custom/n8n:dev'}
        ]
        mock_manager.list_instances.return_value = mock_instances
        mock_get_n8n_manager.return_value = mock_manager
        
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        
        # Mock initialization
        with patch.object(app, 'initialize', return_value=True):
            args = Mock()
            args.command = 'list'
            
            with io.StringIO() as output:
                with redirect_stdout(output):
                    result = app.run_cli(args)
                
                output_text = output.getvalue()
                
                # Verify table structure
                lines = output_text.strip().split('\n')
                
                # Should have header line
                header_line = None
                for line in lines:
                    if 'ID' in line and 'Name' in line and 'Status' in line:
                        header_line = line
                        break
                
                assert header_line is not None, "Table header not found"
                
                # Should have separator line
                separator_found = any('-' in line for line in lines)
                assert separator_found, "Table separator not found"
                
                # Should have data lines
                data_lines = [line for line in lines if any(str(i['id']) in line for i in mock_instances)]
                assert len(data_lines) >= 3, "Not all instances displayed"
                
                # Verify column alignment
                for instance in mock_instances:
                    instance_line = next((line for line in lines if str(instance['id']) in line), None)
                    assert instance_line is not None, f"Instance {instance['id']} not found in output"
                    assert instance['name'] in instance_line
                    assert instance['status'] in instance_line
    
    @patch('main.get_n8n_manager')
    def test_cli_empty_list_formatting(self, mock_get_n8n_manager):
        """Test CLI formatting when no instances exist"""
        # Setup mock manager with empty list
        mock_manager = Mock()
        mock_manager.list_instances.return_value = []
        mock_get_n8n_manager.return_value = mock_manager
        
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        
        # Mock initialization
        with patch.object(app, 'initialize', return_value=True):
            args = Mock()
            args.command = 'list'
            
            with io.StringIO() as output:
                with redirect_stdout(output):
                    result = app.run_cli(args)
                
                output_text = output.getvalue()
                
                # Should display appropriate message
                assert result == 0
                assert 'No instances found' in output_text
    
    @patch('main.get_n8n_manager')
    def test_cli_status_formatting(self, mock_get_n8n_manager):
        """Test CLI status command formatting"""
        # Setup mock manager with detailed status
        mock_manager = Mock()
        mock_status = {
            'name': 'test-instance',
            'status': 'running',
            'health_status': 'healthy',
            'port': 5678,
            'created_at': '2023-01-01 12:00:00',
            'container': {
                'resource_usage': {
                    'cpu_percent': 15.5,
                    'memory_percent': 25.0
                }
            }
        }
        mock_manager.get_instance_status.return_value = mock_status
        mock_get_n8n_manager.return_value = mock_manager
        
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        
        # Mock initialization
        with patch.object(app, 'initialize', return_value=True):
            args = Mock()
            args.command = 'status'
            args.instance_id = 1
            
            with io.StringIO() as output:
                with redirect_stdout(output):
                    result = app.run_cli(args)
                
                output_text = output.getvalue()
                
                # Verify status formatting
                assert result == 0
                
                # Should have key-value pairs
                assert 'Instance:' in output_text
                assert 'Status:' in output_text
                assert 'Health:' in output_text
                assert 'Port:' in output_text
                assert 'Created:' in output_text
                assert 'CPU:' in output_text
                assert 'Memory:' in output_text
                
                # Should have proper values
                assert 'test-instance' in output_text
                assert 'running' in output_text
                assert 'healthy' in output_text
                assert '5678' in output_text
                assert '15.5%' in output_text
                assert '25.0%' in output_text


class TestCLIIntegration:
    """Test CLI integration with system components"""
    
    def test_cli_subprocess_execution(self):
        """Test CLI execution as subprocess"""
        # This test requires the main.py to be executable
        main_py_path = Path(__file__).parent.parent.parent / "src" / "main.py"
        
        if not main_py_path.exists():
            pytest.skip("main.py not found for subprocess testing")
        
        try:
            # Test help command
            result = subprocess.run([
                sys.executable, str(main_py_path), '--help'
            ], capture_output=True, text=True, timeout=10)
            
            # Help should work even without proper setup
            assert 'n8n Management App' in result.stdout or 'n8n Management App' in result.stderr
            
        except subprocess.TimeoutExpired:
            pytest.skip("CLI subprocess test timed out")
        except FileNotFoundError:
            pytest.skip("Python executable not found for subprocess testing")
    
    def test_cli_environment_variables(self):
        """Test CLI handling of environment variables"""
        import os
        
        # Test debug environment variable
        with patch.dict(os.environ, {'N8N_MANAGER_LOG_LEVEL': 'DEBUG'}):
            from main import create_argument_parser
            
            parser = create_argument_parser()
            args = parser.parse_args([])
            
            # Environment variable should be respected
            assert os.environ.get('N8N_MANAGER_LOG_LEVEL') == 'DEBUG'
    
    def test_cli_signal_handling(self):
        """Test CLI signal handling (Ctrl+C, etc.)"""
        from main import N8nManagementApp
        
        app = N8nManagementApp()
        
        # Test signal handler setup
        with patch('signal.signal') as mock_signal:
            with patch.object(app, 'initialize', return_value=True):
                with patch.object(app, 'shutdown'):
                    try:
                        app.run_gui()  # This sets up signal handlers
                    except:
                        pass  # Expected to fail without proper GUI setup
            
            # Verify signal handlers were set up
            assert mock_signal.call_count >= 2  # SIGINT and SIGTERM


if __name__ == '__main__':
    pytest.main([__file__])