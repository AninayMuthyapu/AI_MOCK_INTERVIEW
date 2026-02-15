"""
Gaze Analyzer module.
Tracks eye contact duration and quality over time.
"""

import time
from typing import Optional, Dict, Any
from enum import Enum
import config


class GazeAnalyzer:
    """
    Analyzes eye contact quality based on gaze detection over time.
    """
    
    def __init__(
        self,
        off_center_timeout: float = config.GAZE_OFF_CENTER_TIMEOUT,
        tolerance_duration: float = config.GAZE_TOLERANCE_DURATION
    ):
        """
        Initialize the gaze analyzer.
        
        Args:
            off_center_timeout: Seconds of off-center gaze before penalizing.
            tolerance_duration: Short glances are tolerated within this duration.
        """
        self.off_center_timeout = off_center_timeout
        self.tolerance_duration = tolerance_duration
        
        # State tracking
        self.last_looking_at_camera_time: Optional[float] = None
        self.off_center_start_time: Optional[float] = None
        
        # Metrics
        self.total_eye_contact_duration = 0.0
        self.total_off_center_duration = 0.0
        self.attention_loss_events = 0
        self.last_update_time = time.time()
        
        # Track if we've already counted current off-center event
        self._event_counted = False
        
        # History for smoothing
        self.gaze_history = []
        self.history_size = 15
    
    def analyze(self, gaze_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze eye contact based on gaze detection results.
        
        Args:
            gaze_result: Output from GazeDetector.detect()
            
        Returns:
            Dictionary containing eye contact analysis results.
        """
        current_time = time.time()
        delta_time = current_time - self.last_update_time
        
        analysis_result = {
            "gaze_detected": gaze_result.get("face_mesh_detected", False),
            "is_looking_at_camera": False,
            "gaze_direction": "unknown",
            "off_center_duration": 0.0,
            "eye_contact_score": 0.5,
            "attention_loss_events": self.attention_loss_events,
            "eye_contact_percentage": self.get_eye_contact_percentage()
        }
        
        if not analysis_result["gaze_detected"]:
            return analysis_result
        
        is_looking = gaze_result.get("is_looking_at_camera", False)
        gaze_direction = gaze_result.get("gaze_direction")
        
        if hasattr(gaze_direction, 'value'):
            analysis_result["gaze_direction"] = gaze_direction.value
        elif gaze_direction:
            analysis_result["gaze_direction"] = str(gaze_direction)
        
        # Add to history for smoothing
        self.gaze_history.append(1.0 if is_looking else 0.0)
        if len(self.gaze_history) > self.history_size:
            self.gaze_history.pop(0)
        
        # Consider looking at camera if majority of recent frames were looking
        smoothed_looking = sum(self.gaze_history) / len(self.gaze_history) > 0.5
        
        analysis_result["is_looking_at_camera"] = smoothed_looking
        
        if smoothed_looking:
            # Looking at camera
            self.last_looking_at_camera_time = current_time
            self.total_eye_contact_duration += delta_time
            
            # Reset off-center tracking
            if self.off_center_start_time is not None:
                self.total_off_center_duration += current_time - self.off_center_start_time
            self.off_center_start_time = None
            self._event_counted = False
            
            analysis_result["eye_contact_score"] = 1.0
            
        else:
            # Not looking at camera
            if self.off_center_start_time is None:
                self.off_center_start_time = current_time
            
            off_center_duration = current_time - self.off_center_start_time
            analysis_result["off_center_duration"] = off_center_duration
            
            # Check if this is beyond tolerance
            if off_center_duration <= self.tolerance_duration:
                # Still within tolerance - don't penalize
                analysis_result["eye_contact_score"] = 0.8
                
            elif off_center_duration >= self.off_center_timeout:
                # Significant attention loss
                analysis_result["eye_contact_score"] = 0.2
                
                # Count as attention loss event if not already counted
                if not self._event_counted:
                    self.attention_loss_events += 1
                    self._event_counted = True
                    
            else:
                # Gradual decrease
                progress = (off_center_duration - self.tolerance_duration) / (
                    self.off_center_timeout - self.tolerance_duration
                )
                analysis_result["eye_contact_score"] = max(0.2, 0.8 - progress * 0.6)
        
        analysis_result["attention_loss_events"] = self.attention_loss_events
        analysis_result["eye_contact_percentage"] = self.get_eye_contact_percentage()
        
        self.last_update_time = current_time
        
        return analysis_result
    
    def get_eye_contact_percentage(self) -> float:
        """
        Calculate the percentage of time with eye contact.
        
        Returns:
            Eye contact percentage (0-100).
        """
        total_time = self.total_eye_contact_duration + self.total_off_center_duration
        if total_time == 0:
            return 100.0
        
        return (self.total_eye_contact_duration / total_time) * 100
    
    def reset(self):
        """Reset analyzer state."""
        self.last_looking_at_camera_time = None
        self.off_center_start_time = None
        self.total_eye_contact_duration = 0.0
        self.total_off_center_duration = 0.0
        self.attention_loss_events = 0
        self.last_update_time = time.time()
        self._event_counted = False
        self.gaze_history = []
