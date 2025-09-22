#!/usr/bin/env python3
"""
Test Gemini API Integration
Verify that the Gemini API key works correctly
"""

import os
import asyncio
import google.generativeai as genai

# Your API key
GEMINI_API_KEY = "GEMINI_KEY"

async def test_gemini_api():
    """Test Gemini API connection and functionality"""
    print("🧪 Testing Gemini API Integration")
    print("=" * 40)
    
    try:
        # Configure API
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        print("✅ API configured successfully")
        
        # Test basic connection
        print("\n🔍 Testing basic API call...")
        response = await asyncio.to_thread(
            model.generate_content, 
            "Hello! Please respond with 'API connection successful' to confirm you're working."
        )
        
        print(f"📝 Response: {response.text}")
        
        # Test fraud analysis prompt
        print("\n🚨 Testing fraud analysis prompt...")
        fraud_prompt = """
        Analyze this banking transaction for fraud risk:
        - Amount: $2,500.00
        - Time: 3:45 AM
        - Location: Tokyo, Japan (user normally in San Francisco)
        - Merchant: Electronics Store
        
        Provide a fraud risk score (0.0-1.0) and brief explanation.
        Respond in JSON format: {"fraud_score": 0.0, "explanation": "reason"}
        """
        
        fraud_response = await asyncio.to_thread(model.generate_content, fraud_prompt)
        print(f"🔍 Fraud Analysis Response:")
        print(fraud_response.text)
        
        print("\n✅ Gemini API integration test completed successfully!")
        print("🎉 Your fraud detection system will use real AI analysis!")
        
        return True
        
    except Exception as e:
        print(f"❌ Gemini API test failed: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("1. Check your API key is correct")
        print("2. Ensure you have billing enabled in Google Cloud")
        print("3. Verify the Gemini API is enabled in your project")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_gemini_api())
    exit(0 if success else 1)
