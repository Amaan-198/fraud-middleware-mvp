"""
Session Monitor - Core Session Tracking Logic

Responsible for session lifecycle management and behavioral tracking:
- Create and manage sessions
- Update session metrics
- Detect anomalies
- Manage session termination
- Query and cleanup operations

Designed to integrate with existing fraud detection pipeline.
Uses existing security_storage patterns for database access.
"""

import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from api.models.session_behavior import (
    SessionBehavior,
    SessionEvent,
    SessionStatus,
    AnomalyType,
    create_session_id,
    create_event_id,
    get_session_age_minutes,
    get_session_idle_minutes,
    EVENT_TYPES
)
from api.utils.security_storage import SecurityEventStore

logger = logging.getLogger(__name__)


class SessionMonitor:
    """
    Core session monitoring engine for behavioral biometrics.
    
    Handles all session lifecycle operations and behavioral tracking.
    Uses SecurityEventStore for persistent storage following existing patterns.
    """
    
    def __init__(self, storage: Optional[SecurityEventStore] = None):
        """
        Initialize session monitor.
        
        Args:
            storage: SecurityEventStore instance (default: creates new instance)
        """
        self.storage = storage or SecurityEventStore()
        
        # Optional in-memory cache for active sessions (60 second TTL)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 60  # seconds
        self._cache_timestamps: Dict[str, float] = {}
        
        logger.info("SessionMonitor initialized")
    
    def create_session(
        self,
        session_id: str,
        account_id: str,
        user_id: Optional[str] = None
    ) -> SessionBehavior:
        """
        Create a new session.
        
        Args:
            session_id: Unique session identifier
            account_id: Account/customer ID
            user_id: Optional additional user identifier
        
        Returns:
            SessionBehavior object
        
        Raises:
            ValueError: If session_id or account_id is empty
            
        Example:
            >>> monitor = SessionMonitor()
            >>> session = monitor.create_session("sess_123", "acc_456")
            >>> print(session.session_id)
            sess_123
        """
        if not session_id or not account_id:
            raise ValueError("session_id and account_id are required")
        
        now = int(datetime.now(timezone.utc).timestamp())
        
        # Create session object
        session = SessionBehavior(
            session_id=session_id,
            account_id=account_id,
            user_id=user_id,
            login_time=now,
            last_activity_time=now,
            created_at=now,
            updated_at=now
        )
        
        try:
            # Store in database
            self.storage.store_session(session.to_dict())
            
            # Store session start event
            event = SessionEvent(
                event_id=create_event_id(session_id, EVENT_TYPES["SESSION_START"]),
                session_id=session_id,
                event_type=EVENT_TYPES["SESSION_START"],
                event_time=now,
                risk_delta=0.0,
                event_data={"account_id": account_id, "user_id": user_id}
            )
            self.storage.store_session_event(event.to_dict())
            
            # Update cache
            self._cache[session_id] = session.to_dict()
            self._cache_timestamps[session_id] = time.time()
            
            logger.info(f"Session created: {session_id} for account {account_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            # Return session object anyway for graceful degradation
            return session
    
    def get_session(self, session_id: str) -> Optional[SessionBehavior]:
        """
        Retrieve a session by ID.
        
        Args:
            session_id: Session identifier
        
        Returns:
            SessionBehavior object or None if not found
        
        Example:
            >>> session = monitor.get_session("sess_123")
            >>> if session:
            ...     print(f"Risk score: {session.risk_score}")
        """
        if not session_id:
            return None
        
        # Check cache first
        if session_id in self._cache:
            cache_age = time.time() - self._cache_timestamps.get(session_id, 0)
            if cache_age < self._cache_ttl:
                try:
                    return SessionBehavior.from_dict(self._cache[session_id])
                except Exception as e:
                    logger.warning(f"Cache deserialization failed for {session_id}: {e}")
        
        # Query database
        try:
            session_data = self.storage.get_session(session_id)
            if session_data:
                # Update cache
                self._cache[session_id] = session_data
                self._cache_timestamps[session_id] = time.time()
                return SessionBehavior.from_dict(session_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve session {session_id}: {e}")
            return None
    
    def update_session(self, session: SessionBehavior) -> bool:
        """
        Update an existing session.
        
        Args:
            session: SessionBehavior object with updated data
        
        Returns:
            True if successful, False otherwise
        
        Example:
            >>> session.risk_score = 45.0
            >>> session.add_anomaly(AnomalyType.VELOCITY_SPIKE)
            >>> monitor.update_session(session)
            True
        """
        if not session or not session.session_id:
            logger.warning("Cannot update session: invalid session object")
            return False
        
        try:
            # Update timestamp
            session.updated_at = int(datetime.now(timezone.utc).timestamp())
            
            # Store in database
            self.storage.store_session(session.to_dict())
            
            # Update cache
            self._cache[session.session_id] = session.to_dict()
            self._cache_timestamps[session.session_id] = time.time()
            
            logger.debug(f"Session updated: {session.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session {session.session_id}: {e}")
            return False
    
    def terminate_session(self, session_id: str, reason: str) -> bool:
        """
        Terminate a session.
        
        Args:
            session_id: Session to terminate
            reason: Reason for termination (e.g., "high_risk", "user_logout", "timeout")
        
        Returns:
            True if successful, False if session not found
        
        Example:
            >>> monitor.terminate_session("sess_123", "High risk detected")
            True
        """
        if not session_id or not reason:
            logger.warning("Cannot terminate session: missing session_id or reason")
            return False
        
        try:
            # Terminate in database
            success = self.storage.terminate_session(session_id, reason, terminated_by="system")
            
            if success:
                # Store termination event
                now = int(datetime.now(timezone.utc).timestamp())
                event = SessionEvent(
                    event_id=create_event_id(session_id, EVENT_TYPES["SESSION_TERMINATED"]),
                    session_id=session_id,
                    event_type=EVENT_TYPES["SESSION_TERMINATED"],
                    event_time=now,
                    risk_delta=0.0,
                    event_data={"reason": reason}
                )
                self.storage.store_session_event(event.to_dict())
                
                # Remove from cache
                self._cache.pop(session_id, None)
                self._cache_timestamps.pop(session_id, None)
                
                logger.info(f"Session terminated: {session_id}, reason: {reason}")
                return True
            
            logger.warning(f"Session not found for termination: {session_id}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to terminate session {session_id}: {e}")
            return False
    
    def get_active_sessions(self, limit: int = 50) -> List[SessionBehavior]:
        """
        Get active (non-terminated) sessions.
        
        Args:
            limit: Maximum number of sessions to return (default: 50)
        
        Returns:
            List of SessionBehavior objects
        
        Example:
            >>> active = monitor.get_active_sessions(limit=10)
            >>> print(f"Found {len(active)} active sessions")
        """
        try:
            sessions_data = self.storage.get_sessions_by_account(
                account_id="",  # Empty to get all accounts
                active_only=True,
                limit=limit
            )
            
            # If empty result, try alternative query
            if not sessions_data:
                # Query high risk sessions as fallback
                sessions_data = self.storage.get_high_risk_sessions(
                    min_risk_score=0.0,  # Get all risk levels
                    limit=limit
                )
            
            sessions = []
            for data in sessions_data:
                try:
                    sessions.append(SessionBehavior.from_dict(data))
                except Exception as e:
                    logger.warning(f"Failed to deserialize session: {e}")
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to retrieve active sessions: {e}")
            return []
    
    def get_sessions_by_account(self, account_id: str) -> List[SessionBehavior]:
        """
        Get all sessions for a specific account.
        
        Args:
            account_id: Account identifier
        
        Returns:
            List of SessionBehavior objects
        
        Example:
            >>> sessions = monitor.get_sessions_by_account("acc_456")
            >>> for session in sessions:
            ...     print(f"{session.session_id}: {session.risk_score}")
        """
        if not account_id:
            logger.warning("Cannot get sessions: account_id is required")
            return []
        
        try:
            sessions_data = self.storage.get_sessions_by_account(
                account_id=account_id,
                active_only=False,
                limit=100
            )
            
            sessions = []
            for data in sessions_data:
                try:
                    sessions.append(SessionBehavior.from_dict(data))
                except Exception as e:
                    logger.warning(f"Failed to deserialize session: {e}")
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to retrieve sessions for account {account_id}: {e}")
            return []
    
    def cleanup_old_sessions(self, older_than_hours: int = 24) -> int:
        """
        Clean up old sessions (archive or mark as expired).
        
        Currently marks old active sessions as terminated with reason "expired".
        In production, would archive to cold storage.
        
        Args:
            older_than_hours: Age threshold in hours (default: 24)
        
        Returns:
            Number of sessions cleaned up
        
        Example:
            >>> count = monitor.cleanup_old_sessions(older_than_hours=48)
            >>> print(f"Cleaned up {count} old sessions")
        """
        try:
            # Calculate timestamp threshold
            threshold_dt = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
            threshold = int(threshold_dt.timestamp())
            
            # Get old active sessions
            # Note: This is a simplified approach. Production would use a dedicated query.
            sessions = self.get_active_sessions(limit=1000)
            
            cleaned_count = 0
            for session in sessions:
                if session.created_at < threshold:
                    if self.terminate_session(session.session_id, "expired"):
                        cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} sessions older than {older_than_hours}h")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")
            return 0
    
    def record_transaction(
        self,
        session_id: str,
        transaction_amount: float,
        new_beneficiary: bool = False,
        transaction_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Record a transaction within a session and update metrics.
        
        Args:
            session_id: Session identifier
            transaction_amount: Transaction amount
            new_beneficiary: Whether a new beneficiary was added
            transaction_data: Additional transaction metadata
        
        Returns:
            True if successful, False otherwise
        
        Example:
            >>> monitor.record_transaction(
            ...     session_id="sess_123",
            ...     transaction_amount=500.0,
            ...     new_beneficiary=False
            ... )
            True
        """
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Cannot record transaction: session {session_id} not found")
            return False
        
        try:
            # Update session metrics
            session.update_metrics(
                transaction_amount=transaction_amount,
                new_beneficiary=new_beneficiary
            )
            
            # Store transaction event
            now = int(datetime.now(timezone.utc).timestamp())
            event = SessionEvent(
                event_id=create_event_id(session_id, EVENT_TYPES["TRANSACTION"]),
                session_id=session_id,
                event_type=EVENT_TYPES["TRANSACTION"],
                event_time=now,
                risk_delta=0.0,  # Will be updated by behavioral scorer
                event_data={
                    "amount": transaction_amount,
                    "new_beneficiary": new_beneficiary,
                    **(transaction_data or {})
                }
            )
            self.storage.store_session_event(event.to_dict())
            
            # Update session in database
            self.update_session(session)
            
            logger.debug(f"Transaction recorded for session {session_id}: ${transaction_amount}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record transaction for session {session_id}: {e}")
            return False
    
    def get_session_events(self, session_id: str, limit: int = 100) -> List[SessionEvent]:
        """
        Get events for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum events to return
        
        Returns:
            List of SessionEvent objects
        """
        try:
            events_data = self.storage.get_session_events(session_id, limit=limit)
            
            events = []
            for data in events_data:
                try:
                    events.append(SessionEvent.from_dict(data))
                except Exception as e:
                    logger.warning(f"Failed to deserialize event: {e}")
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to retrieve events for session {session_id}: {e}")
            return []
    
    def _clear_expired_cache(self) -> None:
        """Clear expired entries from in-memory cache (internal maintenance)"""
        now = time.time()
        expired_keys = [
            key for key, ts in self._cache_timestamps.items()
            if now - ts >= self._cache_ttl
        ]
        
        for key in expired_keys:
            self._cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
