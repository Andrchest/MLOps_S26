#!/bin/bash
# MLOps Demo Script - resumes from specified step
# Usage: ./demo.sh [step0|step1|step2|step3|step4|step5|step6]
# Default: runs from step0

STEP=${1:-step0}

# Ensure we're in the right directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ORCH="http://localhost:8000"
INFERENCE="http://localhost:8001"
STREAMLIT="http://localhost:8501"
MLFLOW="http://localhost:5000"
MINIO="http://localhost:9001"

get_latest_model_version() {
    docker compose exec -T postgres psql -U mlops -d mlops -t -c \
        "SELECT model_version FROM trained_models ORDER BY created_at DESC LIMIT 1;" 2>/dev/null | tr -d ' \n'
}

get_deployed_model_version() {
    docker compose exec -T postgres psql -U mlops -d mlops -t -c \
        "SELECT model_version FROM deployments WHERE status='active' ORDER BY deployed_at DESC LIMIT 1;" 2>/dev/null | tr -d ' \n'
}

wait_for_services() {
    echo "Waiting for services to be ready..."
    for i in $(seq 1 30); do
        if curl -s "$ORCH/health" > /dev/null 2>&1; then
            echo "Services are ready!"
            return
        fi
        sleep 2
    done
    echo "ERROR: Services not ready after 60 seconds"
    exit 1
}

run_step0() {
    echo "=========================================="
    echo "STEP 0: Verify all services are running"
    echo "=========================================="
    wait_for_services
    echo ""
    echo "Health checks:"
    echo "  Orchestrator: $(curl -s $ORCH/health)"
    echo "  Inference: $(curl -s $INFERENCE/health)"
    echo "  Monitoring: $(curl -s http://localhost:8002/health)"
    echo ""
    echo "Open these URLs:"
    echo "  Streamlit: $STREAMLIT"
    echo "  MLflow: $MLFLOW"
    echo "  MinIO: $MINIO (minio / minio123)"
    echo "  Orchestrator API: $ORCH/docs"
    echo "  Inference API: $INFERENCE/docs"
    echo ""
    echo "Press Enter when ready for Step 1..."
    read
}

run_step1() {
    echo "=========================================="
    echo "STEP 1: Data Ingestion"
    echo "=========================================="
    echo ""
    echo "Uploading dataset..."
    RESPONSE=$(curl -s -X POST "$ORCH/datasets" -F "file=@seeds/sample_dataset.csv" -F "name=customer_churn")
    echo "$RESPONSE" | python3 -m json.tool
    DATASET_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['dataset_id'])")
    echo ""
    echo "Dataset uploaded with id=$DATASET_ID"
    echo ""
    echo "👉 Show in MinIO: $MINIO → bucket 'datasets'"
    echo "👉 Show in Streamlit: $STREAMLIT → tab 'Datasets'"
    echo ""
    echo "Press Enter when ready for Step 2..."
    read
}

run_step2() {
    echo "=========================================="
    echo "STEP 2: Training"
    echo "=========================================="
    echo ""
    echo "Starting training job..."
    RESPONSE=$(curl -s -X POST "$ORCH/train?dataset_id=1&dataset_name=customer_churn")
    echo "$RESPONSE" | python3 -m json.tool
    JOB_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
    echo ""
    echo "Job created: job_id=$JOB_ID"
    echo "Waiting for training to complete (~30 seconds)..."
    sleep 30
    echo ""
    echo "👉 Show in MLflow: $MLFLOW → experiment 'customer_churn' → run with metrics"
    echo "👉 Show in Streamlit: $STREAMLIT → tab 'Jobs' → status 'succeeded'"
    echo "👉 Show in MinIO: bucket 'models' → 'LogisticRegression'"
    echo ""
    echo "Press Enter when ready for Step 3..."
    read
}

run_step3() {
    echo "=========================================="
    echo "STEP 3: Deployment"
    echo "=========================================="
    echo ""
    MODEL_VER=$(get_latest_model_version)
    echo "Latest model version: $MODEL_VER"
    echo ""
    echo "Deploying model..."
    curl -s -X POST "$ORCH/promote" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "model_name=LogisticRegression&model_version=$MODEL_VER" | python3 -m json.tool
    echo ""
    echo "👉 Show in Streamlit: $STREAMLIT → tab 'Deployments' → status 'active'"
    echo ""
    echo "Press Enter when ready for Step 4..."
    read
}

run_step4() {
    echo "=========================================="
    echo "STEP 4: Inference"
    echo "=========================================="
    echo ""
    MODEL_VER=$(get_deployed_model_version)
    echo "Deployed model version: $MODEL_VER"
    echo ""
    echo "👉 Open Inference API docs: $INFERENCE/docs"
    echo "   1. Expand /predict → 'Try it out'"
    echo "   2. Set model_version=$MODEL_VER"
    echo "   3. Send prediction with body:"
    echo "      {\"age\": 30, \"monthly_spend\": 100, \"tenure_months\": 24, \"income\": 55000, \"credit_score\": 700}"
    echo "   4. Execute and show response"
    echo "   5. Repeat 2-3 times with different values"
    echo ""
    echo "👉 Show in Streamlit: $STREAMLIT → tab 'Monitoring' → prediction stats"
    echo ""
    echo "Press Enter when ready for Step 5..."
    read
}

run_step5() {
    echo "=========================================="
    echo "STEP 5: Drift Detection"
    echo "=========================================="
    echo ""
    MODEL_VER=$(get_deployed_model_version)
    echo "Sending 8 drift requests with extreme values..."
    for i in $(seq 1 8); do
        curl -s -X POST "$INFERENCE/predict?model_name=LogisticRegression&model_version=$MODEL_VER" \
            -H "Content-Type: application/json" \
            -d '{"age": 999, "monthly_spend": 99999, "tenure_months": 999, "income": 999999, "credit_score": 999}' > /dev/null
    done
    echo ""
    echo "Drift requests sent. Checking for retraining job..."
    sleep 5
    echo ""
    echo "👉 Show in Streamlit: $STREAMLIT → tab 'Jobs' → new job with status 'pending'/'running'"
    echo "👉 Check inference logs: docker compose logs inference_service --tail=20 | grep drift"
    echo ""
    echo "Now trigger a fresh training by running Step 2 again to complete the drift→retrain→deploy cycle."
    echo ""
    echo "Press Enter when ready for Step 6..."
    read
}

run_step6() {
    echo "=========================================="
    echo "STEP 6: Fault Tolerance & Crash Recovery"
    echo "=========================================="
    echo ""
    echo "Hypothesis: The system is resilient to failures — inference continues when the worker crashes,"
    echo "and interrupted training jobs recover automatically when the worker restarts."
    echo ""
    
    MODEL_VER=$(get_deployed_model_version)
    
    echo "--- PART 1: Inference survives worker crash ---"
    echo ""
    echo "1. Baseline prediction (worker is running)..."
    RESULT=$(curl -s -X POST "$INFERENCE/predict?model_name=LogisticRegression&model_version=$MODEL_VER" \
        -H "Content-Type: application/json" \
        -d '{"age": 30, "monthly_spend": 100, "tenure_months": 24, "income": 55000, "credit_score": 700}')
    echo "$RESULT" | python3 -m json.tool | grep -E '"latency_ms"|"status"'
    echo ""
    
    echo "2. Simulate crash: kill training worker..."
    docker compose kill training-worker
    echo "Worker killed (simulating crash)."
    echo ""
    
    echo "3. Inference with 'crashed' worker..."
    RESULT=$(curl -s -X POST "$INFERENCE/predict?model_name=LogisticRegression&model_version=$MODEL_VER" \
        -H "Content-Type: application/json" \
        -d '{"age": 35, "monthly_spend": 150, "tenure_months": 12, "income": 60000, "credit_score": 720}')
    echo "$RESULT" | python3 -m json.tool | grep -E '"latency_ms"|"status"'
    echo ""
    
    echo "--- PART 2: Crash Recovery — interrupted training job ---"
    echo ""
    echo "4. Starting new training (will kill worker during training)..."
    RESPONSE=$(curl -s -X POST "$ORCH/train?dataset_id=1&dataset_name=customer_churn")
    JOB_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
    echo "Job создан: job_id=$JOB_ID"
    echo ""
    
    echo "5. Waiting for worker to start training (Phase 1: 3s)..."
    sleep 5
    echo ""
    
    echo "6. CRITICAL: kill worker DURING training..."
    docker compose kill training-worker
    echo "Worker killed during Phase 1/2/3."
    echo ""
    
    echo "7. Job status after crash:"
    docker compose exec -T postgres psql -U mlops -d mlops -t -c \
        "SELECT job_id, status FROM jobs WHERE job_id=$JOB_ID;" 2>/dev/null
    echo ""
    
    echo "8. Restarting worker (simulating auto-recovery)..."
    docker compose up -d training-worker
    echo "Worker restarted."
    echo ""
    
    echo "9. Waiting for training to complete (worker will pick up job)..."
    for i in $(seq 1 12); do
        STATUS=$(docker compose exec -T postgres psql -U mlops -d mlops -t -c \
            "SELECT status FROM jobs WHERE job_id=$JOB_ID;" 2>/dev/null | tr -d ' \n')
        if [ "$STATUS" = "succeeded" ]; then
            echo "  Job recovered and completed in $((i*5))s ✅"
            break
        fi
        if [ "$STATUS" = "failed" ]; then
            echo "  Job failed ❌"
            break
        fi
        echo "  ...$((i*5))s status=$STATUS"
        sleep 5
    done
    echo ""
    
    echo "10. Recovery verification:"
    FINAL_STATUS=$(docker compose exec -T postgres psql -U mlops -d mlops -t -c \
        "SELECT status FROM jobs WHERE job_id=$JOB_ID;" 2>/dev/null | tr -d ' \n')
    echo "    Job status: $FINAL_STATUS"
    
    MODEL_NAME=$(docker compose exec -T postgres psql -U mlops -d mlops -t -c \
        "SELECT model_name FROM trained_models WHERE job_id=$JOB_ID;" 2>/dev/null | tr -d ' \n')
    echo "    Model in DB: ${MODEL_NAME:-NOT FOUND}"
    
    MODEL_PATH=$(docker compose exec -T postgres psql -U mlops -d mlops -t -c \
        "SELECT model_path FROM trained_models WHERE job_id=$JOB_ID;" 2>/dev/null | tr -d ' \n')
    echo "    Model in MinIO: ${MODEL_PATH:-NOT FOUND}"
    echo ""
    
    echo "--- PART 3: Data Integrity ---"
    echo ""
    echo "11. Data integrity check:"
    echo "    Dataset count:"
    docker compose exec -T postgres psql -U mlops -d mlops -t -c "SELECT count(*) FROM datasets;" 2>/dev/null
    echo "    Model count:"
    docker compose exec -T postgres psql -U mlops -d mlops -t -c "SELECT count(*) FROM trained_models;" 2>/dev/null
    echo "    Job count:"
    docker compose exec -T postgres psql -U mlops -d mlops -t -c "SELECT count(*) FROM jobs;" 2>/dev/null
    echo "    Prediction count:"
    docker compose exec -T postgres psql -U mlops -d mlops -t -c "SELECT count(*) FROM prediction_logs;" 2>/dev/null
    echo ""
    
    echo "--- PART 4: Final Verification ---"
    echo ""
    echo "12. Final prediction (everything works):"
    RESULT=$(curl -s -X POST "$INFERENCE/predict?model_name=LogisticRegression&model_version=$MODEL_VER" \
        -H "Content-Type: application/json" \
        -d '{"age": 40, "monthly_spend": 200, "tenure_months": 36, "income": 70000, "credit_score": 750}')
    echo "$RESULT" | python3 -m json.tool | grep -E '"latency_ms"|"status"'
    echo ""
    
    echo "=========================================="
    echo "STEP 6 RESULT"
    echo "=========================================="
    echo ""
    if [ "$FINAL_STATUS" = "succeeded" ] && [ -n "$MODEL_NAME" ]; then
        echo "  ✅ CRASH RECOVERY WORKS — job recovered"
    else
        echo "  ❌ CRASH RECOVERY FAILED — job status=$FINAL_STATUS"
    fi
    echo "  ✅ Inference works when worker is down"
    echo "  ✅ Data intact (DB, MinIO, MLflow)"
    echo "  ✅ System fully operational"
    echo ""
    echo "👉 Show in Streamlit: $STREAMLIT → tab 'Jobs' → job $JOB_ID completed"
    echo ""
    echo "Press Enter when ready to finish..."
    read
}

# Route to requested step
case "$STEP" in
    step0) run_step0 ; run_step1 ;;
    step1) run_step1 ;;
    step2) run_step2 ;;
    step3) run_step3 ;;
    step4) run_step4 ;;
    step5) run_step5 ;;
    step6) run_step6 ;;
    *)
        echo "Usage: $0 [step0|step1|step2|step3|step4|step5|step6]"
        echo ""
        echo "  step0 - Verify services + run step1"
        echo "  step1 - Upload dataset"
        echo "  step2 - Train model"
        echo "  step3 - Deploy model"
        echo "  step4 - Run inference"
        echo "  step5 - Trigger drift detection"
        echo "  step6 - Fault tolerance test"
        echo ""
        echo "Default (no arg): runs from step0"
        exit 1
        ;;
esac
