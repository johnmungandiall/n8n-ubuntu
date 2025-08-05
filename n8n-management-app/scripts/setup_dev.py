#!/usr/bin/env python3
"""
Development environment setup script
Sets up the development environment for n8n Management App
"""

import os
import sys
import subprocess
import venv
from pathlib import Path


def run_command(command, check=True, shell=False):
    """Run a command and handle errors"""
    print(f"Running: {command}")
    try:
        if shell:
            result = subprocess.run(command, shell=True, check=check, text=True, capture_output=True)
        else:
            result = subprocess.run(command.split(), check=check, text=True, capture_output=True)
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Command failed with return code {e.returncode}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        return False


def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        return False
    print(f"Python version: {sys.version}")
    return True


def check_docker():
    """Check if Docker is available"""
    print("Checking Docker availability...")
    if run_command("docker --version", check=False):
        if run_command("docker info", check=False):
            print("✓ Docker is available and running")
            return True
        else:
            print("⚠ Docker is installed but not running")
            return False
    else:
        print("✗ Docker is not available")
        return False


def create_virtual_environment(project_root):
    """Create virtual environment"""
    venv_path = project_root / "venv"
    
    if venv_path.exists():
        print("Virtual environment already exists")
        return True
    
    print("Creating virtual environment...")
    try:
        venv.create(venv_path, with_pip=True)
        print("✓ Virtual environment created")
        return True
    except Exception as e:
        print(f"✗ Failed to create virtual environment: {e}")
        return False


def install_dependencies(project_root):
    """Install project dependencies"""
    venv_path = project_root / "venv"
    
    # Determine pip path based on OS
    if os.name == 'nt':  # Windows
        pip_path = venv_path / "Scripts" / "pip"
    else:  # Unix-like
        pip_path = venv_path / "bin" / "pip"
    
    print("Installing dependencies...")
    
    # Install development dependencies
    requirements_dev = project_root / "requirements-dev.txt"
    if requirements_dev.exists():
        if run_command(f"{pip_path} install -r {requirements_dev}"):
            print("✓ Development dependencies installed")
        else:
            print("✗ Failed to install development dependencies")
            return False
    else:
        print("⚠ requirements-dev.txt not found, installing basic dependencies")
        basic_deps = [
            "docker>=6.0.0",
            "pyyaml>=6.0",
            "requests>=2.28.0",
            "psutil>=5.9.0",
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0"
        ]
        
        for dep in basic_deps:
            if not run_command(f"{pip_path} install {dep}"):
                print(f"✗ Failed to install {dep}")
                return False
    
    return True


def setup_pre_commit_hooks(project_root):
    """Setup pre-commit hooks"""
    venv_path = project_root / "venv"
    
    # Determine pre-commit path based on OS
    if os.name == 'nt':  # Windows
        precommit_path = venv_path / "Scripts" / "pre-commit"
    else:  # Unix-like
        precommit_path = venv_path / "bin" / "pre-commit"
    
    precommit_config = project_root / ".pre-commit-config.yaml"
    
    if not precommit_config.exists():
        print("Creating .pre-commit-config.yaml...")
        config_content = """
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  
  - repo: https://github.com/psf/black
    rev: 22.10.0
    hooks:
      - id: black
        language_version: python3
  
  - repo: https://github.com/pycqa/flake8
    rev: 5.0.4
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203]
"""
        with open(precommit_config, 'w') as f:
            f.write(config_content.strip())
    
    print("Installing pre-commit hooks...")
    if run_command(f"{precommit_path} install"):
        print("✓ Pre-commit hooks installed")
        return True
    else:
        print("⚠ Failed to install pre-commit hooks (optional)")
        return True  # Not critical


def create_sample_data(project_root):
    """Create sample data for development"""
    data_dir = project_root / "data"
    logs_dir = data_dir / "logs"
    
    # Ensure directories exist
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Create sample configuration if it doesn't exist
    config_dir = project_root / "config"
    user_config = config_dir / "user_config.yaml"
    
    if not user_config.exists():
        print("Creating sample user configuration...")
        sample_config = """
# Sample user configuration
app:
  debug: true

logging:
  level: DEBUG
  console_output: true

ui:
  auto_refresh_interval: 3
"""
        with open(user_config, 'w') as f:
            f.write(sample_config.strip())
        print("✓ Sample user configuration created")
    
    print("✓ Sample data structure created")


def run_tests(project_root):
    """Run basic tests to verify setup"""
    venv_path = project_root / "venv"
    
    # Determine pytest path based on OS
    if os.name == 'nt':  # Windows
        pytest_path = venv_path / "Scripts" / "pytest"
    else:  # Unix-like
        pytest_path = venv_path / "bin" / "pytest"
    
    print("Running basic tests...")
    if run_command(f"{pytest_path} tests/ -v", check=False):
        print("✓ Tests passed")
        return True
    else:
        print("⚠ Some tests failed (this might be expected in early development)")
        return True  # Don't fail setup for test failures


def print_next_steps(project_root):
    """Print next steps for the developer"""
    venv_path = project_root / "venv"
    
    if os.name == 'nt':  # Windows
        activate_script = venv_path / "Scripts" / "activate.bat"
        python_path = venv_path / "Scripts" / "python"
    else:  # Unix-like
        activate_script = venv_path / "bin" / "activate"
        python_path = venv_path / "bin" / "python"
    
    print("\n" + "="*60)
    print("🎉 Development environment setup complete!")
    print("="*60)
    print("\nNext steps:")
    print(f"1. Activate virtual environment:")
    if os.name == 'nt':
        print(f"   {activate_script}")
    else:
        print(f"   source {activate_script}")
    
    print(f"\n2. Run the application:")
    print(f"   {python_path} src/main.py")
    
    print(f"\n3. Run tests:")
    print(f"   {python_path} -m pytest tests/")
    
    print(f"\n4. Format code:")
    print(f"   {python_path} -m black src/ tests/")
    
    print(f"\n5. Check code quality:")
    print(f"   {python_path} -m flake8 src/ tests/")
    
    print("\nProject structure:")
    print("├── src/           # Source code")
    print("├── tests/         # Test files")
    print("├── config/        # Configuration files")
    print("├── data/          # Data and logs")
    print("├── docs/          # Documentation")
    print("└── scripts/       # Utility scripts")
    
    print("\nHappy coding! 🚀")


def main():
    """Main setup function"""
    print("n8n Management App - Development Environment Setup")
    print("="*50)
    
    # Get project root
    project_root = Path(__file__).parent.parent
    print(f"Project root: {project_root}")
    
    # Check prerequisites
    if not check_python_version():
        sys.exit(1)
    
    docker_available = check_docker()
    if not docker_available:
        print("⚠ Docker is not available. The application will not work without Docker.")
        response = input("Continue setup anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Setup steps
    steps = [
        ("Creating virtual environment", lambda: create_virtual_environment(project_root)),
        ("Installing dependencies", lambda: install_dependencies(project_root)),
        ("Setting up pre-commit hooks", lambda: setup_pre_commit_hooks(project_root)),
        ("Creating sample data", lambda: create_sample_data(project_root)),
        ("Running tests", lambda: run_tests(project_root)),
    ]
    
    failed_steps = []
    
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        if not step_func():
            failed_steps.append(step_name)
    
    if failed_steps:
        print(f"\n⚠ Some steps failed: {', '.join(failed_steps)}")
        print("You may need to resolve these issues manually.")
    
    print_next_steps(project_root)


if __name__ == "__main__":
    main()