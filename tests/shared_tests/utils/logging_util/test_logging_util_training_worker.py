import unittest
from unittest.mock import patch, MagicMock, call, AsyncMock
import json
import io
import sys
import os
import asyncio
from fastapi.testclient import TestClient

mock_minio_client = MagicMock()
mock_minio_client.download_dataset = MagicMock()
mock_minio_client.save_model_to_minio = MagicMock()

# Mock the Minio class to prevent any connection attempts
mock_minio_class = MagicMock()
mock_minio_client.Minio = mock_minio_class

# Insert the mock into sys.modules BEFORE importing the app
sys.modules['services.training_worker.minio_client'] = mock_minio_client
sys.modules['minio_client'] = mock_minio_client

from services.training_worker import app
from services.training_worker.worker import worker_loop, process_job


class TestTrainingWorkerLogging(unittest.TestCase):
    def setUp(self):
        self.db_pool_patcher = patch("services.training_worker.app.db.db_pool", new=MagicMock())
        self.mock_db_pool = self.db_pool_patcher.start()
        self.mock_db_pool.close = AsyncMock()
        
        # Mock asyncpg.create_pool to prevent actual connection attempts
        self.create_pool_patcher = patch("asyncpg.create_pool", new_callable=AsyncMock)
        self.mock_create_pool = self.create_pool_patcher.start()

        # Set environment variables
        os.environ["LOG_LEVEL"] = "DEBUG"
        os.environ["SERVICE_NAME"] = "training-worker"
        
        # Capture both stdout and stderr
        self.held_output = io.StringIO()
        self.held_stderr = io.StringIO()
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = self.held_output
        sys.stderr = self.held_stderr
        
        # Setup test client for health check
        self.test_ctx = TestClient(app.app)
        self.client = self.test_ctx.__enter__()
        
        # Create event loop for async tests
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
    def tearDown(self):
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        self.test_ctx.__exit__(None, None, None)
        self.loop.close()
        
    def get_logs(self):
        """Parse JSON logs from stdout/stderr"""
        output = self.held_output.getvalue().strip()
        error_output = self.held_stderr.getvalue().strip()
        
        all_output = output + '\n' + error_output if output and error_output else output or error_output
        
        if not all_output:
            return []
        
        logs = []
        for line in all_output.split('\n'):
            line = line.strip()
            if line:
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    # Skip non-JSON lines
                    continue
        return logs
    
    def clear_logs(self):
        """Clear captured logs between tests"""
        self.held_output = io.StringIO()
        self.held_stderr = io.StringIO()
        sys.stdout = self.held_output
        sys.stderr = self.held_stderr
    
    def test_health_check_logging_with_correlation_id(self):
        """Test that health check logs include correlation ID"""
        correlation_id = "test-unique-id-123"
        
        response = self.client.get(
            "/health",
            headers={"X-Correlation-ID": correlation_id}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        
        # Check log records
        log_records = self.get_logs()
        health_logs = [log for log in log_records if log.get("event") == "health_check"]
        
        self.assertTrue(len(health_logs) > 0)
        health_log = health_logs[0]
        self.assertEqual(health_log["correlation_id"], correlation_id)
        self.assertEqual(health_log["service"], "training-worker")
        
    def test_startup_logging(self):
        """Test that startup events are logged correctly"""
        # Startup happens when app is created, so logs should be captured
        log_records = self.get_logs()
        
        # Check DB pool creation logs
        db_pool_creating = [log for log in log_records if log.get("event") == "db_pool_creating"]
        db_pool_ready = [log for log in log_records if log.get("event") == "db_pool_ready"]
        
        self.assertTrue(len(db_pool_creating) > 0, "DB pool creating log not found")
        self.assertTrue(len(db_pool_ready) > 0, "DB pool ready log not found")
        
        # Check worker task start log
        worker_start = [log for log in log_records if log.get("event") == "worker_task_start"]
        self.assertTrue(len(worker_start) > 0, "Worker task start log not found")
        
    @patch('worker.get_job')
    @patch('worker.process_job')
    async def test_worker_loop_polls_and_processes_job(self, mock_process_job, mock_get_job):
        """Test worker loop logging when polling and processing jobs"""
        # Setup mock
        mock_job = {
            "job_id": 123,
            "dataset_name": "test_dataset",
            "dataset_id": 456
        }
        mock_get_job.return_value = mock_job
        mock_process_job.return_value = None
        
        # Run worker loop for a short time
        task = asyncio.create_task(worker_loop())
        await asyncio.sleep(0.1)
        task.cancel()
        
        # Check logs
        log_records = self.get_logs()
        
        # Check worker loop started log
        worker_started = [log for log in log_records if log.get("event") == "worker_loop_started"]
        self.assertTrue(len(worker_started) > 0)
        
        # Check job polled log
        job_polled = [log for log in log_records if log.get("event") == "job_polled"]
        self.assertTrue(len(job_polled) > 0)
        if job_polled:
            self.assertEqual(job_polled[0]["job_id"], 123)
            self.assertEqual(job_polled[0]["dataset_id"], 456)
        
    @patch('worker.download_dataset')
    @patch('worker.subprocess.run')
    @patch('worker.MlflowClient')
    @patch('worker.mlflow.get_experiment_by_name')
    @patch('worker.mlflow.artifacts.download_artifacts')
    @patch('worker.save_model_to_minio')
    @patch('worker.save_trained_model')
    @patch('worker.update_status')
    @patch('shutil.move')
    async def test_process_job_success_logging(
        self, mock_move, mock_update_status, mock_save_trained_model, 
        mock_save_to_minio, mock_download_artifacts, mock_get_experiment,
        mock_mlflow_client, mock_subprocess_run, mock_download_dataset
    ):
        """Test comprehensive logging during successful job processing"""
        
        # Setup mocks
        mock_update_status.return_value = None
        mock_save_trained_model.return_value = None
        mock_save_to_minio.return_value = "minio://models/test_model_123"
        mock_download_artifacts.return_value = "/tmp/model_artifacts"
        
        # Mock subprocess result
        mock_process_result = MagicMock()
        mock_process_result.returncode = 0
        mock_process_result.stdout = "Training completed successfully\nAccuracy: 0.95"
        mock_process_result.stderr = ""
        mock_subprocess_run.return_value = mock_process_result
        
        # Mock MLflow experiment
        mock_exp = MagicMock()
        mock_exp.experiment_id = "exp_123"
        mock_get_experiment.return_value = mock_exp
        
        # Mock MLflow runs
        mock_run = MagicMock()
        mock_run.info.run_id = "run_123"
        mock_run.data.params = {"model_type": "random_forest", "n_estimators": "100"}
        mock_run.data.metrics = {"accuracy": 0.95, "f1_score": 0.93}
        
        mock_client_instance = MagicMock()
        mock_client_instance.search_runs.return_value = [mock_run]
        mock_mlflow_client.return_value = mock_client_instance
        
        # Test job data
        job = {
            "job_id": 123,
            "dataset_name": "test_dataset.csv",
            "dataset_id": 456
        }
        
        # Process the job
        await process_job(job)
        
        # Get logs
        log_records = self.get_logs()
        
        # Check dataset download log
        download_logs = [log for log in log_records if log.get("event") == "dataset_download_start"]
        self.assertTrue(len(download_logs) > 0)
        download_log = download_logs[0]
        self.assertEqual(download_log["job_id"], 123)
        self.assertEqual(download_log["dataset_name"], "test_dataset.csv")
        self.assertEqual(download_log["pipeline"], "first_ml_baseline")
        
        # Check dataset ready log
        ready_logs = [log for log in log_records if log.get("event") == "dataset_ready"]
        self.assertTrue(len(ready_logs) > 0)
        ready_log = ready_logs[0]
        self.assertEqual(ready_log["job_id"], 123)
        self.assertIn("csv_path", ready_log)
        
        # Check training subprocess start log
        training_start_logs = [log for log in log_records if log.get("event") == "training_subprocess_start"]
        self.assertTrue(len(training_start_logs) > 0)
        
        # Check MinIO upload start log
        upload_logs = [log for log in log_records if log.get("event") == "minio_upload_start"]
        self.assertTrue(len(upload_logs) > 0)
        upload_log = upload_logs[0]
        self.assertEqual(upload_log["job_id"], 123)
        self.assertEqual(upload_log["model_version"], f"123_456_run_123")
        
        # Check job success log
        success_logs = [log for log in log_records if log.get("event") == "job_success"]
        self.assertTrue(len(success_logs) > 0)
        success_log = success_logs[0]
        self.assertEqual(success_log["job_id"], 123)
        self.assertEqual(success_log["model_version"], f"123_456_run_123")
        self.assertEqual(success_log["metrics"], {"accuracy": 0.95, "f1_score": 0.93})
        
        # Verify update_status was called with correct statuses
        mock_update_status.assert_has_calls([
            call(123, "persisting"),
            call(123, "succeeded")
        ])
        
    @patch('worker.download_dataset')
    @patch('worker.subprocess.run')
    @patch('worker.update_status')
    async def test_process_job_failure_logging(self, mock_update_status, mock_subprocess_run, mock_download_dataset):
        """Test logging when job processing fails"""
        
        # Setup mock to simulate pipeline failure
        mock_process_result = MagicMock()
        mock_process_result.returncode = 1
        mock_process_result.stderr = "Error: Model training failed due to insufficient memory"
        mock_process_result.stdout = ""
        mock_subprocess_run.return_value = mock_process_result
        mock_update_status.return_value = None
        
        # Test job data
        job = {
            "job_id": 999,
            "dataset_name": "failing_dataset.csv",
            "dataset_id": 888
        }
        
        # Process the job (should fail)
        await process_job(job)
        
        # Get logs
        log_records = self.get_logs()
        
        # Check training subprocess failed log
        failure_logs = [log for log in log_records if log.get("event") == "training_subprocess_failed"]
        self.assertTrue(len(failure_logs) > 0)
        failure_log = failure_logs[0]
        self.assertEqual(failure_log["job_id"], 999)
        self.assertEqual(failure_log["event"], "training_subprocess_failed")
        self.assertIn("Error: Model training failed", failure_log["stderr"])
        
        # Check job failed log
        job_failed_logs = [log for log in log_records if log.get("event") == "job_failed"]
        self.assertTrue(len(job_failed_logs) > 0)
        job_failed_log = job_failed_logs[0]
        self.assertEqual(job_failed_log["job_id"], 999)
        self.assertEqual(job_failed_log["level"], "ERROR")
        
        # Verify update_status was called with failed status
        mock_update_status.assert_called_with(999, "failed")
        
    @patch('worker.get_job')
    async def test_worker_loop_error_logging(self, mock_get_job):
        """Test worker loop error logging when critical error occurs"""
        
        # Setup mock to raise exception
        mock_get_job.side_effect = Exception("Database connection lost")
        
        # Run worker loop briefly
        task = asyncio.create_task(worker_loop())
        await asyncio.sleep(0.1)
        task.cancel()
        
        # Get logs
        log_records = self.get_logs()
        
        # Check worker loop error log
        error_logs = [log for log in log_records if log.get("event") == "worker_loop_error"]
        self.assertTrue(len(error_logs) > 0)
        error_log = error_logs[0]
        self.assertEqual(error_log["level"], "ERROR")
        self.assertIn("Database connection lost", error_log["message"])
        self.assertIsNotNone(error_log.get("exc_info"))
        
    @patch('worker.download_dataset')
    @patch('worker.subprocess.run')
    @patch('worker.update_status')
    async def test_process_job_warning_logging(self, mock_update_status, mock_subprocess_run, mock_download_dataset):
        """Test logging of warnings when pipeline completes with stderr output"""
        
        # Setup mock with warnings in stderr
        mock_process_result = MagicMock()
        mock_process_result.returncode = 0
        mock_process_result.stdout = "Training completed"
        mock_process_result.stderr = "Warning: Deprecated function used\nWarning: Low memory"
        mock_subprocess_run.return_value = mock_process_result
        mock_update_status.return_value = None
        
        # Mock MLflow components (simplified for this test)
        with patch('worker.MlflowClient') as mock_mlflow_client, \
             patch('worker.mlflow.get_experiment_by_name') as mock_get_exp, \
             patch('worker.mlflow.artifacts.download_artifacts') as mock_download, \
             patch('worker.save_model_to_minio') as mock_save_minio, \
             patch('worker.save_trained_model') as mock_save_model, \
             patch('shutil.move') as mock_move:
            
            # Setup mock returns
            mock_exp = MagicMock()
            mock_exp.experiment_id = "exp_123"
            mock_get_exp.return_value = mock_exp
            
            mock_run = MagicMock()
            mock_run.info.run_id = "run_123"
            mock_run.data.params = {"model_type": "test"}
            mock_run.data.metrics = {"accuracy": 0.95}
            
            mock_client = MagicMock()
            mock_client.search_runs.return_value = [mock_run]
            mock_mlflow_client.return_value = mock_client
            
            mock_download.return_value = "/tmp/model"
            mock_save_minio.return_value = "minio://path"
            mock_save_model.return_value = None
            mock_update_status.return_value = None
            
            job = {
                "job_id": 456,
                "dataset_name": "warnings_dataset.csv",
                "dataset_id": 789
            }
            
            await process_job(job)
            
            # Check warning log
            log_records = self.get_logs()
            warning_logs = [log for log in log_records if log.get("event") == "pipeline_warnings"]
            self.assertTrue(len(warning_logs) > 0)
            warning_log = warning_logs[0]
            self.assertEqual(warning_log["job_id"], 456)
            self.assertIn("Warning:", warning_log["stderr"])
            
    def test_correlation_id_propagation_to_worker_logs(self):
        """Test that correlation ID is included in worker logs when set"""
        correlation_id = "test-correlation-worker-789"
        
        # Make health request with correlation ID
        response = self.client.get(
            "/health",
            headers={"X-Correlation-ID": correlation_id}
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Get logs
        log_records = self.get_logs()
        
        # Check that health check log has the correlation_id
        health_logs = [log for log in log_records if log.get("event") == "health_check"]
        self.assertTrue(len(health_logs) > 0)
        self.assertEqual(health_logs[0].get("correlation_id"), correlation_id)
        
        # Check that startup logs (which occurred before the request) don't have correlation_id
        startup_logs = [log for log in log_records if log.get("event") == "db_pool_ready"]
        if startup_logs:
            # These logs shouldn't have correlation_id as they were before the request
            self.assertIsNone(startup_logs[0].get("correlation_id"))
            
    @patch('worker.get_job')
    async def test_worker_loop_poll_interval_logging(self, mock_get_job):
        """Test that worker loop logs continue to work across multiple poll cycles"""
        # Setup mock to return None (no jobs) then a job
        mock_get_job.side_effect = [None, {"job_id": 1, "dataset_name": "test", "dataset_id": 2}]
        
        # Run worker loop for a couple of cycles
        task = asyncio.create_task(worker_loop())
        await asyncio.sleep(0.3)  # Allow for multiple polls
        task.cancel()
        
        # Get logs
        log_records = self.get_logs()
        
        # Verify worker loop continues running
        worker_started = [log for log in log_records if log.get("event") == "worker_loop_started"]
        self.assertTrue(len(worker_started) > 0)


if __name__ == "__main__":
    unittest.main()