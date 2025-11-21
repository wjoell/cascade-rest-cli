# Cascade REST CLI

A command-line interface for interacting with Cascade Server REST API. This tool provides operations for searching assets, reading metadata, updating fields, and publishing content.

## Important Notices

**USE AT YOUR OWN RISK**: This is an orchestration tool under active development. Features and functionality may change without notice. The codebase has not been extensively battle-tested in production environments.

**CAUTION**: This tool can perform batch operations that may have destructive outcomes that are difficult or impossible to reverse. Always:
- Test thoroughly in a test environment before using in production
- Use the `--dry-run` flag to preview operations
- Maintain backups of your content
- Verify operations on small datasets before scaling up

**COMPATIBILITY**: This project is intended for use with Cascade CMS on-premises instances. Compatibility with Cascade Cloud is not guaranteed and your mileage may vary.

**DEVELOPMENT STATUS**: This is a comprehensive orchestration tool that is actively being developed. Code quality, test coverage, and feature stability may vary across different modules.

## Features

### Core Operations

-   **Authentication**: Support for API key and username/password authentication
-   **Search**: Search for assets across sites
-   **Read**: Read individual asset details and metadata
-   **Update**: Update metadata fields on assets
-   **Publish**: Publish or unpublish assets
-   **Browse**: List folder contents
-   **Reports**: View operation summaries
-   **Interactive Mode**: Command-line interface for interactive use

### Batch Operations

-   **Batch Operations**: Bulk update assets by type and path patterns
-   **Tag Management**: Set tags across multiple assets
-   **Dry Run Mode**: Preview changes before applying them

### Advanced Features

-   **Comprehensive Logging**: Structured logging with configurable levels and file rotation
-   **CSV Import/Export**: Batch operations from spreadsheet data with templates
-   **Advanced Filtering**: Search criteria with multiple operators
-   **Rollback Operations**: Attempt to undo batch operations with automatic state tracking
-   **Performance Optimization**: Parallel processing and connection pooling
-   **Performance Monitoring**: Basic metrics and operation statistics
-   **Automated Cleanup**: Remove old rollback records and expired cache entries
-   **Secure Secret Management**: Encrypted credential storage with keyring support
-   **Scheduled Jobs**: Automated recurring operations with background scheduling

## Installation

1. Install dependencies:

```bash
uv add click
```

2. Make the CLI executable:

```bash
chmod +x cli.py
```

## Quick Start

### 1. Setup Connection

First, set up your connection to Cascade Server:

```bash
# Using API key
python cli.py setup --api-key YOUR_API_KEY

# Using username/password
python cli.py setup --username YOUR_USERNAME --password YOUR_PASSWORD

# Interactive setup
python cli.py setup
```

### 2. Basic Commands

```bash
# Search for assets
python cli.py search "faculty"

# Search within a specific site
python cli.py search "course" --site "myslc"

# Read a specific asset
python cli.py read page "abc123def456"

# List folder contents
python cli.py ls "folder_xyz789"

# Update metadata
python cli.py update page "abc123def456" title "New Title"

# Publish an asset
python cli.py publish page "abc123def456"

# Unpublish an asset
python cli.py publish page "abc123def456" --unpublish

# View operation reports
python cli.py reports
```

### 3. Interactive Mode

For the most convenient experience, use interactive mode:

```bash
python cli.py interactive
```

This starts an interactive shell where you can run commands without the `python cli.py` prefix:

```
cascade> search faculty
cascade> read page 12345
cascade> update page 12345 department "Computer Science"
cascade> batch-update page "2024-2025" academic_year "2024-2025"
cascade> batch-tag page "2024-2025" semester "Fall 2024"
cascade> batch-publish page "2024-2025"
cascade> help
cascade> quit
```

## Command Reference

### `setup`

Set up connection to Cascade Server.

**Options:**

-   `--cms-path`: Cascade Server URL (default: https://cms.example.edu:8443)
-   `--api-key`: API key for authentication
-   `--username`: Username for authentication
-   `--password`: Password for authentication

### `search`

Search for assets.

**Arguments:**

-   `search_terms`: Search query

**Options:**

-   `--site`: Site name to limit search

### `read`

Read a single asset.

**Arguments:**

-   `asset_type`: Type of asset (e.g., page, file, block)
-   `asset_id`: Asset ID

### `ls`

List children of a folder.

**Arguments:**

-   `folder_id`: Folder ID

### `update`

Update metadata field.

**Arguments:**

-   `asset_type`: Type of asset
-   `asset_id`: Asset ID
-   `field_name`: Metadata field name
-   `new_value`: New value for the field

### `publish`

Publish or unpublish an asset.

**Arguments:**

-   `asset_type`: Type of asset
-   `asset_id`: Asset ID

**Options:**

-   `--unpublish`: Unpublish instead of publish

### `batch-update`

Batch update metadata for assets matching type and path pattern.

**Arguments:**

-   `asset_type`: Type of asset (e.g., page, file, block)
-   `path_pattern`: Path pattern to match (e.g., "2024-2025")
-   `field_name`: Metadata field name
-   `new_value`: New value for the field

**Options:**

-   `--site`: Site name to limit search
-   `--dry-run`: Show what would be updated without making changes

### `batch-tag`

Batch set tag value for assets matching type and path pattern.

**Arguments:**

-   `asset_type`: Type of asset (e.g., page, file, block)
-   `path_pattern`: Path pattern to match (e.g., "2024-2025")
-   `tag_name`: Tag name
-   `tag_value`: Tag value

**Options:**

-   `--site`: Site name to limit search
-   `--dry-run`: Show what would be updated without making changes

### `batch-publish`

Batch publish/unpublish assets matching type and path pattern.

**Arguments:**

-   `asset_type`: Type of asset (e.g., page, file, block)
-   `path_pattern`: Path pattern to match (e.g., "2024-2025")

**Options:**

-   `--site`: Site name to limit search
-   `--unpublish`: Unpublish instead of publish
-   `--dry-run`: Show what would be published without making changes

### `reports`

Show operation reports and summaries.

### `interactive`

Start interactive mode for command-line interface.

## Advanced Features

### CSV Import/Export

#### `csv-template`

Create a CSV template for a specific asset type:

```bash
python cli.py csv-template page
# Creates template_page.csv with example data
```

#### `export-csv`

Export assets to CSV file:

```bash
python cli.py export-csv page "2024-2025" assets.csv --include-metadata
```

#### `csv-import`

Import and process assets from CSV file:

```bash
python cli.py csv-import data.csv --operation metadata --dry-run
```

### Advanced Filtering

#### `advanced-search`

Search with sophisticated filtering capabilities:

```bash
# Find published pages containing "2024" in the name
python cli.py advanced-search page "/" --field name --operator contains --value "2024"

# Find assets created after a specific date
python cli.py advanced-search page "/" --field createdDate --operator date_after --value "2024-01-01"

# Find assets with specific tag values
python cli.py advanced-search page "/" --field tags --operator in --value "priority,important"
```

**Available Operators:**

-   `equals`: Exact match
-   `contains`: Contains substring
-   `starts_with`: Starts with string
-   `ends_with`: Ends with string
-   `regex`: Regular expression match
-   `in`: Value in list
-   `not_in`: Value not in list
-   `date_after`: Date after specified date
-   `date_before`: Date before specified date
-   `is_empty`: Field is empty
-   `is_not_empty`: Field has value

### Rollback Operations

#### `rollback-list`

List available rollback operations:

```bash
python cli.py rollback-list --limit 10
```

#### `rollback-execute`

Execute a rollback operation:

```bash
python cli.py rollback-execute abc12345-6789-def0-1234-567890abcdef
```

### Performance Monitoring

#### `performance-stats`

Show performance statistics:

```bash
python cli.py performance-stats
```

#### `cleanup`

Clean up old rollback records and cache:

```bash
python cli.py cleanup
```

### Secure Secret Management

#### `setup`

Set up connection with secure credential storage:

```bash
# Store credentials securely with encryption
python cli.py setup --api-key "your_api_key" --connection-name "production" --use-keyring

# Store multiple connections
python cli.py setup --api-key "dev_key" --connection-name "development"
python cli.py setup --username "user" --password "pass" --connection-name "staging"
```

#### `connect`

Connect using a stored connection:

```bash
python cli.py connect production
python cli.py connect development
```

#### `connections`

List all stored connections:

```bash
python cli.py connections
```

#### `delete-connection`

Delete a stored connection:

```bash
python cli.py delete-connection development
```

#### `interactive-setup`

Interactive setup wizard:

```bash
python cli.py interactive-setup --connection-name "my_connection"
```

#### Environment Variables

Load credentials from environment variables:

```bash
# Set environment variables
export CASCADE_API_KEY="your_api_key"
export CASCADE_USERNAME="your_username"
export CASCADE_PASSWORD="your_password"
export CASCADE_URL="https://your-cascade-server.com"

# Use environment credentials
python cli.py setup --from-env
```

#### 1Password Integration

For teams and organizations using 1Password, the CLI provides seamless integration:

```bash
# Quick connect to test or production environments
python cli.py quick-connect --env test
python cli.py quick-connect --env production

# Connect using specific 1Password vault and item
python cli.py connect-1password "Cascade Test" "Test Service Account"

# List Cascade items in a 1Password vault
python cli.py list-1password "Cascade Test"

# Set up new credentials in 1Password
python cli.py setup-1password --vault "Cascade Production" --item-name "Production Service Account"
```

**1Password Setup:**

1. **Install 1Password CLI**: Download from [1password.com](https://1password.com/downloads/command-line/)
2. **Authenticate**: `op signin`
3. **Create Vaults**: Create separate vaults for test and production environments
4. **Store Service Accounts**: Create API credential items in each vault

**Recommended Structure:**

```
Cascade Test/
├── Test Service Account
└── Test API Key

Cascade Production/
├── Production Service Account
└── Production API Key
```

**Quick Environment Switching:**

```bash
# Test your operations safely
python cli.py quick-connect --env test
python cli.py search --type page --path-filter "2024-2025" --dry-run

# Switch to production when ready
python cli.py quick-connect --env production
python cli.py search --type page --path-filter "2024-2025"
```

**Security Features:**

-   **Encrypted Storage**: Local credentials encrypted with AES-256
-   **Keyring Integration**: Uses system keyring (macOS Keychain, Windows Credential Manager, etc.)
-   **Environment Variables**: Credential loading from environment variables
-   **1Password Integration**: Team credential management with 1Password CLI
-   **Restricted Permissions**: Credential files have restricted access (600 permissions)
-   **Automatic Cleanup**: Secure deletion of stored credentials

### Scheduled Jobs

Automate recurring operations with the built-in job scheduler:

```bash
# Create a scheduled job
python cli.py job-create "Daily Faculty Update" "daily at 09:00" batch-update --type page --path-filter "faculty" --field "last_updated" --value "$(date)"

# List all scheduled jobs
python cli.py job-list

# Run a job immediately (with dry-run)
python cli.py job-run "daily_faculty_update" --dry-run

# Enable/disable jobs
python cli.py job-enable "daily_faculty_update"
python cli.py job-disable "daily_faculty_update"

# View job execution history
python cli.py job-history "daily_faculty_update"

# Start background scheduler
python cli.py scheduler-start

# Clean up old execution history
python cli.py job-cleanup --days 30
```

**Job Templates:**

```bash
# View example job templates
python cli.py job-templates

# Common schedule formats:
# "daily at 09:00" - Run daily at 9 AM
# "every 30 minutes" - Run every 30 minutes
# "every 2 hours" - Run every 2 hours
# "weekly on Monday at 06:00" - Run weekly on Monday at 6 AM
```

**Environment-Specific Jobs:**

```bash
# Create test environment job
python cli.py job-create "Test Faculty Update" "daily at 10:00" batch-update --type page --path-filter "faculty" --environment "test"

# Create production environment job
python cli.py job-create "Production Faculty Update" "daily at 09:00" batch-update --type page --path-filter "faculty" --environment "production"
```

## Examples

### Batch Operations

You can use the CLI in scripts for batch operations:

```python
import subprocess
import json

# Search for assets
result = subprocess.run([
    "python", "cli.py", "search", "faculty"
], capture_output=True, text=True)
assets = json.loads(result.stdout)

# Update metadata for each asset
for asset in assets:
    subprocess.run([
        "python", "cli.py", "update",
        asset["type"], asset["id"],
        "department", "Computer Science"
    ])
```

### Common Workflows

1. **Find and Update Faculty Information:**

```bash
# Search for faculty assets
python cli.py search "faculty" --site "myslc"

# Read specific faculty member
python cli.py read page "abc123def456"

# Update department
python cli.py update page "abc123def456" department "Mathematics"

# Publish changes
python cli.py publish page "abc123def456"
```

2. **Batch Update Course Information:**

```bash
# Find all course pages
python cli.py search "course" --site "catalogue"

# For each course found, update the semester field
# (This would typically be done in a script)
```

3. **Batch Update Academic Year Pages:**

```bash
# Update all page assets with "2024-2025" in their path
python cli.py batch-update page "2024-2025" academic_year "2024-2025"

# Set a tag for all 2024-2025 course pages
python cli.py batch-tag page "2024-2025" semester "Fall 2024"

# Publish all updated pages
python cli.py batch-publish page "2024-2025"

# Test with dry-run first
python cli.py batch-update page "2024-2025" status "active" --dry-run
```

4. **Batch Operations by Site:**

```bash
# Update faculty pages in myslc site
python cli.py batch-update page "faculty" department "Computer Science" --site "myslc"

# Set tags for all course pages in catalogue site
python cli.py batch-tag page "course" catalog_year "2024-2025" --site "catalogue"

# Unpublish old academic year pages
python cli.py batch-publish page "2023-2024" --unpublish --site "catalogue"
```

## Configuration

The CLI uses default settings that can be customized in `config.py`:

-   Default CMS path
-   Output format preferences
-   Batch operation settings
-   Logging configuration

## Error Handling

The CLI provides clear error messages and handles common issues:

-   Connection failures
-   Authentication errors
-   Invalid asset IDs
-   Permission denied errors

## Best Practices

1. **Test Environment First**: Always test operations in a non-production environment
2. **Use Dry Run**: Use the `--dry-run` flag to preview changes before executing
3. **Start Small**: Test commands on a single asset before running batch operations
4. **Maintain Backups**: Back up important assets before performing bulk updates
5. **Review Changes**: Use `reports` command to review operation summaries
6. **Document Operations**: Keep records of batch operations for audit purposes
7. **Understand Rollback Limitations**: Rollback operations may not always succeed or fully restore previous state

## Troubleshooting

### Common Issues

1. **"Not connected" error**: Run `setup` command first
2. **Authentication failed**: Check your API key or credentials
3. **Asset not found**: Verify the asset type and ID
4. **Permission denied**: Check your user permissions in Cascade
5. **Unexpected behavior**: Test in a controlled environment before production use
6. **Rollback failures**: Not all operations can be successfully rolled back

### Getting Help

-   Use `python cli.py --help` for general help
-   Use `python cli.py <command> --help` for command-specific help
-   In interactive mode, type `help` for available commands
-   Review the test suite in `tests/` for usage examples

## Development

This tool is built using:

-   **Click**: Command-line interface creation kit
-   **Requests**: HTTP library for API communication
-   **Python 3.12+**: Minimum Python version

### Contributing

This is an active development project. When contributing:

1. Test thoroughly in a test environment
2. Add unit tests for new functionality (see `tests/` directory)
3. Follow existing code patterns and conventions
4. Document new features and commands
5. Consider edge cases and error handling

### Testing

See `tests/README.md` for comprehensive testing documentation. The test suite includes:

-   CRUD operation tests
-   Advanced filtering tests
-   CSV import/export tests
-   Tag operation tests
-   Job scheduler tests

Run tests with:
```bash
pytest tests/ -v
```

## License

This project is provided as-is without warranty. Use at your own risk.

## Disclaimer

This tool can modify and delete content in your Cascade CMS instance. The authors are not responsible for any data loss, corruption, or other issues that may arise from its use. Always test in a non-production environment and maintain proper backups.
