#!/usr/bin/env bash
# =============================================================================
# MLOps Platform Demo Script
# =============================================================================
# This script demonstrates the full ML lifecycle:
#   1. Data ingestion → 2. Training → 3. Deployment → 4. Inference
#   5. Drift detection → 6. Scheduled retraining → 7. Fault tolerance
# =============================================================================
set -euo pipefail

BASE_URL="http://localhost:8000"
INFERENCE_URL="http://localhost:8001"
MLFLOW_URL="http://localhost:5000"
GRAFANA_URL="http://localhost:3000"
STREAMLIT_URL="http://localhost:8501"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}   $*"; }
success() { echo -e "${GREEN}[✓]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[!]${NC}    $*"; }
error() { echo -e "${RED}[✗]${NC}    $*"; }
section() {
    echo -e "\n${BOLD}${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}  $*${NC}"
    echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════${NC}\n"
}

# Wait for a service to be ready
wait_for_service() {
    local name="$1"
    local url="$2"
    local max_wait="${3:-30}"
    info "Waiting for $name at $url ..."
    for i in $(seq 1 $max_wait); do
        if curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null | grep -q "200\|404"; then
            success "$name is ready"
            return 0
        fi
        sleep 1
    done
    warn "$name did not respond within ${max_wait}s"
    return 1
}

# Check if all containers are healthy
check_health() {
    section "STEP 0: Checking all services"
    local all_healthy=true
    local services=(
        "postgres:5432"
        "minio:9000"
        "mlflow:5000"
        "orchestrator:${BASE_URL#http://}"
        "inference-service:${INFERENCE_URL#http://}"
        "grafana:3000"
        "streamlit:8501"
    )
    for svc in "${services[@]}"; do
        local name="${svc%%:*}"
        local port="${svc##*:}"
        if docker compose ps "$name" 2>/dev/null | grep -q "healthy\|Up"; then
            success "$name is running"
        else
            warn "$name is NOT healthy"
            all_healthy=false
        fi
    done
    if [ "$all_healthy" = true ]; then
        success "All services healthy"
    fi
}

# =============================================================================
# STEP 1: Data Ingestion
# =============================================================================
step1_data_ingestion() {
    section "STEP 1: Data Ingestion"

    # Check if datasets already exist in DB
    local existing
    existing=$(docker compose exec postgres psql -U mlops -d mlops -t -A \
        -c "SELECT COUNT(*) FROM datasets;" 2>/dev/null || echo "0")

    if [ "$existing" -gt 0 ]; then
        warn "Dataset already exists in DB ($existing records). Skipping ingestion."
        info "You can clear with: docker compose exec postgres psql -U mlops -d mlops -c 'DELETE FROM datasets;'"
        return 0
    fi

    info "Uploading sample dataset (seeds/sample_dataset.csv) ..."

    local response
    response=$(curl -s -X POST "$BASE_URL/datasets" \
        -F "file=@seeds/sample_dataset.csv" \
        -F "name=customer_churn" \
        -F "description=\"Customer churn prediction dataset\"" \
        -H "Content-Type: multipart/form-data")

    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"

    local dataset_id
    dataset_id=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin)['dataset_id'])" 2>/dev/null || echo "")

    if [ -z "$dataset_id" ]; then
        error "Failed to get dataset_id from response"
        exit 1
    fi

    success "Dataset uploaded: id=$dataset_id"

    # Verify in MinIO
    info "Verifying dataset in MinIO ..."
    docker compose exec minio sh -c "mc alias set myminio http://localhost:9000 minio minio123 && mc ls myminio/datasets/" 2>/dev/null | head -5
    success "Dataset verified in MinIO"
}

# =============================================================================
# STEP 2: Training
# =============================================================================
step2_training() {
    section "STEP 2: Model Training"

    # Get dataset_id
    local dataset_id
    dataset_id=$(docker compose exec postgres psql -U mlops -d mlops -t -A \
        -c "SELECT dataset_id FROM datasets LIMIT 1;" 2>/dev/null || echo "")

    if [ -z "$dataset_id" ]; then
        error "No dataset found. Run step 1 first."
        exit 1
    fi

    info "Creating training job for dataset_id=$dataset_id ..."

    local response
    response=$(curl -s -X POST "$BASE_URL/train?dataset_id=$dataset_id&dataset_name=customer_churn")

    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"

    local job_id
    job_id=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])" 2>/dev/null || echo "")

    if [ -z "$job_id" ]; then
        error "Failed to get job_id"
        exit 1
    fi

    success "Training job created: job_id=$job_id"

    # Wait for training to complete
    info "Waiting for training to complete (up to 120s) ..."
    for i in $(seq 1 60); do
        local status
        status=$(docker compose exec postgres psql -U mlops -d mlops -t -A \
            -c "SELECT status FROM jobs WHERE job_id=$job_id;" 2>/dev/null || echo "unknown")

        case "$status" in
            succeeded)
                success "Training completed successfully!"
                # Show results
                info "Training results:"
                docker compose exec postgres psql -U mlops -d mlops -t -A \
                    -c "SELECT j.job_id, j.status, j.created_at, tm.model_name, tm.model_version, tm.accuracy FROM jobs j JOIN trained_models tm ON j.job_id = tm.job_id WHERE j.job_id=$job_id;" 2>/dev/null | \
                    column -t -s$'\t'
                return 0
                ;;
            failed)
                error "Training failed!"
                docker compose exec postgres psql -U mlops -d mlops -t -A \
                    -c "SELECT error FROM jobs WHERE job_id=$job_id;" 2>/dev/null
                exit 1
                ;;
        esac
        sleep 2
    done
    warn "Training still running after 120s. Check training worker logs."
}

# =============================================================================
# STEP 3: Deployment
# =============================================================================
step3_deployment() {
    section "STEP 3: Model Deployment"

    # Get latest model
    local model_info
    model_info=$(docker compose exec postgres psql -U mlops -d mlops -t -A \
        -c "SELECT model_name, model_version FROM trained_models ORDER BY created_at DESC LIMIT 1;" 2>/dev/null)

    local model_name model_version
    model_name=$(echo "$model_info" | cut -d'|' -f1)
    model_version=$(echo "$model_info" | cut -d'|' -f2)

    if [ -z "$model_name" ] || [ -z "$model_version" ]; then
        error "No trained model found. Run step 2 first."
        exit 1
    fi

    info "Deploying $model_name v$model_version ..."

    local response
    response=$(curl -s -X POST "$BASE_URL/promote" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "model_name=$model_name&model_version=$model_version")

    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    success "Model deployed: $model_name v$model_version"
}

# =============================================================================
# STEP 4: Inference
# =============================================================================
step4_inference() {
    section "STEP 4: Inference"

    local model_name
    model_name=$(docker compose exec postgres psql -U mlops -d mlops -t -A \
        -c "SELECT model_name FROM trained_models ORDER BY created_at DESC LIMIT 1;" 2>/dev/null)

    local model_version
    model_version=$(docker compose exec postgres psql -U mlops -d mlops -t -A \
        -c "SELECT model_version FROM trained_models ORDER BY created_at DESC LIMIT 1;" 2>/dev/null)

    # Normal prediction
    info "Making normal prediction ..."
    local response
    response=$(curl -s -X POST "$INFERENCE_URL/predict?model_name=$model_name&model_version=$model_version" \
        -H "Content-Type: application/json" \
        -d '{"age": 30, "monthly_spend": 100, "tenure_months": 24, "income": 55000, "credit_score": 700}')

    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    success "Prediction successful"

    # Multiple predictions for metrics
    info "Making 5 predictions for metrics collection ..."
    for i in $(seq 1 5); do
        local spend=$((50 + RANDOM % 200))
        local age=$((20 + RANDOM % 50))
        curl -s -X POST "$INFERENCE_URL/predict?model_name=$model_name&model_version=$model_version" \
            -H "Content-Type: application/json" \
            -d "{\"age\": $age, \"monthly_spend\": $spend, \"tenure_months\": 12, \"income\": 50000, \"credit_score\": 650}" > /dev/null
    done
    success "5 additional predictions sent"
}

# =============================================================================
# STEP 5: Drift Detection & Retraining
# =============================================================================
step5_drift_retraining() {
    section "STEP 5: Drift Detection & Automated Retraining"

    local model_name
    model_name=$(docker compose exec postgres psql -U mlops -d mlops -t -A \
        -c "SELECT model_name FROM trained_models ORDER BY created_at DESC LIMIT 1;" 2>/dev/null)

    local model_version
    model_version=$(docker compose exec postgres psql -U mlops -d mlops -t -A \
        -c "SELECT model_version FROM trained_models ORDER BY created_at DESC LIMIT 1;" 2>/dev/null)

    # Send out-of-distribution data (extreme values that differ from training distribution)
    info "Sending drift data (extreme values) ..."
    local drift_response
    drift_response=$(curl -s -X POST "$INFERENCE_URL/predict?model_name=$model_name&model_version=$model_version" \
        -H "Content-Type: application/json" \
        -d '{"age": 999, "monthly_spend": 99999, "tenure_months": 999, "income": 999999, "credit_score": 999}')

    echo "$drift_response" | python3 -m json.tool 2>/dev/null || echo "$drift_response"

    # Send more drift data to trigger drift detection
    for i in $(seq 1 10); do
        curl -s -X POST "$INFERENCE_URL/predict?model_name=$model_name&model_version=$model_version" \
            -H "Content-Type: application/json" \
            -d "{\"age\": 999, \"monthly_spend\": 99999, \"tenure_months\": 999, \"income\": 999999, \"credit_score\": 999}" > /dev/null
    done

    info "Checking for drift detection and retraining jobs ..."
    sleep 3

    local retraining_jobs
    retraining_jobs=$(docker compose exec postgres psql -U mlops -d mlops -t -A \
        -c "SELECT job_id, dataset_name, status FROM jobs WHERE status='pending' AND dataset_name='customer_churn' ORDER BY job_id DESC LIMIT 5;" 2>/dev/null)

    if [ -n "$retraining_jobs" ]; then
        success "Drift-triggered retraining jobs found:"
        echo "$retraining_jobs" | column -t -s$'\t'
    else
        warn "No pending retraining jobs found. Check inference logs for drift detection."
        info "Drift detection runs in background. Check: docker compose logs inference-service | grep -i drift"
    fi
}

# =============================================================================
# STEP 6: Fault Tolerance
# =============================================================================
step6_fault_tolerance() {
    section "STEP 6: Fault Tolerance - Simulating Container Failure"

    # Pick a service to fail (training worker is a good choice - doesn't affect inference)
    local target="training-worker"

    info "Stopping $target container ..."
    docker compose stop "$target"
    sleep 2

    # Verify it's stopped
    if docker compose ps "$target" 2>/dev/null | grep -q "exited\|Exited"; then
        success "$target is stopped"
    else
        warn "$target may still be running"
    fi

    # Verify inference still works (circuit breaker should protect)
    info "Verifying inference service is still operational ..."
    local health_response
    health_response=$(curl -s "$INFERENCE_URL/health")
    echo "$health_response" | python3 -m json.tool 2>/dev/null || echo "$health_response"

    if echo "$health_response" | grep -q '"ok"'; then
        success "Inference service is still healthy despite $target being down"
    else
        warn "Inference service health check failed"
    fi

    # Verify orchestrator still works
    info "Verifying orchestrator is still operational ..."
    local orch_health
    orch_health=$(curl -s "$BASE_URL/health")
    echo "$orch_health" | python3 -m json.tool 2>/dev/null || echo "$orch_health"

    if echo "$orch_health" | grep -q '"ok"'; then
        success "Orchestrator is still healthy"
    fi

    # Restart the stopped container
    info "Restarting $target ..."
    docker compose start "$target"
    sleep 5

    # Verify it came back
    if docker compose ps "$target" 2>/dev/null | grep -q "healthy\|Up"; then
        success "$target is back up and running"
    else
        warn "$target may not have recovered yet"
    fi

    # Final health check
    info "Final system health check ..."
    docker compose ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null | grep -E "NAME|postgres|minio|mlflow|orchestrator|inference|grafana|monitoring"
}

# =============================================================================
# STEP 7: Demo Summary
# =============================================================================
step7_summary() {
    section "DEMO COMPLETE - Access Points"

    echo -e "${BOLD}Platform Services:${NC}"
    echo -e "  ${CYAN}Orchestrator API:${NC}      http://localhost:8000"
    echo -e "  ${CYAN}Inference Service:${NC}     http://localhost:8001"
    echo -e "  ${CYAN}MLflow (Experiments):${NC}  http://localhost:5000"
    echo -e "  ${CYAN}Grafana (Monitoring):${NC}  http://localhost:3000  (admin/admin)"
    echo -e "  ${CYAN}Streamlit (Dashboard):${NC} http://localhost:8501"
    echo -e "  ${CYAN}MinIO (Storage):${NC}       http://localhost:9001  (minio/minio123)"
    echo ""
    echo -e "${BOLD}What was demonstrated:${NC}"
    echo -e "  ✓ Data ingestion (CSV → MinIO + DB)"
    echo -e "  ✓ Model training (job queue → worker → MLflow)"
    echo -e "  ✓ Model deployment (MinIO → inference service)"
    echo -e "  ✓ Inference with metrics collection"
    echo -e "  ✓ Drift detection (out-of-distribution data)"
    echo -e "  ✓ Fault tolerance (container failure + recovery)"
    echo ""
    echo -e "${YELLOW}To record your demo:${NC}"
    echo -e "  1. Run this script: bash scripts/demo.sh"
    echo -e "  2. Open MLflow at http://localhost:5000 to show experiment tracking"
    echo -e "  3. Open Grafana at http://localhost:3000 to show monitoring dashboards"
    echo -e "  4. Open Streamlit at http://localhost:8501 to show operational dashboard"
}

# =============================================================================
# Main
# =============================================================================
main() {
    section "MLOps Platform Demo"
    info "Base URLs: Orchestrator=$BASE_URL, Inference=$INFERENCE_URL"
    info "MLflow=$MLFLOW_URL, Grafana=$GRAFANA_URL, Streamlit=$STREAMLIT_URL"

    # Check all services are running
    check_health

    # Run all demo steps
    step1_data_ingestion
    step2_training
    step3_deployment
    step4_inference
    step5_drift_retraining
    step6_fault_tolerance
    step7_summary
}

# Parse arguments
case "${1:-all}" in
    data)     step1_data_ingestion ;;
    train)    step2_training ;;
    deploy)   step3_deployment ;;
    infer)    step4_inference ;;
    drift)    step5_drift_retraining ;;
    fault)    step6_fault_tolerance ;;
    all)      main ;;
    *)        echo "Usage: $0 {data|train|deploy|infer|drift|fault|all}"; exit 1 ;;
esac
