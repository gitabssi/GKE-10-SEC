"""
Transaction Monitor Service
GKE Turns 10 Hackathon 

Monitors Bank of Anthos transactions and sends them to fraud detection service
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
import json

import httpx
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://fraud_user:fraud_pass@fraud-db:5432/fraud_detection")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Configuration
BANK_API_BASE = os.getenv("BANK_API_BASE", "http://frontend:8080")
FRAUD_API_BASE = os.getenv("FRAUD_API_BASE", "http://fraud-api:8000")
DEMO_USERNAME = os.getenv("DEMO_USERNAME", "testuser")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "bankofanthos")
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "5"))  # seconds

class MonitoredTransaction(Base):
    __tablename__ = "monitored_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True)
    account_id = Column(String, index=True)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False)
    fraud_analysis_sent = Column(Boolean, default=False)

class BankAPIClient:
    """Client for interacting with Bank of Anthos APIs"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.jwt_token = None
        self.token_expires_at = None
        
    async def authenticate(self) -> bool:
        """Authenticate with Bank of Anthos and get JWT token"""
        try:
            # Login to get JWT token
            login_url = f"{BANK_API_BASE}/login"
            params = {
                "username": DEMO_USERNAME,
                "password": DEMO_PASSWORD
            }
            
            response = await self.client.get(login_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                self.jwt_token = data.get("token")
                # JWT tokens typically expire in 1 hour, refresh every 45 minutes
                self.token_expires_at = datetime.utcnow() + timedelta(minutes=45)
                logger.info("Successfully authenticated with Bank of Anthos")
                return True
            else:
                logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
    
    async def ensure_authenticated(self) -> bool:
        """Ensure we have a valid JWT token"""
        if not self.jwt_token or (self.token_expires_at and datetime.utcnow() >= self.token_expires_at):
            return await self.authenticate()
        return True
    
    async def get_user_transactions(self, account_id: str, limit: int = 100) -> List[Dict]:
        """Get transactions for a specific account"""
        if not await self.ensure_authenticated():
            return []
            
        try:
            url = f"{BANK_API_BASE}/transactions/{account_id}"
            headers = {"Authorization": f"Bearer {self.jwt_token}"}
            
            response = await self.client.get(url, headers=headers)
            
            if response.status_code == 200:
                transactions = response.json()
                return transactions if isinstance(transactions, list) else []
            else:
                logger.warning(f"Failed to get transactions for {account_id}: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting transactions for {account_id}: {str(e)}")
            return []
    
    async def get_account_balance(self, account_id: str) -> Optional[float]:
        """Get balance for a specific account"""
        if not await self.ensure_authenticated():
            return None
            
        try:
            url = f"{BANK_API_BASE}/balances/{account_id}"
            headers = {"Authorization": f"Bearer {self.jwt_token}"}
            
            response = await self.client.get(url, headers=headers)
            
            if response.status_code == 200:
                balance = response.json()
                return float(balance) / 100.0  # Convert cents to dollars
            else:
                logger.warning(f"Failed to get balance for {account_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting balance for {account_id}: {str(e)}")
            return None

class FraudAPIClient:
    """Client for sending transactions to fraud detection service"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def analyze_transaction(self, transaction: Dict) -> Optional[Dict]:
        """Send transaction to fraud detection service for analysis"""
        try:
            url = f"{FRAUD_API_BASE}/analyze"
            
            # Convert transaction to expected format
            transaction_data = {
                "transactionId": transaction.get("transactionId", 0),
                "fromAccountNum": transaction.get("fromAccountNum", ""),
                "fromRoutingNum": transaction.get("fromRoutingNum", ""),
                "toAccountNum": transaction.get("toAccountNum", ""),
                "toRoutingNum": transaction.get("toRoutingNum", ""),
                "amount": transaction.get("amount", 0),
                "timestamp": transaction.get("timestamp", datetime.utcnow().isoformat())
            }
            
            response = await self.client.post(url, json=transaction_data)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Fraud analysis failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending transaction for fraud analysis: {str(e)}")
            return None

class TransactionMonitor:
    """Main transaction monitoring service"""
    
    def __init__(self):
        self.bank_client = BankAPIClient()
        self.fraud_client = FraudAPIClient()
        self.known_transactions: Set[str] = set()
        self.demo_accounts = [
            "1011226360",  # testuser account
            "1033623433",  # alice account  
            "1055757655",  # bob account
            "1077441377",  # eve account
        ]
        
    async def initialize(self):
        """Initialize the monitor"""
        Base.metadata.create_all(bind=engine)
        
        # Load known transactions from database
        db = SessionLocal()
        try:
            monitored = db.query(MonitoredTransaction).all()
            self.known_transactions = {t.transaction_id for t in monitored}
            logger.info(f"Loaded {len(self.known_transactions)} known transactions")
        finally:
            db.close()
    
    async def discover_new_transactions(self) -> List[Dict]:
        """Discover new transactions from Bank of Anthos"""
        new_transactions = []
        
        for account_id in self.demo_accounts:
            try:
                transactions = await self.bank_client.get_user_transactions(account_id)
                
                for transaction in transactions:
                    transaction_id = str(transaction.get("transactionId", ""))
                    
                    if transaction_id and transaction_id not in self.known_transactions:
                        new_transactions.append(transaction)
                        self.known_transactions.add(transaction_id)
                        
                        # Store in database
                        await self.store_monitored_transaction(transaction_id, account_id)
                        
                        logger.info(f"Discovered new transaction: {transaction_id}")
                        
            except Exception as e:
                logger.error(f"Error discovering transactions for account {account_id}: {str(e)}")
        
        return new_transactions
    
    async def store_monitored_transaction(self, transaction_id: str, account_id: str):
        """Store monitored transaction in database"""
        db = SessionLocal()
        try:
            monitored = MonitoredTransaction(
                transaction_id=transaction_id,
                account_id=account_id
            )
            db.add(monitored)
            db.commit()
        except Exception as e:
            logger.error(f"Error storing monitored transaction: {str(e)}")
            db.rollback()
        finally:
            db.close()
    
    async def process_transaction(self, transaction: Dict):
        """Process a single transaction through fraud detection"""
        transaction_id = str(transaction.get("transactionId", ""))
        
        try:
            # Send to fraud detection service
            analysis_result = await self.fraud_client.analyze_transaction(transaction)
            
            if analysis_result:
                logger.info(f"Transaction {transaction_id} analyzed - Fraud Score: {analysis_result.get('fraud_score', 0)}")
                
                # Mark as processed in database
                await self.mark_transaction_processed(transaction_id, True)
                
                # Log high-risk transactions
                if analysis_result.get("fraud_score", 0) > 0.7:
                    logger.warning(f"HIGH RISK TRANSACTION DETECTED: {transaction_id}")
                    logger.warning(f"Risk Level: {analysis_result.get('risk_level')}")
                    logger.warning(f"Explanation: {analysis_result.get('explanation')}")
            else:
                logger.error(f"Failed to analyze transaction {transaction_id}")
                await self.mark_transaction_processed(transaction_id, False)
                
        except Exception as e:
            logger.error(f"Error processing transaction {transaction_id}: {str(e)}")
    
    async def mark_transaction_processed(self, transaction_id: str, success: bool):
        """Mark transaction as processed in database"""
        db = SessionLocal()
        try:
            monitored = db.query(MonitoredTransaction).filter(
                MonitoredTransaction.transaction_id == transaction_id
            ).first()
            
            if monitored:
                monitored.processed = True
                monitored.fraud_analysis_sent = success
                db.commit()
                
        except Exception as e:
            logger.error(f"Error marking transaction processed: {str(e)}")
            db.rollback()
        finally:
            db.close()
    
    async def run_monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("Starting transaction monitoring loop")
        
        while True:
            try:
                # Discover new transactions
                new_transactions = await self.discover_new_transactions()
                
                # Process each new transaction
                for transaction in new_transactions:
                    await self.process_transaction(transaction)
                
                if new_transactions:
                    logger.info(f"Processed {len(new_transactions)} new transactions")
                
                # Wait before next poll
                await asyncio.sleep(POLLING_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(POLLING_INTERVAL)

async def main():
    """Main entry point"""
    monitor = TransactionMonitor()
    await monitor.initialize()
    
    logger.info("Transaction Monitor starting...")
    await monitor.run_monitoring_loop()

if __name__ == "__main__":
    asyncio.run(main())
