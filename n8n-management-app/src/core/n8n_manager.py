"""
n8n Instance Manager
High-level management of n8n instances with database integration
"""

import json
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from .docker_manager import get_docker_manager
from .database import get_database
from .config_manager import get_config
from .logger import get_logger


class N8nManager:
    """High-level n8n instance management"""
    
    def __init__(self):
        self.logger = get_logger()
        self.config = get_config()
        self.docker = get_docker_manager()
        self.db = get_database()
    
    def create_instance(self, name: str, config: Dict[str, Any] = None) -> Tuple[bool, str, Optional[int]]:
        """
        Create a new n8n instance
        Returns: (success, message, instance_id)
        """
        try:
            # Validate instance name
            if not self._validate_instance_name(name):
                return False, f"Invalid instance name: {name}", None
            
            # Check if instance already exists
            existing = self.db.get_instance_by_name(name)
            if existing:
                return False, f"Instance '{name}' already exists", None
            
            # Prepare instance configuration
            instance_config = self._prepare_instance_config(name, config or {})
            
            # Find available port
            port = self.docker.find_available_port()
            if not port:
                return False, "No available ports in configured range", None
            
            instance_config['port'] = port
            
            # Create database record first
            instance_id = self.db.create_instance(instance_config)
            
            # Create Docker container
            success, message, container_id = self.docker.create_container(instance_config)
            
            if success:
                # Update database with container ID
                self.db.update_instance(instance_id, {
                    'container_id': container_id,
                    'status': 'created'
                })
                
                # Auto-start if configured
                if self.config.get('instances.auto_start_on_create', True):
                    start_success, start_message = self.start_instance(instance_id)
                    if not start_success:
                        self.logger.warning(f"Instance created but failed to start: {start_message}")
                
                self.logger.info(f"Successfully created n8n instance '{name}' (ID: {instance_id})")
                return True, f"Instance '{name}' created successfully", instance_id
            else:
                # Clean up database record if container creation failed
                self.db.delete_instance(instance_id)
                return False, f"Failed to create container: {message}", None
                
        except Exception as e:
            error_msg = f"Error creating instance '{name}': {e}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    def start_instance(self, instance_id: int) -> Tuple[bool, str]:
        """Start an n8n instance"""
        try:
            instance = self.db.get_instance(instance_id)
            if not instance:
                return False, f"Instance {instance_id} not found"
            
            if not instance['container_id']:
                return False, f"Instance '{instance['name']}' has no associated container"
            
            # Start container
            success, message = self.docker.start_container(instance['container_id'])
            
            if success:
                # Update database status
                self.db.update_instance(instance_id, {
                    'status': 'running',
                    'health_status': 'starting'
                })
                
                # Schedule health check
                self._schedule_health_check(instance_id)
                
                self.logger.info(f"Started instance '{instance['name']}'")
                return True, f"Instance '{instance['name']}' started successfully"
            else:
                self.db.update_instance(instance_id, {'status': 'failed'})
                return False, message
                
        except Exception as e:
            error_msg = f"Error starting instance {instance_id}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def stop_instance(self, instance_id: int) -> Tuple[bool, str]:
        """Stop an n8n instance"""
        try:
            instance = self.db.get_instance(instance_id)
            if not instance:
                return False, f"Instance {instance_id} not found"
            
            if not instance['container_id']:
                return False, f"Instance '{instance['name']}' has no associated container"
            
            # Stop container
            success, message = self.docker.stop_container(instance['container_id'])
            
            if success:
                # Update database status
                self.db.update_instance(instance_id, {
                    'status': 'stopped',
                    'health_status': 'stopped'
                })
                
                self.logger.info(f"Stopped instance '{instance['name']}'")
                return True, f"Instance '{instance['name']}' stopped successfully"
            else:
                return False, message
                
        except Exception as e:
            error_msg = f"Error stopping instance {instance_id}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def restart_instance(self, instance_id: int) -> Tuple[bool, str]:
        """Restart an n8n instance"""
        try:
            instance = self.db.get_instance(instance_id)
            if not instance:
                return False, f"Instance {instance_id} not found"
            
            if not instance['container_id']:
                return False, f"Instance '{instance['name']}' has no associated container"
            
            # Restart container
            success, message = self.docker.restart_container(instance['container_id'])
            
            if success:
                # Update database status
                self.db.update_instance(instance_id, {
                    'status': 'running',
                    'health_status': 'starting'
                })
                
                # Schedule health check
                self._schedule_health_check(instance_id)
                
                self.logger.info(f"Restarted instance '{instance['name']}'")
                return True, f"Instance '{instance['name']}' restarted successfully"
            else:
                self.db.update_instance(instance_id, {'status': 'failed'})
                return False, message
                
        except Exception as e:
            error_msg = f"Error restarting instance {instance_id}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def delete_instance(self, instance_id: int, remove_data: bool = False) -> Tuple[bool, str]:
        """Delete an n8n instance"""
        try:
            instance = self.db.get_instance(instance_id)
            if not instance:
                return False, f"Instance {instance_id} not found"
            
            instance_name = instance['name']
            
            # Stop and remove container if it exists
            if instance['container_id']:
                # Stop first
                self.docker.stop_container(instance['container_id'])
                
                # Remove container
                success, message = self.docker.remove_container(
                    instance['container_id'], 
                    force=True, 
                    remove_volumes=remove_data
                )
                
                if not success:
                    self.logger.warning(f"Failed to remove container: {message}")
            
            # Remove associated volume if requested
            if remove_data:
                volume_name = f"{instance_name}_data"
                self.docker.remove_volume(volume_name, force=True)
            
            # Remove database record
            self.db.delete_instance(instance_id)
            
            self.logger.info(f"Deleted instance '{instance_name}' (data removed: {remove_data})")
            return True, f"Instance '{instance_name}' deleted successfully"
            
        except Exception as e:
            error_msg = f"Error deleting instance {instance_id}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def get_instance_status(self, instance_id: int) -> Dict[str, Any]:
        """Get comprehensive instance status"""
        try:
            instance = self.db.get_instance(instance_id)
            if not instance:
                return {'error': f'Instance {instance_id} not found'}
            
            # Get basic instance info
            status_info = {
                'id': instance['id'],
                'name': instance['name'],
                'image': instance['image'],
                'port': instance['port'],
                'status': instance['status'],
                'health_status': instance['health_status'],
                'created_at': instance['created_at'],
                'updated_at': instance['updated_at'],
                'last_health_check': instance['last_health_check']
            }
            
            # Get Docker container status if available
            if instance['container_id']:
                container_status = self.docker.get_container_status(instance['container_id'])
                status_info['container'] = container_status
                
                # Update database status if container status changed
                if 'status' in container_status and container_status['status'] != instance['status']:
                    self.db.update_instance(instance_id, {'status': container_status['status']})
                    status_info['status'] = container_status['status']
            
            return status_info
            
        except Exception as e:
            self.logger.error(f"Error getting instance status {instance_id}: {e}")
            return {'error': str(e)}
    
    def list_instances(self) -> List[Dict[str, Any]]:
        """List all instances with current status"""
        try:
            instances = self.db.get_all_instances()
            
            # Enrich with current Docker status
            for instance in instances:
                if instance['container_id']:
                    container_status = self.docker.get_container_status(instance['container_id'])
                    if 'status' in container_status:
                        # Update database if status changed
                        if container_status['status'] != instance['status']:
                            self.db.update_instance(instance['id'], {'status': container_status['status']})
                        instance['current_status'] = container_status['status']
                        instance['resource_usage'] = container_status.get('resource_usage', {})
                    else:
                        instance['current_status'] = 'unknown'
                        instance['resource_usage'] = {}
                else:
                    instance['current_status'] = 'no_container'
                    instance['resource_usage'] = {}
            
            return instances
            
        except Exception as e:
            self.logger.error(f"Error listing instances: {e}")
            return []
    
    def clone_instance(self, source_instance_id: int, new_name: str, 
                      clone_data: bool = False) -> Tuple[bool, str, Optional[int]]:
        """Clone an existing instance"""
        try:
            # Get source instance
            source = self.db.get_instance(source_instance_id)
            if not source:
                return False, f"Source instance {source_instance_id} not found", None
            
            # Prepare clone configuration
            clone_config = {
                'image': source['image'],
                'config': json.loads(source['config']) if source['config'] else {},
                'resource_limits': json.loads(source['resource_limits']) if source['resource_limits'] else {},
                'environment_vars': json.loads(source['environment_vars']) if source['environment_vars'] else {},
                'volumes': json.loads(source['volumes']) if source['volumes'] else {},
                'networks': json.loads(source['networks']) if source['networks'] else {}
            }
            
            # Create new instance
            success, message, new_instance_id = self.create_instance(new_name, clone_config)
            
            if success and clone_data and source['container_id']:
                # Implement data cloning from source container volumes
                clone_success = self._clone_instance_data(source, new_instance_id)
                if clone_success:
                    self.logger.info(f"Successfully cloned data from '{source['name']}' to '{new_name}'")
                else:
                    self.logger.warning(f"Instance cloned but data cloning failed for '{new_name}'")
            
            if success:
                self.logger.info(f"Cloned instance '{source['name']}' to '{new_name}'")
            
            return success, message, new_instance_id
            
        except Exception as e:
            error_msg = f"Error cloning instance {source_instance_id}: {e}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    def update_instance_config(self, instance_id: int, config_updates: Dict[str, Any]) -> Tuple[bool, str]:
        """Update instance configuration"""
        try:
            instance = self.db.get_instance(instance_id)
            if not instance:
                return False, f"Instance {instance_id} not found"
            
            # Update database record
            success = self.db.update_instance(instance_id, config_updates)
            
            if success:
                self.logger.info(f"Updated configuration for instance '{instance['name']}'")
                return True, f"Configuration updated for instance '{instance['name']}'"
            else:
                return False, "Failed to update configuration"
                
        except Exception as e:
            error_msg = f"Error updating instance config {instance_id}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def get_instance_logs(self, instance_id: int, tail: int = 100) -> str:
        """Get instance logs"""
        try:
            instance = self.db.get_instance(instance_id)
            if not instance:
                return f"Instance {instance_id} not found"
            
            if not instance['container_id']:
                return f"Instance '{instance['name']}' has no associated container"
            
            return self.docker.get_container_logs(instance['container_id'], tail)
            
        except Exception as e:
            error_msg = f"Error getting logs for instance {instance_id}: {e}"
            self.logger.error(error_msg)
            return error_msg
    
    def get_instance_stats(self, instance_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed instance statistics"""
        try:
            instance = self.db.get_instance(instance_id)
            if not instance:
                return None
            
            if not instance['container_id']:
                return None
            
            # Get container stats from Docker
            container_stats = self.docker.get_container_stats(instance['container_id'])
            
            if not container_stats or 'error' in container_stats:
                return None
            
            # Get container info
            container_info = self.docker.get_container_info(instance['container_id'])
            
            # Combine stats and info
            stats = {
                'status': container_info.get('status', 'unknown'),
                'started_at': container_info.get('started_at'),
                'restart_count': container_info.get('restart_count', 0),
                'cpu_usage': container_stats.get('cpu_percent', 0),
                'memory_usage': container_stats.get('memory_usage', 0),
                'memory_limit': container_stats.get('memory_limit', 0),
                'memory_percent': container_stats.get('memory_percent', 0),
                'network_rx_bytes': container_stats.get('network_rx_bytes', 0),
                'network_tx_bytes': container_stats.get('network_tx_bytes', 0),
                'block_read_bytes': container_stats.get('block_read_bytes', 0),
                'block_write_bytes': container_stats.get('block_write_bytes', 0),
                'pids': container_stats.get('pids', 0)
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting stats for instance {instance_id}: {e}")
            return None
    
    def perform_health_check(self, instance_id: int) -> Tuple[bool, str, str]:
        """
        Perform health check on instance
        Returns: (is_healthy, status, message)
        """
        try:
            instance = self.db.get_instance(instance_id)
            if not instance:
                return False, 'unknown', f"Instance {instance_id} not found"
            
            if not instance['container_id']:
                return False, 'no_container', f"Instance '{instance['name']}' has no associated container"
            
            # Get container status
            container_status = self.docker.get_container_status(instance['container_id'])
            
            if 'error' in container_status:
                health_status = 'unhealthy'
                is_healthy = False
                message = container_status['error']
            elif container_status.get('status') == 'running':
                # Perform HTTP health check to n8n endpoint
                health_status = self._perform_http_health_check(instance)
                is_healthy = True
                message = 'Container running'
            else:
                health_status = 'unhealthy'
                is_healthy = False
                message = f"Container status: {container_status.get('status', 'unknown')}"
            
            # Update database
            self.db.update_instance(instance_id, {
                'health_status': health_status,
                'last_health_check': datetime.now().isoformat()
            })
            
            return is_healthy, health_status, message
            
        except Exception as e:
            error_msg = f"Error performing health check for instance {instance_id}: {e}"
            self.logger.error(error_msg)
            return False, 'error', error_msg
    
    def bulk_operation(self, instance_ids: List[int], operation: str) -> Dict[int, Tuple[bool, str]]:
        """Perform bulk operations on multiple instances"""
        results = {}
        
        for instance_id in instance_ids:
            try:
                if operation == 'start':
                    results[instance_id] = self.start_instance(instance_id)
                elif operation == 'stop':
                    results[instance_id] = self.stop_instance(instance_id)
                elif operation == 'restart':
                    results[instance_id] = self.restart_instance(instance_id)
                elif operation == 'health_check':
                    is_healthy, status, message = self.perform_health_check(instance_id)
                    results[instance_id] = (is_healthy, message)
                else:
                    results[instance_id] = (False, f"Unknown operation: {operation}")
            except Exception as e:
                results[instance_id] = (False, str(e))
        
        return results
    
    # Private helper methods
    def _validate_instance_name(self, name: str) -> bool:
        """Validate instance name"""
        if not name or len(name) < 3 or len(name) > 50:
            return False
        
        # Check for valid characters (alphanumeric, hyphens, underscores)
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            return False
        
        return True
    
    def _prepare_instance_config(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare instance configuration with defaults"""
        default_config = {
            'name': name,
            'image': self.config.get('docker.default_image', 'n8nio/n8n:latest'),
            'environment_vars': {
                'N8N_HOST': '0.0.0.0',
                'N8N_PORT': '5678',
                'N8N_PROTOCOL': 'http',
                'NODE_ENV': 'production'
            },
            'resource_limits': {
                'memory': self.config.get('docker.default_memory_limit', '512m'),
                'cpu': self.config.get('docker.default_cpu_limit', '0.5')
            },
            'volumes': {},
            'networks': {}
        }
        
        # Merge with provided config
        for key, value in config.items():
            if key in default_config:
                if isinstance(default_config[key], dict) and isinstance(value, dict):
                    default_config[key].update(value)
                else:
                    default_config[key] = value
            else:
                default_config[key] = value
        
        return default_config
    
    def _schedule_health_check(self, instance_id: int):
        """Schedule a health check for an instance"""
        # Implement background health checking with threading
        import threading
        
        def delayed_health_check():
            # Wait a bit for the container to fully start
            time.sleep(10)
            try:
                self.perform_health_check(instance_id)
            except Exception as e:
                self.logger.warning(f"Failed to perform scheduled health check for instance {instance_id}: {e}")
        
        # Start health check in background thread
        health_check_thread = threading.Thread(target=delayed_health_check, daemon=True)
        health_check_thread.start()
        
        # Also perform immediate health check
        try:
            self.perform_health_check(instance_id)
        except Exception as e:
            self.logger.warning(f"Failed to perform initial health check for instance {instance_id}: {e}")
    
    def _perform_http_health_check(self, instance: Dict[str, Any]) -> str:
        """Perform HTTP health check on n8n instance"""
        try:
            import requests
            
            port = instance.get('port')
            if not port:
                return 'unhealthy'
            
            # Try to connect to n8n main endpoint (n8n doesn't have /healthz)
            url = f"http://localhost:{port}/"
            
            # Set a short timeout for health checks
            timeout = self.config.get('health_check.timeout', 5)
            
            response = requests.get(url, timeout=timeout)
            
            if response.status_code == 200:
                return 'healthy'
            else:
                self.logger.debug(f"Health check failed for instance {instance['name']}: HTTP {response.status_code}")
                return 'unhealthy'
                
        except requests.exceptions.ConnectionError:
            # n8n might not be fully started yet
            return 'starting'
        except requests.exceptions.Timeout:
            self.logger.debug(f"Health check timeout for instance {instance['name']}")
            return 'unhealthy'
        except Exception as e:
            self.logger.warning(f"Health check error for instance {instance['name']}: {e}")
            return 'unhealthy'
    
    def _clone_instance_data(self, source_instance: Dict[str, Any], target_instance_id: int) -> bool:
        """Clone data from source instance to target instance"""
        try:
            import subprocess
            import tempfile
            import shutil
            from pathlib import Path
            
            # Get target instance
            target_instance = self.db.get_instance(target_instance_id)
            if not target_instance:
                self.logger.error(f"Target instance {target_instance_id} not found")
                return False
            
            source_name = source_instance['name']
            target_name = target_instance['name']
            
            # Stop both containers to ensure data consistency
            self.logger.info(f"Stopping containers for data cloning...")
            self.docker.stop_container(source_instance['container_id'])
            if target_instance['container_id']:
                self.docker.stop_container(target_instance['container_id'])
            
            # Create temporary directory for data transfer
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                source_data_path = temp_path / "source_data"
                
                # Copy data from source volume to temporary directory
                source_volume = f"{source_name}_data"
                self.logger.info(f"Copying data from source volume {source_volume}...")
                
                # Create a temporary container to access the source volume
                copy_command = [
                    'docker', 'run', '--rm',
                    '-v', f'{source_volume}:/source:ro',
                    '-v', f'{temp_dir}:/temp',
                    'alpine:latest',
                    'sh', '-c', 'cp -r /source/* /temp/source_data/ 2>/dev/null || mkdir -p /temp/source_data'
                ]
                
                # Create source_data directory
                source_data_path.mkdir(exist_ok=True)
                
                result = subprocess.run(copy_command, capture_output=True, text=True)
                if result.returncode != 0:
                    self.logger.warning(f"Data copy from source may be incomplete: {result.stderr}")
                
                # Copy data to target volume
                target_volume = f"{target_name}_data"
                self.logger.info(f"Copying data to target volume {target_volume}...")
                
                copy_to_target_command = [
                    'docker', 'run', '--rm',
                    '-v', f'{target_volume}:/target',
                    '-v', f'{temp_dir}:/temp',
                    'alpine:latest',
                    'sh', '-c', 'cp -r /temp/source_data/* /target/ 2>/dev/null || true'
                ]
                
                result = subprocess.run(copy_to_target_command, capture_output=True, text=True)
                if result.returncode != 0:
                    self.logger.error(f"Failed to copy data to target: {result.stderr}")
                    return False
            
            # Restart source container if it was running
            if source_instance.get('status') == 'running':
                self.docker.start_container(source_instance['container_id'])
            
            # Restart target container
            if target_instance['container_id']:
                self.docker.start_container(target_instance['container_id'])
            
            self.logger.info(f"Successfully cloned data from '{source_name}' to '{target_name}'")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cloning instance data: {e}")
            
            # Attempt to restart containers even if cloning failed
            try:
                if source_instance.get('status') == 'running':
                    self.docker.start_container(source_instance['container_id'])
                if target_instance and target_instance.get('container_id'):
                    self.docker.start_container(target_instance['container_id'])
            except:
                pass
            
            return False


# Global n8n manager instance
_n8n_manager_instance = None

def get_n8n_manager() -> N8nManager:
    """Get the global n8n manager instance"""
    global _n8n_manager_instance
    if _n8n_manager_instance is None:
        _n8n_manager_instance = N8nManager()
    return _n8n_manager_instance