"""
Unit tests for session behavior models.

Tests data models, validation, and serialization for behavioral biometrics.
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from api.models.session_behavior import (
    SessionBehavior,
    SessionEvent,
    SessionRiskScore,
    SessionBehaviorModel,
    SessionEventModel,
    SessionRiskScoreModel,
    SessionStatus,
    AnomalyType,
    SessionRiskLevel,
    create_session_id,
    create_event_id,
    parse_anomaly_string,
    get_session_age_minutes,
    get_session_idle_minutes,
    DEFAULT_THRESHOLDS,
    RISK_WEIGHTS,
    EVENT_TYPES,
)


class TestSessionBehaviorDataclass:
    """Tests for SessionBehavior dataclass"""

    def test_create_session_behavior(self):
        """Test creating a session behavior instance"""
        now = int(datetime.now(timezone.utc).timestamp())
        
        session = SessionBehavior(
            session_id="sess_test_123",
            account_id="acc_001",
            user_id="user_001",
            login_time=now,
            last_activity_time=now,
            created_at=now,
            updated_at=now
        )
        
        assert session.session_id == "sess_test_123"
        assert session.account_id == "acc_001"
        assert session.transaction_count == 0
        assert session.total_amount == 0.0
        assert session.risk_score == 0.0
        assert session.is_terminated is False
        assert len(session.anomalies_detected) == 0

    def test_to_dict_converts_json_fields(self):
        """Test to_dict() converts lists/dicts to JSON strings"""
        now = int(datetime.now(timezone.utc).timestamp())
        
        session = SessionBehavior(
            session_id="sess_test_123",
            account_id="acc_001",
            login_time=now,
            last_activity_time=now,
            anomalies_detected=["velocity_spike", "amount_anomaly"],
            metadata={"test": "data"},
            created_at=now,
            updated_at=now
        )
        
        data = session.to_dict()
        
        # JSON fields should be strings
        assert isinstance(data['anomalies_detected'], str)
        assert isinstance(data['metadata'], str)
        
        # Verify JSON content
        assert json.loads(data['anomalies_detected']) == ["velocity_spike", "amount_anomaly"]
        assert json.loads(data['metadata']) == {"test": "data"}

    def test_from_dict_parses_json_fields(self):
        """Test from_dict() parses JSON strings back to Python objects"""
        data = {
            'session_id': 'sess_test_123',
            'account_id': 'acc_001',
            'user_id': None,
            'login_time': 1234567890,
            'last_activity_time': 1234567890,
            'transaction_count': 5,
            'total_amount': 500.0,
            'beneficiaries_added': 1,
            'risk_score': 35.5,
            'is_terminated': False,
            'termination_reason': None,
            'anomalies_detected': '["velocity_spike"]',
            'metadata': '{"device": "mobile"}',
            'created_at': 1234567890,
            'updated_at': 1234567890
        }
        
        session = SessionBehavior.from_dict(data)
        
        assert session.session_id == 'sess_test_123'
        assert session.transaction_count == 5
        assert session.anomalies_detected == ["velocity_spike"]
        assert session.metadata == {"device": "mobile"}

    def test_add_anomaly(self):
        """Test adding anomalies to session"""
        now = int(datetime.now(timezone.utc).timestamp())
        
        session = SessionBehavior(
            session_id="sess_test_123",
            account_id="acc_001",
            login_time=now,
            last_activity_time=now,
            created_at=now,
            updated_at=now
        )
        
        session.add_anomaly(AnomalyType.VELOCITY_SPIKE, "10 txns in 5 min")
        session.add_anomaly(AnomalyType.AMOUNT_ANOMALY)
        
        assert len(session.anomalies_detected) == 2
        assert "velocity_spike:10 txns in 5 min" in session.anomalies_detected
        assert "amount_anomaly" in session.anomalies_detected
        
        # Adding duplicate should not add again
        session.add_anomaly(AnomalyType.VELOCITY_SPIKE, "10 txns in 5 min")
        assert len(session.anomalies_detected) == 2

    def test_update_metrics(self):
        """Test updating session metrics"""
        now = int(datetime.now(timezone.utc).timestamp())
        
        session = SessionBehavior(
            session_id="sess_test_123",
            account_id="acc_001",
            login_time=now,
            last_activity_time=now,
            created_at=now,
            updated_at=now
        )
        
        # Update with transaction
        session.update_metrics(transaction_amount=100.0)
        assert session.transaction_count == 1
        assert session.total_amount == 100.0
        
        # Update with beneficiary
        session.update_metrics(new_beneficiary=True)
        assert session.beneficiaries_added == 1
        
        # Update with both
        session.update_metrics(transaction_amount=200.0, new_beneficiary=True)
        assert session.transaction_count == 2
        assert session.total_amount == 300.0
        assert session.beneficiaries_added == 2


class TestSessionEventDataclass:
    """Tests for SessionEvent dataclass"""

    def test_create_session_event(self):
        """Test creating a session event"""
        now = int(datetime.now(timezone.utc).timestamp())
        
        event = SessionEvent(
            event_id="evt_123",
            session_id="sess_test_123",
            event_type="transaction",
            event_time=now,
            risk_delta=5.0,
            event_data={"amount": 100.0}
        )
        
        assert event.event_id == "evt_123"
        assert event.session_id == "sess_test_123"
        assert event.risk_delta == 5.0

    def test_to_dict_converts_event_data(self):
        """Test to_dict() converts event_data to JSON string"""
        now = int(datetime.now(timezone.utc).timestamp())
        
        event = SessionEvent(
            event_id="evt_123",
            session_id="sess_test_123",
            event_type="transaction",
            event_time=now,
            event_data={"amount": 100.0, "merchant": "Store"}
        )
        
        data = event.to_dict()
        
        assert isinstance(data['event_data'], str)
        assert json.loads(data['event_data']) == {"amount": 100.0, "merchant": "Store"}

    def test_from_dict_parses_event_data(self):
        """Test from_dict() parses JSON event_data"""
        data = {
            'event_id': 'evt_123',
            'session_id': 'sess_test_123',
            'event_type': 'transaction',
            'event_time': 1234567890,
            'risk_delta': 10.0,
            'event_data': '{"test": "data"}'
        }
        
        event = SessionEvent.from_dict(data)
        
        assert event.event_data == {"test": "data"}


class TestSessionRiskScore:
    """Tests for SessionRiskScore dataclass"""

    def test_get_risk_level_low(self):
        """Test risk level classification - LOW"""
        score = SessionRiskScore(
            session_id="sess_test",
            overall_score=25.0
        )
        
        assert score.get_risk_level() == SessionRiskLevel.LOW

    def test_get_risk_level_medium(self):
        """Test risk level classification - MEDIUM"""
        score = SessionRiskScore(
            session_id="sess_test",
            overall_score=45.0
        )
        
        assert score.get_risk_level() == SessionRiskLevel.MEDIUM

    def test_get_risk_level_high(self):
        """Test risk level classification - HIGH"""
        score = SessionRiskScore(
            session_id="sess_test",
            overall_score=70.0
        )
        
        assert score.get_risk_level() == SessionRiskLevel.HIGH

    def test_get_risk_level_critical(self):
        """Test risk level classification - CRITICAL"""
        score = SessionRiskScore(
            session_id="sess_test",
            overall_score=85.0
        )
        
        assert score.get_risk_level() == SessionRiskLevel.CRITICAL

    def test_to_dict_includes_risk_level(self):
        """Test to_dict() includes calculated risk level"""
        score = SessionRiskScore(
            session_id="sess_test",
            overall_score=65.0,
            recommended_action="challenge",
            confidence=0.85
        )
        
        data = score.to_dict()
        
        assert data['risk_level'] == 'high'
        assert data['overall_score'] == 65.0


class TestPydanticModels:
    """Tests for Pydantic validation models"""

    def test_session_behavior_model_validation(self):
        """Test SessionBehaviorModel validates correctly"""
        now = datetime.now(timezone.utc)
        
        model = SessionBehaviorModel(
            session_id="sess_test_123",
            account_id="acc_001",
            login_time=now,
            last_activity_time=now
        )
        
        assert model.session_id == "sess_test_123"
        assert model.transaction_count == 0
        assert model.risk_score == 0.0

    def test_session_behavior_model_parses_json_strings(self):
        """Test model parses JSON string fields"""
        now = datetime.now(timezone.utc)
        
        model = SessionBehaviorModel(
            session_id="sess_test_123",
            account_id="acc_001",
            login_time=now,
            last_activity_time=now,
            anomalies_detected='["velocity_spike"]',
            metadata='{"test": "data"}'
        )
        
        assert model.anomalies_detected == ["velocity_spike"]
        assert model.metadata == {"test": "data"}

    def test_session_event_model_validation(self):
        """Test SessionEventModel validates correctly"""
        now = datetime.now(timezone.utc)
        
        model = SessionEventModel(
            event_id="evt_123",
            session_id="sess_test",
            event_type="transaction",
            event_time=now
        )
        
        assert model.event_id == "evt_123"
        assert model.risk_delta == 0.0

    def test_session_risk_score_model_validation(self):
        """Test SessionRiskScoreModel validates correctly"""
        model = SessionRiskScoreModel(
            session_id="sess_test",
            overall_score=45.0,
            risk_level=SessionRiskLevel.MEDIUM,
            recommended_action="allow",
            confidence=0.75
        )
        
        assert model.risk_level == SessionRiskLevel.MEDIUM
        assert model.confidence == 0.75


class TestHelperFunctions:
    """Tests for helper functions"""

    def test_create_session_id(self):
        """Test session ID generation"""
        session_id = create_session_id("acc_001")
        
        assert session_id.startswith("sess_acc_001_")
        assert len(session_id) > 20  # Has hash suffix

    def test_create_session_id_deterministic_with_timestamp(self):
        """Test session ID is deterministic with same inputs"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        id1 = create_session_id("acc_001", timestamp)
        id2 = create_session_id("acc_001", timestamp)
        
        assert id1 == id2

    def test_create_event_id(self):
        """Test event ID generation"""
        event_id = create_event_id("sess_test_123", "transaction")
        
        assert event_id.startswith("evt_")
        assert len(event_id) > 10

    def test_parse_anomaly_string_with_details(self):
        """Test parsing anomaly string with details"""
        result = parse_anomaly_string("velocity_spike:10_txns_in_5_min")
        
        assert result['type'] == "velocity_spike"
        assert result['details'] == "10_txns_in_5_min"

    def test_parse_anomaly_string_without_details(self):
        """Test parsing anomaly string without details"""
        result = parse_anomaly_string("amount_anomaly")
        
        assert result['type'] == "amount_anomaly"
        assert result['details'] is None

    def test_get_session_age_minutes(self):
        """Test calculating session age"""
        # Session started 10 minutes ago
        login_time = int((datetime.now(timezone.utc) - timedelta(minutes=10)).timestamp())
        
        session = SessionBehavior(
            session_id="sess_test",
            account_id="acc_001",
            login_time=login_time,
            last_activity_time=login_time,
            created_at=login_time,
            updated_at=login_time
        )
        
        age = get_session_age_minutes(session)
        
        # Should be approximately 10 minutes (allow small variance)
        assert 9 <= age <= 11

    def test_get_session_idle_minutes(self):
        """Test calculating session idle time"""
        now = int(datetime.now(timezone.utc).timestamp())
        # Last activity 5 minutes ago
        last_activity = int((datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp())
        
        session = SessionBehavior(
            session_id="sess_test",
            account_id="acc_001",
            login_time=now,
            last_activity_time=last_activity,
            created_at=now,
            updated_at=now
        )
        
        idle = get_session_idle_minutes(session)
        
        # Should be approximately 5 minutes
        assert 4 <= idle <= 6


class TestConstants:
    """Tests for module constants"""

    def test_default_thresholds_exist(self):
        """Test default thresholds are defined"""
        assert 'velocity_spike_threshold' in DEFAULT_THRESHOLDS
        assert 'amount_multiplier_threshold' in DEFAULT_THRESHOLDS
        assert 'session_idle_timeout_minutes' in DEFAULT_THRESHOLDS

    def test_risk_weights_sum_to_one(self):
        """Test risk weights sum to 1.0"""
        total = sum(RISK_WEIGHTS.values())
        assert 0.99 <= total <= 1.01  # Allow small floating point variance

    def test_event_types_defined(self):
        """Test event types are defined"""
        assert 'SESSION_START' in EVENT_TYPES
        assert 'TRANSACTION' in EVENT_TYPES
        assert 'SESSION_TERMINATED' in EVENT_TYPES


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
