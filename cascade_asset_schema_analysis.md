# Cascade Asset Schema Analysis

## Overview

This document analyzes the actual JSON structure of Cascade assets based on real data from the SarahLawrence.edu site. This analysis will help inform batch operations, filtering, and metadata handling in the CLI.

## Asset Types Analyzed

### 1. Page Assets

**Example**: `/admission/visit/index` (ID: `40deb3bac0a8022b3fd92ff26ece5b84`)

#### Key Structure Elements:

-   **Basic Properties**:

    -   `id`: Unique asset identifier
    -   `path`: Full path within the site
    -   `name`: Asset name (filename)
    -   `type`: Asset type (`page`, `file`, `format`, etc.)
    -   `siteId`: Parent site identifier
    -   `siteName`: Human-readable site name

-   **Metadata Structure**:

    ```json
    "metadata": {
      "displayName": "Visits & More",
      "title": "Experience Sarah Lawrence College",
      "summary": "",
      "teaser": "",
      "keywords": "Undergraduate,application,statistics,visit,tours...",
      "metaDescription": "",
      "author": "",
      "dynamicFields": [
        {
          "name": "field-name",
          "fieldValues": [
            {
              "value": "field-value"
            }
          ]
        }
      ]
    }
    ```

-   **Tags Structure**:

    ```json
    "tags": []  // Simple array of tag strings
    ```

-   **Template Configuration**:
    ```json
    "templateConfigurations": [
      {
        "name": "configuration-name",
        "defaultConfiguration": true/false,
        "templateId": "template-id",
        "templatePath": "template-path",
        "pageRegions": [...]
      }
    ]
    ```

### 2. File Assets

**Example**: PDF file (ID: `dea1ce68c0a8022b680c239f45d81063`)

#### Key Differences from Pages:

-   **Content**: Contains actual file data as byte array
-   **Metadata Set**: Uses different metadata set (`Config:Default`)
-   **File-specific fields**: `filesize`, `assetType`, etc.
-   **Same tag structure**: `"tags": []` (empty array)

## Key Schema Insights

### 1. Tags vs Dynamic Fields

**Tags** are simple string arrays:

```json
"tags": ["tag1", "tag2", "tag3"]
```

**Dynamic Fields** are structured key-value pairs:

```json
"dynamicFields": [
  {
    "name": "page-heading",
    "fieldValues": [{"value": "Page Title"}]
  },
  {
    "name": "assignment",
    "fieldValues": []  // Can be empty
  }
]
```

### 2. Metadata Handling

**Standard Metadata** (always present):

-   `displayName`, `title`, `summary`, `teaser`, `keywords`, `metaDescription`, `author`

**Dynamic Metadata** (varies by asset type):

-   Different metadata sets for different asset types
-   Field values can be empty arrays `[]` or contain objects with `value` property
-   Some fields are multi-valued (arrays), others are single-valued

### 3. Asset Relationships

**Parent/Child**:

-   `parentFolderId`: Parent folder identifier
-   `parentFolderPath`: Human-readable parent path

**Site Context**:

-   `siteId`: Site identifier
-   `siteName`: Site display name

### 4. Publishing & Workflow

**Publishing Flags**:

-   `shouldBePublished`: Boolean
-   `shouldBeIndexed`: Boolean
-   `lastPublishedDate`: ISO timestamp
-   `lastPublishedBy`: User identifier

**Review Settings**:

-   `reviewOnSchedule`: Boolean
-   `reviewEvery`: Days (180 = 6 months)

## Implications for CLI Operations

### 1. Batch Tag Operations

```python
# Tags are simple arrays - easy to append/remove
current_tags = asset["tags"]
new_tags = current_tags + ["new-tag"]
```

### 2. Dynamic Field Updates

```python
# More complex - need to find existing field or create new
def update_dynamic_field(asset, field_name, new_value):
    for field in asset["metadata"]["dynamicFields"]:
        if field["name"] == field_name:
            field["fieldValues"] = [{"value": new_value}]
            return
    # Field doesn't exist - add it
    asset["metadata"]["dynamicFields"].append({
        "name": field_name,
        "fieldValues": [{"value": new_value}]
    })
```

### 3. Path-based Filtering

```python
# Filter by path patterns
def filter_by_path_pattern(assets, pattern):
    return [asset for asset in assets if pattern in asset["path"]]
```

### 4. Metadata Set Handling

-   Different asset types use different metadata sets
-   Need to handle field variations across metadata sets
-   Some fields may not exist in all asset types

## Recommendations for CLI Enhancement

### 1. Tag Operations

-   ✅ Current implementation should work well
-   Tags are simple arrays, easy to manipulate

### 2. Dynamic Field Operations

-   ⚠️ Need to handle field existence checking
-   ⚠️ Need to handle empty vs populated field values
-   ⚠️ Need to handle multi-valued fields

### 3. Batch Operations

-   ✅ Path filtering should work as expected
-   ✅ Asset type filtering is straightforward
-   ⚠️ Metadata operations need field-specific logic

### 4. CSV Export/Import

-   ✅ Basic fields (id, path, name, type) are straightforward
-   ⚠️ Dynamic fields need special handling (flatten to columns)
-   ⚠️ Tags can be exported as comma-separated string

## Sample Asset Structures

### Minimal Page Asset

```json
{
    "id": "asset-id",
    "path": "path/to/page",
    "name": "page-name",
    "type": "page",
    "siteId": "site-id",
    "siteName": "Site Name",
    "metadata": {
        "displayName": "Page Title",
        "title": "Page Title",
        "summary": "",
        "teaser": "",
        "keywords": "",
        "metaDescription": "",
        "author": "",
        "dynamicFields": []
    },
    "tags": [],
    "shouldBePublished": true,
    "shouldBeIndexed": true,
    "lastModifiedDate": "2025-01-01T00:00:00.000Z",
    "lastModifiedBy": "user",
    "createdDate": "2025-01-01T00:00:00.000Z",
    "createdBy": "user"
}
```

This analysis provides the foundation for understanding how to properly handle Cascade assets in batch operations, filtering, and metadata manipulation.

