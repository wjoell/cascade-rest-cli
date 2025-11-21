"""
Unit tests for CSVOperations

Tests CSV export, import, and batch operations including:
- Export assets to CSV with metadata
- Import assets from CSV preserving metadata and tags  
- Create template CSV files
- Batch updates from CSV
"""

import unittest
import tempfile
import csv
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import pytest

from csv_operations import CSVOperations


class TestCSVExport(unittest.TestCase):
    """Test CSV export functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.csv_ops = CSVOperations()
        self.temp_dir = tempfile.mkdtemp()

        self.sample_assets = [
            {
                "id": "asset1",
                "name": "test-page",
                "path": "/content/test-page",
                "type": "page",
                "site": "example.com",
                "metadata_title": "Test Page",
                "metadata_department": "Computer Science",
                "tag_category": "faculty",
            },
            {
                "id": "asset2",
                "name": "test-file",
                "path": "/documents/test.pdf",
                "type": "file",
                "site": "example.com",
                "metadata_title": "Test Document",
                "tag_category": "resources",
            },
        ]

    def tearDown(self):
        """Clean up temporary files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_assets_to_csv(self):
        """Test exporting assets to CSV file"""
        output_file = Path(self.temp_dir) / "test_export.csv"

        result_path = self.csv_ops.export_assets_to_csv(
            self.sample_assets, str(output_file), include_metadata=True
        )

        # Verify file was created
        self.assertTrue(Path(result_path).exists())

        # Read and verify CSV content
        with open(result_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["id"], "asset1")
            self.assertEqual(rows[0]["name"], "test-page")
            self.assertEqual(rows[0]["metadata_title"], "Test Page")

    def test_export_without_metadata(self):
        """Test exporting assets without metadata fields"""
        output_file = Path(self.temp_dir) / "test_export_no_metadata.csv"

        result_path = self.csv_ops.export_assets_to_csv(
            self.sample_assets, str(output_file), include_metadata=False
        )

        # Read and verify CSV content
        with open(result_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames

            # Should have base columns only
            self.assertIn("id", columns)
            self.assertIn("name", columns)
            self.assertNotIn("metadata_title", columns)

    def test_export_with_special_characters(self):
        """Test exporting assets with special characters"""
        assets_with_special_chars = [
            {
                "id": "asset1",
                "name": "test,page",
                "path": '/content/"special"/page',
                "type": "page",
                "site": "example.com",
                "metadata_title": 'Page with "quotes"',
            }
        ]

        output_file = Path(self.temp_dir) / "test_special_chars.csv"
        result_path = self.csv_ops.export_assets_to_csv(
            assets_with_special_chars, str(output_file), include_metadata=True
        )

        # Read and verify CSV handles special characters
        with open(result_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            self.assertEqual(rows[0]["name"], "test,page")
            self.assertEqual(rows[0]["metadata_title"], 'Page with "quotes"')

    def test_export_with_nested_data(self):
        """Test exporting assets with nested dict/list data"""
        assets_with_nested = [
            {
                "id": "asset1",
                "name": "test-page",
                "path": "/content/test",
                "type": "page",
                "site": "example.com",
                "metadata_complex": {"nested": "value", "array": [1, 2, 3]},
            }
        ]

        output_file = Path(self.temp_dir) / "test_nested.csv"
        result_path = self.csv_ops.export_assets_to_csv(
            assets_with_nested, str(output_file), include_metadata=True
        )

        # Read and verify JSON serialization of complex data
        with open(result_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # Should have JSON-encoded complex data
            self.assertIn("{", rows[0].get("metadata_complex", ""))

    def test_export_empty_asset_list_raises_error(self):
        """Test that exporting empty list raises ValueError"""
        output_file = Path(self.temp_dir) / "test_empty.csv"

        with self.assertRaises(ValueError):
            self.csv_ops.export_assets_to_csv([], str(output_file))

    def test_export_creates_backup_of_existing_file(self):
        """Test that export creates backup of existing file"""
        output_file = Path(self.temp_dir) / "test_backup.csv"

        # Create initial file
        output_file.write_text("existing content")

        # Export should create backup
        self.csv_ops.export_assets_to_csv(
            self.sample_assets, str(output_file), include_metadata=True
        )

        # Check that backup was created
        backups = list(self.csv_ops.backup_dir.glob("test_backup_*.csv"))
        self.assertGreater(len(backups), 0)


class TestCSVImport(unittest.TestCase):
    """Test CSV import functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.csv_ops = CSVOperations()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_import_csv_to_assets(self):
        """Test importing assets from CSV file"""
        # Create test CSV file
        csv_file = Path(self.temp_dir) / "test_import.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "id",
                    "name",
                    "path",
                    "type",
                    "site",
                    "metadata_title",
                    "tag_category",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "id": "asset1",
                    "name": "test-page",
                    "path": "/content/test",
                    "type": "page",
                    "site": "example.com",
                    "metadata_title": "Test Page",
                    "tag_category": "faculty",
                }
            )
            writer.writerow(
                {
                    "id": "asset2",
                    "name": "test-file",
                    "path": "/documents/test.pdf",
                    "type": "file",
                    "site": "example.com",
                    "metadata_title": "Test Document",
                    "tag_category": "resources",
                }
            )

        # Import assets
        assets = self.csv_ops.import_csv_to_assets(str(csv_file))

        # Verify import
        self.assertEqual(len(assets), 2)
        self.assertEqual(assets[0]["id"], "asset1")
        self.assertEqual(assets[0]["metadata_title"], "Test Page")
        self.assertEqual(assets[1]["tag_category"], "resources")

    def test_import_preserves_metadata_and_tags(self):
        """Test that import preserves metadata and tag fields"""
        csv_file = Path(self.temp_dir) / "test_metadata_tags.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "id",
                    "name",
                    "type",
                    "metadata_title",
                    "metadata_department",
                    "metadata_author",
                    "tag_category",
                    "tag_academic_year",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "id": "asset1",
                    "name": "test-page",
                    "type": "page",
                    "metadata_title": "Test Title",
                    "metadata_department": "Computer Science",
                    "metadata_author": "John Doe",
                    "tag_category": "faculty",
                    "tag_academic_year": "2024-2025",
                }
            )

        assets = self.csv_ops.import_csv_to_assets(str(csv_file))

        # Verify all metadata and tags are preserved
        self.assertEqual(assets[0]["metadata_title"], "Test Title")
        self.assertEqual(assets[0]["metadata_department"], "Computer Science")
        self.assertEqual(assets[0]["metadata_author"], "John Doe")
        self.assertEqual(assets[0]["tag_category"], "faculty")
        self.assertEqual(assets[0]["tag_academic_year"], "2024-2025")

    def test_import_handles_json_values(self):
        """Test that import correctly parses JSON values"""
        csv_file = Path(self.temp_dir) / "test_json.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["id", "name", "complex_field"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "id": "asset1",
                    "name": "test",
                    "complex_field": '{"nested": "value", "array": [1, 2, 3]}',
                }
            )

        assets = self.csv_ops.import_csv_to_assets(str(csv_file))

        # Verify JSON was parsed
        self.assertIsInstance(assets[0]["complex_field"], dict)
        self.assertEqual(assets[0]["complex_field"]["nested"], "value")

    def test_import_skips_empty_fields(self):
        """Test that import skips empty fields"""
        csv_file = Path(self.temp_dir) / "test_empty_fields.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["id", "name", "empty_field", "filled_field"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "id": "asset1",
                    "name": "test",
                    "empty_field": "",
                    "filled_field": "value",
                }
            )

        assets = self.csv_ops.import_csv_to_assets(str(csv_file))

        # Verify empty fields are not included
        self.assertNotIn("empty_field", assets[0])
        self.assertIn("filled_field", assets[0])

    def test_import_nonexistent_file_raises_error(self):
        """Test that importing nonexistent file raises FileNotFoundError"""
        with self.assertRaises(FileNotFoundError):
            self.csv_ops.import_csv_to_assets("/nonexistent/file.csv")

    def test_import_creates_backup(self):
        """Test that import creates backup of original file"""
        csv_file = Path(self.temp_dir) / "test_import_backup.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "name"])
            writer.writeheader()
            writer.writerow({"id": "asset1", "name": "test"})

        self.csv_ops.import_csv_to_assets(str(csv_file))

        # Check that backup was created
        backups = list(self.csv_ops.backup_dir.glob("test_import_backup_*.csv"))
        self.assertGreater(len(backups), 0)


class TestCSVTemplates(unittest.TestCase):
    """Test CSV template creation"""

    def setUp(self):
        """Set up test fixtures"""
        self.csv_ops = CSVOperations()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_template_csv(self):
        """Test creating template CSV file"""
        template_file = Path(self.temp_dir) / "template.csv"

        result_path = self.csv_ops.create_template_csv("page", str(template_file))

        # Verify file was created
        self.assertTrue(Path(result_path).exists())

        # Read and verify template
        with open(result_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            columns = reader.fieldnames

            # Verify has expected columns
            self.assertIn("id", columns)
            self.assertIn("name", columns)
            self.assertIn("type", columns)
            self.assertIn("metadata_field_1", columns)
            self.assertIn("tag_1", columns)

            # Verify has example row
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["type"], "page")

    def test_template_for_different_asset_types(self):
        """Test creating templates for different asset types"""
        for asset_type in ["page", "file", "folder", "block"]:
            template_file = Path(self.temp_dir) / f"template_{asset_type}.csv"
            result_path = self.csv_ops.create_template_csv(asset_type, str(template_file))

            with open(result_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                self.assertEqual(rows[0]["type"], asset_type)


class TestCSVBatchOperations(unittest.TestCase):
    """Test batch operations from CSV"""

    def setUp(self):
        """Set up test fixtures"""
        self.csv_ops = CSVOperations()
        self.temp_dir = tempfile.mkdtemp()

        # Create mock cascade CLI
        self.mock_cascade_cli = MagicMock()

    def tearDown(self):
        """Clean up temporary files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_batch_update_metadata_from_csv(self):
        """Test batch updating metadata from CSV file"""
        # Create test CSV
        csv_file = Path(self.temp_dir) / "batch_update.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["id", "type", "metadata_title", "metadata_department"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "id": "asset1",
                    "type": "page",
                    "metadata_title": "New Title",
                    "metadata_department": "Computer Science",
                }
            )
            writer.writerow(
                {
                    "id": "asset2",
                    "type": "page",
                    "metadata_title": "Another Title",
                    "metadata_department": "Mathematics",
                }
            )

        # Perform batch update
        results = self.csv_ops.batch_update_from_csv(
            str(csv_file), operation_type="metadata", cascade_cli=self.mock_cascade_cli
        )

        # Verify results
        self.assertEqual(results["total"], 2)
        self.assertEqual(results["successful"], 2)
        self.assertEqual(results["failed"], 0)

        # Verify update_metadata was called correctly
        self.assertEqual(self.mock_cascade_cli.update_metadata.call_count, 4)  # 2 assets * 2 fields

    def test_batch_update_tags_from_csv(self):
        """Test batch updating tags from CSV file"""
        csv_file = Path(self.temp_dir) / "batch_tags.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["id", "type", "tag_category", "tag_year"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "id": "asset1",
                    "type": "page",
                    "tag_category": "faculty",
                    "tag_year": "2024",
                }
            )

        results = self.csv_ops.batch_update_from_csv(
            str(csv_file), operation_type="tags", cascade_cli=self.mock_cascade_cli
        )

        # Verify results
        self.assertEqual(results["total"], 1)
        self.assertEqual(results["successful"], 1)

        # Verify set_tag was called
        self.assertEqual(self.mock_cascade_cli.set_tag.call_count, 2)  # 2 tags

    def test_batch_update_skips_assets_without_id(self):
        """Test that batch update skips assets without ID"""
        csv_file = Path(self.temp_dir) / "batch_no_id.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["id", "type", "metadata_title"]
            )
            writer.writeheader()
            writer.writerow({"id": "", "type": "page", "metadata_title": "Title"})
            writer.writerow(
                {"id": "asset1", "type": "page", "metadata_title": "Valid"}
            )

        results = self.csv_ops.batch_update_from_csv(
            str(csv_file), operation_type="metadata", cascade_cli=self.mock_cascade_cli
        )

        # Verify skipped count
        self.assertEqual(results["skipped"], 1)
        self.assertEqual(results["successful"], 1)

    def test_batch_update_handles_errors(self):
        """Test that batch update handles errors gracefully"""
        csv_file = Path(self.temp_dir) / "batch_errors.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["id", "type", "metadata_title"]
            )
            writer.writeheader()
            writer.writerow({"id": "asset1", "type": "page", "metadata_title": "Title1"})
            writer.writerow({"id": "asset2", "type": "page", "metadata_title": "Title2"})

        # Mock an error on second asset
        self.mock_cascade_cli.update_metadata.side_effect = [
            None,  # First call succeeds
            Exception("Update failed"),  # Second call fails
        ]

        results = self.csv_ops.batch_update_from_csv(
            str(csv_file), operation_type="metadata", cascade_cli=self.mock_cascade_cli
        )

        # Verify error handling
        self.assertEqual(results["successful"], 1)
        self.assertEqual(results["failed"], 1)
        self.assertEqual(len(results["errors"]), 1)

    def test_batch_update_requires_cascade_cli(self):
        """Test that batch update requires CascadeCLI instance"""
        csv_file = Path(self.temp_dir) / "batch_test.csv"
        csv_file.write_text("id,type\nasset1,page")

        with self.assertRaises(ValueError):
            self.csv_ops.batch_update_from_csv(
                str(csv_file), operation_type="metadata", cascade_cli=None
            )


@pytest.mark.parametrize(
    "asset_count,include_metadata",
    [
        (1, True),
        (5, True),
        (10, False),
        (100, True),
    ],
)
def test_export_import_roundtrip(asset_count, include_metadata):
    """Test that export and import are symmetrical (roundtrip)"""
    csv_ops = CSVOperations()
    temp_dir = tempfile.mkdtemp()

    try:
        # Generate test assets
        assets = [
            {
                "id": f"asset{i}",
                "name": f"test-{i}",
                "path": f"/content/test-{i}",
                "type": "page",
                "site": "example.com",
                "metadata_title": f"Title {i}",
            }
            for i in range(asset_count)
        ]

        # Export
        csv_file = Path(temp_dir) / "roundtrip.csv"
        csv_ops.export_assets_to_csv(assets, str(csv_file), include_metadata=include_metadata)

        # Import
        imported_assets = csv_ops.import_csv_to_assets(str(csv_file))

        # Verify roundtrip
        assert len(imported_assets) == asset_count
        for i, asset in enumerate(imported_assets):
            assert asset["id"] == f"asset{i}"
            assert asset["name"] == f"test-{i}"

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
