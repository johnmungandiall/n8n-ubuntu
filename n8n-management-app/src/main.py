"""
Main entry point for n8n Management App
Handles application startup, initialization, and shutdown
"""

import sys
import argparse
import signal
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.logger import setup_logger, get_logger
from core.config_manager import setup_config, get_config
from core.database import setup_database, get_database
from core.docker_manager import get_docker_manager
from gui.main_window import MainWindow


class N8nManagementApp:
    """Main application class"""
    
    def __init__(self, config_dir: Optional[str] = None, db_path: Optional[str] = None):
        self.config_dir = config_dir
        self.db_path = db_path
        self.logger = None
        self.config = None
        self.database = None
        self.docker_manager = None
        self.main_window = None
        self.running = False
    
    def initialize(self) -> bool:
        """Initialize application components"""
        try:
            # Setup logging first
            self.logger = setup_logger()
            self.logger.info("Starting n8n Management App...")
            
            # Setup configuration
            self.config = setup_config(self.config_dir)
            self.config.update_from_env()  # Load environment variables
            
            # Setup database
            self.database = setup_database(self.db_path)
            
            # Test Docker connection
            self.docker_manager = get_docker_manager()
            if not self.docker_manager.is_docker_available():
                self.logger.error("Docker daemon is not available. Please ensure Docker is running.")
                return False
            
            # Log Docker info
            docker_info = self.docker_manager.get_docker_info()
            self.logger.info(f"Connected to Docker (version: {docker_info.get('server_version', 'Unknown')})")
            
            self.logger.info("Application initialization completed successfully")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize application: {e}")
            else:
                print(f"Failed to initialize application: {e}")
            return False
    
    def run_gui(self) -> int:
        """Run the GUI application"""
        try:
            if not self.initialize():
                return 1
            
            # Create and run main window
            self.main_window = MainWindow()
            self.running = True
            
            # Setup signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            self.logger.info("Starting GUI application")
            self.main_window.run()
            
            return 0
            
        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user")
            return 0
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error running GUI application: {e}")
            else:
                print(f"Error running GUI application: {e}")
            return 1
        finally:
            self.shutdown()
    
    def run_cli(self, args) -> int:
        """Run CLI commands"""
        try:
            if not self.initialize():
                return 1
            
            from core.n8n_manager import get_n8n_manager
            n8n_manager = get_n8n_manager()
            
            if args.command == 'list':
                instances = n8n_manager.list_instances()
                if not instances:
                    print("No instances found.")
                else:
                    print(f"{'ID':<5} {'Name':<20} {'Status':<12} {'Port':<6} {'Image'}")
                    print("-" * 70)
                    for instance in instances:
                        print(f"{instance['id']:<5} {instance['name']:<20} "
                              f"{instance['status']:<12} {instance['port'] or 'N/A':<6} "
                              f"{instance['image']}")
            
            elif args.command == 'create':
                if not args.name:
                    print("Error: Instance name is required")
                    return 1
                
                success, message, instance_id = n8n_manager.create_instance(args.name)
                if success:
                    print(f"Success: {message} (ID: {instance_id})")
                else:
                    print(f"Error: {message}")
                    return 1
            
            elif args.command == 'start':
                if not args.instance_id:
                    print("Error: Instance ID is required")
                    return 1
                
                success, message = n8n_manager.start_instance(args.instance_id)
                if success:
                    print(f"Success: {message}")
                else:
                    print(f"Error: {message}")
                    return 1
            
            elif args.command == 'stop':
                if not args.instance_id:
                    print("Error: Instance ID is required")
                    return 1
                
                success, message = n8n_manager.stop_instance(args.instance_id)
                if success:
                    print(f"Success: {message}")
                else:
                    print(f"Error: {message}")
                    return 1
            
            elif args.command == 'delete':
                if not args.instance_id:
                    print("Error: Instance ID is required")
                    return 1
                
                success, message = n8n_manager.delete_instance(args.instance_id, args.remove_data)
                if success:
                    print(f"Success: {message}")
                else:
                    print(f"Error: {message}")
                    return 1
            
            elif args.command == 'status':
                if not args.instance_id:
                    print("Error: Instance ID is required")
                    return 1
                
                status = n8n_manager.get_instance_status(args.instance_id)
                if 'error' in status:
                    print(f"Error: {status['error']}")
                    return 1
                else:
                    print(f"Instance: {status['name']}")
                    print(f"Status: {status['status']}")
                    print(f"Health: {status['health_status']}")
                    print(f"Port: {status['port']}")
                    print(f"Created: {status['created_at']}")
                    if 'container' in status and 'resource_usage' in status['container']:
                        usage = status['container']['resource_usage']
                        print(f"CPU: {usage.get('cpu_percent', 0):.1f}%")
                        print(f"Memory: {usage.get('memory_percent', 0):.1f}%")
            
            elif args.command == 'logs':
                if not args.instance_id:
                    print("Error: Instance ID is required")
                    return 1
                
                logs = n8n_manager.get_instance_logs(args.instance_id, args.tail)
                print(logs)
            
            else:
                print(f"Unknown command: {args.command}")
                return 1
            
            return 0
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error running CLI command: {e}")
            else:
                print(f"Error running CLI command: {e}")
            return 1
        finally:
            self.shutdown()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        if self.logger:
            self.logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)
    
    def shutdown(self):
        """Graceful application shutdown"""
        if not self.running:
            return
        
        self.running = False
        
        try:
            if self.logger:
                self.logger.info("Shutting down application...")
            
            # Close GUI if running
            if self.main_window:
                self.main_window.destroy()
            
            # Cleanup database connections
            if self.database:
                # Database connections are handled by context managers
                pass
            
            if self.logger:
                self.logger.info("Application shutdown completed")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error during shutdown: {e}")


def create_argument_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description='n8n Management App - Manage multiple n8n instances',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Start GUI application
  %(prog)s --cli list                # List all instances
  %(prog)s --cli create --name test  # Create new instance
  %(prog)s --cli start --id 1        # Start instance with ID 1
  %(prog)s --cli stop --id 1         # Stop instance with ID 1
  %(prog)s --cli status --id 1       # Show instance status
  %(prog)s --cli logs --id 1         # Show instance logs
        """
    )
    
    parser.add_argument(
        '--cli', 
        action='store_true',
        help='Run in CLI mode instead of GUI'
    )
    
    parser.add_argument(
        '--config-dir',
        type=str,
        help='Configuration directory path'
    )
    
    parser.add_argument(
        '--db-path',
        type=str,
        help='Database file path'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    # CLI subcommands
    parser.add_argument(
        'command',
        nargs='?',
        choices=['list', 'create', 'start', 'stop', 'restart', 'delete', 'status', 'logs'],
        help='CLI command to execute'
    )
    
    parser.add_argument(
        '--name',
        type=str,
        help='Instance name (for create command)'
    )
    
    parser.add_argument(
        '--id', '--instance-id',
        dest='instance_id',
        type=int,
        help='Instance ID'
    )
    
    parser.add_argument(
        '--remove-data',
        action='store_true',
        help='Remove instance data when deleting (for delete command)'
    )
    
    parser.add_argument(
        '--tail',
        type=int,
        default=100,
        help='Number of log lines to show (for logs command)'
    )
    
    return parser


def main():
    """Main entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Create application instance
    app = N8nManagementApp(
        config_dir=args.config_dir,
        db_path=args.db_path
    )
    
    # Set debug mode if requested
    if args.debug:
        import os
        os.environ['N8N_MANAGER_LOG_LEVEL'] = 'DEBUG'
    
    # Run in appropriate mode
    if args.cli:
        if not args.command:
            parser.error("CLI mode requires a command")
        return app.run_cli(args)
    else:
        return app.run_gui()


if __name__ == '__main__':
    sys.exit(main())