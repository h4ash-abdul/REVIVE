from typing import List, Dict, Optional
from datetime import datetime
from uuid import UUID

from src.domain.audit import RecoveryAuditEvent, RecoveryEventType

class AuditLogger:
    """
    Append-only chronological logger that records all steps of the recovery process.
    """
    def __init__(self):
        self._events: List[RecoveryAuditEvent] = []
        
    def log(self, mandate_id: UUID, obligation_id: UUID, event_type: RecoveryEventType, actor: str, current_time: datetime, details: Optional[Dict] = None):
        event = RecoveryAuditEvent(
            timestamp=current_time,
            mandate_id=mandate_id,
            obligation_id=obligation_id,
            event_type=event_type,
            actor=actor,
            details=details or {}
        )
        self._events.append(event)
        
    def get_events(self, mandate_id: Optional[UUID] = None, obligation_id: Optional[UUID] = None) -> List[RecoveryAuditEvent]:
        filtered = self._events
        if mandate_id:
            filtered = [e for e in filtered if e.mandate_id == mandate_id]
        if obligation_id:
            filtered = [e for e in filtered if e.obligation_id == obligation_id]
            
        return sorted(filtered, key=lambda x: x.timestamp)
        
    def get_all(self) -> List[RecoveryAuditEvent]:
        return sorted(self._events, key=lambda x: x.timestamp)
