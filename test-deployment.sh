#!/bin/bash

# Test Deployment Script
# GKE Turns 10 Hackathon - Bank of Anthos + AI Fraud Detection

set -e

echo "🧪 Testing Fraud Detection System Deployment"
echo "============================================="

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

# Test 1: Skaffold Configuration
print_status "Testing Skaffold configuration..."
if skaffold build --dry-run --profile=development > /dev/null 2>&1; then
    print_success "Skaffold configuration is valid"
else
    print_error "Skaffold configuration has errors"
    exit 1
fi

# Test 2: Kubernetes Manifests
print_status "Testing Kubernetes manifests..."
if kubectl apply --dry-run=client -k src/fraud-detection/fraud-api/k8s/overlays/development > /dev/null 2>&1; then
    print_success "Fraud API manifests are valid"
else
    print_error "Fraud API manifests have errors"
    exit 1
fi

# Test 3: ADK Agent Import
print_status "Testing ADK Agent import..."
cd src/fraud-detection/fraud-api
if python3 -c "from adk_agent import FraudDetectionAgent; print('ADK Agent import successful')" 2>/dev/null; then
    print_success "ADK Agent imports correctly"
else
    print_error "ADK Agent import failed"
    cd ../../..
    exit 1
fi
cd ../../..

# Test 4: Gemini API Configuration
print_status "Testing Gemini API configuration..."
if [ -n "$GEMINI_API_KEY" ] && [ "$GEMINI_API_KEY" != "your-gemini-api-key-here" ]; then
    print_success "Gemini API key is configured"
else
    print_warning "Gemini API key not set. Set with: export GEMINI_API_KEY='your-key'"
fi

# Test 5: Docker Build Context
print_status "Testing Docker build contexts..."
for service in fraud-api fraud-monitor fraud-dashboard; do
    if [ -f "src/fraud-detection/$service/Dockerfile" ]; then
        print_success "$service Dockerfile exists"
    else
        print_error "$service Dockerfile missing"
        exit 1
    fi
done

print_success "All tests passed! ✅"
echo ""
print_status "🚀 Ready to deploy with:"
echo "  skaffold dev --profile=development --port-forward --platform=linux/amd64"
echo ""
print_status "📊 Services will be available at:"
echo "  🏦 Bank of Anthos:     http://localhost:8080"
echo "  🚨 Fraud Dashboard:    http://localhost:8501"
echo "  🔧 Fraud API:          http://localhost:8000"
echo "  📚 API Documentation:  http://localhost:8000/docs"
