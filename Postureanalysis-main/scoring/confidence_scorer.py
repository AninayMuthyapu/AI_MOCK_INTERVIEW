"""
Confidence Scorer module.
Computes dynamic confidence score based on all behavioral metrics.
"""

import time
from typing import Dict, Any, Optional
from enum import Enum
import config


class ConfidenceLevel(Enum):
    """Enum for confidence level labels."""
    HIGH = "high_confidence"
    MODERATE = "moderate_confidence"
    LOW = "low_confidence"


class ConfidenceScorer:
    """
    Dynamic confidence scoring engine.
    Computes a 0-100 score based on multiple behavioral inputs.
    """
    
    def __init__(
        self,
        baseline: float = config.CONFIDENCE_BASELINE,
        boost_rate: float = config.CONFIDENCE_BOOST_RATE,
        decay_rate: float = config.CONFIDENCE_DECAY_RATE,
        away_penalty: float = config.CONFIDENCE_AWAY_PENALTY
    ):
        """
        Initialize the confidence scorer.
        
        Args:
            baseline: Starting confidence score (0-100).
            boost_rate: Points gained per second of good behavior.
            decay_rate: Points lost per second of poor behavior.
            away_penalty: Points lost per second when away from screen.
        """
        self.baseline = baseline
        self.boost_rate = boost_rate
        self.decay_rate = decay_rate
        self.away_penalty = away_penalty
        
        # Weights for different components
        self.weights = {
            "attention": config.WEIGHT_FACE_PRESENCE,
            "eye_contact": config.WEIGHT_EYE_CONTACT,
            "posture": config.WEIGHT_POSTURE,
            "movement": config.WEIGHT_MOVEMENT
        }
        
        # Current state
        self.current_score = baseline
        self.last_update_time = time.time()
        
        # Thresholds
        self.high_threshold = config.HIGH_CONFIDENCE_THRESHOLD
        self.moderate_threshold = config.MODERATE_CONFIDENCE_THRESHOLD
        
        # History for averaging
        self.score_history = []
        self.history_max_size = 30
    
    def compute_score(
        self,
        attention_result: Dict[str, Any],
        gaze_result: Dict[str, Any],
        posture_result: Dict[str, Any],
        movement_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute confidence score based on all behavioral inputs.
        
        Args:
            attention_result: Output from AttentionAnalyzer
            gaze_result: Output from GazeAnalyzer
            posture_result: Output from PostureAnalyzer
            movement_result: Output from MovementAnalyzer
            
        Returns:
            Dictionary containing confidence score and breakdown.
        """
        current_time = time.time()
        delta_time = current_time - self.last_update_time
        
        result = {
            "score": self.current_score,
            "level": self._get_level(self.current_score),
            "component_scores": {},
            "is_away": False,
            "score_delta": 0.0
        }
        
        # Extract component scores
        attention_score = attention_result.get("attention_score", 0.5)
        eye_contact_score = gaze_result.get("eye_contact_score", 0.5)
        posture_score = posture_result.get("posture_score", 0.5)
        movement_score = movement_result.get("movement_score", 0.5)
        
        result["component_scores"] = {
            "attention": attention_score,
            "eye_contact": eye_contact_score,
            "posture": posture_score,
            "movement": movement_score
        }
        
        # Check if user is away from screen
        attention_state = attention_result.get("state")
        if hasattr(attention_state, 'value'):
            is_away = attention_state.value == "away_from_screen"
        else:
            is_away = str(attention_state) == "away_from_screen"
        
        result["is_away"] = is_away
        
        # Calculate weighted composite score (0-1)
        composite = (
            attention_score * self.weights["attention"] +
            eye_contact_score * self.weights["eye_contact"] +
            posture_score * self.weights["posture"] +
            movement_score * self.weights["movement"]
        )
        
        # Apply score changes based on behavior
        if is_away:
            # Significant penalty when away
            score_change = -self.away_penalty * delta_time
        elif composite >= 0.7:
            # Good behavior - boost score
            score_change = self.boost_rate * delta_time * composite
        elif composite < 0.4:
            # Poor behavior - decay score
            score_change = -self.decay_rate * delta_time * (1 - composite)
        else:
            # Neutral - slight drift toward baseline
            if self.current_score > self.baseline:
                score_change = -0.5 * delta_time
            else:
                score_change = 0.5 * delta_time
        
        # Apply change
        self.current_score = max(
            config.CONFIDENCE_MIN,
            min(config.CONFIDENCE_MAX, self.current_score + score_change)
        )
        
        result["score_delta"] = score_change
        
        # Add to history for smoothing
        self.score_history.append(self.current_score)
        if len(self.score_history) > self.history_max_size:
            self.score_history.pop(0)
        
        # Use smoothed score
        smoothed_score = sum(self.score_history) / len(self.score_history)
        
        result["score"] = round(smoothed_score, 1)
        result["level"] = self._get_level(smoothed_score)
        
        self.last_update_time = current_time
        
        return result
    
    def _get_level(self, score: float) -> ConfidenceLevel:
        """Get confidence level label from score."""
        if score >= self.high_threshold:
            return ConfidenceLevel.HIGH
        elif score >= self.moderate_threshold:
            return ConfidenceLevel.MODERATE
        else:
            return ConfidenceLevel.LOW
    
    def get_average_score(self) -> float:
        """Get the average confidence score over the session."""
        if len(self.score_history) == 0:
            return self.baseline
        return sum(self.score_history) / len(self.score_history)
    
    def reset(self):
        """Reset scorer state."""
        self.current_score = self.baseline
        self.last_update_time = time.time()
        self.score_history = []
