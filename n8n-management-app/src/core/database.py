"""
Database management for n8n Management App
Handles SQLite database operations, schema management, and migrations
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager
from .logger import get_logger
from .config_manager import get_config


class DatabaseManager:
    """Manages SQLite database operations and schema"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.logger = get_logger()
        self.config = get_config()
        
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path(self.config.get('database.path', 'data/n8n_manager.db'))
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database with required tables"""
        try:
            with self.get_connection() as conn:
                self._create_tables(conn)
                self._run_migrations(conn)
            self.logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise
    
    def _create_tables(self, conn: sqlite3.Connection):
        """Create database tables if they don't exist"""
        
        # Instances table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                container_id TEXT,
                image TEXT NOT NULL,
                port INTEGER,
                status TEXT DEFAULT 'stopped',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                config TEXT,  -- JSON configuration
                resource_limits TEXT,  -- JSON resource limits
                environment_vars TEXT,  -- JSON environment variables
                volumes TEXT,  -- JSON volume mappings
                networks TEXT,  -- JSON network configuration
                health_status TEXT DEFAULT 'unknown',
                last_health_check TIMESTAMP
            )
        """)
        
        # Configurations table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS configurations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                config_data TEXT NOT NULL,  -- JSON configuration
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_template BOOLEAN DEFAULT 0,
                tags TEXT  -- JSON array of tags
            )
        """)
        
        # Logs table for audit trail
        conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                component TEXT NOT NULL,
                action TEXT NOT NULL,
                instance_id INTEGER,
                message TEXT NOT NULL,
                details TEXT,  -- JSON additional details
                FOREIGN KEY (instance_id) REFERENCES instances (id)
            )
        """)
        
        # Backups table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instance_id INTEGER NOT NULL,
                backup_path TEXT NOT NULL,
                backup_type TEXT DEFAULT 'full',
                size_bytes INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'completed',
                checksum TEXT,
                FOREIGN KEY (instance_id) REFERENCES instances (id)
            )
        """)
        
        # Templates table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                version TEXT DEFAULT '1.0.0',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usage_count INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                tags TEXT,  -- JSON array of tags
                metadata TEXT  -- JSON metadata
            )
        """)
        
        # Create indexes for better performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_instances_name ON instances (name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_instances_status ON instances (status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs (timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_instance ON logs (instance_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_backups_instance ON backups (instance_id)")
        
        conn.commit()
    
    def _run_migrations(self, conn: sqlite3.Connection):
        """Run database migrations"""
        # Check if migrations table exists
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='migrations'
        """)
        
        if not cursor.fetchone():
            # Create migrations table
            conn.execute("""
                CREATE TABLE migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        
        # Define migrations
        migrations = [
            ('1.0.0', self._migration_1_0_0),
        ]
        
        # Apply migrations
        for version, migration_func in migrations:
            cursor = conn.execute(
                "SELECT version FROM migrations WHERE version = ?", 
                (version,)
            )
            if not cursor.fetchone():
                try:
                    migration_func(conn)
                    conn.execute(
                        "INSERT INTO migrations (version) VALUES (?)", 
                        (version,)
                    )
                    conn.commit()
                    self.logger.info(f"Applied migration {version}")
                except Exception as e:
                    self.logger.error(f"Error applying migration {version}: {e}")
                    conn.rollback()
                    raise
    
    def _migration_1_0_0(self, conn: sqlite3.Connection):
        """Initial migration - placeholder for future schema changes"""
        pass
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    # Instance management methods
    def create_instance(self, instance_data: Dict[str, Any]) -> int:
        """Create a new instance record"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO instances (
                    name, image, port, config, resource_limits, 
                    environment_vars, volumes, networks
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                instance_data['name'],
                instance_data['image'],
                instance_data.get('port'),
                json.dumps(instance_data.get('config', {})),
                json.dumps(instance_data.get('resource_limits', {})),
                json.dumps(instance_data.get('environment_vars', {})),
                json.dumps(instance_data.get('volumes', {})),
                json.dumps(instance_data.get('networks', {}))
            ))
            instance_id = cursor.lastrowid
            conn.commit()
            
            self.log_action('database', 'create_instance', instance_id, 
                          f"Created instance: {instance_data['name']}")
            return instance_id
    
    def get_instance(self, instance_id: int) -> Optional[Dict[str, Any]]:
        """Get instance by ID"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM instances WHERE id = ?", 
                (instance_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_instance_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get instance by name"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM instances WHERE name = ?", 
                (name,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_instances(self) -> List[Dict[str, Any]]:
        """Get all instances"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM instances ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]
    
    def update_instance(self, instance_id: int, updates: Dict[str, Any]) -> bool:
        """Update instance record"""
        if not updates:
            return False
        
        # Build dynamic update query
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            if key in ['config', 'resource_limits', 'environment_vars', 'volumes', 'networks']:
                set_clauses.append(f"{key} = ?")
                values.append(json.dumps(value))
            else:
                set_clauses.append(f"{key} = ?")
                values.append(value)
        
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        values.append(instance_id)
        
        query = f"UPDATE instances SET {', '.join(set_clauses)} WHERE id = ?"
        
        with self.get_connection() as conn:
            cursor = conn.execute(query, values)
            success = cursor.rowcount > 0
            conn.commit()
            
            if success:
                self.log_action('database', 'update_instance', instance_id, 
                              f"Updated instance fields: {list(updates.keys())}")
            
            return success
    
    def delete_instance(self, instance_id: int) -> bool:
        """Delete instance record"""
        with self.get_connection() as conn:
            # Get instance name for logging
            cursor = conn.execute("SELECT name FROM instances WHERE id = ?", (instance_id,))
            row = cursor.fetchone()
            instance_name = row['name'] if row else f"ID:{instance_id}"
            
            # Delete instance
            cursor = conn.execute("DELETE FROM instances WHERE id = ?", (instance_id,))
            success = cursor.rowcount > 0
            conn.commit()
            
            if success:
                self.log_action('database', 'delete_instance', instance_id, 
                              f"Deleted instance: {instance_name}")
            
            return success
    
    # Configuration management methods
    def save_configuration(self, name: str, config_data: Dict[str, Any], 
                          description: str = "", is_template: bool = False,
                          tags: List[str] = None) -> int:
        """Save configuration template"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO configurations 
                (name, description, config_data, is_template, tags, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                name,
                description,
                json.dumps(config_data),
                is_template,
                json.dumps(tags or [])
            ))
            config_id = cursor.lastrowid
            conn.commit()
            
            self.log_action('database', 'save_configuration', None, 
                          f"Saved configuration: {name}")
            return config_id
    
    def get_configuration(self, name: str) -> Optional[Dict[str, Any]]:
        """Get configuration by name"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM configurations WHERE name = ?", 
                (name,)
            )
            row = cursor.fetchone()
            if row:
                config = dict(row)
                config['config_data'] = json.loads(config['config_data'])
                config['tags'] = json.loads(config['tags'])
                return config
            return None
    
    def get_all_configurations(self, templates_only: bool = False) -> List[Dict[str, Any]]:
        """Get all configurations"""
        query = "SELECT * FROM configurations"
        if templates_only:
            query += " WHERE is_template = 1"
        query += " ORDER BY name"
        
        with self.get_connection() as conn:
            cursor = conn.execute(query)
            configs = []
            for row in cursor.fetchall():
                config = dict(row)
                config['config_data'] = json.loads(config['config_data'])
                config['tags'] = json.loads(config['tags'])
                configs.append(config)
            return configs
    
    # Logging methods
    def log_action(self, component: str, action: str, instance_id: Optional[int], 
                   message: str, level: str = 'INFO', details: Dict[str, Any] = None):
        """Log an action to the audit trail"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO logs (level, component, action, instance_id, message, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                level,
                component,
                action,
                instance_id,
                message,
                json.dumps(details) if details else None
            ))
            conn.commit()
    
    def get_logs(self, instance_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get logs with optional filtering"""
        query = "SELECT * FROM logs"
        params = []
        
        if instance_id is not None:
            query += " WHERE instance_id = ?"
            params.append(instance_id)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            logs = []
            for row in cursor.fetchall():
                log = dict(row)
                if log['details']:
                    log['details'] = json.loads(log['details'])
                logs.append(log)
            return logs
    
    # Backup methods
    def create_backup_record(self, instance_id: int, backup_path: str, 
                           backup_type: str = 'full', size_bytes: int = 0,
                           checksum: str = None) -> int:
        """Create backup record"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO backups (instance_id, backup_path, backup_type, size_bytes, checksum)
                VALUES (?, ?, ?, ?, ?)
            """, (instance_id, backup_path, backup_type, size_bytes, checksum))
            backup_id = cursor.lastrowid
            conn.commit()
            
            self.log_action('database', 'create_backup', instance_id, 
                          f"Created backup record: {backup_path}")
            return backup_id
    
    def get_backups(self, instance_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get backup records"""
        query = "SELECT * FROM backups"
        params = []
        
        if instance_id is not None:
            query += " WHERE instance_id = ?"
            params.append(instance_id)
        
        query += " ORDER BY created_at DESC"
        
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    # Utility methods
    def cleanup_old_logs(self, days: int = 30):
        """Clean up old log entries"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM logs 
                WHERE timestamp < datetime('now', '-{} days')
            """.format(days))
            deleted_count = cursor.rowcount
            conn.commit()
            
            self.logger.info(f"Cleaned up {deleted_count} old log entries")
            return deleted_count
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        with self.get_connection() as conn:
            stats = {}
            
            # Count records in each table
            for table in ['instances', 'configurations', 'logs', 'backups']:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f"{table}_count"] = cursor.fetchone()[0]
            
            # Database file size
            stats['db_size_bytes'] = self.db_path.stat().st_size
            
            return stats


# Global database instance
_db_instance = None

def get_database() -> DatabaseManager:
    """Get the global database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance

def setup_database(db_path: Optional[str] = None) -> DatabaseManager:
    """Setup and return the global database instance"""
    global _db_instance
    _db_instance = DatabaseManager(db_path)
    return _db_instance