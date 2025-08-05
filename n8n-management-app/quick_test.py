#!/usr/bin/env python3
"""
Quick Test Execution - Demonstrates core testing capabilities
Runs essential tests without external dependencies
"""

import sys
import os
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all core modules can be imported"""
    print("🔍 Testing module imports...")
    
    try:
        from main import N8nManagementApp, create_argument_parser
        print("   ✅ Main application module imported successfully")
        
        from core.config_manager import ConfigManager
        print("   ✅ Configuration manager imported successfully")
        
        from core.database import setup_database
        print("   ✅ Database module imported successfully")
        
        return True
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False

def test_argument_parsing():
    """Test CLI argument parsing"""
    print("🔍 Testing CLI argument parsing...")
    
    try:
        from main import create_argument_parser
        
        parser = create_argument_parser()
        
        # Test various argument combinations
        test_cases = [
            (['--cli', 'list'], {'cli': True, 'command': 'list'}),
            (['--cli', 'create', '--name', 'test'], {'cli': True, 'command': 'create', 'name': 'test'}),
            (['--debug'], {'debug': True}),
        ]
        
        for args_list, expected in test_cases:
            args = parser.parse_args(args_list)
            for key, value in expected.items():
                if getattr(args, key) != value:
                    raise AssertionError(f"Expected {key}={value}, got {getattr(args, key)}")
        
        print("   ✅ CLI argument parsing working correctly")
        return True
    except Exception as e:
        print(f"   ❌ CLI parsing failed: {e}")
        return False

def test_application_structure():
    """Test application class structure"""
    print("🔍 Testing application structure...")
    
    try:
        from main import N8nManagementApp
        
        app = N8nManagementApp()
        
        # Test basic attributes
        assert hasattr(app, 'config_dir')
        assert hasattr(app, 'db_path')
        assert hasattr(app, 'running')
        assert hasattr(app, 'initialize')
        assert hasattr(app, 'run_cli')
        assert hasattr(app, 'run_gui')
        assert hasattr(app, 'shutdown')
        
        # Test initial state
        assert app.running is False
        assert app.config_dir is None
        assert app.db_path is None
        
        print("   ✅ Application structure is correct")
        return True
    except Exception as e:
        print(f"   ❌ Application structure test failed: {e}")
        return False

def test_configuration_basic():
    """Test basic configuration functionality"""
    print("🔍 Testing configuration management...")
    
    try:
        from core.config_manager import ConfigManager
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Test that config manager initializes
            assert config_manager is not None
            
            # Test basic get/set operations
            config_manager.set('test.key', 'test_value')
            value = config_manager.get('test.key')
            assert value == 'test_value'
            
        print("   ✅ Configuration management working correctly")
        return True
    except Exception as e:
        print(f"   ❌ Configuration test failed: {e}")
        return False

def test_gui_availability():
    """Test GUI framework availability"""
    print("🔍 Testing GUI framework availability...")
    
    try:
        import tkinter as tk
        
        # Test basic GUI creation
        root = tk.Tk()
        root.withdraw()  # Hide window
        
        # Test basic components
        frame = tk.Frame(root)
        label = tk.Label(frame, text="Test")
        button = tk.Button(frame, text="Test")
        
        assert frame is not None
        assert label is not None
        assert button is not None
        
        root.destroy()
        
        print("   ✅ GUI framework available and functional")
        return True
    except Exception as e:
        print(f"   ❌ GUI test failed: {e}")
        return False

def test_performance_basic():
    """Test basic performance characteristics"""
    print("🔍 Testing basic performance...")
    
    try:
        from core.config_manager import ConfigManager
        import tempfile
        
        start_time = time.time()
        
        # Perform operations
        for i in range(5):
            with tempfile.TemporaryDirectory() as temp_dir:
                config_manager = ConfigManager(temp_dir)
                config_manager.set(f'test.key{i}', f'value{i}')
                value = config_manager.get(f'test.key{i}')
                assert value == f'value{i}'
        
        duration = time.time() - start_time
        
        # Should complete quickly
        assert duration < 2.0, f"Operations too slow: {duration:.2f}s"
        
        print(f"   ✅ Performance acceptable: {duration:.3f}s for 5 operations")
        return True
    except Exception as e:
        print(f"   ❌ Performance test failed: {e}")
        return False

def main():
    """Run quick tests"""
    print("🚀 Quick Test Execution for n8n Management App")
    print("=" * 60)
    
    tests = [
        ("Module Imports", test_imports),
        ("CLI Argument Parsing", test_argument_parsing),
        ("Application Structure", test_application_structure),
        ("Configuration Management", test_configuration_basic),
        ("GUI Framework", test_gui_availability),
        ("Basic Performance", test_performance_basic),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            failed += 1
        print()
    
    print("=" * 60)
    print("📊 QUICK TEST SUMMARY")
    print("=" * 60)
    
    total = passed + failed
    success_rate = (passed / total * 100) if total > 0 else 0
    
    status_icon = "✅" if failed == 0 else "❌"
    print(f"{status_icon} Overall Status: {'PASSED' if failed == 0 else 'FAILED'}")
    print(f"📊 Total Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {success_rate:.1f}%")
    
    print("\n🎯 Test Coverage:")
    print("   • Core module imports and availability")
    print("   • CLI argument parsing and validation")
    print("   • Application structure and initialization")
    print("   • Configuration management functionality")
    print("   • GUI framework availability")
    print("   • Basic performance characteristics")
    
    print("\n✨ Testing Capabilities Demonstrated:")
    print("   • Automated test execution")
    print("   • Exception handling and validation")
    print("   • Temporary environment management")
    print("   • Performance benchmarking")
    print("   • Cross-platform compatibility")
    print("   • Comprehensive result reporting")
    
    return 0 if failed == 0 else 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)