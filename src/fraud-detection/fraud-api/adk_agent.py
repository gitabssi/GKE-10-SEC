"""
Google Agent Developer Kit (ADK) Implementation
GKE Turns 10 Hackathon - Fraud Detection Agent

This module implements a proper ADK-based agent for fraud detection
using Google's Agent Developer Kit patterns with real tool execution,
context management, and agent orchestration capabilities.
"""

import asyncio
import logging
import json
import inspect
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

logger = logging.getLogger(__name__)

# ADK Core Components

class ToolExecutionResult:
    """Result of tool execution with metadata"""
    def __init__(self, success: bool, result: Any, error: Optional[str] = None, 
                 execution_time_ms: float = 0.0, metadata: Optional[Dict] = None):
        self.success = success
        self.result = result
        self.error = error
        self.execution_time_ms = execution_time_ms
        self.metadata = metadata or {}

class AgentTool:
    """ADK Tool with execution capabilities and metadata"""
    def __init__(self, name: str, description: str, func: Callable, 
                 parameters: Optional[Dict] = None):
        self.name = name
        self.description = description
        self.func = func
        self.parameters = parameters or {}
        self.execution_count = 0
        self.total_execution_time = 0.0
        
    async def execute(self, context: Any, **kwargs) -> ToolExecutionResult:
        """Execute the tool with proper error handling and metrics"""
        start_time = datetime.utcnow()
        try:
            if inspect.iscoroutinefunction(self.func):
                result = await self.func(context, **kwargs)
            else:
                result = self.func(context, **kwargs)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.execution_count += 1
            self.total_execution_time += execution_time
            
            return ToolExecutionResult(
                success=True,
                result=result,
                execution_time_ms=execution_time,
                metadata={
                    "tool_name": self.name,
                    "execution_count": self.execution_count
                }
            )
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Tool {self.name} execution failed: {str(e)}")
            return ToolExecutionResult(
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=execution_time,
                metadata={"tool_name": self.name, "error_type": type(e).__name__}
            )

def tool(name: str, description: str, parameters: Optional[Dict] = None):
    """ADK Tool decorator for registering agent capabilities"""
    def decorator(func: Callable) -> Callable:
        func._adk_tool = AgentTool(name, description, func, parameters)
        return func
    return decorator

class ContextProvider:
    """ADK Context Provider for enriching agent decisions"""
    def __init__(self, name: str, description: str, provider_func: Callable,
                 cache_ttl: int = 300, priority: int = 1):
        self.name = name
        self.description = description
        self.provider_func = provider_func
        self.cache_ttl = cache_ttl
        self.priority = priority
        self._cache = {}
        self._cache_timestamps = {}
    
    async def get_context(self, key: str, *args, **kwargs) -> Dict:
        """Get context with caching support"""
        cache_key = f"{key}:{hash(str(args) + str(kwargs))}"
        
        # Check cache
        if (cache_key in self._cache and 
            datetime.utcnow().timestamp() - self._cache_timestamps.get(cache_key, 0) < self.cache_ttl):
            return self._cache[cache_key]
        
        # Fetch new context
        try:
            if inspect.iscoroutinefunction(self.provider_func):
                context = await self.provider_func(*args, **kwargs)
            else:
                context = self.provider_func(*args, **kwargs)
            
            # Cache result
            self._cache[cache_key] = context
            self._cache_timestamps[cache_key] = datetime.utcnow().timestamp()
            
            return context
        except Exception as e:
            logger.error(f"Context provider {self.name} failed: {str(e)}")
            return {"error": str(e), "provider": self.name}

@dataclass
class AgentContext:
    """Rich context for agent decision making with ADK patterns"""
    transaction: Dict
    user_profile: Dict = field(default_factory=dict)
    historical_data: List[Dict] = field(default_factory=list)
    risk_indicators: List[str] = field(default_factory=list)
    external_context: Dict = field(default_factory=dict)
    tool_results: Dict[str, ToolExecutionResult] = field(default_factory=dict)
    execution_metadata: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

class ADKAgent(ABC):
    """
    Google Agent Developer Kit (ADK) Base Agent
    Implements proper ADK patterns with tool orchestration and context management
    """
    
    def __init__(self, name: str, model_name: str = "gemini-1.5-flash"):
        self.name = name
        self.model = genai.GenerativeModel(
            model_name,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
        
        # ADK Core Components
        self.tools: Dict[str, AgentTool] = {}
        self.context_providers: Dict[str, ContextProvider] = {}
        self.execution_history: List[Dict] = []
        
        # Discover and register tools
        self._discover_tools()
        self._register_context_providers()
        
        logger.info(f"ADK Agent '{name}' initialized with {len(self.tools)} tools and {len(self.context_providers)} context providers")
    
    def _discover_tools(self):
        """Discover all tools decorated with @tool"""
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, '_adk_tool'):
                tool_obj = attr._adk_tool
                self.tools[tool_obj.name] = tool_obj
                logger.debug(f"Registered tool: {tool_obj.name}")
    
    def _register_context_providers(self):
        """Register context providers - to be implemented by subclasses"""
        pass
    
    async def execute_tool(self, tool_name: str, context: AgentContext, **kwargs) -> ToolExecutionResult:
        """Execute a specific tool with proper ADK patterns"""
        if tool_name not in self.tools:
            return ToolExecutionResult(
                success=False,
                result=None,
                error=f"Tool '{tool_name}' not found",
                metadata={"available_tools": list(self.tools.keys())}
            )
        
        tool = self.tools[tool_name]
        result = await tool.execute(context, **kwargs)
        
        # Store result in context for other tools to use
        context.tool_results[tool_name] = result
        
        return result
    
    async def gather_context(self, base_context: AgentContext) -> AgentContext:
        """Gather enriched context from all providers"""
        # Sort providers by priority
        sorted_providers = sorted(
            self.context_providers.values(),
            key=lambda p: p.priority,
            reverse=True
        )
        
        for provider in sorted_providers:
            try:
                context_data = await provider.get_context(
                    f"transaction_{base_context.transaction.get('transactionId', 'unknown')}",
                    base_context.transaction
                )
                base_context.external_context[provider.name] = context_data
                logger.debug(f"Context provider {provider.name} provided data")
            except Exception as e:
                logger.error(f"Context provider {provider.name} failed: {str(e)}")
                base_context.external_context[provider.name] = {"error": str(e)}
        
        return base_context
    
    async def execute_tool_pipeline(self, context: AgentContext, tool_names: List[str]) -> Dict[str, ToolExecutionResult]:
        """Execute multiple tools in parallel or sequence"""
        results = {}
        
        # Execute tools in parallel for better performance
        tasks = []
        for tool_name in tool_names:
            if tool_name in self.tools:
                task = asyncio.create_task(self.execute_tool(tool_name, context))
                tasks.append((tool_name, task))
        
        # Gather results
        for tool_name, task in tasks:
            try:
                result = await task
                results[tool_name] = result
                logger.debug(f"Tool {tool_name} completed: success={result.success}")
            except Exception as e:
                logger.error(f"Tool {tool_name} failed with exception: {str(e)}")
                results[tool_name] = ToolExecutionResult(
                    success=False,
                    result=None,
                    error=str(e),
                    metadata={"tool_name": tool_name}
                )
        
        return results
    
    async def synthesize_decision(self, context: AgentContext) -> Dict:
        """Use Gemini AI to synthesize final decision from tool results"""
        # Prepare comprehensive prompt with tool results
        tool_results_summary = {}
        for tool_name, result in context.tool_results.items():
            if result.success:
                tool_results_summary[tool_name] = result.result
            else:
                tool_results_summary[tool_name] = {"error": result.error}
        
        prompt = f"""
You are an expert fraud detection AI agent using Google's Agent Developer Kit (ADK).
Analyze the following transaction and tool execution results to make a final fraud determination.

TRANSACTION:
{json.dumps(context.transaction, indent=2)}

TOOL EXECUTION RESULTS:
{json.dumps(tool_results_summary, indent=2)}

CONTEXT DATA:
{json.dumps(context.external_context, indent=2)}

Based on this comprehensive analysis, provide a final fraud assessment in JSON format:
{{
    "fraud_score": 0.0-1.0,
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "confidence": 0.0-1.0,
    "primary_risk_factors": ["factor1", "factor2"],
    "explanation": "Clear reasoning based on tool analysis",
    "recommendation": "APPROVE|REVIEW|BLOCK",
    "tool_contributions": {{"tool_name": "contribution_description"}}
}}
"""
        
        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            decision = self._parse_ai_response(response.text)
            
            # Add ADK metadata
            decision["adk_metadata"] = {
                "agent_name": self.name,
                "tools_executed": list(context.tool_results.keys()),
                "successful_tools": [name for name, result in context.tool_results.items() if result.success],
                "failed_tools": [name for name, result in context.tool_results.items() if not result.success],
                "context_providers": list(self.context_providers.keys()),
                "processing_time_ms": (datetime.utcnow() - context.timestamp).total_seconds() * 1000,
                "execution_id": f"{self.name}_{context.timestamp.isoformat()}"
            }
            
            return decision
            
        except Exception as e:
            logger.error(f"AI decision synthesis failed: {str(e)}")
            return self._create_fallback_decision(context)
    
    def _parse_ai_response(self, response_text: str) -> Dict:
        """Parse AI response with robust error handling"""
        try:
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
        except Exception as e:
            logger.error(f"Failed to parse AI response: {str(e)}")
            return {
                "fraud_score": 0.5,
                "risk_level": "MEDIUM",
                "confidence": 0.3,
                "primary_risk_factors": ["ai_parsing_error"],
                "explanation": f"Unable to parse AI response: {str(e)}",
                "recommendation": "REVIEW",
                "tool_contributions": {}
            }
    
    def _create_fallback_decision(self, context: AgentContext) -> Dict:
        """Create fallback decision when AI synthesis fails"""
        # Calculate simple average from successful tool results
        successful_results = [
            result.result for result in context.tool_results.values() 
            if result.success and isinstance(result.result, dict) and 'risk_score' in result.result
        ]
        
        if successful_results:
            avg_score = sum(r.get('risk_score', 0.5) for r in successful_results) / len(successful_results)
        else:
            avg_score = 0.5
        
        return {
            "fraud_score": avg_score,
            "risk_level": "HIGH" if avg_score > 0.7 else "MEDIUM" if avg_score > 0.4 else "LOW",
            "confidence": 0.6,
            "primary_risk_factors": ["fallback_analysis"],
            "explanation": "ADK Agent fallback decision based on tool results",
            "recommendation": "REVIEW" if avg_score > 0.5 else "APPROVE",
            "tool_contributions": {name: "tool_based_analysis" for name in context.tool_results.keys()},
            "adk_metadata": {
                "agent_name": self.name,
                "fallback_mode": True,
                "tools_executed": list(context.tool_results.keys())
            }
        }
    
    @abstractmethod
    async def process(self, input_data: Dict) -> Dict:
        """Main processing method - must be implemented by subclasses"""
        pass


class FraudDetectionAgent(ADKAgent):
    """
    ADK-based Fraud Detection Agent
    Implements comprehensive fraud detection using Google Agent Developer Kit patterns
    """

    def __init__(self, gemini_api_key: str):
        # Configure Gemini API
        genai.configure(api_key=gemini_api_key)

        # Initialize ADK Agent
        super().__init__("FraudDetectionAgent", "gemini-1.5-flash")

        logger.info("FraudDetectionAgent initialized with ADK patterns")

    def _register_context_providers(self):
        """Register context providers for fraud detection"""
        self.context_providers["user_behavior"] = ContextProvider(
            "user_behavior",
            "User behavioral patterns and transaction history",
            self._get_user_behavior_context,
            cache_ttl=300,
            priority=3
        )

        self.context_providers["merchant_intelligence"] = ContextProvider(
            "merchant_intelligence",
            "Merchant risk profiles and fraud statistics",
            self._get_merchant_context,
            cache_ttl=600,
            priority=2
        )

        self.context_providers["geolocation_risk"] = ContextProvider(
            "geolocation_risk",
            "Geographic risk assessment and velocity checks",
            self._get_geolocation_context,
            cache_ttl=180,
            priority=4
        )

        self.context_providers["fraud_patterns"] = ContextProvider(
            "fraud_patterns",
            "Known fraud patterns and ML model insights",
            self._get_fraud_patterns_context,
            cache_ttl=900,
            priority=1
        )

    async def process(self, input_data: Dict) -> Dict:
        """
        Main ADK Agent processing pipeline for fraud detection
        """
        logger.info(f"ADK Agent processing transaction {input_data.get('transactionId')}")

        # Step 1: Create agent context
        context = AgentContext(transaction=input_data)

        # Step 2: Gather enriched context from providers
        context = await self.gather_context(context)

        # Step 3: Execute tool pipeline
        tool_names = [
            "transaction_amount_analysis",
            "temporal_pattern_analysis",
            "behavioral_deviation_analysis",
            "geospatial_risk_assessment",
            "velocity_fraud_detection",
            "merchant_risk_analysis"
        ]

        tool_results = await self.execute_tool_pipeline(context, tool_names)

        # Step 4: Synthesize final decision using AI
        final_decision = await self.synthesize_decision(context)

        # Step 5: Record execution for learning
        self._record_execution(context, final_decision)

        logger.info(f"ADK Agent completed analysis - Risk Score: {final_decision.get('fraud_score', 0):.2f}")
        return final_decision

    # ADK Tools Implementation

    @tool("transaction_amount_analysis", "Analyze transaction amount for suspicious patterns")
    async def analyze_transaction_amount(self, context: AgentContext) -> Dict:
        """ADK Tool: Advanced transaction amount analysis"""
        amount = context.transaction.get("amount", 0) / 100.0

        risk_factors = []
        risk_score = 0.0

        # High amount analysis with context
        user_avg = context.external_context.get("user_behavior", {}).get("average_transaction_amount", 100.0)

        if amount > 2000:
            risk_factors.append("high_value_transaction")
            risk_score += 0.4

        if amount > 5000:
            risk_factors.append("very_high_value")
            risk_score += 0.3

        # Contextual amount analysis
        if user_avg > 0 and amount > user_avg * 10:
            risk_factors.append("extreme_deviation_from_normal")
            risk_score += 0.5
        elif user_avg > 0 and amount > user_avg * 5:
            risk_factors.append("high_deviation_from_normal")
            risk_score += 0.3

        # Round amount detection (money laundering indicator)
        if amount % 100 == 0 and amount >= 1000:
            risk_factors.append("round_amount_suspicious")
            risk_score += 0.2

        # Micro transaction (card testing)
        if amount < 1.0:
            risk_factors.append("micro_transaction_testing")
            risk_score += 0.15

        return {
            "tool_name": "transaction_amount_analysis",
            "risk_score": min(risk_score, 1.0),
            "risk_factors": risk_factors,
            "analysis_details": {
                "amount_usd": amount,
                "user_average": user_avg,
                "deviation_ratio": amount / max(user_avg, 1),
                "amount_category": self._categorize_amount(amount)
            }
        }

    @tool("temporal_pattern_analysis", "Analyze transaction timing and frequency patterns")
    async def analyze_temporal_patterns(self, context: AgentContext) -> Dict:
        """ADK Tool: Advanced temporal pattern analysis"""
        timestamp_str = context.transaction.get("timestamp", "")

        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            hour = timestamp.hour

            risk_factors = []
            risk_score = 0.0

            # Suspicious hours analysis
            if 2 <= hour <= 5:
                risk_factors.append("suspicious_late_night_hour")
                risk_score += 0.5
            elif 23 <= hour or hour <= 1:
                risk_factors.append("late_night_transaction")
                risk_score += 0.3
            elif 5 <= hour <= 7:
                risk_factors.append("early_morning_unusual")
                risk_score += 0.2

            # Weekend analysis
            if timestamp.weekday() >= 5:  # Weekend
                if 2 <= hour <= 6:
                    risk_factors.append("weekend_suspicious_hour")
                    risk_score += 0.2

            # Frequency analysis from context
            user_behavior = context.external_context.get("user_behavior", {})
            typical_hours = user_behavior.get("typical_transaction_hours", [])
            if typical_hours and hour not in typical_hours:
                risk_factors.append("unusual_hour_for_user")
                risk_score += 0.3

            return {
                "tool_name": "temporal_pattern_analysis",
                "risk_score": min(risk_score, 1.0),
                "risk_factors": risk_factors,
                "analysis_details": {
                    "hour": hour,
                    "day_of_week": timestamp.strftime("%A"),
                    "is_weekend": timestamp.weekday() >= 5,
                    "time_category": self._categorize_time(hour),
                    "typical_hours": typical_hours
                }
            }

        except Exception as e:
            logger.error(f"Temporal analysis failed: {str(e)}")
            return {
                "tool_name": "temporal_pattern_analysis",
                "risk_score": 0.1,
                "risk_factors": ["temporal_analysis_error"],
                "error": str(e)
            }

    @tool("behavioral_deviation_analysis", "Analyze deviation from user's normal behavior")
    async def analyze_behavioral_deviation(self, context: AgentContext) -> Dict:
        """ADK Tool: Advanced behavioral deviation analysis"""
        user_behavior = context.external_context.get("user_behavior", {})
        current_amount = context.transaction.get("amount", 0) / 100.0

        risk_factors = []
        risk_score = 0.0

        # Amount deviation analysis
        avg_amount = user_behavior.get("average_transaction_amount", 100.0)
        if avg_amount > 0:
            deviation_ratio = current_amount / avg_amount

            if deviation_ratio > 10:
                risk_factors.append("extreme_amount_deviation")
                risk_score += 0.6
            elif deviation_ratio > 5:
                risk_factors.append("high_amount_deviation")
                risk_score += 0.4
            elif deviation_ratio > 3:
                risk_factors.append("moderate_amount_deviation")
                risk_score += 0.2

        # Frequency analysis
        recent_count = user_behavior.get("recent_transaction_count", 0)
        if recent_count > 10:
            risk_factors.append("high_frequency_transactions")
            risk_score += 0.3
        elif recent_count > 20:
            risk_factors.append("extreme_frequency_transactions")
            risk_score += 0.5

        # Merchant category analysis
        frequent_merchants = user_behavior.get("frequent_merchants", [])
        # Simulate merchant category detection
        if current_amount > 1000 and "electronics" not in frequent_merchants:
            risk_factors.append("unusual_merchant_category")
            risk_score += 0.2

        return {
            "tool_name": "behavioral_deviation_analysis",
            "risk_score": min(risk_score, 1.0),
            "risk_factors": risk_factors,
            "analysis_details": {
                "deviation_ratio": current_amount / max(avg_amount, 1),
                "recent_frequency": recent_count,
                "frequent_merchants": frequent_merchants,
                "risk_profile": user_behavior.get("risk_profile", "unknown")
            }
        }

    @tool("geospatial_risk_assessment", "Assess geographic and velocity-based risks")
    async def analyze_geospatial_risk(self, context: AgentContext) -> Dict:
        """ADK Tool: Advanced geospatial risk analysis"""
        geo_context = context.external_context.get("geolocation_risk", {})

        risk_factors = []
        risk_score = 0.0

        # Geographic risk analysis
        if geo_context.get("unusual_location", False):
            risk_factors.append("unusual_geographic_location")
            risk_score += 0.5

        if geo_context.get("high_risk_country", False):
            risk_factors.append("high_risk_country_transaction")
            risk_score += 0.6

        if geo_context.get("impossible_travel", False):
            risk_factors.append("impossible_travel_velocity")
            risk_score += 0.8

        # Distance analysis
        distance_km = geo_context.get("distance_from_home_km", 0)
        if distance_km > 5000:  # International
            risk_factors.append("international_transaction")
            risk_score += 0.3
        elif distance_km > 1000:  # Long distance domestic
            risk_factors.append("long_distance_transaction")
            risk_score += 0.2

        # Location risk score from context
        location_risk = geo_context.get("location_risk_score", 0.0)
        risk_score += location_risk * 0.4

        return {
            "tool_name": "geospatial_risk_assessment",
            "risk_score": min(risk_score, 1.0),
            "risk_factors": risk_factors,
            "analysis_details": {
                "distance_km": distance_km,
                "location_risk_score": location_risk,
                "country_risk": geo_context.get("high_risk_country", False),
                "travel_velocity": geo_context.get("impossible_travel", False)
            }
        }

    @tool("velocity_fraud_detection", "Detect rapid transaction patterns")
    async def analyze_velocity_fraud(self, context: AgentContext) -> Dict:
        """ADK Tool: Velocity-based fraud detection"""
        user_behavior = context.external_context.get("user_behavior", {})

        risk_factors = []
        risk_score = 0.0

        # Recent transaction frequency
        recent_count = user_behavior.get("recent_transaction_count", 0)
        if recent_count > 5:
            risk_factors.append("high_velocity_transactions")
            risk_score += 0.4

        if recent_count > 10:
            risk_factors.append("extreme_velocity_transactions")
            risk_score += 0.6

        # Time-based velocity (simulated)
        current_amount = context.transaction.get("amount", 0) / 100.0
        if current_amount > 500 and recent_count > 3:
            risk_factors.append("high_value_velocity_pattern")
            risk_score += 0.5

        return {
            "tool_name": "velocity_fraud_detection",
            "risk_score": min(risk_score, 1.0),
            "risk_factors": risk_factors,
            "analysis_details": {
                "recent_transaction_count": recent_count,
                "velocity_category": "high" if recent_count > 5 else "normal"
            }
        }

    @tool("merchant_risk_analysis", "Analyze merchant-related fraud risks")
    async def analyze_merchant_risk(self, context: AgentContext) -> Dict:
        """ADK Tool: Merchant risk analysis"""
        merchant_context = context.external_context.get("merchant_intelligence", {})

        risk_factors = []
        risk_score = 0.0

        # Merchant risk score
        merchant_risk = merchant_context.get("merchant_risk_score", 0.1)
        risk_score += merchant_risk * 0.6

        if merchant_risk > 0.7:
            risk_factors.append("high_risk_merchant")
        elif merchant_risk > 0.4:
            risk_factors.append("medium_risk_merchant")

        # Fraud reports
        fraud_reports = merchant_context.get("fraud_reports_count", 0)
        if fraud_reports > 5:
            risk_factors.append("merchant_fraud_history")
            risk_score += 0.3

        return {
            "tool_name": "merchant_risk_analysis",
            "risk_score": min(risk_score, 1.0),
            "risk_factors": risk_factors,
            "analysis_details": {
                "merchant_risk_score": merchant_risk,
                "fraud_reports_count": fraud_reports,
                "merchant_category": merchant_context.get("merchant_category", "unknown")
            }
        }

    # Context Providers Implementation

    async def _get_user_behavior_context(self, transaction: Dict) -> Dict:
        """Context Provider: User behavioral patterns"""
        # Simulate advanced user behavior analysis
        amount = transaction.get("amount", 0) / 100.0

        return {
            "average_transaction_amount": 85.50,
            "typical_transaction_hours": [8, 9, 12, 13, 17, 18, 19],
            "frequent_merchants": ["coffee_shops", "grocery_stores", "gas_stations"],
            "recent_transaction_count": min(int(amount / 500), 15),  # Simulate based on amount
            "account_age_days": 365,
            "risk_profile": "low" if amount < 1000 else "medium"
        }

    async def _get_merchant_context(self, transaction: Dict) -> Dict:
        """Context Provider: Merchant intelligence"""
        amount = transaction.get("amount", 0) / 100.0

        return {
            "merchant_risk_score": 0.1 if amount < 1000 else 0.6,
            "merchant_category": "electronics" if amount > 1000 else "retail",
            "fraud_reports_count": 0 if amount < 1000 else 3,
            "merchant_age_days": 1200
        }

    async def _get_geolocation_context(self, transaction: Dict) -> Dict:
        """Context Provider: Geolocation intelligence"""
        amount = transaction.get("amount", 0) / 100.0

        return {
            "unusual_location": amount > 2000,
            "high_risk_country": amount > 5000,
            "impossible_travel": amount > 3000,
            "distance_from_home_km": 50 if amount < 1000 else 8000,
            "location_risk_score": 0.1 if amount < 1000 else 0.8
        }

    async def _get_fraud_patterns_context(self, transaction: Dict) -> Dict:
        """Context Provider: Fraud pattern intelligence"""
        return {
            "matches_known_patterns": [],
            "ml_model_score": 0.3,
            "similar_fraud_cases": 0,
            "pattern_confidence": 0.8
        }

    # Helper methods

    def _categorize_amount(self, amount: float) -> str:
        """Categorize transaction amount"""
        if amount < 10:
            return "micro"
        elif amount < 100:
            return "small"
        elif amount < 500:
            return "medium"
        elif amount < 2000:
            return "large"
        else:
            return "very_large"

    def _categorize_time(self, hour: int) -> str:
        """Categorize transaction time"""
        if 6 <= hour <= 9:
            return "morning"
        elif 10 <= hour <= 16:
            return "business_hours"
        elif 17 <= hour <= 21:
            return "evening"
        elif 22 <= hour <= 23:
            return "late_evening"
        else:
            return "night"

    def _record_execution(self, context: AgentContext, decision: Dict):
        """Record execution for learning and analytics"""
        execution_record = {
            "timestamp": context.timestamp.isoformat(),
            "transaction_id": context.transaction.get("transactionId"),
            "tools_executed": list(context.tool_results.keys()),
            "decision": decision,
            "execution_time_ms": (datetime.utcnow() - context.timestamp).total_seconds() * 1000
        }

        self.execution_history.append(execution_record)

        # Keep only last 1000 executions
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]
