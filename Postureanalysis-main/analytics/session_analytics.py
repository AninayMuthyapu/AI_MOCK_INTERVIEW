"""
Session Analytics module.
Collects and aggregates metrics throughout the session.
"""

import time
from typing import Dict, Any, List, Optional
from collections import deque
import config


class SessionAnalytics:
    """
    Collects and aggregates behavioral metrics throughout a session.
    Provides time-series data for visualization and reporting.
    """
    
    def __init__(self, sample_rate: float = config.ANALYTICS_SAMPLE_RATE):
        """
        Initialize session analytics.
        
        Args:
            sample_rate: Rate at which to sample metrics (seconds).
        """
        self.sample_rate = sample_rate
        self.start_time: Optional[float] = None
        self.last_sample_time = 0.0
        
        # Time series data
        self.confidence_history: List[Dict] = []
        self.attention_history: List[Dict] = []
        self.posture_history: List[Dict] = []
        self.gaze_history: List[Dict] = []
        self.movement_history: List[Dict] = []
        
        # Aggregate metrics
        self.total_frames = 0
        self.total_duration = 0.0
        
        # Running sums for averages
        self.sum_confidence = 0.0
        self.sum_eye_contact = 0.0
        self.sum_posture = 0.0
        self.sum_movement = 0.0
        
        # Event counts
        self.distraction_events = 0
        self.posture_warnings = 0
        self.gaze_warnings = 0
    
    def start_session(self):
        """Start a new analytics session."""
        self.start_time = time.time()
        self.last_sample_time = self.start_time
        self._reset_data()
    
    def record(
        self,
        attention_result: Dict[str, Any],
        gaze_result: Dict[str, Any],
        posture_result: Dict[str, Any],
        movement_result: Dict[str, Any],
        confidence_result: Dict[str, Any]
    ):
        """
        Record metrics from current frame analysis.
        
        Args:
            attention_result: Output from AttentionAnalyzer
            gaze_result: Output from GazeAnalyzer
            posture_result: Output from PostureAnalyzer
            movement_result: Output from MovementAnalyzer
            confidence_result: Output from ConfidenceScorer
        """
        current_time = time.time()
        
        if self.start_time is None:
            self.start_session()
        
        self.total_frames += 1
        self.total_duration = current_time - self.start_time
        
        # Update running sums
        self.sum_confidence += confidence_result.get("score", 70)
        self.sum_eye_contact += gaze_result.get("eye_contact_score", 0.5)
        self.sum_posture += posture_result.get("posture_score", 0.5)
        self.sum_movement += movement_result.get("movement_score", 0.5)
        
        # Update event counts
        self.distraction_events = attention_result.get("distraction_events", 0)
        
        # Sample at specified rate
        if current_time - self.last_sample_time >= self.sample_rate:
            timestamp = current_time - self.start_time
            
            self.confidence_history.append({
                "time": timestamp,
                "score": confidence_result.get("score", 70),
                "level": str(confidence_result.get("level", "unknown"))
            })
            
            attention_state = attention_result.get("state")
            self.attention_history.append({
                "time": timestamp,
                "state": attention_state.value if hasattr(attention_state, 'value') else str(attention_state),
                "score": attention_result.get("attention_score", 0.5)
            })
            
            posture_quality = posture_result.get("posture_quality")
            self.posture_history.append({
                "time": timestamp,
                "quality": posture_quality.value if hasattr(posture_quality, 'value') else str(posture_quality),
                "score": posture_result.get("posture_score", 0.5),
                "issues": posture_result.get("issues", [])
            })
            
            gaze_direction = gaze_result.get("gaze_direction")
            self.gaze_history.append({
                "time": timestamp,
                "direction": gaze_direction.value if hasattr(gaze_direction, 'value') else str(gaze_direction),
                "score": gaze_result.get("eye_contact_score", 0.5),
                "looking_at_camera": gaze_result.get("is_looking_at_camera", False)
            })
            
            nervousness = movement_result.get("nervousness_level")
            self.movement_history.append({
                "time": timestamp,
                "nervousness": nervousness.value if hasattr(nervousness, 'value') else str(nervousness),
                "score": movement_result.get("movement_score", 0.5),
                "displacement": movement_result.get("average_displacement", 0)
            })
            
            self.last_sample_time = current_time
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get aggregate summary of the session.
        
        Returns:
            Dictionary containing session summary metrics.
        """
        if self.total_frames == 0:
            return self._empty_summary()
        
        avg_confidence = self.sum_confidence / self.total_frames
        avg_eye_contact = (self.sum_eye_contact / self.total_frames) * 100
        avg_posture = (self.sum_posture / self.total_frames) * 100
        avg_movement = (self.sum_movement / self.total_frames) * 100
        
        # Calculate overall readiness score
        overall_readiness = (
            avg_confidence * 0.3 +
            avg_eye_contact * 0.25 +
            avg_posture * 0.25 +
            avg_movement * 0.20
        )
        
        return {
            "session_duration_seconds": round(self.total_duration, 1),
            "total_frames_analyzed": self.total_frames,
            "average_confidence_score": round(avg_confidence, 1),
            "eye_contact_percentage": round(avg_eye_contact, 1),
            "posture_quality_score": round(avg_posture, 1),
            "movement_stability_score": round(avg_movement, 1),
            "distraction_events": self.distraction_events,
            "overall_readiness_score": round(overall_readiness, 1)
        }
    
    def get_time_series(self) -> Dict[str, List]:
        """Get time-series data for all metrics."""
        return {
            "confidence": self.confidence_history,
            "attention": self.attention_history,
            "posture": self.posture_history,
            "gaze": self.gaze_history,
            "movement": self.movement_history
        }
    
    def _empty_summary(self) -> Dict[str, Any]:
        """Return empty summary when no data collected."""
        return {
            "session_duration_seconds": 0,
            "total_frames_analyzed": 0,
            "average_confidence_score": 0,
            "eye_contact_percentage": 0,
            "posture_quality_score": 0,
            "movement_stability_score": 0,
            "distraction_events": 0,
            "overall_readiness_score": 0
        }
    
    def _reset_data(self):
        """Reset all collected data."""
        self.confidence_history = []
        self.attention_history = []
        self.posture_history = []
        self.gaze_history = []
        self.movement_history = []
        self.total_frames = 0
        self.total_duration = 0.0
        self.sum_confidence = 0.0
        self.sum_eye_contact = 0.0
        self.sum_posture = 0.0
        self.sum_movement = 0.0
        self.distraction_events = 0
        self.posture_warnings = 0
        self.gaze_warnings = 0
    
    def reset(self):
        """Reset analytics for a new session."""
        self.start_time = None
        self.last_sample_time = 0.0
        self._reset_data()
