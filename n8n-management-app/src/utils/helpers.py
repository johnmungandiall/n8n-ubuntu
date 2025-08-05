"""
Helper utilities for n8n Management App
Provides common utility functions used throughout the application
"""

import os
import socket
import hashlib
import json
import yaml
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple
import subprocess
import platform
import psutil

from .constants import TIMEOUTS, RETRY_CONFIG


class PortChecker:
    """Utility for checking port availability"""
    
    @staticmethod
    def is_port_available(port: int, host: str = 'localhost') -> bool:
        """Check if a port is available on the given host"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(TIMEOUTS['DOCKER_CONNECT'])
                result = sock.connect_ex((host, port))
                return result != 0
        except Exception:
            return False
    
    @staticmethod
    def find_available_port(start_port: int = 5678, end_port: int = 5700, 
                           host: str = 'localhost') -> Optional[int]:
        """Find the first available port in the given range"""
        for port in range(start_port, end_port + 1):
            if PortChecker.is_port_available(port, host):
                return port
        return None
    
    @staticmethod
    def get_port_info(port: int, host: str = 'localhost') -> Dict[str, Any]:
        """Get information about what's using a port"""
        info = {
            'port': port,
            'host': host,
            'available': PortChecker.is_port_available(port, host),
            'process': None,
            'pid': None
        }
        
        try:
            # Find process using the port
            for conn in psutil.net_connections():
                if conn.laddr.port == port:
                    try:
                        process = psutil.Process(conn.pid)
                        info['process'] = process.name()
                        info['pid'] = conn.pid
                        break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
        except Exception:
            pass
        
        return info


class FileSystemHelper:
    """File system utility functions"""
    
    @staticmethod
    def ensure_directory(path: Union[str, Path]) -> Path:
        """Ensure directory exists, create if it doesn't"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @staticmethod
    def safe_delete(path: Union[str, Path]) -> bool:
        """Safely delete a file or directory"""
        try:
            path = Path(path)
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_file_size(path: Union[str, Path]) -> int:
        """Get file size in bytes"""
        try:
            return Path(path).stat().st_size
        except Exception:
            return 0
    
    @staticmethod
    def get_directory_size(path: Union[str, Path]) -> int:
        """Get total size of directory in bytes"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        pass
            return total_size
        except Exception:
            return 0
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size in human-readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    @staticmethod
    def create_backup_filename(base_name: str, extension: str = '.tar.gz') -> str:
        """Create a backup filename with timestamp"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{base_name}_backup_{timestamp}{extension}"
    
    @staticmethod
    def get_temp_directory() -> Path:
        """Get a temporary directory for the application"""
        temp_dir = Path(tempfile.gettempdir()) / 'n8n_manager'
        FileSystemHelper.ensure_directory(temp_dir)
        return temp_dir
    
    @staticmethod
    def calculate_checksum(file_path: Union[str, Path], algorithm: str = 'sha256') -> str:
        """Calculate checksum of a file"""
        hash_func = hashlib.new(algorithm)
        
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        except Exception:
            return ""


class ConfigHelper:
    """Configuration file helper functions"""
    
    @staticmethod
    def load_yaml(file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load YAML configuration file"""
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}
    
    @staticmethod
    def save_yaml(data: Dict[str, Any], file_path: Union[str, Path]) -> bool:
        """Save data to YAML file"""
        try:
            FileSystemHelper.ensure_directory(Path(file_path).parent)
            with open(file_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, indent=2)
            return True
        except Exception:
            return False
    
    @staticmethod
    def load_json(file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load JSON configuration file"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    
    @staticmethod
    def save_json(data: Dict[str, Any], file_path: Union[str, Path]) -> bool:
        """Save data to JSON file"""
        try:
            FileSystemHelper.ensure_directory(Path(file_path).parent)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False
    
    @staticmethod
    def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge two configuration dictionaries"""
        result = base_config.copy()
        
        for key, value in override_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigHelper.merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result


class DateTimeHelper:
    """Date and time utility functions"""
    
    @staticmethod
    def format_datetime(dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
        """Format datetime object to string"""
        try:
            return dt.strftime(format_str)
        except Exception:
            return str(dt)
    
    @staticmethod
    def parse_datetime(dt_str: str, format_str: str = '%Y-%m-%d %H:%M:%S') -> Optional[datetime]:
        """Parse datetime string to datetime object"""
        try:
            return datetime.strptime(dt_str, format_str)
        except Exception:
            return None
    
    @staticmethod
    def get_relative_time(dt: datetime) -> str:
        """Get relative time string (e.g., '2 hours ago')"""
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    
    @staticmethod
    def get_uptime_string(start_time: datetime) -> str:
        """Get uptime string from start time"""
        now = datetime.now()
        uptime = now - start_time
        
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")
        
        return " ".join(parts)


class StringHelper:
    """String manipulation utilities"""
    
    @staticmethod
    def truncate(text: str, max_length: int, suffix: str = '...') -> str:
        """Truncate text to maximum length with suffix"""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename by removing invalid characters"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename.strip()
    
    @staticmethod
    def generate_random_string(length: int = 8) -> str:
        """Generate random string for IDs, passwords, etc."""
        import random
        import string
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
    @staticmethod
    def camel_to_snake(name: str) -> str:
        """Convert camelCase to snake_case"""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    @staticmethod
    def snake_to_camel(name: str) -> str:
        """Convert snake_case to camelCase"""
        components = name.split('_')
        return components[0] + ''.join(word.capitalize() for word in components[1:])


class SystemHelper:
    """System information and utilities"""
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Get system information"""
        return {
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'disk_usage': dict(psutil.disk_usage('/')),
        }
    
    @staticmethod
    def get_resource_usage() -> Dict[str, Any]:
        """Get current resource usage"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory': dict(psutil.virtual_memory()._asdict()),
            'disk': dict(psutil.disk_usage('/')._asdict()),
            'network': dict(psutil.net_io_counters()._asdict()) if psutil.net_io_counters() else {}
        }
    
    @staticmethod
    def is_docker_available() -> bool:
        """Check if Docker is available on the system"""
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    @staticmethod
    def get_docker_version() -> Optional[str]:
        """Get Docker version string"""
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None


class RetryHelper:
    """Retry mechanism for operations"""
    
    @staticmethod
    def retry_operation(operation, max_retries: int = None, delay: float = None, 
                       backoff_factor: float = None, exceptions: Tuple = (Exception,)):
        """
        Retry an operation with exponential backoff
        
        Args:
            operation: Function to retry
            max_retries: Maximum number of retries
            delay: Initial delay between retries
            backoff_factor: Multiplier for delay after each retry
            exceptions: Tuple of exceptions to catch and retry on
        """
        import time
        
        max_retries = max_retries or RETRY_CONFIG['MAX_RETRIES']
        delay = delay or RETRY_CONFIG['RETRY_DELAY']
        backoff_factor = backoff_factor or RETRY_CONFIG['BACKOFF_FACTOR']
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return operation()
            except exceptions as e:
                last_exception = e
                if attempt < max_retries:
                    time.sleep(delay * (backoff_factor ** attempt))
                else:
                    raise last_exception
        
        raise last_exception


class ValidationHelper:
    """Additional validation utilities"""
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if URL is valid"""
        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(url) is not None
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Check if email address is valid"""
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        return email_pattern.match(email) is not None


class DataConverter:
    """Data conversion utilities"""
    
    @staticmethod
    def bytes_to_human_readable(bytes_value: int) -> str:
        """Convert bytes to human readable format"""
        return FileSystemHelper.format_file_size(bytes_value)
    
    @staticmethod
    def seconds_to_human_readable(seconds: int) -> str:
        """Convert seconds to human readable format"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds}s"
        else:
            hours = seconds // 3600
            remaining_minutes = (seconds % 3600) // 60
            return f"{hours}h {remaining_minutes}m"
    
    @staticmethod
    def parse_memory_string(memory_str: str) -> int:
        """Parse memory string (e.g., '512m') to bytes"""
        import re
        
        memory_str = memory_str.lower().strip()
        match = re.match(r'^(\d+(?:\.\d+)?)\s*([kmgt]?b?)$', memory_str)
        
        if not match:
            raise ValueError(f"Invalid memory format: {memory_str}")
        
        number = float(match.group(1))
        unit = match.group(2) or 'b'
        
        multipliers = {
            'b': 1,
            'k': 1024, 'kb': 1024,
            'm': 1024 ** 2, 'mb': 1024 ** 2,
            'g': 1024 ** 3, 'gb': 1024 ** 3,
            't': 1024 ** 4, 'tb': 1024 ** 4
        }
        
        return int(number * multipliers.get(unit, 1))


# Convenience functions
def ensure_directory(path: Union[str, Path]) -> Path:
    """Convenience function for FileSystemHelper.ensure_directory"""
    return FileSystemHelper.ensure_directory(path)

def format_file_size(size_bytes: int) -> str:
    """Convenience function for FileSystemHelper.format_file_size"""
    return FileSystemHelper.format_file_size(size_bytes)

def is_port_available(port: int, host: str = 'localhost') -> bool:
    """Convenience function for PortChecker.is_port_available"""
    return PortChecker.is_port_available(port, host)

def find_available_port(start_port: int = 5678, end_port: int = 5700) -> Optional[int]:
    """Convenience function for PortChecker.find_available_port"""
    return PortChecker.find_available_port(start_port, end_port)

def get_relative_time(dt: datetime) -> str:
    """Convenience function for DateTimeHelper.get_relative_time"""
    return DateTimeHelper.get_relative_time(dt)

def truncate_string(text: str, max_length: int) -> str:
    """Convenience function for StringHelper.truncate"""
    return StringHelper.truncate(text, max_length)