"""
Tests for configuration manager
"""

import pytest
import tempfile
import yaml
from pathlib import Path

from src.core.config_manager import ConfigManager


class TestConfigManager:
    """Test cases for ConfigManager"""
    
    def test_initialization_with_default_config(self):
        """Test initialization with default configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # Create default config
            default_config = {
                'app': {'name': 'Test App', 'version': '1.0.0'},
                'docker': {'default_image': 'test:latest'}
            }
            
            default_config_path = config_dir / 'default_config.yaml'
            with open(default_config_path, 'w') as f:
                yaml.dump(default_config, f)
            
            # Initialize config manager
            config_manager = ConfigManager(str(config_dir))
            
            assert config_manager.get('app.name') == 'Test App'
            assert config_manager.get('docker.default_image') == 'test:latest'
    
    def test_get_with_dot_notation(self):
        """Test getting values with dot notation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            default_config = {
                'app': {'name': 'Test App'},
                'nested': {'level1': {'level2': 'value'}}
            }
            
            default_config_path = config_dir / 'default_config.yaml'
            with open(default_config_path, 'w') as f:
                yaml.dump(default_config, f)
            
            config_manager = ConfigManager(str(config_dir))
            
            assert config_manager.get('app.name') == 'Test App'
            assert config_manager.get('nested.level1.level2') == 'value'
            assert config_manager.get('nonexistent.key', 'default') == 'default'
    
    def test_set_with_dot_notation(self):
        """Test setting values with dot notation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            default_config = {'app': {'name': 'Test App'}}
            
            default_config_path = config_dir / 'default_config.yaml'
            with open(default_config_path, 'w') as f:
                yaml.dump(default_config, f)
            
            config_manager = ConfigManager(str(config_dir))
            
            # Set new value
            config_manager.set('app.version', '2.0.0')
            assert config_manager.get('app.version') == '2.0.0'
            
            # Set nested value
            config_manager.set('new.nested.value', 'test')
            assert config_manager.get('new.nested.value') == 'test'
    
    def test_user_config_override(self):
        """Test user configuration overriding default"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # Default config
            default_config = {
                'app': {'name': 'Default App', 'version': '1.0.0'},
                'docker': {'default_image': 'default:latest'}
            }
            
            default_config_path = config_dir / 'default_config.yaml'
            with open(default_config_path, 'w') as f:
                yaml.dump(default_config, f)
            
            # User config (overrides)
            user_config = {
                'app': {'name': 'User App'},
                'docker': {'default_image': 'user:latest'}
            }
            
            user_config_path = config_dir / 'user_config.yaml'
            with open(user_config_path, 'w') as f:
                yaml.dump(user_config, f)
            
            config_manager = ConfigManager(str(config_dir))
            
            # User config should override default
            assert config_manager.get('app.name') == 'User App'
            assert config_manager.get('app.version') == '1.0.0'  # From default
            assert config_manager.get('docker.default_image') == 'user:latest'
    
    def test_fallback_config(self):
        """Test fallback configuration when files don't exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # No config files exist
            config_manager = ConfigManager(str(config_dir))
            
            # Should have fallback values
            assert config_manager.get('app.name') == 'n8n Management App'
            assert config_manager.get('docker.default_image') == 'n8nio/n8n:latest'
    
    def test_save_user_config(self):
        """Test saving user configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            config_manager = ConfigManager(str(config_dir))
            
            # Modify configuration
            config_manager.set('app.name', 'Modified App')
            config_manager.set('new.setting', 'test_value')
            
            # Save user config
            config_manager.save_user_config()
            
            # Verify file was created
            user_config_path = config_dir / 'user_config.yaml'
            assert user_config_path.exists()
            
            # Load and verify content
            with open(user_config_path, 'r') as f:
                saved_config = yaml.safe_load(f)
            
            assert saved_config['app']['name'] == 'Modified App'
            assert saved_config['new']['setting'] == 'test_value'
    
    def test_validation(self):
        """Test configuration validation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # Invalid config
            invalid_config = {
                'docker': {'default_port_range': [5700, 5678]},  # Invalid range
                'ui': {'window_width': 500}  # Too small
            }
            
            default_config_path = config_dir / 'default_config.yaml'
            with open(default_config_path, 'w') as f:
                yaml.dump(invalid_config, f)
            
            # Should raise validation error
            with pytest.raises(Exception):
                ConfigManager(str(config_dir))