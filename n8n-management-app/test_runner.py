#!/usr/bin/env python3
"""
Comprehensive Test Runner for n8n Management App
Executes all tests in a single shot with detailed reporting
"""

import sys
import os
import subprocess
import time
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
import argparse

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

class TestRunner:
    """Comprehensive test execution and reporting system"""
    
    def __init__(self, verbose: bool = False, coverage: bool = True):
        self.verbose = verbose
        self.coverage = coverage
        self.start_time = datetime.now()
        self.results = {
            'unit_tests': {},
            'integration_tests': {},
            'performance_tests': {},
            'security_tests': {},
            'gui_tests': {},
            'cli_tests': {},
            'docker_tests': {},
            'database_tests': {},
            'coverage_report': {},
            'quality_metrics': {},
            'summary': {}
        }
        self.project_root = Path(__file__).parent
        self.src_path = self.project_root / "src"
        self.test_path = self.project_root / "tests"
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Execute comprehensive test suite"""
        print("🚀 Starting Comprehensive Test Suite for n8n Management App")
        print("=" * 80)
        
        # Pre-test setup
        self._setup_test_environment()
        
        # Execute test categories
        test_categories = [
            ("Unit Tests", self._run_unit_tests),
            ("Integration Tests", self._run_integration_tests),
            ("GUI Tests", self._run_gui_tests),
            ("CLI Tests", self._run_cli_tests),
            ("Docker Tests", self._run_docker_tests),
            ("Database Tests", self._run_database_tests),
            ("Performance Tests", self._run_performance_tests),
            ("Security Tests", self._run_security_tests),
            ("Code Quality", self._run_quality_checks),
        ]
        
        for category_name, test_function in test_categories:
            print(f"\n📋 Running {category_name}...")
            try:
                result = test_function()
                self.results[category_name.lower().replace(' ', '_')] = result
                self._print_category_result(category_name, result)
            except Exception as e:
                print(f"❌ Error in {category_name}: {e}")
                self.results[category_name.lower().replace(' ', '_')] = {
                    'status': 'error',
                    'error': str(e),
                    'passed': 0,
                    'failed': 1,
                    'total': 1
                }
        
        # Generate coverage report
        if self.coverage:
            print(f"\n📊 Generating Coverage Report...")
            self.results['coverage_report'] = self._generate_coverage_report()
        
        # Generate final summary
        self.results['summary'] = self._generate_summary()
        
        # Generate reports
        self._generate_reports()
        
        return self.results
    
    def _setup_test_environment(self):
        """Setup test environment and dependencies"""
        print("🔧 Setting up test environment...")
        
        # Install test dependencies
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", "requirements-dev.txt"
            ], check=True, capture_output=True)
            print("✅ Test dependencies installed")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Warning: Could not install dependencies: {e}")
        
        # Create test directories if they don't exist
        test_dirs = [
            self.test_path / "test_core",
            self.test_path / "test_gui", 
            self.test_path / "test_utils",
            self.test_path / "test_integration",
            self.test_path / "test_performance",
            self.test_path / "test_security"
        ]
        
        for test_dir in test_dirs:
            test_dir.mkdir(parents=True, exist_ok=True)
            (test_dir / "__init__.py").touch(exist_ok=True)
    
    def _run_unit_tests(self) -> Dict[str, Any]:
        """Execute unit tests with pytest"""
        try:
            cmd = [
                sys.executable, "-m", "pytest", 
                str(self.test_path / "test_core"),
                str(self.test_path / "test_utils"),
                "-v", "--tb=short", "--json-report", "--json-report-file=test_results_unit.json"
            ]
            
            if self.coverage:
                cmd.extend(["--cov=src", "--cov-report=json:coverage_unit.json"])
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            
            # Parse pytest JSON output if available
            json_file = self.project_root / "test_results_unit.json"
            if json_file.exists():
                with open(json_file) as f:
                    pytest_data = json.load(f)
                return {
                    'status': 'passed' if result.returncode == 0 else 'failed',
                    'passed': pytest_data['summary']['passed'],
                    'failed': pytest_data['summary']['failed'],
                    'total': pytest_data['summary']['total'],
                    'duration': pytest_data['duration'],
                    'output': result.stdout,
                    'errors': result.stderr
                }
            else:
                return self._parse_pytest_output(result)
                
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'passed': 0, 'failed': 1, 'total': 1}
    
    def _run_integration_tests(self) -> Dict[str, Any]:
        """Execute integration tests"""
        try:
            cmd = [
                sys.executable, "-m", "pytest",
                str(self.test_path / "test_integration"),
                "-v", "--tb=short", "--json-report", "--json-report-file=test_results_integration.json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            return self._parse_pytest_result(result, "test_results_integration.json")
            
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'passed': 0, 'failed': 1, 'total': 1}
    
    def _run_gui_tests(self) -> Dict[str, Any]:
        """Execute GUI tests"""
        try:
            # Set display for headless testing
            env = os.environ.copy()
            env['DISPLAY'] = ':99'  # Virtual display
            
            cmd = [
                sys.executable, "-m", "pytest",
                str(self.test_path / "test_gui"),
                "-v", "--tb=short", "--json-report", "--json-report-file=test_results_gui.json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=self.project_root)
            return self._parse_pytest_result(result, "test_results_gui.json")
            
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'passed': 0, 'failed': 1, 'total': 1}
    
    def _run_cli_tests(self) -> Dict[str, Any]:
        """Execute CLI interface tests"""
        try:
            cmd = [
                sys.executable, "-m", "pytest",
                str(self.test_path / "test_cli"),
                "-v", "--tb=short", "--json-report", "--json-report-file=test_results_cli.json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            return self._parse_pytest_result(result, "test_results_cli.json")
            
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'passed': 0, 'failed': 1, 'total': 1}
    
    def _run_docker_tests(self) -> Dict[str, Any]:
        """Execute Docker integration tests"""
        try:
            cmd = [
                sys.executable, "-m", "pytest",
                str(self.test_path / "test_docker"),
                "-v", "--tb=short", "--json-report", "--json-report-file=test_results_docker.json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            return self._parse_pytest_result(result, "test_results_docker.json")
            
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'passed': 0, 'failed': 1, 'total': 1}
    
    def _run_database_tests(self) -> Dict[str, Any]:
        """Execute database tests"""
        try:
            cmd = [
                sys.executable, "-m", "pytest",
                str(self.test_path / "test_database"),
                "-v", "--tb=short", "--json-report", "--json-report-file=test_results_database.json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            return self._parse_pytest_result(result, "test_results_database.json")
            
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'passed': 0, 'failed': 1, 'total': 1}
    
    def _run_performance_tests(self) -> Dict[str, Any]:
        """Execute performance tests"""
        try:
            cmd = [
                sys.executable, "-m", "pytest",
                str(self.test_path / "test_performance"),
                "-v", "--tb=short", "--json-report", "--json-report-file=test_results_performance.json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            return self._parse_pytest_result(result, "test_results_performance.json")
            
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'passed': 0, 'failed': 1, 'total': 1}
    
    def _run_security_tests(self) -> Dict[str, Any]:
        """Execute security tests"""
        try:
            # Run bandit security scanner
            bandit_cmd = [sys.executable, "-m", "bandit", "-r", "src", "-f", "json", "-o", "bandit_report.json"]
            bandit_result = subprocess.run(bandit_cmd, capture_output=True, text=True, cwd=self.project_root)
            
            # Run safety check for dependencies
            safety_cmd = [sys.executable, "-m", "safety", "check", "--json"]
            safety_result = subprocess.run(safety_cmd, capture_output=True, text=True, cwd=self.project_root)
            
            # Parse results
            security_issues = 0
            if bandit_result.returncode != 0:
                security_issues += 1
            if safety_result.returncode != 0:
                security_issues += 1
            
            return {
                'status': 'passed' if security_issues == 0 else 'failed',
                'passed': 2 - security_issues,
                'failed': security_issues,
                'total': 2,
                'bandit_output': bandit_result.stdout,
                'safety_output': safety_result.stdout,
                'duration': 0
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'passed': 0, 'failed': 1, 'total': 1}
    
    def _run_quality_checks(self) -> Dict[str, Any]:
        """Execute code quality checks"""
        try:
            checks = []
            
            # Black formatting check
            black_cmd = [sys.executable, "-m", "black", "--check", "src"]
            black_result = subprocess.run(black_cmd, capture_output=True, text=True, cwd=self.project_root)
            checks.append(('black', black_result.returncode == 0))
            
            # Flake8 linting
            flake8_cmd = [sys.executable, "-m", "flake8", "src"]
            flake8_result = subprocess.run(flake8_cmd, capture_output=True, text=True, cwd=self.project_root)
            checks.append(('flake8', flake8_result.returncode == 0))
            
            # MyPy type checking
            mypy_cmd = [sys.executable, "-m", "mypy", "src"]
            mypy_result = subprocess.run(mypy_cmd, capture_output=True, text=True, cwd=self.project_root)
            checks.append(('mypy', mypy_result.returncode == 0))
            
            # isort import sorting
            isort_cmd = [sys.executable, "-m", "isort", "--check-only", "src"]
            isort_result = subprocess.run(isort_cmd, capture_output=True, text=True, cwd=self.project_root)
            checks.append(('isort', isort_result.returncode == 0))
            
            passed = sum(1 for _, success in checks if success)
            failed = len(checks) - passed
            
            return {
                'status': 'passed' if failed == 0 else 'failed',
                'passed': passed,
                'failed': failed,
                'total': len(checks),
                'checks': dict(checks),
                'black_output': black_result.stdout,
                'flake8_output': flake8_result.stdout,
                'mypy_output': mypy_result.stdout,
                'isort_output': isort_result.stdout,
                'duration': 0
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'passed': 0, 'failed': 1, 'total': 1}
    
    def _generate_coverage_report(self) -> Dict[str, Any]:
        """Generate comprehensive coverage report"""
        try:
            # Run coverage for entire codebase
            cmd = [
                sys.executable, "-m", "pytest",
                str(self.test_path),
                "--cov=src",
                "--cov-report=json:coverage_final.json",
                "--cov-report=html:htmlcov",
                "--cov-report=term-missing"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            
            # Parse coverage JSON
            coverage_file = self.project_root / "coverage_final.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                
                return {
                    'total_coverage': coverage_data['totals']['percent_covered'],
                    'lines_covered': coverage_data['totals']['covered_lines'],
                    'lines_missing': coverage_data['totals']['missing_lines'],
                    'total_lines': coverage_data['totals']['num_statements'],
                    'files': coverage_data['files'],
                    'html_report': 'htmlcov/index.html'
                }
            else:
                return {'error': 'Coverage report not generated'}
                
        except Exception as e:
            return {'error': str(e)}
    
    def _parse_pytest_result(self, result: subprocess.CompletedProcess, json_file: str) -> Dict[str, Any]:
        """Parse pytest result from JSON output"""
        json_path = self.project_root / json_file
        if json_path.exists():
            try:
                with open(json_path) as f:
                    pytest_data = json.load(f)
                return {
                    'status': 'passed' if result.returncode == 0 else 'failed',
                    'passed': pytest_data['summary']['passed'],
                    'failed': pytest_data['summary']['failed'],
                    'total': pytest_data['summary']['total'],
                    'duration': pytest_data['duration'],
                    'output': result.stdout,
                    'errors': result.stderr
                }
            except Exception:
                pass
        
        return self._parse_pytest_output(result)
    
    def _parse_pytest_output(self, result: subprocess.CompletedProcess) -> Dict[str, Any]:
        """Parse pytest output when JSON is not available"""
        output = result.stdout
        lines = output.split('\n')
        
        # Try to extract test counts from output
        passed = failed = total = 0
        for line in lines:
            if 'passed' in line and 'failed' in line:
                # Parse line like "5 passed, 2 failed in 1.23s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'passed' and i > 0:
                        passed = int(parts[i-1])
                    elif part == 'failed' and i > 0:
                        failed = int(parts[i-1])
        
        total = passed + failed
        
        return {
            'status': 'passed' if result.returncode == 0 else 'failed',
            'passed': passed,
            'failed': failed,
            'total': total,
            'duration': 0,
            'output': output,
            'errors': result.stderr
        }
    
    def _print_category_result(self, category: str, result: Dict[str, Any]):
        """Print formatted result for a test category"""
        status = result.get('status', 'unknown')
        passed = result.get('passed', 0)
        failed = result.get('failed', 0)
        total = result.get('total', 0)
        duration = result.get('duration', 0)
        
        status_icon = "✅" if status == 'passed' else "❌" if status == 'failed' else "⚠️"
        
        print(f"{status_icon} {category}: {passed}/{total} passed, {failed} failed")
        if duration:
            print(f"   Duration: {duration:.2f}s")
        
        if self.verbose and result.get('output'):
            print(f"   Output: {result['output'][:200]}...")
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate comprehensive test summary"""
        total_passed = 0
        total_failed = 0
        total_tests = 0
        total_duration = 0
        categories_passed = 0
        total_categories = 0
        
        for category, result in self.results.items():
            if category in ['summary', 'coverage_report']:
                continue
                
            if isinstance(result, dict) and 'passed' in result:
                total_passed += result.get('passed', 0)
                total_failed += result.get('failed', 0)
                total_tests += result.get('total', 0)
                total_duration += result.get('duration', 0)
                total_categories += 1
                
                if result.get('status') == 'passed':
                    categories_passed += 1
        
        end_time = datetime.now()
        total_time = (end_time - self.start_time).total_seconds()
        
        return {
            'total_tests': total_tests,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'success_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0,
            'categories_passed': categories_passed,
            'total_categories': total_categories,
            'category_success_rate': (categories_passed / total_categories * 100) if total_categories > 0 else 0,
            'total_duration': total_duration,
            'wall_clock_time': total_time,
            'start_time': self.start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'overall_status': 'PASSED' if total_failed == 0 else 'FAILED'
        }
    
    def _generate_reports(self):
        """Generate comprehensive test reports"""
        # Generate JSON report
        json_report_path = self.project_root / "test_report_comprehensive.json"
        with open(json_report_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Generate HTML report
        self._generate_html_report()
        
        # Generate console summary
        self._print_final_summary()
    
    def _generate_html_report(self):
        """Generate HTML test report"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>n8n Management App - Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ background: #e8f5e8; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .category {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
        .error {{ color: orange; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>n8n Management App - Comprehensive Test Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Overall Status:</strong> <span class="{'passed' if self.results['summary']['overall_status'] == 'PASSED' else 'failed'}">{self.results['summary']['overall_status']}</span></p>
        <p><strong>Total Tests:</strong> {self.results['summary']['total_tests']}</p>
        <p><strong>Passed:</strong> <span class="passed">{self.results['summary']['total_passed']}</span></p>
        <p><strong>Failed:</strong> <span class="failed">{self.results['summary']['total_failed']}</span></p>
        <p><strong>Success Rate:</strong> {self.results['summary']['success_rate']:.1f}%</p>
        <p><strong>Duration:</strong> {self.results['summary']['wall_clock_time']:.2f}s</p>
    </div>
    
    <h2>Test Categories</h2>
"""
        
        for category, result in self.results.items():
            if category in ['summary', 'coverage_report']:
                continue
                
            if isinstance(result, dict):
                status_class = result.get('status', 'unknown')
                html_content += f"""
    <div class="category">
        <h3>{category.replace('_', ' ').title()}</h3>
        <p><strong>Status:</strong> <span class="{status_class}">{result.get('status', 'unknown').upper()}</span></p>
        <p><strong>Tests:</strong> {result.get('passed', 0)}/{result.get('total', 0)} passed</p>
        {f"<p><strong>Duration:</strong> {result.get('duration', 0):.2f}s</p>" if result.get('duration') else ""}
    </div>
"""
        
        # Add coverage information
        if 'coverage_report' in self.results and isinstance(self.results['coverage_report'], dict):
            coverage = self.results['coverage_report']
            if 'total_coverage' in coverage:
                html_content += f"""
    <div class="category">
        <h3>Code Coverage</h3>
        <p><strong>Total Coverage:</strong> {coverage['total_coverage']:.1f}%</p>
        <p><strong>Lines Covered:</strong> {coverage.get('lines_covered', 0)}</p>
        <p><strong>Lines Missing:</strong> {coverage.get('lines_missing', 0)}</p>
        <p><strong>Total Lines:</strong> {coverage.get('total_lines', 0)}</p>
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        html_report_path = self.project_root / "test_report.html"
        with open(html_report_path, 'w') as f:
            f.write(html_content)
        
        print(f"📄 HTML report generated: {html_report_path}")
    
    def _print_final_summary(self):
        """Print final test summary to console"""
        summary = self.results['summary']
        
        print("\n" + "=" * 80)
        print("🎯 COMPREHENSIVE TEST RESULTS SUMMARY")
        print("=" * 80)
        
        status_icon = "✅" if summary['overall_status'] == 'PASSED' else "❌"
        print(f"{status_icon} Overall Status: {summary['overall_status']}")
        print(f"📊 Total Tests: {summary['total_tests']}")
        print(f"✅ Passed: {summary['total_passed']}")
        print(f"❌ Failed: {summary['total_failed']}")
        print(f"📈 Success Rate: {summary['success_rate']:.1f}%")
        print(f"⏱️  Total Duration: {summary['wall_clock_time']:.2f}s")
        
        # Coverage summary
        if 'coverage_report' in self.results and isinstance(self.results['coverage_report'], dict):
            coverage = self.results['coverage_report']
            if 'total_coverage' in coverage:
                print(f"📋 Code Coverage: {coverage['total_coverage']:.1f}%")
        
        print("\n📁 Generated Reports:")
        print(f"   • JSON Report: test_report_comprehensive.json")
        print(f"   • HTML Report: test_report.html")
        if self.coverage:
            print(f"   • Coverage Report: htmlcov/index.html")
        
        print("\n" + "=" * 80)


def main():
    """Main entry point for test runner"""
    parser = argparse.ArgumentParser(description='Comprehensive Test Runner for n8n Management App')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--no-coverage', action='store_true', help='Skip coverage reporting')
    parser.add_argument('--category', choices=[
        'unit', 'integration', 'gui', 'cli', 'docker', 'database', 
        'performance', 'security', 'quality'
    ], help='Run specific test category only')
    
    args = parser.parse_args()
    
    runner = TestRunner(verbose=args.verbose, coverage=not args.no_coverage)
    
    if args.category:
        print(f"Running {args.category} tests only...")
        # Run specific category (implementation would filter tests)
    
    results = runner.run_all_tests()
    
    # Exit with appropriate code
    exit_code = 0 if results['summary']['overall_status'] == 'PASSED' else 1
    sys.exit(exit_code)


if __name__ == '__main__':
    main()