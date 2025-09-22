"""
Fraud Detection System Tests
GKE Turns 10 Hackathon 

Comprehensive tests for fraud detection accuracy and performance
"""

import asyncio
import pytest
import httpx
from datetime import datetime
import json

class TestFraudDetection:
    """Test suite for fraud detection system"""
    
    def __init__(self):
        self.fraud_api_base = "http://localhost:8000"
        self.client = httpx.AsyncClient()
        
    async def test_normal_transaction(self):
        """Test that normal transactions get low fraud scores"""
        transaction = {
            "transactionId": 12345,
            "fromAccountNum": "1011226360",
            "fromRoutingNum": "883745000",
            "toAccountNum": "9999999999",
            "toRoutingNum": "123456789",
            "amount": 450,  # $4.50 coffee
            "timestamp": "2024-03-15T08:30:00Z"
        }
        
        response = await self.client.post(f"{self.fraud_api_base}/analyze", json=transaction)
        assert response.status_code == 200
        
        result = response.json()
        assert result["fraud_score"] < 0.3, f"Normal transaction scored too high: {result['fraud_score']}"
        assert result["risk_level"] in ["LOW", "MEDIUM"]
        assert result["recommendation"] == "APPROVE"
        
        print(f"✅ Normal transaction test passed - Score: {result['fraud_score']:.2f}")
        return result
    
    async def test_high_value_fraud(self):
        """Test high-value suspicious transaction detection"""
        transaction = {
            "transactionId": 12346,
            "fromAccountNum": "1011226360",
            "fromRoutingNum": "883745000",
            "toAccountNum": "8888888888",
            "toRoutingNum": "987654321",
            "amount": 250000,  # $2,500
            "timestamp": "2024-03-15T03:45:00Z"  # 3:45 AM
        }
        
        response = await self.client.post(f"{self.fraud_api_base}/analyze", json=transaction)
        assert response.status_code == 200
        
        result = response.json()
        assert result["fraud_score"] > 0.6, f"High-value fraud scored too low: {result['fraud_score']}"
        assert result["risk_level"] in ["HIGH", "CRITICAL"]
        assert result["recommendation"] in ["REVIEW", "BLOCK"]
        
        print(f"✅ High-value fraud test passed - Score: {result['fraud_score']:.2f}")
        return result
    
    async def test_rapid_transactions(self):
        """Test rapid transaction sequence detection"""
        base_time = datetime.now()
        transactions = []
        
        for i in range(3):
            transaction = {
                "transactionId": 12347 + i,
                "fromAccountNum": "1011226360",
                "fromRoutingNum": "883745000",
                "toAccountNum": "7777777777",
                "toRoutingNum": "555666777",
                "amount": 9999 + (i * 1000),  # $99.99, $109.99, $119.99
                "timestamp": base_time.replace(minute=30 + i).isoformat() + "Z"
            }
            transactions.append(transaction)
        
        results = []
        for transaction in transactions:
            response = await self.client.post(f"{self.fraud_api_base}/analyze", json=transaction)
            assert response.status_code == 200
            results.append(response.json())
        
        # At least one should be flagged as suspicious
        max_score = max(r["fraud_score"] for r in results)
        assert max_score > 0.4, f"Rapid transactions not detected properly: max score {max_score}"
        
        print(f"✅ Rapid transactions test passed - Max Score: {max_score:.2f}")
        return results
    
    async def test_round_amount_suspicious(self):
        """Test round amount suspicious transaction"""
        transaction = {
            "transactionId": 12350,
            "fromAccountNum": "1011226360",
            "fromRoutingNum": "883745000",
            "toAccountNum": "6666666666",
            "toRoutingNum": "111222333",
            "amount": 500000,  # Exactly $5,000
            "timestamp": "2024-03-15T15:00:00Z"  # Exactly 3 PM
        }
        
        response = await self.client.post(f"{self.fraud_api_base}/analyze", json=transaction)
        assert response.status_code == 200
        
        result = response.json()
        assert result["fraud_score"] > 0.3, f"Round amount fraud scored too low: {result['fraud_score']}"
        assert result["risk_level"] in ["MEDIUM", "HIGH"]
        
        print(f"✅ Round amount test passed - Score: {result['fraud_score']:.2f}")
        return result
    
    async def test_api_health(self):
        """Test API health endpoint"""
        response = await self.client.get(f"{self.fraud_api_base}/health")
        assert response.status_code == 200
        
        health = response.json()
        assert health["status"] == "healthy"
        
        print("✅ API health test passed")
        return health
    
    async def test_fraud_stats(self):
        """Test fraud statistics endpoint"""
        response = await self.client.get(f"{self.fraud_api_base}/stats")
        assert response.status_code == 200
        
        stats = response.json()
        assert "total_transactions" in stats
        assert "fraud_transactions" in stats
        assert "fraud_rate" in stats
        assert stats["system_status"] == "operational"
        
        print(f"✅ Stats test passed - {stats['total_transactions']} transactions processed")
        return stats
    
    async def test_performance(self):
        """Test API response time performance"""
        transaction = {
            "transactionId": 99999,
            "fromAccountNum": "1011226360",
            "fromRoutingNum": "883745000",
            "toAccountNum": "9999999999",
            "toRoutingNum": "123456789",
            "amount": 1250,  # $12.50
            "timestamp": datetime.now().isoformat() + "Z"
        }
        
        start_time = datetime.now()
        response = await self.client.post(f"{self.fraud_api_base}/analyze", json=transaction)
        end_time = datetime.now()
        
        response_time = (end_time - start_time).total_seconds() * 1000  # milliseconds
        
        assert response.status_code == 200
        assert response_time < 5000, f"Response time too slow: {response_time}ms"  # Should be < 5 seconds
        
        print(f"✅ Performance test passed - Response time: {response_time:.0f}ms")
        return response_time
    
    async def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🧪 Starting Fraud Detection System Tests")
        print("=" * 50)
        
        test_results = {}
        
        try:
            # Test API health first
            test_results["health"] = await self.test_api_health()
            
            # Test normal transaction
            test_results["normal"] = await self.test_normal_transaction()
            
            # Test fraud scenarios
            test_results["high_value"] = await self.test_high_value_fraud()
            test_results["rapid"] = await self.test_rapid_transactions()
            test_results["round_amount"] = await self.test_round_amount_suspicious()
            
            # Test system endpoints
            test_results["stats"] = await self.test_fraud_stats()
            
            # Test performance
            test_results["performance"] = await self.test_performance()
            
            print("\n🎉 All tests passed!")
            print("=" * 50)
            
            # Summary
            print("\n📊 Test Summary:")
            print(f"Normal Transaction Score: {test_results['normal']['fraud_score']:.2f}")
            print(f"High-Value Fraud Score: {test_results['high_value']['fraud_score']:.2f}")
            print(f"Round Amount Score: {test_results['round_amount']['fraud_score']:.2f}")
            print(f"API Response Time: {test_results['performance']:.0f}ms")
            print(f"Total Transactions: {test_results['stats']['total_transactions']}")
            
            return test_results
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            raise
        
        finally:
            await self.client.aclose()

async def main():
    """Run the test suite"""
    tester = TestFraudDetection()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
