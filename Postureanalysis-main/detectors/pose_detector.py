"""
Pose Detector module using MediaPipe Pose.
Extracts upper-body landmarks for posture analysis.
"""

import mediapipe.python.solutions.pose as mp_pose
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
import config


class PoseDetector:
    """
    Wrapper for MediaPipe Pose Detection.
    Extracts upper-body landmarks for posture analysis.
    """
    
    # MediaPipe Pose landmark indices for upper body
    NOSE = 0
    LEFT_EYE_INNER = 1
    LEFT_EYE = 2
    LEFT_EYE_OUTER = 3
    RIGHT_EYE_INNER = 4
    RIGHT_EYE = 5
    RIGHT_EYE_OUTER = 6
    LEFT_EAR = 7
    RIGHT_EAR = 8
    MOUTH_LEFT = 9
    MOUTH_RIGHT = 10
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    
    def __init__(
        self,
        min_detection_confidence: float = config.POSE_DETECTION_CONFIDENCE,
        min_tracking_confidence: float = config.POSE_TRACKING_CONFIDENCE
    ):
        """
        Initialize the pose detector.
        
        Args:
            min_detection_confidence: Minimum confidence for pose detection.
            min_tracking_confidence: Minimum confidence for pose tracking.
        """
        self.pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
        self.last_landmarks: Optional[Dict[str, Any]] = None
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect pose landmarks in the given frame.
        
        Args:
            frame: BGR image from OpenCV.
            
        Returns:
            Dictionary containing landmark positions and derived metrics.
        """
        # Convert BGR to RGB
        rgb_frame = frame[:, :, ::-1]
        
        results = self.pose.process(rgb_frame)
        
        detection_result = {
            "pose_detected": False,
            "landmarks": {},
            "shoulder_line": None,
            "neck_position": None,
            "head_position": None,
            "raw_landmarks": None
        }
        
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            detection_result["pose_detected"] = True
            detection_result["raw_landmarks"] = landmarks
            
            # Extract key landmarks
            detection_result["landmarks"] = {
                "nose": self._get_landmark(landmarks, self.NOSE),
                "left_eye": self._get_landmark(landmarks, self.LEFT_EYE),
                "right_eye": self._get_landmark(landmarks, self.RIGHT_EYE),
                "left_ear": self._get_landmark(landmarks, self.LEFT_EAR),
                "right_ear": self._get_landmark(landmarks, self.RIGHT_EAR),
                "left_shoulder": self._get_landmark(landmarks, self.LEFT_SHOULDER),
                "right_shoulder": self._get_landmark(landmarks, self.RIGHT_SHOULDER)
            }
            
            # Calculate derived positions
            left_shoulder = detection_result["landmarks"]["left_shoulder"]
            right_shoulder = detection_result["landmarks"]["right_shoulder"]
            nose = detection_result["landmarks"]["nose"]
            
            if left_shoulder and right_shoulder:
                # Shoulder line (for tilt detection)
                detection_result["shoulder_line"] = {
                    "left": left_shoulder,
                    "right": right_shoulder,
                    "angle": self._calculate_shoulder_angle(left_shoulder, right_shoulder)
                }
                
                # Neck position (midpoint between shoulders)
                detection_result["neck_position"] = {
                    "x": (left_shoulder["x"] + right_shoulder["x"]) / 2,
                    "y": (left_shoulder["y"] + right_shoulder["y"]) / 2,
                    "z": (left_shoulder["z"] + right_shoulder["z"]) / 2
                }
            
            if nose:
                detection_result["head_position"] = nose
        
        self.last_landmarks = detection_result
        return detection_result
    
    def _get_landmark(
        self, 
        landmarks: List, 
        idx: int
    ) -> Optional[Dict[str, float]]:
        """
        Extract a specific landmark.
        
        Args:
            landmarks: MediaPipe landmark list.
            idx: Landmark index.
            
        Returns:
            Dictionary with x, y, z, visibility, or None if not found.
        """
        if idx < len(landmarks):
            lm = landmarks[idx]
            return {
                "x": lm.x,
                "y": lm.y,
                "z": lm.z,
                "visibility": lm.visibility
            }
        return None
    
    def _calculate_shoulder_angle(
        self, 
        left_shoulder: Dict[str, float], 
        right_shoulder: Dict[str, float]
    ) -> float:
        """
        Calculate the angle of the shoulder line from horizontal.
        
        Args:
            left_shoulder: Left shoulder landmark.
            right_shoulder: Right shoulder landmark.
            
        Returns:
            Angle in degrees (positive = left higher, negative = right higher).
        """
        dx = right_shoulder["x"] - left_shoulder["x"]
        dy = right_shoulder["y"] - left_shoulder["y"]
        
        angle_rad = np.arctan2(dy, dx)
        angle_deg = np.degrees(angle_rad)
        
        return angle_deg
    
    def get_landmark_positions_pixels(
        self,
        frame_width: int,
        frame_height: int
    ) -> Dict[str, Tuple[int, int]]:
        """
        Get landmark positions in pixel coordinates.
        
        Args:
            frame_width: Width of the frame.
            frame_height: Height of the frame.
            
        Returns:
            Dictionary mapping landmark names to (x, y) pixel positions.
        """
        if self.last_landmarks is None or not self.last_landmarks["pose_detected"]:
            return {}
        
        pixel_positions = {}
        for name, lm in self.last_landmarks["landmarks"].items():
            if lm is not None:
                pixel_positions[name] = (
                    int(lm["x"] * frame_width),
                    int(lm["y"] * frame_height)
                )
        
        return pixel_positions
    
    def close(self):
        """Release resources."""
        self.pose.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
