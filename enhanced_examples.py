#!/usr/bin/env python3
"""
Enhanced Cascade REST CLI Examples

This script demonstrates all the new advanced features including:
- Detailed logging with structured output
- CSV import/export for batch operations
- Advanced filtering and search capabilities
- Rollback operations for undo functionality
- Performance monitoring and parallel processing
"""

import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any

from cli import CascadeCLI
from logging_config import logger
from rollback import rollback_manager
from csv_operations import csv_ops
from advanced_filtering import advanced_filter
from performance import performance_monitor, parallel_processor


def example_1_logging_and_performance():
    """Example 1: Demonstrating logging and performance monitoring"""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Logging and Performance Monitoring")
    print("=" * 60)

    # Start performance monitoring
    performance_monitor.start_timing()

    # Log operation start
    logger.log_operation_start(
        "example_workflow", workflow_type="batch_processing", asset_count=100
    )

    # Simulate some work
    time.sleep(0.1)

    # Log batch progress
    for i in range(1, 11):
        logger.log_batch_progress(
            "example_workflow", i * 10, 100, batch_id=f"batch_{i}"
        )
        time.sleep(0.05)

    # Log operation end
    logger.log_operation_end("example_workflow", True, processed=100, success_rate=0.95)

    # End performance monitoring
    performance_monitor.end_timing(success=True)

    # Show metrics
    metrics = performance_monitor.get_metrics()
    print(f"\n📊 Performance Metrics:")
    print(f"  Total Operations: {metrics['total_operations']}")
    print(f"  Average Time: {metrics['average_time']:.2f}s")
    print(f"  Operations/sec: {metrics['operations_per_second']:.2f}")


def example_2_csv_operations():
    """Example 2: CSV import/export operations"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: CSV Import/Export Operations")
    print("=" * 60)

    # Create sample asset data
    sample_assets = [
        {
            "id": "page_001",
            "name": "Home Page",
            "path": "/home",
            "type": "page",
            "site": "main_site",
            "metadata_field_1": "homepage",
            "metadata_field_2": "2024",
            "tag_1": "navigation",
            "tag_2": "priority",
        },
        {
            "id": "page_002",
            "name": "About Us",
            "path": "/about",
            "type": "page",
            "site": "main_site",
            "metadata_field_1": "about",
            "metadata_field_2": "2024",
            "tag_1": "company",
            "tag_2": "info",
        },
        {
            "id": "page_003",
            "name": "Contact",
            "path": "/contact",
            "type": "page",
            "site": "main_site",
            "metadata_field_1": "contact",
            "metadata_field_2": "2024",
            "tag_1": "company",
            "tag_2": "contact",
        },
    ]

    # Export assets to CSV
    print("📤 Exporting assets to CSV...")
    csv_path = csv_ops.export_assets_to_csv(sample_assets, "example_assets.csv", True)
    print(f"✅ Exported to: {csv_path}")

    # Import assets from CSV
    print("\n📥 Importing assets from CSV...")
    imported_assets = csv_ops.import_csv_to_assets(csv_path)
    print(f"✅ Imported {len(imported_assets)} assets")

    # Show imported data
    print("\n📋 Imported Assets:")
    for asset in imported_assets:
        print(f"  {asset['id']}: {asset['name']} ({asset['type']})")


def example_3_advanced_filtering():
    """Example 3: Advanced filtering capabilities"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Advanced Filtering")
    print("=" * 60)

    # Sample data with various attributes
    sample_data = [
        {
            "id": "1",
            "name": "Home Page",
            "status": "published",
            "created": "2024-01-15",
            "type": "page",
        },
        {
            "id": "2",
            "name": "About Us",
            "status": "draft",
            "created": "2024-02-10",
            "type": "page",
        },
        {
            "id": "3",
            "name": "Contact Form",
            "status": "published",
            "created": "2024-01-20",
            "type": "form",
        },
        {
            "id": "4",
            "name": "News Article",
            "status": "published",
            "created": "2024-03-05",
            "type": "article",
        },
        {
            "id": "5",
            "name": "Draft Post",
            "status": "draft",
            "created": "2024-03-10",
            "type": "post",
        },
    ]

    print(f"📋 Original data: {len(sample_data)} items")

    # Test various filters
    filters_to_test = [
        ("status", "equals", "published"),
        ("name", "contains", "Page"),
        ("created", "date_after", "2024-02-01"),
        ("type", "in", ["page", "article"]),
        ("name", "regex", r"^[A-Z].*"),  # Starts with capital letter
    ]

    for field, operator, value in filters_to_test:
        filter_expr = advanced_filter.create_filter_expression(field, operator, value)
        filtered = advanced_filter.apply_filters(sample_data, [filter_expr])

        print(f"\n🔍 Filter: {field} {operator} {value}")
        print(f"   Result: {len(filtered)} items")
        for item in filtered:
            print(f"   - {item['id']}: {item['name']}")


def example_4_rollback_operations():
    """Example 4: Rollback operations"""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Rollback Operations")
    print("=" * 60)

    # Simulate some assets that would be modified
    sample_assets = [
        {"id": "page_001", "type": "page", "path": "/home", "name": "Home Page"},
        {"id": "page_002", "type": "page", "path": "/about", "name": "About Us"},
    ]

    operation_params = {
        "operation": "batch_update",
        "field": "metadata_field_1",
        "new_value": "updated_value",
        "user": "example_user",
    }

    # Create rollback record
    print("📝 Creating rollback record...")
    operation_id = rollback_manager.create_rollback_record(
        "batch_update_metadata", sample_assets, operation_params
    )
    print(f"✅ Created rollback record: {operation_id}")

    # List rollback records
    print("\n📋 Available rollback records:")
    records = rollback_manager.list_rollback_records(10)
    for record in records:
        status_emoji = "✅" if record["status"] == "completed" else "⏳"
        print(
            f"  {status_emoji} {record['operation_id'][:8]}... | "
            f"{record['operation_type']} | {record['asset_count']} assets"
        )

    # Get rollback summary
    if records:
        summary = rollback_manager.get_rollback_summary(records[0]["operation_id"])
        if summary:
            print(f"\n📊 Rollback Summary:")
            print(f"  Operation: {summary['operation_type']}")
            print(f"  Assets: {summary['asset_count']}")
            print(f"  Status: {summary['status']}")


def example_5_parallel_processing():
    """Example 5: Parallel processing demonstration"""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Parallel Processing")
    print("=" * 60)

    # Sample data to process
    items_to_process = [f"item_{i:03d}" for i in range(1, 21)]  # 20 items

    def process_item(item: str) -> Dict[str, Any]:
        """Simulate processing an item"""
        # Simulate some work
        time.sleep(0.1)
        return {"item": item, "processed": True, "timestamp": time.time()}

    print(f"🔄 Processing {len(items_to_process)} items...")

    # Process items in parallel
    start_time = time.time()
    results = parallel_processor.process_batch_parallel(
        items_to_process, process_item, batch_size=5
    )
    end_time = time.time()

    print(f"✅ Processed {len(results)} items in {end_time - start_time:.2f}s")
    print(f"📊 Performance: {len(results)/(end_time - start_time):.2f} items/second")

    # Show some results
    print(f"\n📋 Sample Results:")
    for result in results[:5]:
        if result:
            print(f"  {result['item']}: processed at {result['timestamp']:.2f}")


async def example_6_async_processing():
    """Example 6: Asynchronous processing"""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Asynchronous Processing")
    print("=" * 60)

    # Sample async processing function
    async def async_process_item(item: str, session=None) -> Dict[str, Any]:
        """Simulate async processing"""
        # Simulate async work
        await asyncio.sleep(0.1)
        return {"item": item, "async_processed": True, "timestamp": time.time()}

    items = [f"async_item_{i:03d}" for i in range(1, 11)]  # 10 items

    print(f"🔄 Async processing {len(items)} items...")

    start_time = time.time()
    results = await parallel_processor.process_batch_async(items, async_process_item)
    end_time = time.time()

    print(f"✅ Async processed {len(results)} items in {end_time - start_time:.2f}s")
    print(
        f"📊 Async Performance: {len(results)/(end_time - start_time):.2f} items/second"
    )


def example_7_complex_filtering():
    """Example 7: Complex filtering with multiple conditions"""
    print("\n" + "=" * 60)
    print("EXAMPLE 7: Complex Filtering")
    print("=" * 60)

    # More complex sample data
    complex_data = [
        {
            "id": "1",
            "name": "Home Page",
            "status": "published",
            "priority": "high",
            "tags": ["nav", "home"],
        },
        {
            "id": "2",
            "name": "About Us",
            "status": "draft",
            "priority": "medium",
            "tags": ["company"],
        },
        {
            "id": "3",
            "name": "Contact Form",
            "status": "published",
            "priority": "high",
            "tags": ["contact", "form"],
        },
        {
            "id": "4",
            "name": "News Article",
            "status": "published",
            "priority": "low",
            "tags": ["news", "article"],
        },
        {
            "id": "5",
            "name": "Draft Post",
            "status": "draft",
            "priority": "low",
            "tags": ["draft"],
        },
    ]

    # Create complex filter with AND logic
    complex_filter = advanced_filter.create_complex_filter(
        [
            {"field": "status", "operator": "equals", "value": "published"},
            {"field": "priority", "operator": "in", "value": ["high", "medium"]},
        ],
        "AND",
    )

    print(
        "🔍 Complex Filter: (status = 'published') AND (priority IN ['high', 'medium'])"
    )
    filtered_results = advanced_filter.apply_complex_filter(
        complex_data, complex_filter
    )

    print(f"📊 Result: {len(filtered_results)} items match complex filter")
    for item in filtered_results:
        print(f"  - {item['id']}: {item['name']} (priority: {item['priority']})")


def main():
    """Run all examples"""
    print("🚀 Cascade REST CLI - Enhanced Features Examples")
    print("=" * 60)

    try:
        # Run synchronous examples
        example_1_logging_and_performance()
        example_2_csv_operations()
        example_3_advanced_filtering()
        example_4_rollback_operations()
        example_5_parallel_processing()
        example_7_complex_filtering()

        # Run async example
        print("\n" + "=" * 60)
        print("Running async example...")
        asyncio.run(example_6_async_processing())

        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)

        # Cleanup example files
        cleanup_files = ["example_assets.csv", "template_page.csv"]
        for file in cleanup_files:
            if Path(file).exists():
                Path(file).unlink()
                print(f"🧹 Cleaned up: {file}")

    except Exception as e:
        logger.log_error(e, {"example": "main"})
        print(f"❌ Error running examples: {e}")


if __name__ == "__main__":
    main()
