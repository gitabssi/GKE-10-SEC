"""
Fraud Detection API Service
GKE Turns 10 Hackathon 

External fraud detection system for Bank of Anthos using Gemini AI
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import google.generativeai as genai
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Float, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import asynccontextmanager

# Import our ADK Agent
from adk_agent import FraudDetectionAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://YOUR_DB_USER:YOUR_DB_PASSWORD@YOUR_DB_HOST:5432/fraud_detection")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Gemini AI setup
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
genai.configure(api_key=GEMINI_API_KEY)

# Verify API key is configured
if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
    logger.warning("Using placeholder Gemini API key - please set GEMINI_API_KEY environment variable")
else:
    logger.info("Gemini API configured successfully")

# Bank of Anthos API configuration
BANK_API_BASE = os.getenv("BANK_API_BASE", "http://frontend:8080")
DEMO_JWT_TOKEN = os.getenv("DEMO_JWT_TOKEN", "")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True)
    from_account = Column(String, index=True)
    to_account = Column(String, index=True)
    amount = Column(Integer)  # Amount in cents
    timestamp = Column(DateTime)
    fraud_score = Column(Float, default=0.0)
    is_fraud = Column(Boolean, default=False)
    analysis_result = Column(Text)
    processed_at = Column(DateTime, default=datetime.utcnow)

class FraudAlert(Base):
    __tablename__ = "fraud_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, index=True)
    alert_type = Column(String)
    risk_level = Column(String)  # LOW, MEDIUM, HIGH, CRITICAL
    confidence = Column(Float)
    explanation = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# Pydantic models
class TransactionData(BaseModel):
    transactionId: int
    fromAccountNum: str
    fromRoutingNum: str
    toAccountNum: str
    toRoutingNum: str
    amount: int
    timestamp: str

class FraudAnalysisResult(BaseModel):
    transaction_id: str
    fraud_score: float
    is_fraud: bool
    risk_level: str
    confidence: float
    explanation: str
    risk_factors: List[str]
    recommendation: str

class FraudDetectionService:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.client = httpx.AsyncClient()
        # Initialize AI Agent
        self.agent = FraudDetectionAgent(GEMINI_API_KEY)
        
    async def analyze_transaction(self, transaction: TransactionData, user_history: List[Dict] = None) -> FraudAnalysisResult:
        """
        Analyze transaction using AI Agent for fraud detection
        """
        try:
            # Convert TransactionData to dict for agent
            transaction_dict = {
                "transactionId": transaction.transactionId,
                "fromAccountNum": transaction.fromAccountNum,
                "fromRoutingNum": transaction.fromRoutingNum,
                "toAccountNum": transaction.toAccountNum,
                "toRoutingNum": transaction.toRoutingNum,
                "amount": transaction.amount,
                "timestamp": transaction.timestamp
            }

            # Use AI Agent for analysis
            analysis = await self.agent.analyze_transaction(transaction_dict, user_history)

            # Convert agent result to FraudAnalysisResult
            return FraudAnalysisResult(
                transaction_id=analysis["transaction_id"],
                fraud_score=analysis["fraud_score"],
                is_fraud=analysis["is_fraud"],
                risk_level=analysis["risk_level"],
                confidence=analysis["confidence"],
                explanation=analysis["explanation"],
                risk_factors=analysis["risk_factors"],
                recommendation=analysis["recommendation"]
            )
            
        except Exception as e:
            logger.error(f"Error analyzing transaction {transaction.transactionId}: {str(e)}")
            # Return safe default analysis
            return FraudAnalysisResult(
                transaction_id=str(transaction.transactionId),
                fraud_score=0.1,
                is_fraud=False,
                risk_level="LOW",
                confidence=0.5,
                explanation="Analysis failed - defaulting to low risk",
                risk_factors=["analysis_error"],
                recommendation="APPROVE - Manual review recommended"
            )
    
    def _prepare_analysis_context(self, transaction: TransactionData, user_history: List[Dict] = None) -> Dict:
        """Prepare context data for AI analysis"""
        amount_dollars = transaction.amount / 100.0
        
        context = {
            "transaction": {
                "amount": amount_dollars,
                "from_account": transaction.fromAccountNum,
                "to_account": transaction.toAccountNum,
                "timestamp": transaction.timestamp,
                "hour_of_day": datetime.fromisoformat(transaction.timestamp.replace('Z', '+00:00')).hour
            },
            "user_history": user_history or [],
            "analysis_time": datetime.utcnow().isoformat()
        }
        
        return context
    
    def _create_fraud_analysis_prompt(self, context: Dict) -> str:
        """Create detailed prompt for Gemini AI fraud analysis"""
        transaction = context["transaction"]
        
        prompt = f"""
You are an expert fraud detection AI analyzing a banking transaction. Provide a detailed fraud risk assessment.

TRANSACTION DETAILS:
- Amount: ${transaction['amount']:.2f}
- From Account: {transaction['from_account']}
- To Account: {transaction['to_account']}
- Time: {transaction['timestamp']} (Hour: {transaction['hour_of_day']})

ANALYSIS REQUIREMENTS:
1. Calculate fraud risk score (0.0 = no risk, 1.0 = definite fraud)
2. Identify specific risk factors
3. Determine risk level (LOW/MEDIUM/HIGH/CRITICAL)
4. Provide confidence level (0.0-1.0)
5. Give clear explanation of reasoning
6. Recommend action (APPROVE/REVIEW/BLOCK)

RISK FACTORS TO CONSIDER:
- Transaction amount (unusual high/low amounts)
- Time of transaction (unusual hours)
- Account patterns (new accounts, suspicious routing)
- Frequency patterns (rapid transactions)

Respond in JSON format:
{{
    "fraud_score": 0.0-1.0,
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "confidence": 0.0-1.0,
    "risk_factors": ["factor1", "factor2"],
    "explanation": "Detailed reasoning",
    "recommendation": "APPROVE|REVIEW|BLOCK"
}}
"""
        return prompt
    
    async def _call_gemini_ai(self, prompt: str) -> str:
        """Call Gemini AI with the analysis prompt"""
        try:
            response = await asyncio.to_thread(
                self.model.generate_content, prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini AI call failed: {str(e)}")
            # Return fallback response
            return json.dumps({
                "fraud_score": 0.1,
                "risk_level": "LOW",
                "confidence": 0.5,
                "risk_factors": ["ai_unavailable"],
                "explanation": "AI analysis unavailable - using fallback assessment",
                "recommendation": "REVIEW"
            })
    
    def _parse_ai_response(self, response: str, transaction_id: int) -> FraudAnalysisResult:
        """Parse Gemini AI response into structured result"""
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            json_str = response[json_start:json_end]
            
            ai_result = json.loads(json_str)
            
            return FraudAnalysisResult(
                transaction_id=str(transaction_id),
                fraud_score=float(ai_result.get("fraud_score", 0.1)),
                is_fraud=ai_result.get("fraud_score", 0.1) > 0.7,
                risk_level=ai_result.get("risk_level", "LOW"),
                confidence=float(ai_result.get("confidence", 0.5)),
                explanation=ai_result.get("explanation", "AI analysis completed"),
                risk_factors=ai_result.get("risk_factors", []),
                recommendation=ai_result.get("recommendation", "APPROVE")
            )
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            # Return safe fallback
            return FraudAnalysisResult(
                transaction_id=str(transaction_id),
                fraud_score=0.2,
                is_fraud=False,
                risk_level="MEDIUM",
                confidence=0.3,
                explanation="Unable to parse AI analysis - manual review recommended",
                risk_factors=["parsing_error"],
                recommendation="REVIEW"
            )

# Initialize services
fraud_service = FraudDetectionService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    logger.info("Fraud Detection API started")
    yield
    # Shutdown
    await fraud_service.client.aclose()
    logger.info("Fraud Detection API stopped")

# FastAPI app
app = FastAPI(
    title="Fraud Detection API",
    description="AI-powered fraud detection for Bank of Anthos",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/analyze", response_model=FraudAnalysisResult)
async def analyze_transaction(transaction: TransactionData):
    """Analyze a transaction for fraud"""
    logger.info(f"Analyzing transaction {transaction.transactionId}")
    
    # Get user transaction history (mock for now)
    user_history = []  # TODO: Implement actual history retrieval
    
    # Perform fraud analysis
    result = await fraud_service.analyze_transaction(transaction, user_history)
    
    # Store results in database
    db = SessionLocal()
    try:
        # Store transaction
        db_transaction = Transaction(
            transaction_id=str(transaction.transactionId),
            from_account=transaction.fromAccountNum,
            to_account=transaction.toAccountNum,
            amount=transaction.amount,
            timestamp=datetime.fromisoformat(transaction.timestamp.replace('Z', '+00:00')),
            fraud_score=result.fraud_score,
            is_fraud=result.is_fraud,
            analysis_result=result.explanation
        )
        db.add(db_transaction)
        
        # Store alert if high risk
        if result.fraud_score > 0.5:
            alert = FraudAlert(
                transaction_id=str(transaction.transactionId),
                alert_type="FRAUD_DETECTION",
                risk_level=result.risk_level,
                confidence=result.confidence,
                explanation=result.explanation
            )
            db.add(alert)
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        db.rollback()
    finally:
        db.close()
    
    return result

@app.get("/alerts")
async def get_recent_alerts(limit: int = 10):
    """Get recent fraud alerts"""
    db = SessionLocal()
    try:
        alerts = db.query(FraudAlert).order_by(FraudAlert.created_at.desc()).limit(limit).all()
        return [
            {
                "id": alert.id,
                "transaction_id": alert.transaction_id,
                "alert_type": alert.alert_type,
                "risk_level": alert.risk_level,
                "confidence": alert.confidence,
                "explanation": alert.explanation,
                "created_at": alert.created_at.isoformat()
            }
            for alert in alerts
        ]
    finally:
        db.close()

@app.get("/stats")
async def get_fraud_stats():
    """Get fraud detection statistics"""
    db = SessionLocal()
    try:
        total_transactions = db.query(Transaction).count()
        fraud_transactions = db.query(Transaction).filter(Transaction.is_fraud == True).count()
        recent_alerts = db.query(FraudAlert).filter(
            FraudAlert.created_at > datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        return {
            "total_transactions": total_transactions,
            "fraud_transactions": fraud_transactions,
            "fraud_rate": fraud_transactions / max(total_transactions, 1) * 100,
            "recent_alerts_24h": recent_alerts,
            "system_status": "operational"
        }
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
