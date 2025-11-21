# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

Cascade REST CLI is a comprehensive Python command-line interface for interacting with Cascade Server REST API. It provides an enterprise-grade toolset including command-line tools, interactive shell, secure credential management, automated job scheduling, and advanced data processing capabilities for content management operations.

**Core Features:**
- **Authentication**: API key, username/password, 1Password integration, keyring storage
- **Interactive Mode**: Full-featured command shell with persistent sessions
- **Batch Operations**: Bulk asset management with progress tracking and rollback support
- **CSV Operations**: Import/export with templates and backup functionality
- **Advanced Filtering**: Complex search criteria with multiple operators
- **Secure Credential Management**: Encrypted local storage and 1Password integration
- **Scheduled Jobs**: Automated recurring operations with background scheduling
- **Session Management**: Persistent authentication with auto-reconnection
- **Performance Monitoring**: Operation metrics, caching, and parallel processing
- **Comprehensive Logging**: Structured logging with rotation and monitoring

## Development Commands

### Setup and Installation

```bash
# Project uses uv for package management (see pyproject.toml)
uv sync  # Install all dependencies from lock file

# Or install manually if uv not available
pip install click>=8.2.1 requests>=2.32.4 aiohttp>=3.9.0 tabulate>=0.9.0 cryptography>=41.0.0 keyring>=24.0.0 schedule>=1.2.0

# Make CLI executable
chmod +x cli.py

# Test CLI functionality (no auth required)
python test_cli.py

# Activate virtual environment (if using .venv)
source .venv/bin/activate

# Install 1Password CLI for secure credential management (optional)
brew install 1password-cli
# or download from https://1password.com/downloads/command-line/
```

### Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_core.py

# Run with verbose output
python -m pytest -v

# Test the CLI without authentication
python test_cli.py
```

### Running the Application

#### Quick Start with 1Password (Recommended)
```bash
# Connect to test environment (port 7443)
python cli.py connect-1password "Cascade REST Development Test" "Cascade Rest API Test"

# Connect to production environment (port 8443)
python cli.py connect-1password "Cascade REST Development Production" "Cascade Rest API Production"

# Quick environment switching
python cli.py quick-connect --env test
python cli.py quick-connect --env production
```

#### Traditional Setup
```bash
# Setup connection (interactive)
python cli.py setup

# Setup with API key and secure storage
python cli.py setup --api-key YOUR_API_KEY --connection-name production --use-keyring

# Setup from environment variables
export CASCADE_API_KEY="your_key"
export CASCADE_URL="https://cms.example.edu:8443"
python cli.py setup --from-env
```

#### Interactive Mode (Recommended for Development)
```bash
# Start interactive mode with persistent session
python cli.py interactive

# Within interactive mode:
cascade> search faculty
cascade> read page 12345
cascade> update page 12345 title "New Title"
cascade> batch-update --type page --path-filter "faculty" --field department --value "Computer Science" --dry-run
cascade> job-create "Daily Faculty Update" "daily at 09:00" batch-update --type page --path-filter "faculty"
cascade> help
cascade> quit
```

#### Command Line Operations
```bash
# Basic commands
python cli.py search "faculty"
python cli.py read page 12345
python cli.py update page 12345 title "New Title"
python cli.py publish page 12345

# Advanced batch operations
python cli.py batch-update --type page --path-filter "2024-2025" --field academic_year --value "2024-2025" --dry-run
python cli.py batch-tag --type page --path-filter "faculty" --tag department --value "Computer Science"
python cli.py batch-publish --type page --path-filter "2024-2025" --site "catalogue" --environment production

# CSV operations
python cli.py export-csv --type page --path-filter "faculty" --output faculty.csv --include-metadata
python cli.py csv-import faculty_updates.csv --operation metadata --backup --dry-run
```

## Architecture Overview

### Core Module Structure

#### Primary API Modules (`cascade_rest/` package)
- **`core.py`**: Basic CRUD operations (Create, Read, Update, Delete, Copy, Move)
- **`search.py`**: Search functionality, site listing, and audit operations  
- **`metadata.py`**: Metadata field operations and tag management
- **`publishing.py`**: Publishing, workflow, and subscriber operations
- **`folders.py`**: Folder navigation and structured data operations
- **`utils.py`**: Utility functions, reporting, and logging

#### Advanced CLI Modules (Root level)
- **`cli.py`**: Enhanced Click-based CLI with session management and auto-reconnection
- **`secrets_manager.py`**: Secure credential storage with encryption and keyring support
- **`session_manager.py`**: Persistent session management with encrypted storage
- **`scheduled_jobs.py`**: Automated job scheduling with background execution
- **`csv_operations.py`**: Comprehensive CSV import/export with templates and backup
- **`advanced_filtering.py`**: Complex search filtering with multiple operators
- **`rollback.py`**: Operation rollback and state management
- **`performance.py`**: Performance monitoring, caching, and parallel processing
- **`logging_config.py`**: Structured logging with rotation and monitoring
- **`test_environment_helpers.py`**: Development and testing utilities

### Enhanced CLI Architecture

**Main Components:**
- **`CascadeCLI` class**: Enhanced connection management with auto-reconnection and session persistence
- **`SecretsManager`**: Secure credential storage with multiple backends (keyring, encryption, 1Password)
- **`SessionManager`**: Persistent session management with expiration and auto-renewal
- **`JobScheduler`**: Background job scheduling and execution management
- **Interactive shell**: Feature-rich persistent session with command history and context

**Authentication Flow (Enhanced):**
1. **Auto-load**: Automatically loads saved session credentials on startup
2. **Multiple Auth Methods**: API key, username/password, 1Password, environment variables
3. **Secure Storage**: Credentials encrypted locally or stored in system keyring
4. **Session Persistence**: Credentials persist between CLI invocations (24h default)
5. **Environment Switching**: Quick switching between test/production environments
6. **Auto-reconnection**: Automatic reconnection if session expires

**1Password Integration:**
1. **Vault Management**: Separate vaults for test and production credentials
2. **Quick Connect**: One-command connection to predefined environments
3. **Team Workflows**: Shared credential management for development teams

### Key Design Patterns

**Modular API Design:**
- Each module exposes specific REST API endpoints
- Functions follow consistent parameter patterns: `(cms_path, auth, ...)`
- All functions return structured responses or False on error
- Async support for improved performance

**Enhanced Error Handling:**
- HTTP errors return `False` from API functions with detailed logging
- CLI layer provides user-friendly error messages with context
- Batch operations track success/failure counts with rollback support
- Structured error logging with operation context

**Advanced Batch Operations:**
1. **Pre-execution**: Automatic rollback point creation
2. **Search and Filter**: Complex criteria matching with advanced filters
3. **Parallel Processing**: Concurrent operations with rate limiting
4. **Progress Tracking**: Real-time progress with detailed metrics
5. **Post-execution**: Success/failure reporting with rollback options
6. **Backup Integration**: Automatic CSV backups before bulk changes

**Security and Session Management:**
- **Encryption**: AES-256 encryption for local credential storage
- **Keyring Integration**: System keyring support (macOS Keychain, Windows Credential Manager)
- **Session Expiration**: Time-based session expiration with auto-renewal
- **Secure Cleanup**: Automatic cleanup of expired sessions and credentials

## Development Guidelines

### Adding New Commands

When adding new CLI commands:

1. **Core API Function**: Add to appropriate `cascade_rest/` module (e.g., `core.py`)
2. **CLI Command**: Add to `cli.py` using Click decorators with proper error handling
3. **Interactive Mode**: Add handler to interactive mode if applicable
4. **Logging**: Add structured logging for the operation
5. **Testing**: Add unit tests and integration tests
6. **Documentation**: Update help text, README, and CLI_REFERENCE_GUIDE

**Enhanced Command Example:**
```python path=null start=null
@main.command()
@click.argument("asset_type")
@click.argument("asset_id")
@click.option("--dry-run", is_flag=True, help="Preview changes without executing")
@click.option("--environment", help="Target environment (test/production)")
def new_command(asset_type: str, asset_id: str, dry_run: bool, environment: str):
    """Enhanced command with logging and error handling"""
    logger.log_operation_start("new_command", asset_type=asset_type, asset_id=asset_id)
    
    try:
        # Switch environment if specified
        if environment:
            secrets_manager.switch_environment(environment)
        
        result = cli.new_operation(asset_type, asset_id, dry_run=dry_run)
        if result:
            click.echo(json.dumps(result, indent=2))
            logger.log_operation_end("new_command", True)
        else:
            logger.log_operation_end("new_command", False)
            click.echo("❌ Operation failed")
    except Exception as e:
        logger.log_error(e, {"operation": "new_command", "asset_type": asset_type})
        click.echo(f"❌ Error: {e}")
```

### Testing New Features

#### Test Environment Setup
```bash
# Connect to test environment for safe testing
python cli.py quick-connect --env test

# Or use 1Password test credentials
python cli.py connect-1password "Cascade REST Development Test" "Cascade Rest API Test"

# Test helpers for development
python test_read.py  # Test basic read operations
python test_read_prod.py  # Test production read operations
```

#### Unit Testing
1. Add unit tests in `tests/` directory following existing patterns
2. Use `unittest.mock` to mock HTTP requests
3. Test both success and error conditions
4. Include tests for new advanced features (rollback, CSV, scheduling)
5. Run `python test_cli.py` to verify CLI structure

**Test File Organization:**
- `test_core.py`: Tests for basic CRUD operations
- `test_search.py`: Tests for search and discovery operations
- `test_publishing.py`: Tests for publishing operations
- `test_metadata.py`: Tests for metadata operations
- `test_secrets_manager.py`: Tests for secure credential management
- `test_scheduled_jobs.py`: Tests for job scheduling
- `test_csv_operations.py`: Tests for CSV import/export

**Running Tests:**
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test module
python -m pytest tests/test_core.py -v

# Run with coverage
python -m pytest tests/ --cov=cascade_rest --cov-report=html

# Test CLI structure
python test_cli.py
```

#### Integration Testing
```bash
# Test full workflows with dry-run
python cli.py batch-update --type page --path-filter "test" --field "test_field" --value "test_value" --dry-run --environment test

# Test CSV operations
python cli.py csv-template page --output test_template.csv
python cli.py export-csv --type page --path-filter "test" --output test_export.csv
```

### Metadata and Advanced Operations

#### Metadata Fields
The system supports standard metadata fields defined in `METADATA_ALLOWED_KEYS`:
- `displayName`, `title`, `summary`, `teaser`
- `keywords`, `metaDescription`, `author`
- Dynamic metadata fields through the metadata module
- Tag management with batch operations

#### CSV Operations
- **Templates**: Auto-generated CSV templates for any asset type
- **Export**: Bulk export with metadata inclusion and field selection
- **Import**: Batch import with validation and backup creation
- **Backup**: Automatic backup before bulk operations

#### Advanced Filtering
Supports complex search criteria with operators:
- **Text**: `equals`, `contains`, `starts_with`, `ends_with`, `regex`
- **Lists**: `in`, `not_in`
- **Dates**: `date_after`, `date_before`, `date_between`
- **Numeric**: `greater_than`, `less_than`
- **Validation**: `is_empty`, `is_not_empty`

### Advanced Features Best Practices

#### Batch Operations
- **Always test first**: Use `--dry-run` flag for all batch operations
- **Environment safety**: Test on test environment before production
- **Scope limiting**: Use specific path patterns and filters
- **Progress monitoring**: Built-in progress bars and real-time metrics
- **Automatic backups**: CSV backups created before bulk changes
- **Rollback ready**: Rollback points automatically created

#### Scheduled Jobs
- **Job Templates**: Use built-in templates for common operations
- **Environment-specific**: Create separate jobs for test/production
- **Monitoring**: Regular job history review and cleanup
- **Dry-run scheduling**: Test job commands before scheduling

#### Credential Management
- **1Password preferred**: Use 1Password for team credential management
- **Environment separation**: Separate credentials for test/production
- **Keyring fallback**: Use system keyring when 1Password unavailable
- **Session expiration**: Regular credential rotation (24h default)

#### CSV Operations
- **Template-first**: Always start with generated templates
- **Backup enabled**: Use `--backup` flag for important operations
- **Field validation**: Verify field names and types before import
- **Batch size**: Process in manageable chunks for large datasets

### Interactive Mode Development

The enhanced interactive shell supports:
- **Command Execution**: All CLI commands without `python cli.py` prefix
- **Session Persistence**: Credentials persist across commands and sessions
- **Auto-reconnection**: Automatic reconnection if session expires
- **Command History**: Built-in command history and recall
- **Context-aware Help**: Comprehensive help system with examples
- **Environment Switching**: Quick switching between test/production
- **Job Management**: Create and manage scheduled jobs interactively
- **Real-time Feedback**: Progress indicators and structured output

## Configuration

**Default Settings** (in `config.py`):
- **CMS Paths**: 
  - Production: `https://cms.example.edu:8443`
  - Test: `https://cms.example.edu:7443`
- **Performance**: 
  - Batch Size: 50 operations at a time
  - Parallel Workers: 4 concurrent operations
  - Request Timeout: 30 seconds
  - Connection Pool Size: 10
- **Caching**:
  - Cache TTL: 5 minutes
  - Cache enabled by default
- **Retry Logic**: 3 attempts with 1-second delay
- **Logging**:
  - Log Level: INFO
  - Log Rotation: 10MB files, 5 backups
  - Structured logging with operation context
- **Sessions**: 
  - Default expiration: 24 hours
  - Auto-cleanup of expired sessions
- **CSV Operations**:
  - UTF-8 encoding, comma-delimited
  - Automatic backup directory creation
- **Rollback**: 
  - Retention: 30 days
  - Automatic cleanup of old rollback data

**Authentication Methods (Enhanced):**
- **API Key**: `{"apiKey": "your_key"}` (recommended)
- **Username/Password**: `{"u": "username", "p": "password"}`
- **1Password Integration**: Vault and item-based credential management
- **Environment Variables**: `CASCADE_API_KEY`, `CASCADE_URL`, etc.
- **Keyring Storage**: System keyring integration for secure local storage

## Common Workflows

**Enterprise Content Management Workflow:**
1. **Environment Setup**: `python cli.py quick-connect --env test`
2. **Search and Analyze**: `python cli.py advanced-search --type page --filters "path:contains:faculty,academic_year:equals:2024-2025"`
3. **Export for Review**: `python cli.py export-csv --type page --path-filter "faculty" --output faculty_review.csv --include-metadata`
4. **Test Changes**: `python cli.py batch-update --type page --path-filter "faculty" --field department --value "Computer Science" --dry-run`
5. **Create Rollback Point**: Automatically created during batch operations
6. **Apply Changes**: `python cli.py batch-update --type page --path-filter "faculty" --field department --value "Computer Science" --backup`
7. **Publish Updates**: `python cli.py batch-publish --type page --path-filter "faculty" --environment test`
8. **Switch to Production**: `python cli.py quick-connect --env production`
9. **Deploy to Production**: `python cli.py batch-update --type page --path-filter "faculty" --field department --value "Computer Science"`

**Scheduled Automation Workflow:**
1. **Create Job**: `python cli.py job-create "Daily Faculty Sync" "daily at 09:00" batch-update --type page --path-filter "faculty"`
2. **Test Job**: `python cli.py job-run "daily_faculty_sync" --dry-run`
3. **Enable Job**: `python cli.py job-enable "daily_faculty_sync"`
4. **Start Scheduler**: `python cli.py scheduler-start`
5. **Monitor Jobs**: `python cli.py job-history "daily_faculty_sync"`

**Development/Testing Workflow (Enhanced):**
1. **Code Changes**: Make modifications to core modules
2. **Unit Testing**: `python -m pytest tests/ -v --cov=cascade_rest`
3. **CLI Structure Test**: `python test_cli.py`
4. **Integration Testing**: 
   - `python test_read.py` (test environment)
   - `python test_read_prod.py` (production read-only)
5. **Interactive Testing**: `python cli.py interactive`
6. **Example Workflows**: 
   - `python examples.py` (basic examples)
   - `python enhanced_examples.py` (advanced features)
   - `python batch_examples.py` (batch operations)
7. **Real Environment Testing**: Use test environment for validation

**CSV-Based Bulk Operations:**
1. **Generate Template**: `python cli.py csv-template page --fields "id,title,academic_year,department"`
2. **Export Current State**: `python cli.py export-csv --type page --path-filter "faculty" --output current_faculty.csv`
3. **Modify CSV**: Edit exported CSV with new values
4. **Validate Import**: `python cli.py csv-import updated_faculty.csv --operation metadata --dry-run`
5. **Execute Import**: `python cli.py csv-import updated_faculty.csv --operation metadata --backup`

**Programmatic Usage Examples:**
Multiple example files demonstrate different usage patterns:

**`examples.py`**: Basic programmatic usage
- `setup_connection()`: Setup authentication
- `search_assets()`: Search with JSON result parsing
- `batch_update_metadata()`: Bulk operations on multiple assets
- `search_and_update()`: Combined search and update workflow

**`enhanced_examples.py`**: Advanced feature demonstrations
- CSV import/export workflows
- Advanced filtering examples
- Rollback operation examples
- Performance monitoring usage

**`batch_examples.py`**: Comprehensive batch operation examples
- Multi-step batch workflows
- Error handling and recovery
- Progress monitoring and reporting

**`scheduled_jobs_example.py`**: Job scheduling examples
- Creating recurring jobs
- Job management and monitoring
- Environment-specific scheduling

**`onepassword_example.py`**: 1Password integration examples
- Team credential management
- Environment switching workflows

## Debugging and Troubleshooting

**Common Issues:**
- **"Not connected" errors**: 
  - Check session status: `python cli.py session-info`
  - Reconnect: `python cli.py quick-connect --env test`
  - Manual setup: `python cli.py setup`
- **Authentication failures**: 
  - Verify API key permissions in Cascade Server
  - Check 1Password vault access: `op signin`
  - Test connection: `python cli.py test-connection`
- **Asset not found**: Verify asset type and ID format
- **Permission errors**: Check Cascade Server user role permissions
- **Job execution failures**: Review job history: `python cli.py job-history job_name`

**Advanced Debugging:**
- **Structured Logging**: Check `~/.cascade_cli/logs/cascade_cli.log`
- **Session Debugging**: View session details: `python cli.py session-info`
- **Performance Metrics**: `python cli.py performance-stats`
- **Connection Testing**: 
  - Test environment: `python test_read.py`
  - Production (read-only): `python test_read_prod.py`
- **Verbose Testing**: `pytest -v --log-cli-level=DEBUG`
- **Dry-run Everything**: Use `--dry-run` flag extensively

**Log Analysis:**
- **Operation Logs**: Structured JSON logs with full context
- **API Call Logs**: HTTP request/response timing and status
- **Error Logs**: Full stack traces with operation context
- **Batch Progress**: Detailed progress tracking for bulk operations
- **Rollback Logs**: Complete rollback operation history

**Recovery Procedures:**
- **Failed Batch Operations**: Use rollback: `python cli.py rollback-list && python cli.py rollback-execute rollback_id`
- **Credential Issues**: Clear and recreate: `python cli.py clear-session && python cli.py setup`
- **Job Issues**: Disable problematic jobs: `python cli.py job-disable job_name`
- **Performance Issues**: Clear cache: `python cli.py cleanup`

## Dependencies and Architecture

**Core Runtime Dependencies** (from `pyproject.toml`):
- `click>=8.2.1`: Enhanced CLI framework with interactive mode
- `requests>=2.32.4`: HTTP client for REST API communication
- `aiohttp>=3.9.0`: Async HTTP client for performance optimization
- `tabulate>=0.9.0`: Table formatting for structured output
- `cryptography>=41.0.0`: Encryption for secure credential storage
- `keyring>=24.0.0`: System keyring integration
- `schedule>=1.2.0`: Job scheduling and automation

**External Tools** (Optional but Recommended):
- **1Password CLI**: `op` command for team credential management
- **System Keyring**: macOS Keychain, Windows Credential Manager, etc.

**Development Dependencies:**
- `pytest`: Comprehensive testing framework
- `pytest-cov`: Code coverage reporting
- `unittest.mock`: HTTP request mocking for tests
- `uv`: Fast Python package management (preferred over pip)

**File Organization:**
- **Configuration**: `config.py`, `logging_config.py`
- **Core API**: `cascade_rest/` package modules
- **Advanced Features**: Root-level specialized modules
- **Examples**: Multiple example files for different use cases
- **Data Storage**: `~/.cascade_cli/` for sessions, logs, rollbacks
- **CSV Operations**: `csv_backups/` for automatic backups
- **Notebooks**: Jupyter notebooks for data analysis and exploration
