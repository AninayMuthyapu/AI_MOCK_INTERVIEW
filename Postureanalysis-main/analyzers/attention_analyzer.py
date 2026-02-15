"""
Attention Analyzer module.
Tracks face presence and determines attention state over time.
"""

import time
from typing import Optional, Dict, Any
from enum import Enum
import config


class AttentionState(Enum):
    """Enum for attention states."""
    FULLY_ATTENTIVE = "fully_attentive"
    TEMPORARILY_DISTRACTED = "temporarily_distracted"
    AWAY_FROM_SCREEN = "away_from_screen"
    UNKNOWN = "unknown"


class AttentionAnalyzer:
    """
    Analyzes attention state based on face presence over time.
    """
    
    def __init__(
        self,
        face_absence_timeout: float = config.FACE_ABSENCE_TIMEOUT,
        distraction_timeout: float = config.DISTRACTION_TIMEOUT
    ):
        """
        Initialize the attention analyzer.
        
        Args:
            face_absence_timeout: Seconds before marking as away from screen.
            distraction_timeout: Seconds before counting as distraction event.
        """
        self.face_absence_timeout = face_absence_timeout
        self.distraction_timeout = distraction_timeout
        
        # State tracking
        self.current_state = AttentionState.UNKNOWN
        self.last_face_seen_time: Optional[float] = None
        self.face_absence_start: Optional[float] = None
        
        # Metrics
        self.distraction_events = 0
        self.total_away_duration = 0.0
        self.total_attentive_duration = 0.0
        self.last_update_time = time.time()
        
        # Track if we've already counted this absence as a distraction
        self._distraction_counted = False
    
    def analyze(self, face_detection_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze attention state based on face detection results.
        
        Args:
            face_detection_result: Output from FaceDetector.detect()
            
        Returns:
            Dictionary containing attention analysis results.
        """
        current_time = time.time()
        delta_time = current_time - self.last_update_time
        
        face_present = face_detection_result.get("face_present", False)
        
        analysis_result = {
            "state": self.current_state,
            "face_present": face_present,
            "seconds_since_face": 0.0,
            "distraction_events": self.distraction_events,
            "attention_score": 1.0,  # 0-1 score for current attention
            "total_away_duration": self.total_away_duration,
            "total_attentive_duration": self.total_attentive_duration
        }
        
        if face_present:
            # Face is present - reset absence tracking
            if self.face_absence_start is not None:
                # Calculate how long they were away
                absence_duration = current_time - self.face_absence_start
                self.total_away_duration += absence_duration
            
            self.last_face_seen_time = current_time
            self.face_absence_start = None
            self._distraction_counted = False
            
            self.current_state = AttentionState.FULLY_ATTENTIVE
            self.total_attentive_duration += delta_time
            
            analysis_result["state"] = self.current_state
            analysis_result["attention_score"] = 1.0
            
        else:
            # Face not present
            if self.face_absence_start is None:
                self.face_absence_start = current_time
            
            absence_duration = current_time - self.face_absence_start
            analysis_result["seconds_since_face"] = absence_duration
            
            if absence_duration >= self.face_absence_timeout:
                # Definitely away from screen
                self.current_state = AttentionState.AWAY_FROM_SCREEN
                analysis_result["attention_score"] = 0.0
                
                # Count as distraction event if not already counted
                if not self._distraction_counted and absence_duration >= self.distraction_timeout:
                    self.distraction_events += 1
                    self._distraction_counted = True
                
            elif absence_duration > 0.5:  # Short grace period
                # Temporarily distracted
                self.current_state = AttentionState.TEMPORARILY_DISTRACTED
                # Gradual score decrease
                analysis_result["attention_score"] = max(
                    0.3, 
                    1.0 - (absence_duration / self.face_absence_timeout)
                )
            
            analysis_result["state"] = self.current_state
        
        analysis_result["distraction_events"] = self.distraction_events
        analysis_result["total_away_duration"] = self.total_away_duration
        analysis_result["total_attentive_duration"] = self.total_attentive_duration
        
        self.last_update_time = current_time
        
        return analysis_result
    
    def get_attention_percentage(self) -> float:
        """
        Calculate the percentage of time the user was attentive.
        
        Returns:
            Attention percentage (0-100).
        """
        total_time = self.total_attentive_duration + self.total_away_duration
        if total_time == 0:
            return 100.0
        
        return (self.total_attentive_duration / total_time) * 100
    
    def reset(self):
        """Reset all metrics."""
        self.current_state = AttentionState.UNKNOWN
        self.last_face_seen_time = None
        self.face_absence_start = None
        self.distraction_events = 0
        self.total_away_duration = 0.0
        self.total_attentive_duration = 0.0
        self.last_update_time = time.time()
        self._distraction_counted = False
