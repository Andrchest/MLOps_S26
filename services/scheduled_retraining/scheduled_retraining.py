"""Scheduled Retraining Service.

Periodically checks for active deployments and triggers retraining
based on a configurable schedule. Complements drift-based retraining
by ensuring models stay fresh even without detected drift.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta

import asyncpg
import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("scheduled_retraining")

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8000")
RETRAIN_INTERVAL_HOURS = int(os.getenv("RETRAIN_INTERVAL_HOURS", "24"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY_SECONDS", "30"))


async def get_active_deployments(db_pool: asyncpg.Pool) -> list[dict]:
    """Get all active deployments with their model info."""
    query = """
    SELECT d.deployment_id, d.model_name, d.model_version, d.deployed_at,
           j.dataset_id, j.dataset_name, j.dataset_path
    FROM deployments d
    JOIN trained_models tm ON tm.model_name = d.model_name AND tm.model_version = d.model_version
    JOIN jobs j ON j.job_id = tm.job_id
    WHERE d.status = 'active'
    """
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(query)
    return [dict(row) for row in rows]


async def check_last_retrain(deployment: dict, db_pool: asyncpg.Pool) -> bool:
    """Check if this deployment was retrained recently."""
    query = """
    SELECT MAX(j.created_at) as last_retrain
    FROM jobs j
    JOIN trained_models tm ON tm.job_id = j.job_id
    WHERE tm.model_name = $1 AND tm.model_version = $2
    """
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(query, deployment["model_name"], deployment["model_version"])
    last_retrain = row["last_retrain"] if row and row["last_retrain"] else None
    if last_retrain is None:
        return False
    return (datetime.now() - last_retrain) < timedelta(hours=RETRAIN_INTERVAL_HOURS)


async def trigger_retraining(deployment: dict) -> bool:
    """Trigger a retraining job via the orchestrator API."""
    url = f"{ORCHESTRATOR_URL}/train"
    params = {
        "dataset_name": deployment["dataset_name"],
        "dataset_id": deployment["dataset_id"],
        "dataset_path": deployment.get("dataset_path", ""),
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, params=params)
            if response.status_code == 200:
                job_id = response.json().get("job_id")
                logger.info(
                    "Scheduled retraining triggered for %s:%s (deployment_id=%s) -> job_id=%s",
                    deployment["model_name"],
                    deployment["model_version"],
                    deployment["deployment_id"],
                    job_id,
                )
                return True
            else:
                logger.warning(
                    "Failed to trigger retraining for %s:%s: %s",
                    deployment["model_name"],
                    deployment["model_version"],
                    response.text,
                )
                return False
    except Exception as exc:
        logger.error(
            "Error triggering retraining for %s:%s: %s",
            deployment["model_name"],
            deployment["model_version"],
            exc,
        )
        return False


async def run_retraining_cycle(db_pool: asyncpg.Pool) -> int:
    """Run one cycle of scheduled retraining. Returns number of jobs triggered."""
    deployments = await get_active_deployments(db_pool)
    if not deployments:
        logger.info("No active deployments found")
        return 0

    triggered = 0
    for deployment in deployments:
        if await check_last_retrain(deployment, db_pool):
            logger.debug(
                "Skipping %s:%s - recently retrained",
                deployment["model_name"],
                deployment["model_version"],
            )
            continue

        if await trigger_retraining(deployment):
            triggered += 1

    logger.info(
        "Scheduled retraining cycle complete: %d/%d deployments triggered",
        triggered,
        len(deployments),
    )
    return triggered


async def main():
    """Main entry point for scheduled retraining service."""
    db_pool = await asyncpg.create_pool(
        user=os.getenv("POSTGRES_USER", "mlops"),
        password=os.getenv("POSTGRES_PASSWORD", "mlops"),
        database=os.getenv("POSTGRES_DB", "mlops"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )

    interval_seconds = RETRAIN_INTERVAL_HOURS * 3600
    logger.info(
        "Scheduled retraining service started (interval: %d hours)",
        RETRAIN_INTERVAL_HOURS,
    )

    while True:
        try:
            await run_retraining_cycle(db_pool)
        except Exception as exc:
            logger.error("Error in retraining cycle: %s", exc)

        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    asyncio.run(main())
