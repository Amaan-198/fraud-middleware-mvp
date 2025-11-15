"""
Session Behavior Models

Data models for behavioral biometrics session monitoring.

Tracks user session behavior over time to detect:
- Account takeover
- Session hijacking
- Behavioral anomalies
- Suspicious activity patterns

Designed to integrate with existing fraud detection pipeline.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from pydantic import BaseModel, Field, validator
from enum import Enum


class SessionStatus(str, Enum):
    """Session lifecycle status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    EXPIRED = "expired"


class AnomalyType(str, Enum):
    """Types of behavioral anomalies"""
    VELOCITY_SPIKE = "velocity_spike"              # Unusual transaction frequency
    AMOUNT_ANOMALY = "amount_anomaly"              # Unusual transaction amounts
    LOCATION_CHANGE = "location_change"            # Sudden location shift
    TIME_PATTERN_CHANGE = "time_pattern_change"    # Different time-of-day pattern
    DEVICE_CHANGE = "device_change"                # Device switch mid-session
    BENEFICIARY_SPIKE = "beneficiary_spike"        # Multiple new beneficiaries
    MERCHANT_ANOMALY = "merchant_anomaly"          # Unusual merchant types
    TYPING_PATTERN_CHANGE = "typing_pattern_change"  # Different interaction speed


class SessionRiskLevel(str, Enum):
    """Session risk assessment levels"""
    LOW = "low"           # Normal behavior, 0-30
    MEDIUM = "medium"     # Minor anomalies, 30-60
    HIGH = "high"         # Suspicious patterns, 60-80
    CRITICAL = "critical" # Likely compromise, 80-100


# ============================================================================
# Pydantic Models (for API validation)
# ============================================================================

class SessionBehaviorModel(BaseModel):
    """
    Pydantic model for session behavior tracking.
    
    Used for API request/response validation.
    """
    session_id: str = Field(..., min_length=1, max_length=200, description="Unique session identifier")
    account_id: str = Field(..., min_length=1, max_length=100, description="Account/user ID")
    user_id: Optional[str] = Field(None, max_length=100, description="Additional user identifier")
    
    # Session lifecycle
    login_time: datetime = Field(..., description="Session start timestamp")
    last_activity_time: datetime = Field(..., description="Last activity timestamp")
    
    # Behavioral metrics
    transaction_count: int = Field(default=0, ge=0, description="Number of transactions in session")
    total_amount: float = Field(default=0.0, ge=0, description="Total transaction amount")
    beneficiaries_added: int = Field(default=0, ge=0, description="New beneficiaries added")
    
    # Risk assessment
    risk_score: float = Field(default=0.0, ge=0, le=100, description="Session risk score (0-100)")
    is_terminated: bool = Field(default=False, description="Whether session was terminated")
    termination_reason: Optional[str] = Field(None, max_length=500, description="Reason for termination")
    
    # Anomalies
    anomalies_detected: List[str] = Field(default_factory=list, description="List of detected anomalies")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('anomalies_detected', pre=True)
    def parse_anomalies(cls, v):
        """Parse anomalies from JSON string if needed"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v if v else []
    
    @validator('metadata', pre=True)
    def parse_metadata(cls, v):
        """Parse metadata from JSON string if needed"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v if v else {}


class SessionEventModel(BaseModel):
    """
    Pydantic model for session events.
    
    Tracks individual events within a session.
    """
    event_id: str = Field(..., min_length=1, max_length=200, description="Unique event identifier")
    session_id: str = Field(..., min_length=1, max_length=200, description="Parent session ID")
    event_type: str = Field(..., min_length=1, max_length=100, description="Event type")
    event_time: datetime = Field(..., description="Event timestamp")
    risk_delta: float = Field(default=0.0, description="Risk score change from this event")
    event_data: Dict[str, Any] = Field(default_factory=dict, description="Event-specific data")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('event_data', pre=True)
    def parse_event_data(cls, v):
        """Parse event data from JSON string if needed"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v if v else {}


class SessionRiskScoreModel(BaseModel):
    """
    Risk score breakdown for a session.
    
    Provides detailed risk analysis.
    """
    session_id: str = Field(..., description="Session identifier")
    overall_score: float = Field(..., ge=0, le=100, description="Overall risk score")
    risk_level: SessionRiskLevel = Field(..., description="Risk level classification")
    
    # Component scores
    velocity_score: float = Field(default=0.0, ge=0, le=100, description="Transaction velocity risk")
    amount_score: float = Field(default=0.0, ge=0, le=100, description="Amount pattern risk")
    location_score: float = Field(default=0.0, ge=0, le=100, description="Location risk")
    time_score: float = Field(default=0.0, ge=0, le=100, description="Time pattern risk")
    device_score: float = Field(default=0.0, ge=0, le=100, description="Device consistency risk")
    
    # Anomalies
    anomalies: List[Dict[str, Any]] = Field(default_factory=list, description="Detected anomalies")
    
    # Recommendations
    recommended_action: str = Field(..., description="Recommended action (allow/challenge/terminate)")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in assessment")


# ============================================================================
# Dataclass Models (for internal use)
# ============================================================================

@dataclass
class SessionBehavior:
    """
    Internal dataclass for session behavior tracking.
    
    Used within the session monitoring engine for efficient processing.
    """
    session_id: str
    account_id: str
    user_id: Optional[str] = None
    
    # Session lifecycle (stored as UNIX timestamps for SQLite)
    login_time: int = 0  # UNIX timestamp
    last_activity_time: int = 0  # UNIX timestamp
    
    # Behavioral metrics
    transaction_count: int = 0
    total_amount: float = 0.0
    beneficiaries_added: int = 0
    
    # Risk assessment
    risk_score: float = 0.0
    is_terminated: bool = False
    termination_reason: Optional[str] = None
    
    # Anomalies (stored as JSON string)
    anomalies_detected: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps (stored as UNIX timestamps)
    created_at: int = 0
    updated_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        # Convert lists/dicts to JSON strings for SQLite
        data['anomalies_detected'] = json.dumps(self.anomalies_detected)
        data['metadata'] = json.dumps(self.metadata)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionBehavior':
        """Create from dictionary (e.g., from database)"""
        # Parse JSON strings back to Python objects
        if isinstance(data.get('anomalies_detected'), str):
            data['anomalies_detected'] = json.loads(data['anomalies_detected'])
        if isinstance(data.get('metadata'), str):
            data['metadata'] = json.loads(data['metadata'])
        
        return cls(**data)
    
    def add_anomaly(self, anomaly_type: AnomalyType, details: Optional[str] = None) -> None:
        """Add an anomaly to the session"""
        anomaly_str = anomaly_type.value
        if details:
            anomaly_str = f"{anomaly_str}:{details}"
        
        if anomaly_str not in self.anomalies_detected:
            self.anomalies_detected.append(anomaly_str)
    
    def update_metrics(
        self,
        transaction_amount: Optional[float] = None,
        new_beneficiary: bool = False
    ) -> None:
        """Update session metrics after a transaction"""
        if transaction_amount is not None:
            self.transaction_count += 1
            self.total_amount += transaction_amount
        
        if new_beneficiary:
            self.beneficiaries_added += 1
        
        self.last_activity_time = int(datetime.now(timezone.utc).timestamp())
        self.updated_at = self.last_activity_time


@dataclass
class SessionEvent:
    """
    Internal dataclass for session events.
    
    Tracks individual events within a session for audit trail.
    """
    event_id: str
    session_id: str
    event_type: str
    event_time: int  # UNIX timestamp
    risk_delta: float = 0.0
    event_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        # Convert dict to JSON string for SQLite
        data['event_data'] = json.dumps(self.event_data)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionEvent':
        """Create from dictionary (e.g., from database)"""
        # Parse JSON string back to dict
        if isinstance(data.get('event_data'), str):
            data['event_data'] = json.loads(data['event_data'])
        
        return cls(**data)


@dataclass
class SessionRiskScore:
    """
    Detailed risk score breakdown for a session.
    
    Provides component scores and reasoning.
    """
    session_id: str
    overall_score: float
    
    # Component scores
    velocity_score: float = 0.0
    amount_score: float = 0.0
    location_score: float = 0.0
    time_score: float = 0.0
    device_score: float = 0.0
    
    # Anomalies
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    
    # Recommendations
    recommended_action: str = "allow"  # allow, challenge, terminate
    confidence: float = 0.0
    
    def get_risk_level(self) -> SessionRiskLevel:
        """Classify risk level based on overall score"""
        if self.overall_score >= 80:
            return SessionRiskLevel.CRITICAL
        elif self.overall_score >= 60:
            return SessionRiskLevel.HIGH
        elif self.overall_score >= 30:
            return SessionRiskLevel.MEDIUM
        else:
            return SessionRiskLevel.LOW
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['risk_level'] = self.get_risk_level().value
        return data


# ============================================================================
# Helper Functions
# ============================================================================

def create_session_id(account_id: str, timestamp: Optional[datetime] = None) -> str:
    """
    Generate a unique session ID.
    
    Args:
        account_id: Account identifier
        timestamp: Session start time (default: now)
    
    Returns:
        Unique session ID
    """
    import hashlib
    
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    # Create hash from account + timestamp for uniqueness
    data = f"{account_id}:{timestamp.isoformat()}".encode()
    hash_digest = hashlib.sha256(data).hexdigest()[:16]
    
    return f"sess_{account_id}_{hash_digest}"


def create_event_id(session_id: str, event_type: str, timestamp: Optional[datetime] = None) -> str:
    """
    Generate a unique event ID.
    
    Args:
        session_id: Parent session ID
        event_type: Type of event
        timestamp: Event time (default: now)
    
    Returns:
        Unique event ID
    """
    import hashlib
    
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    # Create hash from session + type + timestamp
    data = f"{session_id}:{event_type}:{timestamp.isoformat()}".encode()
    hash_digest = hashlib.sha256(data).hexdigest()[:12]
    
    return f"evt_{hash_digest}"


def parse_anomaly_string(anomaly: str) -> Dict[str, Any]:
    """
    Parse an anomaly string into structured data.
    
    Args:
        anomaly: Anomaly string (e.g., "velocity_spike:10_txns_in_5_min")
    
    Returns:
        Dictionary with type and details
    """
    parts = anomaly.split(":", 1)
    return {
        "type": parts[0],
        "details": parts[1] if len(parts) > 1 else None
    }


def get_session_age_minutes(session: SessionBehavior) -> float:
    """
    Calculate session age in minutes.
    
    Args:
        session: Session behavior object
    
    Returns:
        Age in minutes
    """
    now = int(datetime.now(timezone.utc).timestamp())
    age_seconds = now - session.login_time
    return age_seconds / 60.0


def get_session_idle_minutes(session: SessionBehavior) -> float:
    """
    Calculate time since last activity in minutes.
    
    Args:
        session: Session behavior object
    
    Returns:
        Idle time in minutes
    """
    now = int(datetime.now(timezone.utc).timestamp())
    idle_seconds = now - session.last_activity_time
    return idle_seconds / 60.0


# ============================================================================
# Constants
# ============================================================================

# Default thresholds for anomaly detection
DEFAULT_THRESHOLDS = {
    "velocity_spike_window_minutes": 5,
    "velocity_spike_threshold": 10,  # transactions
    "amount_multiplier_threshold": 5.0,  # 5x average
    "location_change_km_threshold": 500,
    "time_pattern_deviation_hours": 3,
    "max_beneficiaries_per_session": 5,
    "session_idle_timeout_minutes": 30,
    "session_max_age_hours": 8,
}

# Risk score weights
RISK_WEIGHTS = {
    "velocity": 0.25,
    "amount": 0.20,
    "location": 0.15,
    "time_pattern": 0.15,
    "device": 0.15,
    "anomaly_count": 0.10,
}

# Event types
EVENT_TYPES = {
    "SESSION_START": "session_start",
    "TRANSACTION": "transaction",
    "BENEFICIARY_ADD": "beneficiary_add",
    "DEVICE_CHANGE": "device_change",
    "LOCATION_CHANGE": "location_change",
    "ANOMALY_DETECTED": "anomaly_detected",
    "RISK_ESCALATION": "risk_escalation",
    "SESSION_CHALLENGED": "session_challenged",
    "SESSION_TERMINATED": "session_terminated",
}
