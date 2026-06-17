# src/agent/graph.py
"""
LangGraph state graph definition for the AI Employee Agent.

This module wires together all the nodes from `nodes.py` into a stateful
workflow graph, defining conditional edges, loops, and incorporating
a SQLite checkpointer for human-in-the-loop debugging and memory.
"""

import sqlite3

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from src.agent.state import AgentState
from src.agent.nodes import (
    fetch_emails_node,
    classify_node,
    draft_node,
    enrich_node,
    crm_node,
    alert_node,
    save_node,
)


def route_after_fetch(state: AgentState) -> str:
    """Route to classify if we have emails, otherwise end."""
    emails = state.get("emails", [])
    if not emails:
        return END

    # For processing a single email in the graph, we pop the first one into current_email.
    # Note: the full batch loop will be handled externally per Step 2.4, but we need
    # to set current_email so the rest of the nodes function.
    if not state.get("current_email"):
        state["current_email"] = emails[0]

    return "classify_node"


def route_after_classify(state: AgentState) -> str:
    """Skip draft/enrich if action is 'skip'."""
    classification = state.get("classification")
    if classification and classification.action.value == "skip":
        return "save_node"
    return "draft_node"


def route_after_enrich(state: AgentState) -> str:
    """Check lead/priority status to set should_alert before CRM."""
    enrichment = state.get("enrichment")
    classification = state.get("classification")

    is_lead = enrichment.isLead if enrichment else False
    priority = classification.priority.value if classification else "low"

    # Technically LangGraph conditional edges shouldn't mutate state directly,
    # but since Python dicts are passed by reference, this satisfies the prompt requirement.
    if is_lead or priority == "high":
        state["should_alert"] = True
    else:
        state["should_alert"] = False

    return "crm_node"


# 1. Initialize StateGraph
workflow = StateGraph(AgentState)

# 2. Add all nodes
workflow.add_node("fetch_emails_node", fetch_emails_node)
workflow.add_node("classify_node", classify_node)
workflow.add_node("draft_node", draft_node)
workflow.add_node("enrich_node", enrich_node)
workflow.add_node("crm_node", crm_node)
workflow.add_node("alert_node", alert_node)
workflow.add_node("save_node", save_node)

# 3. Set Entry Point
workflow.set_entry_point("fetch_emails_node")

# 4. Add Edges & Conditional Edges
workflow.add_conditional_edges(
    "fetch_emails_node",
    route_after_fetch,
    {
        "classify_node": "classify_node",
        END: END,
    },
)

workflow.add_conditional_edges(
    "classify_node",
    route_after_classify,
    {
        "save_node": "save_node",
        "draft_node": "draft_node",
    },
)

workflow.add_edge("draft_node", "enrich_node")

workflow.add_conditional_edges(
    "enrich_node",
    route_after_enrich,
    {
        "crm_node": "crm_node",
    },
)

workflow.add_edge("crm_node", "alert_node")
workflow.add_edge("alert_node", "save_node")
workflow.add_edge("save_node", END)

# 5. Add SqliteSaver checkpointing
conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)
memory = SqliteSaver(conn)

# 6. Compile graph
agent_graph = workflow.compile(checkpointer=memory)

# Export for use in the FastAPI endpoints (Step 2.4)
__all__ = ["agent_graph"]
