"""
Gaze Detector module using MediaPipe Face Mesh.
Tracks eye gaze direction using iris landmarks.
"""

import mediapipe.python.solutions.face_mesh as mp_face_mesh
import numpy as np
from typing import Optional, Dict, Any, Tuple
from enum import Enum
import config


class GazeDirection(Enum):
    """Enum for gaze direction classification."""
    CENTER = "center"
    LEFT = "left"
    RIGHT = "right"
    DOWN = "down"
    UP = "up"
    UNKNOWN = "unknown"


class GazeDetector:
    """
    Gaze tracking using MediaPipe Face Mesh iris landmarks.
    """
    
    # Key Face Mesh landmark indices
    # Left eye landmarks
    LEFT_EYE_LEFT_CORNER = 33
    LEFT_EYE_RIGHT_CORNER = 133
    LEFT_EYE_TOP = 159
    LEFT_EYE_BOTTOM = 145
    LEFT_IRIS_CENTER = 468
    
    # Right eye landmarks
    RIGHT_EYE_LEFT_CORNER = 362
    RIGHT_EYE_RIGHT_CORNER = 263
    RIGHT_EYE_TOP = 386
    RIGHT_EYE_BOTTOM = 374
    RIGHT_IRIS_CENTER = 473
    
    def __init__(
        self,
        min_detection_confidence: float = config.FACE_MESH_CONFIDENCE,
        min_tracking_confidence: float = config.FACE_MESH_CONFIDENCE
    ):
        """
        Initialize the gaze detector.
        
        Args:
            min_detection_confidence: Minimum confidence for face mesh detection.
            min_tracking_confidence: Minimum confidence for tracking.
        """
        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,  # Enables iris landmarks
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
        self.center_threshold = config.GAZE_CENTER_THRESHOLD
        self.last_gaze: Optional[Dict[str, Any]] = None
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect gaze direction from the frame.
        
        Args:
            frame: BGR image from OpenCV.
            
        Returns:
            Dictionary containing gaze information.
        """
        # Convert BGR to RGB
        rgb_frame = frame[:, :, ::-1]
        
        results = self.face_mesh.process(rgb_frame)
        
        detection_result = {
            "face_mesh_detected": False,
            "gaze_direction": GazeDirection.UNKNOWN,
            "gaze_vector": None,
            "left_eye_ratio": None,
            "right_eye_ratio": None,
            "average_ratio": None,
            "is_looking_at_camera": False
        }
        
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            detection_result["face_mesh_detected"] = True
            
            # Calculate gaze for both eyes
            left_ratio = self._calculate_eye_gaze_ratio(
                landmarks,
                self.LEFT_EYE_LEFT_CORNER,
                self.LEFT_EYE_RIGHT_CORNER,
                self.LEFT_EYE_TOP,
                self.LEFT_EYE_BOTTOM,
                self.LEFT_IRIS_CENTER
            )
            
            right_ratio = self._calculate_eye_gaze_ratio(
                landmarks,
                self.RIGHT_EYE_LEFT_CORNER,
                self.RIGHT_EYE_RIGHT_CORNER,
                self.RIGHT_EYE_TOP,
                self.RIGHT_EYE_BOTTOM,
                self.RIGHT_IRIS_CENTER
            )
            
            if left_ratio is not None and right_ratio is not None:
                detection_result["left_eye_ratio"] = left_ratio
                detection_result["right_eye_ratio"] = right_ratio
                
                # Average the ratios
                avg_horizontal = (left_ratio["horizontal"] + right_ratio["horizontal"]) / 2
                avg_vertical = (left_ratio["vertical"] + right_ratio["vertical"]) / 2
                
                detection_result["average_ratio"] = {
                    "horizontal": avg_horizontal,
                    "vertical": avg_vertical
                }
                
                detection_result["gaze_vector"] = (avg_horizontal, avg_vertical)
                
                # Classify gaze direction
                detection_result["gaze_direction"] = self._classify_gaze(
                    avg_horizontal, avg_vertical
                )
                
                # Check if looking at camera (center)
                detection_result["is_looking_at_camera"] = (
                    detection_result["gaze_direction"] == GazeDirection.CENTER
                )
        
        self.last_gaze = detection_result
        return detection_result
    
    def _calculate_eye_gaze_ratio(
        self,
        landmarks,
        left_corner_idx: int,
        right_corner_idx: int,
        top_idx: int,
        bottom_idx: int,
        iris_center_idx: int
    ) -> Optional[Dict[str, float]]:
        """
        Calculate gaze ratio for a single eye.
        
        The ratio indicates the position of the iris within the eye bounds.
        - Horizontal: 0.0 = looking left, 0.5 = center, 1.0 = looking right
        - Vertical: 0.0 = looking up, 0.5 = center, 1.0 = looking down
        
        Returns:
            Dictionary with horizontal and vertical ratios.
        """
        try:
            left_corner = landmarks[left_corner_idx]
            right_corner = landmarks[right_corner_idx]
            top = landmarks[top_idx]
            bottom = landmarks[bottom_idx]
            iris_center = landmarks[iris_center_idx]
            
            # Calculate eye width and height
            eye_width = right_corner.x - left_corner.x
            eye_height = bottom.y - top.y
            
            if eye_width <= 0 or eye_height <= 0:
                return None
            
            # Calculate iris position relative to eye bounds
            horizontal_ratio = (iris_center.x - left_corner.x) / eye_width
            vertical_ratio = (iris_center.y - top.y) / eye_height
            
            # Clamp to valid range
            horizontal_ratio = max(0.0, min(1.0, horizontal_ratio))
            vertical_ratio = max(0.0, min(1.0, vertical_ratio))
            
            return {
                "horizontal": horizontal_ratio,
                "vertical": vertical_ratio
            }
            
        except (IndexError, ZeroDivisionError):
            return None
    
    def _classify_gaze(
        self, 
        horizontal: float, 
        vertical: float
    ) -> GazeDirection:
        """
        Classify gaze direction based on ratios.
        
        Args:
            horizontal: Horizontal gaze ratio (0-1, 0.5 = center)
            vertical: Vertical gaze ratio (0-1, 0.5 = center)
            
        Returns:
            GazeDirection enum value.
        """
        # Deviation from center
        h_deviation = horizontal - 0.5
        v_deviation = vertical - 0.5
        
        # Check if looking at center (camera)
        if (abs(h_deviation) < self.center_threshold and 
            abs(v_deviation) < self.center_threshold):
            return GazeDirection.CENTER
        
        # Determine dominant direction
        if abs(h_deviation) > abs(v_deviation):
            # Horizontal deviation is dominant
            if h_deviation < -self.center_threshold:
                return GazeDirection.LEFT
            elif h_deviation > self.center_threshold:
                return GazeDirection.RIGHT
        else:
            # Vertical deviation is dominant
            if v_deviation < -self.center_threshold:
                return GazeDirection.UP
            elif v_deviation > self.center_threshold:
                return GazeDirection.DOWN
        
        return GazeDirection.CENTER
    
    def get_gaze_direction_string(self) -> str:
        """Get the current gaze direction as a string."""
        if self.last_gaze is None:
            return "unknown"
        return self.last_gaze["gaze_direction"].value
    
    def close(self):
        """Release resources."""
        self.face_mesh.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
