"""
Template Manager for n8n Management App
Handles instance templates for quick deployment and configuration reuse
"""

import json
import yaml
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

from .logger import get_logger
from .config_manager import get_config
from .database import get_database


class TemplateManager:
    """Manages instance templates"""
    
    def __init__(self):
        self.logger = get_logger()
        self.config = get_config()
        self.database = get_database()
        
        # Template storage directory
        self.templates_dir = Path(self.config.get('templates.storage_path', 'data/templates'))
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize built-in templates
        self._initialize_builtin_templates()
    
    def create_template(self, name: str, description: str, config: Dict[str, Any], 
                       tags: List[str] = None, version: str = "1.0.0") -> Tuple[bool, str, Optional[str]]:
        """
        Create a new template
        Returns: (success, message, template_id)
        """
        try:
            # Validate template name
            if not self._validate_template_name(name):
                return False, f"Invalid template name: {name}", None
            
            # Check if template already exists
            if self._template_exists(name):
                return False, f"Template '{name}' already exists", None
            
            # Create template ID
            template_id = self._generate_template_id(name)
            
            # Prepare template data
            template_data = {
                'id': template_id,
                'name': name,
                'description': description,
                'version': version,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'tags': tags or [],
                'config': config,
                'metadata': {
                    'author': self.config.get('user.name', 'Unknown'),
                    'type': 'user',
                    'usage_count': 0
                }
            }
            
            # Save template to file
            template_file = self.templates_dir / f"{template_id}.yaml"
            with open(template_file, 'w') as f:
                yaml.dump(template_data, f, default_flow_style=False, indent=2)
            
            # Store in database
            self.database.create_template(template_data)
            
            self.logger.info(f"Created template '{name}' with ID {template_id}")
            return True, f"Template '{name}' created successfully", template_id
            
        except Exception as e:
            error_msg = f"Error creating template '{name}': {e}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    def create_template_from_instance(self, instance_id: int, template_name: str, 
                                    description: str = "", tags: List[str] = None) -> Tuple[bool, str, Optional[str]]:
        """Create a template from an existing instance"""
        try:
            # Get instance configuration
            instance = self.database.get_instance(instance_id)
            if not instance:
                return False, f"Instance {instance_id} not found", None
            
            # Extract template configuration from instance
            template_config = {
                'image': instance['image'],
                'environment_vars': json.loads(instance['environment_vars']) if instance['environment_vars'] else {},
                'resource_limits': json.loads(instance['resource_limits']) if instance['resource_limits'] else {},
                'volumes': json.loads(instance['volumes']) if instance['volumes'] else {},
                'networks': json.loads(instance['networks']) if instance['networks'] else {},
                'config': json.loads(instance['config']) if instance['config'] else {}
            }
            
            # Add template-specific metadata
            if not description:
                description = f"Template created from instance '{instance['name']}'"
            
            if not tags:
                tags = ['from-instance', instance['status']]
            
            return self.create_template(template_name, description, template_config, tags)
            
        except Exception as e:
            error_msg = f"Error creating template from instance {instance_id}: {e}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template by ID"""
        try:
            template_file = self.templates_dir / f"{template_id}.yaml"
            
            if not template_file.exists():
                return None
            
            with open(template_file, 'r') as f:
                template_data = yaml.safe_load(f)
            
            return template_data
            
        except Exception as e:
            self.logger.error(f"Error getting template {template_id}: {e}")
            return None
    
    def get_template_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get template by name"""
        try:
            templates = self.list_templates()
            for template in templates:
                if template['name'] == name:
                    return self.get_template(template['id'])
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting template by name '{name}': {e}")
            return None
    
    def list_templates(self, tags: List[str] = None, template_type: str = None) -> List[Dict[str, Any]]:
        """List all templates with optional filtering"""
        try:
            templates = []
            
            # Get templates from database
            db_templates = self.database.get_all_templates()
            
            for template_record in db_templates:
                template_data = self.get_template(template_record['template_id'])
                if template_data:
                    # Apply filters
                    if tags:
                        template_tags = template_data.get('tags', [])
                        if not any(tag in template_tags for tag in tags):
                            continue
                    
                    if template_type:
                        if template_data.get('metadata', {}).get('type') != template_type:
                            continue
                    
                    # Add database metadata
                    template_data['usage_count'] = template_record.get('usage_count', 0)
                    template_data['last_used'] = template_record.get('last_used')
                    
                    templates.append(template_data)
            
            # Sort by name
            templates.sort(key=lambda x: x['name'])
            
            return templates
            
        except Exception as e:
            self.logger.error(f"Error listing templates: {e}")
            return []
    
    def update_template(self, template_id: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
        """Update an existing template"""
        try:
            template_data = self.get_template(template_id)
            if not template_data:
                return False, f"Template {template_id} not found"
            
            # Update fields
            for key, value in updates.items():
                if key in ['id', 'created_at']:
                    continue  # Don't allow updating these fields
                template_data[key] = value
            
            # Update timestamp
            template_data['updated_at'] = datetime.now().isoformat()
            
            # Save updated template
            template_file = self.templates_dir / f"{template_id}.yaml"
            with open(template_file, 'w') as f:
                yaml.dump(template_data, f, default_flow_style=False, indent=2)
            
            # Update database
            self.database.update_template(template_id, updates)
            
            self.logger.info(f"Updated template {template_id}")
            return True, f"Template updated successfully"
            
        except Exception as e:
            error_msg = f"Error updating template {template_id}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def delete_template(self, template_id: str) -> Tuple[bool, str]:
        """Delete a template"""
        try:
            template_data = self.get_template(template_id)
            if not template_data:
                return False, f"Template {template_id} not found"
            
            # Don't allow deleting built-in templates
            if template_data.get('metadata', {}).get('type') == 'builtin':
                return False, "Cannot delete built-in templates"
            
            # Remove template file
            template_file = self.templates_dir / f"{template_id}.yaml"
            if template_file.exists():
                template_file.unlink()
            
            # Remove from database
            self.database.delete_template(template_id)
            
            self.logger.info(f"Deleted template {template_id}")
            return True, f"Template '{template_data['name']}' deleted successfully"
            
        except Exception as e:
            error_msg = f"Error deleting template {template_id}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def export_template(self, template_id: str, file_path: str, format: str = 'yaml') -> Tuple[bool, str]:
        """Export template to file"""
        try:
            template_data = self.get_template(template_id)
            if not template_data:
                return False, f"Template {template_id} not found"
            
            # Prepare export data (remove internal metadata)
            export_data = {
                'name': template_data['name'],
                'description': template_data['description'],
                'version': template_data['version'],
                'tags': template_data['tags'],
                'config': template_data['config'],
                'exported_at': datetime.now().isoformat(),
                'exported_from': 'n8n-management-app'
            }
            
            # Write to file
            with open(file_path, 'w') as f:
                if format.lower() == 'json':
                    json.dump(export_data, f, indent=2)
                else:  # yaml
                    yaml.dump(export_data, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Exported template {template_id} to {file_path}")
            return True, f"Template exported to {file_path}"
            
        except Exception as e:
            error_msg = f"Error exporting template {template_id}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def import_template(self, file_path: str, overwrite: bool = False) -> Tuple[bool, str, Optional[str]]:
        """Import template from file"""
        try:
            if not os.path.exists(file_path):
                return False, f"File {file_path} not found", None
            
            # Load template data
            with open(file_path, 'r') as f:
                if file_path.endswith('.json'):
                    template_data = json.load(f)
                else:  # assume yaml
                    template_data = yaml.safe_load(f)
            
            # Validate required fields
            required_fields = ['name', 'config']
            for field in required_fields:
                if field not in template_data:
                    return False, f"Missing required field: {field}", None
            
            # Check if template exists
            if self._template_exists(template_data['name']) and not overwrite:
                return False, f"Template '{template_data['name']}' already exists", None
            
            # Create template
            return self.create_template(
                name=template_data['name'],
                description=template_data.get('description', ''),
                config=template_data['config'],
                tags=template_data.get('tags', ['imported']),
                version=template_data.get('version', '1.0.0')
            )
            
        except Exception as e:
            error_msg = f"Error importing template from {file_path}: {e}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    def apply_template(self, template_id: str, instance_name: str, 
                      overrides: Dict[str, Any] = None) -> Tuple[bool, str, Optional[int]]:
        """Apply template to create a new instance"""
        try:
            from .n8n_manager import get_n8n_manager
            
            template_data = self.get_template(template_id)
            if not template_data:
                return False, f"Template {template_id} not found", None
            
            # Prepare instance configuration from template
            instance_config = template_data['config'].copy()
            
            # Apply overrides
            if overrides:
                self._deep_update(instance_config, overrides)
            
            # Create instance using n8n manager
            n8n_manager = get_n8n_manager()
            success, message, instance_id = n8n_manager.create_instance(instance_name, instance_config)
            
            if success:
                # Update template usage statistics
                self._update_template_usage(template_id)
                
                self.logger.info(f"Applied template {template_id} to create instance '{instance_name}'")
            
            return success, message, instance_id
            
        except Exception as e:
            error_msg = f"Error applying template {template_id}: {e}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    def get_template_versions(self, template_name: str) -> List[Dict[str, Any]]:
        """Get all versions of a template"""
        try:
            templates = self.list_templates()
            versions = []
            
            for template in templates:
                if template['name'] == template_name:
                    versions.append({
                        'id': template['id'],
                        'version': template['version'],
                        'created_at': template['created_at'],
                        'updated_at': template['updated_at']
                    })
            
            # Sort by version
            versions.sort(key=lambda x: x['version'], reverse=True)
            
            return versions
            
        except Exception as e:
            self.logger.error(f"Error getting template versions for '{template_name}': {e}")
            return []
    
    def validate_template(self, template_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate template configuration"""
        errors = []
        
        try:
            # Check required fields
            required_fields = ['name', 'config']
            for field in required_fields:
                if field not in template_data:
                    errors.append(f"Missing required field: {field}")
            
            # Validate name
            if 'name' in template_data:
                if not self._validate_template_name(template_data['name']):
                    errors.append("Invalid template name")
            
            # Validate config structure
            if 'config' in template_data:
                config = template_data['config']
                
                # Check for required config fields
                if 'image' not in config:
                    errors.append("Template config must specify Docker image")
                
                # Validate environment variables
                if 'environment_vars' in config:
                    if not isinstance(config['environment_vars'], dict):
                        errors.append("Environment variables must be a dictionary")
                
                # Validate resource limits
                if 'resource_limits' in config:
                    limits = config['resource_limits']
                    if not isinstance(limits, dict):
                        errors.append("Resource limits must be a dictionary")
                    else:
                        # Validate memory format
                        if 'memory' in limits:
                            if not self._validate_memory_format(limits['memory']):
                                errors.append("Invalid memory format in resource limits")
                        
                        # Validate CPU format
                        if 'cpu' in limits:
                            if not self._validate_cpu_format(limits['cpu']):
                                errors.append("Invalid CPU format in resource limits")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            self.logger.error(f"Error validating template: {e}")
            return False, [f"Validation error: {e}"]
    
    # Private helper methods
    def _validate_template_name(self, name: str) -> bool:
        """Validate template name"""
        if not name or len(name) < 3 or len(name) > 50:
            return False
        
        # Check for valid characters
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            return False
        
        return True
    
    def _template_exists(self, name: str) -> bool:
        """Check if template with name exists"""
        templates = self.list_templates()
        return any(template['name'] == name for template in templates)
    
    def _generate_template_id(self, name: str) -> str:
        """Generate unique template ID"""
        import hashlib
        import time
        
        # Create ID from name and timestamp
        timestamp = str(int(time.time()))
        id_string = f"{name}_{timestamp}"
        
        return hashlib.md5(id_string.encode()).hexdigest()[:12]
    
    def _deep_update(self, base_dict: Dict, update_dict: Dict):
        """Deep update dictionary"""
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def _update_template_usage(self, template_id: str):
        """Update template usage statistics"""
        try:
            self.database.update_template_usage(template_id)
        except Exception as e:
            self.logger.warning(f"Failed to update template usage for {template_id}: {e}")
    
    def _validate_memory_format(self, memory: str) -> bool:
        """Validate memory format (e.g., '512m', '1g')"""
        import re
        return bool(re.match(r'^\d+[kmg]?$', str(memory).lower()))
    
    def _validate_cpu_format(self, cpu: str) -> bool:
        """Validate CPU format (e.g., '0.5', '1', '2.0')"""
        try:
            float(cpu)
            return True
        except (ValueError, TypeError):
            return False
    
    def _initialize_builtin_templates(self):
        """Initialize built-in templates"""
        try:
            builtin_templates = [
                {
                    'name': 'basic-n8n',
                    'description': 'Basic n8n instance with default configuration',
                    'version': '1.0.0',
                    'tags': ['basic', 'default'],
                    'config': {
                        'image': 'n8nio/n8n:latest',
                        'environment_vars': {
                            'N8N_HOST': '0.0.0.0',
                            'N8N_PORT': '5678',
                            'N8N_PROTOCOL': 'http',
                            'NODE_ENV': 'production'
                        },
                        'resource_limits': {
                            'memory': '512m',
                            'cpu': '0.5'
                        }
                    },
                    'metadata': {
                        'type': 'builtin',
                        'author': 'n8n Management App'
                    }
                },
                {
                    'name': 'development-n8n',
                    'description': 'n8n instance configured for development',
                    'version': '1.0.0',
                    'tags': ['development', 'debug'],
                    'config': {
                        'image': 'n8nio/n8n:latest',
                        'environment_vars': {
                            'N8N_HOST': '0.0.0.0',
                            'N8N_PORT': '5678',
                            'N8N_PROTOCOL': 'http',
                            'NODE_ENV': 'development',
                            'N8N_LOG_LEVEL': 'debug'
                        },
                        'resource_limits': {
                            'memory': '1g',
                            'cpu': '1.0'
                        }
                    },
                    'metadata': {
                        'type': 'builtin',
                        'author': 'n8n Management App'
                    }
                },
                {
                    'name': 'production-n8n',
                    'description': 'n8n instance optimized for production use',
                    'version': '1.0.0',
                    'tags': ['production', 'optimized'],
                    'config': {
                        'image': 'n8nio/n8n:latest',
                        'environment_vars': {
                            'N8N_HOST': '0.0.0.0',
                            'N8N_PORT': '5678',
                            'N8N_PROTOCOL': 'http',
                            'NODE_ENV': 'production',
                            'N8N_LOG_LEVEL': 'info',
                            'N8N_METRICS': 'true'
                        },
                        'resource_limits': {
                            'memory': '2g',
                            'cpu': '2.0'
                        }
                    },
                    'metadata': {
                        'type': 'builtin',
                        'author': 'n8n Management App'
                    }
                }
            ]
            
            # Create built-in templates if they don't exist
            for template_data in builtin_templates:
                if not self._template_exists(template_data['name']):
                    template_id = self._generate_template_id(template_data['name'])
                    template_data['id'] = template_id
                    template_data['created_at'] = datetime.now().isoformat()
                    template_data['updated_at'] = datetime.now().isoformat()
                    
                    # Save to file
                    template_file = self.templates_dir / f"{template_id}.yaml"
                    with open(template_file, 'w') as f:
                        yaml.dump(template_data, f, default_flow_style=False, indent=2)
                    
                    # Save to database
                    self.database.create_template(template_data)
                    
                    self.logger.info(f"Created built-in template: {template_data['name']}")
            
        except Exception as e:
            self.logger.error(f"Error initializing built-in templates: {e}")


# Global template manager instance
_template_manager_instance = None

def get_template_manager() -> TemplateManager:
    """Get the global template manager instance"""
    global _template_manager_instance
    if _template_manager_instance is None:
        _template_manager_instance = TemplateManager()
    return _template_manager_instance