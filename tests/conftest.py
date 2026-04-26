import sys
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

import services.orchestrator.app as app_module

# Add project root to sys.path so "services.X" imports work
root = Path(__file__).parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

# Add service directories to sys.path for bare imports (e.g., from dataset_service import ...)
# In Docker, WORKDIR is the service directory, so bare imports work
for svc in [
    "services/orchestrator",
    "services/training_worker",
    "services/inference_service",
]:
    svc_path = root / svc
    if str(svc_path) not in sys.path:
        sys.path.insert(0, str(svc_path))


# -----------------------
# Fake DB layer
# -----------------------
class FakeConn:
    def __init__(self):
        # tables
        self.jobs = {}
        self.deployments = []
        self.models = set()

        # sequences
        self.job_seq = 1
        self.deployment_seq = 1

    # -------------------------
    # SELECT SINGLE VALUE
    # -------------------------
    async def fetchval(self, query, *args):

        # idempotency check
        if "FROM jobs WHERE client_id" in query:
            client_id = args[0]
            for job_id, job in self.jobs.items():
                if job["client_id"] == client_id:
                    return job_id
            return None

        # insert job
        if "INSERT INTO jobs" in query:
            job_id = self.job_seq
            self.jobs[job_id] = {
                "client_id": args[0],
                "dataset_name": args[1],
                "dataset_id": args[2],
                "status": "pending",
            }
            self.job_seq += 1
            return job_id

        # job status
        if "FROM jobs WHERE job_id" in query:
            job_id = int(args[0])
            return self.jobs.get(job_id, {}).get("status")

        return None

    # -------------------------
    # SELECT MULTI ROWS
    # -------------------------
    async def fetch(self, query, *args):

        # model deployments by model
        if "FROM deployments" in query and "model_name" in query:
            model = args[0]
            return [d for d in self.deployments if d["model_name"] == model]

        # all deployments
        if "FROM deployments ORDER BY" in query:
            return list(self.deployments)

        # rollback (last 2)
        if "LIMIT 2" in query:
            model = args[0]
            filtered = [r for r in self.deployments if r["model_name"] == model]
            return filtered[:2]

        # list models
        if "FROM trained_models" in query:
            return [{"model_name": m} for m in self.models]

        return []

    # -------------------------
    # EXECUTE (INSERT / UPDATE)
    # -------------------------
    async def execute(self, query, *args):

        # promote model
        if "INSERT INTO deployments" in query:
            self.deployments.append(
                {
                    "deployment_id": self.deployment_seq,
                    "model_name": args[0],
                    "model_version": args[1],
                    "deployed_by": args[2],
                    "status": "active",
                }
            )

            self.models.add(args[0])
            self.deployment_seq += 1

        # rollback update
        if "UPDATE deployments" in query:
            dep_id = args[0]
            for r in self.deployments:
                if r["deployment_id"] == dep_id:
                    r["status"] = "active"


class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        pass


class FakePool:
    def __init__(self):
        self.conn = FakeConn()

    def acquire(self):
        return FakeAcquire(self.conn)


# -----------------------
# Fixtures
# -----------------------
@pytest.fixture
async def client():
    app_module.db_pool = FakePool()

    transport = ASGITransport(app=app_module.app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
