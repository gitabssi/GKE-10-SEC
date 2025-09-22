"""
Fraud Detection AI Agent
GKE Turns 10 Hackathon 

AI Agent implementation for intelligent fraud detection using agent patterns
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

import google.generativeai as genai

logger = logging.getLogger(__name__)

@dataclass
class Tool:
    """Represents an agent tool/capability"""
    name: str
    description: str
    function: callable

@dataclass
class AgentContext:
    """Context for agent decision making"""
    transaction: Dict
    user_history: List[Dict]
    risk_factors: List[str]
    external_data: Dict

class FraudDetectionAgent:
    """
    AI Agent for fraud detection using tool-based reasoning
    Simulates ADK (Agent Developer Kit) patterns
    """
    
    def __init__(self, gemini_api_key: str):
        # Configure Gemini API
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

        # Verify API key works
        logger.info(f"Initializing Fraud Detection Agent with Gemini API")
        try:
            # Test API connection
            test_response = self.model.generate_content("Test connection")
            logger.info("Gemini API connection verified successfully")
        except Exception as e:
            logger.error(f"Gemini API connection failed: {str(e)}")
            logger.warning("Agent will use fallback analysis if API calls fail")
        
        # Agent tools (simulating ADK Tool decorator)
        self.tools = [
            Tool("analyze_transaction_amount", "Analyze if transaction amount is suspicious", self._analyze_amount),
            Tool("analyze_transaction_timing", "Analyze if transaction timing is suspicious", self._analyze_timing),
            Tool("analyze_location_risk", "Analyze location-based risk factors", self._analyze_location),
            Tool("analyze_user_behavior", "Analyze user behavioral patterns", self._analyze_behavior),
            Tool("calculate_risk_score", "Calculate overall fraud risk score", self._calculate_risk_score),
            Tool("generate_explanation", "Generate human-readable explanation", self._generate_explanation),
        ]
        
        # MCP-like context data (simulating Model Context Protocol)
        self.context_providers = {
            "user_profiles": self._get_user_profile_context,
            "merchant_data": self._get_merchant_context,
            "location_intelligence": self._get_location_context,
            "fraud_patterns": self._get_fraud_pattern_context,
        }
    
    async def analyze_transaction(self, transaction: Dict, user_history: List[Dict] = None) -> Dict:
        """
        Main agent analysis method - orchestrates all tools
        """
        logger.info(f"Agent analyzing transaction {transaction.get('transactionId')}")
        
        # Build agent context (MCP-like)
        context = await self._build_context(transaction, user_history or [])
        
        # Execute agent reasoning workflow
        analysis_results = {}
        
        # Step 1: Analyze individual risk factors using tools
        for tool in self.tools[:4]:  # First 4 tools are analysis tools
            try:
                result = await tool.function(context)
                analysis_results[tool.name] = result
                logger.debug(f"Tool {tool.name} result: {result}")
            except Exception as e:
                logger.error(f"Tool {tool.name} failed: {str(e)}")
                analysis_results[tool.name] = {"risk_score": 0.1, "factors": ["tool_error"]}
        
        # Step 2: Calculate overall risk score
        risk_calculation = await self._calculate_risk_score(context, analysis_results)
        
        # Step 3: Generate AI explanation
        explanation = await self._generate_explanation(context, analysis_results, risk_calculation)
        
        # Step 4: Make final decision
        final_result = {
            "transaction_id": str(transaction.get("transactionId", "")),
            "fraud_score": risk_calculation["overall_score"],
            "is_fraud": risk_calculation["overall_score"] > 0.7,
            "risk_level": risk_calculation["risk_level"],
            "confidence": risk_calculation["confidence"],
            "explanation": explanation["summary"],
            "risk_factors": explanation["risk_factors"],
            "recommendation": risk_calculation["recommendation"],
            "agent_analysis": {
                "tools_used": [tool.name for tool in self.tools],
                "context_sources": list(self.context_providers.keys()),
                "analysis_details": analysis_results
            }
        }
        
        logger.info(f"Agent analysis complete - Score: {final_result['fraud_score']:.2f}")
        return final_result
    
    async def _build_context(self, transaction: Dict, user_history: List[Dict]) -> AgentContext:
        """Build comprehensive context for agent analysis (MCP-like)"""
        
        # Gather context from all providers
        external_data = {}
        for provider_name, provider_func in self.context_providers.items():
            try:
                data = await provider_func(transaction)
                external_data[provider_name] = data
            except Exception as e:
                logger.warning(f"Context provider {provider_name} failed: {str(e)}")
                external_data[provider_name] = {}
        
        return AgentContext(
            transaction=transaction,
            user_history=user_history,
            risk_factors=[],
            external_data=external_data
        )
    
    # Agent Tools (simulating ADK @Tool decorator)
    
    async def _analyze_amount(self, context: AgentContext) -> Dict:
        """Tool: Analyze transaction amount for suspicious patterns"""
        amount = context.transaction.get("amount", 0) / 100.0  # Convert cents to dollars
        
        risk_factors = []
        risk_score = 0.0
        
        # High amount risk
        if amount > 1000:
            risk_factors.append(f"high_amount_{amount}")
            risk_score += 0.3
        
        if amount > 5000:
            risk_factors.append("very_high_amount")
            risk_score += 0.4
        
        # Round amount risk (money laundering pattern)
        if amount % 100 == 0 and amount >= 1000:
            risk_factors.append("round_amount_suspicious")
            risk_score += 0.2
        
        # Unusual small amounts (card testing)
        if amount < 1.0:
            risk_factors.append("micro_transaction")
            risk_score += 0.1
        
        return {
            "risk_score": min(risk_score, 1.0),
            "factors": risk_factors,
            "amount_analysis": {
                "amount_dollars": amount,
                "category": "high" if amount > 1000 else "medium" if amount > 100 else "low"
            }
        }
    
    async def _analyze_timing(self, context: AgentContext) -> Dict:
        """Tool: Analyze transaction timing patterns"""
        timestamp_str = context.transaction.get("timestamp", "")
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            hour = timestamp.hour
            
            risk_factors = []
            risk_score = 0.0
            
            # Suspicious hours (2 AM - 5 AM)
            if 2 <= hour <= 5:
                risk_factors.append("suspicious_hour_late_night")
                risk_score += 0.4
            
            # Early morning (5 AM - 7 AM)
            elif 5 <= hour <= 7:
                risk_factors.append("early_morning_transaction")
                risk_score += 0.2
            
            # Very late (11 PM - 2 AM)
            elif hour >= 23 or hour <= 2:
                risk_factors.append("late_night_transaction")
                risk_score += 0.3
            
            # Weekend analysis
            if timestamp.weekday() >= 5:  # Saturday = 5, Sunday = 6
                if 2 <= hour <= 6:
                    risk_factors.append("weekend_suspicious_hour")
                    risk_score += 0.2
            
            return {
                "risk_score": min(risk_score, 1.0),
                "factors": risk_factors,
                "timing_analysis": {
                    "hour": hour,
                    "day_of_week": timestamp.strftime("%A"),
                    "is_weekend": timestamp.weekday() >= 5
                }
            }
            
        except Exception as e:
            logger.error(f"Timing analysis failed: {str(e)}")
            return {"risk_score": 0.1, "factors": ["timing_analysis_error"]}
    
    async def _analyze_location(self, context: AgentContext) -> Dict:
        """Tool: Analyze location-based risk factors"""
        # In a real implementation, this would use actual location data
        # For demo, we'll simulate based on account patterns
        
        from_account = context.transaction.get("fromAccountNum", "")
        
        risk_factors = []
        risk_score = 0.0
        
        # Simulate location analysis based on account patterns
        # In real implementation, this would use MCP to get actual location data
        location_data = context.external_data.get("location_intelligence", {})
        
        if location_data.get("unusual_location", False):
            risk_factors.append("unusual_geographic_location")
            risk_score += 0.5
        
        if location_data.get("high_risk_country", False):
            risk_factors.append("high_risk_country")
            risk_score += 0.6
        
        if location_data.get("velocity_check_failed", False):
            risk_factors.append("impossible_travel_velocity")
            risk_score += 0.8
        
        return {
            "risk_score": min(risk_score, 1.0),
            "factors": risk_factors,
            "location_analysis": location_data
        }
    
    async def _analyze_behavior(self, context: AgentContext) -> Dict:
        """Tool: Analyze user behavioral patterns"""
        user_history = context.user_history
        current_amount = context.transaction.get("amount", 0) / 100.0
        
        risk_factors = []
        risk_score = 0.0
        
        if user_history:
            # Calculate average transaction amount
            amounts = [tx.get("amount", 0) / 100.0 for tx in user_history]
            avg_amount = sum(amounts) / len(amounts) if amounts else 0
            
            # Deviation from normal behavior
            if current_amount > avg_amount * 10:
                risk_factors.append("amount_deviation_extreme")
                risk_score += 0.6
            elif current_amount > avg_amount * 5:
                risk_factors.append("amount_deviation_high")
                risk_score += 0.4
            
            # Frequency analysis
            recent_transactions = [tx for tx in user_history 
                                 if self._is_recent_transaction(tx, hours=24)]
            
            if len(recent_transactions) > 10:
                risk_factors.append("high_frequency_24h")
                risk_score += 0.3
        else:
            # No history available
            risk_factors.append("no_transaction_history")
            risk_score += 0.2
        
        return {
            "risk_score": min(risk_score, 1.0),
            "factors": risk_factors,
            "behavior_analysis": {
                "history_available": len(user_history) > 0,
                "recent_transaction_count": len([tx for tx in user_history 
                                               if self._is_recent_transaction(tx, hours=24)])
            }
        }
    
    async def _calculate_risk_score(self, context: AgentContext, analysis_results: Dict) -> Dict:
        """Tool: Calculate overall fraud risk score"""
        
        # Weight different analysis components
        weights = {
            "analyze_transaction_amount": 0.3,
            "analyze_transaction_timing": 0.2,
            "analyze_location_risk": 0.3,
            "analyze_user_behavior": 0.2
        }
        
        # Calculate weighted score
        total_score = 0.0
        total_weight = 0.0
        
        for analysis_name, result in analysis_results.items():
            if analysis_name in weights:
                weight = weights[analysis_name]
                score = result.get("risk_score", 0.0)
                total_score += score * weight
                total_weight += weight
        
        # Normalize score
        overall_score = total_score / total_weight if total_weight > 0 else 0.0
        overall_score = min(max(overall_score, 0.0), 1.0)  # Clamp to [0, 1]
        
        # Determine risk level
        if overall_score >= 0.8:
            risk_level = "CRITICAL"
            recommendation = "BLOCK"
        elif overall_score >= 0.6:
            risk_level = "HIGH"
            recommendation = "REVIEW"
        elif overall_score >= 0.3:
            risk_level = "MEDIUM"
            recommendation = "REVIEW"
        else:
            risk_level = "LOW"
            recommendation = "APPROVE"
        
        # Calculate confidence based on consistency of tool results
        scores = [r.get("risk_score", 0.0) for r in analysis_results.values()]
        if scores:
            score_variance = sum((s - overall_score) ** 2 for s in scores) / len(scores)
            confidence = max(0.5, 1.0 - score_variance)  # Higher consistency = higher confidence
        else:
            confidence = 0.5
        
        return {
            "overall_score": overall_score,
            "risk_level": risk_level,
            "recommendation": recommendation,
            "confidence": confidence,
            "component_scores": {name: result.get("risk_score", 0.0) 
                               for name, result in analysis_results.items()}
        }
    
    async def _generate_explanation(self, context: AgentContext, analysis_results: Dict, risk_calculation: Dict) -> Dict:
        """Tool: Generate human-readable explanation using Gemini AI"""
        
        # Collect all risk factors
        all_risk_factors = []
        for result in analysis_results.values():
            all_risk_factors.extend(result.get("factors", []))
        
        # Create prompt for Gemini
        prompt = f"""
        Generate a clear, professional explanation for a fraud detection decision.
        
        Transaction Details:
        - Amount: ${context.transaction.get('amount', 0) / 100:.2f}
        - Time: {context.transaction.get('timestamp', 'unknown')}
        - Account: {context.transaction.get('fromAccountNum', 'unknown')}
        
        Risk Analysis:
        - Overall Score: {risk_calculation['overall_score']:.2f}
        - Risk Level: {risk_calculation['risk_level']}
        - Risk Factors: {', '.join(all_risk_factors)}
        
        Provide a concise explanation (2-3 sentences) of why this transaction received this risk score.
        Focus on the most significant risk factors.
        """
        
        try:
            # Make real Gemini API call
            logger.debug("Calling Gemini API for fraud explanation")
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            explanation_text = response.text.strip()
            logger.debug(f"Gemini API response received: {len(explanation_text)} characters")
        except Exception as e:
            logger.error(f"Gemini API call failed for explanation: {str(e)}")
            # Provide detailed fallback explanation
            risk_factors_text = ", ".join(all_risk_factors) if all_risk_factors else "multiple indicators"
            explanation_text = f"Transaction flagged with {risk_calculation['risk_level']} risk ({risk_calculation['overall_score']:.2f}) based on {risk_factors_text}. Manual review recommended due to API unavailability."
        
        return {
            "summary": explanation_text,
            "risk_factors": all_risk_factors,
            "detailed_analysis": analysis_results
        }
    
    # Context Providers (simulating MCP)
    
    async def _get_user_profile_context(self, transaction: Dict) -> Dict:
        """MCP-like context provider for user profile data"""
        # Simulate user profile lookup
        return {
            "account_age_days": 365,
            "average_transaction_amount": 75.50,
            "typical_merchants": ["coffee_shops", "grocery_stores", "gas_stations"],
            "risk_profile": "low"
        }
    
    async def _get_merchant_context(self, transaction: Dict) -> Dict:
        """MCP-like context provider for merchant data"""
        return {
            "merchant_risk_score": 0.1,
            "merchant_category": "unknown",
            "fraud_reports": 0
        }
    
    async def _get_location_context(self, transaction: Dict) -> Dict:
        """MCP-like context provider for location intelligence"""
        # Simulate location analysis
        amount = transaction.get("amount", 0) / 100.0
        hour = 12  # Default hour
        
        try:
            timestamp = datetime.fromisoformat(transaction.get("timestamp", "").replace('Z', '+00:00'))
            hour = timestamp.hour
        except:
            pass
        
        return {
            "unusual_location": amount > 2000 and (hour < 6 or hour > 22),
            "high_risk_country": False,
            "velocity_check_failed": False,
            "distance_from_home": 0
        }
    
    async def _get_fraud_pattern_context(self, transaction: Dict) -> Dict:
        """MCP-like context provider for known fraud patterns"""
        return {
            "matches_known_patterns": [],
            "similar_fraud_cases": 0,
            "pattern_confidence": 0.0
        }
    
    def _is_recent_transaction(self, transaction: Dict, hours: int = 24) -> bool:
        """Helper to check if transaction is recent"""
        try:
            tx_time = datetime.fromisoformat(transaction.get("timestamp", "").replace('Z', '+00:00'))
            return (datetime.now() - tx_time).total_seconds() < (hours * 3600)
        except:
            return False
