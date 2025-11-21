# Unit Tests for Cascade REST CLI

This directory contains comprehensive unit tests for the Cascade REST CLI project.

## Test Files

### 1. `test_crud_operations.py`
Tests for basic CRUD operations on various asset types (pages, files, folders, blocks, symlinks):
- **Create**: Test asset creation for all asset types
- **Read**: Test reading assets by ID and by path
- **Update**: Test updating asset metadata, content, and properties
- **Delete**: Test deletion with and without unpublishing
- **Error Handling**: Test various error scenarios

**Key Test Classes:**
- `TestCRUDOperations`: Main CRUD tests for all asset types
- `TestCRUDErrorHandling`: Error handling scenarios
- `TestParametrizedCoreOperations`: Parametrized tests for URL construction

### 2. `test_advanced_filtering.py`
Tests for the AdvancedFilter system with various filter operators:
- **Text Operators**: equals, contains, starts_with, ends_with, regex
- **List Operators**: in, not_in
- **Numeric Operators**: greater_than, less_than
- **Date Operators**: date_after, date_before, date_between
- **Validation Operators**: is_empty, is_not_empty
- **Complex Filters**: AND/OR logic, nested filters
- **Edge Cases**: Empty lists, nonexistent fields, case sensitivity

**Key Test Classes:**
- `TestAdvancedFilterOperators`: Test all filter operators
- `TestAdvancedFilterPresets`: Test preset filter creation

### 3. `test_csv_operations.py`
Tests for CSV import/export functionality with metadata and tag preservation:
- **Export**: Export assets to CSV with/without metadata
- **Import**: Import assets from CSV preserving all fields
- **Templates**: Create template CSV files for different asset types
- **Batch Operations**: Batch updates from CSV files
- **Special Cases**: Special characters, nested data, JSON values
- **Roundtrip**: Verify export/import symmetry

**Key Test Classes:**
- `TestCSVExport`: CSV export functionality
- `TestCSVImport`: CSV import functionality
- `TestCSVTemplates`: Template creation
- `TestCSVBatchOperations`: Batch operations from CSV

### 4. `test_tags.py`
Tests for tag operations (add, remove, set, search):
- **Add Tags**: Add tags to assets with/without existing tags
- **Replace Tags**: Replace existing tags
- **Prevent Duplicates**: Ensure duplicate tags aren't added
- **Search**: Find assets by tags (single, multiple, prefixes)
- **Batch Operations**: Batch tag operations across multiple assets
- **Validation**: Handle special characters, whitespace, malformed responses

**Key Test Classes:**
- `TestTagOperations`: Core tag CRUD operations
- `TestTagSearch`: Search assets by tags
- `TestTagBatchOperations`: Batch tag operations
- `TestTagValidation`: Edge cases and validation

### 5. `test_scheduled_jobs.py`
Tests for the JobScheduler system:
- **Create Jobs**: Create scheduled jobs with various configurations
- **List Jobs**: List all jobs, filter by environment
- **Update Jobs**: Update schedule, command args, environment
- **Enable/Disable**: Enable and disable jobs
- **Execute Jobs**: Run jobs immediately with success/failure handling
- **Job History**: Track and retrieve execution history
- **Cleanup**: Clean up old execution records

**Key Test Classes:**
- `TestJobCreation`: Job creation functionality
- `TestJobListing`: Job listing and filtering
- `TestJobUpdates`: Job update operations
- `TestJobDeletion`: Job deletion
- `TestJobExecution`: Job execution (immediate)
- `TestJobHistory`: Job execution history
- `TestJobHistoryCleanup`: History cleanup

## Running the Tests

### Prerequisites

Install pytest (if not already installed):

```bash
# Using uv (recommended for this project)
uv pip install pytest pytest-cov

# Or using pip
pip install pytest pytest-cov
```

### Run All Tests

```bash
# Run all tests in the tests directory
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=. --cov-report=html
```

### Run Specific Test Files

```bash
# Run CRUD operation tests
pytest tests/test_crud_operations.py -v

# Run AdvancedFilter tests
pytest tests/test_advanced_filtering.py -v

# Run CSV operations tests
pytest tests/test_csv_operations.py -v

# Run tag operation tests
pytest tests/test_tags.py -v

# Run scheduled jobs tests
pytest tests/test_scheduled_jobs.py -v
```

### Run Specific Test Classes or Methods

```bash
# Run a specific test class
pytest tests/test_crud_operations.py::TestCRUDOperations -v

# Run a specific test method
pytest tests/test_crud_operations.py::TestCRUDOperations::test_create_page -v

# Run tests matching a pattern
pytest tests/ -k "test_create" -v
```

### Run with Different Output Formats

```bash
# Verbose output
pytest tests/ -v

# Show print statements
pytest tests/ -v -s

# Show only failures
pytest tests/ --tb=short

# Generate HTML coverage report
pytest tests/ --cov=. --cov-report=html
# Then open htmlcov/index.html
```

## Test Coverage

The test suite provides comprehensive coverage for:

1. **CRUD Operations (test_crud_operations.py)**
   - 5 asset types (page, file, folder, block, symlink)
   - 4 operations (create, read, update, delete)
   - Error handling and edge cases
   - ~30 tests

2. **Advanced Filtering (test_advanced_filtering.py)**
   - 14 filter operators
   - Case sensitivity handling
   - Complex filters with AND/OR logic
   - Nested field access
   - ~35 tests

3. **CSV Operations (test_csv_operations.py)**
   - Export with/without metadata
   - Import preserving all fields
   - Template generation
   - Batch operations
   - Special character handling
   - ~25 tests

4. **Tag Operations (test_tags.py)**
   - Add, replace, search tags
   - Batch tag operations
   - Tag validation
   - Search by single/multiple tags
   - ~20 tests

5. **Scheduled Jobs (test_scheduled_jobs.py)**
   - Job CRUD operations
   - Job execution
   - History tracking
   - Environment filtering
   - ~30 tests

**Total: ~140 comprehensive unit tests**

## Test Design Patterns

### Mocking
All tests use `unittest.mock` to mock HTTP requests and external dependencies:
- `@patch("cascade_rest.core.requests.post")` for API calls
- `@patch("scheduled_jobs.subprocess.run")` for job execution

### Fixtures
Each test class has `setUp()` and `tearDown()` methods for:
- Creating test data
- Temporary file/directory management
- Cleanup after tests

### Parametrized Tests
Many tests use `@pytest.mark.parametrize` for testing multiple scenarios:
- Different asset types
- Different filter operators
- Different environments

### Assertions
Tests use both unittest and pytest assertions:
- `self.assertEqual()`, `self.assertTrue()`, etc.
- `assert` statements for pytest-style tests

## Continuous Integration

To integrate with CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install pytest pytest-cov
          pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Adding New Tests

When adding new features, follow these guidelines:

1. **Create test file**: `test_<feature_name>.py`
2. **Import modules**: Import the modules to test
3. **Create test class**: `class Test<FeatureName>(unittest.TestCase)`
4. **Add setUp/tearDown**: For test fixtures and cleanup
5. **Write tests**: One test per behavior/scenario
6. **Use descriptive names**: `test_<action>_<scenario>_<expected_result>`
7. **Mock external dependencies**: Don't make real API calls
8. **Assert expectations**: Verify both success and failure cases

### Example Test Template

```python
import unittest
from unittest.mock import patch, MagicMock
import pytest

from module_to_test import function_to_test


class TestNewFeature(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.test_data = {...}

    def tearDown(self):
        """Clean up after tests"""
        pass

    @patch("module_to_test.requests.post")
    def test_feature_success(self, mock_post):
        """Test feature with successful response"""
        mock_post.return_value = MagicMock(...)
        
        result = function_to_test(...)
        
        self.assertEqual(result, expected_value)
        mock_post.assert_called_once()

    def test_feature_error_case(self):
        """Test feature with error handling"""
        # Test implementation
        pass
```

## Troubleshooting

### Import Errors
If you get import errors, make sure the project root is in your PYTHONPATH:
```bash
export PYTHONPATH=/Users/winston/Repositories/wjoell/cascade-rest-cli:$PYTHONPATH
```

### Module Not Found
Install missing dependencies:
```bash
uv pip install <missing-module>
```

### Test Failures
Run with verbose output to see details:
```bash
pytest tests/test_file.py -vv -s
```

## Best Practices

1. **Test Independence**: Each test should be independent
2. **Mock External Calls**: Don't make real API calls or write real files
3. **Use Temporary Files**: For file operations, use `tempfile` module
4. **Clean Up**: Always clean up resources in `tearDown()`
5. **Descriptive Names**: Test names should clearly describe what they test
6. **One Assertion Focus**: Each test should focus on one behavior
7. **Test Both Paths**: Test both success and failure cases
8. **Fast Tests**: Tests should run quickly (< 1 second each)

## References

- [pytest documentation](https://docs.pytest.org/)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Test-Driven Development (TDD)](https://en.wikipedia.org/wiki/Test-driven_development)
