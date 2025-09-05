#!/usr/bin/env python3
"""
Comprehensive test runner script for the Telegram bot.

This script runs various types of tests and quality checks:
- Unit tests with coverage
- Integration tests
- Code style checks
- Type checking
- Security analysis
- Performance benchmarks

Usage:
    python scripts/run_tests.py [options]
    
Options:
    --unit              Run unit tests only
    --integration       Run integration tests only
    --coverage          Run tests with coverage report
    --lint              Run code style checks only
    --security          Run security analysis only
    --quick             Run a quick subset of tests
    --all               Run all tests and checks (default)
    --parallel          Run tests in parallel
    --benchmark         Run performance benchmarks
"""

import argparse
import asyncio
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
import json


class TestRunner:
    """Comprehensive test runner for the Telegram bot."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results = {}
        
    def run_command(self, command: List[str], description: str) -> bool:
        """Run a command and track results."""
        print(f"\n🔄 {description}...")
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            duration = time.time() - start_time
            self.results[description] = {
                'status': 'PASSED',
                'duration': duration,
                'output': result.stdout
            }
            
            print(f"✅ {description} passed ({duration:.2f}s)")
            return True
            
        except subprocess.CalledProcessError as e:
            duration = time.time() - start_time
            self.results[description] = {
                'status': 'FAILED',
                'duration': duration,
                'output': e.stdout,
                'error': e.stderr
            }
            
            print(f"❌ {description} failed ({duration:.2f}s)")
            if e.stdout:
                print("STDOUT:", e.stdout)
            if e.stderr:
                print("STDERR:", e.stderr)
            return False
    
    def run_unit_tests(self, with_coverage: bool = False) -> bool:
        """Run unit tests."""
        command = ["python", "-m", "pytest", "tests/unit/", "-v"]
        
        if with_coverage:
            command.extend([
                "--cov=bot",
                "--cov-report=html:htmlcov",
                "--cov-report=xml",
                "--cov-report=term-missing"
            ])
            
        return self.run_command(command, "Unit Tests")
    
    def run_integration_tests(self) -> bool:
        """Run integration tests."""
        command = ["python", "-m", "pytest", "tests/integration/", "-v"]
        return self.run_command(command, "Integration Tests")
    
    def run_lint_checks(self) -> bool:
        """Run code style and formatting checks."""
        checks = [
            (["ruff", "check", "."], "Ruff Linting"),
            (["ruff", "format", "--check", "."], "Ruff Formatting"),
            (["black", "--check", "."], "Black Formatting"),
        ]
        
        results = []
        for command, description in checks:
            try:
                results.append(self.run_command(command, description))
            except Exception:
                # Some tools might not be installed
                print(f"⚠️  {description} skipped (tool not installed)")
                
        return all(results)
    
    def run_type_checks(self) -> bool:
        """Run type checking."""
        command = ["mypy", "bot/", "--ignore-missing-imports", "--no-error-summary"]
        return self.run_command(command, "Type Checking")
    
    def run_security_analysis(self) -> bool:
        """Run security analysis."""
        checks = [
            (["bandit", "-r", "bot/", "-f", "json", "-o", "bandit-report.json"], "Bandit Security Analysis"),
            (["safety", "check", "--file", "requirements.txt"], "Safety Dependency Check"),
        ]
        
        results = []
        for command, description in checks:
            try:
                # Allow these to "fail" as they might find issues
                result = self.run_command(command, description)
                results.append(True)  # We ran it successfully
            except Exception:
                print(f"⚠️  {description} skipped (tool not installed)")
                
        return True  # Don't fail the build on security warnings
    
    def run_performance_benchmarks(self) -> bool:
        """Run performance benchmarks."""
        print("\n🔄 Running performance benchmarks...")
        
        # Create a simple benchmark script
        benchmark_script = """
import asyncio
import time
from bot.services.synonym_service import SynonymService
from bot.services.activity_service import ActivityService

async def benchmark_synonym_service():
    service = SynonymService()
    
    start_time = time.time()
    
    # Benchmark adding synonyms
    for i in range(100):
        await service.add_synonym(f'word{i}', f'synonym{i}', 123, 456)
    
    # Benchmark searching
    for i in range(20):
        await service.search_synonyms('word')
    
    duration = time.time() - start_time
    print(f"Synonym service benchmark: {duration:.3f}s for 100 inserts + 20 searches")

async def main():
    await benchmark_synonym_service()

if __name__ == "__main__":
    asyncio.run(main())
"""
        
        # Write and run benchmark
        benchmark_file = self.project_root / "benchmark_temp.py"
        try:
            with open(benchmark_file, 'w') as f:
                f.write(benchmark_script)
            
            return self.run_command(["python", "benchmark_temp.py"], "Performance Benchmarks")
        finally:
            if benchmark_file.exists():
                benchmark_file.unlink()
    
    def generate_report(self):
        """Generate and save test report."""
        total_duration = sum(r['duration'] for r in self.results.values())
        passed_count = sum(1 for r in self.results.values() if r['status'] == 'PASSED')
        failed_count = len(self.results) - passed_count
        
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_duration': total_duration,
            'passed': passed_count,
            'failed': failed_count,
            'results': self.results
        }
        
        # Save detailed report
        report_file = self.project_root / "test-report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total Duration: {total_duration:.2f}s")
        print(f"Passed: {passed_count}")
        print(f"Failed: {failed_count}")
        
        if failed_count == 0:
            print(f"🎉 All tests passed!")
            return True
        else:
            print(f"💥 {failed_count} test(s) failed")
            return False


def main():
    parser = argparse.ArgumentParser(description='Run comprehensive tests for the Telegram bot')
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--coverage', action='store_true', help='Run tests with coverage report')
    parser.add_argument('--lint', action='store_true', help='Run code style checks only')
    parser.add_argument('--security', action='store_true', help='Run security analysis only')
    parser.add_argument('--type-check', action='store_true', help='Run type checking only')
    parser.add_argument('--benchmark', action='store_true', help='Run performance benchmarks')
    parser.add_argument('--quick', action='store_true', help='Run a quick subset of tests')
    parser.add_argument('--all', action='store_true', help='Run all tests and checks (default)')
    parser.add_argument('--parallel', action='store_true', help='Run tests in parallel')
    
    args = parser.parse_args()
    
    # Default to --all if no specific options given
    if not any([args.unit, args.integration, args.lint, args.security, 
                args.type_check, args.benchmark, args.quick]):
        args.all = True
    
    runner = TestRunner()
    success = True
    
    print("🚀 Starting comprehensive test suite...")
    
    if args.quick:
        # Quick mode: just unit tests and basic linting
        success &= runner.run_unit_tests()
        success &= runner.run_lint_checks()
    
    elif args.unit:
        success &= runner.run_unit_tests(with_coverage=args.coverage)
    
    elif args.integration:
        success &= runner.run_integration_tests()
    
    elif args.lint:
        success &= runner.run_lint_checks()
    
    elif args.security:
        success &= runner.run_security_analysis()
    
    elif args.type_check:
        success &= runner.run_type_checks()
    
    elif args.benchmark:
        success &= runner.run_performance_benchmarks()
    
    elif args.all:
        # Run everything
        success &= runner.run_lint_checks()
        success &= runner.run_type_checks()
        success &= runner.run_unit_tests(with_coverage=True)
        success &= runner.run_integration_tests()
        success &= runner.run_security_analysis()
        success &= runner.run_performance_benchmarks()
    
    # Generate final report
    final_success = runner.generate_report()
    
    if final_success and success:
        print("\n🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()