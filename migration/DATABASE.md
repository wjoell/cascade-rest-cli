# Migration Database Layer

## Overview

The migration database provides a SQLite-based tracking system for the Cascade CMS migration. It stores mappings between source paths and Cascade asset IDs for both folders and pages, enabling:

- **Fast lookups**: No need to rebuild folder maps via API calls
- **Resume capability**: Skip already-migrated assets automatically
- **Audit trail**: Complete record of what's been migrated
- **Future passes**: Efficient access to asset IDs for content migration

## Database Location

Default: `~/.cascade_cli/migration.db`

This location is consistent with other Cascade CLI data (sessions, logs, etc.).

## Schema

### Folders Table
```sql
CREATE TABLE folders (
    source_path TEXT PRIMARY KEY,      -- Relative path from source directory
    cascade_id TEXT NOT NULL,          -- Cascade asset ID
    parent_path TEXT,                  -- Parent folder's source path
    folder_name TEXT NOT NULL,         -- Name of the folder
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_folders_cascade_id ON folders(cascade_id);
CREATE INDEX idx_folders_parent ON folders(parent_path);
```

**Example data:**
- `source_path`: `"about/diversity"`
- `cascade_id`: `"e179c5267f000101269ba29b4762cdbd"`
- `parent_path`: `"about"`
- `folder_name`: `"diversity"`

### Pages Table
```sql
CREATE TABLE pages (
    source_path TEXT PRIMARY KEY,      -- Relative path from source directory
    cascade_id TEXT NOT NULL,          -- Cascade asset ID
    folder_path TEXT,                  -- Parent folder's source path
    page_name TEXT NOT NULL,           -- Name of the page (without .xml)
    xml_source TEXT,                   -- Full path to source XML file
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_pages_cascade_id ON pages(cascade_id);
CREATE INDEX idx_pages_folder ON pages(folder_path);
```

**Example data:**
- `source_path`: `"about/diversity/index.xml"`
- `cascade_id`: `"f289d6367f000101269ba29b4762cdbd"`
- `folder_path`: `"about/diversity"`
- `page_name`: `"index"`
- `xml_source`: `"/full/path/to/source/about/diversity/index.xml"`

## Python API

### Basic Usage

```python
from migration.database import get_db

# Get singleton database instance
db = get_db()

# Add a folder
db.add_folder(
    source_path="about/diversity",
    cascade_id="e179c5267f000101269ba29b4762cdbd",
    parent_path="about",
    folder_name="diversity"
)

# Add a page
db.add_page(
    source_path="about/diversity/index.xml",
    cascade_id="f289d6367f000101269ba29b4762cdbd",
    folder_path="about/diversity",
    page_name="index",
    xml_source="/full/path/to/source/about/diversity/index.xml"
)

# Check if asset exists
if db.folder_exists("about/diversity"):
    folder_id = db.get_folder_id("about/diversity")
    print(f"Folder already migrated: {folder_id}")

if db.page_exists("about/diversity/index.xml"):
    page_id = db.get_page_id("about/diversity/index.xml")
    print(f"Page already migrated: {page_id}")
```

### Building Folder Map

```python
# Load all folder IDs into memory (for page creation)
folder_id_map = db.build_folder_id_map()

# Returns: {"about": "abc123", "about/diversity": "def456", ...}
# Can be used for quick parent folder lookups
```

### Query Operations

```python
# Get all folders
all_folders = db.get_all_folders()

# Get folders under a specific path
about_folders = db.get_folders_in_path("about")

# Get pages in a specific folder
diversity_pages = db.get_pages_in_folder("about/diversity")

# Get statistics
stats = db.get_stats()
# Returns: {'folders': 14, 'pages': 39, 'total': 53}
```

### Context Manager

```python
# Use with context manager for explicit connection management
from migration.database import MigrationDatabase

with MigrationDatabase() as db:
    db.add_folder("test", "test-id", None, "test")
    print(db.get_stats())
# Connection automatically closed
```

## Integration with Migration Process

### Folder Creation (folder_creator.py)

```python
from migration.database import get_db

db = get_db()

# Before creating folder: Check if already exists
if db.folder_exists(folder_path):
    existing_id = db.get_folder_id(folder_path)
    folder_id_map[folder_path] = existing_id
    print(f"⏭️  Skipping (already migrated): {folder_path}")
    continue

# After creating folder: Store in database
if folder_id != 'unknown':
    db.add_folder(
        source_path=folder_path,
        cascade_id=folder_id,
        parent_path=parent_path,
        folder_name=folder_name
    )
    print(f"💾 Stored in database")
```

### Page Creation (page_creator.py)

```python
from migration.database import get_db

db = get_db()

# Load folder map from database (instead of API calls)
folder_id_map = db.build_folder_id_map()

# Before creating page: Check if already exists
if db.page_exists(source_path):
    existing_id = db.get_page_id(source_path)
    print(f"⏭️  Skipping (already migrated): {display_path}")
    continue

# After creating page: Store in database
if page_id != 'unknown':
    db.add_page(
        source_path=source_path,
        cascade_id=page_id,
        folder_path=folder_path,
        page_name=page_name,
        xml_source=xml_path
    )
    print(f"💾 Stored in database")
```

## CLI Commands

### Show Statistics

```bash
python cli.py migrate-db-stats
```

Output:
```
📊 Migration Database Statistics
========================================
Database: /Users/winston/.cascade_cli/migration.db

Assets tracked:
  Folders: 14
  Pages:   39
  Total:   53
```

### List Assets

```bash
# List all folders and pages (first 50)
python cli.py migrate-db-list

# List only folders
python cli.py migrate-db-list --folders

# List only pages
python cli.py migrate-db-list --pages

# Filter by path prefix
python cli.py migrate-db-list --path about

# Increase limit
python cli.py migrate-db-list --limit 100
```

Output example:
```
📁 Folders:
================================================================================
  about                                              | b2ced1e27f0001015b805e73d0886cfd
  about/diversity                                    | e179c5267f000101269ba29b4762cdbd
  about/diversity/campus-life                        | f289d6367f000101269ba29b4762cdbd

📄 Pages:
================================================================================
  about/index.xml                                    | a123b4567f000101269ba29b4762cdbd
  about/diversity/index.xml                          | b234c5678f000101269ba29b4762cdbd
```

### Clear Database

```bash
# Clear all migration data (with confirmation prompt)
python cli.py migrate-db-clear
```

**⚠️ Warning:** This is destructive and cannot be undone. Use with caution.

## Migration Workflow with Database

### Initial Shell Creation (Phase 1)

1. **Folders:**
   ```bash
   python cli.py migrate-run --folders-only --cms-path="..." --api-key="..."
   ```
   
   - Checks database for existing folders (skips if found)
   - Creates new folders via Asset Factory
   - Stores folder IDs in database immediately after creation
   - Builds in-memory folder map from database for parent lookups

2. **Pages:**
   ```bash
   python cli.py migrate-run --pages-only --cms-path="..." --api-key="..."
   ```
   
   - Loads folder map from database (fast!)
   - Checks database for existing pages (skips if found)
   - Creates new pages via Asset Factory
   - Stores page IDs in database immediately after creation

### Future Content Passes (Phase 2+)

The database enables efficient content migration in future passes:

```python
from migration.database import get_db

db = get_db()

# Get page ID for content update
page_id = db.get_page_id("about/diversity/index.xml")

# Get folder ID for operations
folder_id = db.get_folder_id("about/diversity")

# Get all pages in a folder for batch processing
pages = db.get_pages_in_folder("about/diversity")
for page in pages:
    update_page_content(page['cascade_id'], page['xml_source'])
```

## Benefits

### Before Database Layer

- **Folder map building**: Slow API calls to reconstruct hierarchy
- **No resume capability**: Re-process everything on failures
- **No tracking**: Can't easily tell what's been migrated
- **API heavy**: Constant API calls for ID lookups

### After Database Layer

- **Instant folder maps**: Load from SQLite in milliseconds
- **Smart resume**: Skip already-migrated assets automatically
- **Complete audit trail**: Query what's been done at any time
- **API efficient**: Only call API for actual creation operations
- **Future-ready**: IDs available for all future content passes

## Performance

- **Database size**: ~1KB per asset (53 assets = ~50KB)
- **Folder map loading**: <10ms for 500+ folders
- **Lookup operations**: O(1) with indexed queries
- **Storage overhead**: Negligible compared to source assets

## Maintenance

### Backup Database

```bash
cp ~/.cascade_cli/migration.db ~/.cascade_cli/migration.db.backup
```

### Restore Database

```bash
cp ~/.cascade_cli/migration.db.backup ~/.cascade_cli/migration.db
```

### Reset for Fresh Migration

```bash
python cli.py migrate-db-clear --yes
```

## Implementation Notes

### Singleton Pattern

The `get_db()` function returns a singleton instance to avoid multiple connections:

```python
from migration.database import get_db

db1 = get_db()
db2 = get_db()
# db1 and db2 are the same instance
```

### Connection Management

- Auto-creates database and tables on first use
- Connection persists for lifetime of Python process
- Use context manager for explicit control:
  ```python
  with MigrationDatabase() as db:
      # Use db
      pass
  # Connection closed
  ```

### INSERT OR REPLACE

Uses `INSERT OR REPLACE` for idempotency:
- Re-running migration on same assets updates `updated_at`
- No duplicate key errors
- Safe to re-run folder/page creation

## Future Enhancements

Potential additions for future migration phases:

1. **Migration phases tracking**: Which pass (shell, content, media, etc.)
2. **Content checksums**: Track if source content has changed
3. **Migration logs**: Store operation logs per asset
4. **Validation status**: Track which assets have been validated
5. **Rollback support**: Link to rollback operations
