import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
import json
from services.orchestrator import app
import io
import sys
import os


class TestOrchestratorLogging(unittest.TestCase):
    def setUp(self):
        self.patcher = patch("services.orchestrator.app.init_db")
        self.mock_init_db = self.patcher.start()
        self.mock_init_db.return_value = None

        self.db_pool_patcher = patch("services.orchestrator.app.db_pool", new=MagicMock())
        self.mock_db_pool = self.db_pool_patcher.start()
        self.mock_db_pool.close = AsyncMock()

        os.environ["LOG_LEVEL"] = "DEBUG"
        # Capture both stdout and stderr
        self.held_output = io.StringIO()
        self.held_stderr = io.StringIO()
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = self.held_output
        sys.stderr = self.held_stderr

        self.test_ctx = TestClient(app.app)
        self.client = self.test_ctx.__enter__()

    def tearDown(self):
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        self.test_ctx.__exit__(None, None, None)

    def get_logs(self):
        # Check both stdout and stderr for logs
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
        
    def test_startup_logging(self):
        """Test that startup events are logged correctly"""
        # Since startup happens when app is created, we need to check logs after client is created
        log_records = self.get_logs()
        
        startup_logs = [log for log in log_records if log.get("event") == "startup_initiated"]
        self.assertTrue(len(startup_logs) > 0)
        
        startup_finished_logs = [log for log in log_records if log.get("event") == "startup_finished"]
        self.assertTrue(len(startup_finished_logs) > 0)
        

    def test_train_endpoint_logging_success(self):
        """Test logging when training job is created successfully"""
        # Setup mock
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=123)
        self.mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Make request
        response = self.client.post(
            "/train",
            params={"dataset_name": "test_dataset", "dataset_id": 456}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"job_id": 123, "status": "pending"})
        
        # Check log records
        log_records = self.get_logs()
        
        # Check request received log
        request_logs = [log for log in log_records if log.get("event") == "train_request_received"]
        self.assertTrue(len(request_logs) > 0)
        request_log = request_logs[0]
        self.assertEqual(request_log["dataset_name"], "test_dataset")
        self.assertEqual(request_log["dataset_id"], 456)
        self.assertIsNotNone(request_log.get("correlation_id"))
        
        # Check job created log
        job_created_logs = [log for log in log_records if log.get("event") == "job_created_in_db"]
        self.assertTrue(len(job_created_logs) > 0)
        job_log = job_created_logs[0]
        self.assertEqual(job_log["job_id"], 123)
        self.assertEqual(job_log["dataset_name"], "test_dataset")
        
    def test_train_endpoint_logging_error(self):
        """Test logging when training job creation fails"""
        # Setup mock to raise exception
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=Exception("Database connection failed"))
        self.mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Make request
        response = self.client.post(
            "/train",
            params={"dataset_name": "test_dataset", "dataset_id": 456}
        )
        
        self.assertEqual(response.status_code, 500)
        
        # Check error log
        log_records = self.get_logs()
        error_logs = [log for log in log_records if log.get("event") == "job_creation_failed"]
        self.assertTrue(len(error_logs) > 0)
        error_log = error_logs[0]
        self.assertEqual(error_log["level"], "ERROR")
        self.assertIn("Database connection failed", error_log["message"])
        self.assertIsNotNone(error_log.get("exc_info"))
        
    def test_get_status_endpoint_logging_job_exists(self):
        """Test logging when checking status of existing job"""
        # Setup mock
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value="running")
        self.mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Make request
        response = self.client.get("/jobs/123")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"job_id": 123, "status": "running"})
        
        # Check log records
        log_records = self.get_logs()
        
        # Check status check log
        status_logs = [log for log in log_records if log.get("event") == "status_check_requested"]
        self.assertTrue(len(status_logs) > 0)
        status_log = status_logs[0]
        self.assertEqual(status_log["job_id"], 123)

    def test_get_status_endpoint_logging_job_not_found(self):
        """Test logging when job is not found"""
        # Setup mock to return None (job not found)
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=None)
        self.mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Make request
        response = self.client.get("/jobs/999")
        
        self.assertEqual(response.status_code, 404)
        
        # Check warning log
        log_records = self.get_logs()
        warning_logs = [log for log in log_records if log.get("event") == "job_not_found"]
        self.assertTrue(len(warning_logs) > 0)
        warning_log = warning_logs[0]
        self.assertEqual(warning_log["level"], "WARNING")
        self.assertEqual(warning_log["job_id"], 999)
        
    def test_register_dataset_logging(self):
        """Test logging for dataset registration endpoint"""
        response = self.client.post("/datasets")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        
        # Check log records
        log_records = self.get_logs()
        dataset_logs = [log for log in log_records if log.get("event") == "dataset_reg_started"]
        self.assertTrue(len(dataset_logs) > 0)
            
    def test_request_id_uniqueness_in_train_endpoint(self):
        """Test that each train request gets a unique request_id"""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=123)
        self.mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Make two requests
        self.client.post("/train", params={"dataset_name": "dataset1", "dataset_id": 1})
        self.client.post("/train", params={"dataset_name": "dataset2", "dataset_id": 2})
        
        log_records = self.get_logs()
        request_logs = [log for log in log_records if log.get("event") == "train_request_received"]
        
        # Get request_ids from logs
        request_ids = [log.get("correlation_id") for log in request_logs]
        # Filter out None values and check uniqueness
        request_ids = [rid for rid in request_ids if rid is not None]
        
        # Should have at least 2 different request IDs
        self.assertGreaterEqual(len(set(request_ids)), 2)

    def test_correlation_id_propagation_to_all_logs(self):
        """Test that correlation ID is included in all logs for a request"""
        correlation_id = "test-correlation-456"
        
        # Setup mock
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=123)
        self.mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Make request with correlation ID
        self.client.post(
            "/train",
            params={"dataset_name": "test_dataset", "dataset_id": 456},
            headers={"X-Correlation-ID": correlation_id}
        )
        
        # Get all logs generated during this request
        log_records = self.get_logs()
        
        # Check that all logs have the correlation_id
        for log in log_records:
            if log.get("event") in ["train_request_received", "job_created_in_db"]:
                self.assertEqual(log.get("correlation_id"), correlation_id)