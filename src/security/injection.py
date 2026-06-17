# src/security/injection.py
"""
Prompt Injection Detection and Sanitization.

Scans incoming text for known malicious patterns attempting to hijack
or override the agent's core instructions. Redacts matches and logs
the attempt to the database for auditing.
"""

import re
from src.security.audit import log_event
from src.observability.metrics import injection_attempts

INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"ignore all instructions",
    r"you are now",
    r"disregard your",
    r"forget everything",
    r"new instructions:",
    r"system prompt:",
    r"act as",
    r"jailbreak",
    r"dan mode"
]

# Compile patterns for fast, case-insensitive matching
COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def detect_and_sanitize(text: str, source_email: str) -> str:
    """
    Scans text for prompt injection patterns.
    
    If found, replaces the matched phrase with [REDACTED], logs the
    attempt to the AuditLog table, and returns the sanitized text.
    """
    if not text:
        return text
        
    sanitized_text = text
    detected_patterns = []
    
    for pattern in COMPILED_PATTERNS:
        if pattern.search(sanitized_text):
            detected_patterns.append(pattern.pattern)
            sanitized_text = pattern.sub("[REDACTED]", sanitized_text)
            
    if detected_patterns:
        injection_attempts.inc(len(detected_patterns))
        full_log_text = f"Source: {source_email} | Patterns: {', '.join(detected_patterns)} | Original: {text}"
        log_event("injection_detected", None, None, full_log_text)
            
    return sanitized_text
