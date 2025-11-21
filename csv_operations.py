"""
CSV import/export operations for Cascade REST CLI
"""

import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import shutil

from config import CSV_ENCODING, CSV_DELIMITER, CSV_QUOTECHAR, CSV_BACKUP_DIR
from logging_config import logger


class CSVOperations:
    """Handles CSV import/export for batch operations"""

    def __init__(self):
        self.backup_dir = CSV_BACKUP_DIR
        self.backup_dir.mkdir(exist_ok=True)

    def export_assets_to_csv(
        self, assets: List[Dict[str, Any]], filename: str, include_metadata: bool = True
    ) -> str:
        """Export assets to CSV file"""
        if not assets:
            raise ValueError("No assets to export")

        # Create backup of existing file
        csv_path = Path(filename)
        if csv_path.exists():
            self._backup_file(csv_path)

        # Determine columns based on assets and options
        columns = self._get_export_columns(assets[0], include_metadata)

        with open(csv_path, "w", newline="", encoding=CSV_ENCODING) as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=columns,
                delimiter=CSV_DELIMITER,
                quotechar=CSV_QUOTECHAR,
                quoting=csv.QUOTE_MINIMAL,
            )

            writer.writeheader()

            for asset in assets:
                row = self._asset_to_row(asset, columns, include_metadata)
                writer.writerow(row)

        logger.log_operation_end(
            "csv_export",
            True,
            filename=str(csv_path),
            asset_count=len(assets),
            columns=len(columns),
        )

        return str(csv_path)

    def import_csv_to_assets(self, filename: str) -> List[Dict[str, Any]]:
        """Import assets from CSV file"""
        csv_path = Path(filename)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {filename}")

        # Create backup of original file
        self._backup_file(csv_path)

        assets = []

        with open(csv_path, "r", newline="", encoding=CSV_ENCODING) as csvfile:
            # Detect delimiter if not specified
            sample = csvfile.read(1024)
            csvfile.seek(0)
            sniffer = csv.Sniffer()
            detected_delimiter = sniffer.sniff(sample).delimiter

            reader = csv.DictReader(
                csvfile, delimiter=detected_delimiter, quotechar=CSV_QUOTECHAR
            )

            for row_num, row in enumerate(reader, 1):
                try:
                    asset = self._row_to_asset(row)
                    assets.append(asset)
                except Exception as e:
                    logger.log_error(
                        e,
                        {"filename": filename, "row_number": row_num, "row_data": row},
                    )
                    # Continue processing other rows

        logger.log_operation_end(
            "csv_import", True, filename=str(csv_path), asset_count=len(assets)
        )

        return assets

    def create_template_csv(self, asset_type: str, filename: str) -> str:
        """Create a template CSV file for a specific asset type"""
        template_columns = [
            "id",
            "name",
            "path",
            "type",
            "site",
            "metadata_field_1",
            "metadata_field_2",
            "tag_1",
            "tag_2",
        ]

        # Add example row
        example_row = {
            "id": "example_asset_id",
            "name": "Example Asset Name",
            "path": "/path/to/asset",
            "type": asset_type,
            "site": "example_site",
            "metadata_field_1": "example_metadata_value",
            "metadata_field_2": "another_metadata_value",
            "tag_1": "example_tag_value",
            "tag_2": "another_tag_value",
        }

        csv_path = Path(filename)
        if csv_path.exists():
            self._backup_file(csv_path)

        with open(csv_path, "w", newline="", encoding=CSV_ENCODING) as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=template_columns,
                delimiter=CSV_DELIMITER,
                quotechar=CSV_QUOTECHAR,
                quoting=csv.QUOTE_MINIMAL,
            )

            writer.writeheader()
            writer.writerow(example_row)

        logger.log_operation_end(
            "template_creation", True, filename=str(csv_path), asset_type=asset_type
        )

        return str(csv_path)

    def batch_update_from_csv(
        self, filename: str, operation_type: str = "metadata", cascade_cli=None
    ) -> Dict[str, Any]:
        """Perform batch operations from CSV file"""
        if not cascade_cli:
            raise ValueError("CascadeCLI instance required for batch operations")

        assets = self.import_csv_to_assets(filename)

        results = {
            "total": len(assets),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

        logger.log_operation_start(
            "batch_update_from_csv",
            filename=filename,
            operation_type=operation_type,
            asset_count=len(assets),
        )

        for i, asset in enumerate(assets, 1):
            try:
                asset_id = asset.get("id")
                asset_type = asset.get("type", "page")

                if not asset_id:
                    results["skipped"] += 1
                    continue

                # Perform the specified operation
                if operation_type == "metadata":
                    # Update metadata fields
                    metadata_updates = {
                        k: v
                        for k, v in asset.items()
                        if k.startswith("metadata_") and v
                    }
                    for field, value in metadata_updates.items():
                        field_name = field.replace("metadata_", "")
                        cascade_cli.update_metadata(
                            asset_type, asset_id, field_name, value
                        )

                elif operation_type == "tags":
                    # Update tag values
                    tag_updates = {
                        k: v for k, v in asset.items() if k.startswith("tag_") and v
                    }
                    for tag, value in tag_updates.items():
                        tag_name = tag.replace("tag_", "")
                        cascade_cli.set_tag(asset_type, asset_id, tag_name, value)

                results["successful"] += 1

                # Log progress
                if i % 10 == 0:
                    logger.log_batch_progress("batch_update_from_csv", i, len(assets))

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"asset_id": asset.get("id"), "error": str(e)})
                logger.log_error(e, {"asset": asset, "operation": operation_type})

        logger.log_operation_end(
            "batch_update_from_csv", results["failed"] == 0, **results
        )

        return results

    def _get_export_columns(
        self, sample_asset: Dict[str, Any], include_metadata: bool
    ) -> List[str]:
        """Determine which columns to include in export"""
        base_columns = ["id", "name", "path", "type", "site"]

        if include_metadata:
            # Add metadata fields
            metadata_fields = [
                k
                for k in sample_asset.keys()
                if k.startswith("metadata_") or k.startswith("tag_")
            ]
            base_columns.extend(sorted(metadata_fields))

        return base_columns

    def _asset_to_row(
        self, asset: Dict[str, Any], columns: List[str], include_metadata: bool
    ) -> Dict[str, str]:
        """Convert asset dict to CSV row"""
        row = {}

        for col in columns:
            if col in asset:
                value = asset[col]
                # Convert to string, handling different data types
                if isinstance(value, (dict, list)):
                    row[col] = json.dumps(value)
                else:
                    row[col] = str(value) if value is not None else ""
            else:
                row[col] = ""

        return row

    def _row_to_asset(self, row: Dict[str, str]) -> Dict[str, Any]:
        """Convert CSV row to asset dict"""
        asset = {}

        for key, value in row.items():
            if not value.strip():
                continue

            # Try to parse JSON values
            if value.startswith(("{", "[")):
                try:
                    asset[key] = json.loads(value)
                except json.JSONDecodeError:
                    asset[key] = value
            else:
                asset[key] = value

        return asset

    def _backup_file(self, file_path: Path):
        """Create backup of file before modification"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = self.backup_dir / backup_filename

        shutil.copy2(file_path, backup_path)
        logger.log_operation_end(
            "file_backup", True, original=str(file_path), backup=str(backup_path)
        )


# Global CSV operations instance
csv_ops = CSVOperations()
