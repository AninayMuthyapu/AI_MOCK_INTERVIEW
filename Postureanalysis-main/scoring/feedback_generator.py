"""
Feedback Generator module.
Provides supportive, context-aware feedback to users.
"""

import time
from typing import Dict, Any, Optional, List
from enum import Enum
import config


class FeedbackType(Enum):
    """Types of feedback messages."""
    POSITIVE = "positive"
    CORRECTIVE = "corrective"
    WARNING = "warning"


class Feedback:
    """Represents a single feedback item."""
    
    def __init__(
        self, 
        message: str, 
        feedback_type: FeedbackType,
        category: str,
        priority: int = 5
    ):
        self.message = message
        self.feedback_type = feedback_type
        self.category = category
        self.priority = priority
        self.timestamp = time.time()


class FeedbackGenerator:
    """
    Generates supportive, context-aware feedback based on behavioral analysis.
    Implements cooldown to prevent message flooding.
    """
    
    # Minimum time a message stays visible (in seconds)
    MESSAGE_PERSISTENCE = 3.0
    
    def __init__(
        self,
        cooldown: float = config.FEEDBACK_COOLDOWN,
        max_active: int = config.FEEDBACK_MAX_ACTIVE
    ):
        """
        Initialize the feedback generator.
        
        Args:
            cooldown: Minimum seconds between same feedback type.
            max_active: Maximum number of active feedback messages.
        """
        self.cooldown = cooldown
        self.max_active = max_active
        
        # Track last time each feedback was shown
        self.last_feedback_times: Dict[str, float] = {}
        
        # Currently active feedback
        self.active_feedback: List[Feedback] = []
        
        # Persistent message tracking
        self.current_message: Optional[str] = None
        self.message_shown_at: float = 0.0
        
        # Feedback messages
        self.messages = config.FEEDBACK_MESSAGES
    
    def generate(
        self,
        attention_result: Dict[str, Any],
        gaze_result: Dict[str, Any],
        posture_result: Dict[str, Any],
        movement_result: Dict[str, Any],
        confidence_result: Dict[str, Any]
    ) -> List[Feedback]:
        """
        Generate feedback based on current behavioral state.
        
        Returns:
            List of Feedback objects to display.
        """
        current_time = time.time()
        potential_feedback = []
        
        # Check attention state
        attention_state = attention_result.get("state")
        if hasattr(attention_state, 'value'):
            attention_value = attention_state.value
        else:
            attention_value = str(attention_state)
        
        if attention_value == "away_from_screen":
            potential_feedback.append(self._create_feedback(
                "away", FeedbackType.WARNING, priority=10
            ))
        
        # Check eye contact
        eye_contact_score = gaze_result.get("eye_contact_score", 1.0)
        is_looking = gaze_result.get("is_looking_at_camera", True)
        
        if not is_looking and eye_contact_score < 0.5:
            potential_feedback.append(self._create_feedback(
                "eye_contact", FeedbackType.CORRECTIVE, priority=7
            ))
        elif is_looking and eye_contact_score > 0.8:
            potential_feedback.append(self._create_feedback(
                "good_eye_contact", FeedbackType.POSITIVE, priority=3
            ))
        
        # Check posture
        posture_quality = posture_result.get("posture_quality")
        if hasattr(posture_quality, 'value'):
            posture_value = posture_quality.value
        else:
            posture_value = str(posture_quality)
        
        posture_issues = posture_result.get("issues", [])
        
        if posture_value == "poor":
            if "slouching" in posture_issues:
                potential_feedback.append(self._create_feedback(
                    "posture_slouch", FeedbackType.CORRECTIVE, priority=8
                ))
            elif any(lean in posture_issues for lean in ["leaning_forward", "leaning_backward"]):
                potential_feedback.append(self._create_feedback(
                    "posture_lean", FeedbackType.CORRECTIVE, priority=7
                ))
            elif any("head_tilt" in issue for issue in posture_issues):
                potential_feedback.append(self._create_feedback(
                    "head_tilt", FeedbackType.CORRECTIVE, priority=6
                ))
        elif posture_value == "good" and posture_result.get("posture_score", 0) > 0.85:
            potential_feedback.append(self._create_feedback(
                "great_posture", FeedbackType.POSITIVE, priority=2
            ))
        
        # Check movement/nervousness
        nervousness = movement_result.get("nervousness_level")
        if hasattr(nervousness, 'value'):
            nervousness_value = nervousness.value
        else:
            nervousness_value = str(nervousness)
        
        if nervousness_value == "highly_nervous":
            potential_feedback.append(self._create_feedback(
                "stay_calm", FeedbackType.CORRECTIVE, priority=6
            ))
        
        # Check gaze direction
        gaze_direction = gaze_result.get("gaze_direction", "center")
        if hasattr(gaze_direction, 'value'):
            gaze_value = gaze_direction.value
        else:
            gaze_value = str(gaze_direction)
        
        if gaze_value in ["left", "right", "down"] and gaze_result.get("off_center_duration", 0) > 2:
            potential_feedback.append(self._create_feedback(
                "looking_away", FeedbackType.CORRECTIVE, priority=5
            ))
        
        # Filter by cooldown and priority
        valid_feedback = []
        for fb in potential_feedback:
            if fb is not None and self._can_show_feedback(fb.category, current_time):
                valid_feedback.append(fb)
        
        # Sort by priority (higher first) and take top N
        valid_feedback.sort(key=lambda x: x.priority, reverse=True)
        selected = valid_feedback[:self.max_active]
        
        # Update last shown times
        for fb in selected:
            self.last_feedback_times[fb.category] = current_time
        
        # Prefer corrective over positive if we have both
        has_corrective = any(fb.feedback_type == FeedbackType.CORRECTIVE for fb in selected)
        if has_corrective:
            selected = [fb for fb in selected if fb.feedback_type != FeedbackType.POSITIVE]
        
        self.active_feedback = selected
        return selected
    
    def _create_feedback(
        self, 
        key: str, 
        feedback_type: FeedbackType,
        priority: int = 5
    ) -> Optional[Feedback]:
        """Create a Feedback object from message key."""
        message = self.messages.get(key)
        if message is None:
            return None
        
        return Feedback(
            message=message,
            feedback_type=feedback_type,
            category=key,
            priority=priority
        )
    
    def _can_show_feedback(self, category: str, current_time: float) -> bool:
        """Check if feedback can be shown based on cooldown."""
        last_time = self.last_feedback_times.get(category, 0)
        return (current_time - last_time) >= self.cooldown
    
    def get_active_messages(self) -> List[str]:
        """Get list of active feedback message strings."""
        return [fb.message for fb in self.active_feedback]
    
    def get_primary_feedback(self) -> Optional[str]:
        """Get the highest priority feedback message with persistence."""
        current_time = time.time()
        
        # Check if current message should persist
        if self.current_message is not None:
            time_since_shown = current_time - self.message_shown_at
            if time_since_shown < self.MESSAGE_PERSISTENCE:
                # Keep showing the current message
                return self.current_message
        
        # Time to potentially update the message
        if self.active_feedback:
            new_message = self.active_feedback[0].message
            # Only update if message is different or enough time has passed
            if new_message != self.current_message:
                self.current_message = new_message
                self.message_shown_at = current_time
            return self.current_message
        
        # No active feedback - clear after persistence period
        if self.current_message is not None:
            time_since_shown = current_time - self.message_shown_at
            if time_since_shown >= self.MESSAGE_PERSISTENCE:
                self.current_message = None
        
        return self.current_message
    
    def reset(self):
        """Reset generator state."""
        self.last_feedback_times = {}
        self.active_feedback = []
        self.current_message = None
        self.message_shown_at = 0.0
