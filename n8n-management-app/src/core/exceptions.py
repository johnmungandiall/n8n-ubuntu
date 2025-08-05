"""
Custom exceptions for n8n Management App
Provides standardized error handling across the application
"""

import time
from typing import Dict, Any, Optional
from functools import wraps
from .logger import get_logger


class N8nManagerException(Exception):
    """Base exception for n8n Manager"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.timestamp = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization"""
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp
        }


class DockerException(N8nManagerException):
    """Docker-related errors"""
    pass


class DatabaseException(N8nManagerException):
    """Database-related errors"""
    pass


class ValidationException(N8nManagerException):
    """Input validation errors"""
    pass


class ConfigurationException(N8nManagerException):
    """Configuration-related errors"""
    pass


class InstanceException(N8nManagerException):
    """Instance management errors"""
    pass


class NetworkException(N8nManagerException):
    """Network-related errors"""
    pass


class SecurityException(N8nManagerException):
    """Security-related errors"""
    pass


class ResourceException(N8nManagerException):
    """Resource management errors"""
    pass


def handle_errors(error_type=N8nManagerException, return_format='tuple'):
    """
    Decorator for standardized error handling
    
    Args:
        error_type: Type of exception to catch
        return_format: 'tuple' for (success, message) or 'dict' for detailed response
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            try:
                result = func(*args, **kwargs)
                
                # If function already returns tuple format, pass through
                if return_format == 'tuple' and isinstance(result, tuple):
                    return result
                elif return_format == 'dict' and isinstance(result, dict):
                    return result
                
                # Convert single values to expected format
                if return_format == 'tuple':
                    return True, result if isinstance(result, str) else "Operation completed successfully"
                else:
                    return {
                        'success': True,
                        'data': result,
                        'message': "Operation completed successfully"
                    }
                    
            except error_type as e:
                error_dict = e.to_dict()
                logger.error(f"Error in {func.__name__}: {e.message}", 
                           extra={'error_code': e.error_code, 'details': e.details})
                
                if return_format == 'tuple':
                    return False, e.message
                else:
                    return {
                        'success': False,
                        'error': error_dict,
                        'message': e.message
                    }
                    
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {e}")
                
                if return_format == 'tuple':
                    return False, f"Unexpected error: {e}"
                else:
                    return {
                        'success': False,
                        'error': {
                            'error_type': 'UnexpectedError',
                            'message': str(e)
                        },
                        'message': f"Unexpected error: {e}"
                    }
        return wrapper
    return decorator


def validate_input(validation_func, error_message: str = "Invalid input"):
    """
    Decorator for input validation
    
    Args:
        validation_func: Function that takes the same args/kwargs and returns bool
        error_message: Error message if validation fails
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not validation_func(*args, **kwargs):
                raise ValidationException(error_message, 'VALIDATION_FAILED')
            return func(*args, **kwargs)
        return wrapper
    return decorator


class ErrorContext:
    """Context manager for error handling with automatic logging"""
    
    def __init__(self, operation_name: str, logger=None):
        self.operation_name = operation_name
        self.logger = logger or get_logger()
        self.success = False
    
    def __enter__(self):
        self.logger.debug(f"Starting operation: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.success = True
            self.logger.debug(f"Operation completed successfully: {self.operation_name}")
        else:
            self.logger.error(f"Operation failed: {self.operation_name} - {exc_val}")
        return False  # Don't suppress exceptions
    
    def add_context(self, key: str, value: Any):
        """Add contextual information for debugging"""
        self.logger.debug(f"Context for {self.operation_name}: {key} = {value}")


def create_error_response(success: bool, message: str, data: Any = None, 
                         error_code: str = None, details: Dict = None) -> Dict[str, Any]:
    """Create standardized error response dictionary"""
    response = {
        'success': success,
        'message': message
    }
    
    if success:
        if data is not None:
            response['data'] = data
    else:
        response['error'] = {
            'code': error_code or 'UNKNOWN_ERROR',
            'details': details or {}
        }
    
    return response


# Example usage of @handle_errors decorator
@handle_errors(error_type=ValidationException)
def example_validation_function(data: str) -> str:
    """Example function demonstrating @handle_errors decorator usage"""
    if not data:
        raise ValidationException("Data cannot be empty", "EMPTY_DATA")
    return f"Processed: {data}"


@handle_errors(error_type=N8nManagerException, return_format='dict')
def example_operation_function(operation_id: str) -> Dict[str, Any]:
    """Example function demonstrating @handle_errors decorator with dict return"""
    if not operation_id:
        raise N8nManagerException("Operation ID is required", "MISSING_OPERATION_ID")
    
    return {
        'operation_id': operation_id,
        'status': 'completed',
        'timestamp': time.time()
    }