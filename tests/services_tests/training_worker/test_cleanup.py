import unittest
import os
import shutil
from unittest.mock import MagicMock, patch
import sys

mock_minio_client = MagicMock()
mock_minio_client.download_dataset = MagicMock()
mock_minio_client.save_model_to_minio = MagicMock()

# Mock the Minio class to prevent any connection attempts
mock_minio_class = MagicMock()
mock_minio_client.Minio = mock_minio_class

# Insert the mock into sys.modules BEFORE importing the app
sys.modules["services.training_worker.minio_client"] = mock_minio_client
sys.modules["minio_client"] = mock_minio_client

from services.training_worker.worker import process_job


class TestWorkerCleanupIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.dataset_name = "integration_test_dataset"
        self.temp_dir = f"/tmp/{self.dataset_name}"
        self.csv_path = f"/tmp/{self.dataset_name}.csv"

        # Полная очистка перед тестом
        for p in [self.temp_dir, self.csv_path]:
            if os.path.exists(p):
                shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)

        # 1. Создаем ТОЛЬКО исходную директорию
        os.makedirs(self.temp_dir, exist_ok=True)

        # 2. Создаем файл ВНУТРИ директории
        with open(os.path.join(self.temp_dir, "raw_data.tmp"), "w") as f:
            f.write("id,label\n1,0")

    def tearDown(self):
        for p in [self.temp_dir, self.csv_path]:
            if os.path.exists(p):
                if os.path.isdir(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)

    @patch("services.training_worker.worker.download_dataset")
    @patch("services.training_worker.worker.subprocess.run")
    @patch("services.training_worker.worker.MlflowClient")
    @patch("services.training_worker.worker.mlflow.get_experiment_by_name")
    @patch("services.training_worker.worker.mlflow.artifacts.download_artifacts")
    @patch("services.training_worker.worker.save_model_to_minio")
    @patch("services.training_worker.worker.save_trained_model")
    @patch("services.training_worker.worker.update_status")
    async def test_process_job_success_cleanup(
        self,
        mock_update_status,
        mock_save_trained_model,
        mock_save_to_minio,
        mock_download_artifacts,
        mock_get_experiment,
        mock_mlflow_client,
        mock_subprocess_run,
        mock_download_dataset,
    ):
        """Test comprehensive clean up during successful job processing"""
        self.assertTrue(
            os.path.exists(self.temp_dir), "Directory must exist before test!"
        )
        # self.assertTrue(os.path.exists(self.csv_path), "CSV must exist before test!")

        # Setup mocks
        mock_update_status.return_value = None
        mock_save_trained_model.return_value = None
        mock_save_to_minio.return_value = "minio://models/test_model_123"
        mock_download_artifacts.return_value = self.csv_path

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
        job = {"job_id": 123, "dataset_name": self.dataset_name, "dataset_id": 456}

        # Process the job
        await process_job(job)

        self.assertFalse(os.path.exists(self.temp_dir), "Directory was not removed!")
        self.assertFalse(os.path.exists(self.csv_path), "CSV was not removed!")

    @patch("services.training_worker.worker.download_dataset")
    @patch("services.training_worker.worker.subprocess.run")
    @patch("services.training_worker.worker.update_status")
    async def test_cleanup_when_process_job_failure(
        self, mock_update_status, mock_subprocess_run, mock_download_dataset
    ):
        """Test clean up when job processing fails"""
        self.assertTrue(
            os.path.exists(self.temp_dir), "Directory must exist before test!"
        )
        # self.assertTrue(os.path.exists(self.csv_path), "CSV must exist before test!")

        # Setup mock to simulate pipeline failure
        mock_process_result = MagicMock()
        mock_process_result.returncode = 1
        mock_process_result.stderr = (
            "Error: Model training failed due to insufficient memory"
        )
        mock_process_result.stdout = ""
        mock_subprocess_run.return_value = mock_process_result
        mock_update_status.return_value = None

        # Test job data
        job = {"job_id": 999, "dataset_name": self.dataset_name, "dataset_id": 888}

        # Process the job (should fail)
        await process_job(job)

        self.assertFalse(os.path.exists(self.temp_dir), "Directory was not removed!")
        self.assertFalse(os.path.exists(self.csv_path), "CSV was not removed!")


if __name__ == "__main__":
    unittest.main()
