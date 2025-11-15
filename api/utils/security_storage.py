"""
Security Event Storage - SQLite Database for Audit Logs

Persistent storage for:
- Security events and alerts
- Audit logs (who accessed what, when)
- SOC review queue
- System access logs

Uses SQLite for MVP (production would use PostgreSQL/TimescaleDB)
"""

import sqlite3
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager


class SecurityEventStore:
    """
    Persistent storage for security events and audit logs.

    Provides:
    - Event storage and retrieval
    - Audit log tracking
    - Review queue management
    - Analytics queries
    """

    def __init__(self, db_path: str = "data/security_events.db"):
        """
        Initialize security event storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database schema
        self._init_schema()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Security events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    threat_type TEXT NOT NULL,
                    threat_level INTEGER NOT NULL,
                    source_identifier TEXT NOT NULL,
                    description TEXT NOT NULL,
                    metadata TEXT,
                    requires_review BOOLEAN NOT NULL,
                    reviewed BOOLEAN DEFAULT 0,
                    reviewed_at TEXT,
                    reviewed_by TEXT,
                    review_notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Audit logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # API access logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_access_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    response_time_ms REAL NOT NULL,
                    ip_address TEXT,
                    blocked BOOLEAN DEFAULT 0,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Blocked sources table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blocked_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT UNIQUE NOT NULL,
                    blocked_at TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    threat_level INTEGER NOT NULL,
                    auto_blocked BOOLEAN DEFAULT 1,
                    unblocked BOOLEAN DEFAULT 0,
                    unblocked_at TEXT,
                    unblocked_by TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indices for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                ON security_events(timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_review
                ON security_events(requires_review, reviewed)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_source
                ON security_events(source_identifier)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                ON audit_logs(timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_source
                ON audit_logs(source_id, timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_access_timestamp
                ON api_access_logs(timestamp DESC)
            """)

            # ===================================================================
            # SESSION TRACKING TABLES (Behavioral Biometrics)
            # Added for session monitoring feature - fully additive
            # ===================================================================

            # Session behaviors table - tracks behavioral metrics for each session
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_behaviors (
                    session_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    user_id TEXT,
                    login_time INTEGER NOT NULL,
                    transaction_count INTEGER DEFAULT 0,
                    total_amount REAL DEFAULT 0.0,
                    beneficiaries_added INTEGER DEFAULT 0,
                    last_activity_time INTEGER NOT NULL,
                    risk_score REAL DEFAULT 0.0,
                    is_terminated BOOLEAN DEFAULT 0,
                    termination_reason TEXT,
                    anomalies_detected TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)

            # Session events table - audit trail of events within sessions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_events (
                    event_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_time INTEGER NOT NULL,
                    risk_delta REAL DEFAULT 0.0,
                    event_data TEXT DEFAULT '{}',
                    FOREIGN KEY (session_id) REFERENCES session_behaviors(session_id)
                )
            """)

            # Indices for session queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_account
                ON session_behaviors(account_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_risk
                ON session_behaviors(risk_score DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_active
                ON session_behaviors(is_terminated)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_time
                ON session_behaviors(created_at DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_session
                ON session_events(session_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_time
                ON session_events(event_time DESC)
            """)

    def store_event(self, event: Dict[str, Any]) -> int:
        """
        Store a security event.

        Args:
            event: Security event dictionary

        Returns:
            Database ID of stored event
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO security_events (
                    event_id, timestamp, threat_type, threat_level,
                    source_identifier, description, metadata, requires_review
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event["event_id"],
                event["timestamp"],
                event["threat_type"],
                event["threat_level"],
                event["source_identifier"],
                event["description"],
                json.dumps(event.get("metadata", {})),
                event["requires_review"]
            ))

            return cursor.lastrowid

    def log_audit_event(
        self,
        source_id: str,
        action: str,
        resource: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Log an audit event.

        Args:
            source_id: User/API key performing action
            action: Action performed (e.g., "read", "write", "delete")
            resource: Resource accessed (e.g., "user:12345", "transaction:abc")
            success: Whether action succeeded
            ip_address: Source IP
            user_agent: User agent string
            metadata: Additional context

        Returns:
            Database ID of audit log
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO audit_logs (
                    timestamp, source_id, action, resource, success,
                    ip_address, user_agent, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                source_id,
                action,
                resource,
                success,
                ip_address,
                user_agent,
                json.dumps(metadata or {})
            ))

            return cursor.lastrowid

    def log_api_access(
        self,
        source_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        ip_address: Optional[str] = None,
        blocked: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Log an API access event.

        Args:
            source_id: API key or user ID
            endpoint: API endpoint accessed
            method: HTTP method
            status_code: Response status code
            response_time_ms: Response time in milliseconds
            ip_address: Source IP
            blocked: Whether request was blocked
            metadata: Additional context

        Returns:
            Database ID of log entry
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO api_access_logs (
                    timestamp, source_id, endpoint, method, status_code,
                    response_time_ms, ip_address, blocked, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                source_id,
                endpoint,
                method,
                status_code,
                response_time_ms,
                ip_address,
                blocked,
                json.dumps(metadata or {})
            ))

            return cursor.lastrowid

    def get_events(
        self,
        limit: int = 100,
        min_threat_level: int = 0,
        threat_type: Optional[str] = None,
        source_id: Optional[str] = None,
        reviewed: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve security events with filters.

        Args:
            limit: Maximum events to return
            min_threat_level: Minimum threat level (0-4)
            threat_type: Filter by threat type
            source_id: Filter by source
            reviewed: Filter by review status

        Returns:
            List of security events
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Build query dynamically based on filters
            query = "SELECT * FROM security_events WHERE threat_level >= ? AND requires_review = 1"
            params = [min_threat_level]

            if threat_type:
                query += " AND threat_type = ?"
                params.append(threat_type)

            if source_id:
                query += " AND source_identifier = ?"
                params.append(source_id)

            if reviewed is not None:
                query += " AND reviewed = ?"
                params.append(reviewed)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)

            events = []
            for row in cursor.fetchall():
                event = dict(row)
                event["metadata"] = json.loads(event["metadata"]) if event["metadata"] else {}
                events.append(event)

            return events

    def get_review_queue(self, limit: int = 10000) -> List[Dict[str, Any]]:
        """
        Get events requiring SOC review (unreviewed events that require human review).

        Args:
            limit: Maximum events to return (default 10000 for bulk operations)

        Returns:
            List of unreviewed events flagged for review
        """
        return self.get_events(
            limit=limit,
            min_threat_level=0,
            reviewed=False  # CRITICAL: Only unreviewed events
        )

    def mark_reviewed(
        self,
        event_id: str,
        reviewed_by: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Mark an event as reviewed by SOC analyst.

        Args:
            event_id: Event ID to mark as reviewed
            reviewed_by: Analyst ID/name
            notes: Review notes

        Returns:
            True if successful, False if event not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE security_events
                SET reviewed = 1,
                    reviewed_at = ?,
                    reviewed_by = ?,
                    review_notes = ?
                WHERE event_id = ?
            """, (
                datetime.now(timezone.utc).isoformat(),
                reviewed_by,
                notes,
                event_id
            ))

            return cursor.rowcount > 0

    def clear_all_reviews(
        self,
        reviewed_by: str,
        notes: Optional[str] = None
    ) -> int:
        """
        Mark all unreviewed events as reviewed (bulk operation).
        
        Args:
            reviewed_by: Analyst ID performing bulk clear
            notes: Notes for all cleared reviews
            
        Returns:
            Number of events marked as reviewed
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE security_events
                SET reviewed = 1,
                    reviewed_at = ?,
                    reviewed_by = ?,
                    review_notes = ?
                WHERE reviewed = 0 AND requires_review = 1
            """, (
                datetime.now(timezone.utc).isoformat(),
                reviewed_by,
                notes or "Bulk cleared"
            ))
            
            return cursor.rowcount

    def block_source(
        self,
        source_id: str,
        reason: str,
        threat_level: int,
        auto_blocked: bool = True
    ) -> int:
        """
        Block a source (API key, user, IP).

        Args:
            source_id: Source to block
            reason: Reason for blocking
            threat_level: Associated threat level
            auto_blocked: Whether auto-blocked by system

        Returns:
            Database ID of block record
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Upsert - update if exists, insert if not
            cursor.execute("""
                INSERT INTO blocked_sources (
                    source_id, blocked_at, reason, threat_level, auto_blocked
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    blocked_at = excluded.blocked_at,
                    reason = excluded.reason,
                    threat_level = excluded.threat_level,
                    unblocked = 0,
                    unblocked_at = NULL,
                    unblocked_by = NULL
            """, (
                source_id,
                datetime.now(timezone.utc).isoformat(),
                reason,
                threat_level,
                auto_blocked
            ))

            return cursor.lastrowid

    def unblock_source(self, source_id: str, unblocked_by: str) -> bool:
        """
        Unblock a previously blocked source.

        Args:
            source_id: Source to unblock
            unblocked_by: Analyst/admin performing unblock

        Returns:
            True if successful, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE blocked_sources
                SET unblocked = 1,
                    unblocked_at = ?,
                    unblocked_by = ?
                WHERE source_id = ? AND unblocked = 0
            """, (
                datetime.now(timezone.utc).isoformat(),
                unblocked_by,
                source_id
            ))

            return cursor.rowcount > 0

    def is_source_blocked(self, source_id: str) -> bool:
        """Check if a source is currently blocked"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) as count
                FROM blocked_sources
                WHERE source_id = ? AND unblocked = 0
            """, (source_id,))

            result = cursor.fetchone()
            return result["count"] > 0

    def get_audit_trail(
        self,
        source_id: Optional[str] = None,
        resource: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get audit trail for compliance/investigation.

        Args:
            source_id: Filter by source
            resource: Filter by resource
            limit: Maximum entries to return

        Returns:
            List of audit log entries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM audit_logs WHERE 1=1"
            params = []

            if source_id:
                query += " AND source_id = ?"
                params.append(source_id)

            if resource:
                query += " AND resource = ?"
                params.append(resource)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)

            logs = []
            for row in cursor.fetchall():
                log = dict(row)
                log["metadata"] = json.loads(log["metadata"]) if log["metadata"] else {}
                logs.append(log)

            return logs

    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get security statistics for dashboards.

        Args:
            days: Number of days to analyze

        Returns:
            Statistics dictionary
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Calculate date threshold
            threshold = datetime.now(timezone.utc).isoformat()[:10]  # Today's date

            # Total events by severity
            cursor.execute("""
                SELECT threat_level, COUNT(*) as count
                FROM security_events
                GROUP BY threat_level
            """)
            threat_levels = {row["threat_level"]: row["count"] for row in cursor.fetchall()}

            # Events requiring review
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM security_events
                WHERE requires_review = 1 AND reviewed = 0
            """)
            pending_reviews = cursor.fetchone()["count"]

            # Currently blocked sources
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM blocked_sources
                WHERE unblocked = 0
            """)
            blocked_count = cursor.fetchone()["count"]

            # Threat type distribution
            cursor.execute("""
                SELECT threat_type, COUNT(*) as count
                FROM security_events
                GROUP BY threat_type
            """)
            threat_types = {row["threat_type"]: row["count"] for row in cursor.fetchall()}

            # API access stats
            cursor.execute("""
                SELECT
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN blocked = 1 THEN 1 ELSE 0 END) as blocked_requests,
                    AVG(response_time_ms) as avg_response_time
                FROM api_access_logs
            """)
            api_stats = dict(cursor.fetchone())

            return {
                "threat_level_distribution": threat_levels,
                "threat_type_distribution": threat_types,
                "pending_reviews": pending_reviews,
                "blocked_sources": blocked_count,
                "total_events": sum(threat_levels.values()),
                "api_statistics": api_stats,
            }

    # ========================================================================
    # SESSION TRACKING METHODS (Behavioral Biometrics)
    # Added for session monitoring feature - fully additive
    # ========================================================================

    def store_session(self, session_data: Dict[str, Any]) -> bool:
        """
        Store or update a session behavior record.

        Args:
            session_data: Session behavior dictionary with fields:
                - session_id (required)
                - account_id (required)
                - user_id (optional)
                - login_time (required, UNIX timestamp)
                - transaction_count
                - total_amount
                - beneficiaries_added
                - last_activity_time (required, UNIX timestamp)
                - risk_score
                - is_terminated
                - termination_reason
                - anomalies_detected (JSON string or list)
                - metadata (JSON string or dict)
                - created_at (UNIX timestamp)
                - updated_at (UNIX timestamp)

        Returns:
            True if successful
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Ensure JSON fields are strings
            anomalies = session_data.get('anomalies_detected', '[]')
            if isinstance(anomalies, (list, dict)):
                anomalies = json.dumps(anomalies)

            metadata = session_data.get('metadata', '{}')
            if isinstance(metadata, dict):
                metadata = json.dumps(metadata)

            # Upsert - update if exists, insert if not
            cursor.execute("""
                INSERT INTO session_behaviors (
                    session_id, account_id, user_id, login_time,
                    transaction_count, total_amount, beneficiaries_added,
                    last_activity_time, risk_score, is_terminated,
                    termination_reason, anomalies_detected, metadata,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    transaction_count = excluded.transaction_count,
                    total_amount = excluded.total_amount,
                    beneficiaries_added = excluded.beneficiaries_added,
                    last_activity_time = excluded.last_activity_time,
                    risk_score = excluded.risk_score,
                    is_terminated = excluded.is_terminated,
                    termination_reason = excluded.termination_reason,
                    anomalies_detected = excluded.anomalies_detected,
                    metadata = excluded.metadata,
                    updated_at = excluded.updated_at
            """, (
                session_data['session_id'],
                session_data['account_id'],
                session_data.get('user_id'),
                session_data['login_time'],
                session_data.get('transaction_count', 0),
                session_data.get('total_amount', 0.0),
                session_data.get('beneficiaries_added', 0),
                session_data['last_activity_time'],
                session_data.get('risk_score', 0.0),
                session_data.get('is_terminated', False),
                session_data.get('termination_reason'),
                anomalies,
                metadata,
                session_data.get('created_at', int(datetime.now(timezone.utc).timestamp())),
                session_data.get('updated_at', int(datetime.now(timezone.utc).timestamp()))
            ))

            return True

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session data dict or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM session_behaviors
                WHERE session_id = ?
            """, (session_id,))

            row = cursor.fetchone()
            if not row:
                return None

            session = dict(row)
            # Parse JSON fields
            session['anomalies_detected'] = json.loads(session['anomalies_detected']) if session['anomalies_detected'] else []
            session['metadata'] = json.loads(session['metadata']) if session['metadata'] else {}

            return session

    def get_sessions_by_account(
        self,
        account_id: str,
        active_only: bool = False,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get sessions for an account.

        Args:
            account_id: Account identifier
            active_only: Only return non-terminated sessions
            limit: Maximum sessions to return

        Returns:
            List of session data dicts
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM session_behaviors WHERE account_id = ?"
            params = [account_id]

            if active_only:
                query += " AND is_terminated = 0"

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)

            sessions = []
            for row in cursor.fetchall():
                session = dict(row)
                session['anomalies_detected'] = json.loads(session['anomalies_detected']) if session['anomalies_detected'] else []
                session['metadata'] = json.loads(session['metadata']) if session['metadata'] else {}
                sessions.append(session)

            return sessions

    def get_high_risk_sessions(
        self,
        min_risk_score: float = 60.0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get high-risk sessions.

        Args:
            min_risk_score: Minimum risk score threshold
            limit: Maximum sessions to return

        Returns:
            List of high-risk session data dicts
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM session_behaviors
                WHERE risk_score >= ? AND is_terminated = 0
                ORDER BY risk_score DESC
                LIMIT ?
            """, (min_risk_score, limit))

            sessions = []
            for row in cursor.fetchall():
                session = dict(row)
                session['anomalies_detected'] = json.loads(session['anomalies_detected']) if session['anomalies_detected'] else []
                session['metadata'] = json.loads(session['metadata']) if session['metadata'] else {}
                sessions.append(session)

            return sessions

    def terminate_session(
        self,
        session_id: str,
        reason: str,
        terminated_by: Optional[str] = None
    ) -> bool:
        """
        Terminate a session.

        Args:
            session_id: Session to terminate
            reason: Reason for termination
            terminated_by: Who terminated (analyst ID, system, etc.)

        Returns:
            True if successful, False if session not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            termination_reason = f"{reason}"
            if terminated_by:
                termination_reason += f" (by: {terminated_by})"

            cursor.execute("""
                UPDATE session_behaviors
                SET is_terminated = 1,
                    termination_reason = ?,
                    updated_at = ?
                WHERE session_id = ?
            """, (
                termination_reason,
                int(datetime.now(timezone.utc).timestamp()),
                session_id
            ))

            return cursor.rowcount > 0

    def store_session_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Store a session event.

        Args:
            event_data: Event data dictionary with fields:
                - event_id (required)
                - session_id (required)
                - event_type (required)
                - event_time (required, UNIX timestamp)
                - risk_delta (optional)
                - event_data (JSON string or dict)

        Returns:
            True if successful
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Ensure event_data field is JSON string
            event_json = event_data.get('event_data', '{}')
            if isinstance(event_json, dict):
                event_json = json.dumps(event_json)

            cursor.execute("""
                INSERT INTO session_events (
                    event_id, session_id, event_type, event_time,
                    risk_delta, event_data
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event_data['event_id'],
                event_data['session_id'],
                event_data['event_type'],
                event_data['event_time'],
                event_data.get('risk_delta', 0.0),
                event_json
            ))

            return True

    def get_session_events(
        self,
        session_id: str,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get events for a session.

        Args:
            session_id: Session identifier
            limit: Maximum events to return

        Returns:
            List of event data dicts
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM session_events
                WHERE session_id = ?
                ORDER BY event_time DESC
                LIMIT ?
            """, (session_id, limit))

            events = []
            for row in cursor.fetchall():
                event = dict(row)
                event['event_data'] = json.loads(event['event_data']) if event['event_data'] else {}
                events.append(event)

            return events

    def get_session_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get session statistics for dashboards.

        Args:
            days: Number of days to analyze

        Returns:
            Statistics dictionary
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Calculate timestamp threshold (days ago)
            from datetime import timedelta
            threshold_dt = datetime.now(timezone.utc) - timedelta(days=days)
            threshold = int(threshold_dt.timestamp())

            # Total sessions
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM session_behaviors
                WHERE created_at >= ?
            """, (threshold,))
            total_sessions = cursor.fetchone()['count']

            # Active sessions
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM session_behaviors
                WHERE is_terminated = 0
            """)
            active_sessions = cursor.fetchone()['count']

            # High-risk sessions
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM session_behaviors
                WHERE risk_score >= 60 AND is_terminated = 0
            """)
            high_risk_sessions = cursor.fetchone()['count']

            # Average risk score
            cursor.execute("""
                SELECT AVG(risk_score) as avg_score
                FROM session_behaviors
                WHERE is_terminated = 0
            """)
            avg_risk_score = cursor.fetchone()['avg_score'] or 0.0

            # Total transactions across sessions
            cursor.execute("""
                SELECT SUM(transaction_count) as total
                FROM session_behaviors
                WHERE created_at >= ?
            """, (threshold,))
            total_transactions = cursor.fetchone()['total'] or 0

            # Sessions by risk level
            cursor.execute("""
                SELECT
                    CASE
                        WHEN risk_score < 30 THEN 'low'
                        WHEN risk_score < 60 THEN 'medium'
                        WHEN risk_score < 80 THEN 'high'
                        ELSE 'critical'
                    END as risk_level,
                    COUNT(*) as count
                FROM session_behaviors
                WHERE is_terminated = 0
                GROUP BY risk_level
            """)
            risk_distribution = {row['risk_level']: row['count'] for row in cursor.fetchall()}

            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "high_risk_sessions": high_risk_sessions,
                "average_risk_score": round(avg_risk_score, 2),
                "total_transactions": total_transactions,
                "risk_distribution": risk_distribution,
                "period_days": days
            }
