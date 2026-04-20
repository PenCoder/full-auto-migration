# Test Quick Reference Guide

Quick reference for running and managing tests in the Semi-AutoMigration project.

## Installation

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Or install pytest specifically
pip install pytest pytest-cov pytest-xdist pytest-mock
```

## Quick Start

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src --cov-report=html
```

## Run Specific Tests

### By Category

```bash
# Unit tests only
pytest tests/test_unit/

# Integration tests only
pytest tests/test_integration/

# E2E tests only
pytest tests/test_e2e/

# UI tests only
pytest tests/test_ui/

# Performance tests only
pytest tests/test_performance/
```

### By Component

```bash
# Configuration tests
pytest tests/ -k "config"

# State tests
pytest tests/ -k "state"

# Service tests
pytest tests/ -k "service"

# Error handling tests
pytest tests/ -k "error"
```

### By Test File

```bash
pytest tests/test_unit/test_error_handling.py
pytest tests/test_integration/test_configuration.py
pytest tests/test_e2e/test_workflows.py
```

### By Test Class

```bash
pytest tests/test_unit/test_error_handling.py::TestConfigurationErrorHandling
pytest tests/test_integration/test_state_management.py::TestStateManagement
```

### By Test Function

```bash
pytest tests/test_unit/test_error_handling.py::TestConfigurationErrorHandling::test_missing_config_file
```

## Output Options

```bash
# Quiet mode (only show failures)
pytest -q

# Verbose mode (show test names and results)
pytest -v

# Very verbose (show test docstrings and parameters)
pytest -vv

# Show local variables in failures
pytest -l

# Show slowest tests
pytest --durations=10

# Show summary of test results
pytest -ra

# Short traceback format
pytest --tb=short

# Full traceback format
pytest --tb=long

# No traceback (just pass/fail)
pytest --tb=no
```

## Coverage Reports

```bash
# Generate coverage report in terminal
pytest --cov=src

# Generate HTML coverage report
pytest --cov=src --cov-report=html

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows

# Coverage report with missing lines shown
pytest --cov=src --cov-report=term-missing

# Combined coverage report
pytest --cov=src --cov-report=html --cov-report=term-missing
```

## Parallel Execution

```bash
# Run tests in parallel (requires pytest-xdist)
pytest -n auto  # Auto-detect number of CPUs

# Run with specific number of workers
pytest -n 4

# Run with distribution strategy
pytest -n auto -dist loadscope
```

## Watch Mode

```bash
# Run tests on file changes (requires pytest-watch)
ptw

# Run tests on file changes with specific path
ptw tests/test_unit/

# Run tests on file changes with coverage
ptw -- --cov=src
```

## Filtering Tests

```bash
# Run only passing tests from last run
pytest --lf

# Run tests that failed last time first, then others
pytest --ff

# Run only tests matching expression
pytest -k "config and not error"

# Run only tests with specific marker
pytest -m unit

# Run all except specific marker
pytest -m "not performance"

# Run only tests in specific module
pytest tests/test_unit/test_config_schema.py
```

## Test Markers

```bash
# Run unit tests
pytest -m unit

# Run integration tests
pytest -m integration

# Run E2E tests
pytest -m e2e

# Run UI tests
pytest -m ui

# Run performance tests
pytest -m performance

# Run fast tests
pytest -m fast

# Run slow tests
pytest -m slow

# Exclude slow tests
pytest -m "not slow"
```

## Debugging

```bash
# Stop on first failure
pytest -x

# Stop after N failures
pytest --maxfail=3

# Show print statements
pytest -s

# Debug with pdb (Python debugger)
pytest --pdb

# Drop into debugger on error
pytest -x --pdb

# Drop into debugger at start
pytest --trace

# Capture output (show print statements)
pytest -s
```

## Test Configuration

### pytest.ini

Configuration file for pytest. See `pytest.ini` in project root.

```bash
# Use specific pytest config
pytest -c pytest.ini

# Show current configuration
pytest --co
```

## Environment Variables

```bash
# Run tests with specific environment
QT_QPA_PLATFORM=offscreen pytest  # For Qt tests without display

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest

# Run with debug logging
PYTEST_DEBUG=1 pytest
```

## Common Tasks

### Run tests before commit

```bash
pytest tests/test_unit/ --cov=src -q
```

### Run tests for pull request

```bash
pytest tests/ --cov=src --cov-report=html -v
```

### Run tests in CI/CD

```bash
pytest tests/ \
  --cov=src \
  --cov-report=html \
  --cov-report=xml \
  -v \
  --tb=short
```

### Generate test report

```bash
pytest tests/ \
  --html=report.html \
  --self-contained-html \
  -v
```

### Performance benchmark

```bash
pytest tests/test_performance/ \
  --benchmark-only \
  -v
```

## Troubleshooting

### ImportError: No module named 'src'

**Solution**: Add project root to PYTHONPATH

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### Qt/PyQt5 errors

**Solution**: Use virtual display for Qt tests

```bash
QT_QPA_PLATFORM=offscreen pytest
```

### Pytest not found

**Solution**: Install test requirements

```bash
pip install -r requirements-test.txt
```

### Tests running slowly

**Solution**: Run in parallel with pytest-xdist

```bash
pytest -n auto
```

### Flaky tests (intermittent failures)

**Solution**: Run tests repeatedly

```bash
pytest --count=10  # Requires pytest-repeat
```

### Can't find conftest.py

**Solution**: Run pytest from project root

```bash
cd /path/to/Semi-AutoMigration-Win-to-Lin
pytest
```

### Coverage report is empty

**Solution**: Ensure tests actually execute code

```bash
pytest --cov=src --cov-report=term-missing
```

## Performance Tips

1. **Use `-n auto`** for parallel execution on multi-core systems
2. **Run `-x`** to stop on first failure during development
3. **Use `-k` filter** to run only relevant tests
4. **Mock external dependencies** to speed up tests
5. **Use fixtures** to avoid redundant setup

## Best Practices

### Before Each Test Run

```bash
# Ensure dependencies are installed
pip install -r requirements-test.txt

# Navigate to project root
cd /path/to/project
```

### During Development

```bash
# Run unit tests frequently
pytest tests/test_unit/ -q

# Run tests on file changes
ptw
```

### Before Commit

```bash
# Run all tests with coverage
pytest --cov=src --cov-report=html -v

# Check coverage threshold
pytest --cov=src --cov-fail-under=80
```

### For CI/CD

```bash
# Run all tests with all reports
pytest tests/ \
  --cov=src \
  --cov-report=html \
  --cov-report=xml \
  --html=report.html \
  --self-contained-html \
  --tb=short \
  -v
```

## Tools and Extensions

### VS Code Extensions

- **Python** (microsoft.python)
- **Pylance** (ms-python.vscode-pylance)
- **Pytest** (littlefoxteam.vscode-python-test-adapter)

### Command Line Tools

- **pytest** - Test runner
- **pytest-cov** - Coverage reporting
- **pytest-xdist** - Parallel execution
- **pytest-watch** - File change watching
- **coverage** - Coverage analysis

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Coverage Documentation](https://coverage.readthedocs.io/)
- [pytest-xdist](https://pytest-xdist.readthedocs.io/)

## Cheat Sheet

```bash
# Most common commands
pytest                          # Run all tests
pytest -v                       # Verbose output
pytest --cov=src               # With coverage
pytest -x                       # Stop on first failure
pytest -k "config"             # Match by name
pytest tests/test_unit/        # Run specific directory
pytest -n auto                 # Parallel execution
pytest --lf                    # Run last failed
pytest --pdb                   # Debug mode
```

## Contact

For test-related questions or issues, contact the development team.
