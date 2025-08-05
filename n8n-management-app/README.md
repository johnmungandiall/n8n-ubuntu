# n8n Management App

A comprehensive desktop application for managing multiple n8n instances using Docker containers.

## Features

- **Instance Management**: Create, start, stop, restart, and delete n8n instances
- **Real-time Monitoring**: Monitor instance status, resource usage, and health
- **Configuration Management**: Manage instance configurations and templates
- **Logging**: View container logs and application audit logs
- **GUI Interface**: User-friendly desktop interface built with Tkinter
- **CLI Support**: Command-line interface for automation and scripting
- **Database Integration**: SQLite database for persistent storage
- **Docker Integration**: Full Docker API integration for container management

## Prerequisites

- Python 3.8 or higher
- Docker Desktop or Docker Engine
- 4GB+ RAM recommended
- 2GB+ free disk space

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd n8n-management-app
```

### 2. Setup Development Environment

```bash
python scripts/setup_dev.py
```

This script will:
- Create a virtual environment
- Install all dependencies
- Setup pre-commit hooks
- Create sample configuration
- Run basic tests

### 3. Activate Virtual Environment

**Linux/macOS:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

### 4. Run the Application

**GUI Mode (default):**
```bash
python src/main.py
```

**CLI Mode:**
```bash
python src/main.py --cli list
python src/main.py --cli create --name my-instance
python src/main.py --cli start --id 1
```

## Project Structure

```
n8n-management-app/
├── src/                    # Source code
│   ├── core/              # Core functionality
│   │   ├── config_manager.py
│   │   ├── database.py
│   │   ├── docker_manager.py
│   │   ├── logger.py
│   │   └── n8n_manager.py
│   ├── gui/               # GUI components
│   │   ├── main_window.py
│   │   ├── instance_manager.py
│   │   └── logs_viewer.py
│   ├── utils/             # Utility functions
│   │   ├── constants.py
│   │   ├── helpers.py
│   │   └── validators.py
│   └── main.py            # Application entry point
├── config/                # Configuration files
│   └── default_config.yaml
├── data/                  # Data storage
│   └── logs/              # Application logs
├── tests/                 # Test files
├── docs/                  # Documentation
├── scripts/               # Utility scripts
└── requirements.txt       # Dependencies
```

## Configuration

The application uses YAML configuration files:

- `config/default_config.yaml` - Default settings
- `config/user_config.yaml` - User overrides (created automatically)

### Key Configuration Sections

```yaml
app:
  name: "n8n Management App"
  version: "1.0.0"
  debug: false

docker:
  default_image: "n8nio/n8n:latest"
  default_port_range: [5678, 5700]
  default_memory_limit: "512m"
  default_cpu_limit: "0.5"

database:
  type: "sqlite"
  path: "data/n8n_manager.db"

logging:
  level: "INFO"
  file_path: "data/logs/app.log"

ui:
  theme: "light"
  window_width: 1200
  window_height: 800
  auto_refresh_interval: 5
```

## Usage

### GUI Interface

1. **Instance Management Tab**:
   - View all n8n instances
   - Create new instances
   - Start/stop/restart instances
   - View instance details and resource usage
   - Clone existing instances
   - Delete instances

2. **Logs Tab**:
   - View container logs
   - View application logs
   - View audit logs
   - Auto-refresh logs
   - Save logs to file

### CLI Commands

```bash
# List all instances
python src/main.py --cli list

# Create new instance
python src/main.py --cli create --name production-n8n

# Start instance
python src/main.py --cli start --id 1

# Stop instance
python src/main.py --cli stop --id 1

# View instance status
python src/main.py --cli status --id 1

# View instance logs
python src/main.py --cli logs --id 1 --tail 100

# Delete instance
python src/main.py --cli delete --id 1 --remove-data
```

## Development

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run specific test file
python -m pytest tests/test_core/test_config_manager.py -v
```

### Code Quality

```bash
# Format code
python -m black src/ tests/

# Check code style
python -m flake8 src/ tests/

# Type checking
python -m mypy src/
```

### Pre-commit Hooks

Pre-commit hooks are automatically installed during setup and will run:
- Code formatting (Black)
- Linting (Flake8)
- YAML validation
- Trailing whitespace removal

## Docker Integration

The application manages n8n instances as Docker containers with:

- **Automatic port assignment** from configured range
- **Volume persistence** for n8n data
- **Resource limits** (CPU, memory)
- **Network isolation** with custom Docker network
- **Health monitoring** and status tracking

### Default n8n Configuration

Each instance is created with:
- n8n image: `n8nio/n8n:latest`
- Port: Auto-assigned from range 5678-5700
- Memory limit: 512MB
- CPU limit: 0.5 cores
- Data volume: Persistent storage for workflows and settings

## Database Schema

The application uses SQLite with the following main tables:

- **instances**: Instance metadata and configuration
- **configurations**: Saved configuration templates
- **logs**: Audit trail of all operations
- **backups**: Backup metadata and tracking

## Troubleshooting

### Common Issues

1. **Docker not available**:
   - Ensure Docker Desktop is running
   - Check Docker daemon status: `docker info`

2. **Port conflicts**:
   - Check configured port range in settings
   - Use `netstat` to identify port usage

3. **Permission errors**:
   - Ensure user has Docker permissions
   - On Linux: Add user to docker group

4. **Database locked**:
   - Close other instances of the application
   - Check for stale lock files in data directory

### Debug Mode

Enable debug mode for detailed logging:

```bash
python src/main.py --debug
```

Or set in configuration:
```yaml
app:
  debug: true
logging:
  level: DEBUG
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and ensure code quality
5. Submit a pull request

### Development Guidelines

- Follow PEP 8 coding standards
- Write tests for new functionality
- Update documentation as needed
- Use type hints throughout
- Maintain 90%+ test coverage

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Search existing issues
3. Create a new issue with detailed information

## Roadmap

### Phase 1 (Current)
- ✅ Basic instance management
- ✅ GUI interface
- ✅ Docker integration
- ✅ Configuration management

### Phase 2 (Planned)
- [ ] Instance templates
- [ ] Backup and restore
- [ ] Advanced monitoring
- [ ] Workflow management

### Phase 3 (Future)
- [ ] Multi-host support
- [ ] API endpoints
- [ ] Plugin system
- [ ] Advanced security features

## Acknowledgments

- n8n team for the excellent workflow automation platform
- Docker for containerization technology
- Python community for the amazing ecosystem