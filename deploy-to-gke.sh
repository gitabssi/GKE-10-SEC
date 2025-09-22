#!/bin/bash

# Deploy Bank of Anthos + Fraud Detection to GKE
# GKE Turns 10 Hackathon

set -e

echo "🚀 Deploying Bank of Anthos + AI Fraud Detection to GKE"
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

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're connected to the right cluster
CURRENT_CONTEXT=$(kubectl config current-context)
if [[ "$CURRENT_CONTEXT" != *"bank-of-anthos-fraud-detection"* ]]; then
    print_error "Not connected to the right cluster. Current context: $CURRENT_CONTEXT"
    exit 1
fi

print_status "Connected to cluster: $CURRENT_CONTEXT"

# Deploy Bank of Anthos using pre-built images
print_status "Deploying Bank of Anthos with pre-built images..."

# Apply all Bank of Anthos manifests using pre-built images
kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: default
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: accounts-db
spec:
  selector:
    matchLabels:
      app: accounts-db
  template:
    metadata:
      labels:
        app: accounts-db
    spec:
      containers:
      - name: accounts-db
        image: gcr.io/bank-of-anthos-ci/accounts-db:v0.6.7
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          value: "accounts-db"
        - name: POSTGRES_USER
          value: "accounts-admin"
        - name: POSTGRES_PASSWORD
          value: "accounts-pwd"
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "250m"
---
apiVersion: v1
kind: Service
metadata:
  name: accounts-db
spec:
  type: ClusterIP
  selector:
    app: accounts-db
  ports:
  - name: tcp
    port: 5432
    targetPort: 5432
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: userservice
spec:
  selector:
    matchLabels:
      app: userservice
  template:
    metadata:
      labels:
        app: userservice
    spec:
      containers:
      - name: userservice
        image: gcr.io/bank-of-anthos-ci/userservice:v0.6.7
        ports:
        - containerPort: 8080
        env:
        - name: VERSION
          value: "v0.6.7"
        - name: PORT
          value: "8080"
        - name: ACCOUNTS_DB_URI
          value: "postgresql://accounts-admin:accounts-pwd@accounts-db:5432/accounts-db"
        - name: TOKEN_EXPIRY_SECONDS
          value: "3600"
        - name: PRIV_KEY_PATH
          value: "/tmp/.ssh/privatekey"
        volumeMounts:
        - name: keys
          mountPath: "/tmp/.ssh"
          readOnly: true
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "250m"
      volumes:
      - name: keys
        secret:
          secretName: jwt-key
          items:
          - key: jwtRS256.key
            path: privatekey
          - key: jwtRS256.key.pub
            path: publickey
---
apiVersion: v1
kind: Service
metadata:
  name: userservice
spec:
  type: ClusterIP
  selector:
    app: userservice
  ports:
  - name: http
    port: 8080
    targetPort: 8080
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
spec:
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: gcr.io/bank-of-anthos-ci/frontend:v0.6.7
        ports:
        - containerPort: 8080
        env:
        - name: VERSION
          value: "v0.6.7"
        - name: PORT
          value: "8080"
        - name: ACCOUNTS_URI
          value: "http://userservice:8080"
        - name: TRANSACTIONS_URI
          value: "http://transactionhistory:8080"
        - name: BALANCES_URI
          value: "http://balancereader:8080"
        - name: HISTORY_URI
          value: "http://transactionhistory:8080"
        - name: LOGIN_URI
          value: "http://userservice:8080"
        - name: CONTACTS_URI
          value: "http://contacts:8080"
        - name: PUB_KEY_PATH
          value: "/tmp/.ssh/publickey"
        volumeMounts:
        - name: keys
          mountPath: "/tmp/.ssh"
          readOnly: true
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "250m"
      volumes:
      - name: keys
        secret:
          secretName: jwt-key
          items:
          - key: jwtRS256.key.pub
            path: publickey
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
spec:
  type: LoadBalancer
  selector:
    app: frontend
  ports:
  - name: http
    port: 80
    targetPort: 8080
EOF

print_success "Bank of Anthos core services deployed"

# Wait for services to be ready
print_status "Waiting for services to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/accounts-db
kubectl wait --for=condition=available --timeout=300s deployment/userservice
kubectl wait --for=condition=available --timeout=300s deployment/frontend

print_success "Bank of Anthos is ready!"

# Get the external IP for frontend
print_status "Getting external IP for Bank of Anthos frontend..."
FRONTEND_IP=""
for i in {1..30}; do
    FRONTEND_IP=$(kubectl get service frontend -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [ -n "$FRONTEND_IP" ]; then
        break
    fi
    echo "Waiting for external IP... ($i/30)"
    sleep 10
done

if [ -n "$FRONTEND_IP" ]; then
    print_success "Bank of Anthos is accessible at: http://$FRONTEND_IP"
else
    print_error "Could not get external IP for frontend service"
fi

print_success "🎉 Deployment completed!"
echo ""
print_status "📊 Access your services:"
if [ -n "$FRONTEND_IP" ]; then
    echo "  🏦 Bank of Anthos: http://$FRONTEND_IP"
else
    echo "  🏦 Bank of Anthos: Check 'kubectl get service frontend' for external IP"
fi
echo ""
print_status "🔍 Check deployment status:"
echo "  kubectl get pods"
echo "  kubectl get services"
