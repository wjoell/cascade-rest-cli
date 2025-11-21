"""
Unit tests for JobScheduler

Tests job scheduling functionality including:
- Creating scheduled jobs
- Listing jobs
- Executing jobs (immediate and scheduled)
- Tracking job history
- Enabling/disabling jobs
"""

import unittest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pytest

from scheduled_jobs import JobScheduler, JobType, JobStatus, ScheduledJob, JobExecution


class TestJobCreation(unittest.TestCase):
    """Test job creation functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.scheduler = JobScheduler(jobs_dir=Path(self.temp_dir))

    def tearDown(self):
        """Clean up temporary files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_job(self):
        """Test creating a scheduled job"""
        job_id = self.scheduler.create_job(
            name="Test Job",
            job_type=JobType.BATCH_UPDATE,
            schedule_expr="daily at 09:00",
            command_args=["batch-update", "--type", "page"],
            environment="test",
            enabled=True,
        )

        # Verify job was created
        self.assertIsNotNone(job_id)
        self.assertIn(job_id, self.scheduler.jobs)

        # Verify job properties
        job = self.scheduler.get_job(job_id)
        self.assertEqual(job.name, "Test Job")
        self.assertEqual(job.job_type, JobType.BATCH_UPDATE)
        self.assertEqual(job.schedule_expr, "daily at 09:00")
        self.assertTrue(job.enabled)
        self.assertEqual(job.environment, "test")

    def test_create_multiple_jobs(self):
        """Test creating multiple jobs"""
        job1_id = self.scheduler.create_job(
            name="Job 1",
            job_type=JobType.BATCH_TAG,
            schedule_expr="daily at 10:00",
            command_args=["batch-tag", "--tag", "faculty"],
            environment="production",
        )

        job2_id = self.scheduler.create_job(
            name="Job 2",
            job_type=JobType.CSV_IMPORT,
            schedule_expr="weekly on monday",
            command_args=["csv-import", "data.csv"],
            environment="production",
        )

        # Verify both jobs exist
        self.assertNotEqual(job1_id, job2_id)
        self.assertEqual(len(self.scheduler.jobs), 2)

    def test_create_job_with_unique_id(self):
        """Test that job IDs are unique"""
        # Create jobs with same name
        job1_id = self.scheduler.create_job(
            name="Duplicate Name",
            job_type=JobType.BATCH_UPDATE,
            schedule_expr="daily",
            command_args=["update"],
            environment="test",
        )

        job2_id = self.scheduler.create_job(
            name="Duplicate Name",
            job_type=JobType.BATCH_UPDATE,
            schedule_expr="daily",
            command_args=["update"],
            environment="test",
        )

        # IDs should be different (e.g., duplicate_name and duplicate_name_1)
        self.assertNotEqual(job1_id, job2_id)

    def test_create_job_with_disabled_state(self):
        """Test creating a disabled job"""
        job_id = self.scheduler.create_job(
            name="Disabled Job",
            job_type=JobType.BATCH_UPDATE,
            schedule_expr="daily",
            command_args=["update"],
            environment="test",
            enabled=False,
        )

        job = self.scheduler.get_job(job_id)
        self.assertFalse(job.enabled)


class TestJobListing(unittest.TestCase):
    """Test job listing functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.scheduler = JobScheduler(jobs_dir=Path(self.temp_dir))

        # Create test jobs
        self.scheduler.create_job(
            name="Test Job",
            job_type=JobType.BATCH_UPDATE,
            schedule_expr="daily",
            command_args=["update"],
            environment="test",
        )

        self.scheduler.create_job(
            name="Production Job",
            job_type=JobType.BATCH_PUBLISH,
            schedule_expr="weekly",
            command_args=["publish"],
            environment="production",
        )

        self.scheduler.create_job(
            name="Another Test Job",
            job_type=JobType.CSV_IMPORT,
            schedule_expr="daily",
            command_args=["import"],
            environment="test",
        )

    def tearDown(self):
        """Clean up temporary files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_list_all_jobs(self):
        """Test listing all jobs"""
        jobs = self.scheduler.list_jobs()

        self.assertEqual(len(jobs), 3)

    def test_list_jobs_by_environment(self):
        """Test filtering jobs by environment"""
        test_jobs = self.scheduler.list_jobs(environment="test")
        prod_jobs = self.scheduler.list_jobs(environment="production")

        self.assertEqual(len(test_jobs), 2)
        self.assertEqual(len(prod_jobs), 1)

    def test_list_jobs_sorted_by_next_run(self):
        """Test that jobs are sorted by next run time"""
        jobs = self.scheduler.list_jobs()

        # Verify jobs are sorted (jobs with next_run come first)
        for i in range(len(jobs) - 1):
            if jobs[i].next_run and jobs[i + 1].next_run:
                self.assertLessEqual(jobs[i].next_run, jobs[i + 1].next_run)

    def test_get_specific_job(self):
        """Test retrieving a specific job by ID"""
        # Create a job and get its ID
        job_id = self.scheduler.create_job(
            name="Specific Job",
            job_type=JobType.BATCH_TAG,
            schedule_expr="daily",
            command_args=["tag"],
            environment="test",
        )

        # Retrieve the job
        job = self.scheduler.get_job(job_id)

        self.assertIsNotNone(job)
        self.assertEqual(job.id, job_id)
        self.assertEqual(job.name, "Specific Job")

    def test_get_nonexistent_job(self):
        """Test retrieving a job that doesn't exist"""
        job = self.scheduler.get_job("nonexistent_job_id")

        self.assertIsNone(job)


class TestJobUpdates(unittest.TestCase):
    """Test job update functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.scheduler = JobScheduler(jobs_dir=Path(self.temp_dir))

        self.job_id = self.scheduler.create_job(
            name="Test Job",
            job_type=JobType.BATCH_UPDATE,
            schedule_expr="daily at 09:00",
            command_args=["update"],
            environment="test",
        )

    def tearDown(self):
        """Clean up temporary files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_update_job_schedule(self):
        """Test updating job schedule"""
        result = self.scheduler.update_job(
            self.job_id, schedule_expr="weekly on monday"
        )

        self.assertTrue(result)

        job = self.scheduler.get_job(self.job_id)
        self.assertEqual(job.schedule_expr, "weekly on monday")

    def test_update_job_command_args(self):
        """Test updating job command arguments"""
        new_args = ["batch-update", "--type", "file", "--filter", "documents"]
        result = self.scheduler.update_job(self.job_id, command_args=new_args)

        self.assertTrue(result)

        job = self.scheduler.get_job(self.job_id)
        self.assertEqual(job.command_args, new_args)

    def test_update_job_environment(self):
        """Test updating job environment"""
        result = self.scheduler.update_job(self.job_id, environment="production")

        self.assertTrue(result)

        job = self.scheduler.get_job(self.job_id)
        self.assertEqual(job.environment, "production")

    def test_update_nonexistent_job(self):
        """Test updating a job that doesn't exist"""
        result = self.scheduler.update_job("nonexistent_id", schedule_expr="daily")

        self.assertFalse(result)

    def test_enable_job(self):
        """Test enabling a job"""
        # Disable first
        self.scheduler.update_job(self.job_id, enabled=False)

        # Then enable
        result = self.scheduler.enable_job(self.job_id)

        self.assertTrue(result)

        job = self.scheduler.get_job(self.job_id)
        self.assertTrue(job.enabled)

    def test_disable_job(self):
        """Test disabling a job"""
        result = self.scheduler.disable_job(self.job_id)

        self.assertTrue(result)

        job = self.scheduler.get_job(self.job_id)
        self.assertFalse(job.enabled)


class TestJobDeletion(unittest.TestCase):
    """Test job deletion functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.scheduler = JobScheduler(jobs_dir=Path(self.temp_dir))

        self.job_id = self.scheduler.create_job(
            name="Test Job",
            job_type=JobType.BATCH_UPDATE,
            schedule_expr="daily",
            command_args=["update"],
            environment="test",
        )

    def tearDown(self):
        """Clean up temporary files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_delete_job(self):
        """Test deleting a job"""
        result = self.scheduler.delete_job(self.job_id)

        self.assertTrue(result)
        self.assertNotIn(self.job_id, self.scheduler.jobs)

    def test_delete_nonexistent_job(self):
        """Test deleting a job that doesn't exist"""
        result = self.scheduler.delete_job("nonexistent_id")

        self.assertFalse(result)


class TestJobExecution(unittest.TestCase):
    """Test job execution functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.scheduler = JobScheduler(jobs_dir=Path(self.temp_dir))

        self.job_id = self.scheduler.create_job(
            name="Test Job",
            job_type=JobType.BATCH_UPDATE,
            schedule_expr="daily",
            command_args=["batch-update", "--type", "page"],
            environment="test",
        )

    def tearDown(self):
        """Clean up temporary files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("scheduled_jobs.subprocess.run")
    def test_run_job_immediately(self, mock_subprocess):
        """Test running a job immediately"""
        # Mock successful command execution
        mock_subprocess.return_value = MagicMock(
            returncode=0, stdout="Success", stderr=""
        )

        execution = self.scheduler.run_job(self.job_id)

        # Verify execution was created
        self.assertIsNotNone(execution)
        self.assertEqual(execution.job_id, self.job_id)
        self.assertEqual(execution.status, JobStatus.COMPLETED)
        self.assertEqual(execution.exit_code, 0)

        # Verify subprocess was called
        mock_subprocess.assert_called_once()

    @patch("scheduled_jobs.subprocess.run")
    def test_run_job_with_dry_run(self, mock_subprocess):
        """Test running a job with dry-run flag"""
        mock_subprocess.return_value = MagicMock(
            returncode=0, stdout="Dry run success", stderr=""
        )

        execution = self.scheduler.run_job(self.job_id, dry_run=True)

        # Verify dry-run flag was added to command
        call_args = mock_subprocess.call_args
        command = call_args[0][0]
        self.assertIn("--dry-run", command)

    @patch("scheduled_jobs.subprocess.run")
    def test_run_job_with_failure(self, mock_subprocess):
        """Test running a job that fails"""
        # Mock failed command execution
        mock_subprocess.return_value = MagicMock(
            returncode=1, stdout="", stderr="Error occurred"
        )

        execution = self.scheduler.run_job(self.job_id)

        # Verify execution failed
        self.assertEqual(execution.status, JobStatus.FAILED)
        self.assertEqual(execution.exit_code, 1)
        self.assertIn("Error occurred", execution.error)

    @patch("scheduled_jobs.subprocess.run")
    def test_run_nonexistent_job(self, mock_subprocess):
        """Test running a job that doesn't exist"""
        execution = self.scheduler.run_job("nonexistent_id")

        # Should return None
        self.assertIsNone(execution)

        # Subprocess should not be called
        mock_subprocess.assert_not_called()

    @patch("scheduled_jobs.subprocess.run")
    def test_job_updates_last_run_time(self, mock_subprocess):
        """Test that job's last_run is updated after execution"""
        mock_subprocess.return_value = MagicMock(
            returncode=0, stdout="Success", stderr=""
        )

        before_run = datetime.now()
        self.scheduler.run_job(self.job_id)
        after_run = datetime.now()

        job = self.scheduler.get_job(self.job_id)

        # Verify last_run was updated
        self.assertIsNotNone(job.last_run)
        self.assertGreaterEqual(job.last_run, before_run)
        self.assertLessEqual(job.last_run, after_run)


class TestJobHistory(unittest.TestCase):
    """Test job execution history functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.scheduler = JobScheduler(jobs_dir=Path(self.temp_dir))

        # Create jobs
        self.job1_id = self.scheduler.create_job(
            name="Job 1",
            job_type=JobType.BATCH_UPDATE,
            schedule_expr="daily",
            command_args=["update"],
            environment="test",
        )

        self.job2_id = self.scheduler.create_job(
            name="Job 2",
            job_type=JobType.CSV_IMPORT,
            schedule_expr="daily",
            command_args=["import"],
            environment="test",
        )

    def tearDown(self):
        """Clean up temporary files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("scheduled_jobs.subprocess.run")
    def test_get_all_job_history(self, mock_subprocess):
        """Test retrieving all job execution history"""
        mock_subprocess.return_value = MagicMock(
            returncode=0, stdout="Success", stderr=""
        )

        # Execute jobs multiple times
        self.scheduler.run_job(self.job1_id)
        self.scheduler.run_job(self.job2_id)
        self.scheduler.run_job(self.job1_id)

        # Get all history
        history = self.scheduler.get_job_history()

        self.assertEqual(len(history), 3)

    @patch("scheduled_jobs.subprocess.run")
    def test_get_job_history_for_specific_job(self, mock_subprocess):
        """Test retrieving history for a specific job"""
        mock_subprocess.return_value = MagicMock(
            returncode=0, stdout="Success", stderr=""
        )

        # Execute jobs
        self.scheduler.run_job(self.job1_id)
        self.scheduler.run_job(self.job2_id)
        self.scheduler.run_job(self.job1_id)

        # Get history for job1 only
        history = self.scheduler.get_job_history(job_id=self.job1_id)

        self.assertEqual(len(history), 2)
        self.assertTrue(all(h.job_id == self.job1_id for h in history))

    @patch("scheduled_jobs.subprocess.run")
    def test_get_job_history_with_limit(self, mock_subprocess):
        """Test retrieving limited job history"""
        mock_subprocess.return_value = MagicMock(
            returncode=0, stdout="Success", stderr=""
        )

        # Execute job multiple times
        for _ in range(10):
            self.scheduler.run_job(self.job1_id)

        # Get limited history
        history = self.scheduler.get_job_history(limit=5)

        self.assertEqual(len(history), 5)

    @patch("scheduled_jobs.subprocess.run")
    def test_job_history_sorted_by_recent_first(self, mock_subprocess):
        """Test that job history is sorted with most recent first"""
        mock_subprocess.return_value = MagicMock(
            returncode=0, stdout="Success", stderr=""
        )

        # Execute jobs with delays
        import time

        self.scheduler.run_job(self.job1_id)
        time.sleep(0.1)
        self.scheduler.run_job(self.job2_id)

        history = self.scheduler.get_job_history()

        # Most recent should be first
        self.assertEqual(history[0].job_id, self.job2_id)
        self.assertEqual(history[1].job_id, self.job1_id)


class TestJobHistoryCleanup(unittest.TestCase):
    """Test job history cleanup functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.scheduler = JobScheduler(jobs_dir=Path(self.temp_dir))

        self.job_id = self.scheduler.create_job(
            name="Test Job",
            job_type=JobType.BATCH_UPDATE,
            schedule_expr="daily",
            command_args=["update"],
            environment="test",
        )

    def tearDown(self):
        """Clean up temporary files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cleanup_old_executions(self):
        """Test cleaning up old job executions"""
        # Create old and new executions
        old_execution = JobExecution(
            job_id=self.job_id,
            execution_id="old_exec",
            started=datetime.now() - timedelta(days=60),
            status=JobStatus.COMPLETED,
        )

        recent_execution = JobExecution(
            job_id=self.job_id,
            execution_id="recent_exec",
            started=datetime.now(),
            status=JobStatus.COMPLETED,
        )

        self.scheduler.executions = [old_execution, recent_execution]

        # Cleanup executions older than 30 days
        deleted_count = self.scheduler.cleanup_old_executions(days_to_keep=30)

        self.assertEqual(deleted_count, 1)
        self.assertEqual(len(self.scheduler.executions), 1)
        self.assertEqual(self.scheduler.executions[0].execution_id, "recent_exec")

    def test_cleanup_with_no_old_executions(self):
        """Test cleanup when there are no old executions"""
        # Create only recent executions
        recent_execution = JobExecution(
            job_id=self.job_id,
            execution_id="recent_exec",
            started=datetime.now(),
            status=JobStatus.COMPLETED,
        )

        self.scheduler.executions = [recent_execution]

        deleted_count = self.scheduler.cleanup_old_executions(days_to_keep=30)

        self.assertEqual(deleted_count, 0)
        self.assertEqual(len(self.scheduler.executions), 1)


@pytest.mark.parametrize(
    "job_type,command_args",
    [
        (JobType.BATCH_UPDATE, ["batch-update", "--type", "page"]),
        (JobType.BATCH_TAG, ["batch-tag", "--tag", "category"]),
        (JobType.BATCH_PUBLISH, ["batch-publish", "--site", "example"]),
        (JobType.CSV_IMPORT, ["csv-import", "data.csv"]),
        (JobType.ADVANCED_SEARCH, ["advanced-search", "--filter", "status:published"]),
        (JobType.CUSTOM_COMMAND, ["custom-command", "--arg", "value"]),
    ],
)
def test_create_jobs_with_different_types(job_type, command_args):
    """Test creating jobs with different job types"""
    temp_dir = tempfile.mkdtemp()
    scheduler = JobScheduler(jobs_dir=Path(temp_dir))

    try:
        job_id = scheduler.create_job(
            name=f"Test {job_type.value}",
            job_type=job_type,
            schedule_expr="daily",
            command_args=command_args,
            environment="test",
        )

        job = scheduler.get_job(job_id)

        assert job.job_type == job_type
        assert job.command_args == command_args

    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.parametrize(
    "environment",
    ["test", "production", "staging", "custom_connection_name"],
)
def test_create_jobs_with_different_environments(environment):
    """Test creating jobs for different environments"""
    temp_dir = tempfile.mkdtemp()
    scheduler = JobScheduler(jobs_dir=Path(temp_dir))

    try:
        job_id = scheduler.create_job(
            name=f"Test Job for {environment}",
            job_type=JobType.BATCH_UPDATE,
            schedule_expr="daily",
            command_args=["update"],
            environment=environment,
        )

        job = scheduler.get_job(job_id)

        assert job.environment == environment

    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
