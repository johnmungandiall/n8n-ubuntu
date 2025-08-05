"""
Configuration management for n8n Management App
Handles loading, saving, and validation of application configuration
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from .logger import get_logger


class ConfigManager:
    """Manages application configuration with validation and persistence"""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.logger = get_logger()
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / "config"
        self.default_config_path = self.config_dir / "default_config.yaml"
        self.user_config_path = self.config_dir / "user_config.yaml"
        
        self._config = {}
        self._load_configuration()
    
    def _load_configuration(self):
        """Load configuration from default and user config files"""
        try:
            # Load default configuration
            if self.default_config_path.exists():
                with open(self.default_config_path, 'r') as f:
                    self._config = yaml.safe_load(f) or {}
                self.logger.info(f"Loaded default configuration from {self.default_config_path}")
            else:
                self.logger.warning(f"Default config file not found: {self.default_config_path}")
                self._config = self._get_fallback_config()
            
            # Load user configuration and merge
            if self.user_config_path.exists():
                with open(self.user_config_path, 'r') as f:
                    user_config = yaml.safe_load(f) or {}
                self._merge_config(self._config, user_config)
                self.logger.info(f"Loaded user configuration from {self.user_config_path}")
            
            # Validate configuration
            self._validate_config()
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            self._config = self._get_fallback_config()
    
    def _get_fallback_config(self) -> Dict[str, Any]:
        """Get fallback configuration when files are not available"""
        return {
            'app': {
                'name': 'n8n Management App',
                'version': '1.0.0',
                'debug': False
            },
            'docker': {
                'default_image': 'n8nio/n8n:latest',
                'default_port_range': [5678, 5700],
                'default_memory_limit': '512m',
                'default_cpu_limit': '0.5',
                'network_name': 'n8n_network'
            },
            'database': {
                'type': 'sqlite',
                'path': 'data/n8n_manager.db',
                'backup_interval': 3600
            },
            'logging': {
                'level': 'INFO',
                'file_path': 'data/logs/app.log',
                'max_file_size': '10MB',
                'backup_count': 5,
                'console_output': True
            },
            'ui': {
                'theme': 'light',
                'window_width': 1200,
                'window_height': 800,
                'auto_refresh_interval': 5
            },
            'instances': {
                'default_name_prefix': 'n8n-instance',
                'auto_start_on_create': True,
                'health_check_interval': 30
            },
            'backup': {
                'enabled': True,
                'schedule': 'daily',
                'retention_days': 30,
                'compression': True
            }
        }
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]):
        """Recursively merge override config into base config"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def _validate_config(self):
        """Validate configuration values"""
        try:
            # Validate port range
            port_range = self.get('docker.default_port_range', [5678, 5700])
            if not isinstance(port_range, list) or len(port_range) != 2:
                raise ValueError("docker.default_port_range must be a list of two integers")
            if port_range[0] >= port_range[1]:
                raise ValueError("docker.default_port_range start must be less than end")
            
            # Validate window dimensions
            width = self.get('ui.window_width', 1200)
            height = self.get('ui.window_height', 800)
            if not isinstance(width, int) or width < 800:
                raise ValueError("ui.window_width must be an integer >= 800")
            if not isinstance(height, int) or height < 600:
                raise ValueError("ui.window_height must be an integer >= 600")
            
            # Validate refresh interval
            refresh = self.get('ui.auto_refresh_interval', 5)
            if not isinstance(refresh, (int, float)) or refresh < 1:
                raise ValueError("ui.auto_refresh_interval must be a number >= 1")
            
            self.logger.info("Configuration validation passed")
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'docker.default_image')"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value using dot notation"""
        keys = key.split('.')
        config = self._config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
        self.logger.debug(f"Set configuration: {key} = {value}")
    
    def save_user_config(self):
        """Save current configuration to user config file"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.user_config_path, 'w') as f:
                yaml.dump(self._config, f, default_flow_style=False, indent=2)
            self.logger.info(f"Saved user configuration to {self.user_config_path}")
        except Exception as e:
            self.logger.error(f"Error saving user configuration: {e}")
            raise
    
    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        try:
            if self.default_config_path.exists():
                with open(self.default_config_path, 'r') as f:
                    self._config = yaml.safe_load(f) or {}
            else:
                self._config = self._get_fallback_config()
            
            self._validate_config()
            self.logger.info("Configuration reset to defaults")
        except Exception as e:
            self.logger.error(f"Error resetting configuration: {e}")
            raise
    
    def get_all(self) -> Dict[str, Any]:
        """Get the entire configuration dictionary"""
        return self._config.copy()
    
    def update_from_env(self):
        """Update configuration from environment variables"""
        env_mappings = {
            'N8N_MANAGER_DEBUG': 'app.debug',
            'N8N_MANAGER_LOG_LEVEL': 'logging.level',
            'N8N_MANAGER_DB_PATH': 'database.path',
            'N8N_MANAGER_DOCKER_IMAGE': 'docker.default_image',
        }
        
        for env_var, config_key in env_mappings.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                # Convert string values to appropriate types
                if config_key.endswith('.debug'):
                    value = value.lower() in ('true', '1', 'yes', 'on')
                self.set(config_key, value)
                self.logger.debug(f"Updated config from env: {config_key} = {value}")


# Global configuration instance
_config_instance = None

def get_config() -> ConfigManager:
    """Get the global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance

def setup_config(config_dir: Optional[str] = None) -> ConfigManager:
    """Setup and return the global configuration instance"""
    global _config_instance
    _config_instance = ConfigManager(config_dir)
    return _config_instance