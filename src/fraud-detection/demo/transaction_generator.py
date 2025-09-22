"""
Demo Transaction Generator
GKE Turns 10 Hackathon 

Generates realistic transactions including fraud scenarios for demo
"""

import asyncio
import random
import json
from datetime import datetime, timedelta
from typing import List, Dict
import httpx

class TransactionGenerator:
    """Generate realistic transactions for demo purposes"""
    
    def __init__(self):
        self.fraud_api_base = "http://localhost:8000"
        self.client = httpx.AsyncClient()
        
        # Demo accounts
        self.accounts = [
            {"id": "1011226360", "name": "testuser", "location": "San Francisco, CA"},
            {"id": "1033623433", "name": "alice", "location": "New York, NY"},
            {"id": "1055757655", "name": "bob", "location": "Los Angeles, CA"},
            {"id": "1077441377", "name": "eve", "location": "Chicago, IL"},
        ]
        
        # Merchant categories
        self.merchants = {
            "coffee": ["Starbucks", "Blue Bottle", "Peet's Coffee"],
            "grocery": ["Whole Foods", "Safeway", "Trader Joe's"],
            "gas": ["Shell", "Chevron", "BP"],
            "restaurant": ["McDonald's", "Chipotle", "Subway"],
            "electronics": ["Best Buy", "Apple Store", "Amazon"],
            "clothing": ["Target", "Macy's", "H&M"],
            "pharmacy": ["CVS", "Walgreens", "Rite Aid"]
        }
        
        # Normal spending patterns
        self.normal_patterns = {
            "coffee": {"min": 3.50, "max": 12.99, "frequency": 0.3},
            "grocery": {"min": 25.00, "max": 150.00, "frequency": 0.2},
            "gas": {"min": 30.00, "max": 80.00, "frequency": 0.15},
            "restaurant": {"min": 8.00, "max": 45.00, "frequency": 0.25},
            "electronics": {"min": 50.00, "max": 500.00, "frequency": 0.05},
            "clothing": {"min": 20.00, "max": 200.00, "frequency": 0.1},
            "pharmacy": {"min": 5.00, "max": 50.00, "frequency": 0.08}
        }
    
    def generate_normal_transaction(self, account: Dict) -> Dict:
        """Generate a normal, legitimate transaction"""
        # Choose merchant category based on frequency
        category = random.choices(
            list(self.normal_patterns.keys()),
            weights=[p["frequency"] for p in self.normal_patterns.values()]
        )[0]
        
        pattern = self.normal_patterns[category]
        merchant = random.choice(self.merchants[category])
        amount = round(random.uniform(pattern["min"], pattern["max"]), 2)
        
        # Normal business hours (7 AM - 11 PM)
        hour = random.randint(7, 23)
        minute = random.randint(0, 59)
        
        timestamp = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        return {
            "transactionId": random.randint(100000, 999999),
            "fromAccountNum": account["id"],
            "fromRoutingNum": "883745000",
            "toAccountNum": "9999999999",  # Merchant account
            "toRoutingNum": "123456789",
            "amount": int(amount * 100),  # Convert to cents
            "timestamp": timestamp.isoformat() + "Z",
            "merchant": merchant,
            "category": category,
            "location": account["location"]
        }
    
    def generate_fraud_scenario_1(self, account: Dict) -> Dict:
        """High-value transaction from unusual location at suspicious time"""
        # Very high amount
        amount = round(random.uniform(2000.00, 5000.00), 2)
        
        # Suspicious time (2 AM - 5 AM)
        hour = random.randint(2, 5)
        minute = random.randint(0, 59)
        
        # Unusual location
        unusual_locations = ["Tokyo, Japan", "London, UK", "Moscow, Russia", "Lagos, Nigeria"]
        location = random.choice(unusual_locations)
        
        timestamp = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        return {
            "transactionId": random.randint(100000, 999999),
            "fromAccountNum": account["id"],
            "fromRoutingNum": "883745000",
            "toAccountNum": "8888888888",
            "toRoutingNum": "987654321",
            "amount": int(amount * 100),
            "timestamp": timestamp.isoformat() + "Z",
            "merchant": "Electronics Store",
            "category": "electronics",
            "location": location,
            "fraud_type": "high_value_unusual_location"
        }
    
    def generate_fraud_scenario_2(self, account: Dict) -> List[Dict]:
        """Rapid sequence of transactions (card skimming)"""
        transactions = []
        base_time = datetime.now()
        
        # 3-5 rapid transactions within 10 minutes
        num_transactions = random.randint(3, 5)
        
        for i in range(num_transactions):
            amount = round(random.uniform(99.99, 299.99), 2)
            
            # Each transaction 1-3 minutes apart
            time_offset = timedelta(minutes=i * random.randint(1, 3))
            timestamp = base_time + time_offset
            
            transaction = {
                "transactionId": random.randint(100000, 999999),
                "fromAccountNum": account["id"],
                "fromRoutingNum": "883745000",
                "toAccountNum": "7777777777",
                "toRoutingNum": "555666777",
                "amount": int(amount * 100),
                "timestamp": timestamp.isoformat() + "Z",
                "merchant": f"ATM Withdrawal #{i+1}",
                "category": "atm",
                "location": "Unknown Location",
                "fraud_type": "rapid_transactions"
            }
            transactions.append(transaction)
        
        return transactions
    
    def generate_fraud_scenario_3(self, account: Dict) -> Dict:
        """Round number transaction (money laundering pattern)"""
        # Exact round amounts
        round_amounts = [1000.00, 2000.00, 5000.00, 10000.00]
        amount = random.choice(round_amounts)
        
        # Normal business hours but suspicious merchant
        hour = random.randint(9, 17)
        minute = 0  # Exactly on the hour
        
        timestamp = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        return {
            "transactionId": random.randint(100000, 999999),
            "fromAccountNum": account["id"],
            "fromRoutingNum": "883745000",
            "toAccountNum": "6666666666",
            "toRoutingNum": "111222333",
            "amount": int(amount * 100),
            "timestamp": timestamp.isoformat() + "Z",
            "merchant": "Cash Advance Service",
            "category": "financial",
            "location": account["location"],
            "fraud_type": "round_amount_suspicious"
        }
    
    async def send_transaction_for_analysis(self, transaction: Dict):
        """Send transaction to fraud detection API"""
        try:
            url = f"{self.fraud_api_base}/analyze"
            response = await self.client.post(url, json=transaction)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Transaction {transaction['transactionId']} analyzed:")
                print(f"   Fraud Score: {result['fraud_score']:.2f}")
                print(f"   Risk Level: {result['risk_level']}")
                print(f"   Recommendation: {result['recommendation']}")
                if result['fraud_score'] > 0.5:
                    print(f"   🚨 ALERT: {result['explanation']}")
                print()
                return result
            else:
                print(f"❌ Failed to analyze transaction {transaction['transactionId']}")
                return None
                
        except Exception as e:
            print(f"❌ Error analyzing transaction: {str(e)}")
            return None
    
    async def run_demo_scenario(self):
        """Run a comprehensive demo scenario"""
        print("🚀 Starting Fraud Detection Demo")
        print("=" * 50)
        
        # Generate normal transactions
        print("📊 Generating normal transactions...")
        for i in range(5):
            account = random.choice(self.accounts)
            transaction = self.generate_normal_transaction(account)
            await self.send_transaction_for_analysis(transaction)
            await asyncio.sleep(1)
        
        print("\n🚨 Generating fraud scenarios...")
        
        # Scenario 1: High-value unusual location
        print("\n🎯 Scenario 1: High-value transaction from unusual location")
        account = random.choice(self.accounts)
        fraud_tx = self.generate_fraud_scenario_1(account)
        await self.send_transaction_for_analysis(fraud_tx)
        await asyncio.sleep(2)
        
        # Scenario 2: Rapid transactions
        print("\n🎯 Scenario 2: Rapid sequence of transactions")
        account = random.choice(self.accounts)
        rapid_txs = self.generate_fraud_scenario_2(account)
        for tx in rapid_txs:
            await self.send_transaction_for_analysis(tx)
            await asyncio.sleep(0.5)
        
        await asyncio.sleep(2)
        
        # Scenario 3: Round amount suspicious
        print("\n🎯 Scenario 3: Suspicious round amount transaction")
        account = random.choice(self.accounts)
        suspicious_tx = self.generate_fraud_scenario_3(account)
        await self.send_transaction_for_analysis(suspicious_tx)
        
        print("\n✅ Demo scenario completed!")
        print("Check the fraud detection dashboard for results.")

async def main():
    generator = TransactionGenerator()
    await generator.run_demo_scenario()

if __name__ == "__main__":
    asyncio.run(main())
