"""
Unit tests for main.py - Application entry point and core functionality
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import argparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from main import N8nManagementApp, create_argument_parser, main


class TestN8nManagementApp:
    """Test cases for N8nManagementApp class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.app = N8nManagementApp()
    
    def test_init_default_values(self):
        """Test app initialization with default values"""
        assert self.app.config_dir is None
        assert self.app.db_path is None
        assert self.app.logger is None
        assert self.app.config is None
        assert self.app.database is None
        assert self.app.docker_manager is None
        assert self.app.main_window is None
        assert self.app.running is False
    
    def test_init_custom_values(self):
        """Test app initialization with custom values"""
        app = N8nManagementApp(config_dir="/custom/config", db_path="/custom/db.sqlite")
        assert app.config_dir == "/custom/config"
        assert app.db_path == "/custom/db.sqlite"
    
    @patch('main.setup_logger')
    @patch('main.setup_config')
    @patch('main.setup_database')
    @patch('main.get_docker_manager')
    def test_initialize_success(self, mock_docker_manager, mock_setup_database, 
                               mock_setup_config, mock_setup_logger):
        """Test successful application initialization"""
        # Setup mocks
        mock_logger = Mock()
        mock_config = Mock()
        mock_database = Mock()
        mock_docker = Mock()
        
        mock_setup_logger.return_value = mock_logger
        mock_setup_config.return_value = mock_config
        mock_setup_database.return_value = mock_database
        mock_docker_manager.return_value = mock_docker
        
        mock_docker.is_docker_available.return_value = True
        mock_docker.get_docker_info.return_value = {'server_version': '20.10.0'}
        
        # Test initialization
        result = self.app.initialize()
        
        assert result is True
        assert self.app.logger == mock_logger
        assert self.app.config == mock_config
        assert self.app.database == mock_database
        assert self.app.docker_manager == mock_docker
        
        # Verify method calls
        mock_setup_logger.assert_called_once()
        mock_setup_config.assert_called_once_with(None)
        mock_setup_database.assert_called_once_with(None)
        mock_config.update_from_env.assert_called_once()
        mock_docker.is_docker_available.assert_called_once()
        mock_docker.get_docker_info.assert_called_once()
    
    @patch('main.setup_logger')
    @patch('main.setup_config')
    @patch('main.setup_database')
    @patch('main.get_docker_manager')
    def test_initialize_docker_unavailable(self, mock_docker_manager, mock_setup_database,
                                          mock_setup_config, mock_setup_logger):
        """Test initialization failure when Docker is unavailable"""
        # Setup mocks
        mock_logger = Mock()
        mock_config = Mock()
        mock_database = Mock()
        mock_docker = Mock()
        
        mock_setup_logger.return_value = mock_logger
        mock_setup_config.return_value = mock_config
        mock_setup_database.return_value = mock_database
        mock_docker_manager.return_value = mock_docker
        
        mock_docker.is_docker_available.return_value = False
        
        # Test initialization
        result = self.app.initialize()
        
        assert result is False
        mock_logger.error.assert_called_with(
            "Docker daemon is not available. Please ensure Docker is running."
        )
    
    @patch('main.setup_logger')
    def test_initialize_exception_handling(self, mock_setup_logger):
        """Test initialization exception handling"""
        mock_setup_logger.side_effect = Exception("Setup failed")
        
        result = self.app.initialize()
        
        assert result is False
    
    @patch.object(N8nManagementApp, 'initialize')
    @patch.object(N8nManagementApp, 'shutdown')
    @patch('main.MainWindow')
    @patch('signal.signal')
    def test_run_gui_success(self, mock_signal, mock_main_window, mock_shutdown, mock_initialize):
        """Test successful GUI application run"""
        mock_initialize.return_value = True
        mock_window = Mock()
        mock_main_window.return_value = mock_window
        
        result = self.app.run_gui()
        
        assert result == 0
        mock_initialize.assert_called_once()
        mock_main_window.assert_called_once()
        mock_window.run.assert_called_once()
        mock_shutdown.assert_called_once()
    
    @patch.object(N8nManagementApp, 'initialize')
    @patch.object(N8nManagementApp, 'shutdown')
    def test_run_gui_initialization_failure(self, mock_shutdown, mock_initialize):
        """Test GUI run with initialization failure"""
        mock_initialize.return_value = False
        
        result = self.app.run_gui()
        
        assert result == 1
        mock_shutdown.assert_called_once()
    
    @patch.object(N8nManagementApp, 'initialize')
    @patch.object(N8nManagementApp, 'shutdown')
    @patch('main.MainWindow')
    def test_run_gui_keyboard_interrupt(self, mock_main_window, mock_shutdown, mock_initialize):
        """Test GUI run with keyboard interrupt"""
        mock_initialize.return_value = True
        mock_window = Mock()
        mock_main_window.return_value = mock_window
        mock_window.run.side_effect = KeyboardInterrupt()
        
        result = self.app.run_gui()
        
        assert result == 0
        mock_shutdown.assert_called_once()
    
    @patch.object(N8nManagementApp, 'initialize')
    @patch.object(N8nManagementApp, 'shutdown')
    @patch('main.get_n8n_manager')
    def test_run_cli_list_command(self, mock_get_n8n_manager, mock_shutdown, mock_initialize):
        """Test CLI list command"""
        mock_initialize.return_value = True
        mock_n8n_manager = Mock()
        mock_get_n8n_manager.return_value = mock_n8n_manager
        
        mock_instances = [
            {'id': 1, 'name': 'test1', 'status': 'running', 'port': 5678, 'image': 'n8nio/n8n'},
            {'id': 2, 'name': 'test2', 'status': 'stopped', 'port': None, 'image': 'n8nio/n8n'}
        ]
        mock_n8n_manager.list_instances.return_value = mock_instances
        
        args = Mock()
        args.command = 'list'
        
        with patch('builtins.print') as mock_print:
            result = self.app.run_cli(args)
        
        assert result == 0
        mock_n8n_manager.list_instances.assert_called_once()
        mock_shutdown.assert_called_once()
    
    @patch.object(N8nManagementApp, 'initialize')
    @patch.object(N8nManagementApp, 'shutdown')
    @patch('main.get_n8n_manager')
    def test_run_cli_create_command_success(self, mock_get_n8n_manager, mock_shutdown, mock_initialize):
        """Test CLI create command success"""
        mock_initialize.return_value = True
        mock_n8n_manager = Mock()
        mock_get_n8n_manager.return_value = mock_n8n_manager
        
        mock_n8n_manager.create_instance.return_value = (True, "Instance created", 1)
        
        args = Mock()
        args.command = 'create'
        args.name = 'test-instance'
        
        with patch('builtins.print') as mock_print:
            result = self.app.run_cli(args)
        
        assert result == 0
        mock_n8n_manager.create_instance.assert_called_once_with('test-instance')
    
    @patch.object(N8nManagementApp, 'initialize')
    @patch.object(N8nManagementApp, 'shutdown')
    @patch('main.get_n8n_manager')
    def test_run_cli_create_command_no_name(self, mock_get_n8n_manager, mock_shutdown, mock_initialize):
        """Test CLI create command without name"""
        mock_initialize.return_value = True
        
        args = Mock()
        args.command = 'create'
        args.name = None
        
        with patch('builtins.print') as mock_print:
            result = self.app.run_cli(args)
        
        assert result == 1
    
    def test_signal_handler(self):
        """Test signal handler"""
        self.app.logger = Mock()
        
        with patch.object(self.app, 'shutdown') as mock_shutdown:
            with patch('sys.exit') as mock_exit:
                self.app._signal_handler(2, None)
        
        mock_shutdown.assert_called_once()
        mock_exit.assert_called_once_with(0)
    
    def test_shutdown_not_running(self):
        """Test shutdown when app is not running"""
        self.app.running = False
        
        # Should return early without doing anything
        self.app.shutdown()
        
        assert self.app.running is False
    
    def test_shutdown_with_components(self):
        """Test shutdown with initialized components"""
        self.app.running = True
        self.app.logger = Mock()
        self.app.main_window = Mock()
        self.app.database = Mock()
        
        self.app.shutdown()
        
        assert self.app.running is False
        self.app.main_window.destroy.assert_called_once()


class TestArgumentParser:
    """Test cases for argument parser"""
    
    def test_create_argument_parser(self):
        """Test argument parser creation"""
        parser = create_argument_parser()
        
        assert isinstance(parser, argparse.ArgumentParser)
        assert 'n8n Management App' in parser.description
    
    def test_parser_default_gui_mode(self):
        """Test parser defaults to GUI mode"""
        parser = create_argument_parser()
        args = parser.parse_args([])
        
        assert args.cli is False
        assert args.config_dir is None
        assert args.db_path is None
        assert args.debug is False
    
    def test_parser_cli_mode(self):
        """Test parser CLI mode"""
        parser = create_argument_parser()
        args = parser.parse_args(['--cli', 'list'])
        
        assert args.cli is True
        assert args.command == 'list'
    
    def test_parser_create_command(self):
        """Test parser create command with name"""
        parser = create_argument_parser()
        args = parser.parse_args(['--cli', 'create', '--name', 'test-instance'])
        
        assert args.cli is True
        assert args.command == 'create'
        assert args.name == 'test-instance'
    
    def test_parser_instance_operations(self):
        """Test parser instance operations"""
        parser = create_argument_parser()
        args = parser.parse_args(['--cli', 'start', '--id', '1'])
        
        assert args.cli is True
        assert args.command == 'start'
        assert args.instance_id == 1
    
    def test_parser_debug_mode(self):
        """Test parser debug mode"""
        parser = create_argument_parser()
        args = parser.parse_args(['--debug'])
        
        assert args.debug is True
    
    def test_parser_custom_paths(self):
        """Test parser with custom paths"""
        parser = create_argument_parser()
        args = parser.parse_args([
            '--config-dir', '/custom/config',
            '--db-path', '/custom/db.sqlite'
        ])
        
        assert args.config_dir == '/custom/config'
        assert args.db_path == '/custom/db.sqlite'


class TestMainFunction:
    """Test cases for main function"""
    
    @patch('main.N8nManagementApp')
    @patch('main.create_argument_parser')
    def test_main_gui_mode(self, mock_parser_func, mock_app_class):
        """Test main function in GUI mode"""
        # Setup mocks
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.cli = False
        mock_args.config_dir = None
        mock_args.db_path = None
        mock_args.debug = False
        
        mock_parser.parse_args.return_value = mock_args
        mock_parser_func.return_value = mock_parser
        
        mock_app = Mock()
        mock_app.run_gui.return_value = 0
        mock_app_class.return_value = mock_app
        
        with patch('sys.argv', ['main.py']):
            result = main()
        
        assert result == 0
        mock_app_class.assert_called_once_with(config_dir=None, db_path=None)
        mock_app.run_gui.assert_called_once()
    
    @patch('main.N8nManagementApp')
    @patch('main.create_argument_parser')
    def test_main_cli_mode(self, mock_parser_func, mock_app_class):
        """Test main function in CLI mode"""
        # Setup mocks
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.cli = True
        mock_args.command = 'list'
        mock_args.config_dir = None
        mock_args.db_path = None
        mock_args.debug = False
        
        mock_parser.parse_args.return_value = mock_args
        mock_parser_func.return_value = mock_parser
        
        mock_app = Mock()
        mock_app.run_cli.return_value = 0
        mock_app_class.return_value = mock_app
        
        with patch('sys.argv', ['main.py', '--cli', 'list']):
            result = main()
        
        assert result == 0
        mock_app.run_cli.assert_called_once_with(mock_args)
    
    @patch('main.N8nManagementApp')
    @patch('main.create_argument_parser')
    @patch('os.environ', {})
    def test_main_debug_mode(self, mock_parser_func, mock_app_class):
        """Test main function with debug mode"""
        # Setup mocks
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.cli = False
        mock_args.config_dir = None
        mock_args.db_path = None
        mock_args.debug = True
        
        mock_parser.parse_args.return_value = mock_args
        mock_parser_func.return_value = mock_parser
        
        mock_app = Mock()
        mock_app.run_gui.return_value = 0
        mock_app_class.return_value = mock_app
        
        with patch('sys.argv', ['main.py', '--debug']):
            with patch.dict(os.environ, {}, clear=True):
                result = main()
        
        assert result == 0
        assert os.environ.get('N8N_MANAGER_LOG_LEVEL') == 'DEBUG'
    
    @patch('main.create_argument_parser')
    def test_main_cli_without_command(self, mock_parser_func):
        """Test main function CLI mode without command"""
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.cli = True
        mock_args.command = None
        
        mock_parser.parse_args.return_value = mock_args
        mock_parser.error.side_effect = SystemExit(2)
        mock_parser_func.return_value = mock_parser
        
        with patch('sys.argv', ['main.py', '--cli']):
            with pytest.raises(SystemExit):
                main()
        
        mock_parser.error.assert_called_once_with("CLI mode requires a command")


# Integration test for full application flow
class TestApplicationIntegration:
    """Integration tests for full application workflow"""
    
    @patch('main.setup_logger')
    @patch('main.setup_config')
    @patch('main.setup_database')
    @patch('main.get_docker_manager')
    @patch('main.MainWindow')
    def test_full_gui_startup_flow(self, mock_main_window, mock_docker_manager,
                                  mock_setup_database, mock_setup_config, mock_setup_logger):
        """Test complete GUI startup flow"""
        # Setup all mocks for successful initialization
        mock_logger = Mock()
        mock_config = Mock()
        mock_database = Mock()
        mock_docker = Mock()
        mock_window = Mock()
        
        mock_setup_logger.return_value = mock_logger
        mock_setup_config.return_value = mock_config
        mock_setup_database.return_value = mock_database
        mock_docker_manager.return_value = mock_docker
        mock_main_window.return_value = mock_window
        
        mock_docker.is_docker_available.return_value = True
        mock_docker.get_docker_info.return_value = {'server_version': '20.10.0'}
        
        # Create and run app
        app = N8nManagementApp()
        
        with patch('signal.signal'):
            result = app.run_gui()
        
        # Verify complete flow
        assert result == 0
        mock_setup_logger.assert_called_once()
        mock_setup_config.assert_called_once()
        mock_setup_database.assert_called_once()
        mock_docker_manager.assert_called_once()
        mock_main_window.assert_called_once()
        mock_window.run.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__])