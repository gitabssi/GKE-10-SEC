#!/bin/bash

# M1 Mac Specific Deployment Script for Fraud Detection System
# GKE Turns 10 Hackathon 

set -e

echo "🚀 Deploying Fraud Detection System on M1 Mac"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
GEMINI_API_KEY="GEMINI_KEY"

check_prerequisites() {
    print_status "Checking prerequisites for M1 Mac..."
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check if skaffold is installed
    if ! command -v skaffold &> /dev/null; then
        print_error "skaffold is not installed. Please install skaffold first."
        exit 1
    fi
    
    # Check if docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    # Check Docker buildx for multi-platform builds
    if ! docker buildx version &> /dev/null; then
        print_warning "Docker buildx not available. Installing..."
        docker buildx install
    fi
    
    print_success "Prerequisites check completed"
}

cleanup_previous_deployments() {
    print_status "Cleaning up any previous deployments..."
    
    # Kill any existing skaffold processes
    pkill -f "skaffold" || true
    
    # Delete fraud detection namespace if it exists
    kubectl delete namespace fraud-detection --ignore-not-found=true
    
    # Wait for cleanup
    sleep 5
    
    print_success "Cleanup completed"
}

deploy_bank_of_anthos() {
    print_status "Deploying Bank of Anthos..."
    
    # Go to parent directory
    cd ..
    
    # Check if already running
    if kubectl get pods -l app=frontend 2>/dev/null | grep -q "Running"; then
        print_success "Bank of Anthos is already running"
        cd fraud-detection-system
        return
    fi
    
    # Apply JWT secret
    print_status "Applying JWT secret..."
    kubectl apply -f ./extras/jwt/jwt-secret.yaml
    
    # Start Bank of Anthos deployment
    print_status "Starting Bank of Anthos (this will take a few minutes)..."
    skaffold dev --profile=development --port-forward --platform=linux/amd64 &
    BANK_PID=$!
    
    # Wait for services to be ready
    print_status "Waiting for Bank of Anthos services..."
    local retries=0
    while [ $retries -lt 60 ]; do
        if kubectl get pods 2>/dev/null | grep -E "(frontend|userservice|ledgerwriter)" | grep -q "Running"; then
            print_success "Bank of Anthos core services are running"
            break
        fi
        
        if [ $((retries % 10)) -eq 0 ]; then
            print_status "Still waiting for Bank of Anthos... (${retries}/60)"
            kubectl get pods 2>/dev/null || true
        fi
        
        sleep 10
        retries=$((retries + 1))
    done
    
    if [ $retries -eq 60 ]; then
        print_error "Bank of Anthos failed to start within 10 minutes"
        print_status "Current pod status:"
        kubectl get pods
        exit 1
    fi
    
    # Return to fraud detection directory
    cd fraud-detection-system
}

deploy_fraud_detection() {
    print_status "Deploying Fraud Detection System..."
    
    # Ensure we have the Gemini API key configured
    print_status "Configuring Gemini API key..."
    ENCODED_KEY=$(echo -n "$GEMINI_API_KEY" | base64)
    
    # Update the secret in fraud-api.yaml
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/GEMINI_API_KEY: .*/GEMINI_API_KEY: $ENCODED_KEY/" k8s/fraud-api.yaml
    else
        # Linux
        sed -i "s/GEMINI_API_KEY: .*/GEMINI_API_KEY: $ENCODED_KEY/" k8s/fraud-api.yaml
    fi
    
    print_success "Gemini API key configured"
    
    # Deploy fraud detection system
    print_status "Building and deploying fraud detection services..."
    print_status "This may take several minutes for the first build..."
    
    # Use development profile with M1 Mac platform support
    skaffold dev --profile=development --port-forward --platform=linux/amd64 &
    FRAUD_PID=$!
    
    # Wait for fraud detection services
    print_status "Waiting for fraud detection services to be ready..."
    local retries=0
    while [ $retries -lt 40 ]; do
        if kubectl get pods -n fraud-detection 2>/dev/null | grep -q "Running"; then
            print_success "Fraud Detection System is running"
            break
        fi
        
        if [ $((retries % 5)) -eq 0 ]; then
            print_status "Building/deploying fraud detection services... (${retries}/40)"
            kubectl get pods -n fraud-detection 2>/dev/null || print_status "Namespace not ready yet..."
        fi
        
        sleep 15
        retries=$((retries + 1))
    done
    
    if [ $retries -eq 40 ]; then
        print_warning "Fraud detection services taking longer than expected"
        print_status "Current status:"
        kubectl get pods -n fraud-detection 2>/dev/null || print_status "Namespace not created yet"
    fi
    
    print_success "Fraud Detection System deployed!"
}

show_access_info() {
    print_success "Deployment completed successfully!"
    echo ""
    print_status "🌐 Access your services at:"
    echo "  📊 Fraud Dashboard:    http://localhost:8501"
    echo "  🔧 Fraud API:          http://localhost:8000"
    echo "  📚 API Documentation:  http://localhost:8000/docs"
    echo "  🏦 Bank of Anthos:     http://localhost:8080"
    echo ""
    print_status "🧪 Test the system:"
    echo "  cd demo && python transaction_generator.py"
    echo ""
    print_status "📊 Monitor the system:"
    echo "  kubectl get pods -n fraud-detection"
    echo "  kubectl logs -f deployment/fraud-api -n fraud-detection"
    echo ""
    print_warning "Press Ctrl+C to stop all services"
}

run_demo() {
    print_status "Running demo scenarios..."
    
    # Wait a bit more for services to be fully ready
    sleep 30
    
    # Check if fraud API is responding
    local retries=0
    while [ $retries -lt 10 ]; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            print_success "Fraud API is responding"
            break
        fi
        print_status "Waiting for Fraud API to be ready... (${retries}/10)"
        sleep 10
        retries=$((retries + 1))
    done
    
    if [ $retries -eq 10 ]; then
        print_warning "Fraud API not responding. Demo skipped."
        return
    fi
    
    # Run demo if available
    if [ -f "demo/transaction_generator.py" ]; then
        print_status "Installing demo dependencies..."
        cd demo
        python3 -m pip install -r requirements.txt &> /dev/null || true
        
        print_status "Running fraud detection demo..."
        python3 transaction_generator.py
        cd ..
        
        print_success "Demo completed! Check the dashboard at http://localhost:8501"
    else
        print_warning "Demo script not found. Skipping demo."
    fi
}

# Trap to cleanup on exit
cleanup() {
    print_status "Cleaning up..."
    pkill -f "skaffold" || true
    exit 0
}
trap cleanup INT TERM

# Main execution
print_status "Starting M1 Mac deployment process..."

check_prerequisites
cleanup_previous_deployments
deploy_bank_of_anthos
deploy_fraud_detection
show_access_info
run_demo

# Keep running until interrupted
print_status "All services are running. Monitoring..."
while true; do
    sleep 30
    # Check if services are still running
    if ! kubectl get pods -n fraud-detection &> /dev/null; then
        print_warning "Fraud detection services stopped"
        break
    fi
done
