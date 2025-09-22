#!/bin/bash

# Fraud Detection System Deployment Script
# GKE Turns 10 Hackathon 

set -e

echo "🚀 Deploying Fraud Detection System for GKE Turns 10 Hackathon"
echo "================================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
GEMINI_API_KEY=${GEMINI_API_KEY:-""}
DEPLOY_MODE=${DEPLOY_MODE:-"local"}  # local or gke

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
    
    # Check Gemini API key
    if [ -z "$GEMINI_API_KEY" ]; then
        print_warning "GEMINI_API_KEY not set. Using placeholder key."
        print_warning "Please update k8s/fraud-api.yaml with your actual API key."
    fi
    
    print_success "Prerequisites check completed"
}

setup_gemini_api_key() {
    if [ -n "$GEMINI_API_KEY" ]; then
        print_status "Setting up Gemini API key..."
        
        # Base64 encode the API key
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
    fi
}

deploy_bank_of_anthos() {
    print_status "Checking Bank of Anthos deployment..."

    # Check if Bank of Anthos is already running
    if kubectl get pods -l app=frontend &> /dev/null; then
        print_success "Bank of Anthos is already running"
        return
    fi

    print_status "Deploying Bank of Anthos..."

    # Go to parent directory for Bank of Anthos
    cd ..

    # Apply JWT secret first
    print_status "Applying JWT secret..."
    kubectl apply -f ./extras/jwt/jwt-secret.yaml

    # Deploy Bank of Anthos with platform specification for M1 Mac
    print_status "Starting Bank of Anthos deployment (this may take a few minutes)..."
    skaffold dev --profile=development --port-forward --platform=linux/amd64 &
    BANK_SKAFFOLD_PID=$!

    # Wait for Bank of Anthos to be ready
    print_status "Waiting for Bank of Anthos services to be ready..."
    sleep 60

    # Check if services are running
    local retries=0
    while [ $retries -lt 30 ]; do
        if kubectl get pods -l app=frontend | grep -q "Running"; then
            print_success "Bank of Anthos is ready"
            break
        fi
        print_status "Waiting for Bank of Anthos... (attempt $((retries + 1))/30)"
        sleep 10
        retries=$((retries + 1))
    done

    if [ $retries -eq 30 ]; then
        print_error "Bank of Anthos failed to start properly"
        print_status "Checking pod status:"
        kubectl get pods
        exit 1
    fi

    # Return to fraud detection directory
    cd fraud-detection-system
}

deploy_fraud_detection() {
    print_status "Deploying Fraud Detection System..."

    # Ensure we're in the right directory
    if [ ! -f "skaffold.yaml" ]; then
        print_error "skaffold.yaml not found. Make sure you're in the fraud-detection-system directory"
        exit 1
    fi

    if [ "$DEPLOY_MODE" = "gke" ]; then
        print_status "Deploying to GKE..."
        skaffold run --profile=development --platform=linux/amd64
    else
        print_status "Deploying locally with Skaffold..."
        print_status "Building and deploying fraud detection services..."

        # Use development profile with platform specification for M1 Mac
        skaffold dev --profile=development --port-forward --platform=linux/amd64 &
        FRAUD_SKAFFOLD_PID=$!

        # Wait for services to be ready
        print_status "Waiting for fraud detection services to be ready..."
        sleep 30

        # Check if fraud detection services are running
        local retries=0
        while [ $retries -lt 20 ]; do
            if kubectl get pods -n fraud-detection -l app=fraud-api | grep -q "Running"; then
                print_success "Fraud Detection System deployed successfully"
                break
            fi
            print_status "Waiting for fraud detection services... (attempt $((retries + 1))/20)"
            sleep 10
            retries=$((retries + 1))
        done

        if [ $retries -eq 20 ]; then
            print_warning "Fraud detection services taking longer than expected to start"
            print_status "Current pod status:"
            kubectl get pods -n fraud-detection
        fi

        print_success "Fraud Detection System deployed locally"
        print_status "Services will be available at:"
        echo "  - Fraud Dashboard: http://localhost:8501"
        echo "  - Fraud API: http://localhost:8000"
        echo "  - API Documentation: http://localhost:8000/docs"
        echo ""
        print_status "Press Ctrl+C to stop the deployment"

        # Wait for Skaffold to be interrupted
        wait $FRAUD_SKAFFOLD_PID
    fi
}

run_tests() {
    print_status "Running system tests..."
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check if fraud API is responding
    if curl -f http://localhost:8000/health &> /dev/null; then
        print_success "Fraud API is responding"
        
        # Run tests if available
        if [ -f "tests/test_fraud_detection.py" ]; then
            print_status "Running fraud detection tests..."
            cd tests
            python -m pip install httpx pytest asyncio &> /dev/null
            python test_fraud_detection.py
            cd ..
        fi
    else
        print_warning "Fraud API not responding yet. Tests skipped."
    fi
}

run_demo() {
    print_status "Running demo scenarios..."
    
    if [ -f "demo/transaction_generator.py" ]; then
        cd demo
        python -m pip install httpx asyncio &> /dev/null
        python transaction_generator.py
        cd ..
        
        print_success "Demo scenarios completed!"
        print_status "Check the dashboard at http://localhost:8501 for results"
    else
        print_warning "Demo script not found. Skipping demo."
    fi
}

cleanup() {
    print_status "Cleaning up..."
    
    # Kill skaffold if running
    if [ -n "$SKAFFOLD_PID" ]; then
        kill $SKAFFOLD_PID 2>/dev/null || true
    fi
    
    # Delete fraud detection namespace
    kubectl delete namespace fraud-detection --ignore-not-found=true
    
    print_success "Cleanup completed"
}

show_help() {
    echo "Fraud Detection System Deployment Script"
    echo ""
    echo "Usage: $0 [OPTIONS] [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy    Deploy the fraud detection system (default)"
    echo "  test      Run system tests"
    echo "  demo      Run demo scenarios"
    echo "  cleanup   Clean up deployed resources"
    echo "  help      Show this help message"
    echo ""
    echo "Options:"
    echo "  --gke     Deploy to GKE instead of local"
    echo ""
    echo "Environment Variables:"
    echo "  GEMINI_API_KEY    Your Gemini API key (required)"
    echo "  DEPLOY_MODE       'local' or 'gke' (default: local)"
    echo ""
    echo "Examples:"
    echo "  GEMINI_API_KEY=your-key ./deploy.sh"
    echo "  ./deploy.sh --gke"
    echo "  ./deploy.sh test"
    echo "  ./deploy.sh demo"
    echo "  ./deploy.sh cleanup"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --gke)
            DEPLOY_MODE="gke"
            shift
            ;;
        deploy)
            COMMAND="deploy"
            shift
            ;;
        test)
            COMMAND="test"
            shift
            ;;
        demo)
            COMMAND="demo"
            shift
            ;;
        cleanup)
            COMMAND="cleanup"
            shift
            ;;
        help|--help|-h)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Default command
COMMAND=${COMMAND:-"deploy"}

# Main execution
case $COMMAND in
    deploy)
        check_prerequisites
        setup_gemini_api_key
        deploy_bank_of_anthos
        deploy_fraud_detection
        
        if [ "$DEPLOY_MODE" = "local" ]; then
            sleep 10
            run_tests
            run_demo
        fi
        ;;
    test)
        run_tests
        ;;
    demo)
        run_demo
        ;;
    cleanup)
        cleanup
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        show_help
        exit 1
        ;;
esac

print_success "Script completed successfully!"
