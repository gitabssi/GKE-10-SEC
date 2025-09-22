# 🚨 Bank of Anthos Fraud Detection System

## 🏆 GKE Turns 10 Hackathon

An intelligent fraud detection system that acts as an external "smart brain" for Bank of Anthos, using AI agents (Gemini + ADK + MCP) to provide real-time fraud analysis with explainable AI reasoning.

## 🎯 Solution Overview

This system monitors Bank of Anthos transactions externally without modifying the core application, providing:

- **Real-time fraud detection** with AI-powered analysis
- **Explainable AI decisions** with clear reasoning
- **External microservice architecture** deployed on GKE
- **Impressive demo capabilities** with live dashboard

## 🏗️ Architecture

```
Bank of Anthos (UNCHANGED) → [Public APIs] → Fraud Detection Brain (NEW GKE Service)
                                                    ↓
                                              Alert Dashboard (NEW)
                                                    ↓
                                            Real-time Notifications
```

### Core Components

1. **Fraud Detection Service** (`fraud-api/`) - Python FastAPI with Gemini AI
2. **AI Agent** (`agent/`) - ADK + MCP integration for intelligent analysis
3. **Transaction Monitor** (`monitor/`) - External API polling system
4. **Demo Dashboard** (`dashboard/`) - React/Streamlit real-time interface
5. **Kubernetes Configs** (`k8s/`) - GKE deployment manifests

## 🚀 Key Features

### AI-Powered Fraud Detection

- **Behavioral Analysis**: Learn user spending patterns
- **Risk Scoring**: Multi-factor fraud indicators
- **Explainable AI**: Clear reasoning for every decision
- **Real-time Processing**: < 100ms analysis time

### Demo Scenarios

- ✅ **Normal Transaction**: Morning coffee purchase
- 🚨 **High-Value Alert**: Unusual large amount + location
- 🚨 **Rapid Spending**: Multiple transactions in short time
- 🚨 **Geographic Anomaly**: Transaction from unusual location

### Technical Excellence

- **Microservices Architecture**: Properly orchestrated on GKE
- **Event-Driven Design**: Real-time processing capabilities
- **Scalable Infrastructure**: Auto-scaling based on load
- **API-First Design**: Clean, documented interfaces

## 📊 Expected Results

- **Fraud Detection Rate**: > 95% accuracy
- **Response Time**: < 100ms analysis
- **False Positive Rate**: < 5%
- **Scalability**: 1000+ transactions/minute

## 🛠️ Technology Stack

- **Backend**: Python FastAPI, SQLAlchemy, PostgreSQL
- **AI/ML**: Google Gemini, Agent Developer Kit (ADK), Model Context Protocol (MCP)
- **Frontend**: React/Streamlit dashboard
- **Infrastructure**: Google Kubernetes Engine (GKE), Skaffold
- **Monitoring**: Cloud Operations, Prometheus

## 🚀 Quick Start

```bash
# Deploy Bank of Anthos first
skaffold dev

# Deploy fraud detection system
cd fraud-detection-system
skaffold dev -f skaffold.yaml
```

## 📁 Project Structure

```
fraud-detection-system/
├── fraud-api/           # Core fraud detection service
├── agent/              # AI agent with ADK + MCP
├── monitor/            # Transaction monitoring
├── dashboard/          # Demo dashboard
├── k8s/               # Kubernetes manifests
├── docker/            # Docker configurations
├── tests/             # Test scenarios
└── docs/              # Documentation
```

## 🎬 Demo Features

- **Live Transaction Stream** with fraud scores
- **Geographic Fraud Heat Map**
- **User Risk Profiles** with behavioral analysis
- **Alert Timeline** with detailed explanations
- **System Performance Metrics**

## 🏅 Hackathon Compliance

✅ **Base Application**: Uses Bank of Anthos (unmodified)  
✅ **External Microservice**: New containerized component on GKE  
✅ **AI Agent Integration**: Gemini + ADK + MCP  
✅ **Container Orchestration**: Full GKE deployment  
✅ **API Integration**: External API consumption only  
✅ **MVP + Demo**: Working prototype with demo video

---

**Built for GKE Turns 10 Hackathon** - Showcasing the power of GKE + AI agents in solving real-world fraud detection challenges.
