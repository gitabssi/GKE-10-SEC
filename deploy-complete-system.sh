#!/bin/bash

# Complete System Deployment Script
# GKE Turns 10 Hackathon - Bank of Anthos + AI Fraud Detection
# 
# This script deploys the complete system with proper integration

set -e

echo "🚀 GKE Turns 10 Hackathon - Complete System Deployment"
echo "======================================================="

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
GEMINI_API_KEY="${GEMINI_API_KEY:-GEMINI _KEY}"

check_prerequisites() {
    print_status "Checking prerequisites..."
    
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
    
    # Check Kubernetes cluster
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Kubernetes cluster not accessible. Please check your kubeconfig."
        exit 1
    fi
    
    print_success "Prerequisites check completed"
}

configure_gemini_api() {
    print_status "Configuring Gemini API key..."
    
    if [ "$GEMINI_API_KEY" = "your-gemini-api-key-here" ] || [ -z "$GEMINI_API_KEY" ]; then
        print_error "Please set your Gemini API key:"
        echo "  export GEMINI_API_KEY=\"your-actual-api-key\""
        echo "  Get your key at: https://makersuite.google.com/app/apikey"
        exit 1
    fi
    
    # Update the secret in fraud detection manifests
    ENCODED_KEY=$(echo -n "$GEMINI_API_KEY" | base64)
    
    # Update fraud-api secret
    if [ -f "src/fraud-detection/fraud-api/k8s-manifests.yaml" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/GEMINI_API_KEY: .*/GEMINI_API_KEY: $ENCODED_KEY/" src/fraud-detection/fraud-api/k8s-manifests.yaml
        else
            # Linux
            sed -i "s/GEMINI_API_KEY: .*/GEMINI_API_KEY: $ENCODED_KEY/" src/fraud-detection/fraud-api/k8s-manifests.yaml
        fi
    fi
    
    print_success "Gemini API key configured"
}

apply_prerequisites() {
    print_status "Applying prerequisites..."
    
    # Apply JWT secret for Bank of Anthos
    if [ -f "extras/jwt/jwt-secret.yaml" ]; then
        kubectl apply -f extras/jwt/jwt-secret.yaml
        print_success "JWT secret applied"
    else
        print_warning "JWT secret file not found, skipping..."
    fi
    
    # Create fraud detection namespace
    kubectl create namespace fraud-detection --dry-run=client -o yaml | kubectl apply -f -
    print_success "Fraud detection namespace created"
}

deploy_system() {
    print_status "Deploying complete system..."
    print_status "This will take several minutes for the first deployment..."
    
    # Deploy everything using the main skaffold configuration
    print_status "Starting deployment with Skaffold..."
    
    # Use development profile with M1 Mac platform support
    skaffold dev --profile=development --port-forward --platform=linux/amd64 &
    SKAFFOLD_PID=$!
    
    print_status "Deployment started (PID: $SKAFFOLD_PID)"
    print_status "Waiting for services to be ready..."
    
    # Wait for Bank of Anthos services
    local retries=0
    while [ $retries -lt 60 ]; do
        if kubectl get pods -l app=frontend 2>/dev/null | grep -q "Running"; then
            print_success "Bank of Anthos services are running"
            break
        fi
        
        if [ $((retries % 10)) -eq 0 ]; then
            print_status "Waiting for Bank of Anthos services... (${retries}/60)"
        fi
        
        sleep 10
        retries=$((retries + 1))
    done
    
    # Wait for fraud detection services
    retries=0
    while [ $retries -lt 40 ]; do
        if kubectl get pods -n fraud-detection -l app=fraud-api 2>/dev/null | grep -q "Running"; then
            print_success "Fraud detection services are running"
            break
        fi
        
        if [ $((retries % 5)) -eq 0 ]; then
            print_status "Waiting for fraud detection services... (${retries}/40)"
        fi
        
        sleep 15
        retries=$((retries + 1))
    done
    
    print_success "System deployment completed!"
}

verify_deployment() {
    print_status "Verifying deployment..."
    
    # Check all pods
    print_status "Checking pod status..."
    kubectl get pods -A
    
    # Test fraud API
    print_status "Testing fraud API..."
    local retries=0
    while [ $retries -lt 10 ]; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            print_success "Fraud API is responding"
            break
        fi
        print_status "Waiting for Fraud API... (${retries}/10)"
        sleep 10
        retries=$((retries + 1))
    done
    
    if [ $retries -eq 10 ]; then
        print_warning "Fraud API not responding yet, but deployment may still be in progress"
    fi
    
    print_success "Deployment verification completed"
}

show_access_info() {
    print_success "🎉 Deployment completed successfully!"
    echo ""
    print_status "🌐 Access your services at:"
    echo "  🏦 Bank of Anthos:     http://localhost:8080"
    echo "  🚨 Fraud Dashboard:    http://localhost:8501"
    echo "  🔧 Fraud API:          http://localhost:8000"
    echo "  📚 API Documentation:  http://localhost:8000/docs"
    echo ""
    print_status "🧪 Test the system:"
    echo "  # Normal transaction (low risk)"
    echo "  curl -X POST http://localhost:8000/analyze \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"transactionId\":\"test-001\",\"amount\":450,\"timestamp\":\"2024-01-15T14:30:00Z\",\"fromAccountNum\":\"1234567890\",\"toAccountNum\":\"0987654321\"}'"
    echo ""
    echo "  # Suspicious transaction (high risk)"
    echo "  curl -X POST http://localhost:8000/analyze \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"transactionId\":\"test-002\",\"amount\":250000,\"timestamp\":\"2024-01-15T03:45:00Z\",\"fromAccountNum\":\"1234567890\",\"toAccountNum\":\"9999999999\"}'"
    echo ""
    print_status "📊 Monitor the system:"
    echo "  kubectl get pods -A"
    echo "  kubectl logs -f deployment/fraud-api -n fraud-detection"
    echo ""
    print_status "🎬 Demo scenarios:"
    echo "  cd demo && python transaction_generator.py"
    echo ""
    print_warning "Press Ctrl+C to stop all services"
}

run_demo() {
    print_status "Running demo scenarios..."
    
    # Wait for services to be fully ready
    sleep 30
    
    # Check if demo directory exists
    if [ -d "demo" ]; then
        cd demo
        
        # Install demo dependencies if requirements.txt exists
        if [ -f "requirements.txt" ]; then
            print_status "Installing demo dependencies..."
            python3 -m pip install -r requirements.txt &> /dev/null || true
        fi
        
        # Run demo if script exists
        if [ -f "transaction_generator.py" ]; then
            print_status "Running fraud detection demo..."
            python3 transaction_generator.py || print_warning "Demo script failed, but system is still running"
        fi
        
        cd ..
        print_success "Demo completed! Check the dashboard at http://localhost:8501"
    else
        print_warning "Demo directory not found. Skipping demo."
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
print_status "Starting complete system deployment..."

check_prerequisites
configure_gemini_api
apply_prerequisites
deploy_system
verify_deployment
show_access_info

# Ask if user wants to run demo
echo ""
read -p "Would you like to run the demo scenarios? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    run_demo
fi

# Keep running until interrupted
print_status "All services are running. Monitoring..."
print_status "Press Ctrl+C to stop all services"

while true; do
    sleep 30
    # Check if services are still running
    if ! kubectl get pods -n fraud-detection &> /dev/null; then
        print_warning "Fraud detection services stopped"
        break
    fi
done
