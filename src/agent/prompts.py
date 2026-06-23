# src/agent/prompts.py
"""Prompt templates and parsers for the AI Employee Agent.
Each task (email classification, sender enrichment, draft reply) has a
LangChain `PromptTemplate` paired with a `PydanticOutputParser` that
validates Gemini's structured output.
All other modules should import the exported tuples:
    from src.agent.prompts import EMAIL_CLASSIFICATION_PROMPT,
                               SENDER_ENRICHMENT_PROMPT,
                               DRAFT_REPLY_PROMPT
"""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# ------------------------------------------------------------
# 1. Email Classification
# ------------------------------------------------------------
class ActionEnum(str, Enum):
    REPLY = "reply"
    FORWARD = "forward"
    SKIP = "skip"
    FLAG = "flag"

class PriorityEnum(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class CategoryEnum(str, Enum):
    CUSTOMER = "customer"
    INTERNAL = "internal"
    SPAM = "spam"
    OTHER = "other"

class SentimentEnum(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"

class ReplyToneEnum(str, Enum):
    FORMAL = "formal"
    FRIENDLY = "friendly"
    CONCISE = "concise"

class EmailClassification(BaseModel):
    """Output schema for the classification node."""
    action: ActionEnum = Field(description="The primary action to take.")
    priority: PriorityEnum = Field(description="Priority of the email.")
    category: CategoryEnum = Field(description="Category of the email.")
    sentiment: SentimentEnum = Field(description="Overall sentiment of the sender.")
    summary: str = Field(description="A concise 1-2 sentence summary of the email.")
    needs_research: bool = Field(description="Set to true if the email asks for factual information, company details, or requires searching the web to formulate a good reply.")
    research_query: Optional[str] = Field(description="If needs_research is true, provide the optimal DuckDuckGo search query to find the answer. Otherwise, leave empty.")

email_classifier_parser = PydanticOutputParser(pydantic_object=EmailClassification)

EMAIL_CLASSIFICATION_PROMPT = (
    PromptTemplate(
        template="""
You are a helpful assistant that classifies incoming emails. Follow the schema below and output only JSON adhering to it.

CRITICAL ROUTING RULES:
- If the email is about a server crash, production being down, or an urgent internal escalation, you MUST classify it as "flag".
- If the email is a vendor proposal, sales pitch, or offering services (e.g., cloud hosting), you MUST classify it as "forward".
- If the email is a customer support request (e.g., password reset), classify as "reply".
- If it is a newsletter requiring no action, classify as "skip".
- If the email mentions specific companies, events, or questions requiring outside facts, set `needs_research` to true and provide a `research_query`.

{format_instructions}

Email content:
{email_body}
""",
        input_variables=["email_body"],
        partial_variables={"format_instructions": email_classifier_parser.get_format_instructions()},
    ),
    email_classifier_parser,
)

# ------------------------------------------------------------
# 2. Sender Enrichment
# ------------------------------------------------------------
class SenderEnrichment(BaseModel):
    name: str = Field(..., description="Full name of the sender")
    company: Optional[str] = Field(None, description="Company name if identifiable")
    role: Optional[str] = Field(None, description="Job title or role of the sender")
    intent: Literal["inquiry", "support", "sales", "other"] = Field(..., description="Primary intent of the sender")
    isLead: bool = Field(..., description="Whether the sender is a potential sales lead")
    urgency: PriorityEnum = Field(..., description="Urgency level based on email content")

sender_enrichment_parser = PydanticOutputParser(pydantic_object=SenderEnrichment)

SENDER_ENRICHMENT_PROMPT = (
    PromptTemplate(
        template="""
Extract structured information about the sender from the email.

{format_instructions}

Email content:
{email_body}
""",
        input_variables=["email_body"],
        partial_variables={"format_instructions": sender_enrichment_parser.get_format_instructions()},
    ),
    sender_enrichment_parser,
)

# ------------------------------------------------------------
# 3. Draft Reply
# ------------------------------------------------------------
class DraftReply(BaseModel):
    """Output schema for the drafting node."""
    reply: str = Field(description="The generated email reply body.")

DRAFT_REPLY_PROMPT = (
    PromptTemplate(
        template="""
You are drafting a professional reply to the following email.
Ensure the tone is {tone}.
If any research context is provided below, incorporate it seamlessly into your response to provide accurate factual details.

<research_context>
{research_context}
</research_context>

Email to reply to:
{email_body}

Respond with only a JSON object adhering to this schema:
{format_instructions}
""",
        input_variables=["email_body", "tone", "research_context"],
        partial_variables={"format_instructions": PydanticOutputParser(pydantic_object=DraftReply).get_format_instructions()}
    ),
    PydanticOutputParser(pydantic_object=DraftReply),
)

# Export convenient names
__all__ = [
    "EMAIL_CLASSIFICATION_PROMPT",
    "SENDER_ENRICHMENT_PROMPT",
    "DRAFT_REPLY_PROMPT",
]
