"""
Movement Analyzer module.
Detects nervousness and stability through landmark displacement analysis.
"""

import numpy as np
from typing import Optional, Dict, Any, List
from enum import Enum
from collections import deque
import config


class NervousnessLevel(Enum):
    """Enum for nervousness classification."""
    CALM = "calm"
    SLIGHTLY_NERVOUS = "slightly_nervous"
    HIGHLY_NERVOUS = "highly_nervous"
    UNKNOWN = "unknown"


class MovementAnalyzer:
    """
    Analyzes movement patterns to detect nervousness and stability.
    Uses frame-to-frame landmark displacement tracking.
    """
    
    def __init__(
        self,
        window_size: int = config.MOVEMENT_WINDOW_SIZE,
        calm_threshold: float = config.CALM_MOVEMENT_THRESHOLD,
        nervous_threshold: float = config.NERVOUS_MOVEMENT_THRESHOLD
    ):
        """
        Initialize the movement analyzer.
        
        Args:
            window_size: Number of frames for rolling average.
            calm_threshold: Max displacement for calm classification.
            nervous_threshold: Displacement threshold for highly nervous.
        """
        self.window_size = window_size
        self.calm_threshold = calm_threshold
        self.nervous_threshold = nervous_threshold
        
        # Landmark history for displacement calculation
        self.landmark_history: deque = deque(maxlen=window_size)
        self.displacement_history: deque = deque(maxlen=window_size)
        
        # Metrics
        self.total_frames = 0
        self.calm_frames = 0
        self.slightly_nervous_frames = 0
        self.highly_nervous_frames = 0
        
        # Smoothing for score
        self.score_history: deque = deque(maxlen=10)
    
    def analyze(self, pose_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze movement from pose detection results.
        
        Args:
            pose_result: Output from PoseDetector.detect()
            
        Returns:
            Dictionary containing movement analysis results.
        """
        analysis_result = {
            "movement_detected": False,
            "nervousness_level": NervousnessLevel.UNKNOWN,
            "displacement": 0.0,
            "average_displacement": 0.0,
            "movement_score": 1.0,  # 1.0 = calm, 0.0 = highly nervous
            "is_stable": True
        }
        
        if not pose_result.get("pose_detected", False):
            return analysis_result
        
        analysis_result["movement_detected"] = True
        landmarks = pose_result.get("landmarks", {})
        
        # Extract key positions for tracking
        current_positions = self._extract_key_positions(landmarks)
        
        if current_positions is None:
            return analysis_result
        
        # Calculate displacement from previous frame
        displacement = 0.0
        if len(self.landmark_history) > 0:
            prev_positions = self.landmark_history[-1]
            displacement = self._calculate_displacement(prev_positions, current_positions)
        
        # Store current positions
        self.landmark_history.append(current_positions)
        self.displacement_history.append(displacement)
        
        analysis_result["displacement"] = displacement
        
        # Calculate average displacement over window
        if len(self.displacement_history) > 0:
            # Weighted average (recent frames more important)
            weights = np.linspace(0.5, 1.0, len(self.displacement_history))
            avg_displacement = np.average(
                list(self.displacement_history), 
                weights=weights
            )
        else:
            avg_displacement = displacement
        
        analysis_result["average_displacement"] = avg_displacement
        
        # Classify nervousness level
        nervousness_level, is_stable = self._classify_nervousness(avg_displacement)
        analysis_result["nervousness_level"] = nervousness_level
        analysis_result["is_stable"] = is_stable
        
        # Update frame counts
        self.total_frames += 1
        if nervousness_level == NervousnessLevel.CALM:
            self.calm_frames += 1
        elif nervousness_level == NervousnessLevel.SLIGHTLY_NERVOUS:
            self.slightly_nervous_frames += 1
        elif nervousness_level == NervousnessLevel.HIGHLY_NERVOUS:
            self.highly_nervous_frames += 1
        
        # Calculate movement score (0-1, higher is calmer)
        movement_score = self._calculate_movement_score(avg_displacement)
        
        # Smooth the score
        self.score_history.append(movement_score)
        smoothed_score = np.mean(self.score_history)
        
        analysis_result["movement_score"] = smoothed_score
        
        return analysis_result
    
    def _extract_key_positions(self, landmarks: Dict) -> Optional[np.ndarray]:
        """
        Extract key landmark positions for movement tracking.
        
        Returns:
            numpy array of positions or None if key landmarks missing.
        """
        key_landmarks = ["nose", "left_shoulder", "right_shoulder", "left_ear", "right_ear"]
        positions = []
        
        for name in key_landmarks:
            lm = landmarks.get(name)
            if lm is not None:
                positions.append([lm["x"], lm["y"]])
            else:
                # Use placeholder if some landmarks are missing
                if len(positions) > 0:
                    positions.append(positions[-1])
                else:
                    return None
        
        return np.array(positions)
    
    def _calculate_displacement(
        self, 
        prev_positions: np.ndarray, 
        current_positions: np.ndarray
    ) -> float:
        """
        Calculate total displacement between frames.
        
        Returns:
            Sum of Euclidean distances for all tracked landmarks.
        """
        if prev_positions.shape != current_positions.shape:
            return 0.0
        
        # Calculate Euclidean distance for each landmark
        distances = np.linalg.norm(current_positions - prev_positions, axis=1)
        
        # Use RMS of distances (root mean square)
        rms_displacement = np.sqrt(np.mean(distances ** 2))
        
        # Scale to a more intuitive range (multiply by 1000 for pixel-like values)
        return rms_displacement * 1000
    
    def _classify_nervousness(self, avg_displacement: float) -> tuple:
        """
        Classify nervousness level based on displacement.
        
        Returns:
            Tuple of (NervousnessLevel, is_stable)
        """
        if avg_displacement <= self.calm_threshold:
            return NervousnessLevel.CALM, True
        elif avg_displacement <= self.nervous_threshold:
            return NervousnessLevel.SLIGHTLY_NERVOUS, True
        else:
            return NervousnessLevel.HIGHLY_NERVOUS, False
    
    def _calculate_movement_score(self, avg_displacement: float) -> float:
        """
        Calculate a 0-1 score based on movement.
        1.0 = perfectly calm, 0.0 = highly nervous
        """
        if avg_displacement <= self.calm_threshold:
            return 1.0
        elif avg_displacement >= self.nervous_threshold:
            return 0.0
        else:
            # Linear interpolation
            range_size = self.nervous_threshold - self.calm_threshold
            progress = (avg_displacement - self.calm_threshold) / range_size
            return 1.0 - progress
    
    def get_nervousness_percentage(self) -> Dict[str, float]:
        """Get percentage breakdown of nervousness levels."""
        if self.total_frames == 0:
            return {"calm": 100, "slightly_nervous": 0, "highly_nervous": 0}
        
        return {
            "calm": (self.calm_frames / self.total_frames) * 100,
            "slightly_nervous": (self.slightly_nervous_frames / self.total_frames) * 100,
            "highly_nervous": (self.highly_nervous_frames / self.total_frames) * 100
        }
    
    def reset(self):
        """Reset analyzer state."""
        self.landmark_history.clear()
        self.displacement_history.clear()
        self.total_frames = 0
        self.calm_frames = 0
        self.slightly_nervous_frames = 0
        self.highly_nervous_frames = 0
        self.score_history.clear()
