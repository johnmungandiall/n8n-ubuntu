"""
Validation utilities for n8n Management App
Provides validation functions for various input types
"""

import re
import socket
from typing import Any, Dict, List, Optional, Tuple, Union
from .constants import VALIDATION_PATTERNS, RESOURCE_LIMITS


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class Validators:
    """Collection of validation functions"""
    
    @staticmethod
    def validate_instance_name(name: str) -> Tuple[bool, str]:
        """
        Validate instance name
        Returns: (is_valid, error_message)
        """
        if not name:
            return False, "Instance name cannot be empty"
        
        if len(name) < 3:
            return False, "Instance name must be at least 3 characters long"
        
        if len(name) > 50:
            return False, "Instance name cannot exceed 50 characters"
        
        if not re.match(VALIDATION_PATTERNS['INSTANCE_NAME'], name):
            return False, "Instance name can only contain letters, numbers, hyphens, and underscores"
        
        # Check for reserved names
        reserved_names = ['con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 
                         'com5', 'com6', 'com7', 'com8', 'com9', 'lpt1', 'lpt2', 
                         'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9']
        
        if name.lower() in reserved_names:
            return False, f"'{name}' is a reserved name and cannot be used"
        
        return True, ""
    
    @staticmethod
    def validate_port(port: Union[str, int]) -> Tuple[bool, str]:
        """
        Validate port number
        Returns: (is_valid, error_message)
        """
        try:
            port_num = int(port)
        except (ValueError, TypeError):
            return False, "Port must be a valid integer"
        
        if port_num < RESOURCE_LIMITS['MIN_PORT']:
            return False, f"Port must be at least {RESOURCE_LIMITS['MIN_PORT']}"
        
        if port_num > RESOURCE_LIMITS['MAX_PORT']:
            return False, f"Port cannot exceed {RESOURCE_LIMITS['MAX_PORT']}"
        
        # Check for well-known ports that should be avoided
        well_known_ports = [22, 23, 25, 53, 80, 110, 143, 443, 993, 995]
        if port_num in well_known_ports:
            return False, f"Port {port_num} is a well-known port and should be avoided"
        
        return True, ""
    
    @staticmethod
    def validate_memory_limit(memory: str) -> Tuple[bool, str]:
        """
        Validate memory limit string (e.g., '512m', '1g')
        Returns: (is_valid, error_message)
        """
        if not memory:
            return False, "Memory limit cannot be empty"
        
        if not re.match(VALIDATION_PATTERNS['MEMORY_SIZE'], memory):
            return False, "Invalid memory format. Use format like '512m', '1g', '2048mb'"
        
        # Convert to bytes for validation
        try:
            bytes_value = Validators._parse_memory_to_bytes(memory)
            min_bytes = Validators._parse_memory_to_bytes(RESOURCE_LIMITS['MIN_MEMORY'])
            max_bytes = Validators._parse_memory_to_bytes(RESOURCE_LIMITS['MAX_MEMORY'])
            
            if bytes_value < min_bytes:
                return False, f"Memory limit must be at least {RESOURCE_LIMITS['MIN_MEMORY']}"
            
            if bytes_value > max_bytes:
                return False, f"Memory limit cannot exceed {RESOURCE_LIMITS['MAX_MEMORY']}"
            
        except ValueError as e:
            return False, f"Invalid memory format: {e}"
        
        return True, ""
    
    @staticmethod
    def validate_cpu_limit(cpu: Union[str, float]) -> Tuple[bool, str]:
        """
        Validate CPU limit
        Returns: (is_valid, error_message)
        """
        try:
            cpu_value = float(cpu)
        except (ValueError, TypeError):
            return False, "CPU limit must be a valid number"
        
        min_cpu = float(RESOURCE_LIMITS['MIN_CPU'])
        max_cpu = float(RESOURCE_LIMITS['MAX_CPU'])
        
        if cpu_value < min_cpu:
            return False, f"CPU limit must be at least {min_cpu}"
        
        if cpu_value > max_cpu:
            return False, f"CPU limit cannot exceed {max_cpu}"
        
        return True, ""
    
    @staticmethod
    def validate_docker_image(image: str) -> Tuple[bool, str]:
        """
        Validate Docker image name
        Returns: (is_valid, error_message)
        """
        if not image:
            return False, "Docker image cannot be empty"
        
        # Basic Docker image name validation
        # Format: [registry/]namespace/repository[:tag]
        image_pattern = r'^(?:[a-zA-Z0-9._-]+(?:\.[a-zA-Z0-9._-]+)*(?::[0-9]+)?/)?[a-zA-Z0-9._-]+(?:/[a-zA-Z0-9._-]+)*(?::[a-zA-Z0-9._-]+)?$'
        
        if not re.match(image_pattern, image):
            return False, "Invalid Docker image format"
        
        # Check image name length
        if len(image) > 255:
            return False, "Docker image name cannot exceed 255 characters"
        
        return True, ""
    
    @staticmethod
    def validate_environment_variables(env_vars: Dict[str, str]) -> Tuple[bool, str]:
        """
        Validate environment variables
        Returns: (is_valid, error_message)
        """
        if not isinstance(env_vars, dict):
            return False, "Environment variables must be a dictionary"
        
        for key, value in env_vars.items():
            # Validate key
            if not key:
                return False, "Environment variable name cannot be empty"
            
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                return False, f"Invalid environment variable name: {key}"
            
            # Validate value
            if not isinstance(value, str):
                return False, f"Environment variable value must be a string: {key}"
            
            # Check for potentially dangerous variables
            dangerous_vars = ['PATH', 'LD_LIBRARY_PATH', 'HOME', 'USER']
            if key in dangerous_vars:
                return False, f"Environment variable '{key}' should not be modified"
        
        return True, ""
    
    @staticmethod
    def validate_volume_mapping(volumes: Dict[str, str]) -> Tuple[bool, str]:
        """
        Validate volume mappings
        Returns: (is_valid, error_message)
        """
        if not isinstance(volumes, dict):
            return False, "Volume mappings must be a dictionary"
        
        for source, target in volumes.items():
            # Validate source
            if not source:
                return False, "Volume source cannot be empty"
            
            # Validate target
            if not target:
                return False, "Volume target cannot be empty"
            
            # Check for absolute paths in target
            if not target.startswith('/'):
                return False, f"Volume target must be an absolute path: {target}"
            
            # Check for dangerous mount points
            dangerous_mounts = ['/', '/etc', '/usr', '/bin', '/sbin', '/boot']
            if target in dangerous_mounts:
                return False, f"Volume target '{target}' is not allowed for security reasons"
        
        return True, ""
    
    @staticmethod
    def validate_network_configuration(network_config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate network configuration
        Returns: (is_valid, error_message)
        """
        if not isinstance(network_config, dict):
            return False, "Network configuration must be a dictionary"
        
        # Validate network mode if specified
        if 'mode' in network_config:
            valid_modes = ['bridge', 'host', 'none', 'container']
            if network_config['mode'] not in valid_modes:
                return False, f"Invalid network mode. Must be one of: {', '.join(valid_modes)}"
        
        # Validate port mappings if specified
        if 'ports' in network_config:
            ports = network_config['ports']
            if not isinstance(ports, dict):
                return False, "Port mappings must be a dictionary"
            
            for container_port, host_port in ports.items():
                # Validate container port
                is_valid, error = Validators.validate_port(container_port.split('/')[0])
                if not is_valid:
                    return False, f"Invalid container port: {error}"
                
                # Validate host port
                is_valid, error = Validators.validate_port(host_port)
                if not is_valid:
                    return False, f"Invalid host port: {error}"
        
        return True, ""
    
    @staticmethod
    def validate_ip_address(ip: str) -> Tuple[bool, str]:
        """
        Validate IP address
        Returns: (is_valid, error_message)
        """
        if not ip:
            return False, "IP address cannot be empty"
        
        try:
            socket.inet_aton(ip)
            return True, ""
        except socket.error:
            return False, "Invalid IP address format"
    
    @staticmethod
    def validate_configuration_data(config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate complete configuration data
        Returns: (is_valid, error_message)
        """
        if not isinstance(config, dict):
            return False, "Configuration must be a dictionary"
        
        # Validate required fields
        required_fields = ['name', 'image']
        for field in required_fields:
            if field not in config:
                return False, f"Required field missing: {field}"
        
        # Validate instance name
        is_valid, error = Validators.validate_instance_name(config['name'])
        if not is_valid:
            return False, f"Invalid instance name: {error}"
        
        # Validate Docker image
        is_valid, error = Validators.validate_docker_image(config['image'])
        if not is_valid:
            return False, f"Invalid Docker image: {error}"
        
        # Validate port if specified
        if 'port' in config:
            is_valid, error = Validators.validate_port(config['port'])
            if not is_valid:
                return False, f"Invalid port: {error}"
        
        # Validate resource limits if specified
        if 'resource_limits' in config:
            limits = config['resource_limits']
            if 'memory' in limits:
                is_valid, error = Validators.validate_memory_limit(limits['memory'])
                if not is_valid:
                    return False, f"Invalid memory limit: {error}"
            
            if 'cpu' in limits:
                is_valid, error = Validators.validate_cpu_limit(limits['cpu'])
                if not is_valid:
                    return False, f"Invalid CPU limit: {error}"
        
        # Validate environment variables if specified
        if 'environment_vars' in config:
            is_valid, error = Validators.validate_environment_variables(config['environment_vars'])
            if not is_valid:
                return False, f"Invalid environment variables: {error}"
        
        # Validate volumes if specified
        if 'volumes' in config:
            is_valid, error = Validators.validate_volume_mapping(config['volumes'])
            if not is_valid:
                return False, f"Invalid volume mapping: {error}"
        
        # Validate network configuration if specified
        if 'networks' in config:
            is_valid, error = Validators.validate_network_configuration(config['networks'])
            if not is_valid:
                return False, f"Invalid network configuration: {error}"
        
        return True, ""
    
    @staticmethod
    def _parse_memory_to_bytes(memory_str: str) -> int:
        """
        Parse memory string to bytes
        Supports formats: 512m, 1g, 2048mb, etc.
        """
        memory_str = memory_str.lower().strip()
        
        # Extract number and unit
        match = re.match(r'^(\d+(?:\.\d+)?)\s*([kmgt]?b?)$', memory_str)
        if not match:
            raise ValueError(f"Invalid memory format: {memory_str}")
        
        number = float(match.group(1))
        unit = match.group(2) or 'b'
        
        # Convert to bytes
        multipliers = {
            'b': 1,
            'k': 1024,
            'kb': 1024,
            'm': 1024 ** 2,
            'mb': 1024 ** 2,
            'g': 1024 ** 3,
            'gb': 1024 ** 3,
            't': 1024 ** 4,
            'tb': 1024 ** 4
        }
        
        if unit not in multipliers:
            raise ValueError(f"Unknown memory unit: {unit}")
        
        return int(number * multipliers[unit])
    
    @staticmethod
    def sanitize_input(input_str: str, max_length: int = 255) -> str:
        """
        Sanitize input string by removing potentially dangerous characters
        """
        if not isinstance(input_str, str):
            return str(input_str)
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in input_str if ord(char) >= 32 or char in '\t\n\r')
        
        # Trim to max length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized.strip()
    
    @staticmethod
    def is_safe_path(path: str) -> bool:
        """
        Check if a path is safe (no directory traversal)
        """
        if not path:
            return False
        
        # Check for directory traversal patterns
        dangerous_patterns = ['../', '..\\', '/./', '\\.\\']
        for pattern in dangerous_patterns:
            if pattern in path:
                return False
        
        # Check for absolute paths to system directories
        dangerous_prefixes = ['/etc/', '/usr/', '/bin/', '/sbin/', '/boot/', '/sys/', '/proc/']
        for prefix in dangerous_prefixes:
            if path.startswith(prefix):
                return False
        
        return True


# Convenience functions for common validations
def validate_instance_name(name: str) -> None:
    """Validate instance name and raise ValidationError if invalid"""
    is_valid, error = Validators.validate_instance_name(name)
    if not is_valid:
        raise ValidationError(error)

def validate_port(port: Union[str, int]) -> None:
    """Validate port and raise ValidationError if invalid"""
    is_valid, error = Validators.validate_port(port)
    if not is_valid:
        raise ValidationError(error)

def validate_memory_limit(memory: str) -> None:
    """Validate memory limit and raise ValidationError if invalid"""
    is_valid, error = Validators.validate_memory_limit(memory)
    if not is_valid:
        raise ValidationError(error)

def validate_cpu_limit(cpu: Union[str, float]) -> None:
    """Validate CPU limit and raise ValidationError if invalid"""
    is_valid, error = Validators.validate_cpu_limit(cpu)
    if not is_valid:
        raise ValidationError(error)

def validate_docker_image(image: str) -> None:
    """Validate Docker image and raise ValidationError if invalid"""
    is_valid, error = Validators.validate_docker_image(image)
    if not is_valid:
        raise ValidationError(error)

def validate_configuration(config: Dict[str, Any]) -> None:
    """Validate configuration and raise ValidationError if invalid"""
    is_valid, error = Validators.validate_configuration_data(config)
    if not is_valid:
        raise ValidationError(error)