# 🚀 Fraud Detection System - Deployment Guide

## Prerequisites

- Docker Desktop with Kubernetes enabled
- Skaffold installed (`brew install skaffold` on macOS)
- kubectl configured
- Google Cloud SDK (for Gemini API)

## Quick Start (Local Development)

### 1. Deploy Bank of Anthos First

```bash
# In the bank-of-anthos root directory
kubectl apply -f ./extras/jwt/jwt-secret.yaml
skaffold dev
```

Wait for all Bank of Anthos services to be running:
```bash
kubectl get pods
```

### 2. Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Update the secret in `k8s/fraud-api.yaml`:

```bash
# Base64 encode your API key
echo -n "your-actual-gemini-api-key" | base64

# Update the secret in k8s/fraud-api.yaml
# Replace: GEMINI_API_KEY: eW91ci1nZW1pbmktYXBpLWtleQ==
# With:    GEMINI_API_KEY: <your-base64-encoded-key>
```

### 3. Deploy Fraud Detection System

```bash
cd fraud-detection-system
skaffold dev
```

This will:
- Build all Docker images locally
- Deploy to Kubernetes
- Set up port forwarding
- Watch for code changes

### 4. Access the Services

- **Fraud Dashboard**: http://localhost:8501
- **Fraud API**: http://localhost:8000
- **Bank of Anthos**: http://localhost:8080 (from main skaffold)

### 5. Run Demo Scenarios

```bash
# Install demo dependencies
cd demo
pip install httpx asyncio

# Run demo transaction generator
python transaction_generator.py
```

## Production Deployment (GKE)

### 1. Create GKE Cluster

```bash
export PROJECT_ID=your-project-id
export REGION=us-central1

gcloud container clusters create-auto fraud-detection-cluster \
  --project=${PROJECT_ID} \
  --region=${REGION}
```

### 2. Configure Skaffold for GKE

```bash
# Update skaffold.yaml to push to GCR
skaffold config set default-repo gcr.io/${PROJECT_ID}
```

### 3. Deploy to GKE

```bash
# Deploy Bank of Anthos to GKE first
kubectl apply -f ../extras/jwt/jwt-secret.yaml
kubectl apply -f ../kubernetes-manifests

# Deploy fraud detection system
skaffold run
```

### 4. Get External IP

```bash
kubectl get service fraud-dashboard -n fraud-detection
```

## Demo Scenarios

### Scenario 1: Normal Transactions ✅
- Small coffee purchases ($3-12)
- Grocery shopping ($25-150)
- Gas station visits ($30-80)
- **Expected**: Low fraud scores (0.1-0.3)

### Scenario 2: High-Value Fraud 🚨
- Large electronics purchase ($2,500)
- Unusual location (Tokyo, Japan)
- Suspicious time (3:45 AM)
- **Expected**: High fraud score (0.8-0.9)

### Scenario 3: Rapid Transactions 🚨
- Multiple ATM withdrawals
- Within 5-minute window
- Increasing amounts
- **Expected**: Medium-High fraud score (0.6-0.8)

### Scenario 4: Round Amount Suspicious 🚨
- Exact round amounts ($1,000, $5,000)
- Cash advance services
- Exactly on the hour
- **Expected**: Medium fraud score (0.5-0.7)

## Monitoring & Observability

### Health Checks
```bash
# Check fraud API health
curl http://localhost:8000/health

# Check fraud detection stats
curl http://localhost:8000/stats

# Check recent alerts
curl http://localhost:8000/alerts
```

### Logs
```bash
# Fraud API logs
kubectl logs -f deployment/fraud-api -n fraud-detection

# Transaction monitor logs
kubectl logs -f deployment/transaction-monitor -n fraud-detection

# Dashboard logs
kubectl logs -f deployment/fraud-dashboard -n fraud-detection
```

### Database Access
```bash
# Connect to fraud detection database
kubectl port-forward service/fraud-db 5432:5432 -n fraud-detection

# Connect with psql
psql -h localhost -p 5432 -U fraud_user -d fraud_detection
```

## Troubleshooting

### Common Issues

1. **Gemini API Key Issues**
   - Verify API key is correctly base64 encoded
   - Check API key has proper permissions
   - Ensure billing is enabled in Google Cloud

2. **Bank of Anthos Connection Issues**
   - Verify Bank of Anthos is running: `kubectl get pods`
   - Check service names match in ConfigMaps
   - Ensure JWT authentication is working

3. **Database Connection Issues**
   - Check database pod is running: `kubectl get pods -n fraud-detection`
   - Verify connection string in ConfigMaps
   - Check database credentials

4. **Port Forwarding Issues**
   - Kill existing port forwards: `pkill -f "kubectl port-forward"`
   - Restart skaffold: `skaffold dev`

### Reset Everything
```bash
# Delete fraud detection system
kubectl delete namespace fraud-detection

# Redeploy
skaffold dev
```

## Performance Tuning

### Scaling
```bash
# Scale fraud API
kubectl scale deployment fraud-api --replicas=5 -n fraud-detection

# Check HPA status
kubectl get hpa -n fraud-detection
```

### Resource Limits
- Fraud API: 512Mi-1Gi memory, 250m-500m CPU
- Monitor: 256Mi-512Mi memory, 100m-250m CPU
- Dashboard: 256Mi-512Mi memory, 100m-250m CPU
- Database: 256Mi-512Mi memory, 250m-500m CPU

## Security Considerations

1. **API Keys**: Store in Kubernetes secrets, not ConfigMaps
2. **Database**: Use strong passwords, enable SSL
3. **Network**: Use NetworkPolicies to restrict traffic
4. **RBAC**: Implement proper service account permissions
5. **Images**: Scan for vulnerabilities before deployment

## Next Steps

1. **Add Authentication**: Implement proper API authentication
2. **Enhanced Monitoring**: Add Prometheus/Grafana
3. **Machine Learning**: Train custom fraud detection models
4. **Real-time Alerts**: Integrate with Slack/PagerDuty
5. **Data Pipeline**: Add streaming data processing
