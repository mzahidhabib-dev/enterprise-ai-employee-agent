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
    action: ActionEnum = Field(..., description="What the agent should do with the email")
    priority: PriorityEnum = Field(..., description="Urgency level of the email")
    category: CategoryEnum = Field(..., description="Business category of the email")
    sentiment: SentimentEnum = Field(..., description="Overall sentiment of the email content")
    summary: str = Field(..., description="One‑sentence summary of the email")
    suggestedReplyTone: ReplyToneEnum = Field(..., description="Tone for the draft reply")

email_classifier_parser = PydanticOutputParser(pydantic_object=EmailClassification)

EMAIL_CLASSIFICATION_PROMPT = (
    PromptTemplate(
        template="""
You are a helpful assistant that classifies incoming emails. Follow the schema below and output only JSON adhering to it.

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
    reply: str = Field(..., description="Full draft reply to be sent to the email sender")

draft_reply_parser = PydanticOutputParser(pydantic_object=DraftReply)

DRAFT_REPLY_PROMPT = (
    PromptTemplate(
        template="""
Generate a concise reply to the email according to the supplied tone.

{format_instructions}

Email content:
{email_body}

Desired tone: {tone}
""",
        input_variables=["email_body", "tone"],
        partial_variables={"format_instructions": draft_reply_parser.get_format_instructions()},
    ),
    draft_reply_parser,
)

# Export convenient names
__all__ = [
    "EMAIL_CLASSIFICATION_PROMPT",
    "SENDER_ENRICHMENT_PROMPT",
    "DRAFT_REPLY_PROMPT",
]
