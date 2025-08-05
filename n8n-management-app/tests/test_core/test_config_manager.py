"""
Unit tests for config_manager.py - Configuration management functionality
"""

import pytest
import os
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.config_manager import ConfigManager, setup_config, get_config


class TestConfigManager:
    """Test cases for ConfigManager class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "config.yaml"
        self.config_manager = ConfigManager(str(self.temp_dir))
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_default_config_dir(self):
        """Test ConfigManager initialization with default config directory"""
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path('/home/user')
            config_manager = ConfigManager()
            
            expected_path = Path('/home/user/.config/n8n-manager')
            assert config_manager.config_dir == expected_path
    
    def test_init_custom_config_dir(self):
        """Test ConfigManager initialization with custom config directory"""
        custom_dir = "/custom/config"
        config_manager = ConfigManager(custom_dir)
        
        assert config_manager.config_dir == Path(custom_dir)
    
    def test_default_config_values(self):
        """Test default configuration values"""
        expected_defaults = {
            'app': {
                'name': 'n8n Management App',
                'version': '1.0.0',
                'debug': False,
                'log_level': 'INFO'
            },
            'docker': {
                'default_image': 'n8nio/n8n:latest',
                'network_name': 'n8n-network',
                'volume_prefix': 'n8n-data',
                'container_prefix': 'n8n-instance',
                'default_port_range': [5678, 5700],
                'health_check_timeout': 30,
                'startup_timeout': 60
            },
            'database': {
                'type': 'sqlite',
                'path': 'data/instances.db',
                'backup_enabled': True,
                'backup_interval': 3600
            },
            'gui': {
                'theme': 'modern',
                'window_size': [1200, 800],
                'auto_refresh_interval': 5,
                'show_advanced_options': False
            },
            'logging': {
                'level': 'INFO',
                'file': 'logs/app.log',
                'max_size': 10485760,
                'backup_count': 5,
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        }
        
        assert self.config_manager.config == expected_defaults
    
    def test_load_config_file_not_exists(self):
        """Test loading config when file doesn't exist"""
        # Config file doesn't exist, should use defaults
        self.config_manager.load_config()
        
        # Should have default values
        assert self.config_manager.config['app']['name'] == 'n8n Management App'
        assert self.config_manager.config['docker']['default_image'] == 'n8nio/n8n:latest'
    
    def test_load_config_file_exists(self):
        """Test loading config from existing file"""
        # Create config file with custom values
        config_data = {
            'app': {
                'name': 'Custom n8n Manager',
                'debug': True
            },
            'docker': {
                'default_image': 'custom/n8n:latest'
            }
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        self.config_manager.load_config()
        
        # Should merge with defaults
        assert self.config_manager.config['app']['name'] == 'Custom n8n Manager'
        assert self.config_manager.config['app']['debug'] is True
        assert self.config_manager.config['app']['version'] == '1.0.0'  # Default preserved
        assert self.config_manager.config['docker']['default_image'] == 'custom/n8n:latest'
    
    def test_load_config_invalid_yaml(self):
        """Test loading config with invalid YAML"""
        # Create invalid YAML file
        with open(self.config_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        # Should handle gracefully and use defaults
        self.config_manager.load_config()
        
        assert self.config_manager.config['app']['name'] == 'n8n Management App'
    
    def test_save_config(self):
        """Test saving configuration to file"""
        # Modify config
        self.config_manager.config['app']['name'] = 'Modified App'
        self.config_manager.config['docker']['default_image'] = 'modified/n8n:latest'
        
        # Save config
        self.config_manager.save_config()
        
        # Verify file was created and contains correct data
        assert self.config_file.exists()
        
        with open(self.config_file, 'r') as f:
            saved_data = yaml.safe_load(f)
        
        assert saved_data['app']['name'] == 'Modified App'
        assert saved_data['docker']['default_image'] == 'modified/n8n:latest'
    
    def test_save_config_creates_directory(self):
        """Test saving config creates directory if it doesn't exist"""
        # Remove config directory
        import shutil
        shutil.rmtree(self.temp_dir)
        
        # Save config should create directory
        self.config_manager.save_config()
        
        assert Path(self.temp_dir).exists()
        assert self.config_file.exists()
    
    def test_get_value_existing_key(self):
        """Test getting existing configuration value"""
        value = self.config_manager.get('app.name')
        assert value == 'n8n Management App'
        
        value = self.config_manager.get('docker.default_image')
        assert value == 'n8nio/n8n:latest'
    
    def test_get_value_nested_key(self):
        """Test getting nested configuration value"""
        value = self.config_manager.get('gui.window_size')
        assert value == [1200, 800]
    
    def test_get_value_nonexistent_key(self):
        """Test getting non-existent configuration value"""
        value = self.config_manager.get('nonexistent.key')
        assert value is None
        
        # With default value
        value = self.config_manager.get('nonexistent.key', 'default')
        assert value == 'default'
    
    def test_set_value_existing_key(self):
        """Test setting existing configuration value"""
        self.config_manager.set('app.name', 'New App Name')
        
        assert self.config_manager.get('app.name') == 'New App Name'
    
    def test_set_value_new_key(self):
        """Test setting new configuration value"""
        self.config_manager.set('new.section.key', 'new value')
        
        assert self.config_manager.get('new.section.key') == 'new value'
    
    def test_set_value_nested_creation(self):
        """Test setting value creates nested structure"""
        self.config_manager.set('deep.nested.structure.value', 42)
        
        assert self.config_manager.config['deep']['nested']['structure']['value'] == 42
    
    def test_update_from_env_existing_vars(self):
        """Test updating config from environment variables"""
        env_vars = {
            'N8N_MANAGER_APP_NAME': 'Env App Name',
            'N8N_MANAGER_APP_DEBUG': 'true',
            'N8N_MANAGER_DOCKER_DEFAULT_IMAGE': 'env/n8n:latest',
            'N8N_MANAGER_GUI_WINDOW_SIZE': '[800, 600]'
        }
        
        with patch.dict(os.environ, env_vars):
            self.config_manager.update_from_env()
        
        assert self.config_manager.get('app.name') == 'Env App Name'
        assert self.config_manager.get('app.debug') is True
        assert self.config_manager.get('docker.default_image') == 'env/n8n:latest'
        assert self.config_manager.get('gui.window_size') == [800, 600]
    
    def test_update_from_env_type_conversion(self):
        """Test environment variable type conversion"""
        env_vars = {
            'N8N_MANAGER_APP_DEBUG': 'false',
            'N8N_MANAGER_DOCKER_DEFAULT_PORT_RANGE': '[8000, 8100]',
            'N8N_MANAGER_DATABASE_BACKUP_ENABLED': 'true',
            'N8N_MANAGER_GUI_AUTO_REFRESH_INTERVAL': '10'
        }
        
        with patch.dict(os.environ, env_vars):
            self.config_manager.update_from_env()
        
        assert self.config_manager.get('app.debug') is False
        assert self.config_manager.get('docker.default_port_range') == [8000, 8100]
        assert self.config_manager.get('database.backup_enabled') is True
        assert self.config_manager.get('gui.auto_refresh_interval') == 10
    
    def test_update_from_env_invalid_json(self):
        """Test handling invalid JSON in environment variables"""
        env_vars = {
            'N8N_MANAGER_GUI_WINDOW_SIZE': '[invalid json'
        }
        
        with patch.dict(os.environ, env_vars):
            self.config_manager.update_from_env()
        
        # Should keep original value
        assert self.config_manager.get('gui.window_size') == [1200, 800]
    
    def test_validate_config_valid(self):
        """Test configuration validation with valid config"""
        result = self.config_manager.validate_config()
        
        assert result is True
    
    def test_validate_config_missing_required(self):
        """Test configuration validation with missing required fields"""
        # Remove required field
        del self.config_manager.config['app']['name']
        
        result = self.config_manager.validate_config()
        
        assert result is False
    
    def test_validate_config_invalid_type(self):
        """Test configuration validation with invalid types"""
        # Set invalid type
        self.config_manager.config['gui']['window_size'] = "invalid"
        
        result = self.config_manager.validate_config()
        
        assert result is False
    
    def test_reset_to_defaults(self):
        """Test resetting configuration to defaults"""
        # Modify config
        self.config_manager.set('app.name', 'Modified')
        self.config_manager.set('custom.key', 'value')
        
        # Reset to defaults
        self.config_manager.reset_to_defaults()
        
        assert self.config_manager.get('app.name') == 'n8n Management App'
        assert self.config_manager.get('custom.key') is None
    
    def test_get_docker_config(self):
        """Test getting Docker-specific configuration"""
        docker_config = self.config_manager.get_docker_config()
        
        expected_keys = [
            'default_image', 'network_name', 'volume_prefix', 
            'container_prefix', 'default_port_range', 
            'health_check_timeout', 'startup_timeout'
        ]
        
        for key in expected_keys:
            assert key in docker_config
        
        assert docker_config['default_image'] == 'n8nio/n8n:latest'
    
    def test_get_database_config(self):
        """Test getting database-specific configuration"""
        db_config = self.config_manager.get_database_config()
        
        expected_keys = ['type', 'path', 'backup_enabled', 'backup_interval']
        
        for key in expected_keys:
            assert key in db_config
        
        assert db_config['type'] == 'sqlite'
    
    def test_get_gui_config(self):
        """Test getting GUI-specific configuration"""
        gui_config = self.config_manager.get_gui_config()
        
        expected_keys = [
            'theme', 'window_size', 'auto_refresh_interval', 
            'show_advanced_options'
        ]
        
        for key in expected_keys:
            assert key in gui_config
        
        assert gui_config['theme'] == 'modern'


class TestConfigManagerGlobalFunctions:
    """Test cases for global configuration functions"""
    
    def test_setup_config_default(self):
        """Test setup_config with default parameters"""
        with patch('core.config_manager.ConfigManager') as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config
            
            result = setup_config()
            
            mock_config_class.assert_called_once_with(None)
            mock_config.load_config.assert_called_once()
            assert result == mock_config
    
    def test_setup_config_custom_dir(self):
        """Test setup_config with custom directory"""
        with patch('core.config_manager.ConfigManager') as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config
            
            result = setup_config('/custom/config')
            
            mock_config_class.assert_called_once_with('/custom/config')
            mock_config.load_config.assert_called_once()
            assert result == mock_config
    
    def test_get_config_singleton(self):
        """Test get_config returns singleton instance"""
        with patch('core.config_manager._config_instance', None):
            with patch('core.config_manager.setup_config') as mock_setup:
                mock_config = Mock()
                mock_setup.return_value = mock_config
                
                # First call should setup
                result1 = get_config()
                mock_setup.assert_called_once()
                assert result1 == mock_config
                
                # Second call should return same instance
                result2 = get_config()
                assert result2 == mock_config
                assert mock_setup.call_count == 1  # Not called again


class TestConfigManagerEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_config_file_permission_error(self):
        """Test handling permission errors when saving config"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Make directory read-only
            os.chmod(temp_dir, 0o444)
            
            try:
                # Should handle permission error gracefully
                config_manager.save_config()
                # If no exception, test passes
            except PermissionError:
                # Expected on some systems
                pass
            finally:
                # Restore permissions for cleanup
                os.chmod(temp_dir, 0o755)
    
    def test_config_file_corrupted(self):
        """Test handling corrupted config file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.yaml"
            config_manager = ConfigManager(temp_dir)
            
            # Create corrupted file (binary data)
            with open(config_file, 'wb') as f:
                f.write(b'\x00\x01\x02\x03\x04\x05')
            
            # Should handle gracefully
            config_manager.load_config()
            
            # Should fall back to defaults
            assert config_manager.get('app.name') == 'n8n Management App'
    
    def test_deeply_nested_config_access(self):
        """Test accessing deeply nested configuration"""
        config_manager = ConfigManager()
        
        # Set deeply nested value
        config_manager.set('level1.level2.level3.level4.value', 'deep_value')
        
        # Should be able to retrieve
        assert config_manager.get('level1.level2.level3.level4.value') == 'deep_value'
        
        # Should be able to get intermediate levels
        level3 = config_manager.get('level1.level2.level3')
        assert level3['level4']['value'] == 'deep_value'
    
    def test_config_merge_complex_structures(self):
        """Test merging complex configuration structures"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.yaml"
            config_manager = ConfigManager(temp_dir)
            
            # Create complex config file
            complex_config = {
                'app': {
                    'name': 'Custom App',
                    'features': {
                        'feature1': {'enabled': True, 'config': {'param1': 'value1'}},
                        'feature2': {'enabled': False}
                    }
                },
                'docker': {
                    'default_image': 'custom/n8n:latest',
                    'networks': ['network1', 'network2']
                }
            }
            
            with open(config_file, 'w') as f:
                yaml.dump(complex_config, f)
            
            config_manager.load_config()
            
            # Should merge complex structures correctly
            assert config_manager.get('app.name') == 'Custom App'
            assert config_manager.get('app.features.feature1.enabled') is True
            assert config_manager.get('app.features.feature1.config.param1') == 'value1'
            assert config_manager.get('docker.networks') == ['network1', 'network2']
            
            # Default values should still be present
            assert config_manager.get('app.version') == '1.0.0'
            assert config_manager.get('docker.container_prefix') == 'n8n-instance'


if __name__ == '__main__':
    pytest.main([__file__])