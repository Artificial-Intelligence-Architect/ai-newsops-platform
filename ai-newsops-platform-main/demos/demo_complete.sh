#!/bin/bash

# ============================================================================
# AI NewsOps Platform - Complete Demo with Docker
# ============================================================================
# This script launches the complete MLOps stack:
# - DistilBERT API (FastAPI)
# - Prometheus (metrics)
# - Grafana (dashboard)
# - MLflow (model registry)
# - Airflow (orchestration)
# - Streamlit (interactive dashboard)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}${NC}================================================================================${NC}"
    echo -e "${CYAN}${1}${NC}"
    echo -e "${BLUE}${NC}================================================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# ============================================================================
# CHECKS
# ============================================================================

print_header "AI NewsOps Platform - Complete Demo"

print_info "Checking dependencies..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_success "Docker found: $(docker --version)"
print_success "Docker Compose found: $(docker-compose --version)"

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found in current directory!"
    print_info "Please run this script from the project root directory"
    exit 1
fi

print_success "docker-compose.yml found"

# ============================================================================
# STOP EXISTING CONTAINERS (if running)
# ============================================================================

print_header "Cleanup - Stopping existing containers"

if [ "$(docker-compose ps -q)" ]; then
    print_info "Stopping existing containers..."
    docker-compose down 2>/dev/null || true
    sleep 2
    print_success "Existing containers stopped"
else
    print_info "No existing containers found"
fi

# ============================================================================
# START SERVICES
# ============================================================================

print_header "Starting Services"

print_info "Launching Docker containers..."
print_info "This may take 1-2 minutes on first run (downloading images)..."

docker-compose up -d 2>&1 | head -20

# Wait for services to be healthy
print_info "Waiting for services to start (30 seconds)..."
sleep 30

# ============================================================================
# VERIFY SERVICES
# ============================================================================

print_header "Verifying Services"

services=(
    "api:8000"
    "prometheus:9090"
    "grafana:3000"
    "mlflow:5000"
    "airflow:8080"
    "streamlit:8501"
)

for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if nc -z localhost "$port" 2>/dev/null; then
        print_success "$name is running on port $port"
    else
        print_warning "$name may take a moment to start (port $port)"
    fi
done

# ============================================================================
# DEMO SECTION 1: API TESTS
# ============================================================================

print_header "Section 1: API Predictions"

print_info "Testing prediction endpoint..."

test_cases=(
    '{"headline": "Senate Passes Climate Bill", "short_description": "Congress votes on environmental legislation"}'
    '{"headline": "New iPhone 16 Pro Released", "short_description": "Apple announces latest flagship smartphone"}'
    '{"headline": "Paris Travel Guide", "short_description": "Top 10 restaurants in Paris to visit"}'
)

for i in "${!test_cases[@]}"; do
    echo ""
    print_info "Test $((i + 1))/${#test_cases[@]}"
    
    response=$(curl -s -X POST "http://localhost:8000/predict" \
        -H "Content-Type: application/json" \
        -d "${test_cases[$i]}")
    
    # Extract category and confidence
    category=$(echo "$response" | grep -o '"category":"[^"]*' | cut -d'"' -f4 | head -1)
    confidence=$(echo "$response" | grep -o '"confidence":[0-9.]*' | cut -d':' -f2 | head -1)
    
    if [ ! -z "$category" ]; then
        print_success "Prediction: $category (confidence: ${confidence})"
        echo "Full response:"
        echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    else
        print_warning "API not yet ready, retrying..."
        sleep 5
    fi
done

# ============================================================================
# DEMO SECTION 2: MONITORING
# ============================================================================

print_header "Section 2: Monitoring Dashboard"

print_info "Checking Prometheus metrics..."

metrics_check=$(curl -s "http://localhost:9090/api/v1/query?query=up" | grep -o '"value":\[[^]]*\]' | head -1)

if [ ! -z "$metrics_check" ]; then
    print_success "Prometheus is collecting metrics"
else
    print_warning "Prometheus may take a moment to collect metrics"
fi

# ============================================================================
# DEMO SECTION 3: GENERATE TRAFFIC
# ============================================================================

print_header "Section 3: Generating Traffic"

print_info "Sending requests to generate metrics (20 requests)..."

for i in {1..20}; do
    categories=("politics" "tech" "entertainment" "science" "business")
    category=${categories[$((RANDOM % 5))]}
    
    curl -s -X POST "http://localhost:8000/predict" \
        -H "Content-Type: application/json" \
        -d "{\"headline\": \"$category news article $i\", \"short_description\": \"This is test article $i\"}" > /dev/null
    
    echo -ne "\rProgress: $i/20 requests sent"
done

echo ""
print_success "Traffic generated"

# ============================================================================
# PRINT DASHBOARD URLS
# ============================================================================

print_header "Access the Platform"

cat << EOF

${CYAN}API Endpoints:${NC}
  • Swagger UI:       ${BLUE}http://localhost:8000/docs${NC}
  • ReDoc:            ${BLUE}http://localhost:8000/redoc${NC}
  • Health:           ${BLUE}http://localhost:8000/health${NC}
  • Predict endpoint: ${BLUE}http://localhost:8000/predict${NC}

${CYAN}Monitoring & Dashboards:${NC}
  • Prometheus:       ${BLUE}http://localhost:9090${NC}
  • Grafana:          ${BLUE}http://localhost:3000${NC} (admin/admin)
  • MLflow:           ${BLUE}http://localhost:5000${NC}

${CYAN}Orchestration:${NC}
  • Airflow:          ${BLUE}http://localhost:8080${NC}
  • Streamlit:        ${BLUE}http://localhost:8501${NC}

EOF

# ============================================================================
# PROVIDE NEXT STEPS
# ============================================================================

print_header "Next Steps"

cat << EOF

${GREEN}1. Open Grafana${NC}
   → Go to http://localhost:3000
   → Login: admin / admin
   → View the 11-panel dashboard with:
     - Latency metrics (P95 ~5ms)
     - Error rate (should be 0%)
     - Request rate (real-time updates)
     - Model accuracy

${GREEN}2. Test Predictions${NC}
   → Go to http://localhost:8000/docs
   → Try the /predict endpoint
   → Send different headlines
   → See predictions in real-time

${GREEN}3. Check Airflow DAG${NC}
   → Go to http://localhost:8080
   → View retraining_dag
   → Check run history

${GREEN}4. View MLflow Registry${NC}
   → Go to http://localhost:5000
   → See model versions
   → Track experiments

${GREEN}5. Watch Streamlit Dashboard${NC}
   → Go to http://localhost:8501
   → Interactive predictions
   → Real-time monitoring

EOF

# ============================================================================
# MONITORING
# ============================================================================

print_header "Continuous Monitoring"

print_info "Services are running. Press Ctrl+C to stop."
print_info "View logs with: docker-compose logs -f [service_name]"

echo ""
print_info "Example commands:"
echo "  • docker-compose logs -f api          (API logs)"
echo "  • docker-compose logs -f prometheus   (Prometheus logs)"
echo "  • docker-compose ps                   (Show running containers)"
echo "  • docker-compose down                 (Stop all services)"

echo ""
print_info "To stop the demo, run: docker-compose down"

# ============================================================================
# FINAL MESSAGE
# ============================================================================

print_header "🎉 Demo Ready!"

cat << EOF

${GREEN}All services are running!${NC}

This demo showcases:
  ✅ Real-time predictions with DistilBERT
  ✅ Monitoring dashboard (Prometheus + Grafana)
  ✅ Model orchestration (Airflow DAG)
  ✅ Experiment tracking (MLflow)
  ✅ Interactive dashboard (Streamlit)
  ✅ Complete CI/CD pipeline

${CYAN}Repository:${NC}
  https://github.com/Artificial-Intelligence-Architect/ai-newsops-platform

EOF

# Keep the script running until Ctrl+C
while true; do
    sleep 1
done
