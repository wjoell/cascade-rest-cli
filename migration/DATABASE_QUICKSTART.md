# Database Quick Start Guide

## TL;DR

The migration database tracks asset IDs so you can:
- Skip already-migrated assets (resume capability)
- Fast folder map lookups (no API calls)
- Query migration progress at any time

## Quick Commands

```bash
# Check what's in the database
python cli.py migrate-db-stats

# List tracked assets
python cli.py migrate-db-list

# Clear database (start fresh)
python cli.py migrate-db-clear --yes
```

## How It Works

### Without Database (Old Behavior)
```bash
# Run migration
python cli.py migrate-run --folders-only --cms-path="..." --api-key="..."

# If it fails halfway through:
# - Must restart from beginning
# - Re-attempts to create all folders (collisions!)
# - No way to track progress
```

### With Database (New Behavior)
```bash
# Run migration
python cli.py migrate-run --folders-only --cms-path="..." --api-key="..."

# Database automatically:
# ✅ Stores folder IDs as they're created
# ✅ Loads existing IDs on startup
# ✅ Skips folders already in database

# If it fails halfway through:
python cli.py migrate-run --folders-only --cms-path="..." --api-key="..."
# ✅ Automatically skips already-migrated folders
# ✅ Only creates missing folders
# ✅ Resumes exactly where it left off
```

## During Migration

### Monitor Progress
```bash
# In another terminal
watch -n 5 "python cli.py migrate-db-stats"
```

Output updates every 5 seconds:
```
📊 Migration Database Statistics
========================================
Database: /Users/winston/.cascade_cli/migration.db

Assets tracked:
  Folders: 14
  Pages:   39
  Total:   53
```

### Check Specific Folder
```bash
python cli.py migrate-db-list --path "about"
```

## After Migration

### Verify Completion
```bash
python cli.py migrate-db-stats

# Should show:
# Folders: 546 (or ~532 if "about" excluded)
# Pages: 2742 (or ~2703 if "about" excluded)
```

### List Assets
```bash
# Show all folders
python cli.py migrate-db-list --folders --limit 100

# Show all pages
python cli.py migrate-db-list --pages --limit 100

# Show specific path
python cli.py migrate-db-list --path "about/diversity"
```

## Common Scenarios

### Scenario 1: Migration Failed Halfway
```bash
# Just re-run the same command
python cli.py migrate-run --cms-path="..." --api-key="..."

# Database automatically:
# - Skips folders already created
# - Skips pages already created
# - Only creates what's missing
```

### Scenario 2: Need to Start Fresh
```bash
# 1. Clear database
python cli.py migrate-db-clear --yes

# 2. (Optional) Delete assets in Cascade UI

# 3. Re-run migration
python cli.py migrate-run --cms-path="..." --api-key="..."
```

### Scenario 3: Check Progress
```bash
# Quick stats
python cli.py migrate-db-stats

# Detailed list of last 50 assets
python cli.py migrate-db-list
```

### Scenario 4: Migrate Different Folders Separately
```bash
# The database tracks by source path, so you can:

# 1. Edit TEST_FOLDER_FILTER = "academics" in config.py
python cli.py migrate-run --cms-path="..." --api-key="..."

# 2. Edit TEST_FOLDER_FILTER = "admissions" in config.py
python cli.py migrate-run --cms-path="..." --api-key="..."

# Database tracks all of them independently
python cli.py migrate-db-stats
# Shows: Folders from both "academics" and "admissions"
```

## Benefits

| Feature | Without DB | With DB |
|---------|-----------|---------|
| Resume on failure | ❌ Start over | ✅ Auto-skip created |
| Progress tracking | ❌ None | ✅ Real-time stats |
| Folder map loading | 🐌 50+ API calls | ⚡ <10ms SQLite |
| Future content passes | 🐌 Rebuild every time | ⚡ Instant ID lookup |

## Database Details

**Location:** `~/.cascade_cli/migration.db`

**Schema:**
- `folders` table: source_path → cascade_id
- `pages` table: source_path → cascade_id

**Size:** ~1KB per asset (~3MB for 3,000 assets)

**Operations:** O(1) indexed lookups

## Python API

For future content migration scripts:

```python
from migration.database import get_db

db = get_db()

# Get page ID for content update
page_id = db.get_page_id("about/diversity/index.xml")

# Get all pages in a folder
pages = db.get_pages_in_folder("about/diversity")
for page in pages:
    print(f"Update page {page['cascade_id']} from {page['xml_source']}")

# Get folder ID
folder_id = db.get_folder_id("about/diversity")
```

## Troubleshooting

### Database not updating
- ✅ Check `use_db=True` is set (it's default)
- ✅ Verify database file exists: `ls -lh ~/.cascade_cli/migration.db`

### Want to disable database temporarily
```bash
# Add --no-db flag (not implemented yet, but can add if needed)
# For now, just clear it: python cli.py migrate-db-clear --yes
```

### Database shows wrong count
```bash
# Backup first
cp ~/.cascade_cli/migration.db ~/.cascade_cli/migration.db.backup

# Clear and re-run
python cli.py migrate-db-clear --yes
python cli.py migrate-run --cms-path="..." --api-key="..."
```

## Next Steps

1. **Now:** Use database for shell creation phase
2. **Later:** Use database for content migration passes
3. **Future:** Extend database schema for content checksums, validation status, etc.

## Questions?

See full documentation: `migration/DATABASE.md`
