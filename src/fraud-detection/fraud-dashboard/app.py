"""
Fraud Detection Dashboard
GKE Turns 10 Hackathon 

Real-time dashboard for fraud detection system
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time
from datetime import datetime, timedelta
import json

# Page configuration
st.set_page_config(
    page_title="🚨 Fraud Detection Dashboard",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration
FRAUD_API_BASE = "http://fraud-api:8000"

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ff4b4b;
    }
    .fraud-alert {
        background-color: #ffebee;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #f44336;
        margin: 0.5rem 0;
    }
    .safe-transaction {
        background-color: #e8f5e8;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #4caf50;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

def get_fraud_stats():
    """Get fraud detection statistics"""
    try:
        response = requests.get(f"{FRAUD_API_BASE}/stats", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    
    # Return mock data if API unavailable
    return {
        "total_transactions": 1247,
        "fraud_transactions": 23,
        "fraud_rate": 1.85,
        "recent_alerts_24h": 5,
        "system_status": "operational"
    }

def get_recent_alerts():
    """Get recent fraud alerts"""
    try:
        response = requests.get(f"{FRAUD_API_BASE}/alerts?limit=20", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    
    # Return mock data if API unavailable
    return [
        {
            "id": 1,
            "transaction_id": "12345",
            "alert_type": "FRAUD_DETECTION",
            "risk_level": "HIGH",
            "confidence": 0.89,
            "explanation": "High amount ($2,500) transaction from unusual location (Tokyo) at suspicious time (3:45 AM)",
            "created_at": "2024-03-15T03:45:00"
        },
        {
            "id": 2,
            "transaction_id": "12346",
            "alert_type": "FRAUD_DETECTION", 
            "risk_level": "MEDIUM",
            "confidence": 0.67,
            "explanation": "Rapid sequence of transactions detected within 5-minute window",
            "created_at": "2024-03-15T14:32:00"
        }
    ]

def create_fraud_score_gauge(score):
    """Create a gauge chart for fraud score"""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = score * 100,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Fraud Risk Score"},
        delta = {'reference': 50},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 30], 'color': "lightgreen"},
                {'range': [30, 70], 'color': "yellow"},
                {'range': [70, 100], 'color': "red"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 70
            }
        }
    ))
    fig.update_layout(height=300)
    return fig

def main():
    """Main dashboard"""
    
    # Header
    st.title("🚨 Bank of Anthos Fraud Detection System")
    st.markdown("**GKE Turns 10 Hackathon - AI-Powered Fraud Detection**")
    
    # Sidebar
    st.sidebar.title("🎛️ Controls")
    auto_refresh = st.sidebar.checkbox("Auto Refresh (5s)", value=True)
    show_safe_transactions = st.sidebar.checkbox("Show Safe Transactions", value=False)
    
    # Get data
    stats = get_fraud_stats()
    alerts = get_recent_alerts()
    
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Transactions",
            value=f"{stats['total_transactions']:,}",
            delta=f"+{stats.get('new_transactions_today', 47)} today"
        )
    
    with col2:
        st.metric(
            label="Fraud Detected",
            value=f"{stats['fraud_transactions']:,}",
            delta=f"{stats['fraud_rate']:.1f}% rate",
            delta_color="inverse"
        )
    
    with col3:
        st.metric(
            label="Alerts (24h)",
            value=f"{stats['recent_alerts_24h']:,}",
            delta=f"+{stats.get('new_alerts_today', 2)} today",
            delta_color="inverse"
        )
    
    with col4:
        status_color = "🟢" if stats['system_status'] == 'operational' else "🔴"
        st.metric(
            label="System Status",
            value=f"{status_color} {stats['system_status'].title()}"
        )
    
    st.divider()
    
    # Real-time alerts section
    st.subheader("🚨 Real-Time Fraud Alerts")
    
    if alerts:
        for alert in alerts[:5]:  # Show top 5 alerts
            risk_color = {
                "CRITICAL": "🔴",
                "HIGH": "🟠", 
                "MEDIUM": "🟡",
                "LOW": "🟢"
            }.get(alert['risk_level'], "⚪")
            
            with st.container():
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col1:
                    st.markdown(f"**{risk_color} {alert['risk_level']} RISK**")
                    st.markdown(f"Transaction: `{alert['transaction_id']}`")
                
                with col2:
                    st.markdown(f"**Explanation:** {alert['explanation']}")
                    st.markdown(f"*Confidence: {alert['confidence']*100:.1f}%*")
                
                with col3:
                    alert_time = datetime.fromisoformat(alert['created_at'].replace('Z', '+00:00'))
                    st.markdown(f"**Time:** {alert_time.strftime('%H:%M:%S')}")
                    st.markdown(f"**Date:** {alert_time.strftime('%Y-%m-%d')}")
                
                st.divider()
    else:
        st.info("No recent fraud alerts - system is monitoring transactions")
    
    # Charts section
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Fraud Detection Trends")
        
        # Mock trend data
        dates = pd.date_range(start='2024-03-01', end='2024-03-15', freq='D')
        fraud_counts = [2, 1, 3, 0, 1, 4, 2, 1, 0, 2, 3, 1, 2, 4, 1]
        
        trend_df = pd.DataFrame({
            'Date': dates,
            'Fraud_Alerts': fraud_counts
        })
        
        fig = px.line(trend_df, x='Date', y='Fraud_Alerts', 
                     title='Daily Fraud Alerts',
                     markers=True)
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🎯 Risk Level Distribution")
        
        # Mock risk level data
        risk_data = pd.DataFrame({
            'Risk_Level': ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'],
            'Count': [156, 45, 12, 3],
            'Color': ['green', 'yellow', 'orange', 'red']
        })
        
        fig = px.pie(risk_data, values='Count', names='Risk_Level',
                    title='Transaction Risk Levels (Last 7 Days)',
                    color_discrete_map={
                        'LOW': 'lightgreen',
                        'MEDIUM': 'yellow', 
                        'HIGH': 'orange',
                        'CRITICAL': 'red'
                    })
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Live transaction feed
    st.subheader("📡 Live Transaction Feed")
    
    # Mock live transactions
    live_transactions = [
        {"id": "tx_001", "amount": 45.99, "risk": 0.12, "status": "APPROVED", "time": "14:32:15"},
        {"id": "tx_002", "amount": 2500.00, "risk": 0.89, "status": "BLOCKED", "time": "14:31:45"},
        {"id": "tx_003", "amount": 89.50, "risk": 0.23, "status": "APPROVED", "time": "14:31:20"},
        {"id": "tx_004", "amount": 199.99, "risk": 0.67, "status": "REVIEW", "time": "14:30:55"},
        {"id": "tx_005", "amount": 12.50, "risk": 0.08, "status": "APPROVED", "time": "14:30:30"},
    ]
    
    for tx in live_transactions:
        risk_score = tx['risk']
        status_color = {
            "APPROVED": "🟢",
            "REVIEW": "🟡", 
            "BLOCKED": "🔴"
        }.get(tx['status'], "⚪")
        
        if risk_score < 0.3 and not show_safe_transactions:
            continue
            
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
        
        with col1:
            st.markdown(f"**{tx['id']}**")
        
        with col2:
            st.markdown(f"${tx['amount']:.2f}")
        
        with col3:
            # Risk score with color coding
            if risk_score < 0.3:
                st.markdown(f"🟢 {risk_score:.2f}")
            elif risk_score < 0.7:
                st.markdown(f"🟡 {risk_score:.2f}")
            else:
                st.markdown(f"🔴 {risk_score:.2f}")
        
        with col4:
            st.markdown(f"{status_color} {tx['status']}")
        
        with col5:
            st.markdown(f"{tx['time']}")
    
    # Footer
    st.divider()
    st.markdown("**🏆 GKE Turns 10 Hackathon** - Powered by Gemini AI + GKE")
    
    # Auto refresh
    if auto_refresh:
        time.sleep(5)
        st.rerun()

if __name__ == "__main__":
    main()
