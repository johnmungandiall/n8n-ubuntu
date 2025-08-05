"""
Docker integration for n8n Management App
Handles Docker daemon communication and container lifecycle management
"""

import docker
import time
import socket
import threading
from contextlib import contextmanager
from typing import Dict, List, Optional, Any, Tuple
from docker.models.containers import Container
from docker.models.images import Image
from docker.models.networks import Network
from docker.models.volumes import Volume
from docker.errors import DockerException, APIError, NotFound
from .logger import get_logger
from .config_manager import get_config
try:
    from utils.timeout_wrapper import docker_timeout, TimeoutError
except ImportError:
    # Fallback if timeout wrapper is not available
    class TimeoutError(Exception):
        pass
    
    class MockTimeout:
        def wrap_operation(self, operation, func, *args, **kwargs):
            return func(*args, **kwargs)
    
    docker_timeout = MockTimeout()


class PortManager:
    """Thread-safe port management with atomic reservation"""
    
    def __init__(self):
        self._reserved_ports = set()
        self._lock = threading.Lock()
    
    @contextmanager
    def reserve_port(self, start_port, end_port):
        """Atomically reserve an available port"""
        with self._lock:
            for port in range(start_port, end_port + 1):
                if port not in self._reserved_ports and self._is_port_bindable(port):
                    self._reserved_ports.add(port)
                    try:
                        yield port
                    finally:
                        self._reserved_ports.discard(port)
                    return
            raise RuntimeError(f"No available ports in range {start_port}-{end_port}")
    
    def _is_port_bindable(self, port):
        """Test if port can actually be bound"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('localhost', port))
                return True
        except OSError:
            return False


class DockerManager:
    """Manages Docker operations for n8n instances"""
    
    def __init__(self):
        self.logger = get_logger()
        self.config = get_config()
        self.client = None
        self.port_manager = PortManager()
        self._connect()
    
    def _connect(self, max_retries=5, base_delay=1.0):
        """Establish connection to Docker daemon with retry logic"""
        for attempt in range(max_retries):
            try:
                self.client = docker.from_env()
                self.client.ping()
                self.logger.info(f"Successfully connected to Docker daemon (attempt {attempt + 1})")
                return
            except DockerException as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"Failed to connect to Docker daemon after {max_retries} attempts: {e}")
                    raise
                
                delay = base_delay * (2 ** attempt)  # exponential backoff
                self.logger.warning(f"Docker connection attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                time.sleep(delay)
    
    def is_docker_available(self) -> bool:
        """Check if Docker daemon is available and responsive"""
        try:
            if self.client is None:
                self._connect()
            return docker_timeout.wrap_operation('ping', self.client.ping)
        except (TimeoutError, Exception) as e:
            self.logger.error(f"Docker daemon not available: {e}")
            return False
    
    def get_docker_info(self) -> Dict[str, Any]:
        """Get Docker daemon information"""
        try:
            info = self.client.info()
            version = self.client.version()
            return {
                'daemon_info': info,
                'version': version,
                'containers_running': info.get('ContainersRunning', 0),
                'containers_total': info.get('Containers', 0),
                'images_count': info.get('Images', 0),
                'server_version': version.get('Version', 'Unknown')
            }
        except Exception as e:
            self.logger.error(f"Error getting Docker info: {e}")
            return {}
    
    # Container lifecycle management
    def create_container(self, instance_config: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """
        Create a new n8n container
        Returns: (success, message, container_id)
        """
        try:
            # Extract configuration
            name = instance_config['name']
            image = instance_config.get('image', self.config.get('docker.default_image'))
            port = instance_config.get('port', 5678)
            environment = instance_config.get('environment_vars', {})
            volumes = instance_config.get('volumes', {})
            resource_limits = instance_config.get('resource_limits', {})
            
            # Prepare container configuration
            container_config = {
                'image': image,
                'name': name,
                'ports': {f'{port}/tcp': port},
                'environment': environment,
                'detach': True,
                'restart_policy': {'Name': 'unless-stopped'}
            }
            
            # Add volume mounts
            if volumes:
                container_config['volumes'] = volumes
            else:
                # Default volume for n8n data persistence
                default_volume = f"{name}_data"
                self._ensure_volume_exists(default_volume)
                container_config['volumes'] = {
                    default_volume: {'bind': '/home/node/.n8n', 'mode': 'rw'}
                }
            
            # Add resource limits
            if resource_limits:
                if 'memory' in resource_limits:
                    container_config['mem_limit'] = resource_limits['memory']
                if 'cpu' in resource_limits:
                    container_config['cpu_quota'] = int(float(resource_limits['cpu']) * 100000)
                    container_config['cpu_period'] = 100000
            
            # Ensure network exists
            network_name = self.config.get('docker.network_name', 'n8n_network')
            self._ensure_network_exists(network_name)
            container_config['network'] = network_name
            
            # Pull image if not available
            self._ensure_image_available(image)
            
            # Create container
            container = self.client.containers.create(**container_config)
            
            self.logger.info(f"Created container {name} with ID {container.id}")
            return True, f"Container {name} created successfully", container.id
            
        except APIError as e:
            error_msg = f"Docker API error creating container {name}: {e}"
            self.logger.error(error_msg)
            return False, error_msg, None
        except Exception as e:
            error_msg = f"Error creating container {name}: {e}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    def start_container(self, container_id: str) -> Tuple[bool, str]:
        """Start a container"""
        try:
            container = self.client.containers.get(container_id)
            container.start()
            
            # Wait a moment and check if it's actually running
            time.sleep(2)
            container.reload()
            
            if container.status == 'running':
                self.logger.info(f"Started container {container.name}")
                return True, f"Container {container.name} started successfully"
            else:
                error_msg = f"Container {container.name} failed to start (status: {container.status})"
                self.logger.error(error_msg)
                return False, error_msg
                
        except NotFound:
            error_msg = f"Container {container_id} not found"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error starting container {container_id}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def stop_container(self, container_id: str, timeout: int = 10) -> Tuple[bool, str]:
        """Stop a container"""
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=timeout)
            
            self.logger.info(f"Stopped container {container.name}")
            return True, f"Container {container.name} stopped successfully"
            
        except NotFound:
            error_msg = f"Container {container_id} not found"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error stopping container {container_id}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def restart_container(self, container_id: str, timeout: int = 10) -> Tuple[bool, str]:
        """Restart a container"""
        try:
            container = self.client.containers.get(container_id)
            container.restart(timeout=timeout)
            
            # Wait and verify it's running
            time.sleep(2)
            container.reload()
            
            if container.status == 'running':
                self.logger.info(f"Restarted container {container.name}")
                return True, f"Container {container.name} restarted successfully"
            else:
                error_msg = f"Container {container.name} failed to restart (status: {container.status})"
                self.logger.error(error_msg)
                return False, error_msg
                
        except NotFound:
            error_msg = f"Container {container_id} not found"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error restarting container {container_id}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def pause_container(self, container_id: str) -> Tuple[bool, str]:
        """Pause a container"""
        try:
            container = self.client.containers.get(container_id)
            container.pause()
            
            self.logger.info(f"Paused container {container.name}")
            return True, f"Container {container.name} paused successfully"
            
        except NotFound:
            error_msg = f"Container {container_id} not found"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error pausing container {container_id}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def unpause_container(self, container_id: str) -> Tuple[bool, str]:
        """Unpause a container"""
        try:
            container = self.client.containers.get(container_id)
            container.unpause()
            
            self.logger.info(f"Unpaused container {container.name}")
            return True, f"Container {container.name} unpaused successfully"
            
        except NotFound:
            error_msg = f"Container {container_id} not found"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error unpausing container {container_id}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def remove_container(self, container_id: str, force: bool = False, 
                        remove_volumes: bool = False) -> Tuple[bool, str]:
        """Remove a container"""
        try:
            container = self.client.containers.get(container_id)
            container_name = container.name
            
            # Stop container if running
            if container.status == 'running':
                container.stop(timeout=10)
            
            # Remove container
            container.remove(force=force, v=remove_volumes)
            
            self.logger.info(f"Removed container {container_name}")
            return True, f"Container {container_name} removed successfully"
            
        except NotFound:
            error_msg = f"Container {container_id} not found"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error removing container {container_id}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def get_container_status(self, container_id: str) -> Dict[str, Any]:
        """Get detailed container status"""
        try:
            container = self.client.containers.get(container_id)
            container.reload()
            
            # Get container stats (non-blocking)
            stats = {}
            try:
                stats_stream = container.stats(stream=False)
                stats = self._parse_container_stats(stats_stream)
            except Exception as e:
                self.logger.warning(f"Could not get stats for container {container.name}: {e}")
            
            return {
                'id': container.id,
                'name': container.name,
                'status': container.status,
                'image': container.image.tags[0] if container.image.tags else container.image.id,
                'created': container.attrs['Created'],
                'started_at': container.attrs['State'].get('StartedAt'),
                'ports': container.ports,
                'environment': container.attrs['Config'].get('Env', []),
                'mounts': [mount['Source'] + ':' + mount['Destination'] 
                          for mount in container.attrs.get('Mounts', [])],
                'network_settings': container.attrs.get('NetworkSettings', {}),
                'resource_usage': stats
            }
            
        except NotFound:
            return {'error': f'Container {container_id} not found'}
        except Exception as e:
            self.logger.error(f"Error getting container status {container_id}: {e}")
            return {'error': str(e)}
    
    def _parse_container_stats(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Parse container statistics"""
        try:
            # CPU usage calculation
            cpu_stats = stats.get('cpu_stats', {})
            precpu_stats = stats.get('precpu_stats', {})
            
            cpu_usage = 0.0
            if cpu_stats and precpu_stats:
                cpu_delta = cpu_stats.get('cpu_usage', {}).get('total_usage', 0) - precpu_stats.get('cpu_usage', {}).get('total_usage', 0)
                system_delta = cpu_stats.get('system_cpu_usage', 0) - precpu_stats.get('system_cpu_usage', 0)
                if system_delta > 0 and cpu_delta >= 0:
                    # Use online_cpus if available, otherwise fall back to percpu_usage length or 1
                    num_cpus = cpu_stats.get('online_cpus', 1)
                    if num_cpus == 0:
                        percpu_usage = cpu_stats.get('cpu_usage', {}).get('percpu_usage', [])
                        num_cpus = len(percpu_usage) if percpu_usage else 1
                    cpu_usage = (cpu_delta / system_delta) * num_cpus * 100.0
            
            # Memory usage
            memory_stats = stats.get('memory_stats', {})
            memory_usage = memory_stats.get('usage', 0)
            memory_limit = memory_stats.get('limit', 0)
            memory_percent = (memory_usage / memory_limit * 100) if memory_limit > 0 else 0
            
            # Network I/O
            networks = stats.get('networks', {})
            network_rx = sum(net.get('rx_bytes', 0) for net in networks.values())
            network_tx = sum(net.get('tx_bytes', 0) for net in networks.values())
            
            return {
                'cpu_percent': round(cpu_usage, 2),
                'memory_usage': memory_usage,
                'memory_limit': memory_limit,
                'memory_percent': round(memory_percent, 2),
                'network_rx_bytes': network_rx,
                'network_tx_bytes': network_tx
            }
            
        except Exception as e:
            self.logger.warning(f"Error parsing container stats: {e}")
            return {}
    
    def get_container_logs(self, container_id: str, tail: int = 100) -> str:
        """Get container logs"""
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(tail=tail, timestamps=True).decode('utf-8')
            return logs
        except NotFound:
            return f"Container {container_id} not found"
        except Exception as e:
            self.logger.error(f"Error getting logs for container {container_id}: {e}")
            return f"Error getting logs: {e}"
    
    def get_container_stats(self, container_id: str) -> Dict[str, Any]:
        """Get real-time container statistics"""
        try:
            container = self.client.containers.get(container_id)
            
            # Get stats (non-blocking, single snapshot)
            stats_stream = container.stats(stream=False)
            parsed_stats = self._parse_container_stats(stats_stream)
            
            # Add block I/O stats
            blkio_stats = stats_stream.get('blkio_stats', {})
            io_service_bytes = blkio_stats.get('io_service_bytes_recursive', [])
            
            block_read = 0
            block_write = 0
            for entry in io_service_bytes:
                if entry.get('op') == 'Read':
                    block_read += entry.get('value', 0)
                elif entry.get('op') == 'Write':
                    block_write += entry.get('value', 0)
            
            parsed_stats.update({
                'block_read_bytes': block_read,
                'block_write_bytes': block_write,
                'pids': stats_stream.get('pids_stats', {}).get('current', 0)
            })
            
            return parsed_stats
            
        except NotFound:
            return {'error': f'Container {container_id} not found'}
        except Exception as e:
            self.logger.error(f"Error getting container stats {container_id}: {e}")
            return {'error': str(e)}
    
    def get_container_info(self, container_id: str) -> Dict[str, Any]:
        """Get detailed container information"""
        try:
            container = self.client.containers.get(container_id)
            container.reload()
            
            attrs = container.attrs
            state = attrs.get('State', {})
            
            return {
                'id': container.id,
                'name': container.name,
                'status': container.status,
                'image': container.image.tags[0] if container.image.tags else container.image.id,
                'created_at': attrs.get('Created'),
                'started_at': state.get('StartedAt'),
                'finished_at': state.get('FinishedAt'),
                'restart_count': state.get('RestartCount', 0),
                'exit_code': state.get('ExitCode'),
                'pid': state.get('Pid'),
                'ports': container.ports,
                'environment': attrs.get('Config', {}).get('Env', []),
                'mounts': attrs.get('Mounts', []),
                'network_settings': attrs.get('NetworkSettings', {})
            }
            
        except NotFound:
            return {'error': f'Container {container_id} not found'}
        except Exception as e:
            self.logger.error(f"Error getting container info {container_id}: {e}")
            return {'error': str(e)}
    
    # Image management
    def _ensure_image_available(self, image_name: str):
        """Ensure Docker image is available locally"""
        try:
            self.client.images.get(image_name)
            self.logger.debug(f"Image {image_name} already available")
        except NotFound:
            self.logger.info(f"Pulling image {image_name}...")
            try:
                self.client.images.pull(image_name)
                self.logger.info(f"Successfully pulled image {image_name}")
            except Exception as e:
                self.logger.error(f"Failed to pull image {image_name}: {e}")
                raise
    
    def list_images(self) -> List[Dict[str, Any]]:
        """List available Docker images"""
        try:
            images = self.client.images.list()
            return [
                {
                    'id': img.id,
                    'tags': img.tags,
                    'created': img.attrs['Created'],
                    'size': img.attrs['Size']
                }
                for img in images
            ]
        except Exception as e:
            self.logger.error(f"Error listing images: {e}")
            return []
    
    # Network management
    def _ensure_network_exists(self, network_name: str):
        """Ensure Docker network exists"""
        try:
            self.client.networks.get(network_name)
            self.logger.debug(f"Network {network_name} already exists")
        except NotFound:
            try:
                self.client.networks.create(network_name, driver='bridge')
                self.logger.info(f"Created network {network_name}")
            except Exception as e:
                self.logger.error(f"Failed to create network {network_name}: {e}")
                raise
    
    def list_networks(self) -> List[Dict[str, Any]]:
        """List Docker networks"""
        try:
            networks = self.client.networks.list()
            return [
                {
                    'id': net.id,
                    'name': net.name,
                    'driver': net.attrs['Driver'],
                    'created': net.attrs['Created']
                }
                for net in networks
            ]
        except Exception as e:
            self.logger.error(f"Error listing networks: {e}")
            return []
    
    # Volume management
    def _ensure_volume_exists(self, volume_name: str):
        """Ensure Docker volume exists"""
        try:
            self.client.volumes.get(volume_name)
            self.logger.debug(f"Volume {volume_name} already exists")
        except NotFound:
            try:
                self.client.volumes.create(volume_name)
                self.logger.info(f"Created volume {volume_name}")
            except Exception as e:
                self.logger.error(f"Failed to create volume {volume_name}: {e}")
                raise
    
    def list_volumes(self) -> List[Dict[str, Any]]:
        """List Docker volumes"""
        try:
            volumes = self.client.volumes.list()
            return [
                {
                    'name': vol.name,
                    'driver': vol.attrs['Driver'],
                    'created': vol.attrs['CreatedAt'],
                    'mountpoint': vol.attrs['Mountpoint']
                }
                for vol in volumes
            ]
        except Exception as e:
            self.logger.error(f"Error listing volumes: {e}")
            return []
    
    def remove_volume(self, volume_name: str, force: bool = False) -> Tuple[bool, str]:
        """Remove a Docker volume"""
        try:
            volume = self.client.volumes.get(volume_name)
            volume.remove(force=force)
            self.logger.info(f"Removed volume {volume_name}")
            return True, f"Volume {volume_name} removed successfully"
        except NotFound:
            error_msg = f"Volume {volume_name} not found"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error removing volume {volume_name}: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    # Utility methods
    def is_port_available(self, port: int) -> bool:
        """Check if a port is available for use"""
        try:
            containers = self.client.containers.list()
            for container in containers:
                if container.ports:
                    for container_port, host_bindings in container.ports.items():
                        if host_bindings:
                            for binding in host_bindings:
                                if int(binding['HostPort']) == port:
                                    return False
            return True
        except Exception as e:
            self.logger.error(f"Error checking port availability: {e}")
            return False
    
    def find_available_port(self, start_port: int = None, end_port: int = None) -> Optional[int]:
        """Find an available port in the specified range"""
        if start_port is None or end_port is None:
            port_range = self.config.get('docker.default_port_range', [5678, 5700])
            start_port = port_range[0]
            end_port = port_range[1]
        
        for port in range(start_port, end_port + 1):
            if self.is_port_available(port):
                return port
        
        return None
    
    def cleanup_unused_resources(self) -> Dict[str, int]:
        """Clean up unused Docker resources"""
        cleanup_stats = {
            'containers_removed': 0,
            'images_removed': 0,
            'volumes_removed': 0,
            'networks_removed': 0
        }
        
        try:
            # Remove stopped containers
            stopped_containers = self.client.containers.list(filters={'status': 'exited'})
            for container in stopped_containers:
                try:
                    container.remove()
                    cleanup_stats['containers_removed'] += 1
                except Exception as e:
                    self.logger.warning(f"Could not remove container {container.name}: {e}")
            
            # Remove unused images
            try:
                removed_images = self.client.images.prune()
                cleanup_stats['images_removed'] = len(removed_images.get('ImagesDeleted', []))
            except Exception as e:
                self.logger.warning(f"Could not prune images: {e}")
            
            # Remove unused volumes
            try:
                removed_volumes = self.client.volumes.prune()
                cleanup_stats['volumes_removed'] = len(removed_volumes.get('VolumesDeleted', []))
            except Exception as e:
                self.logger.warning(f"Could not prune volumes: {e}")
            
            # Remove unused networks
            try:
                removed_networks = self.client.networks.prune()
                cleanup_stats['networks_removed'] = len(removed_networks.get('NetworksDeleted', []))
            except Exception as e:
                self.logger.warning(f"Could not prune networks: {e}")
            
            self.logger.info(f"Cleanup completed: {cleanup_stats}")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
        
        return cleanup_stats


# Global Docker manager instance
_docker_instance = None

def get_docker_manager() -> DockerManager:
    """Get the global Docker manager instance"""
    global _docker_instance
    if _docker_instance is None:
        _docker_instance = DockerManager()
    return _docker_instance