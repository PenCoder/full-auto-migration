# Testing Strategy and Guide

This document outlines the comprehensive testing strategy for the Semi-AutoMigration Windows-to-Linux project.

## Testing Philosophy

Our testing approach follows these principles:

1. **Test-Driven Development**: Write tests alongside code
2. **Comprehensive Coverage**: Aim for >90% code coverage on critical paths
3. **Multiple Test Levels**: Unit, integration, E2E, and performance tests
4. **Clear Test Names**: Tests document expected behavior
5. **Maintainability**: Tests are easy to understand and modify
6. **Isolation**: Tests are independent and can run in any order

## Test Pyramid

```
        / \
       /   \    E2E Tests (10%)
      /     \   - Complete workflows
     /-------\  - User scenarios
    /         \
   /           \ Integration Tests (30%)
  /             \ - Component interactions
 /               \ - Service APIs
/-------------------\ 
    Unit Tests (60%)
    - Individual components
    - Validation logic
    - State management
```

## Test Levels

### 1. Unit Tests (60%)

**Focus**: Individual components in isolation

**What to test**:
- Configuration schema validation
- State management
- Utility functions
- Validators
- Error handling

**Tools**: pytest, unittest.mock

**Example**:
```python
def test_config_has_all_required_fields(mock_config):
    """Test that configuration has all required fields."""
    ConfigAssertions.assert_config_valid(mock_config)
```

### 2. Integration Tests (30%)

**Focus**: How components work together

**What to test**:
- Configuration loading and validation
- Service APIs and interactions
- Data flow between components
- State propagation
- Page presenter workflows

**Tools**: pytest, unittest.mock

**Example**:
```python
def test_inventory_to_analysis_flow(mock_inventory_callback):
    """Test data flow from inventory to analysis."""
    inventory_data = mock_inventory_callback()
    analysis_result = analyze_inventory(inventory_data)
    assert analysis_result is not None
```

### 3. End-to-End Tests (10%)

**Focus**: Complete user workflows

**What to test**:
- Full migration workflows
- Multi-step user interactions
- State across multiple pages
- Complete business processes

**Tools**: pytest, PyQt5 (if applicable)

**Example**:
```python
def test_full_migration_workflow(ui_state):
    """Test complete migration workflow from start to finish."""
    # Mode selection
    mode_presenter = ModePresenter(ui_state)
    mode_presenter.set_mode("guided")
    
    # Inventory scan
    scan_presenter = ScanPresenter(ui_state, callback1, callback2)
    # ... continue workflow
```

### 4. Performance Tests (Optional)

**Focus**: System efficiency and scalability

**What to test**:
- Configuration loading speed
- State update performance
- Service throughput
- Memory efficiency
- Scalability with large datasets

**Tools**: pytest, pytest-benchmark

**Example**:
```python
def test_config_loading_performance(benchmark):
    """Test configuration loading performance."""
    result = benchmark(load_config, "config.yaml")
    assert result is not None
```

## Test Organization

### By Component

Tests are organized by the component they test:

```
tests/
├── test_unit/
│   ├── test_config_*.py      # Configuration tests
│   ├── test_state.py         # State tests
│   └── test_error_*.py       # Error handling tests
├── test_integration/
│   ├── test_configuration.py # Config integration
│   ├── test_service_api.py   # Service integration
│   └── test_state_management.py
├── test_e2e/
│   └── test_workflows.py     # Complete workflows
└── test_ui/
    └── test_components.py    # UI components
```

### By Feature

Tests can also be organized by feature:

```
tests/
├── test_configuration/       # All config-related tests
├── test_backup/             # All backup-related tests
├── test_migration/          # All migration-related tests
└── test_restore/            # All restore-related tests
```

## Writing Effective Tests

### 1. Clear Test Names

Test names should describe what is being tested:

```python
# Good
def test_config_loading_with_valid_yaml():
def test_state_updates_mode_when_setter_called():
def test_migration_service_returns_true_on_success():

# Bad
def test_config():
def test_state():
def test_service():
```

### 2. Arrange-Act-Assert Pattern

Structure tests with clear sections:

```python
def test_something(ui_state, mock_config):
    # Arrange - Set up test data
    mode_presenter = ModePresenter(ui_state)
    
    # Act - Perform the action
    mode_presenter.set_mode("expert")
    
    # Assert - Verify the result
    assert ui_state.mode == "expert"
```

### 3. Use Fixtures

Leverage pytest fixtures for reusable test setup:

```python
def test_mode_selection(ui_state, mock_config):
    """Test mode selection uses provided fixtures."""
    presenter = ModePresenter(ui_state)
    assert presenter is not None
```

### 4. Test Error Cases

Always test error handling:

```python
def test_invalid_mode_handling():
    """Test that invalid mode raises error."""
    with pytest.raises(ValueError):
        ModePresenter(None)
```

### 5. Parametrize for Multiple Cases

Use parametrization for testing multiple inputs:

```python
@pytest.mark.parametrize("mode", ["guided", "balanced", "expert"])
def test_all_modes_are_valid(mode, ui_state):
    """Test that all migration modes are valid."""
    presenter = ModePresenter(ui_state)
    presenter.set_mode(mode)
    assert presenter.on_page_before_next() is True
```

## Mocking Strategy

### When to Mock

Mock external dependencies:
- File system operations
- Network calls
- System APIs
- Database operations
- Qt signals/slots

### When NOT to Mock

Test real behavior for:
- Core business logic
- State management
- Configuration validation
- Internal component interactions

### Mocking Example

```python
def test_backup_with_mocked_file_system(mock_migration_service):
    """Test backup using mocked file system."""
    # File system is mocked
    with patch('os.listdir', return_value=['file1.txt']):
        result = mock_migration_service.create_backup(config)
        assert result is True
```

## Coverage Goals

| Component | Target Coverage | Priority |
|-----------|-----------------|----------|
| Configuration | 95% | High |
| State Management | 90% | High |
| Services | 85% | High |
| UI Components | 70% | Medium |
| Error Handling | 85% | High |
| Utilities | 80% | Medium |

## Running Tests in Development

### Quick Test Run

```bash
# Run unit tests quickly
pytest tests/test_unit/ -q
```

### Full Test Run

```bash
# Run all tests with coverage
pytest --cov=src --cov-report=html
```

### Test Specific Component

```bash
# Test configuration
pytest tests/ -k "config"

# Test state management
pytest tests/ -k "state"
```

### Watch Mode

```bash
# Run tests on file changes (requires pytest-watch)
ptw
```

## Continuous Integration

Tests run automatically in CI/CD pipeline:

1. **Pre-commit**: Quick unit tests
2. **Pull Request**: Full test suite + coverage
3. **Merge**: Integration and E2E tests
4. **Release**: Performance tests + regression tests

## Test Maintenance

### Regular Updates

- Update tests when requirements change
- Remove obsolete tests
- Refactor duplicate test code
- Keep fixtures fresh

### Common Issues

| Issue | Solution |
|-------|----------|
| Slow tests | Use mocks, parallelize with pytest-xdist |
| Flaky tests | Add timeouts, fix race conditions |
| Hard to read | Improve naming, break into smaller tests |
| Too many mocks | Consider integration tests instead |
| Low coverage | Add edge case tests |

## Test Reports

### HTML Report

```bash
pytest --html=report.html --self-contained-html
```

### Coverage Report

```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Detailed Report

```bash
pytest -v --tb=long
```

## Advanced Testing

### Parametrized Tests

Test multiple inputs with one test function:

```python
@pytest.mark.parametrize(
    "input,expected",
    [
        ("ubuntu", True),
        ("debian", True),
        ("invalid", False),
    ]
)
def test_valid_distro(input, expected):
    assert is_valid_distro(input) == expected
```

### Fixture Parametrization

Create multiple fixture variants:

```python
@pytest.fixture(params=["guided", "balanced", "expert"])
def mode(request):
    return request.param

def test_mode_variant(mode):
    # Runs 3 times with different modes
    assert mode in ["guided", "balanced", "expert"]
```

### Async Tests

Test async code:

```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result is not None
```

## Best Practices Checklist

- [ ] Tests have clear, descriptive names
- [ ] Each test tests one thing
- [ ] Tests use appropriate fixtures
- [ ] Tests include both success and error cases
- [ ] Tests are independent and isolated
- [ ] Tests run quickly (< 1 second for unit tests)
- [ ] Tests have >90% coverage for critical paths
- [ ] Tests are easy to understand
- [ ] Tests are maintainable
- [ ] Tests follow project conventions

## Resources

- [Pytest Documentation](https://pytest.org/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Testing Best Practices](https://docs.pytest.org/en/6.2.x/goodpractices.html)
- [Fixture Patterns](https://docs.pytest.org/en/6.2.x/fixture.html)

## Contact

For questions about testing strategy or implementation, contact the development team.
