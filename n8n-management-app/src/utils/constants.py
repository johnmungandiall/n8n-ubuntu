"""
Constants for n8n Management App
Defines application-wide constants and default values
"""

# Application Information
APP_NAME = "n8n Management App"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "A comprehensive desktop application for managing multiple n8n instances"

# Docker Configuration
DEFAULT_N8N_IMAGE = "n8nio/n8n:latest"
DEFAULT_PORT_RANGE = (5678, 5700)
DEFAULT_MEMORY_LIMIT = "512m"
DEFAULT_CPU_LIMIT = "0.5"
DEFAULT_NETWORK_NAME = "n8n_network"

# Database Configuration
DEFAULT_DB_PATH = "data/n8n_manager.db"
DEFAULT_BACKUP_INTERVAL = 3600  # seconds

# Logging Configuration
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_PATH = "data/logs/app.log"
DEFAULT_LOG_MAX_SIZE = "10MB"
DEFAULT_LOG_BACKUP_COUNT = 5

# UI Configuration
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800
DEFAULT_THEME = "light"
DEFAULT_REFRESH_INTERVAL = 5  # seconds

# Instance Configuration
DEFAULT_NAME_PREFIX = "n8n-instance"
DEFAULT_AUTO_START = True
DEFAULT_HEALTH_CHECK_INTERVAL = 30  # seconds

# Backup Configuration
DEFAULT_BACKUP_ENABLED = True
DEFAULT_BACKUP_SCHEDULE = "daily"
DEFAULT_BACKUP_RETENTION_DAYS = 30
DEFAULT_BACKUP_COMPRESSION = True

# Container Status Constants
CONTAINER_STATUS = {
    'CREATED': 'created',
    'RUNNING': 'running',
    'PAUSED': 'paused',
    'RESTARTING': 'restarting',
    'REMOVING': 'removing',
    'EXITED': 'exited',
    'DEAD': 'dead'
}

# Health Status Constants
HEALTH_STATUS = {
    'HEALTHY': 'healthy',
    'UNHEALTHY': 'unhealthy',
    'STARTING': 'starting',
    'STOPPED': 'stopped',
    'UNKNOWN': 'unknown',
    'ERROR': 'error'
}

# Log Levels
LOG_LEVELS = {
    'DEBUG': 'DEBUG',
    'INFO': 'INFO',
    'WARNING': 'WARNING',
    'ERROR': 'ERROR',
    'CRITICAL': 'CRITICAL'
}

# Error Messages
ERROR_MESSAGES = {
    'DOCKER_NOT_AVAILABLE': "Docker daemon is not available. Please ensure Docker is running.",
    'INSTANCE_NOT_FOUND': "Instance not found.",
    'INSTANCE_NAME_EXISTS': "An instance with this name already exists.",
    'INVALID_INSTANCE_NAME': "Invalid instance name. Use only letters, numbers, hyphens, and underscores.",
    'NO_AVAILABLE_PORTS': "No available ports in the configured range.",
    'CONTAINER_NOT_FOUND': "Container not found.",
    'DATABASE_ERROR': "Database operation failed.",
    'CONFIG_ERROR': "Configuration error.",
    'NETWORK_ERROR': "Network operation failed.",
    'PERMISSION_ERROR': "Permission denied.",
    'RESOURCE_LIMIT_EXCEEDED': "Resource limit exceeded."
}

# Success Messages
SUCCESS_MESSAGES = {
    'INSTANCE_CREATED': "Instance created successfully.",
    'INSTANCE_STARTED': "Instance started successfully.",
    'INSTANCE_STOPPED': "Instance stopped successfully.",
    'INSTANCE_RESTARTED': "Instance restarted successfully.",
    'INSTANCE_DELETED': "Instance deleted successfully.",
    'INSTANCE_CLONED': "Instance cloned successfully.",
    'CONFIG_SAVED': "Configuration saved successfully.",
    'BACKUP_CREATED': "Backup created successfully.",
    'CLEANUP_COMPLETED': "Cleanup completed successfully."
}

# File Extensions
FILE_EXTENSIONS = {
    'CONFIG': ['.yaml', '.yml', '.json'],
    'LOG': ['.log', '.txt'],
    'BACKUP': ['.tar.gz', '.zip'],
    'EXPORT': ['.yaml', '.json']
}

# Validation Patterns
VALIDATION_PATTERNS = {
    'INSTANCE_NAME': r'^[a-zA-Z0-9_-]{3,50}$',
    'PORT': r'^([1-9][0-9]{0,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$',
    'IPV4': r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
    'MEMORY_SIZE': r'^[0-9]+[kmgKMG]?[bB]?$',
    'CPU_LIMIT': r'^[0-9]*\.?[0-9]+$'
}

# Default Environment Variables for n8n
DEFAULT_N8N_ENV_VARS = {
    'N8N_HOST': '0.0.0.0',
    'N8N_PORT': '5678',
    'N8N_PROTOCOL': 'http',
    'NODE_ENV': 'production',
    'WEBHOOK_URL': 'http://localhost:5678/',
    'GENERIC_TIMEZONE': 'UTC'
}

# Resource Limits
RESOURCE_LIMITS = {
    'MIN_MEMORY': '128m',
    'MAX_MEMORY': '8g',
    'MIN_CPU': '0.1',
    'MAX_CPU': '4.0',
    'MIN_PORT': 1024,
    'MAX_PORT': 65535
}

# Timeouts (in seconds)
TIMEOUTS = {
    'DOCKER_CONNECT': 10,
    'CONTAINER_START': 30,
    'CONTAINER_STOP': 10,
    'HEALTH_CHECK': 5,
    'HTTP_REQUEST': 10,
    'DATABASE_QUERY': 30
}

# Retry Configuration
RETRY_CONFIG = {
    'MAX_RETRIES': 3,
    'RETRY_DELAY': 1,  # seconds
    'BACKOFF_FACTOR': 2
}

# GUI Constants
GUI_CONSTANTS = {
    'MIN_WINDOW_WIDTH': 800,
    'MIN_WINDOW_HEIGHT': 600,
    'TREE_COLUMN_WIDTHS': {
        'name': 200,
        'status': 100,
        'port': 80,
        'health': 100
    },
    'BUTTON_PADDING': 5,
    'FRAME_PADDING': 10,
    'STATUS_UPDATE_INTERVAL': 1000  # milliseconds
}

# Color Schemes
COLOR_SCHEMES = {
    'light': {
        'background': '#ffffff',
        'foreground': '#000000',
        'success': '#28a745',
        'warning': '#ffc107',
        'error': '#dc3545',
        'info': '#17a2b8'
    },
    'dark': {
        'background': '#2b2b2b',
        'foreground': '#ffffff',
        'success': '#28a745',
        'warning': '#ffc107',
        'error': '#dc3545',
        'info': '#17a2b8'
    }
}

# Status Icons (Unicode)
STATUS_ICONS = {
    'running': '🟢',
    'stopped': '🔴',
    'paused': '🟡',
    'created': '🔵',
    'failed': '❌',
    'unknown': '❓',
    'healthy': '✅',
    'unhealthy': '❌',
    'starting': '🔄'
}

# Menu Accelerators
MENU_ACCELERATORS = {
    'new_instance': 'Ctrl+N',
    'refresh': 'F5',
    'quit': 'Ctrl+Q',
    'save': 'Ctrl+S',
    'open': 'Ctrl+O'
}

# Configuration Sections
CONFIG_SECTIONS = [
    'app',
    'docker',
    'database',
    'logging',
    'ui',
    'instances',
    'backup'
]

# Export/Import Formats
EXPORT_FORMATS = {
    'yaml': 'YAML Configuration',
    'json': 'JSON Configuration'
}

# Backup Types
BACKUP_TYPES = {
    'full': 'Full Backup',
    'config': 'Configuration Only',
    'data': 'Data Only'
}

# Health Check Endpoints
HEALTH_CHECK_ENDPOINTS = {
    'n8n': '/healthz',
    'webhook': '/webhook-test'
}

# Default Volumes
DEFAULT_VOLUMES = {
    'n8n_data': '/home/node/.n8n',
    'n8n_files': '/files'
}

# Network Modes
NETWORK_MODES = [
    'bridge',
    'host',
    'none',
    'container'
]

# Restart Policies
RESTART_POLICIES = [
    'no',
    'always',
    'unless-stopped',
    'on-failure'
]