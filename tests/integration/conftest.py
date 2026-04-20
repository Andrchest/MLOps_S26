# Test configuration for integration tests
import pytest
import asyncio
import subprocess
import time
import httpx
import asyncpg
from minio import Minio
import mlflow
from mlflow.tracking import MlflowClient


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def docker_compose():
    """
    Fixture to manage docker-compose lifecycle.
    Starts docker-compose in the background and waits for services to be healthy.
    """
    project_dir = "/home/andreipc/MLOps/MLOps_S26"
    print(f"\nStarting docker-compose in {project_dir}...")

    # Start docker-compose
    try:
        subprocess.run(
            ["docker-compose", "up", "-d"],
            cwd=project_dir,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error starting docker-compose: {e.stderr}")
        raise

    # Wait for services to be healthy using curl as required
    # We'll check a few key services using curl
    health_checks = [
        ("minio", 9000),
        ("mlflow", 5000),
        ("orchestrator", 8000),
        ("inference-service", 8001),
        ("monitoring-service", 8002),
    ]

    print("Waiting for services to be healthy...")
    timeout = 60
    start_time = time.time()

    for service_name, port in health_checks:
        success = False
        while time.time() - start_time < timeout:
            try:
                # Try to curl the service and check for 200 or 404 (404 is often okay for some health checks)
                result = subprocess.run(
                    [
                        "curl",
                        "-s",
                        "-o",
                        "/dev/null",
                        "-w",
                        "%{http_code}",
                        f"http://localhost:{port}",
                    ],
                    capture_output=True,
                    text=True,
                )
                if result.stdout in ["200", "404"]:
                    success = True
                    break
            except Exception:
                pass
            time.sleep(2)

        if not success:
            raise TimeoutError(
                f"Service {service_name} on port {port} did not become healthy."
            )

    yield

    print("\nStopping docker-compose...")
    subprocess.run(
        ["docker-compose", "down", "-v"],
        cwd=project_dir,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="session")
def test_config(docker_compose):
    """Test configuration values."""
    return {
        "base_url": "http://localhost",
        "orchestrator_url": "http://localhost:8000",
        "inference_url": "http://localhost:8001",
        "monitoring_url": "http://localhost:8002",
        "mlflow_url": "http://localhost:5000",
        "minio_url": "http://localhost:9000",
        "postgres_host": "localhost",
        "postgres_port": 5432,
        "postgres_user": "mlops",
        "postgres_password": "mlops",
        "postgres_db": "mlops",
        "minio_access_key": "minioadmin",
        "minio_secret_key": "minioadmin",
    }


@pytest.fixture(scope="session")
async def db_pool(test_config, docker_compose):
    """Asyncpg connection pool."""
    pool = await asyncpg.create_pool(
        user=test_config["postgres_user"],
        password=test_config["postgres_password"],
        database=test_config["postgres_db"],
        host=test_config["postgres_host"],
        port=test_config["postgres_port"],
    )
    yield pool
    await pool.close()


@pytest.fixture(scope="session")
def minio_client(test_config, docker_compose):
    """Minio client."""
    client = Minio(
        test_config["minio_url"],
        access_key=test_config["minio_access_key"],
        secret_key=test_config["minio_secret_key"],
        secure=False,
    )
    yield client


@pytest.fixture(scope="session")
def mlflow_client(docker_compose):
    """Mlflow client."""
    client = MlflowClient(tracking_uri="http://localhost:5000")
    yield client


@pytest.fixture(scope="session")
async def orchestrator_client(test_config, docker_compose):
    """Httpx AsyncClient for orchestrator."""
    async with httpx.AsyncClient(base_url=test_config["orchestrator_url"]) as client:
        yield client


@pytest.fixture(scope="session")
async def inference_client(test_config, docker_compose):
    """Httpx AsyncClient for inference service."""
    async with httpx.AsyncClient(base_url=test_config["inference_url"]) as client:
        yield client


@pytest.fixture(scope="session")
async def monitoring_client(test_config, docker_compose):
    """Httpx AsyncClient for monitoring service."""
    async with httpx.AsyncClient(base_url=test_config["monitoring_url"]) as client:
        yield client


@pytest.fixture(scope="function")
async def db_conn(db_pool):
    """Database connection."""
    async with db_pool.acquire() as connection:
        yield connection
