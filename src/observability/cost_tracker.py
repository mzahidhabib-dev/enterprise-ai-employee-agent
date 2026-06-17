# src/observability/cost_tracker.py
"""
Cost Per Request Tracker.

Intercepts LangChain executions to extract token usage directly from the
Gemini LLM response metadata. Calculates real-world costs and logs them
to PostgreSQL for client billing dashboards, while also updating Prometheus.
"""

from typing import Any
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from src.db.database import SessionLocal
from src.db.models import CostLog
from src.observability.metrics import gemini_cost

# Gemini 1.5 Flash Pricing (Approximate USD per 1M tokens)
# Refer to Google Cloud pricing for exact up-to-date figures.
INPUT_TOKEN_PRICE_PER_MILLION = 0.35
OUTPUT_TOKEN_PRICE_PER_MILLION = 1.05

def calculate_gemini_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculates the USD cost based on token volume."""
    cost = (input_tokens / 1_000_000) * INPUT_TOKEN_PRICE_PER_MILLION
    cost += (output_tokens / 1_000_000) * OUTPUT_TOKEN_PRICE_PER_MILLION
    return cost

class CostTrackingCallbackHandler(BaseCallbackHandler):
    """
    LangChain Callback Handler that fires when the LLM finishes generating.
    It reads the usage_metadata, calculates the cost, and persists it.
    """
    def __init__(self, node_name: str, email_id: str):
        self.node_name = node_name
        self.email_id = email_id

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        try:
            input_tokens = 0
            output_tokens = 0

            # Safely extract token counts from the underlying AIMessage metadata
            if response.generations and len(response.generations) > 0:
                generation = response.generations[0][0]
                
                # Different models/providers store token usage in different nested metadata objects.
                # For ChatGoogleGenerativeAI, it is usually under message.usage_metadata
                if hasattr(generation, "message") and hasattr(generation.message, "usage_metadata"):
                    usage = generation.message.usage_metadata
                    if usage:
                        input_tokens = usage.get("input_tokens", 0)
                        output_tokens = usage.get("output_tokens", 0)
                
                # Fallback check standard LLM output if missing
                if input_tokens == 0 and response.llm_output:
                    token_usage = response.llm_output.get("token_usage", {})
                    input_tokens = token_usage.get("prompt_tokens", 0)
                    output_tokens = token_usage.get("completion_tokens", 0)

            total_tokens = input_tokens + output_tokens
            
            if total_tokens > 0:
                cost_usd = calculate_gemini_cost(input_tokens, output_tokens)
                
                # 1. Update the live Prometheus Gauge
                gemini_cost.labels(agent_id="default").inc(cost_usd)
                
                # 2. Persist to PostgreSQL for the billing dashboard
                with SessionLocal() as db:
                    log = CostLog(
                        email_id=self.email_id,
                        node_name=self.node_name,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost_usd=cost_usd
                    )
                    db.add(log)
                    db.commit()
                    
        except Exception as e:
            # Failsafe so tracking errors don't crash the main pipeline
            print(f"Cost tracking error in {self.node_name}: {e}")
