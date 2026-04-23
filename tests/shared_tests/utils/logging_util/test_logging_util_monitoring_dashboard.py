import unittest
from unittest.mock import patch, MagicMock
import json
import io
import sys
import os
from asgi_correlation_id import correlation_id


class TestDashboardLogging(unittest.TestCase):
    def setUp(self):
        for mod in ["services.monitoring_dashboard.app", "services.monitoring_dashboard.db", "services.monitoring_dashboard.repository"]:
            if mod in sys.modules:
                del sys.modules[mod]

        # Set environment variables
        os.environ["LOG_LEVEL"] = "DEBUG"
        os.environ["SERVICE_NAME"] = "monitoring-dashboard"
        
        self.held_output = io.StringIO()
        self.held_stderr = io.StringIO()
        sys.stdout = self.held_output
        sys.stderr = self.held_stderr
        
        # Mock streamlit
        self.st_patcher = patch("services.monitoring_dashboard.app.st")
        self.mock_st = self.st_patcher.start()
        self.mock_st.session_state = MagicMock()
        
        # Mock db health
        self.db_patcher = patch("services.monitoring_dashboard.app.check_db_health")
        self.mock_check_db = self.db_patcher.start()
        self.mock_check_db.return_value = (True, None)

        # Mock db get_total_jobs and get_total_models
        self.mock_jobs = patch("services.monitoring_dashboard.app.get_total_jobs").start()
        self.mock_models = patch("services.monitoring_dashboard.app.get_total_models").start()

        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.iloc = [{"total_jobs": 10, "total_models": 5}]

        self.mock_jobs.return_value = {"ok": True, "data": mock_df}
        self.mock_models.return_value = {"ok": True, "data": mock_df}

        import services.monitoring_dashboard.app as dashboard
        self.dashboard = dashboard
        
    def tearDown(self):
        # Restore stdout/stderr
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        self.st_patcher.stop()
        self.db_patcher.stop()
        patch.stopall()
        
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
            if line and line.startswith('{'):
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return logs
    
    def clear_logs(self):
        """Clear captured logs"""
        self.held_output.truncate(0)
        self.held_output.seek(0)
        self.held_stderr.truncate(0)
        self.held_stderr.seek(0)
    
    def test_dashboard_startup_logging(self):
        """Test that dashboard startup is logged correctly"""
        # The dashboard was already imported in setUp, which should have generated startup logs
        logs = self.get_logs()
        
        # Debug: print what logs we have
        sys.stdout = sys.__stdout__
        print(f"\nFound {len(logs)} logs")
        for log in logs:
            print(f"Log: {log}")
        
        # Check dashboard started log
        startup_logs = [log for log in logs if log.get("event") == "dashboard_started"]
        self.assertTrue(len(startup_logs) > 0, "Dashboard started log not found")
        
        # Check service name
        if startup_logs:
            self.assertEqual(startup_logs[0].get("service"), "monitoring-dashboard")

    def test_dashboard_inject_correlation_id(self):
        """Test correlation id created and added in logs"""
        # Clear previous logs
        self.clear_logs()
        
        # Clear session
        self.mock_st.session_state = MagicMock()
        # Reset context
        correlation_id.set(None)
        
        self.dashboard.inject_correlation_id()
        # Generate a test log entry
        self.dashboard.logger.info("Test event", extra={"event": "test_event"})
        
        logs = self.get_logs()
        test_logs = [l for l in logs if l.get("event") == "test_event"]
        
        self.assertTrue(len(test_logs) > 0, "No logs were found")
        
        # Get correlation ID from session (should be generated)
        # Note: You may need to call a function that generates the correlation ID
        # For now, let's check if correlation_id exists in the log
        log_cid = test_logs[0].get("correlation_id")
        self.assertIsNotNone(log_cid, "Correlation id not found in log")

    def test_dashboard_uses_existing_correlation_id(self):
        """Test that dashboard uses existing correlation ID from session"""
        self.clear_logs()
        existing_cid = "existing-uuid-123"
        correlation_id.set(None)
        
        session_dict = {"correlation_id": existing_cid}
        self.mock_st.session_state.__contains__.side_effect = lambda k: k in session_dict
        self.mock_st.session_state.get.side_effect = lambda k, d=None: session_dict.get(k, d)

        type(self.mock_st.session_state).correlation_id = existing_cid

        self.dashboard.inject_correlation_id()

        self.dashboard.logger.info("dashboard_started", extra={"event": "dashboard_started"})
        
        logs = self.get_logs()
        logs_with_event = [log for log in logs if log.get("event") == "dashboard_started"]
        
        self.assertTrue(len(logs_with_event) > 0)
        log = logs_with_event[-1]
        
        self.assertEqual(log.get("correlation_id"), existing_cid)
