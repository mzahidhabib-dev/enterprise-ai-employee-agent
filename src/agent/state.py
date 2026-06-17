# src/agent/state.py
"""
LangGraph state schema for the AI Employee Agent.

This TypedDict represents the shared memory passed between all nodes
in the LangGraph workflow. Nodes read from and write to this state.
"""

from typing import TypedDict, List, Dict, Optional
from src.agent.prompts import EmailClassification, SenderEnrichment

class AgentState(TypedDict):
    """
    The state structure that flows through the LangGraph nodes.
    """
    # The batch of all unread emails fetched
    emails: List[Dict]
    
    # The single email currently being processed in the loop
    current_email: Optional[Dict]
    
    # Structured LLM output from classification node
    classification: Optional[EmailClassification]
    
    # Generated string reply from draft node (if action == reply)
    draft_reply: Optional[str]
    
    # Structured LLM output from enrichment node
    enrichment: Optional[SenderEnrichment]
    
    # Database ID of the upserted Contact record from CRM node
    contact_id: Optional[str]
    
    # Accumulated error messages for observability
    errors: List[str]
    
    # Total number of emails processed in this batch run
    processed_count: int
    
    # Flag to determine if an alert should be sent via Slack node
    should_alert: bool
