# src/main.py
"""
FastAPI entrypoint for the AI Employee Agent.

Exposes endpoints for n8n webhooks to trigger the email processing batch loop
and the daily report generation. Protected by API key authentication.
"""

import os
import uuid

from fastapi import FastAPI, Depends, HTTPException, Security, Request
from fastapi.responses import JSONResponse, HTMLResponse, PlainTextResponse
from fastapi.security import APIKeyHeader
from contextlib import asynccontextmanager
from pydantic import BaseModel

from src.agent.graph import agent_graph
from src.agent.report_crew import generate_and_send_daily_report
from src.tools.gmail_tools import mark_email_read
from src.security.rate_limit import rate_limiter
from src.security.audit import log_event
from src.observability.metrics import get_prometheus_metrics, agent_latency
from src.observability.cost_alerter import check_daily_cost
from apscheduler.schedulers.background import BackgroundScheduler
import time

# --- Lifespan & App Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the background cost alerter
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_daily_cost, 'interval', hours=1)
    scheduler.start()
    print("APScheduler started: cost tracking background job active.")
    
    yield
    
    # Shutdown
    scheduler.shutdown()

app = FastAPI(
    title="AI Employee Agent API",
    description="Webhook endpoints for n8n automation",
    version="1.0.0",
    lifespan=lifespan
)

# --- Security ---
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)):
    expected_key = os.getenv("AGENT_API_KEY", "dev-secret-key")
    if not api_key or api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return api_key


# --- Models ---
class TriggerResponse(BaseModel):
    status: str
    processed_count: int
    errors: list[str]


# --- Endpoints ---

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Checks Redis rate limit for /agent/trigger and logs the event."""
    if request.url.path == "/agent/trigger" and request.method == "POST":
        api_key = request.headers.get(API_KEY_NAME)
        ip_address = request.client.host if request.client else "unknown"
        
        # Log the incoming trigger
        log_event("trigger", api_key, ip_address, "n8n Webhook trigger received")
        
        if api_key:
            if not rate_limiter.check_and_increment(f"trigger:{api_key}", 10, 3600):
                log_event("rate_limited", api_key, ip_address, "Trigger endpoint rate limited (10/hr exceeded)")
                return JSONResponse(
                    status_code=429, 
                    content={"detail": "Rate limit exceeded. Max 10 triggers per hour allowed."}
                )
    return await call_next(request)

@app.post("/agent/trigger", response_model=TriggerResponse)
async def trigger_agent(api_key: str = Depends(verify_api_key)):
    """
    Triggered by n8n every 15 minutes.
    Runs the agent graph in a loop until all unread emails in the inbox are processed.
    """
    total_processed = 0
    all_errors = []
    
    # Batch loop: The graph processes one email at a time.
    while True:
        # Unique thread ID per run ensures fresh checkpointer memory for each email
        config = {"configurable": {"thread_id": f"email_{uuid.uuid4()}"}}
        
        # Invoke graph. fetch_emails_node will populate state.
        initial_state = {"processed_count": total_processed, "errors": []}
        
        # Track execution latency
        start_time = time.time()
        result = agent_graph.invoke(initial_state, config=config)
        duration = time.time() - start_time
        agent_latency.labels(agent_id="default").observe(duration)
        
        emails = result.get("emails", [])
        if not emails:
            # Inbox is empty, break the batch loop
            break
            
        current_email = result.get("current_email")
        if current_email:
            # Mark the processed email as read so the next iteration doesn't fetch it again
            try:
                mark_email_read.invoke({"message_id": current_email["id"]})
            except Exception as e:
                all_errors.append(f"Failed to mark email {current_email['id']} read: {e}")
            
            total_processed += 1
            
        # Accumulate any errors from this graph run
        if result.get("errors"):
            all_errors.extend(result["errors"])
            
    return TriggerResponse(
        status="success",
        processed_count=total_processed,
        errors=all_errors
    )


@app.post("/agent/daily-report")
async def daily_report(api_key: str = Depends(verify_api_key)):
    """
    Triggered by n8n at 11 PM daily.
    Executes the CrewAI role-based agents (Phase 3) to generate the daily report.
    """
    try:
        final_report = generate_and_send_daily_report()
        return {
            "status": "success", 
            "message": "Daily report successfully generated and sent to Slack.",
            "report_preview": final_report
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to generate report: {str(e)}"
        }

@app.get("/reports/accuracy", response_class=HTMLResponse)
async def get_accuracy_report(api_key: str = Depends(verify_api_key)):
    """
    Serves the auto-generated HTML accuracy report for clients.
    This report justifies the retainer by proving system reliability.
    """
    report_path = os.path.join("d:/My Porjects/ai employee agent", "reports", "accuracy.html")
    if not os.path.exists(report_path):
        return HTMLResponse(
            content="<h1>Report not found</h1><p>No evaluation run has generated a report yet.</p>", 
            status_code=404
        )
        
    with open(report_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    return HTMLResponse(content=html_content)

@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """
    Prometheus metrics endpoint. 
    Scraped every 15s to populate the Grafana dashboard.
    """
    return get_prometheus_metrics()
