# src/db/models.py
"""
SQLAlchemy models representing the 5 core tables for the AI Employee Agent:
Agent, EmailLog, Contact (CRM), SlackAlert, DailyReport.
"""

from datetime import datetime
import uuid

from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, Float, Integer
from sqlalchemy.orm import declarative_base

from .database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Agent(Base):
    __tablename__ = "agents"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class EmailLog(Base):
    __tablename__ = "email_logs"
    id = Column(String, primary_key=True, default=generate_uuid)
    message_id = Column(String, unique=True, index=True, nullable=False)
    thread_id = Column(String, index=True)
    sender_address = Column(String, index=True)
    subject = Column(String)
    body_snippet = Column(Text)
    
    # Classification results
    classification_action = Column(String)
    priority = Column(String)
    category = Column(String)
    sentiment = Column(String)
    summary = Column(Text)
    
    # Generated draft
    draft_reply = Column(Text)
    
    # Feedback from dashboard
    feedback_correct = Column(Boolean, nullable=True)
    feedback_notes = Column(Text, nullable=True)
    
    # Execution trace details
    errors = Column(JSON, default=list)
    processed_at = Column(DateTime, default=datetime.utcnow)


class Contact(Base):
    """CRM table to hold enriched sender details."""
    __tablename__ = "contacts"
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    company = Column(String)
    role = Column(String)
    intent = Column(String)
    is_lead = Column(Boolean, default=False)
    urgency = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SlackAlert(Base):
    __tablename__ = "slack_alerts"
    id = Column(String, primary_key=True, default=generate_uuid)
    channel = Column(String, nullable=False)
    title = Column(String)
    message = Column(Text)
    priority = Column(String)
    sent_at = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=True)


class DailyReport(Base):
    __tablename__ = "daily_reports"
    id = Column(String, primary_key=True, default=generate_uuid)
    report_date = Column(DateTime, default=datetime.utcnow)
    metrics_json = Column(JSON, nullable=True) # Output from the Researcher agent
    report_text = Column(Text, nullable=True)  # Output from Writer & Reviewer agents
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    """General audit log for tracing agent operations and security events."""
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=generate_uuid)
    event_type = Column(String) # e.g. pii_detected, injection_detected
    api_key_hash = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    payload_summary = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class EvalResult(Base):
    """Stores the output of the RAGAS evaluation suite."""
    __tablename__ = "eval_results"
    id = Column(String, primary_key=True, default=generate_uuid)
    accuracy_pct = Column(Float)
    faithfulness_score = Column(Float)
    relevancy_score = Column(Float)
    recall_score = Column(Float)
    failed_cases = Column(JSON, default=list) # List of test IDs that failed classification
    created_at = Column(DateTime, default=datetime.utcnow)

class CostLog(Base):
    """Tracks token usage and cost per LLM request for client billing."""
    __tablename__ = "cost_logs"
    id = Column(String, primary_key=True, default=generate_uuid)
    email_id = Column(String)
    node_name = Column(String)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)
