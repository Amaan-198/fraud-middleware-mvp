"""
Tests for SessionMonitor class

Tests session lifecycle, retrieval, updates, and cleanup.
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from api.models.session_monitor import SessionMonitor


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix='.db')
    yield path
    os.close(fd)
    os.unlink(path)


@pytest.fixture
def monitor(temp_db):
    """Create a SessionMonitor instance with temp database"""
    return SessionMonitor(db_path=temp_db)


class TestSessionMonitorBasics:
    """Test basic session operations"""

    def test_create_session(self, monitor):
        """Test creating a new session"""
        session = monitor.create_session(
            session_id='test_session_001',
            account_id='ACC123',
            user_agent='TestAgent/1.0',
            ip_address='192.168.1.1'
        )

        assert session is not None
        assert session['session_id'] == 'test_session_001'
        assert session['account_id'] == 'ACC123'
        assert session['transaction_count'] == 0
        assert session['total_amount'] == 0.0
        assert session['risk_score'] == 0.0
        assert session['is_terminated'] == 0

    def test_create_duplicate_session(self, monitor):
        """Test creating session with duplicate ID returns existing"""
        session1 = monitor.create_session('test_001', 'ACC123')
        session2 = monitor.create_session('test_001', 'ACC123')

        assert session1['session_id'] == session2['session_id']

    def test_get_session_exists(self, monitor):
        """Test retrieving an existing session"""
        monitor.create_session('test_002', 'ACC456')
        session = monitor.get_session('test_002')

        assert session is not None
        assert session['session_id'] == 'test_002'
        assert session['account_id'] == 'ACC456'

    def test_get_session_not_exists(self, monitor):
        """Test retrieving non-existent session returns None"""
        session = monitor.get_session('nonexistent')
        assert session is None


class TestSessionUpdates:
    """Test session update operations"""

    def test_update_session_metrics(self, monitor):
        """Test updating session transaction count and amount"""
        monitor.create_session('test_003', 'ACC789')
        
        monitor.update_session(
            session_id='test_003',
            transaction_count=5,
            total_amount=12500.0,
            risk_score=25.5
        )

        session = monitor.get_session('test_003')
        assert session['transaction_count'] == 5
        assert session['total_amount'] == 12500.0
        assert session['risk_score'] == 25.5

    def test_update_nonexistent_session(self, monitor):
        """Test updating non-existent session does nothing"""
        # Should not raise an error
        monitor.update_session(
            session_id='nonexistent',
            transaction_count=10
        )

    def test_update_anomalies(self, monitor):
        """Test updating session anomalies list"""
        monitor.create_session('test_004', 'ACC100')
        
        anomalies = ['amount_spike:5000', 'velocity_high:10_txns']
        monitor.update_session(
            session_id='test_004',
            anomalies=anomalies
        )

        session = monitor.get_session('test_004')
        assert session['anomalies'] == '["amount_spike:5000", "velocity_high:10_txns"]'


class TestSessionTermination:
    """Test session termination"""

    def test_terminate_session(self, monitor):
        """Test terminating an active session"""
        monitor.create_session('test_005', 'ACC200')
        
        result = monitor.terminate_session(
            session_id='test_005',
            reason='High risk detected'
        )

        assert result is True
        session = monitor.get_session('test_005')
        assert session['is_terminated'] == 1
        assert session['termination_reason'] == 'High risk detected'
        assert session['terminated_at'] is not None

    def test_terminate_nonexistent_session(self, monitor):
        """Test terminating non-existent session returns False"""
        result = monitor.terminate_session('nonexistent', 'test')
        assert result is False

    def test_terminate_already_terminated(self, monitor):
        """Test terminating already terminated session"""
        monitor.create_session('test_006', 'ACC300')
        monitor.terminate_session('test_006', 'First termination')
        
        # Terminating again should still return True
        result = monitor.terminate_session('test_006', 'Second termination')
        assert result is True


class TestSessionRetrieval:
    """Test session retrieval methods"""

    def test_get_active_sessions(self, monitor):
        """Test retrieving active sessions"""
        # Create mix of active and terminated sessions
        monitor.create_session('active_001', 'ACC1')
        monitor.create_session('active_002', 'ACC2')
        monitor.create_session('terminated_001', 'ACC3')
        monitor.terminate_session('terminated_001', 'Test')

        active = monitor.get_active_sessions(limit=100)
        
        assert len(active) == 2
        assert all(s['is_terminated'] == 0 for s in active)
        session_ids = [s['session_id'] for s in active]
        assert 'active_001' in session_ids
        assert 'active_002' in session_ids
        assert 'terminated_001' not in session_ids

    def test_get_active_sessions_with_limit(self, monitor):
        """Test active sessions respects limit"""
        for i in range(10):
            monitor.create_session(f'session_{i}', f'ACC{i}')

        active = monitor.get_active_sessions(limit=5)
        assert len(active) == 5

    def test_get_sessions_by_account(self, monitor):
        """Test retrieving sessions for specific account"""
        monitor.create_session('s1', 'ACC_ALPHA')
        monitor.create_session('s2', 'ACC_ALPHA')
        monitor.create_session('s3', 'ACC_BETA')

        sessions = monitor.get_sessions_by_account('ACC_ALPHA')
        
        assert len(sessions) == 2
        assert all(s['account_id'] == 'ACC_ALPHA' for s in sessions)

    def test_get_sessions_by_account_none_found(self, monitor):
        """Test retrieving sessions for account with no sessions"""
        sessions = monitor.get_sessions_by_account('NONEXISTENT')
        assert len(sessions) == 0


class TestSessionEvents:
    """Test session event recording"""

    def test_add_event(self, monitor):
        """Test adding an event to a session"""
        monitor.create_session('test_007', 'ACC400')
        
        event_id = monitor.add_event(
            session_id='test_007',
            event_type='transaction',
            transaction_data={'amount': 5000, 'beneficiary': 'BEN123'},
            risk_score=15.0
        )

        assert event_id is not None
        assert isinstance(event_id, int)

    def test_add_event_with_anomalies(self, monitor):
        """Test adding event with anomalies"""
        monitor.create_session('test_008', 'ACC500')
        
        event_id = monitor.add_event(
            session_id='test_008',
            event_type='transaction',
            transaction_data={'amount': 50000},
            risk_score=75.0,
            anomalies=['amount_spike:50000']
        )

        assert event_id is not None

    def test_get_session_events(self, monitor):
        """Test retrieving events for a session"""
        monitor.create_session('test_009', 'ACC600')
        
        # Add multiple events
        monitor.add_event('test_009', 'transaction', {'amount': 1000}, 10.0)
        monitor.add_event('test_009', 'transaction', {'amount': 2000}, 20.0)
        monitor.add_event('test_009', 'transaction', {'amount': 3000}, 30.0)

        events = monitor.get_session_events('test_009', limit=10)
        
        assert len(events) == 3
        # Events should be ordered by timestamp (most recent first by default)
        assert all('session_id' in e for e in events)


class TestSessionCleanup:
    """Test session cleanup operations"""

    def test_cleanup_old_sessions(self, monitor):
        """Test cleaning up old sessions"""
        # Create an old session by manipulating the database directly
        monitor.create_session('old_session', 'ACC_OLD')
        
        # Manually update created_at to be old (48 hours ago)
        old_time = (datetime.now() - timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')
        with monitor._get_connection() as conn:
            conn.execute(
                'UPDATE session_behaviors SET created_at = ? WHERE session_id = ?',
                (old_time, 'old_session')
            )
            conn.commit()

        # Create a recent session
        monitor.create_session('new_session', 'ACC_NEW')

        # Cleanup sessions older than 24 hours
        deleted = monitor.cleanup_old_sessions(hours=24)

        # Old session should be deleted, new one should remain
        assert deleted >= 1
        assert monitor.get_session('old_session') is None
        assert monitor.get_session('new_session') is not None

    def test_cleanup_no_old_sessions(self, monitor):
        """Test cleanup when no old sessions exist"""
        monitor.create_session('recent', 'ACC_RECENT')
        
        deleted = monitor.cleanup_old_sessions(hours=24)
        
        # No sessions should be deleted
        assert deleted == 0
        assert monitor.get_session('recent') is not None


class TestDatabaseIntegrity:
    """Test database integrity and constraints"""

    def test_session_count(self, monitor):
        """Test counting sessions"""
        for i in range(5):
            monitor.create_session(f'count_test_{i}', f'ACC{i}')

        active = monitor.get_active_sessions(limit=100)
        assert len(active) == 5

    def test_concurrent_updates(self, monitor):
        """Test multiple updates to same session"""
        monitor.create_session('concurrent_test', 'ACC_CONCURRENT')
        
        # Multiple rapid updates
        for i in range(10):
            monitor.update_session(
                session_id='concurrent_test',
                transaction_count=i + 1,
                risk_score=float(i * 10)
            )

        session = monitor.get_session('concurrent_test')
        assert session['transaction_count'] == 10
        assert session['risk_score'] == 90.0

    def test_anomalies_json_format(self, monitor):
        """Test anomalies are stored as valid JSON"""
        import json
        
        monitor.create_session('json_test', 'ACC_JSON')
        
        anomalies = ['test1:value1', 'test2:value2', 'test3:value3']
        monitor.update_session('json_test', anomalies=anomalies)

        session = monitor.get_session('json_test')
        parsed = json.loads(session['anomalies'])
        
        assert isinstance(parsed, list)
        assert len(parsed) == 3
        assert parsed == anomalies


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_session_id(self, monitor):
        """Test handling empty session ID"""
        session = monitor.create_session('', 'ACC_EMPTY')
        # Should still create session with empty ID (unusual but valid)
        assert session is not None

    def test_very_long_session_id(self, monitor):
        """Test handling very long session ID"""
        long_id = 'x' * 500
        session = monitor.create_session(long_id, 'ACC_LONG')
        assert session is not None
        assert session['session_id'] == long_id

    def test_special_characters_in_data(self, monitor):
        """Test handling special characters"""
        monitor.create_session('special_test', "ACC'WITH'QUOTES")
        session = monitor.get_session('special_test')
        assert session is not None

    def test_negative_values(self, monitor):
        """Test handling negative values"""
        monitor.create_session('negative_test', 'ACC_NEG')
        monitor.update_session(
            'negative_test',
            transaction_count=-1,  # Invalid but should be handled
            total_amount=-5000.0,
            risk_score=-10.0
        )
        
        session = monitor.get_session('negative_test')
        # Values should be stored as-is (validation is done at higher level)
        assert session is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
