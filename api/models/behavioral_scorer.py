"""
Behavioral Scorer - Risk Scoring Engine for Session Monitoring

Analyzes session behavior patterns to detect anomalies and calculate risk scores.

Based on 5 behavioral signals:
1. TRANSACTION_VELOCITY - Frequency of transactions
2. AMOUNT_DEVIATION - Unusual transaction amounts
3. BENEFICIARY_CHANGES - New beneficiaries added
4. TIME_OF_DAY_ANOMALY - Off-hours activity
5. TRANSACTION_PATTERN - Excessive transaction count

Designed for integration with session monitoring and fraud detection pipeline.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from api.models.session_behavior import (
    SessionBehavior,
    SessionRiskScore,
    SessionRiskLevel,
    AnomalyType,
    get_session_age_minutes,
)

# Setup logging
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration and Baselines
# ============================================================================

# User behavioral baselines (MVP: hard-coded, future: per-user profiles)
USER_BASELINES = {
    "default": {
        "avg_transaction_amount": 2500.0,
        "active_hours_range": (9, 22),  # 9 AM to 10 PM
        "avg_transactions_per_session": 2,
        "typical_beneficiaries": 2,
        "avg_time_between_transactions": 60,  # seconds
    }
}

# Risk thresholds and weights for anomaly detection
RISK_THRESHOLDS = {
    # Transaction velocity
    "velocity_normal_min": 1,
    "velocity_normal_max": 3,
    "velocity_time_window_min": 2,  # minutes
    "velocity_anomaly_count": 5,  # transactions
    "velocity_score_per_excess": 20,
    
    # Amount deviation
    "amount_deviation_multiplier": 3.0,  # 3x average
    "amount_deviation_score": 30,
    
    # Beneficiary changes
    "beneficiary_score_per_new": 25,
    
    # Time of day
    "time_anomaly_score": 15,
    
    # Transaction pattern
    "pattern_deviation_multiplier": 2.0,  # 2x typical
    "pattern_deviation_score": 20,
    
    # Risk level thresholds
    "risk_low": 30,
    "risk_medium": 60,
    "risk_high": 80,
}


# ============================================================================
# Risk Score Data Model
# ============================================================================

@dataclass
class RiskScore:
    """
    Detailed risk score breakdown.
    
    Attributes:
        score: Overall risk score (0-100)
        signals_triggered: List of signal names that detected anomalies
        anomalies: List of anomaly descriptions
        details: Dictionary with component scores and metadata
    """
    score: float
    signals_triggered: List[str] = field(default_factory=list)
    anomalies: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def get_risk_level(self) -> SessionRiskLevel:
        """Get risk level classification"""
        if self.score >= RISK_THRESHOLDS["risk_high"]:
            return SessionRiskLevel.CRITICAL
        elif self.score >= RISK_THRESHOLDS["risk_medium"]:
            return SessionRiskLevel.HIGH
        elif self.score >= RISK_THRESHOLDS["risk_low"]:
            return SessionRiskLevel.MEDIUM
        else:
            return SessionRiskLevel.LOW


# ============================================================================
# Behavioral Scorer
# ============================================================================

class BehavioralScorer:
    """
    Behavioral risk scoring engine for session monitoring.
    
    Analyzes session behavior patterns and calculates risk scores based on
    multiple behavioral signals.
    """
    
    def __init__(
        self,
        baselines: Optional[Dict[str, Any]] = None,
        thresholds: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize behavioral scorer.
        
        Args:
            baselines: User behavioral baselines (default: USER_BASELINES)
            thresholds: Risk thresholds (default: RISK_THRESHOLDS)
        """
        self.baselines = baselines or USER_BASELINES
        self.thresholds = thresholds or RISK_THRESHOLDS
        
        logger.info("BehavioralScorer initialized")
    
    def calculate_risk(
        self,
        session: SessionBehavior,
        transaction_data: Optional[Dict[str, Any]] = None
    ) -> RiskScore:
        """
        Calculate risk score for a session based on behavioral signals.
        
        Args:
            session: SessionBehavior object
            transaction_data: Optional transaction data for context
        
        Returns:
            RiskScore object with detailed breakdown
        
        Example:
            >>> scorer = BehavioralScorer()
            >>> session = SessionBehavior(...)
            >>> risk = scorer.calculate_risk(session)
            >>> print(f"Risk: {risk.score}, Level: {risk.get_risk_level()}")
        """
        transaction_data = transaction_data or {}
        
        # Get baseline for this user (default for MVP)
        baseline = self._get_baseline(session.account_id)
        
        # Initialize risk score
        total_score = 0.0
        signals_triggered = []
        anomalies = []
        details = {}
        
        # Signal 1: Transaction Velocity
        velocity_score, velocity_anomalies = self._check_transaction_velocity(
            session, baseline, transaction_data
        )
        if velocity_score > 0:
            total_score += velocity_score
            signals_triggered.append("TRANSACTION_VELOCITY")
            anomalies.extend(velocity_anomalies)
        details["velocity_score"] = velocity_score
        
        # Signal 2: Amount Deviation
        amount_score, amount_anomalies = self._check_amount_deviation(
            session, baseline, transaction_data
        )
        if amount_score > 0:
            total_score += amount_score
            signals_triggered.append("AMOUNT_DEVIATION")
            anomalies.extend(amount_anomalies)
        details["amount_score"] = amount_score
        
        # Signal 3: Beneficiary Changes
        beneficiary_score, beneficiary_anomalies = self._check_beneficiary_changes(
            session, baseline
        )
        if beneficiary_score > 0:
            total_score += beneficiary_score
            signals_triggered.append("BENEFICIARY_CHANGES")
            anomalies.extend(beneficiary_anomalies)
        details["beneficiary_score"] = beneficiary_score
        
        # Signal 4: Time of Day Anomaly
        time_score, time_anomalies = self._check_time_of_day(
            session, baseline, transaction_data
        )
        if time_score > 0:
            total_score += time_score
            signals_triggered.append("TIME_OF_DAY_ANOMALY")
            anomalies.extend(time_anomalies)
        details["time_score"] = time_score
        
        # Signal 5: Transaction Pattern
        pattern_score, pattern_anomalies = self._check_transaction_pattern(
            session, baseline
        )
        if pattern_score > 0:
            total_score += pattern_score
            signals_triggered.append("TRANSACTION_PATTERN")
            anomalies.extend(pattern_anomalies)
        details["pattern_score"] = pattern_score
        
        # Clamp to [0, 100]
        total_score = max(0.0, min(100.0, total_score))
        
        # Create risk score object
        risk_score = RiskScore(
            score=total_score,
            signals_triggered=signals_triggered,
            anomalies=anomalies,
            details=details
        )
        
        logger.debug(
            f"Risk calculated for session {session.session_id}: "
            f"score={total_score:.1f}, signals={len(signals_triggered)}"
        )
        
        return risk_score
    
    def get_risk_explanation(self, session: SessionBehavior) -> str:
        """
        Generate human-readable risk explanation for a session.
        
        Args:
            session: SessionBehavior object
        
        Returns:
            Explanation string
        
        Example:
            >>> explanation = scorer.get_risk_explanation(session)
            >>> print(explanation)
            Session risk: HIGH (75.0). Anomalies detected: velocity_spike, ...
        """
        # Calculate current risk
        risk = self.calculate_risk(session)
        
        # Build explanation
        level = risk.get_risk_level().value.upper()
        explanation = f"Session risk: {level} ({risk.score:.1f}). "
        
        if risk.anomalies:
            explanation += f"Anomalies detected: {', '.join(risk.anomalies[:3])}"
            if len(risk.anomalies) > 3:
                explanation += f" (+{len(risk.anomalies) - 3} more)"
        else:
            explanation += "No anomalies detected."
        
        return explanation
    
    # ========================================================================
    # Internal Signal Detection Methods
    # ========================================================================
    
    def _get_baseline(self, account_id: str) -> Dict[str, Any]:
        """
        Get behavioral baseline for account.
        
        TODO: Implement per-user baselines from database/profile table.
        TODO: Use ML to learn user-specific patterns over time.
        
        Args:
            account_id: Account identifier
        
        Returns:
            Baseline dictionary
        """
        # MVP: Return default baseline for all users
        return self.baselines.get("default", {})
    
    def _check_transaction_velocity(
        self,
        session: SessionBehavior,
        baseline: Dict[str, Any],
        transaction_data: Dict[str, Any]
    ) -> Tuple[float, List[str]]:
        """
        Check transaction velocity anomaly.
        
        Normal: 1-3 transactions per session, 30-120 seconds between.
        Anomaly: 5+ transactions in under 2 minutes.
        Score: +20 per rapid transaction over normal pattern.
        
        Args:
            session: Session object
            baseline: Behavioral baseline
            transaction_data: Transaction context
        
        Returns:
            Tuple of (score, anomaly_descriptions)
        """
        score = 0.0
        anomalies = []
        
        # Check transaction count
        count = session.transaction_count
        velocity_max = self.thresholds["velocity_normal_max"]
        velocity_anomaly = self.thresholds["velocity_anomaly_count"]
        
        if count >= velocity_anomaly:
            # Calculate session age in minutes
            session_age_min = get_session_age_minutes(session)
            window = self.thresholds["velocity_time_window_min"]
            
            # Check if transactions are rapid
            if session_age_min < window:
                excess = count - velocity_max
                score = excess * self.thresholds["velocity_score_per_excess"]
                anomalies.append(
                    f"velocity_spike:{count}_txns_in_{session_age_min:.0f}_min"
                )
        
        return score, anomalies
    
    def _check_amount_deviation(
        self,
        session: SessionBehavior,
        baseline: Dict[str, Any],
        transaction_data: Dict[str, Any]
    ) -> Tuple[float, List[str]]:
        """
        Check for unusual transaction amounts.
        
        Normal: Transactions within user's typical range.
        Anomaly: Amount > 3x user's average.
        Score: +30 if threshold exceeded.
        
        Args:
            session: Session object
            baseline: Behavioral baseline
            transaction_data: Transaction context
        
        Returns:
            Tuple of (score, anomaly_descriptions)
        """
        score = 0.0
        anomalies = []
        
        # Get current transaction amount if available
        current_amount = transaction_data.get("amount", 0.0)
        
        # Calculate average transaction amount for session
        if session.transaction_count > 0:
            session_avg = session.total_amount / session.transaction_count
        else:
            session_avg = current_amount
        
        # Compare to baseline
        baseline_avg = baseline.get("avg_transaction_amount", 2500.0)
        multiplier = self.thresholds["amount_deviation_multiplier"]
        
        # Check if session average or current amount is anomalous
        if session_avg > baseline_avg * multiplier:
            score = self.thresholds["amount_deviation_score"]
            anomalies.append(
                f"amount_anomaly:avg_{session_avg:.0f}_vs_baseline_{baseline_avg:.0f}"
            )
        elif current_amount > baseline_avg * multiplier:
            score = self.thresholds["amount_deviation_score"]
            anomalies.append(
                f"amount_anomaly:current_{current_amount:.0f}_vs_baseline_{baseline_avg:.0f}"
            )
        
        return score, anomalies
    
    def _check_beneficiary_changes(
        self,
        session: SessionBehavior,
        baseline: Dict[str, Any]
    ) -> Tuple[float, List[str]]:
        """
        Check for beneficiary addition anomalies.
        
        Normal: Transfers to existing beneficiaries.
        Anomaly: Adding new beneficiaries mid-session.
        Score: +25 per new beneficiary added.
        
        Args:
            session: Session object
            baseline: Behavioral baseline
        
        Returns:
            Tuple of (score, anomaly_descriptions)
        """
        score = 0.0
        anomalies = []
        
        new_count = session.beneficiaries_added
        
        if new_count > 0:
            score = new_count * self.thresholds["beneficiary_score_per_new"]
            anomalies.append(f"beneficiary_spike:{new_count}_new_beneficiaries")
        
        return score, anomalies
    
    def _check_time_of_day(
        self,
        session: SessionBehavior,
        baseline: Dict[str, Any],
        transaction_data: Dict[str, Any]
    ) -> Tuple[float, List[str]]:
        """
        Check for off-hours activity.
        
        Normal: User's typical active hours (9 AM - 10 PM default).
        Anomaly: Activity during off-hours.
        Score: +15 for off-hours activity.
        
        Args:
            session: Session object
            baseline: Behavioral baseline
            transaction_data: Transaction context
        
        Returns:
            Tuple of (score, anomaly_descriptions)
        """
        score = 0.0
        anomalies = []
        
        # Get active hours range from baseline
        active_start, active_end = baseline.get("active_hours_range", (9, 22))
        
        # Check session login time
        login_dt = datetime.fromtimestamp(session.login_time, tz=timezone.utc)
        login_hour = login_dt.hour
        
        # Check if outside active hours
        is_off_hours = False
        if active_end > active_start:
            # Normal range (e.g., 9-22)
            is_off_hours = login_hour < active_start or login_hour >= active_end
        else:
            # Wrapped range (e.g., 22-6 for night shift)
            is_off_hours = active_start <= login_hour < active_end
        
        if is_off_hours:
            score = self.thresholds["time_anomaly_score"]
            anomalies.append(f"time_anomaly:activity_at_{login_hour:02d}00hrs")
        
        return score, anomalies
    
    def _check_transaction_pattern(
        self,
        session: SessionBehavior,
        baseline: Dict[str, Any]
    ) -> Tuple[float, List[str]]:
        """
        Check for unusual transaction patterns.
        
        Normal: User's typical transaction count per session.
        Anomaly: Excessive transactions (>2x typical).
        Score: +20 for significant pattern deviations.
        
        Args:
            session: Session object
            baseline: Behavioral baseline
        
        Returns:
            Tuple of (score, anomaly_descriptions)
        """
        score = 0.0
        anomalies = []
        
        count = session.transaction_count
        typical = baseline.get("avg_transactions_per_session", 2)
        multiplier = self.thresholds["pattern_deviation_multiplier"]
        
        if count > typical * multiplier:
            score = self.thresholds["pattern_deviation_score"]
            anomalies.append(
                f"pattern_anomaly:{count}_txns_vs_typical_{typical}"
            )
        
        return score, anomalies


# ============================================================================
# Utility Functions
# ============================================================================

def create_scorer_with_custom_thresholds(
    velocity_weight: Optional[float] = None,
    amount_weight: Optional[float] = None,
    beneficiary_weight: Optional[float] = None,
    time_weight: Optional[float] = None,
    pattern_weight: Optional[float] = None
) -> BehavioralScorer:
    """
    Create a behavioral scorer with custom threshold weights.
    
    This is a convenience function for tuning the scoring engine.
    
    Args:
        velocity_weight: Custom weight for velocity score (default: 20)
        amount_weight: Custom weight for amount score (default: 30)
        beneficiary_weight: Custom weight for beneficiary score (default: 25)
        time_weight: Custom weight for time anomaly score (default: 15)
        pattern_weight: Custom weight for pattern score (default: 20)
    
    Returns:
        BehavioralScorer with custom thresholds
    
    Example:
        >>> # Create a stricter scorer
        >>> scorer = create_scorer_with_custom_thresholds(
        ...     velocity_weight=30,  # More sensitive to velocity
        ...     amount_weight=40      # More sensitive to amount
        ... )
    """
    custom_thresholds = RISK_THRESHOLDS.copy()
    
    if velocity_weight is not None:
        custom_thresholds["velocity_score_per_excess"] = velocity_weight
    if amount_weight is not None:
        custom_thresholds["amount_deviation_score"] = amount_weight
    if beneficiary_weight is not None:
        custom_thresholds["beneficiary_score_per_new"] = beneficiary_weight
    if time_weight is not None:
        custom_thresholds["time_anomaly_score"] = time_weight
    if pattern_weight is not None:
        custom_thresholds["pattern_deviation_score"] = pattern_weight
    
    return BehavioralScorer(thresholds=custom_thresholds)


# ============================================================================
# Example Calculations (for documentation/testing)
# ============================================================================

def _example_normal_session() -> Dict[str, Any]:
    """
    Example: Normal, low-risk session.
    
    Returns:
        Dictionary with example data and expected results
    """
    return {
        "description": "Normal session: 2 transactions, typical amounts, during business hours",
        "session": SessionBehavior(
            session_id="sess_normal_001",
            account_id="acc_12345",
            login_time=int(datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc).timestamp()),
            last_activity_time=int(datetime(2024, 1, 15, 14, 45, tzinfo=timezone.utc).timestamp()),
            transaction_count=2,
            total_amount=5000.0,
            beneficiaries_added=0,
            created_at=int(datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc).timestamp()),
            updated_at=int(datetime(2024, 1, 15, 14, 45, tzinfo=timezone.utc).timestamp())
        ),
        "expected_risk": "LOW",
        "expected_score_range": (0, 20),
        "signals": []
    }


def _example_high_risk_session() -> Dict[str, Any]:
    """
    Example: High-risk, attack-like session.
    
    Returns:
        Dictionary with example data and expected results
    """
    return {
        "description": "Attack session: Off-hours, rapid transactions, new beneficiaries, high amounts",
        "session": SessionBehavior(
            session_id="sess_attack_001",
            account_id="acc_67890",
            login_time=int(datetime(2024, 1, 15, 2, 30, tzinfo=timezone.utc).timestamp()),  # 2:30 AM
            last_activity_time=int(datetime(2024, 1, 15, 2, 32, tzinfo=timezone.utc).timestamp()),
            transaction_count=8,  # 8 transactions in 2 minutes
            total_amount=80000.0,  # $10k average, 4x typical
            beneficiaries_added=3,
            created_at=int(datetime(2024, 1, 15, 2, 30, tzinfo=timezone.utc).timestamp()),
            updated_at=int(datetime(2024, 1, 15, 2, 32, tzinfo=timezone.utc).timestamp())
        ),
        "expected_risk": "CRITICAL",
        "expected_score_range": (100, 200),  # Will be clamped to 100
        "signals": [
            "TRANSACTION_VELOCITY",
            "AMOUNT_DEVIATION",
            "BENEFICIARY_CHANGES",
            "TIME_OF_DAY_ANOMALY",
            "TRANSACTION_PATTERN"
        ]
    }


# ============================================================================
# Tuning Guidance
# ============================================================================

"""
TUNING GUIDANCE - How to adjust scoring engine sensitivity:

1. Make Engine STRICTER (catch more fraud, more false positives):
   - DECREASE anomaly thresholds:
     * velocity_anomaly_count: 5 → 3 (trigger sooner)
     * amount_deviation_multiplier: 3.0 → 2.0 (lower threshold)
   - INCREASE score weights:
     * velocity_score_per_excess: 20 → 30
     * amount_deviation_score: 30 → 40
     * beneficiary_score_per_new: 25 → 35

2. Make Engine LOOSER (fewer false positives, miss some fraud):
   - INCREASE anomaly thresholds:
     * velocity_anomaly_count: 5 → 7
     * amount_deviation_multiplier: 3.0 → 4.0
   - DECREASE score weights:
     * velocity_score_per_excess: 20 → 15
     * amount_deviation_score: 30 → 20
     * beneficiary_score_per_new: 25 → 15

3. Adjust Risk Level Boundaries:
   - RISK_THRESHOLDS["risk_low"]: 30 (LOW → MEDIUM)
   - RISK_THRESHOLDS["risk_medium"]: 60 (MEDIUM → HIGH)
   - RISK_THRESHOLDS["risk_high"]: 80 (HIGH → CRITICAL)

4. Per-Signal Tuning:
   - Focus on velocity: Increase velocity_score_per_excess
   - Focus on amounts: Increase amount_deviation_score
   - Ignore time anomalies: Set time_anomaly_score = 0

Example tuning for conservative fraud detection:
    scorer = create_scorer_with_custom_thresholds(
        velocity_weight=30,    # More sensitive
        amount_weight=40,      # More sensitive
        beneficiary_weight=35, # More sensitive
        time_weight=20,        # More sensitive
        pattern_weight=25      # More sensitive
    )
"""
