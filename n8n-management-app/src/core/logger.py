"""
Logging system for n8n Management App
Provides structured logging with file rotation and multiple handlers
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional
import yaml


class AppLogger:
    """Centralized logging system for the application"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.logger = None
        self._setup_logger()
    
    def _load_config(self, config_path: Optional[str] = None) -> dict:
        """Load logging configuration from YAML file"""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "default_config.yaml"
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config.get('logging', {})
        except Exception:
            # Fallback configuration
            return {
                'level': 'INFO',
                'file_path': 'data/logs/app.log',
                'max_file_size': '10MB',
                'backup_count': 5,
                'console_output': True
            }
    
    def _setup_logger(self):
        """Set up the logger with file and console handlers"""
        self.logger = logging.getLogger('n8n_manager')
        self.logger.setLevel(getattr(logging, self.config.get('level', 'INFO')))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler with rotation
        log_file = Path(self.config.get('file_path', 'data/logs/app.log'))
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        max_bytes = self._parse_size(self.config.get('max_file_size', '10MB'))
        backup_count = self.config.get('backup_count', 5)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler
        if self.config.get('console_output', True):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '10MB' to bytes"""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance"""
        return self.logger
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message"""
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message"""
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message"""
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message"""
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Log critical message"""
        self.logger.critical(message, *args, **kwargs)


# Global logger instance
_logger_instance = None

def get_logger() -> AppLogger:
    """Get the global logger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = AppLogger()
    return _logger_instance

def setup_logger(config_path: Optional[str] = None) -> AppLogger:
    """Setup and return the global logger instance"""
    global _logger_instance
    _logger_instance = AppLogger(config_path)
    return _logger_instance