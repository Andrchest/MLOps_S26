import unittest
import json
import io
import sys
from fastapi.testclient import TestClient
from services.inference_service import app 
import os


class TestInferenceLogging(unittest.TestCase):
    def setUp(self):
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
        correlation_id = "test-unique-id-123"
        response = self.client.get("/health", headers={"X-Correlation-ID": correlation_id})
        
        self.assertEqual(response.status_code, 200)
        
        logs = self.get_logs()
        print(f"\nAll logs captured: {json.dumps(logs, indent=2)}")
        health_log = next((l for l in logs if l.get("event") == "health_check"), None)
        
        self.assertIsNotNone(health_log, "Event health_check not found in log")
        self.assertEqual(health_log["correlation_id"], correlation_id)
        self.assertEqual(health_log["service"], "inference-service")

    def test_predict_error_logging(self):
        self.client.post("/predict", json={"invalid": "data"})
        logs = self.get_logs()
        for log in logs:
            self.assertIn("correlation_id", log)

    def test_reload_endpoint_logs(self):
        response = self.client.post("/reload")
        logs = self.get_logs()
        reload_logs = [l for l in logs if l.get("event") == "reload_started"]
        self.assertTrue(len(reload_logs) > 0, f"No reload_started logs found. Available logs: {logs}")
        # The correlation_id should be present in the log
        if reload_logs:
            self.assertIn("correlation_id", reload_logs[0])

if __name__ == "__main__":
    unittest.main()