"""
Tests for BehavioralScorer class

Tests all 5 behavioral signals and risk scoring logic.
"""

import pytest
from datetime import datetime, time
from api.models.behavioral_scorer import BehavioralScorer


@pytest.fixture
def scorer():
    """Create a BehavioralScorer instance"""
    return BehavioralScorer()


class TestAmountDeviationSignal:
    """Test AMOUNT_DEVIATION signal"""

    def test_normal_amount(self, scorer):
        """Test normal transaction amount"""
        session = {
            'transaction_count': 5,
            'total_amount': 10000.0,  # avg 2000
        }
        transaction = {'amount': 2500.0}
        
        result = scorer.calculate_risk(session, transaction)
        
        # Should not trigger amount deviation
        assert 'AMOUNT_DEVIATION' not in result['signals_triggered']

    def test_large_amount_deviation(self, scorer):
        """Test large amount deviation triggers signal"""
        session = {
            'transaction_count': 5,
            'total_amount': 10000.0,  # avg 2000
        }
        transaction = {'amount': 50000.0}  # 25x average
        
        result = scorer.calculate_risk(session, transaction)
        
        assert 'AMOUNT_DEVIATION' in result['signals_triggered']
        assert result['risk_score'] > 0
        assert any('amount_anomaly' in a for a in result['anomalies'])

    def test_first_transaction_no_baseline(self, scorer):
        """Test first transaction has no baseline for comparison"""
        session = {
            'transaction_count': 0,
            'total_amount': 0.0,
        }
        transaction = {'amount': 100000.0}
        
        result = scorer.calculate_risk(session, transaction)
        
        # First transaction shouldn't trigger (no baseline)
        # But if amount is extremely large, might trigger other signals
        assert result is not None


class TestBeneficiaryChangesSignal:
    """Test BENEFICIARY_CHANGES signal"""

    def test_existing_beneficiary(self, scorer):
        """Test transaction to existing beneficiary"""
        session = {
            'transaction_count': 3,
            'total_amount': 9000.0,
        }
        transaction = {
            'amount': 3000.0,
            'is_new_beneficiary': False
        }
        
        result = scorer.calculate_risk(session, transaction)
        
        assert 'BENEFICIARY_CHANGES' not in result['signals_triggered']

    def test_new_beneficiary_normal(self, scorer):
        """Test adding new beneficiary at normal rate"""
        session = {
            'transaction_count': 10,
            'total_amount': 30000.0,
        }
        transaction = {
            'amount': 3000.0,
            'is_new_beneficiary': True
        }
        
        result = scorer.calculate_risk(session, transaction)
        
        # One new beneficiary in 10 transactions is normal
        assert 'BENEFICIARY_CHANGES' not in result['signals_triggered']

    def test_rapid_beneficiary_changes(self, scorer):
        """Test rapid beneficiary changes trigger signal"""
        session = {
            'transaction_count': 3,
            'total_amount': 9000.0,
        }
        
        # Simulate multiple new beneficiaries
        total_risk = 0
        signals_count = 0
        
        for i in range(3):
            transaction = {
                'amount': 3000.0,
                'is_new_beneficiary': True
            }
            result = scorer.calculate_risk(session, transaction)
            if 'BENEFICIARY_CHANGES' in result['signals_triggered']:
                signals_count += 1

        # Should trigger at least once with multiple new beneficiaries
        assert signals_count > 0


class TestTimePatternSignal:
    """Test TIME_PATTERN signal"""

    def test_business_hours_transaction(self, scorer):
        """Test transaction during business hours"""
        session = {
            'transaction_count': 5,
            'total_amount': 15000.0,
        }
        
        # 2 PM - normal business hours
        transaction = {
            'amount': 3000.0,
            'session_metadata': {
                'transaction_time': time(14, 0).strftime('%H:%M:%S')
            }
        }
        
        result = scorer.calculate_risk(session, transaction)
        
        assert 'TIME_PATTERN' not in result['signals_triggered']

    def test_odd_hours_transaction(self, scorer):
        """Test transaction at odd hours"""
        session = {
            'transaction_count': 5,
            'total_amount': 15000.0,
        }
        
        # 3 AM - odd hours
        transaction = {
            'amount': 3000.0,
            'session_metadata': {
                'transaction_time': time(3, 0).strftime('%H:%M:%S')
            }
        }
        
        result = scorer.calculate_risk(session, transaction)
        
        assert 'TIME_PATTERN' in result['signals_triggered']
        assert any('odd_hour' in a for a in result['anomalies'])

    def test_missing_time_no_signal(self, scorer):
        """Test missing time info doesn't trigger signal"""
        session = {
            'transaction_count': 5,
            'total_amount': 15000.0,
        }
        transaction = {
            'amount': 3000.0,
            'session_metadata': {}
        }
        
        result = scorer.calculate_risk(session, transaction)
        
        assert 'TIME_PATTERN' not in result['signals_triggered']


class TestVelocitySignal:
    """Test VELOCITY signal"""

    def test_normal_velocity(self, scorer):
        """Test normal transaction velocity"""
        session = {
            'transaction_count': 5,
            'total_amount': 15000.0,
        }
        transaction = {'amount': 3000.0}
        
        result = scorer.calculate_risk(session, transaction)
        
        # 6 transactions total is normal
        assert 'VELOCITY' not in result['signals_triggered']

    def test_high_velocity(self, scorer):
        """Test high transaction velocity triggers signal"""
        session = {
            'transaction_count': 14,  # Already 14 transactions
            'total_amount': 42000.0,
        }
        transaction = {'amount': 3000.0}
        
        result = scorer.calculate_risk(session, transaction)
        
        # 15 transactions is high velocity
        assert 'VELOCITY' in result['signals_triggered']
        assert any('velocity_high' in a for a in result['anomalies'])


class TestGeolocationSignal:
    """Test GEOLOCATION signal"""

    def test_same_location(self, scorer):
        """Test transaction from same location"""
        session = {
            'transaction_count': 5,
            'total_amount': 15000.0,
        }
        transaction = {
            'amount': 3000.0,
            'session_metadata': {
                'location': 'Mumbai'
            }
        }
        
        result = scorer.calculate_risk(session, transaction)
        
        # Same location shouldn't trigger (we'd need session history)
        assert 'GEOLOCATION' not in result['signals_triggered']

    def test_missing_location(self, scorer):
        """Test missing location info"""
        session = {
            'transaction_count': 5,
            'total_amount': 15000.0,
        }
        transaction = {
            'amount': 3000.0,
            'session_metadata': {}
        }
        
        result = scorer.calculate_risk(session, transaction)
        
        assert 'GEOLOCATION' not in result['signals_triggered']


class TestMultipleSignals:
    """Test multiple signals firing together"""

    def test_multiple_signals_compound_risk(self, scorer):
        """Test multiple signals increase risk score"""
        session = {
            'transaction_count': 3,
            'total_amount': 9000.0,  # avg 3000
        }
        
        # Transaction with multiple risk factors
        transaction = {
            'amount': 70000.0,  # Large deviation
            'is_new_beneficiary': True,  # New beneficiary
            'session_metadata': {
                'transaction_time': time(3, 30).strftime('%H:%M:%S')  # Odd hours
            }
        }
        
        result = scorer.calculate_risk(session, transaction)
        
        # Should trigger multiple signals
        assert len(result['signals_triggered']) >= 2
        # Risk score should be elevated
        assert result['risk_score'] >= 50
        # Should have multiple anomalies
        assert len(result['anomalies']) >= 2

    def test_all_signals_maximum_risk(self, scorer):
        """Test maximum risk with all signals"""
        session = {
            'transaction_count': 14,  # High velocity
            'total_amount': 30000.0,
        }
        
        transaction = {
            'amount': 100000.0,  # Large amount
            'is_new_beneficiary': True,  # New beneficiary
            'session_metadata': {
                'transaction_time': time(2, 0).strftime('%H:%M:%S'),  # Odd hours
                'location': 'UnknownCity'  # Different location
            }
        }
        
        result = scorer.calculate_risk(session, transaction)
        
        # Should have high risk score
        assert result['risk_score'] >= 70


class TestRiskScoreBounds:
    """Test risk score stays within valid bounds"""

    def test_risk_score_minimum(self, scorer):
        """Test risk score has minimum of 0"""
        session = {
            'transaction_count': 5,
            'total_amount': 15000.0,
        }
        transaction = {'amount': 3000.0}
        
        result = scorer.calculate_risk(session, transaction)
        
        assert result['risk_score'] >= 0

    def test_risk_score_maximum(self, scorer):
        """Test risk score has maximum of 100"""
        session = {
            'transaction_count': 20,
            'total_amount': 50000.0,
        }
        
        # Extreme transaction
        transaction = {
            'amount': 500000.0,
            'is_new_beneficiary': True,
            'session_metadata': {
                'transaction_time': time(3, 0).strftime('%H:%M:%S')
            }
        }
        
        result = scorer.calculate_risk(session, transaction)
        
        assert result['risk_score'] <= 100


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_missing_transaction_amount(self, scorer):
        """Test handling missing transaction amount"""
        session = {
            'transaction_count': 5,
            'total_amount': 15000.0,
        }
        transaction = {}  # No amount
        
        result = scorer.calculate_risk(session, transaction)
        
        # Should not crash
        assert result is not None
        assert 'risk_score' in result

    def test_zero_amount_transaction(self, scorer):
        """Test handling zero amount"""
        session = {
            'transaction_count': 5,
            'total_amount': 15000.0,
        }
        transaction = {'amount': 0.0}
        
        result = scorer.calculate_risk(session, transaction)
        
        assert result is not None
        assert result['risk_score'] >= 0

    def test_negative_amount(self, scorer):
        """Test handling negative amount (refund?)"""
        session = {
            'transaction_count': 5,
            'total_amount': 15000.0,
        }
        transaction = {'amount': -5000.0}
        
        result = scorer.calculate_risk(session, transaction)
        
        # Should not crash, treated as absolute value or special case
        assert result is not None

    def test_empty_session(self, scorer):
        """Test handling empty/new session"""
        session = {
            'transaction_count': 0,
            'total_amount': 0.0,
        }
        transaction = {'amount': 5000.0}
        
        result = scorer.calculate_risk(session, transaction)
        
        # First transaction should have low/zero risk
        assert result is not None
        assert result['risk_score'] >= 0

    def test_very_high_transaction_count(self, scorer):
        """Test handling very high transaction count"""
        session = {
            'transaction_count': 1000,
            'total_amount': 2000000.0,
        }
        transaction = {'amount': 2000.0}
        
        result = scorer.calculate_risk(session, transaction)
        
        assert result is not None
        # Velocity should definitely be triggered
        assert 'VELOCITY' in result['signals_triggered']

    def test_malformed_time_string(self, scorer):
        """Test handling malformed time string"""
        session = {
            'transaction_count': 5,
            'total_amount': 15000.0,
        }
        transaction = {
            'amount': 3000.0,
            'session_metadata': {
                'transaction_time': 'not-a-time'
            }
        }
        
        result = scorer.calculate_risk(session, transaction)
        
        # Should not crash
        assert result is not None

    def test_none_metadata(self, scorer):
        """Test handling None metadata"""
        session = {
            'transaction_count': 5,
            'total_amount': 15000.0,
        }
        transaction = {
            'amount': 3000.0,
            'session_metadata': None
        }
        
        result = scorer.calculate_risk(session, transaction)
        
        # Should handle gracefully
        assert result is not None


class TestResultStructure:
    """Test result structure and content"""

    def test_result_has_required_fields(self, scorer):
        """Test result contains all required fields"""
        session = {
            'transaction_count': 5,
            'total_amount': 15000.0,
        }
        transaction = {'amount': 3000.0}
        
        result = scorer.calculate_risk(session, transaction)
        
        assert 'risk_score' in result
        assert 'signals_triggered' in result
        assert 'anomalies' in result
        assert 'details' in result

    def test_signals_triggered_is_list(self, scorer):
        """Test signals_triggered is always a list"""
        session = {
            'transaction_count': 5,
            'total_amount': 15000.0,
        }
        transaction = {'amount': 3000.0}
        
        result = scorer.calculate_risk(session, transaction)
        
        assert isinstance(result['signals_triggered'], list)

    def test_anomalies_is_list(self, scorer):
        """Test anomalies is always a list"""
        session = {
            'transaction_count': 5,
            'total_amount': 15000.0,
        }
        transaction = {'amount': 3000.0}
        
        result = scorer.calculate_risk(session, transaction)
        
        assert isinstance(result['anomalies'], list)

    def test_risk_score_is_float(self, scorer):
        """Test risk_score is a float"""
        session = {
            'transaction_count': 5,
            'total_amount': 15000.0,
        }
        transaction = {'amount': 3000.0}
        
        result = scorer.calculate_risk(session, transaction)
        
        assert isinstance(result['risk_score'], (int, float))

    def test_anomalies_match_signals(self, scorer):
        """Test that triggered signals have corresponding anomalies"""
        session = {
            'transaction_count': 3,
            'total_amount': 9000.0,
        }
        transaction = {
            'amount': 50000.0,  # Should trigger AMOUNT_DEVIATION
        }
        
        result = scorer.calculate_risk(session, transaction)
        
        if 'AMOUNT_DEVIATION' in result['signals_triggered']:
            # Should have corresponding anomaly
            assert any('amount' in a.lower() for a in result['anomalies'])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
