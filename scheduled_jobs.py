#!/usr/bin/env python3
"""
Scheduled Jobs System for Cascade REST CLI

Provides automated job scheduling, execution, and monitoring capabilities
for recurring Cascade CMS operations.
"""

import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import schedule

from logging_config import logger


class JobStatus(Enum):
    """Job execution status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(Enum):
    """Types of scheduled jobs"""

    BATCH_UPDATE = "batch_update"
    BATCH_TAG = "batch_tag"
    BATCH_PUBLISH = "batch_publish"
    CSV_IMPORT = "csv_import"
    ADVANCED_SEARCH = "advanced_search"
    CUSTOM_COMMAND = "custom_command"


@dataclass
class ScheduledJob:
    """Represents a scheduled job"""

    id: str
    name: str
    job_type: JobType
    schedule_expr: str  # Cron-like expression or schedule description
    command_args: List[str]
    environment: str  # test, production, or connection name
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: JobStatus = JobStatus.PENDING
    created: datetime = None
    updated: datetime = None

    def __post_init__(self):
        if self.created is None:
            self.created = datetime.now()
        if self.updated is None:
            self.updated = datetime.now()


@dataclass
class JobExecution:
    """Represents a job execution record"""

    job_id: str
    execution_id: str
    started: datetime
    ended: Optional[datetime] = None
    status: JobStatus = JobStatus.PENDING
    output: str = ""
    error: str = ""
    exit_code: Optional[int] = None


class JobScheduler:
    """Main scheduler for managing and executing scheduled jobs"""

    def __init__(self, jobs_dir: Optional[Path] = None):
        self.jobs_dir = jobs_dir or Path.home() / ".cascade_cli" / "scheduled_jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

        self.jobs_file = self.jobs_dir / "jobs.json"
        self.executions_file = self.jobs_dir / "executions.json"
        self.lock_file = self.jobs_dir / ".lock"

        self.jobs: Dict[str, ScheduledJob] = {}
        self.executions: List[JobExecution] = []
        self.scheduler_thread: Optional[threading.Thread] = None
        self.running = False

        self._load_jobs()
        self._load_executions()

    def create_job(
        self,
        name: str,
        job_type: JobType,
        schedule_expr: str,
        command_args: List[str],
        environment: str = "production",
        enabled: bool = True,
    ) -> str:
        """Create a new scheduled job"""

        job_id = self._generate_job_id(name)

        job = ScheduledJob(
            id=job_id,
            name=name,
            job_type=job_type,
            schedule_expr=schedule_expr,
            command_args=command_args,
            environment=environment,
            enabled=enabled,
        )

        # Calculate next run time
        job.next_run = self._calculate_next_run(schedule_expr)

        self.jobs[job_id] = job
        self._save_jobs()

        logger.log_operation_end(
            "create_scheduled_job",
            True,
            job_id=job_id,
            name=name,
            job_type=job_type.value,
        )

        return job_id

    def list_jobs(self, environment: Optional[str] = None) -> List[ScheduledJob]:
        """List all jobs, optionally filtered by environment"""

        jobs = list(self.jobs.values())

        if environment:
            jobs = [job for job in jobs if job.environment == environment]

        return sorted(jobs, key=lambda x: x.next_run or datetime.max)

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """Get a specific job by ID"""
        return self.jobs.get(job_id)

    def update_job(self, job_id: str, **kwargs) -> bool:
        """Update job properties"""

        if job_id not in self.jobs:
            return False

        job = self.jobs[job_id]

        # Update allowed fields
        allowed_fields = [
            "name",
            "schedule_expr",
            "command_args",
            "environment",
            "enabled",
        ]
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(job, field, value)

        # Recalculate next run if schedule changed
        if "schedule_expr" in kwargs:
            job.next_run = self._calculate_next_run(job.schedule_expr)

        job.updated = datetime.now()
        self._save_jobs()

        logger.log_operation_end("update_scheduled_job", True, job_id=job_id)
        return True

    def delete_job(self, job_id: str) -> bool:
        """Delete a scheduled job"""

        if job_id not in self.jobs:
            return False

        del self.jobs[job_id]
        self._save_jobs()

        logger.log_operation_end("delete_scheduled_job", True, job_id=job_id)
        return True

    def enable_job(self, job_id: str) -> bool:
        """Enable a scheduled job"""
        return self.update_job(job_id, enabled=True)

    def disable_job(self, job_id: str) -> bool:
        """Disable a scheduled job"""
        return self.update_job(job_id, enabled=False)

    def run_job(self, job_id: str, dry_run: bool = False) -> Optional[JobExecution]:
        """Execute a job immediately"""

        job = self.get_job(job_id)
        if not job:
            return None

        execution = JobExecution(
            job_id=job_id,
            execution_id=self._generate_execution_id(job_id),
            started=datetime.now(),
        )

        self.executions.append(execution)
        self._save_executions()

        # Update job status
        job.status = JobStatus.RUNNING
        job.last_run = execution.started
        self._save_jobs()

        try:
            # Build command
            command = ["python", "cli.py"] + job.command_args
            if dry_run and "--dry-run" not in command:
                command.append("--dry-run")

            # Add environment connection if specified
            if job.environment not in ["test", "production"]:
                # Assume it's a connection name
                command = [
                    "python",
                    "cli.py",
                    "connect",
                    job.environment,
                ] + job.command_args[1:]

            logger.log_operation_start(
                "execute_scheduled_job",
                job_id=job_id,
                execution_id=execution.execution_id,
                command=" ".join(command),
            )

            # Execute command
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=3600  # 1 hour timeout
            )

            execution.ended = datetime.now()
            execution.status = (
                JobStatus.COMPLETED if result.returncode == 0 else JobStatus.FAILED
            )
            execution.output = result.stdout
            execution.error = result.stderr
            execution.exit_code = result.returncode

            job.status = execution.status

        except subprocess.TimeoutExpired:
            execution.ended = datetime.now()
            execution.status = JobStatus.FAILED
            execution.error = "Job execution timed out after 1 hour"
            execution.exit_code = -1
            job.status = JobStatus.FAILED

        except Exception as e:
            execution.ended = datetime.now()
            execution.status = JobStatus.FAILED
            execution.error = str(e)
            execution.exit_code = -1
            job.status = JobStatus.FAILED

            logger.log_error(
                e, {"job_id": job_id, "execution_id": execution.execution_id}
            )

        # Update next run time
        if job.enabled and execution.status == JobStatus.COMPLETED:
            job.next_run = self._calculate_next_run(job.schedule_expr)

        self._save_jobs()
        self._save_executions()

        logger.log_operation_end(
            "execute_scheduled_job",
            execution.status == JobStatus.COMPLETED,
            job_id=job_id,
            execution_id=execution.execution_id,
            duration=(execution.ended - execution.started).total_seconds(),
        )

        return execution

    def start_scheduler(self):
        """Start the background scheduler"""

        if self.running:
            return

        self.running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True
        )
        self.scheduler_thread.start()

        logger.log_operation_end("start_scheduler", True)

    def stop_scheduler(self):
        """Stop the background scheduler"""

        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)

        logger.log_operation_end("stop_scheduler", True)

    def get_job_history(
        self, job_id: Optional[str] = None, limit: int = 50
    ) -> List[JobExecution]:
        """Get job execution history"""

        executions = self.executions.copy()

        if job_id:
            executions = [e for e in executions if e.job_id == job_id]

        # Sort by start time, most recent first
        executions.sort(key=lambda x: x.started, reverse=True)

        return executions[:limit]

    def cleanup_old_executions(self, days_to_keep: int = 30):
        """Clean up old execution records"""

        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        original_count = len(self.executions)
        self.executions = [e for e in self.executions if e.started > cutoff_date]

        deleted_count = original_count - len(self.executions)

        if deleted_count > 0:
            self._save_executions()
            logger.log_operation_end(
                "cleanup_old_executions", True, deleted_count=deleted_count
            )

        return deleted_count

    def _scheduler_loop(self):
        """Main scheduler loop"""

        while self.running:
            try:
                now = datetime.now()

                # Check for jobs that should run
                for job in self.jobs.values():
                    if (
                        job.enabled
                        and job.next_run
                        and job.next_run <= now
                        and job.status != JobStatus.RUNNING
                    ):

                        logger.log_operation_start(
                            "trigger_scheduled_job", job_id=job.id, name=job.name
                        )

                        # Run job in a separate thread to avoid blocking
                        thread = threading.Thread(
                            target=self.run_job, args=(job.id,), daemon=True
                        )
                        thread.start()

                # Sleep for a minute before checking again
                time.sleep(60)

            except Exception as e:
                logger.log_error(e, {"operation": "scheduler_loop"})
                time.sleep(60)

    def _generate_job_id(self, name: str) -> str:
        """Generate a unique job ID"""

        base_id = name.lower().replace(" ", "_").replace("-", "_")
        job_id = base_id

        counter = 1
        while job_id in self.jobs:
            job_id = f"{base_id}_{counter}"
            counter += 1

        return job_id

    def _generate_execution_id(self, job_id: str) -> str:
        """Generate a unique execution ID"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{job_id}_{timestamp}"

    def _calculate_next_run(self, schedule_expr: str) -> Optional[datetime]:
        """Calculate next run time from schedule expression"""

        try:
            # Parse different schedule formats
            if schedule_expr.startswith("every "):
                # Handle "every X minutes/hours/days" format
                parts = schedule_expr.split()
                if len(parts) >= 3:
                    interval = int(parts[1])
                    unit = parts[2].rstrip("s")  # Remove plural 's'

                    now = datetime.now()

                    if unit == "minute":
                        return now + timedelta(minutes=interval)
                    elif unit == "hour":
                        return now + timedelta(hours=interval)
                    elif unit == "day":
                        return now + timedelta(days=interval)
                    elif unit == "week":
                        return now + timedelta(weeks=interval)

            elif schedule_expr.startswith("daily at "):
                # Handle "daily at HH:MM" format
                time_str = schedule_expr.replace("daily at ", "")
                try:
                    hour, minute = map(int, time_str.split(":"))
                    now = datetime.now()
                    next_run = now.replace(
                        hour=hour, minute=minute, second=0, microsecond=0
                    )

                    if next_run <= now:
                        next_run += timedelta(days=1)

                    return next_run
                except ValueError:
                    pass

            elif schedule_expr.startswith("weekly on "):
                # Handle "weekly on Monday at HH:MM" format
                # This is a simplified implementation
                return datetime.now() + timedelta(days=7)

            # Default: assume it's a simple interval
            if schedule_expr.isdigit():
                return datetime.now() + timedelta(minutes=int(schedule_expr))

        except Exception as e:
            logger.log_error(e, {"schedule_expr": schedule_expr})

        return None

    def _load_jobs(self):
        """Load jobs from file"""

        if not self.jobs_file.exists():
            return

        try:
            with open(self.jobs_file, "r") as f:
                data = json.load(f)

            self.jobs = {}
            for job_data in data.get("jobs", []):
                # Convert string enums back to enum objects
                job_data["job_type"] = JobType(job_data["job_type"])
                job_data["status"] = JobStatus(job_data["status"])

                # Convert datetime strings back to datetime objects
                for field in ["last_run", "next_run", "created", "updated"]:
                    if job_data.get(field):
                        job_data[field] = datetime.fromisoformat(job_data[field])

                job = ScheduledJob(**job_data)
                self.jobs[job.id] = job

        except Exception as e:
            logger.log_error(e, {"operation": "load_jobs"})

    def _save_jobs(self):
        """Save jobs to file"""

        try:
            data = {"jobs": []}

            for job in self.jobs.values():
                job_dict = asdict(job)
                # Convert enums to strings
                job_dict["job_type"] = job.job_type.value
                job_dict["status"] = job.status.value

                # Convert datetime objects to ISO strings
                for field in ["last_run", "next_run", "created", "updated"]:
                    if job_dict.get(field):
                        job_dict[field] = job_dict[field].isoformat()

                data["jobs"].append(job_dict)

            with open(self.jobs_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.log_error(e, {"operation": "save_jobs"})

    def _load_executions(self):
        """Load execution history from file"""

        if not self.executions_file.exists():
            return

        try:
            with open(self.executions_file, "r") as f:
                data = json.load(f)

            self.executions = []
            for exec_data in data.get("executions", []):
                # Convert string enum back to enum object
                exec_data["status"] = JobStatus(exec_data["status"])

                # Convert datetime strings back to datetime objects
                for field in ["started", "ended"]:
                    if exec_data.get(field):
                        exec_data[field] = datetime.fromisoformat(exec_data[field])

                execution = JobExecution(**exec_data)
                self.executions.append(execution)

        except Exception as e:
            logger.log_error(e, {"operation": "load_executions"})

    def _save_executions(self):
        """Save execution history to file"""

        try:
            data = {"executions": []}

            for execution in self.executions:
                exec_dict = asdict(execution)
                # Convert enum to string
                exec_dict["status"] = execution.status.value

                # Convert datetime objects to ISO strings
                for field in ["started", "ended"]:
                    if exec_dict.get(field):
                        exec_dict[field] = exec_dict[field].isoformat()

                data["executions"].append(exec_dict)

            with open(self.executions_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.log_error(e, {"operation": "save_executions"})


# Global scheduler instance
job_scheduler = JobScheduler()
