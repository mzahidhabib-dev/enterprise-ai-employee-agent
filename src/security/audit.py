# src/security/audit.py
"""
Enterprise Audit Logging.

Provides a unified helper to log all critical events, security triggers, 
and system actions into the AuditLog table. Ensures compliance by 
never storing plain-text API keys and tracking IPs where available.
"""

import hashlib
from src.db.database import SessionLocal
from src.db.models import AuditLog

def log_event(event_type: str, api_key: str | None, ip: str | None, payload: str):
    """
    Logs an event to the AuditLog table.
    
    - Hashes the API key using SHA-256.
    - Truncates the payload to 200 characters to save space.
    """
    key_hash = hashlib.sha256(api_key.encode('utf-8')).hexdigest() if api_key else None
    payload_summary = payload[:200] if payload else ""
    
    try:
        with SessionLocal() as db:
            log = AuditLog(
                event_type=event_type,
                api_key_hash=key_hash,
                ip_address=ip,
                payload_summary=payload_summary
            )
            db.add(log)
            db.commit()
    except Exception as e:
        # Failsafe so logging errors don't crash the pipeline
        print(f"Failed to write audit log: {e}")
