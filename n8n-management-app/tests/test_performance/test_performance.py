"""
Performance tests for n8n Management App
Tests application performance, scalability, and resource usage
"""

import pytest
import time
import threading
import psutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import sys
import concurrent.futures
import statistics

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestApplicationPerformance:
    """Test application startup and operation performance"""
    
    def setup_method(self):
        """Setup performance test environment"""
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
    def test_application_startup_time(self, mock_db_connect, mock_docker):
        """Test application startup performance"""
        # Setup mocks for fast initialization
        mock_docker_client = Mock()
        mock_docker.return_value = mock_docker_client
        mock_docker_client.ping.return_value = True
        mock_docker_client.version.return_value = {'Version': '20.10.0'}
        mock_docker_client.info.return_value = {'ServerVersion': '20.10.0'}
        
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_db_conn.cursor.return_value = mock_cursor
        mock_db_connect.return_value = mock_db_conn
        
        from main import N8nManagementApp
        
        # Measure startup time
        start_time = time.time()
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        
        initialization_success = app.initialize()
        
        end_time = time.time()
        startup_time = end_time - start_time
        
        # Assertions
        assert initialization_success is True
        assert startup_time < 2.0, f"Startup took {startup_time:.2f}s, should be under 2s"
        
        app.shutdown()
    
    @patch('core.docker_manager.docker.from_env')
    @patch('core.database.sqlite3.connect')
    def test_instance_creation_performance(self, mock_db_connect, mock_docker):
        """Test instance creation performance"""
        # Setup mocks
        mock_docker_client = Mock()
        mock_docker.return_value = mock_docker_client
        mock_docker_client.ping.return_value = True
        mock_docker_client.version.return_value = {'Version': '20.10.0'}
        mock_docker_client.info.return_value = {'ServerVersion': '20.10.0'}
        
        # Mock container creation
        mock_container = Mock()
        mock_container.id = 'test_container'
        mock_container.name = 'n8n-instance-test'
        mock_container.status = 'running'
        mock_docker_client.containers.run.return_value = mock_container
        
        # Setup database mock
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_db_conn.cursor.return_value = mock_cursor
        mock_db_connect.return_value = mock_db_conn
        mock_cursor.fetchone.return_value = None  # Instance doesn't exist
        mock_cursor.lastrowid = 1
        
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        app.initialize()
        
        from core.n8n_manager import get_n8n_manager
        n8n_manager = get_n8n_manager()
        
        # Measure instance creation time
        creation_times = []
        
        for i in range(5):
            start_time = time.time()
            success, message, instance_id = n8n_manager.create_instance(f'perf-test-{i}')
            end_time = time.time()
            
            creation_time = end_time - start_time
            creation_times.append(creation_time)
            
            assert success is True
            assert creation_time < 5.0, f"Instance creation took {creation_time:.2f}s, should be under 5s"
        
        # Calculate statistics
        avg_time = statistics.mean(creation_times)
        max_time = max(creation_times)
        
        assert avg_time < 3.0, f"Average creation time {avg_time:.2f}s should be under 3s"
        assert max_time < 5.0, f"Max creation time {max_time:.2f}s should be under 5s"
        
        app.shutdown()
    
    @patch('core.docker_manager.docker.from_env')
    @patch('core.database.sqlite3.connect')
    def test_concurrent_instance_operations(self, mock_db_connect, mock_docker):
        """Test performance under concurrent operations"""
        # Setup mocks
        mock_docker_client = Mock()
        mock_docker.return_value = mock_docker_client
        mock_docker_client.ping.return_value = True
        mock_docker_client.version.return_value = {'Version': '20.10.0'}
        mock_docker_client.info.return_value = {'ServerVersion': '20.10.0'}
        
        # Mock containers
        containers = []
        for i in range(10):
            container = Mock()
            container.id = f'container_{i}'
            container.name = f'n8n-instance-concurrent-{i}'
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
        mock_cursor.fetchone.return_value = None
        mock_cursor.lastrowid = 1
        
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        app.initialize()
        
        from core.n8n_manager import get_n8n_manager
        n8n_manager = get_n8n_manager()
        
        # Test concurrent operations
        def create_instance(instance_id):
            return n8n_manager.create_instance(f'concurrent-{instance_id}')
        
        start_time = time.time()
        
        # Use ThreadPoolExecutor for concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_instance, i) for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify results
        successful_operations = sum(1 for success, _, _ in results if success)
        
        assert successful_operations >= 5, "At least 5 concurrent operations should succeed"
        assert total_time < 15.0, f"Concurrent operations took {total_time:.2f}s, should be under 15s"
        
        app.shutdown()
    
    @patch('core.docker_manager.docker.from_env')
    @patch('core.database.sqlite3.connect')
    def test_memory_usage_during_operations(self, mock_db_connect, mock_docker):
        """Test memory usage during various operations"""
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
        
        from main import N8nManagementApp
        
        # Measure initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        app.initialize()
        
        # Measure memory after initialization
        post_init_memory = process.memory_info().rss / 1024 / 1024  # MB
        init_memory_increase = post_init_memory - initial_memory
        
        # Perform operations and monitor memory
        from core.n8n_manager import get_n8n_manager
        n8n_manager = get_n8n_manager()
        
        # Mock instance data for listing
        mock_cursor.fetchall.return_value = [
            (i, f'test-{i}', f'container_{i}', 'n8nio/n8n:latest', 5678 + i, 'running', '2023-01-01 00:00:00')
            for i in range(100)
        ]
        
        # Perform memory-intensive operations
        for _ in range(10):
            instances = n8n_manager.list_instances()
            assert len(instances) == 100
        
        # Measure final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_memory_increase = final_memory - initial_memory
        
        # Memory usage assertions
        assert init_memory_increase < 50, f"Initialization used {init_memory_increase:.1f}MB, should be under 50MB"
        assert total_memory_increase < 100, f"Total memory increase {total_memory_increase:.1f}MB, should be under 100MB"
        
        app.shutdown()
    
    @patch('core.docker_manager.docker.from_env')
    @patch('core.database.sqlite3.connect')
    def test_database_query_performance(self, mock_db_connect, mock_docker):
        """Test database query performance with large datasets"""
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
        
        # Mock large dataset
        large_dataset = [
            (i, f'instance-{i}', f'container_{i}', 'n8nio/n8n:latest', 5678 + (i % 100), 'running', '2023-01-01 00:00:00')
            for i in range(1000)
        ]
        mock_cursor.fetchall.return_value = large_dataset
        
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        app.initialize()
        
        from core.n8n_manager import get_n8n_manager
        n8n_manager = get_n8n_manager()
        
        # Test query performance
        query_times = []
        
        for _ in range(10):
            start_time = time.time()
            instances = n8n_manager.list_instances()
            end_time = time.time()
            
            query_time = end_time - start_time
            query_times.append(query_time)
            
            assert len(instances) == 1000
            assert query_time < 1.0, f"Query took {query_time:.3f}s, should be under 1s"
        
        # Calculate statistics
        avg_query_time = statistics.mean(query_times)
        max_query_time = max(query_times)
        
        assert avg_query_time < 0.5, f"Average query time {avg_query_time:.3f}s should be under 0.5s"
        assert max_query_time < 1.0, f"Max query time {max_query_time:.3f}s should be under 1s"
        
        app.shutdown()


class TestScalabilityLimits:
    """Test application scalability and limits"""
    
    def setup_method(self):
        """Setup scalability test environment"""
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
    def test_maximum_concurrent_instances(self, mock_db_connect, mock_docker):
        """Test handling maximum number of concurrent instances"""
        # Setup mocks
        mock_docker_client = Mock()
        mock_docker.return_value = mock_docker_client
        mock_docker_client.ping.return_value = True
        mock_docker_client.version.return_value = {'Version': '20.10.0'}
        mock_docker_client.info.return_value = {'ServerVersion': '20.10.0'}
        
        # Mock many containers
        max_instances = 50
        containers = []
        for i in range(max_instances):
            container = Mock()
            container.id = f'container_{i}'
            container.name = f'n8n-instance-scale-{i}'
            container.status = 'running'
            containers.append(container)
        
        mock_docker_client.containers.list.return_value = containers
        
        # Mock database with many instances
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_db_conn.cursor.return_value = mock_cursor
        mock_db_connect.return_value = mock_db_conn
        
        large_instance_data = [
            (i, f'scale-test-{i}', f'container_{i}', 'n8nio/n8n:latest', 5678 + i, 'running', '2023-01-01 00:00:00')
            for i in range(max_instances)
        ]
        mock_cursor.fetchall.return_value = large_instance_data
        
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        app.initialize()
        
        from core.n8n_manager import get_n8n_manager
        n8n_manager = get_n8n_manager()
        
        # Test listing many instances
        start_time = time.time()
        instances = n8n_manager.list_instances()
        end_time = time.time()
        
        list_time = end_time - start_time
        
        assert len(instances) == max_instances
        assert list_time < 2.0, f"Listing {max_instances} instances took {list_time:.2f}s, should be under 2s"
        
        # Test individual instance operations
        mock_cursor.fetchone.return_value = large_instance_data[0]
        
        start_time = time.time()
        status = n8n_manager.get_instance_status(1)
        end_time = time.time()
        
        status_time = end_time - start_time
        
        assert 'error' not in status
        assert status_time < 1.0, f"Getting instance status took {status_time:.2f}s, should be under 1s"
        
        app.shutdown()
    
    @patch('core.docker_manager.docker.from_env')
    @patch('core.database.sqlite3.connect')
    def test_high_frequency_operations(self, mock_db_connect, mock_docker):
        """Test performance under high frequency operations"""
        # Setup mocks
        mock_docker_client = Mock()
        mock_docker.return_value = mock_docker_client
        mock_docker_client.ping.return_value = True
        mock_docker_client.version.return_value = {'Version': '20.10.0'}
        mock_docker_client.info.return_value = {'ServerVersion': '20.10.0'}
        
        mock_container = Mock()
        mock_container.id = 'test_container'
        mock_container.status = 'running'
        mock_docker_client.containers.get.return_value = mock_container
        
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_db_conn.cursor.return_value = mock_cursor
        mock_db_connect.return_value = mock_db_conn
        
        mock_cursor.fetchone.return_value = (
            1, 'test-instance', 'test_container', 'n8nio/n8n:latest', 
            5678, 'running', '2023-01-01 00:00:00'
        )
        
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        app.initialize()
        
        from core.n8n_manager import get_n8n_manager
        n8n_manager = get_n8n_manager()
        
        # Perform high frequency status checks
        operation_count = 100
        start_time = time.time()
        
        for _ in range(operation_count):
            status = n8n_manager.get_instance_status(1)
            assert 'error' not in status
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_operation = total_time / operation_count
        
        assert total_time < 10.0, f"100 operations took {total_time:.2f}s, should be under 10s"
        assert avg_time_per_operation < 0.1, f"Average operation time {avg_time_per_operation:.3f}s should be under 0.1s"
        
        app.shutdown()
    
    @patch('core.docker_manager.docker.from_env')
    @patch('core.database.sqlite3.connect')
    def test_resource_usage_under_load(self, mock_db_connect, mock_docker):
        """Test resource usage under sustained load"""
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
        
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        app.initialize()
        
        from core.n8n_manager import get_n8n_manager
        n8n_manager = get_n8n_manager()
        
        # Monitor resource usage during sustained operations
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Mock instance data
        mock_cursor.fetchall.return_value = [
            (i, f'load-test-{i}', f'container_{i}', 'n8nio/n8n:latest', 5678 + i, 'running', '2023-01-01 00:00:00')
            for i in range(20)
        ]
        
        # Sustained load test
        memory_samples = []
        cpu_samples = []
        
        for i in range(50):
            # Perform operations
            instances = n8n_manager.list_instances()
            assert len(instances) == 20
            
            # Sample resource usage every 10 iterations
            if i % 10 == 0:
                memory_usage = process.memory_info().rss / 1024 / 1024  # MB
                cpu_percent = process.cpu_percent()
                
                memory_samples.append(memory_usage)
                cpu_samples.append(cpu_percent)
            
            # Small delay to allow CPU measurement
            time.sleep(0.01)
        
        # Analyze resource usage
        max_memory = max(memory_samples)
        avg_memory = statistics.mean(memory_samples)
        memory_increase = max_memory - initial_memory
        
        max_cpu = max(cpu_samples)
        avg_cpu = statistics.mean(cpu_samples)
        
        # Resource usage assertions
        assert memory_increase < 50, f"Memory increased by {memory_increase:.1f}MB, should be under 50MB"
        assert avg_memory < initial_memory + 30, f"Average memory {avg_memory:.1f}MB too high"
        assert max_cpu < 80, f"Max CPU usage {max_cpu:.1f}% should be under 80%"
        assert avg_cpu < 50, f"Average CPU usage {avg_cpu:.1f}% should be under 50%"
        
        app.shutdown()


class TestPerformanceRegression:
    """Test for performance regressions"""
    
    def setup_method(self):
        """Setup regression test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.db_path = Path(self.temp_dir) / "test.db"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Performance baselines (in seconds)
        self.baselines = {
            'startup_time': 2.0,
            'instance_creation': 5.0,
            'instance_listing': 1.0,
            'status_check': 0.5,
            'config_load': 0.1
        }
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('core.docker_manager.docker.from_env')
    @patch('core.database.sqlite3.connect')
    def test_startup_performance_baseline(self, mock_db_connect, mock_docker):
        """Test startup performance against baseline"""
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
        
        from main import N8nManagementApp
        
        # Measure startup time multiple times
        startup_times = []
        
        for _ in range(3):
            start_time = time.time()
            
            app = N8nManagementApp(
                config_dir=str(self.config_dir),
                db_path=str(self.db_path)
            )
            success = app.initialize()
            
            end_time = time.time()
            startup_time = end_time - start_time
            startup_times.append(startup_time)
            
            assert success is True
            app.shutdown()
        
        avg_startup_time = statistics.mean(startup_times)
        max_startup_time = max(startup_times)
        
        # Check against baseline
        baseline = self.baselines['startup_time']
        assert avg_startup_time < baseline, f"Average startup time {avg_startup_time:.2f}s exceeds baseline {baseline}s"
        assert max_startup_time < baseline * 1.5, f"Max startup time {max_startup_time:.2f}s exceeds 150% of baseline"
    
    @patch('core.docker_manager.docker.from_env')
    @patch('core.database.sqlite3.connect')
    def test_operation_performance_baselines(self, mock_db_connect, mock_docker):
        """Test various operation performance against baselines"""
        # Setup mocks
        mock_docker_client = Mock()
        mock_docker.return_value = mock_docker_client
        mock_docker_client.ping.return_value = True
        mock_docker_client.version.return_value = {'Version': '20.10.0'}
        mock_docker_client.info.return_value = {'ServerVersion': '20.10.0'}
        
        mock_container = Mock()
        mock_container.id = 'test_container'
        mock_container.status = 'running'
        mock_docker_client.containers.run.return_value = mock_container
        mock_docker_client.containers.get.return_value = mock_container
        
        mock_db_conn = Mock()
        mock_cursor = Mock()
        mock_db_conn.cursor.return_value = mock_cursor
        mock_db_connect.return_value = mock_db_conn
        
        # Mock database responses
        mock_cursor.fetchone.side_effect = [
            None,  # Instance doesn't exist for creation
            (1, 'test-instance', 'test_container', 'n8nio/n8n:latest', 5678, 'running', '2023-01-01 00:00:00'),  # After creation
        ]
        mock_cursor.fetchall.return_value = [
            (1, 'test-instance', 'test_container', 'n8nio/n8n:latest', 5678, 'running', '2023-01-01 00:00:00')
        ]
        mock_cursor.lastrowid = 1
        
        from main import N8nManagementApp
        
        app = N8nManagementApp(
            config_dir=str(self.config_dir),
            db_path=str(self.db_path)
        )
        app.initialize()
        
        from core.n8n_manager import get_n8n_manager
        n8n_manager = get_n8n_manager()
        
        # Test instance creation performance
        start_time = time.time()
        success, message, instance_id = n8n_manager.create_instance('perf-test')
        creation_time = time.time() - start_time
        
        assert success is True
        baseline = self.baselines['instance_creation']
        assert creation_time < baseline, f"Instance creation {creation_time:.2f}s exceeds baseline {baseline}s"
        
        # Test instance listing performance
        start_time = time.time()
        instances = n8n_manager.list_instances()
        listing_time = time.time() - start_time
        
        assert len(instances) >= 1
        baseline = self.baselines['instance_listing']
        assert listing_time < baseline, f"Instance listing {listing_time:.2f}s exceeds baseline {baseline}s"
        
        # Test status check performance
        start_time = time.time()
        status = n8n_manager.get_instance_status(1)
        status_time = time.time() - start_time
        
        assert 'error' not in status
        baseline = self.baselines['status_check']
        assert status_time < baseline, f"Status check {status_time:.2f}s exceeds baseline {baseline}s"
        
        app.shutdown()
    
    def test_configuration_performance_baseline(self):
        """Test configuration loading performance against baseline"""
        from core.config_manager import ConfigManager
        
        # Test configuration loading performance
        config_times = []
        
        for _ in range(5):
            start_time = time.time()
            
            config_manager = ConfigManager(str(self.config_dir))
            config_manager.load_config()
            
            end_time = time.time()
            config_time = end_time - start_time
            config_times.append(config_time)
        
        avg_config_time = statistics.mean(config_times)
        max_config_time = max(config_times)
        
        baseline = self.baselines['config_load']
        assert avg_config_time < baseline, f"Average config load {avg_config_time:.3f}s exceeds baseline {baseline}s"
        assert max_config_time < baseline * 2, f"Max config load {max_config_time:.3f}s exceeds 200% of baseline"


if __name__ == '__main__':
    pytest.main([__file__])