# Test Suite Documentation

This document provides a comprehensive guide to the test suite for the Semi-AutoMigration Windows-to-Linux project.

## Test Organization

The test suite is organized into the following categories:

```
tests/
├── conftest.py                  # Shared fixtures and configuration
├── test_unit/                   # Unit tests for individual components
│   ├── __init__.py
│   ├── test_config_schema.py   # Configuration schema validation
│   ├── test_state.py           # UI state management
│   ├── test_error_handling.py  # Error handling and edge cases
│   └── test_validators.py      # Input validation
├── test_integration/            # Integration tests
│   ├── __init__.py
│   ├── test_configuration.py   # Configuration loading and validation
│   ├── test_state_management.py # State management workflows
│   ├── test_service_api.py     # Service APIs and interactions
│   └── test_workflows.py       # Complete workflows
├── test_e2e/                    # End-to-end tests
│   ├── __init__.py
│   ├── test_workflows.py       # User workflow scenarios
│   └── test_migration_flow.py  # Complete migration flow
├── test_ui/                     # UI component tests
│   ├── __init__.py
│   └── test_components.py      # UI page components
├── test_performance/            # Performance and scalability tests
│   ├── __init__.py
│   └── test_performance.py     # Performance benchmarks
└── README.md                    # This file
```

## Test Categories

### Unit Tests (`test_unit/`)

Unit tests focus on individual components in isolation.

**test_config_schema.py**
- Configuration dataclass validation
- Field type checking
- Default value verification
- Schema completeness

**test_state.py**
- State initialization
- State mutation
- Field defaults
- State isolation

**test_error_handling.py**
- Invalid input handling
- Configuration errors
- Missing required fields
- Type validation errors
- Edge cases (special characters, unicode, etc.)

**test_validators.py**
- Input validation rules
- Path validation
- Configuration value validation

### Integration Tests (`test_integration/`)

Integration tests verify how components work together.

**test_configuration.py**
- Configuration loading from files
- Configuration validation
- Configuration structure
- Optional sections handling

**test_state_management.py**
- State initialization with defaults
- State mutation patterns
- State isolation between instances
- Custom paths management
- Error tracking
- Score tracking

**test_service_api.py**
- Migration service interface
- Restore service interface
- Inventory service interface
- Analysis service interface
- Data flow between services
- Configuration propagation

### End-to-End Tests (`test_e2e/`)

E2E tests verify complete user workflows.

**test_workflows.py**
- Mode selection workflows
- Inventory scan workflows
- Recommendation strategy selection
- Full workflow sequences
- State isolation in workflows
- Presenter signal flow

### UI Component Tests (`test_ui/`)

UI tests verify page components and navigation.

**test_components.py**
- Welcome page
- Mode selection page
- Inventory page
- Analysis page
- Summary page
- Validation page
- Preferences page
- Backup/Restore pages
- Finish page
- Page navigation
- Signal emissions

### Performance Tests (`test_performance/`)

Performance tests verify system efficiency and scalability.

**test_performance.py**
- Configuration loading performance
- State update performance
- Service throughput
- UI responsiveness
- Memory efficiency
- Scalability with many items
- Concurrent access patterns

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

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

### Run Specific Test Files

```bash
pytest tests/test_unit/test_config_schema.py
pytest tests/test_integration/test_configuration.py
```

### Run Specific Test Classes

```bash
pytest tests/test_unit/test_error_handling.py::TestConfigurationErrorHandling
pytest tests/test_integration/test_state_management.py::TestStateManagement
```

### Run Specific Tests

```bash
pytest tests/test_unit/test_error_handling.py::TestConfigurationErrorHandling::test_missing_config_file
```

### Run with Verbose Output

```bash
pytest -v
pytest -vv  # Even more verbose
```

### Run with Coverage Report

```bash
pytest --cov=src --cov-report=html
```

### Run with Markers

```bash
# Run only fast tests (if marked)
pytest -m fast

# Run only integration tests
pytest -m integration
```

### Run in Parallel

```bash
pytest -n auto  # Requires pytest-xdist
```

## Fixtures

Common fixtures are defined in `conftest.py` and are automatically available to all tests.

### State Fixtures

- `ui_state`: Fresh QtUiState instance
- `mock_state`: Mocked QtUiState for advanced testing

### Configuration Fixtures

- `mock_config`: Mock MigrationConfigRoot configuration
- `temp_config_file`: Temporary YAML config file

### Service Fixtures

- `mock_migration_service`: Mocked migration service
- `mock_restore_service`: Mocked restore service
- `mock_inventory_service`: Mocked inventory service

### UI Fixtures

- `mock_page`: Mock page widget
- `mock_presenter`: Mock presenter

### Callback Fixtures

- `mock_inventory_callback`: Mock inventory callback
- `mock_recommendations_callback`: Mock recommendations callback

### Data Fixtures

- `mock_backup_manifest`: Sample backup manifest data
- `sample_inventory_data`: Sample inventory data

### Parametrized Fixtures

- `migration_mode`: Parametrized migration modes
- `linux_distro`: Parametrized Linux distributions
- `swap_size_gb`: Parametrized swap sizes

## Helper Classes

### ConfigAssertions

Helper class for configuration assertions:
- `assert_config_valid(config)`: Verify all required sections exist
- `assert_config_section(config, section_name)`: Verify specific section

### StateAssertions

Helper class for state assertions:
- `assert_valid_mode(state, mode)`: Verify mode is valid
- `assert_completion_flags(state)`: Verify completion flags are boolean

### ServiceAssertions

Helper class for service assertions:
- `assert_service_initialized(service)`: Verify service is initialized
- `assert_backup_manifest_valid(manifest)`: Verify manifest structure

## Test Naming Conventions

Tests follow the convention:
- Test functions start with `test_`
- Test classes start with `Test`
- Describe what is being tested clearly
- Use underscores to separate words

Example:
```python
class TestConfigurationLoading:
    def test_load_config_with_valid_yaml(self):
        """Test loading a valid YAML configuration."""
```

## Best Practices

### 1. Use Fixtures

```python
def test_something(ui_state, mock_config):
    # Use fixtures instead of creating objects
    assert ui_state is not None
```

### 2. One Assertion Per Test (When Possible)

```python
def test_config_name(mock_config):
    """Test that config has correct name."""
    assert mock_config.project.name == "Test Migration"

def test_config_version(mock_config):
    """Test that config has correct version."""
    assert mock_config.project.version == "1.0.0"
```

### 3. Use Descriptive Test Names

```python
# Good
def test_state_mutation_updates_mode():
    pass

# Bad
def test_state():
    pass
```

### 4. Test Error Cases

```python
def test_invalid_input_raises_error():
    """Test that invalid input raises appropriate error."""
    with pytest.raises(ValueError):
        some_function(invalid_input)
```

### 5. Use Parametrization for Multiple Cases

```python
@pytest.mark.parametrize("mode", ["guided", "balanced", "expert"])
def test_all_modes_are_valid(mode, ui_state):
    """Test that all migration modes are valid."""
    presenter.set_mode(mode)
    assert presenter.on_page_before_next() is True
```

## Coverage Goals

Target coverage for each module:
- Core business logic: >90%
- UI components: >70%
- Configuration: >95%
- Error handling: >85%
- Services: >80%

Current coverage can be checked with:
```bash
pytest --cov=src --cov-report=html
```

## Continuous Integration

Tests run automatically on:
- Push to main branch
- Pull requests
- Scheduled daily runs

## Troubleshooting

### Import Errors

If you get import errors, ensure the project root is in PYTHONPATH:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### Qt/PyQt5 Issues

Some tests may require X11 display or Qt virtual framebuffer:
```bash
QT_QPA_PLATFORM=offscreen pytest
```

### Fixture Not Found

Ensure fixtures are defined in `conftest.py` or in the same module.

## Contributing

When adding new tests:

1. Follow the directory structure
2. Use existing fixtures where possible
3. Add docstrings to test functions
4. Keep tests focused and readable
5. Update this documentation

## Contact

For questions about tests, contact the development team.
