#!/bin/bash

# Run comprehensive test suite for the Telegram bot

set -e  # Exit on any error

echo "🧪 Running Telegram Bot Test Suite"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" != "" ]]; then
    print_status "Virtual environment detected: $(basename $VIRTUAL_ENV)"
else
    print_warning "No virtual environment detected. Consider using one."
fi

# Check if required packages are installed
print_status "Checking dependencies..."
python -m pip list | grep -E "(pytest|pytest-cov|pytest-asyncio)" > /dev/null || {
    print_error "Required testing packages not found. Installing..."
    pip install pytest pytest-cov pytest-asyncio pytest-mock
}

# Run code formatting check
print_status "Checking code formatting..."
if command -v black &> /dev/null; then
    black --check bot/ tests/ || {
        print_warning "Code formatting issues found. Run 'black bot/ tests/' to fix."
    }
else
    print_warning "Black not found. Install with 'pip install black'"
fi

# Run import sorting check
print_status "Checking import sorting..."
if command -v isort &> /dev/null; then
    isort --check-only bot/ tests/ || {
        print_warning "Import sorting issues found. Run 'isort bot/ tests/' to fix."
    }
else
    print_warning "isort not found. Install with 'pip install isort'"
fi

# Run linting
print_status "Running linting checks..."
if command -v flake8 &> /dev/null; then
    flake8 bot/ tests/ --max-line-length=88 --extend-ignore=E203,W503 || {
        print_error "Linting issues found. Please fix before running tests."
        exit 1
    }
else
    print_warning "flake8 not found. Install with 'pip install flake8'"
fi

# Run type checking
print_status "Running type checks..."
if command -v mypy &> /dev/null; then
    mypy bot/ --ignore-missing-imports || {
        print_warning "Type checking issues found. Consider fixing them."
    }
else
    print_warning "mypy not found. Install with 'pip install mypy'"
fi

# Run security checks
print_status "Running security checks..."
if command -v bandit &> /dev/null; then
    bandit -r bot/ -f json -o bandit-report.json || {
        print_warning "Security issues found. Check bandit-report.json"
    }
else
    print_warning "bandit not found. Install with 'pip install bandit'"
fi

# Set environment variables for testing
export ENVIRONMENT=testing
export LOG_LEVEL=ERROR
export TELEGRAM_BOT_TOKEN=test_token
export OPENAI_API_KEY=test_openai_key

# Run unit tests
print_status "Running unit tests..."
pytest tests/unit/ -v --tb=short || {
    print_error "Unit tests failed!"
    exit 1
}

print_success "Unit tests passed!"

# Run integration tests
print_status "Running integration tests..."
pytest tests/integration/ -v --tb=short || {
    print_error "Integration tests failed!"
    exit 1
}

print_success "Integration tests passed!"

# Run all tests with coverage
print_status "Running full test suite with coverage..."
pytest tests/ \
    --cov=bot \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-fail-under=80 \
    -v || {
    print_error "Test coverage below threshold!"
    exit 1
}

print_success "All tests passed with adequate coverage!"

# Generate coverage badge (if coverage-badge is installed)
if command -v coverage-badge &> /dev/null; then
    print_status "Generating coverage badge..."
    coverage-badge -o coverage.svg
    print_success "Coverage badge generated: coverage.svg"
fi

# Run performance tests (if they exist)
if [ -d "tests/performance" ]; then
    print_status "Running performance tests..."
    pytest tests/performance/ -v || {
        print_warning "Performance tests failed or didn't meet benchmarks"
    }
fi

# Clean up
print_status "Cleaning up test artifacts..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name ".coverage" -delete 2>/dev/null || true

echo ""
echo "=================================="
print_success "🎉 All tests completed successfully!"
echo "📊 Coverage report available in htmlcov/index.html"
echo "🔒 Security report available in bandit-report.json"
echo "=================================="