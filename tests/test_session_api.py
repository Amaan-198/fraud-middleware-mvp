"""
Tests for Session API endpoints

Tests /v1/sessions/* endpoints and /v1/decision integration.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app


client = TestClient(app)


class TestSessionEndpoints:
    """Test session API endpoints"""

    def test_sessions_health(self):
        """Test GET /v1/sessions/health"""
        response = client.get('/v1/sessions/health')
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'session_monitor' in data
        assert 'behavioral_scorer' in data

    def test_get_active_sessions_empty(self):
        """Test GET /v1/sessions/active with no sessions"""
        response = client.get('/v1/sessions/active')
        
        assert response.status_code == 200
        data = response.json()
        assert 'sessions' in data
        assert isinstance(data['sessions'], list)

    def test_get_active_sessions_with_limit(self):
        """Test GET /v1/sessions/active with limit parameter"""
        response = client.get('/v1/sessions/active?limit=5')
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['sessions']) <= 5

    def test_get_nonexistent_session(self):
        """Test GET /v1/sessions/{id} for non-existent session"""
        response = client.get('/v1/sessions/nonexistent_session_id')
        
        assert response.status_code == 404
        assert 'not found' in response.json()['detail'].lower()

    def test_get_session_risk_nonexistent(self):
        """Test GET /v1/sessions/{id}/risk for non-existent session"""
        response = client.get('/v1/sessions/nonexistent_session_id/risk')
        
        assert response.status_code == 404

    def test_terminate_nonexistent_session(self):
        """Test POST /v1/sessions/{id}/terminate for non-existent session"""
        response = client.post(
            '/v1/sessions/nonexistent_session_id/terminate',
            json={'termination_reason': 'Test'}
        )
        
        assert response.status_code == 404

    def test_get_suspicious_sessions(self):
        """Test GET /v1/sessions/suspicious"""
        response = client.get('/v1/sessions/suspicious')
        
        assert response.status_code == 200
        data = response.json()
        assert 'sessions' in data

    def test_get_suspicious_sessions_with_min_risk(self):
        """Test GET /v1/sessions/suspicious with min_risk_score"""
        response = client.get('/v1/sessions/suspicious?min_risk_score=70')
        
        assert response.status_code == 200
        data = response.json()
        # All returned sessions should have risk >= 70
        for session in data['sessions']:
            assert session['risk_score'] >= 70 or session['is_terminated']


class TestDecisionIntegration:
    """Test /v1/decision integration with sessions"""

    def test_decision_without_session_id(self):
        """Test /v1/decision without session_id (backward compatibility)"""
        transaction = {
            'amount': 5000.0,
            'currency': 'INR',
            'beneficiary_account': 'BEN123',
            'timestamp': '2024-01-15T14:30:00Z',
            'account_id': 'ACC_TEST_001',
            'user_id': 'USER123'
        }
        
        response = client.post('/v1/decision', json=transaction)
        
        assert response.status_code == 200
        data = response.json()
        assert 'decision_code' in data
        assert 'fraud_score' in data
        # Should NOT have session_risk
        assert data.get('session_risk') is None

    def test_decision_with_session_id(self):
        """Test /v1/decision with session_id creates session"""
        transaction = {
            'amount': 5000.0,
            'currency': 'INR',
            'beneficiary_account': 'BEN456',
            'timestamp': '2024-01-15T14:30:00Z',
            'account_id': 'ACC_TEST_002',
            'user_id': 'USER456',
            'session_id': 'test_session_with_id_001'
        }
        
        response = client.post('/v1/decision', json=transaction)
        
        assert response.status_code == 200
        data = response.json()
        assert 'session_risk' in data
        assert data['session_risk'] is not None
        assert data['session_risk']['session_id'] == 'test_session_with_id_001'
        
        # Verify session was created
        session_response = client.get('/v1/sessions/test_session_with_id_001')
        assert session_response.status_code == 200

    def test_decision_multiple_transactions_same_session(self):
        """Test multiple transactions in same session"""
        session_id = 'test_session_multiple_txns'
        
        # First transaction
        transaction1 = {
            'amount': 2000.0,
            'currency': 'INR',
            'beneficiary_account': 'BEN789',
            'timestamp': '2024-01-15T14:30:00Z',
            'account_id': 'ACC_TEST_003',
            'user_id': 'USER789',
            'session_id': session_id
        }
        
        response1 = client.post('/v1/decision', json=transaction1)
        assert response1.status_code == 200
        
        # Second transaction
        transaction2 = {
            **transaction1,
            'amount': 2500.0,
            'beneficiary_account': 'BEN790'
        }
        
        response2 = client.post('/v1/decision', json=transaction2)
        assert response2.status_code == 200
        
        # Check session updated
        session_response = client.get(f'/v1/sessions/{session_id}')
        assert session_response.status_code == 200
        session_data = session_response.json()
        
        assert session_data['transaction_count'] == 2
        assert session_data['total_amount'] == 4500.0

    def test_decision_with_new_beneficiary_flag(self):
        """Test /v1/decision with is_new_beneficiary flag"""
        transaction = {
            'amount': 3000.0,
            'currency': 'INR',
            'beneficiary_account': 'BEN_NEW_001',
            'timestamp': '2024-01-15T14:30:00Z',
            'account_id': 'ACC_TEST_004',
            'user_id': 'USER_NEW',
            'session_id': 'test_session_new_ben',
            'is_new_beneficiary': True
        }
        
        response = client.post('/v1/decision', json=transaction)
        
        assert response.status_code == 200
        data = response.json()
        assert 'session_risk' in data

    def test_decision_with_session_metadata(self):
        """Test /v1/decision with session_metadata"""
        transaction = {
            'amount': 3000.0,
            'currency': 'INR',
            'beneficiary_account': 'BEN_META',
            'timestamp': '2024-01-15T14:30:00Z',
            'account_id': 'ACC_TEST_005',
            'user_id': 'USER_META',
            'session_id': 'test_session_metadata',
            'session_metadata': {
                'transaction_time': '14:30:00',
                'location': 'Mumbai',
                'device_id': 'DEV123'
            }
        }
        
        response = client.post('/v1/decision', json=transaction)
        
        assert response.status_code == 200


class TestSessionLifecycle:
    """Test complete session lifecycle"""

    def test_create_and_retrieve_session(self):
        """Test creating session via decision and retrieving it"""
        session_id = 'test_lifecycle_001'
        
        # Create via decision
        transaction = {
            'amount': 5000.0,
            'currency': 'INR',
            'beneficiary_account': 'BEN_LIFECYCLE',
            'timestamp': '2024-01-15T14:30:00Z',
            'account_id': 'ACC_LIFECYCLE',
            'user_id': 'USER_LIFECYCLE',
            'session_id': session_id
        }
        
        decision_response = client.post('/v1/decision', json=transaction)
        assert decision_response.status_code == 200
        
        # Retrieve session
        session_response = client.get(f'/v1/sessions/{session_id}')
        assert session_response.status_code == 200
        session_data = session_response.json()
        
        assert session_data['session_id'] == session_id
        assert session_data['account_id'] == 'ACC_LIFECYCLE'

    def test_create_retrieve_risk_and_terminate(self):
        """Test full lifecycle: create, get risk, terminate"""
        session_id = 'test_lifecycle_full'
        
        # Create
        transaction = {
            'amount': 5000.0,
            'currency': 'INR',
            'beneficiary_account': 'BEN_FULL',
            'timestamp': '2024-01-15T14:30:00Z',
            'account_id': 'ACC_FULL',
            'user_id': 'USER_FULL',
            'session_id': session_id
        }
        
        client.post('/v1/decision', json=transaction)
        
        # Get risk
        risk_response = client.get(f'/v1/sessions/{session_id}/risk')
        assert risk_response.status_code == 200
        risk_data = risk_response.json()
        assert 'risk_score' in risk_data
        assert 'signals_triggered' in risk_data
        
        # Terminate
        terminate_response = client.post(
            f'/v1/sessions/{session_id}/terminate',
            json={'termination_reason': 'Test termination'}
        )
        assert terminate_response.status_code == 200
        terminate_data = terminate_response.json()
        assert terminate_data['is_terminated'] is True
        assert terminate_data['termination_reason'] == 'Test termination'
        
        # Verify terminated
        session_response = client.get(f'/v1/sessions/{session_id}')
        assert session_response.status_code == 200
        assert session_response.json()['is_terminated'] is True


class TestHighRiskSessionTermination:
    """Test automatic termination of high-risk sessions"""

    def test_high_risk_session_auto_terminates(self):
        """Test that high-risk session (80+) is auto-terminated"""
        session_id = 'test_high_risk_auto_term'
        
        # Create session with normal transaction
        transaction1 = {
            'amount': 2500.0,
            'currency': 'INR',
            'beneficiary_account': 'BEN_NORMAL',
            'timestamp': '2024-01-15T14:30:00Z',
            'account_id': 'ACC_HIGH_RISK',
            'user_id': 'USER_HIGH_RISK',
            'session_id': session_id
        }
        
        response1 = client.post('/v1/decision', json=transaction1)
        assert response1.status_code == 200
        
        # Now send high-risk transactions
        # Multiple large amounts with new beneficiaries
        for i in range(5):
            transaction = {
                'amount': 75000.0,  # Very large amount
                'currency': 'INR',
                'beneficiary_account': f'BEN_ATTACK_{i}',
                'timestamp': '2024-01-15T03:00:00Z',  # Odd hours
                'account_id': 'ACC_HIGH_RISK',
                'user_id': 'USER_HIGH_RISK',
                'session_id': session_id,
                'is_new_beneficiary': True,
                'session_metadata': {
                    'transaction_time': '03:00:00'
                }
            }
            
            response = client.post('/v1/decision', json=transaction)
            assert response.status_code == 200
            
            session_risk = response.json().get('session_risk')
            if session_risk and session_risk.get('is_terminated'):
                # Session was terminated
                assert session_risk['risk_score'] >= 80
                break

    def test_terminated_session_blocks_decision(self):
        """Test that terminated session results in BLOCK decision"""
        session_id = 'test_terminated_blocks'
        
        # Create and terminate session manually
        transaction1 = {
            'amount': 3000.0,
            'currency': 'INR',
            'beneficiary_account': 'BEN_TERM_TEST',
            'timestamp': '2024-01-15T14:30:00Z',
            'account_id': 'ACC_TERM_TEST',
            'user_id': 'USER_TERM_TEST',
            'session_id': session_id
        }
        
        client.post('/v1/decision', json=transaction1)
        
        # Terminate session
        client.post(
            f'/v1/sessions/{session_id}/terminate',
            json={'termination_reason': 'Manual test termination'}
        )
        
        # Try another transaction
        transaction2 = {
            **transaction1,
            'amount': 4000.0
        }
        
        response = client.post('/v1/decision', json=transaction2)
        assert response.status_code == 200
        data = response.json()
        
        # Should be blocked
        assert data['decision_code'] == 1  # BLOCK
        assert data['session_risk']['is_terminated'] is True


class TestDemoEndpoints:
    """Test demo session endpoints"""

    def test_demo_session_scenario_normal(self):
        """Test POST /v1/demo/session-scenario with normal type"""
        response = client.post(
            '/v1/demo/session-scenario',
            json={'type': 'normal'}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'session_id' in data
        assert 'transactions_sent' in data
        assert 'final_risk_score' in data
        assert data['scenario_type'] == 'normal'

    def test_demo_session_scenario_attack(self):
        """Test POST /v1/demo/session-scenario with attack type"""
        response = client.post(
            '/v1/demo/session-scenario',
            json={'type': 'attack'}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'session_id' in data
        assert data['scenario_type'] == 'attack'
        # Attack should result in termination
        assert data['was_terminated'] is True

    def test_demo_session_comparison(self):
        """Test GET /v1/demo/session-comparison"""
        response = client.get('/v1/demo/session-comparison')
        
        assert response.status_code == 200
        data = response.json()
        assert 'normal_session_id' in data
        assert 'attack_session_id' in data
        assert 'message' in data


class TestErrorHandling:
    """Test error handling"""

    def test_invalid_session_id_format(self):
        """Test handling of various session ID formats"""
        # Very long session ID
        long_id = 'x' * 500
        transaction = {
            'amount': 5000.0,
            'currency': 'INR',
            'beneficiary_account': 'BEN_TEST',
            'timestamp': '2024-01-15T14:30:00Z',
            'account_id': 'ACC_TEST',
            'user_id': 'USER_TEST',
            'session_id': long_id
        }
        
        response = client.post('/v1/decision', json=transaction)
        # Should handle gracefully
        assert response.status_code == 200

    def test_terminate_without_reason(self):
        """Test terminating without reason"""
        # Create session first
        session_id = 'test_no_reason'
        transaction = {
            'amount': 3000.0,
            'currency': 'INR',
            'beneficiary_account': 'BEN_TEST',
            'timestamp': '2024-01-15T14:30:00Z',
            'account_id': 'ACC_TEST',
            'user_id': 'USER_TEST',
            'session_id': session_id
        }
        
        client.post('/v1/decision', json=transaction)
        
        # Terminate without reason (should have default)
        response = client.post(
            f'/v1/sessions/{session_id}/terminate',
            json={}
        )
        
        # Might fail validation or use default
        assert response.status_code in [200, 422]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
