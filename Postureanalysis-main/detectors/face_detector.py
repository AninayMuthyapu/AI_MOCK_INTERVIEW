"""
Face Detector module using MediaPipe Face Detection.
Detects face presence and provides bounding box information.
"""

import mediapipe.python.solutions.face_detection as mp_face_detection
import numpy as np
from typing import Optional, Dict, Any, Tuple
import config


class FaceDetector:
    """
    Wrapper for MediaPipe Face Detection.
    Provides face presence detection and bounding box extraction.
    """
    
    def __init__(self, min_detection_confidence: float = config.FACE_DETECTION_CONFIDENCE):
        """
        Initialize the face detector.
        
        Args:
            min_detection_confidence: Minimum confidence for face detection.
        """
        self.face_detection = mp_face_detection.FaceDetection(
            model_selection=0,  # 0 for short-range (within 2 meters)
            min_detection_confidence=min_detection_confidence
        )
        
        self.last_detection: Optional[Dict[str, Any]] = None
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect faces in the given frame.
        
        Args:
            frame: BGR image from OpenCV.
            
        Returns:
            Dictionary containing:
                - face_present: bool
                - confidence: float (0-1)
                - bounding_box: dict with x, y, width, height (normalized)
                - nose_tip: tuple (x, y) normalized coordinates
        """
        # Convert BGR to RGB
        rgb_frame = frame[:, :, ::-1]
        
        results = self.face_detection.process(rgb_frame)
        
        detection_result = {
            "face_present": False,
            "confidence": 0.0,
            "bounding_box": None,
            "nose_tip": None,
            "face_center": None
        }
        
        if results.detections:
            # Use the first (most confident) detection
            detection = results.detections[0]
            
            bounding_box = detection.location_data.relative_bounding_box
            
            detection_result["face_present"] = True
            detection_result["confidence"] = detection.score[0]
            detection_result["bounding_box"] = {
                "x": bounding_box.xmin,
                "y": bounding_box.ymin,
                "width": bounding_box.width,
                "height": bounding_box.height
            }
            
            # Extract nose tip keypoint
            keypoints = detection.location_data.relative_keypoints
            if len(keypoints) > 2:
                nose_tip = keypoints[2]  # Nose tip is index 2
                detection_result["nose_tip"] = (nose_tip.x, nose_tip.y)
            
            # Calculate face center
            detection_result["face_center"] = (
                bounding_box.xmin + bounding_box.width / 2,
                bounding_box.ymin + bounding_box.height / 2
            )
        
        self.last_detection = detection_result
        return detection_result
    
    def get_face_position_in_frame(
        self, 
        frame_width: int, 
        frame_height: int
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Get the face bounding box in pixel coordinates.
        
        Args:
            frame_width: Width of the frame in pixels.
            frame_height: Height of the frame in pixels.
            
        Returns:
            Tuple (x, y, width, height) in pixels, or None if no face detected.
        """
        if self.last_detection is None or not self.last_detection["face_present"]:
            return None
        
        bb = self.last_detection["bounding_box"]
        return (
            int(bb["x"] * frame_width),
            int(bb["y"] * frame_height),
            int(bb["width"] * frame_width),
            int(bb["height"] * frame_height)
        )
    
    def close(self):
        """Release resources."""
        self.face_detection.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
