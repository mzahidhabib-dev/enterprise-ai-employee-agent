# src/observability/cost_alerter.py
"""
Background Cost Alerting Task.

Runs periodically to query the PostgreSQL CostLog table and aggregate
today's total LLM spend. If it exceeds the client's configured threshold,
it broadcasts an urgent alert to the billing Slack channel.
"""

import os
from datetime import date
from sqlalchemy import func

from src.db.database import SessionLocal
from src.db.models import CostLog
from src.tools.slack_tools import send_slack_alert

def check_daily_cost():
    """
    Queries CostLog for today's cost and fires a Slack alert if threshold exceeded.
    """
    threshold_str = os.getenv("COST_ALERT_THRESHOLD_USD", "5.0")
    try:
        threshold = float(threshold_str)
    except ValueError:
        threshold = 5.0
        
    today = date.today()
    
    try:
        with SessionLocal() as db:
            # Efficiently aggregate today's costs at the database level
            # Note: func.date() casts timestamp to date in standard SQL
            total_cost = db.query(func.sum(CostLog.cost_usd)).filter(
                func.date(CostLog.timestamp) == today
            ).scalar()
            
            total_cost = total_cost or 0.0
            
            if total_cost > threshold:
                alert_message = (
                    f"⚠️ *Daily Cost Threshold Exceeded*\n"
                    f"Total Gemini API spend today is *${total_cost:.3f}*, "
                    f"which exceeds the safety limit of *${threshold:.2f}*."
                )
                
                # Broadcast using our existing LangChain slack tool
                send_slack_alert.invoke({
                    "channel": "#ai-agent-biling-alert",
                    "title": "💸 LLM Cost Limit Warning",
                    "message": alert_message,
                    "priority": "high"
                })
                print(f"Cost alert triggered: Spend is ${total_cost:.3f}")
            else:
                print(f"Cost check: ${total_cost:.3f} / ${threshold:.2f} (Safe)")
                
    except Exception as e:
        print(f"Error checking daily cost threshold: {e}")
