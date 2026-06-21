# src/agent/nodes.py
"""
LangGraph nodes for the AI Employee Agent workflow.

Each node represents a distinct step in the agent's process. Nodes take the
current AgentState, perform a specific task (calling an LLM chain, interacting
with tools, or saving to the database), and return the updated AgentState.
"""

import traceback

from src.agent.state import AgentState
from src.agent.llm import llm
from src.agent.prompts import (
    EMAIL_CLASSIFICATION_PROMPT,
    SENDER_ENRICHMENT_PROMPT,
    DRAFT_REPLY_PROMPT,
)
from src.tools.gmail_tools import fetch_unread_emails
from src.tools.slack_tools import send_slack_alert
from src.security.pii import pii_redactor
from src.security.injection import detect_and_sanitize
from src.security.rate_limit import rate_limiter, RateLimitError
from src.security.audit import log_event
from src.observability.metrics import emails_processed, gemini_calls, pii_detections
from src.observability.cost_tracker import CostTrackingCallbackHandler
from src.db.database import SessionLocal
from src.db.models import Contact, EmailLog


def fetch_emails_node(state: AgentState) -> AgentState:
    """Fetch unread emails using the Gmail tool."""
    try:
        # fetch_unread_emails is a LangChain @tool, so we use .invoke()
        emails = fetch_unread_emails.invoke({"max_results": 10})
        state["emails"] = emails
        if emails and not state.get("current_email"):
            state["current_email"] = emails[0]
            
        if "errors" not in state:
            state["errors"] = []
    except Exception as e:
        state.setdefault("errors", []).append(f"fetch_emails_node error: {e}\n{traceback.format_exc()}")
    return state


def classify_node(state: AgentState) -> AgentState:
    """Run the EmailClassification chain on the current email."""
    try:
        email = state.get("current_email")
        if not email:
            return state

        prompt, parser = EMAIL_CLASSIFICATION_PROMPT
        chain = prompt | llm | parser

        body_text = email.get("body") or email.get("snippet", "")
        subject_text = email.get("subject", "")
        full_text = f"Subject: {subject_text}\n\n{body_text}"
        
        # Security: Prompt Injection Detection
        sanitized_text = detect_and_sanitize(full_text, email.get("from", "unknown"))
        
        # Security: PII Redaction
        redacted_body, found_entities = pii_redactor.redact(sanitized_text)
        if found_entities:
            log_event("pii_detected", None, None, f"Found {len(found_entities)} PII entities in email {email.get('id')}")
            for entity in found_entities:
                pii_detections.labels(entity_type=entity['entity_type']).inc()
                
        # Security: Gemini Rate Limiting
        if not rate_limiter.check_and_increment("gemini:global", 15, 60):
            log_event("rate_limited", None, None, "Gemini global limit exceeded during classify")
            raise RateLimitError("Gemini global rate limit exceeded (15 calls per minute).")
                
        log_event("gemini_call", None, None, f"Classify node calling Gemini for {email.get('id')}")
        gemini_calls.labels(node_name="classify", agent_id="default").inc()
        
        # Inject cost tracking callback
        cb = CostTrackingCallbackHandler(node_name="classify", email_id=email.get('id', 'unknown'))
        result = chain.invoke({"email_body": redacted_body}, config={"callbacks": [cb]})
        
        state["classification"] = result
    except Exception as e:
        state.setdefault("errors", []).append(f"classify_node error: {e}\n{traceback.format_exc()}")
    return state


def draft_node(state: AgentState) -> AgentState:
    """Generate a draft reply if the classification action is 'reply'."""
    try:
        classification = state.get("classification")
        email = state.get("current_email")

        if classification and classification.action.value == "reply" and email:
            prompt, parser = DRAFT_REPLY_PROMPT
            chain = prompt | llm | parser

            body_text = email.get("body") or email.get("snippet", "")
            subject_text = email.get("subject", "")
            full_text = f"Subject: {subject_text}\n\n{body_text}"
            
            # Security: Prompt Injection Detection
            sanitized_text = detect_and_sanitize(full_text, email.get("from", "unknown"))
            
            # Security: PII Redaction
            redacted_body, found_entities = pii_redactor.redact(sanitized_text)
            if found_entities:
                log_event("pii_detected", None, None, f"Found {len(found_entities)} PII entities in email {email.get('id')} during draft")
                for entity in found_entities:
                    pii_detections.labels(entity_type=entity['entity_type']).inc()
                    
            tone = classification.suggestedReplyTone.value
            
            # Security: Gemini Rate Limiting
            if not rate_limiter.check_and_increment("gemini:global", 15, 60):
                log_event("rate_limited", None, None, "Gemini global limit exceeded during draft")
                raise RateLimitError("Gemini global rate limit exceeded (15 calls per minute).")
            
            log_event("gemini_call", None, None, f"Draft node calling Gemini for {email.get('id')}")
            gemini_calls.labels(node_name="draft", agent_id="default").inc()
            
            # Inject cost tracking callback
            cb = CostTrackingCallbackHandler(node_name="draft", email_id=email.get('id', 'unknown'))
            result = chain.invoke({"email_body": redacted_body, "tone": tone}, config={"callbacks": [cb]})
            
            state["draft_reply"] = result.reply
    except Exception as e:
        state.setdefault("errors", []).append(f"draft_node error: {e}\n{traceback.format_exc()}")
    return state


def enrich_node(state: AgentState) -> AgentState:
    """Run the SenderEnrichment chain on the current email."""
    try:
        email = state.get("current_email")
        if not email:
            return state

        prompt, parser = SENDER_ENRICHMENT_PROMPT
        chain = prompt | llm | parser

        body_text = email.get("body") or email.get("snippet", "")
        subject_text = email.get("subject", "")
        full_text = f"Subject: {subject_text}\n\n{body_text}"
        
        # Security: Prompt Injection Detection
        sanitized_text = detect_and_sanitize(full_text, email.get("from", "unknown"))
        
        # Security: PII Redaction
        redacted_body, found_entities = pii_redactor.redact(sanitized_text)
        if found_entities:
            log_event("pii_detected", None, None, f"Found {len(found_entities)} PII entities in email {email.get('id')} during enrich")
            for entity in found_entities:
                pii_detections.labels(entity_type=entity['entity_type']).inc()
                
        # Security: Gemini Rate Limiting
        if not rate_limiter.check_and_increment("gemini:global", 15, 60):
            log_event("rate_limited", None, None, "Gemini global limit exceeded during enrich")
            raise RateLimitError("Gemini global rate limit exceeded (15 calls per minute).")
                
        log_event("gemini_call", None, None, f"Enrich node calling Gemini for {email.get('id')}")
        gemini_calls.labels(node_name="enrich", agent_id="default").inc()
        
        # Inject cost tracking callback
        cb = CostTrackingCallbackHandler(node_name="enrich", email_id=email.get('id', 'unknown'))
        result = chain.invoke({"email_body": redacted_body}, config={"callbacks": [cb]})
        
        state["enrichment"] = result
        
        # Determine if we should trigger a Slack alert
        classification = state.get("classification")
        is_lead = result.isLead if result else False
        priority = classification.priority.value if classification else "low"
        if is_lead or priority == "high":
            state["should_alert"] = True
        else:
            state["should_alert"] = False
    except Exception as e:
        state.setdefault("errors", []).append(f"enrich_node error: {e}\n{traceback.format_exc()}")
    return state


def crm_node(state: AgentState) -> AgentState:
    """Upsert the sender details into the Contact (CRM) table in PostgreSQL."""
    try:
        enrichment = state.get("enrichment")
        email = state.get("current_email")

        if enrichment and email:
            sender_email = email.get("from", "unknown@example.com")
            
            with SessionLocal() as db:
                contact = db.query(Contact).filter(Contact.email == sender_email).first()
                if not contact:
                    contact = Contact(email=sender_email)
                    db.add(contact)

                contact.name = enrichment.name
                contact.company = enrichment.company
                contact.role = enrichment.role
                contact.intent = enrichment.intent
                contact.is_lead = enrichment.isLead
                contact.urgency = enrichment.urgency.value if enrichment.urgency else None

                db.commit()
                db.refresh(contact)
                state["contact_id"] = contact.id
    except Exception as e:
        state.setdefault("errors", []).append(f"crm_node error: {e}\n{traceback.format_exc()}")
    return state


def alert_node(state: AgentState) -> AgentState:
    """Trigger a Slack alert if the should_alert flag is set."""
    try:
        if state.get("should_alert"):
            email = state.get("current_email", {})
            classification = state.get("classification")
            enrichment = state.get("enrichment")

            sender = email.get("from", "Unknown")
            subject = email.get("subject", "No Subject")
            priority = classification.priority.value if classification else "low"
            is_lead = enrichment.isLead if enrichment else False

            title = "🚨 High Priority Email" if priority == "high" else "👤 New Lead Detected"
            message = f"*From:* {sender}\n*Subject:* {subject}\n*Priority:* {priority}\n*Is Lead:* {is_lead}"

            send_slack_alert.invoke({
                "channel": "#ai-employee-agent-alerts",
                "title": title,
                "message": message,
                "priority": priority
            })
            log_event("slack_sent", None, None, f"Sent alert to #alerts for {sender}: {title}")
    except Exception as e:
        state.setdefault("errors", []).append(f"alert_node error: {e}\n{traceback.format_exc()}")
    return state


def save_node(state: AgentState) -> AgentState:
    """Write the processed email details to the EmailLog PostgreSQL table."""
    try:
        email = state.get("current_email")
        if not email:
            return state

        classification = state.get("classification")

        with SessionLocal() as db:
            log = db.query(EmailLog).filter(EmailLog.message_id == email.get("id")).first()
            if not log:
                log = EmailLog(message_id=email.get("id"))
                db.add(log)
            
            log.thread_id = email.get("threadId")
            log.sender_address = email.get("from")
            log.subject = email.get("subject")
            log.body_snippet = email.get("snippet")
            log.classification_action = classification.action.value if classification else None
            log.priority = classification.priority.value if classification else None
            log.category = classification.category.value if classification else None
            log.sentiment = classification.sentiment.value if classification else None
            log.summary = classification.summary if classification else None
            log.draft_reply = state.get("draft_reply")
            log.errors = state.get("errors", [])
            
            db.commit()
            
        log_event("email_processed", None, None, f"Successfully completed pipeline for email {email.get('id')}")

        state["processed_count"] = state.get("processed_count", 0) + 1
        
        # Track pipeline completion in Prometheus
        emails_processed.labels(agent_id="default").inc()
    except Exception as e:
        state.setdefault("errors", []).append(f"save_node error: {e}\n{traceback.format_exc()}")
    return state
