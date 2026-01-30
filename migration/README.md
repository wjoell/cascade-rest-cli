# Migration Module

This module handles migration of content from the old Cascade site container to a new site container.

## Overview

The migration creates the folder structure and empty page shells in the new site. **This is phase 1** - it does NOT migrate content or structured data yet. That will come in a later phase.

## Source Structure

- **Source Directory**: `/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/migration-clean`
- **XML Files**: ~2,742 page XML files containing page metadata and structured data
- **HTML Partials**: Rendered HTML content from the `main` region of each page
- **Folders**: ~546 folders to recreate

### Directory Filtering

Directories starting with underscore (`_`) are automatically skipped:
- `__sandbox`
- `____documentation`
- `____reports`
- `_assets`
- `_reports`

## Target Configuration

Configured in `migration/config.py`:

- **Target Base Folder ID**: `b2ced1e27f0001015b805e73d0886cfd`
- **Base Page Asset ID**: `e179c5267f000101269ba29b4762cdbd` (Asset Factory template)
- **Base Folder Asset ID**: `fb6b2b757f000101773f7cb12b4b2845` (Asset Factory template)

### Asset Factory Pattern

This migration uses Cascade's **Asset Factory** pattern:
- Instead of creating assets from scratch, we **copy** pre-configured base assets
- Base assets contain default settings, workflows, and configurations
- Each copy is renamed with the appropriate folder/page name
- This ensures consistency and inherits proper setup from templates

## Commands

### 1. Scan Source Directory

Preview the scope of the migration:

```bash
python cli.py migrate-scan
```

This shows:
- Total folders to create
- Total pages to create
- Optionally displays sample folders/pages

### 2. Create Folders Only

Create the folder structure (default: dry-run):

```bash
# Dry-run (preview)
python cli.py migrate-folders

# Actually create folders
python cli.py migrate-folders --no-dry-run
```

**Important**: You must be connected to Cascade to create folders (use `python cli.py setup` or `python cli.py connect <connection-name>`)

### 3. Create Pages Only

Create empty page shells (default: dry-run):

```bash
# Dry-run (preview)
python cli.py migrate-pages

# Actually create pages (folders must already exist)
python cli.py migrate-pages --no-dry-run
```

### 4. Full Migration (Folders + Pages)

Run the complete migration orchestrator (default: dry-run):

```bash
# Dry-run (preview both phases)
python cli.py migrate-run

# Actually perform migration
python cli.py migrate-run --no-dry-run

# Create folders only
python cli.py migrate-run --folders-only

# Create pages only (assumes folders exist)
python cli.py migrate-run --pages-only
```

## Workflow

### Recommended Migration Process

1. **Scan and validate source data**:
   ```bash
   python cli.py migrate-scan
   ```

2. **Preview folder creation**:
   ```bash
   python cli.py migrate-folders
   ```

3. **Create folders** (ensure you're connected first):
   ```bash
   python cli.py setup  # or connect to existing connection
   python cli.py migrate-folders --no-dry-run
   ```

4. **Preview page creation**:
   ```bash
   python cli.py migrate-pages
   ```

5. **Create pages**:
   ```bash
   python cli.py migrate-pages --no-dry-run
   ```

### Alternative: All at Once

```bash
python cli.py setup
python cli.py migrate-run --no-dry-run
```

## Module Structure

```
migration/
├── __init__.py              # Package initialization
├── config.py                # Configuration (IDs, paths, rules)
├── scanner.py               # Discover folders and XML files
├── folder_creator.py        # Create folder structure in Cascade
├── page_creator.py          # Create page shells in Cascade
├── orchestrator.py          # Coordinate full migration
└── README.md               # This file
```

## Key Features

### Scanner (`scanner.py`)

- Traverses source directory recursively
- Filters out underscore-prefixed directories
- Discovers all XML files
- Extracts page names (strips `.xml` extension)
- Maps folder structure

### Folder Creator (`folder_creator.py`)

- Creates folders in hierarchical order (parent → child)
- Tracks folder IDs for parent-child relationships
- Supports dry-run preview
- Reports success/failure counts

### Page Creator (`page_creator.py`)

- Creates empty page shells from XML files
- Uses base page template for all pages
- Requires folder structure to exist first
- Page names match XML filenames (without extension)
- Supports dry-run preview

### Orchestrator (`orchestrator.py`)

- Coordinates full workflow
- Phase 1: Folder creation
- Phase 2: Page creation
- Comprehensive progress reporting
- Error handling and rollback preparation

## Important Notes

### Page Naming

Cascade page assets do NOT have file extensions. For example:
- `index.xml` → page named `index` in Cascade
- `about.xml` → page named `about` in Cascade

### Current Limitations (Phase 1)

This initial migration creates:
- ✅ Folder structure
- ✅ Empty page shells

It does NOT yet migrate:
- ❌ Page content
- ❌ Structured data
- ❌ Metadata
- ❌ Images/files
- ❌ Relationships/links

These will be addressed in subsequent phases.

## Testing

Run module tests independently:

```bash
# Test scanner
python -m migration.scanner

# Test folder creator (dry-run)
python -m migration.folder_creator

# Test page creator (dry-run)
python -m migration.page_creator

# Test orchestrator (dry-run)
python -m migration.orchestrator
```

## Troubleshooting

### "Not connected" Error

Make sure you're connected to Cascade before running non-dry-run operations:

```bash
python cli.py setup
# or
python cli.py connect <connection-name>
```

### Folder ID Not Found

If page creation fails because folders don't exist:
1. Run folder creation first: `python cli.py migrate-folders --no-dry-run`
2. Then run page creation: `python cli.py migrate-pages --no-dry-run`

### Source Path Not Found

Verify the source path in `migration/config.py` is correct:
```python
SOURCE_DIR = "/Users/winston/Repositories/wjoell/slc-edu-migration/source-assets/migration-clean"
```

## Next Steps (Future Phases)

Phase 2 will add:
- XML parsing to extract structured data
- Content migration (HTML partials)
- Metadata mapping to new schema
- Data definition transformation
- Image and file asset migration
