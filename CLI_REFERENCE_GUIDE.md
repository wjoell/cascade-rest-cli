# Cascade REST CLI - Complete Reference Guide

## 🚀 Quick Start

### Environment Setup

```bash
# Connect to test environment (port 7443)
python cli.py connect-1password "Cascade REST Development Test" "Cascade Rest API Test"

# Connect to production environment (port 8443)
python cli.py connect-1password "Cascade REST Development Production" "Cascade Rest API Production"
```

### Basic Operations

```bash
# Search for assets
python cli.py search "faculty"
python cli.py search "course" --site "myslc"

# Read a specific asset
python cli.py read page "asset_id_here"

# List folder contents
python cli.py ls "folder_id_here"

# Update metadata
python cli.py update page "asset_id_here" title "New Title"

# Publish/unpublish
python cli.py publish page "asset_id_here"
python cli.py publish page "asset_id_here" --unpublish
```

---

## 🔄 Batch Operations

### Batch Update Metadata

```bash
# Update academic year for all pages with "2024-2025" in path
python cli.py batch-update \
  --type page \
  --path-filter "2024-2025" \
  --field "academic_year" \
  --value "2024-2025" \
  --dry-run

# Update multiple fields
python cli.py batch-update \
  --type page \
  --path-filter "faculty" \
  --field "last_updated" \
  --value "$(date)" \
  --environment "production"
```

### Batch Tag Operations

```bash
# Set tags on multiple assets
python cli.py batch-tag \
  --type page \
  --path-filter "2024-2025" \
  --tag "academic_year" \
  --value "2024-2025" \
  --dry-run
```

### Batch Publish Operations

```bash
# Publish multiple assets
python cli.py batch-publish \
  --type page \
  --path-filter "faculty" \
  --publish

# Unpublish multiple assets
python cli.py batch-publish \
  --type page \
  --path-filter "old-content" \
  --unpublish
```

---

## 📊 CSV Operations

### Export Assets to CSV

```bash
# Export faculty pages to CSV
python cli.py export-csv \
  --type page \
  --path-filter "faculty" \
  --output faculty_export.csv \
  --fields "id,title,path,academic_year"

# Export with all metadata fields
python cli.py export-csv \
  --type page \
  --path-filter "2024-2025" \
  --output academic_year_pages.csv \
  --include-metadata
```

### Import from CSV

```bash
# Import and update from CSV
python cli.py csv-import faculty_updates.csv \
  --operation metadata \
  --dry-run

# Import with backup
python cli.py csv-import course_catalog.csv \
  --operation metadata \
  --backup \
  --environment "production"
```

### CSV Templates

```bash
# Create template for page updates
python cli.py csv-template page --output page_template.csv

# Create template with specific fields
python cli.py csv-template page \
  --fields "id,title,academic_year,department" \
  --output faculty_template.csv
```

---

## 🔍 Advanced Search and Filtering

### Advanced Search

```bash
# Complex filtering
python cli.py advanced-search \
  --type page \
  --filters "path:contains:faculty,academic_year:equals:2024-2025" \
  --logic "AND" \
  --limit 50

# Date range filtering
python cli.py advanced-search \
  --type page \
  --filters "created:date_after:2024-01-01,created:date_before:2024-12-31" \
  --logic "AND"
```

### Filter Operators

-   `equals`: Exact match
-   `contains`: Contains substring
-   `regex`: Regular expression match
-   `date_after`: Date after specified date
-   `date_before`: Date before specified date
-   `numeric_gt`: Greater than
-   `numeric_lt`: Less than

---

## ↩️ Rollback Operations

### Create Rollback Points

```bash
# Rollback is automatically created before batch operations
python cli.py batch-update \
  --type page \
  --path-filter "faculty" \
  --field "department" \
  --value "Computer Science"
# Rollback point automatically created
```

### List and Execute Rollbacks

```bash
# List available rollbacks
python cli.py rollback-list

# Execute a rollback
python cli.py rollback-execute rollback_id_here
```

---

## ⏰ Scheduled Jobs

### Create Scheduled Jobs

```bash
# Daily faculty update at 9 AM
python cli.py job-create \
  "Daily Faculty Update" \
  "daily at 09:00" \
  batch-update --type page --path-filter "faculty" --field "last_sync" --value "$(date)" \
  --environment "production"

# Weekly course catalog sync
python cli.py job-create \
  "Weekly Course Sync" \
  "weekly on Monday at 06:00" \
  csv-import courses.csv --operation metadata \
  --environment "production"
```

### Manage Jobs

```bash
# List all jobs
python cli.py job-list

# Run job immediately
python cli.py job-run "daily_faculty_update" --dry-run

# Enable/disable jobs
python cli.py job-enable "daily_faculty_update"
python cli.py job-disable "daily_faculty_update"

# View job history
python cli.py job-history "daily_faculty_update"

# Start background scheduler
python cli.py scheduler-start
```

### Schedule Formats

-   `"daily at 09:00"` - Run daily at 9 AM
-   `"every 30 minutes"` - Run every 30 minutes
-   `"every 2 hours"` - Run every 2 hours
-   `"weekly on Monday at 06:00"` - Run weekly on Monday at 6 AM

---

## 🔐 Credential Management

### 1Password Integration

```bash
# Quick connect to environments
python cli.py connect-1password "Cascade REST Development Test" "Cascade Rest API Test"
python cli.py connect-1password "Cascade REST Development Production" "Cascade Rest API Production"

# List 1Password items
python cli.py list-1password "Cascade REST Development Test"

# Set up new credentials in 1Password
python cli.py setup-1password \
  --vault "Cascade REST Development Test" \
  --item-name "New Service Account" \
  --cms-path "https://cms.example.edu:7443" \
  --api-key "your_api_key"
```

### Local Credential Storage

```bash
# Store credentials locally (encrypted)
python cli.py setup \
  --cms-path "https://cms.example.edu:8443" \
  --api-key "your_api_key" \
  --connection-name "production" \
  --use-keyring

# List stored connections
python cli.py connections

# Connect using stored connection
python cli.py connect production
```

---

## 📈 Performance and Monitoring

### Performance Monitoring

```bash
# View performance statistics
python cli.py performance-stats

# Clean up old data
python cli.py cleanup --days 30
```

### Logging

-   All operations are automatically logged
-   Logs stored in `~/.cascade_cli/logs/`
-   Configurable log levels and rotation

---

## 🧪 Testing and Validation

### Safe Testing Workflow

```bash
# 1. Connect to test environment
python cli.py connect-1password "Cascade REST Development Test" "Cascade Rest API Test"

# 2. Test with dry-run
python cli.py batch-update \
  --type page \
  --path-filter "2024-2025" \
  --field "academic_year" \
  --value "2024-2025" \
  --dry-run

# 3. Review results, then switch to production
python cli.py connect-1password "Cascade REST Development Production" "Cascade Rest API Production"

# 4. Execute for real
python cli.py batch-update \
  --type page \
  --path-filter "2024-2025" \
  --field "academic_year" \
  --value "2024-2025"
```

---

## 📋 Common Workflows

### Academic Year Updates

```bash
# 1. Export current state
python cli.py export-csv \
  --type page \
  --path-filter "2024-2025" \
  --output current_academic_year.csv

# 2. Update CSV with new values
# (Edit CSV file manually)

# 3. Import updates
python cli.py csv-import current_academic_year.csv \
  --operation metadata \
  --backup \
  --dry-run

# 4. Review and execute
python cli.py csv-import current_academic_year.csv \
  --operation metadata \
  --backup
```

### Faculty Directory Updates

```bash
# 1. Export faculty data
python cli.py export-csv \
  --type page \
  --path-filter "faculty" \
  --output faculty_directory.csv \
  --include-metadata

# 2. Update CSV with new faculty information
# (Edit CSV file)

# 3. Import updates
python cli.py csv-import faculty_directory.csv \
  --operation metadata \
  --backup
```

### Course Catalog Updates

```bash
# 1. Create scheduled job for weekly sync
python cli.py job-create \
  "Weekly Course Sync" \
  "weekly on Monday at 06:00" \
  csv-import course_catalog.csv --operation metadata \
  --environment "production"

# 2. Start scheduler
python cli.py scheduler-start
```

---

## 🛠️ Troubleshooting

### Common Issues

1. **"Not connected" error**: Run connect command first
2. **1Password authentication**: Run `op signin` if needed
3. **Permission errors**: Check API key permissions
4. **Dry-run first**: Always test with `--dry-run` flag

### Getting Help

```bash
# Get help for any command
python cli.py --help
python cli.py batch-update --help
python cli.py csv-import --help

# View all available commands
python cli.py --help
```

---

## 📝 Best Practices

1. **Always test first**: Use `--dry-run` flag for testing
2. **Use test environment**: Test on port 7443 before production
3. **Backup before changes**: Use `--backup` flag for important operations
4. **Monitor logs**: Check logs in `~/.cascade_cli/logs/`
5. **Use rollbacks**: Rollback operations are automatically created
6. **Schedule recurring tasks**: Use scheduled jobs for automation
7. **CSV for bulk changes**: Use CSV import/export for large datasets

---

## 🔗 Quick Reference

### Environment URLs

-   **Test**: `https://cms.example.edu:7443`
-   **Production**: `https://cms.example.edu:8443`

### 1Password Vaults

-   **Test**: "Cascade REST Development Test"
-   **Production**: "Cascade REST Development Production"

### Important Flags

-   `--dry-run`: Test mode, no actual changes
-   `--backup`: Create backup before changes
-   `--environment`: Specify environment (test/production)
-   `--limit`: Limit number of results
-   `--site`: Filter by specific site
