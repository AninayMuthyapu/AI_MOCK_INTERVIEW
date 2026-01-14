"""
Enhanced Vision Service - Real-time CV Analysis with Dynamic Visualization
Displays metrics, feedback, and visual indicators directly on video feed
"""

import cv2
import numpy as np
import time
import base64
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)

# Try to import mediapipe with fallback for different versions
MEDIAPIPE_AVAILABLE = False
MEDIAPIPE_LEGACY = False

try:
    import mediapipe as mp
    # Check if legacy solutions API is available
    if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'holistic'):
        MEDIAPIPE_AVAILABLE = True
        MEDIAPIPE_LEGACY = True
        logger.info("mediapipe loaded with legacy solutions API")
    else:
        # New version without solutions - we'll use a simplified fallback
        logger.warning("mediapipe loaded but solutions API not available - using basic mode")
        MEDIAPIPE_AVAILABLE = False
except ImportError:
    logger.warning("mediapipe not installed - vision analysis disabled")

class VisionService:
    def __init__(self):
        self.enabled = MEDIAPIPE_AVAILABLE
        self.last_face_time = time.time()
        self.metrics_history = []
        
        if MEDIAPIPE_AVAILABLE and MEDIAPIPE_LEGACY:
            self.mp_holistic = mp.solutions.holistic
            self.mp_drawing = mp.solutions.drawing_utils
            self.mp_drawing_styles = mp.solutions.drawing_styles
            
            self.holistic = self.mp_holistic.Holistic(
                static_image_mode=False,
                model_complexity=1,
                min_detection_confidence=0.2,
                min_tracking_confidence=0.2,
            )
        else:
            self.mp_holistic = None
            self.mp_drawing = None
            self.mp_drawing_styles = None
            self.holistic = None
            logger.info("VisionService running in disabled mode (no mediapipe)")

        
    def draw_text_with_background(self, img, text, pos, font_scale=0.6, 
                                   thickness=2, text_color=(255, 255, 255), 
                                   bg_color=(0, 0, 0), padding=5):
        """Draw text with background rectangle"""
        font = cv2.FONT_HERSHEY_SIMPLEX
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        
        x, y = pos
        cv2.rectangle(img, 
                     (x - padding, y - text_height - padding),
                     (x + text_width + padding, y + baseline + padding),
                     bg_color, -1)
        cv2.putText(img, text, (x, y), font, font_scale, text_color, thickness)
        
    def draw_confidence_bar(self, img, confidence, x, y, width=200, height=20):
        """Draw confidence score as progress bar"""
        # Background
        cv2.rectangle(img, (x, y), (x + width, y + height), (50, 50, 50), -1)
        
        # Fill based on confidence
        fill_width = int((confidence / 100) * width)
        if confidence >= 70:
            color = (0, 255, 0)  # Green
        elif confidence >= 40:
            color = (0, 255, 255)  # Yellow
        else:
            color = (0, 0, 255)  # Red
            
        cv2.rectangle(img, (x, y), (x + fill_width, y + height), color, -1)
        
        # Border
        cv2.rectangle(img, (x, y), (x + width, y + height), (255, 255, 255), 2)
        
        # Text
        text = f"{confidence}%"
        cv2.putText(img, text, (x + width + 10, y + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    
    def draw_status_indicator(self, img, status, label, x, y):
        """Draw colored status circle with label"""
        colors = {
            'good': (0, 255, 0),
            'moderate': (0, 255, 255),
            'poor': (0, 0, 255),
            'unknown': (128, 128, 128)
        }
        color = colors.get(status, (128, 128, 128))
        
        # Circle
        cv2.circle(img, (x, y), 8, color, -1)
        cv2.circle(img, (x, y), 8, (255, 255, 255), 2)
        
        # Label
        cv2.putText(img, label, (x + 15, y + 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    def head_direction_estimate(self, face_landmarks, image_w, image_h):
        """Calculate head pose angles"""
        nose = face_landmarks.landmark[1]
        chin = face_landmarks.landmark[152]
        left_eye = face_landmarks.landmark[33]
        right_eye = face_landmarks.landmark[263]
        
        yaw = np.degrees(np.arctan2(right_eye.y - left_eye.y, right_eye.x - left_eye.x))
        pitch = np.degrees(np.arctan2(nose.y - chin.y, 
                                      np.sqrt((nose.x - chin.x)**2 + (nose.z - chin.z)**2)))
        
        return {"yaw": float(yaw), "pitch": float(pitch)}
    
    def posture_slouch_estimate(self, pose_landmarks, image_w, image_h):
        """Calculate slouch angle from shoulders to hips"""
        left_shoulder = pose_landmarks.landmark[self.mp_holistic.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = pose_landmarks.landmark[self.mp_holistic.PoseLandmark.RIGHT_SHOULDER]
        left_hip = pose_landmarks.landmark[self.mp_holistic.PoseLandmark.LEFT_HIP]
        right_hip = pose_landmarks.landmark[self.mp_holistic.PoseLandmark.RIGHT_HIP]
        
        shoulder_mid_x = (left_shoulder.x + right_shoulder.x) / 2
        shoulder_mid_y = (left_shoulder.y + right_shoulder.y) / 2
        hip_mid_x = (left_hip.x + right_hip.x) / 2
        hip_mid_y = (left_hip.y + right_hip.y) / 2
        
        dx = shoulder_mid_x - hip_mid_x
        dy = shoulder_mid_y - hip_mid_y
        
        angle = abs(np.degrees(np.arctan2(dx, dy)))
        return float(angle)
    
    def analyze_frame_with_visualization(self, frame):
        """Analyze frame and draw all metrics on it"""
        image_h, image_w = frame.shape[:2]
        now = time.time()
        
        # If mediapipe is not available, return default metrics
        if not self.enabled or self.holistic is None:
            return frame, {
                "presence": False,
                "eye_contact": "unknown",
                "confidence_score": 50,
                "posture": {"slouch_angle": 0.0, "is_good": True},
                "head_pose": {"yaw": 0.0, "pitch": 0.0},
                "feedback": ["⚠ Vision analysis unavailable (mediapipe not configured)"],
                "overall": "Vision analysis disabled",
                "timestamp": now
            }
        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.holistic.process(rgb)
        
        # Initialize metrics
        presence = False
        eye_contact = "unknown"
        confidence_score = 0
        slouch_angle = 0.0
        is_good_posture = True
        head_pose = {"yaw": 0.0, "pitch": 0.0}
        feedback_messages = []
        
        
        print(f"[VisionService] Frame: {image_w}x{image_h}, Face detected: {results.face_landmarks is not None}, Pose detected: {results.pose_landmarks is not None}")
        
        # Draw face mesh if detected
        if results.face_landmarks:
            presence = True
            self.last_face_time = now
            
            # Draw face landmarks
            self.mp_drawing.draw_landmarks(
                frame,
                results.face_landmarks,
                self.mp_holistic.FACEMESH_CONTOURS,
                landmark_drawing_spec=None,
                connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_contours_style()
            )
            
            # Calculate head pose
            head_pose = self.head_direction_estimate(results.face_landmarks, image_w, image_h)
            yaw, pitch = head_pose['yaw'], head_pose['pitch']
            
            # Determine eye contact
            if abs(yaw) < 15 and abs(pitch) < 15:
                eye_contact = "good"
                feedback_messages.append("✓ Good eye contact")
            elif abs(yaw) > 30 or abs(pitch) > 30:
                eye_contact = "away"
                feedback_messages.append("✗ Looking away")
            else:
                eye_contact = "moderate"
                feedback_messages.append("⚠ Moderate eye contact")
        else:
            if now - self.last_face_time > 2.0:
                feedback_messages.append("✗ Not in camera frame")
        
        # Draw pose if detected
        if results.pose_landmarks:
            # Draw pose landmarks
            self.mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                self.mp_holistic.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
            )
            
            # Calculate posture
            slouch_angle = self.posture_slouch_estimate(results.pose_landmarks, image_w, image_h)
            is_good_posture = slouch_angle <= 20.0
            
            if is_good_posture:
                feedback_messages.append("✓ Good posture")
            else:
                feedback_messages.append("✗ Slouching detected")
        
        # Calculate confidence score
        confidence_score = 50
        if presence:
            confidence_score += 30
        if eye_contact == "good":
            confidence_score += 20
        if is_good_posture:
            confidence_score += 10
        confidence_score = max(0, min(100, confidence_score))
        
        # Overall feedback
        if confidence_score >= 80:
            overall = "😊 Excellent! Keep it up"
        elif confidence_score >= 60:
            overall = "🙂 Good, minor improvements needed"
        elif confidence_score >= 40:
            overall = "😐 Needs improvement"
        else:
            overall = "😟 Please improve your presence and engagement"
        
        # === DRAW ALL METRICS ON FRAME ===
        
        # Header background
        cv2.rectangle(frame, (0, 0), (image_w, 60), (0, 0, 0), -1)
        
        # Title
        cv2.putText(frame, "Interview Behavior Analysis", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Confidence bar
        self.draw_text_with_background(frame, "Confidence:", (10, 55), 
                                       font_scale=0.5, bg_color=(40, 40, 40))
        self.draw_confidence_bar(frame, confidence_score, 120, 40)
        
        # Status indicators
        y_offset = 100
        self.draw_status_indicator(frame, 'good' if presence else 'poor', 
                                   "Presence", 10, y_offset)
        self.draw_status_indicator(frame, eye_contact, 
                                   "Eye Contact", 10, y_offset + 30)
        self.draw_status_indicator(frame, 'good' if is_good_posture else 'poor', 
                                   "Posture", 10, y_offset + 60)
        
        # Metrics panel (right side)
        panel_x = image_w - 250
        panel_y = 80
        
        # Draw semi-transparent panel
        overlay = frame.copy()
        cv2.rectangle(overlay, (panel_x - 10, panel_y - 10), 
                     (image_w - 10, panel_y + 200), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Metrics text
        cv2.putText(frame, "METRICS", (panel_x, panel_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        cv2.putText(frame, f"Head Yaw: {head_pose['yaw']:.1f}°", (panel_x, panel_y + 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Head Pitch: {head_pose['pitch']:.1f}°", (panel_x, panel_y + 55),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Slouch: {slouch_angle:.1f}°", (panel_x, panel_y + 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Score: {confidence_score}/100", (panel_x, panel_y + 105),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0) if confidence_score >= 70 else (0, 255, 255), 1)
        
        # Feedback messages (bottom)
        feedback_y = image_h - 120
        cv2.rectangle(frame, (0, feedback_y - 10), (image_w, image_h), (0, 0, 0), -1)
        
        cv2.putText(frame, overall, (10, feedback_y + 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        for i, msg in enumerate(feedback_messages[:3]):
            cv2.putText(frame, msg, (10, feedback_y + 40 + i * 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Return both annotated frame and metrics
        return frame, {
            "presence": presence,
            "eye_contact": eye_contact,
            "confidence_score": confidence_score,
            "posture": {
                "slouch_angle": slouch_angle,
                "is_good": is_good_posture
            },
            "head_pose": head_pose,
            "feedback": feedback_messages,
            "overall": overall,
            "timestamp": now
        }
    
    def process_base64_frame(self, base64_image):
        """Process base64 image and return metrics (for API)"""
        try:
            if "base64," in base64_image:
                base64_image = base64_image.split("base64,")[1]
            
            img_bytes = base64.b64decode(base64_image)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return {"error": "Failed to decode image"}
            
            # Get metrics without visualization (for API response)
            _, metrics = self.analyze_frame_with_visualization(frame)
            return metrics
            
        except Exception as e:
            return {"error": str(e)}
    
    def close(self):
        """Cleanup resources"""
        self.holistic.close()
