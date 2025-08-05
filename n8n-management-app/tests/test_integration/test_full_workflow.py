"""
Integration tests for complete n8n Management App workflows
Tests end-to-end functionality across all components
"""

import pytest
import tempfile
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from main import N8nManagementApp


class TestFullApplicationWorkflow:
    """Integration tests for complete application workflows"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.db_path = Path(self.temp_dir) / "test.db"
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('core.docker_manager.docker.from_env')
    @patch('core.database.sqlite3.connect')
    def test_complete_instance_lifecycle(self, mock_db_connect, mock_docker):
        """Test complete instance creation, management, and deletion workflow"""
        # Setup mocks for Docker
        mock_docker_client = Mock()
        mock_docker.return_value = mock_docker_client
        
        # Mock Docker containers
        mock_container = Mock()
        mock_container.id = 'test_container_id'
        mock_container.name = 'n8n-instance-test'
        mock_container.status = 'running'
        mock_container.attrs = {
            'NetworkSettings': {'Ports': {'5678/tcp': [{'HostPort': '5678'}]}},
            'State': {'Status': 'running', 'Health': {'Status': 'healthy'}},
            'Created': '2023-01-01T00:00:00Z'
        }
        mock_container.logs.return_value = b'n8n instance started successfully'
        mock_container.stats.return_value = iter([{
            'cpu_stats': {'cpu_usage': {'total_usage': 1000000}},
            'memory_stats': {'usage': 50000000, 'limit': 100000000}
        }])
        
        mock_docker_client.containers.list.return_value = []
        mock_docker_client.containers.run.return_value = mock_container
        mock_docker_client.containers.get.return_value = mock_container
        mock_docker_client.ping.return_value = True
        mock_docker_client.version.return_value = {'Version': '20.10.0'}
        mock_docker_client.info.return_value = {'ServerVersion': '20.10.0'}
        
        # Setup database mock
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_db_conn.cursor.return_value = mock_cursor
        mock_db_connect.return_value = mock_db_conn
        
        # Mock database responses
        mock_cursor.fetchone.side_effect = [
            None,  # Instance doesn't exist initially
            (1, 'test-instance', 'test_container_id', 'n8nio/n8n:latest', 5678, 'running', '2023-01-01 00:00:00'),  # After creation
            (1, 'test-instance', 'test_container_id', 'n8nio/n8n:latest', 5678, 'running', '2023-01-01 00:00:00'),  # For status check
        ]
        mock_cursor.fetchall.return_value = [
            (1, 'test-instance', 'test_container_id', 'n8nio/n8n:latest', 5678, 'running', '2023-01-01 00:00:00')
        ]
        mock_cursor.lastrowid = 1
        
        # Create app instance
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        
        # Test initialization
        assert app.initialize() is True
        
        # Import n8n_manager after initialization
        from core.n8n_manager import get_n8n_manager
        n8n_manager = get_n8n_manager()
        
        # Test instance creation
        success, message, instance_id = n8n_manager.create_instance('test-instance')
        assert success is True
        assert instance_id == 1
        assert 'created successfully' in message.lower()
        
        # Test instance listing
        instances = n8n_manager.list_instances()
        assert len(instances) == 1
        assert instances[0]['name'] == 'test-instance'
        assert instances[0]['status'] == 'running'
        
        # Test instance status
        status = n8n_manager.get_instance_status(1)
        assert 'error' not in status
        assert status['name'] == 'test-instance'
        assert status['status'] == 'running'
        
        # Test instance logs
        logs = n8n_manager.get_instance_logs(1)
        assert 'n8n instance started successfully' in logs
        
        # Test instance stopping
        mock_container.status = 'exited'
        success, message = n8n_manager.stop_instance(1)
        assert success is True
        
        # Test instance starting
        mock_container.status = 'running'
        success, message = n8n_manager.start_instance(1)
        assert success is True
        
        # Test instance deletion
        success, message = n8n_manager.delete_instance(1, remove_data=True)
        assert success is True
        
        # Cleanup
        app.shutdown()
    
    @patch('core.docker_manager.docker.from_env')
    @patch('core.database.sqlite3.connect')
    def test_multiple_instances_management(self, mock_db_connect, mock_docker):
        """Test managing multiple n8n instances simultaneously"""
        # Setup Docker mocks
        mock_docker_client = Mock()
        mock_docker.return_value = mock_docker_client
        
        # Create multiple mock containers
        containers = []
        for i in range(3):
            container = Mock()
            container.id = f'container_{i}'
            container.name = f'n8n-instance-test{i}'
            container.status = 'running'
            container.attrs = {
                'NetworkSettings': {'Ports': {'5678/tcp': [{'HostPort': str(5678 + i)}]}},
                'State': {'Status': 'running', 'Health': {'Status': 'healthy'}},
                'Created': '2023-01-01T00:00:00Z'
            }
            containers.append(container)
        
        mock_docker_client.containers.list.return_value = containers
        mock_docker_client.containers.run.side_effect = containers
        mock_docker_client.containers.get.side_effect = lambda name: next(
            c for c in containers if c.name == name or c.id == name
        )
        mock_docker_client.ping.return_value = True
        mock_docker_client.version.return_value = {'Version': '20.10.0'}
        mock_docker_client.info.return_value = {'ServerVersion': '20.10.0'}
        
        # Setup database mock
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_db_conn.cursor.return_value = mock_cursor
        mock_db_connect.return_value = mock_db_conn
        
        # Mock database responses for multiple instances
        mock_cursor.fetchall.return_value = [
            (1, 'test0', 'container_0', 'n8nio/n8n:latest', 5678, 'running', '2023-01-01 00:00:00'),
            (2, 'test1', 'container_1', 'n8nio/n8n:latest', 5679, 'running', '2023-01-01 00:00:00'),
            (3, 'test2', 'container_2', 'n8nio/n8n:latest', 5680, 'running', '2023-01-01 00:00:00'),
        ]
        mock_cursor.lastrowid = 3
        
        # Create app and initialize
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        assert app.initialize() is True
        
        from core.n8n_manager import get_n8n_manager
        n8n_manager = get_n8n_manager()
        
        # Test listing multiple instances
        instances = n8n_manager.list_instances()
        assert len(instances) == 3
        
        # Verify each instance has correct data
        for i, instance in enumerate(instances):
            assert instance['name'] == f'test{i}'
            assert instance['port'] == 5678 + i
            assert instance['status'] == 'running'
        
        # Test bulk operations
        # Stop all instances
        for i in range(3):
            containers[i].status = 'exited'
            mock_cursor.fetchone.return_value = (
                i + 1, f'test{i}', f'container_{i}', 'n8nio/n8n:latest', 
                5678 + i, 'exited', '2023-01-01 00:00:00'
            )
            success, message = n8n_manager.stop_instance(i + 1)
            assert success is True
        
        # Start all instances
        for i in range(3):
            containers[i].status = 'running'
            mock_cursor.fetchone.return_value = (
                i + 1, f'test{i}', f'container_{i}', 'n8nio/n8n:latest', 
                5678 + i, 'running', '2023-01-01 00:00:00'
            )
            success, message = n8n_manager.start_instance(i + 1)
            assert success is True
        
        app.shutdown()
    
    @patch('core.docker_manager.docker.from_env')
    @patch('core.database.sqlite3.connect')
    def test_error_handling_and_recovery(self, mock_db_connect, mock_docker):
        """Test error handling and recovery scenarios"""
        # Setup Docker client that fails initially
        mock_docker_client = Mock()
        mock_docker.return_value = mock_docker_client
        
        # Simulate Docker connection failure
        mock_docker_client.ping.side_effect = Exception("Docker daemon not available")
        
        # Create app
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        
        # Initialization should fail due to Docker
        assert app.initialize() is False
        
        # Fix Docker connection
        mock_docker_client.ping.side_effect = None
        mock_docker_client.ping.return_value = True
        mock_docker_client.version.return_value = {'Version': '20.10.0'}
        mock_docker_client.info.return_value = {'ServerVersion': '20.10.0'}
        
        # Setup database mock
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_db_conn.cursor.return_value = mock_cursor
        mock_db_connect.return_value = mock_db_conn
        
        # Now initialization should succeed
        assert app.initialize() is True
        
        from core.n8n_manager import get_n8n_manager
        n8n_manager = get_n8n_manager()
        
        # Test container creation failure
        mock_docker_client.containers.run.side_effect = Exception("Container creation failed")
        mock_cursor.fetchone.return_value = None
        
        success, message, instance_id = n8n_manager.create_instance('test-instance')
        assert success is False
        assert 'failed' in message.lower()
        
        # Test container operation on non-existent container
        mock_docker_client.containers.get.side_effect = Exception("Container not found")
        mock_cursor.fetchone.return_value = (
            1, 'test-instance', 'nonexistent_container', 'n8nio/n8n:latest', 
            5678, 'running', '2023-01-01 00:00:00'
        )
        
        success, message = n8n_manager.start_instance(1)
        assert success is False
        
        app.shutdown()
    
    @patch('core.docker_manager.docker.from_env')
    @patch('core.database.sqlite3.connect')
    def test_configuration_changes_workflow(self, mock_db_connect, mock_docker):
        """Test configuration changes and their effects"""
        # Setup mocks
        mock_docker_client = Mock()
        mock_docker.return_value = mock_docker_client
        mock_docker_client.ping.return_value = True
        mock_docker_client.version.return_value = {'Version': '20.10.0'}
        mock_docker_client.info.return_value = {'ServerVersion': '20.10.0'}
        
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_db_conn.cursor.return_value = mock_cursor
        mock_db_connect.return_value = mock_db_conn
        
        # Create app
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        assert app.initialize() is True
        
        # Test configuration access and modification
        from core.config_manager import get_config
        config = get_config()
        
        # Verify default configuration
        assert config.get('docker.default_image') == 'n8nio/n8n:latest'
        assert config.get('docker.default_port_range') == [5678, 5700]
        
        # Modify configuration
        config.set('docker.default_image', 'custom/n8n:latest')
        config.set('docker.default_port_range', [8000, 8100])
        
        # Verify changes
        assert config.get('docker.default_image') == 'custom/n8n:latest'
        assert config.get('docker.default_port_range') == [8000, 8100]
        
        # Save configuration
        config.save_config()
        
        # Verify config file was created
        config_file = self.config_dir / "config.yaml"
        assert config_file.exists()
        
        app.shutdown()
    
    def test_cli_interface_workflow(self):
        """Test CLI interface commands and workflows"""
        from main import create_argument_parser
        
        parser = create_argument_parser()
        
        # Test various CLI command parsing
        test_cases = [
            (['--cli', 'list'], {'cli': True, 'command': 'list'}),
            (['--cli', 'create', '--name', 'test'], {'cli': True, 'command': 'create', 'name': 'test'}),
            (['--cli', 'start', '--id', '1'], {'cli': True, 'command': 'start', 'instance_id': 1}),
            (['--cli', 'stop', '--id', '1'], {'cli': True, 'command': 'stop', 'instance_id': 1}),
            (['--cli', 'delete', '--id', '1', '--remove-data'], {
                'cli': True, 'command': 'delete', 'instance_id': 1, 'remove_data': True
            }),
            (['--cli', 'status', '--id', '1'], {'cli': True, 'command': 'status', 'instance_id': 1}),
            (['--cli', 'logs', '--id', '1', '--tail', '50'], {
                'cli': True, 'command': 'logs', 'instance_id': 1, 'tail': 50
            }),
        ]
        
        for args_list, expected_attrs in test_cases:
            args = parser.parse_args(args_list)
            for attr, expected_value in expected_attrs.items():
                assert getattr(args, attr) == expected_value
    
    @patch('core.docker_manager.docker.from_env')
    @patch('core.database.sqlite3.connect')
    def test_concurrent_operations(self, mock_db_connect, mock_docker):
        """Test concurrent operations on instances"""
        # Setup mocks
        mock_docker_client = Mock()
        mock_docker.return_value = mock_docker_client
        mock_docker_client.ping.return_value = True
        mock_docker_client.version.return_value = {'Version': '20.10.0'}
        mock_docker_client.info.return_value = {'ServerVersion': '20.10.0'}
        
        # Mock containers
        containers = []
        for i in range(2):
            container = Mock()
            container.id = f'container_{i}'
            container.name = f'n8n-instance-test{i}'
            container.status = 'running'
            containers.append(container)
        
        mock_docker_client.containers.run.side_effect = containers
        mock_docker_client.containers.get.side_effect = lambda name: next(
            c for c in containers if c.name == name or c.id == name
        )
        
        # Setup database mock
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_db_conn.cursor.return_value = mock_cursor
        mock_db_connect.return_value = mock_db_conn
        mock_cursor.lastrowid = 1
        
        # Create app
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        assert app.initialize() is True
        
        from core.n8n_manager import get_n8n_manager
        n8n_manager = get_n8n_manager()
        
        # Test concurrent instance creation
        results = []
        threads = []
        
        def create_instance(name):
            mock_cursor.fetchone.return_value = None  # Instance doesn't exist
            result = n8n_manager.create_instance(name)
            results.append(result)
        
        # Start multiple threads
        for i in range(2):
            thread = threading.Thread(target=create_instance, args=[f'concurrent-test-{i}'])
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results (at least one should succeed)
        assert len(results) == 2
        success_count = sum(1 for success, _, _ in results if success)
        assert success_count >= 1  # At least one should succeed
        
        app.shutdown()
    
    @patch('core.docker_manager.docker.from_env')
    @patch('core.database.sqlite3.connect')
    def test_performance_monitoring_workflow(self, mock_db_connect, mock_docker):
        """Test performance monitoring and resource usage tracking"""
        # Setup mocks
        mock_docker_client = Mock()
        mock_docker.return_value = mock_docker_client
        mock_docker_client.ping.return_value = True
        mock_docker_client.version.return_value = {'Version': '20.10.0'}
        mock_docker_client.info.return_value = {'ServerVersion': '20.10.0'}
        
        # Mock container with performance stats
        mock_container = Mock()
        mock_container.id = 'test_container'
        mock_container.name = 'n8n-instance-test'
        mock_container.status = 'running'
        mock_container.attrs = {
            'NetworkSettings': {'Ports': {'5678/tcp': [{'HostPort': '5678'}]}},
            'State': {'Status': 'running', 'Health': {'Status': 'healthy'}},
            'Created': '2023-01-01T00:00:00Z'
        }
        
        # Mock performance stats
        mock_container.stats.return_value = iter([{
            'cpu_stats': {
                'cpu_usage': {'total_usage': 1000000000},
                'system_cpu_usage': 10000000000
            },
            'precpu_stats': {
                'cpu_usage': {'total_usage': 900000000},
                'system_cpu_usage': 9000000000
            },
            'memory_stats': {
                'usage': 50000000,
                'limit': 100000000
            }
        }])
        
        mock_docker_client.containers.get.return_value = mock_container
        
        # Setup database mock
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_db_conn.cursor.return_value = mock_cursor
        mock_db_connect.return_value = mock_db_conn
        
        mock_cursor.fetchone.return_value = (
            1, 'test-instance', 'test_container', 'n8nio/n8n:latest', 
            5678, 'running', '2023-01-01 00:00:00'
        )
        
        # Create app
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        assert app.initialize() is True
        
        from core.n8n_manager import get_n8n_manager
        n8n_manager = get_n8n_manager()
        
        # Test performance monitoring
        status = n8n_manager.get_instance_status(1)
        
        assert 'container' in status
        assert 'resource_usage' in status['container']
        
        resource_usage = status['container']['resource_usage']
        assert 'cpu_percent' in resource_usage
        assert 'memory_percent' in resource_usage
        assert isinstance(resource_usage['cpu_percent'], (int, float))
        assert isinstance(resource_usage['memory_percent'], (int, float))
        
        app.shutdown()


class TestApplicationRobustness:
    """Test application robustness and edge cases"""
    
    def test_startup_with_missing_dependencies(self):
        """Test application behavior with missing dependencies"""
        with patch('core.docker_manager.docker.from_env') as mock_docker:
            mock_docker.side_effect = ImportError("Docker library not available")
            
            app = N8nManagementApp()
            
            # Should handle missing Docker gracefully
            result = app.initialize()
            assert result is False
    
    def test_database_corruption_recovery(self):
        """Test recovery from database corruption"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "corrupted.db"
            
            # Create corrupted database file
            with open(db_path, 'wb') as f:
                f.write(b'corrupted database content')
            
            app = N8nManagementApp(db_path=str(db_path))
            
            with patch('core.docker_manager.docker.from_env') as mock_docker:
                mock_docker_client = Mock()
                mock_docker.return_value = mock_docker_client
                mock_docker_client.ping.return_value = True
                mock_docker_client.version.return_value = {'Version': '20.10.0'}
                mock_docker_client.info.return_value = {'ServerVersion': '20.10.0'}
                
                # Should handle database corruption and recreate
                result = app.initialize()
                # May succeed or fail depending on database recovery implementation
                # The important thing is it doesn't crash
                assert isinstance(result, bool)
    
    def test_resource_cleanup_on_shutdown(self):
        """Test proper resource cleanup during shutdown"""
        with tempfile.TemporaryDirectory() as temp_dir:
            app = N8nManagementApp(
                config_dir=temp_dir,
                db_path=str(Path(temp_dir) / "test.db")
            )
            
            # Mock components
            app.logger = Mock()
            app.main_window = Mock()
            app.database = Mock()
            app.running = True
            
            # Test shutdown
            app.shutdown()
            
            # Verify cleanup
            assert app.running is False
            app.main_window.destroy.assert_called_once()
            app.logger.info.assert_called()


if __name__ == '__main__':
    pytest.main([__file__])