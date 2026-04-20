import sys
from pathlib import Path

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
