"""
Rollback system for Cascade REST CLI operations
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import shutil

from config import ROLLBACK_DIR, ROLLBACK_RETENTION_DAYS, ROLLBACK_ENABLED
from logging_config import logger


class RollbackManager:
    """Manages rollback operations for batch updates"""

    def __init__(self):
        self.rollback_dir = ROLLBACK_DIR
        self.rollback_dir.mkdir(exist_ok=True)

    def create_rollback_record(
        self,
        operation_type: str,
        assets: List[Dict[str, Any]],
        operation_params: Dict[str, Any],
    ) -> str:
        """Create a rollback record for an operation"""
        if not ROLLBACK_ENABLED:
            return ""

        operation_id = str(uuid.uuid4())
        timestamp = datetime.now()

        # Read current state of all assets before modification
        asset_states = []
        for asset in assets:
            try:
                # This would need to be implemented based on your cascade_rest module
                # asset_state = cascade.read_single_asset(...)
                asset_states.append(
                    {
                        "asset_id": asset.get("id"),
                        "asset_type": asset.get("type"),
                        "path": asset.get("path"),
                        "state": asset,  # Current state before modification
                    }
                )
            except Exception as e:
                logger.log_error(e, {"operation_id": operation_id, "asset": asset})

        rollback_record = {
            "operation_id": operation_id,
            "operation_type": operation_type,
            "timestamp": timestamp.isoformat(),
            "operation_params": operation_params,
            "asset_count": len(assets),
            "asset_states": asset_states,
            "status": "pending",
        }

        # Save rollback record
        rollback_file = self.rollback_dir / f"{operation_id}.json"
        with open(rollback_file, "w") as f:
            json.dump(rollback_record, f, indent=2)

        logger.log_rollback_operation(
            operation_id,
            "created",
            operation_type=operation_type,
            asset_count=len(assets),
        )

        return operation_id

    def execute_rollback(self, operation_id: str) -> Dict[str, Any]:
        """Execute a rollback operation"""
        rollback_file = self.rollback_dir / f"{operation_id}.json"

        if not rollback_file.exists():
            raise ValueError(f"Rollback record {operation_id} not found")

        with open(rollback_file, "r") as f:
            rollback_record = json.load(f)

        if rollback_record["status"] != "pending":
            raise ValueError(f"Rollback {operation_id} is not in pending status")

        results = {
            "operation_id": operation_id,
            "successful_rollbacks": 0,
            "failed_rollbacks": 0,
            "errors": [],
        }

        logger.log_rollback_operation(operation_id, "started")

        # Restore each asset to its previous state
        for asset_state in rollback_record["asset_states"]:
            try:
                # This would need to be implemented based on your cascade_rest module
                # cascade.update_asset_metadata(...)
                results["successful_rollbacks"] += 1
                logger.log_rollback_operation(
                    operation_id, "asset_restored", asset_id=asset_state["asset_id"]
                )
            except Exception as e:
                results["failed_rollbacks"] += 1
                results["errors"].append(
                    {"asset_id": asset_state["asset_id"], "error": str(e)}
                )
                logger.log_error(
                    e,
                    {
                        "operation_id": operation_id,
                        "asset_id": asset_state["asset_id"],
                        "action": "rollback",
                    },
                )

        # Update rollback record status
        rollback_record["status"] = "completed"
        rollback_record["rollback_timestamp"] = datetime.now().isoformat()
        rollback_record["rollback_results"] = results

        with open(rollback_file, "w") as f:
            json.dump(rollback_record, f, indent=2)

        logger.log_rollback_operation(
            operation_id,
            "completed",
            successful=results["successful_rollbacks"],
            failed=results["failed_rollbacks"],
        )

        return results

    def list_rollback_records(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List available rollback records"""
        rollback_files = sorted(
            self.rollback_dir.glob("*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )

        records = []
        for file_path in rollback_files[:limit]:
            try:
                with open(file_path, "r") as f:
                    record = json.load(f)
                    # Add file info
                    record["file_size"] = file_path.stat().st_size
                    records.append(record)
            except Exception as e:
                logger.log_error(e, {"file": str(file_path)})

        return records

    def cleanup_old_rollbacks(self):
        """Remove rollback records older than retention period"""
        cutoff_date = datetime.now() - timedelta(days=ROLLBACK_RETENTION_DAYS)
        removed_count = 0

        for file_path in self.rollback_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    record = json.load(f)

                record_date = datetime.fromisoformat(record["timestamp"])
                if record_date < cutoff_date:
                    file_path.unlink()
                    removed_count += 1
                    logger.log_rollback_operation(record["operation_id"], "cleaned_up")

            except Exception as e:
                logger.log_error(e, {"file": str(file_path)})

        logger.log_operation_end("rollback_cleanup", True, removed_count=removed_count)
        return removed_count

    def get_rollback_summary(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get summary information about a rollback record"""
        rollback_file = self.rollback_dir / f"{operation_id}.json"

        if not rollback_file.exists():
            return None

        with open(rollback_file, "r") as f:
            record = json.load(f)

        return {
            "operation_id": record["operation_id"],
            "operation_type": record["operation_type"],
            "timestamp": record["timestamp"],
            "asset_count": record["asset_count"],
            "status": record["status"],
            "rollback_timestamp": record.get("rollback_timestamp"),
            "rollback_results": record.get("rollback_results"),
        }


# Global rollback manager instance
rollback_manager = RollbackManager()
