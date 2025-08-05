"""
Tests for validation utilities
"""

import pytest
from src.utils.validators import Validators, ValidationError, validate_instance_name


class TestValidators:
    """Test cases for validation utilities"""
    
    def test_validate_instance_name_valid(self):
        """Test valid instance names"""
        valid_names = [
            'test-instance',
            'my_instance_123',
            'n8n-prod',
            'dev_environment',
            'instance123'
        ]
        
        for name in valid_names:
            is_valid, error = Validators.validate_instance_name(name)
            assert is_valid, f"Name '{name}' should be valid but got error: {error}"
    
    def test_validate_instance_name_invalid(self):
        """Test invalid instance names"""
        invalid_names = [
            '',  # Empty
            'ab',  # Too short
            'a' * 51,  # Too long
            'test instance',  # Space
            'test@instance',  # Special character
            'test.instance',  # Dot
            'con',  # Reserved name
            'prn',  # Reserved name
        ]
        
        for name in invalid_names:
            is_valid, error = Validators.validate_instance_name(name)
            assert not is_valid, f"Name '{name}' should be invalid but was accepted"
            assert error, f"Error message should be provided for invalid name '{name}'"
    
    def test_validate_port_valid(self):
        """Test valid port numbers"""
        valid_ports = [1024, 5678, 8080, 65535, '3000', '8000']
        
        for port in valid_ports:
            is_valid, error = Validators.validate_port(port)
            assert is_valid, f"Port '{port}' should be valid but got error: {error}"
    
    def test_validate_port_invalid(self):
        """Test invalid port numbers"""
        invalid_ports = [
            0, 1023, 65536, 80, 443, 22,  # System ports or out of range
            'abc', '', None, -1, 99999
        ]
        
        for port in invalid_ports:
            is_valid, error = Validators.validate_port(port)
            assert not is_valid, f"Port '{port}' should be invalid but was accepted"
    
    def test_validate_memory_limit_valid(self):
        """Test valid memory limits"""
        valid_memory = ['512m', '1g', '2048mb', '1024MB', '4G', '128m']
        
        for memory in valid_memory:
            is_valid, error = Validators.validate_memory_limit(memory)
            assert is_valid, f"Memory '{memory}' should be valid but got error: {error}"
    
    def test_validate_memory_limit_invalid(self):
        """Test invalid memory limits"""
        invalid_memory = ['', '64m', '16g', 'abc', '512', '1x', '0m']
        
        for memory in invalid_memory:
            is_valid, error = Validators.validate_memory_limit(memory)
            assert not is_valid, f"Memory '{memory}' should be invalid but was accepted"
    
    def test_validate_cpu_limit_valid(self):
        """Test valid CPU limits"""
        valid_cpu = [0.5, 1.0, 2.5, '0.25', '1', '3.0']
        
        for cpu in valid_cpu:
            is_valid, error = Validators.validate_cpu_limit(cpu)
            assert is_valid, f"CPU '{cpu}' should be valid but got error: {error}"
    
    def test_validate_cpu_limit_invalid(self):
        """Test invalid CPU limits"""
        invalid_cpu = [0, 5.0, 'abc', '', None, -1]
        
        for cpu in invalid_cpu:
            is_valid, error = Validators.validate_cpu_limit(cpu)
            assert not is_valid, f"CPU '{cpu}' should be invalid but was accepted"
    
    def test_validate_docker_image_valid(self):
        """Test valid Docker image names"""
        valid_images = [
            'nginx',
            'nginx:latest',
            'nginx:1.20',
            'registry.example.com/nginx:latest',
            'localhost:5000/my-app:v1.0',
            'n8nio/n8n:latest'
        ]
        
        for image in valid_images:
            is_valid, error = Validators.validate_docker_image(image)
            assert is_valid, f"Image '{image}' should be valid but got error: {error}"
    
    def test_validate_docker_image_invalid(self):
        """Test invalid Docker image names"""
        invalid_images = [
            '',  # Empty
            'NGINX',  # Uppercase not allowed in some contexts
            'nginx:',  # Empty tag
            'nginx@',  # Invalid character
            'a' * 256,  # Too long
        ]
        
        for image in invalid_images:
            is_valid, error = Validators.validate_docker_image(image)
            assert not is_valid, f"Image '{image}' should be invalid but was accepted"
    
    def test_validate_environment_variables_valid(self):
        """Test valid environment variables"""
        valid_env = {
            'NODE_ENV': 'production',
            'PORT': '3000',
            'DEBUG': 'true',
            'MY_VAR_123': 'value'
        }
        
        is_valid, error = Validators.validate_environment_variables(valid_env)
        assert is_valid, f"Environment variables should be valid but got error: {error}"
    
    def test_validate_environment_variables_invalid(self):
        """Test invalid environment variables"""
        invalid_env_cases = [
            {'': 'value'},  # Empty key
            {'123VAR': 'value'},  # Key starts with number
            {'MY-VAR': 'value'},  # Hyphen in key
            {'PATH': '/usr/bin'},  # Dangerous variable
            {'HOME': '/home/user'},  # Dangerous variable
        ]
        
        for env_vars in invalid_env_cases:
            is_valid, error = Validators.validate_environment_variables(env_vars)
            assert not is_valid, f"Environment variables {env_vars} should be invalid but was accepted"
    
    def test_validate_configuration_data_valid(self):
        """Test valid configuration data"""
        valid_config = {
            'name': 'test-instance',
            'image': 'n8nio/n8n:latest',
            'port': 5678,
            'resource_limits': {
                'memory': '512m',
                'cpu': '0.5'
            },
            'environment_vars': {
                'NODE_ENV': 'production'
            }
        }
        
        is_valid, error = Validators.validate_configuration_data(valid_config)
        assert is_valid, f"Configuration should be valid but got error: {error}"
    
    def test_validate_configuration_data_invalid(self):
        """Test invalid configuration data"""
        # Missing required fields
        invalid_config = {
            'image': 'n8nio/n8n:latest'
            # Missing 'name'
        }
        
        is_valid, error = Validators.validate_configuration_data(invalid_config)
        assert not is_valid, "Configuration should be invalid due to missing name"
        assert 'name' in error
    
    def test_validation_error_exception(self):
        """Test ValidationError exception"""
        with pytest.raises(ValidationError):
            validate_instance_name('')  # Empty name should raise exception
    
    def test_sanitize_input(self):
        """Test input sanitization"""
        test_cases = [
            ('normal text', 'normal text'),
            ('text\x00with\x01null', 'textwithNull'),  # Remove null bytes
            ('a' * 300, 'a' * 255),  # Truncate to max length
            ('  spaced  ', 'spaced'),  # Trim spaces
        ]
        
        for input_text, expected in test_cases:
            result = Validators.sanitize_input(input_text)
            assert result == expected, f"Expected '{expected}' but got '{result}'"
    
    def test_is_safe_path(self):
        """Test path safety validation"""
        safe_paths = [
            '/home/user/data',
            'relative/path',
            './local/path',
            '/opt/app/data'
        ]
        
        unsafe_paths = [
            '../../../etc/passwd',
            '/etc/shadow',
            '..\\windows\\system32',
            '/usr/bin/dangerous',
            '/sys/kernel'
        ]
        
        for path in safe_paths:
            assert Validators.is_safe_path(path), f"Path '{path}' should be safe"
        
        for path in unsafe_paths:
            assert not Validators.is_safe_path(path), f"Path '{path}' should be unsafe"