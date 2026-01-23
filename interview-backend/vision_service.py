"""
Enhanced Vision Service - Accurate Real-time Behavior Analysis
Improved with:
- Stricter eye contact thresholds
- Iris-based gaze direction
- Eye Aspect Ratio for blink/liveness detection
- Temporal smoothing for stable scores
"""

import cv2
import numpy as np
import time
import base64
from typing import Dict, List, Tuple, Optional
from collections import deque
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
    """Enhanced vision service with accurate confidence scoring."""
    
    # Stricter thresholds for eye contact
    EYE_CONTACT_GOOD_THRESHOLD = 8       # degrees (was 15)
    EYE_CONTACT_MODERATE_THRESHOLD = 15  # degrees (was 30)
    EYE_CONTACT_AWAY_THRESHOLD = 25      # degrees (was not defined)
    
    # Posture thresholds
    GOOD_POSTURE_THRESHOLD = 15.0        # degrees (was 20)
    
    # Eye Aspect Ratio thresholds for blink detection
    EAR_BLINK_THRESHOLD = 0.2            # Below this = eyes closed
    EAR_OPEN_THRESHOLD = 0.25            # Above this = eyes open
    
    # Temporal smoothing parameters
    SMOOTHING_WINDOW = 5                 # Number of frames to average
    
    # MediaPipe landmark indices for eyes
    # Left eye landmarks
    LEFT_EYE_LANDMARKS = [33, 160, 158, 133, 153, 144]
    # Right eye landmarks
    RIGHT_EYE_LANDMARKS = [362, 385, 387, 263, 373, 380]
    # Iris landmarks (center of each iris)
    LEFT_IRIS_CENTER = 468
    RIGHT_IRIS_CENTER = 473
    
    def __init__(self):
        self.enabled = MEDIAPIPE_AVAILABLE
        self.last_face_time = time.time()
        
        # Temporal smoothing buffers
        self.confidence_history: deque = deque(maxlen=self.SMOOTHING_WINDOW)
        self.ear_history: deque = deque(maxlen=self.SMOOTHING_WINDOW)
        self.gaze_history: deque = deque(maxlen=self.SMOOTHING_WINDOW)
        
        # Blink detection
        self.blink_count = 0
        self.last_blink_time = time.time()
        self.eyes_were_closed = False
        
        if MEDIAPIPE_AVAILABLE and MEDIAPIPE_LEGACY:
            self.mp_holistic = mp.solutions.holistic
            self.mp_face_mesh = mp.solutions.face_mesh
            self.mp_drawing = mp.solutions.drawing_utils
            self.mp_drawing_styles = mp.solutions.drawing_styles
            
            # Use holistic for pose + face landmarks
            self.holistic = self.mp_holistic.Holistic(
                static_image_mode=False,
                model_complexity=1,
                min_detection_confidence=0.5,  # Increased from 0.2
                min_tracking_confidence=0.5,   # Increased from 0.2
                refine_face_landmarks=True,    # Enable iris tracking
            )
        else:
            self.mp_holistic = None
            self.mp_face_mesh = None
            self.mp_drawing = None
            self.mp_drawing_styles = None
            self.holistic = None
            logger.info("VisionService running in disabled mode (no mediapipe)")

    def calculate_eye_aspect_ratio(self, eye_landmarks: List, all_landmarks) -> float:
        """
        Calculate Eye Aspect Ratio (EAR) to detect blinks and verify real eyes.
        EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)
        Where p1-p6 are the 6 eye landmarks.
        
        Real eyes blink regularly (EAR drops to ~0.1-0.2 during blink).
        Photos/static images have constant EAR.
        """
        try:
            # Get the 6 landmark coordinates
            p1 = np.array([all_landmarks.landmark[eye_landmarks[0]].x, 
                          all_landmarks.landmark[eye_landmarks[0]].y])
            p2 = np.array([all_landmarks.landmark[eye_landmarks[1]].x, 
                          all_landmarks.landmark[eye_landmarks[1]].y])
            p3 = np.array([all_landmarks.landmark[eye_landmarks[2]].x, 
                          all_landmarks.landmark[eye_landmarks[2]].y])
            p4 = np.array([all_landmarks.landmark[eye_landmarks[3]].x, 
                          all_landmarks.landmark[eye_landmarks[3]].y])
            p5 = np.array([all_landmarks.landmark[eye_landmarks[4]].x, 
                          all_landmarks.landmark[eye_landmarks[4]].y])
            p6 = np.array([all_landmarks.landmark[eye_landmarks[5]].x, 
                          all_landmarks.landmark[eye_landmarks[5]].y])
            
            # Calculate vertical distances
            vertical1 = np.linalg.norm(p2 - p6)
            vertical2 = np.linalg.norm(p3 - p5)
            
            # Calculate horizontal distance
            horizontal = np.linalg.norm(p1 - p4)
            
            if horizontal == 0:
                return 0.3  # Default to open
                
            ear = (vertical1 + vertical2) / (2.0 * horizontal)
            return float(ear)
            
        except Exception as e:
            logger.debug(f"EAR calculation error: {e}")
            return 0.3  # Default to open
    
    def calculate_gaze_direction(self, face_landmarks, image_w: int, image_h: int) -> Dict[str, float]:
        """
        Calculate gaze direction using iris position relative to eye corners.
        More accurate than head pose alone for determining where user is looking.
        """
        try:
            # Get iris centers (available with refine_face_landmarks=True)
            left_iris = face_landmarks.landmark[self.LEFT_IRIS_CENTER]
            right_iris = face_landmarks.landmark[self.RIGHT_IRIS_CENTER]
            
            # Get eye corners for reference
            left_eye_inner = face_landmarks.landmark[133]
            left_eye_outer = face_landmarks.landmark[33]
            right_eye_inner = face_landmarks.landmark[362]
            right_eye_outer = face_landmarks.landmark[263]
            
            # Calculate horizontal gaze ratio for each eye
            # 0 = looking far left, 0.5 = center, 1 = looking far right
            left_eye_width = abs(left_eye_outer.x - left_eye_inner.x)
            right_eye_width = abs(right_eye_outer.x - right_eye_inner.x)
            
            if left_eye_width > 0:
                left_gaze_ratio = (left_iris.x - left_eye_outer.x) / left_eye_width
            else:
                left_gaze_ratio = 0.5
                
            if right_eye_width > 0:
                right_gaze_ratio = (right_iris.x - right_eye_inner.x) / right_eye_width
            else:
                right_gaze_ratio = 0.5
            
            # Average gaze ratio (0.5 = looking at camera)
            gaze_ratio = (left_gaze_ratio + right_gaze_ratio) / 2
            
            # Calculate vertical gaze using iris Y position relative to eye height
            left_eye_top = face_landmarks.landmark[159]
            left_eye_bottom = face_landmarks.landmark[145]
            left_eye_height = abs(left_eye_top.y - left_eye_bottom.y)
            
            if left_eye_height > 0:
                vertical_gaze = (left_iris.y - left_eye_top.y) / left_eye_height
            else:
                vertical_gaze = 0.5
            
            # Convert to deviation from center (0 = looking at camera)
            horizontal_deviation = abs(gaze_ratio - 0.5) * 100  # 0-50 scale
            vertical_deviation = abs(vertical_gaze - 0.5) * 100  # 0-50 scale
            
            return {
                "horizontal_deviation": float(horizontal_deviation),
                "vertical_deviation": float(vertical_deviation),
                "gaze_ratio": float(gaze_ratio),
                "vertical_gaze": float(vertical_gaze)
            }
            
        except Exception as e:
            logger.debug(f"Gaze calculation error: {e}")
            return {
                "horizontal_deviation": 25.0,
                "vertical_deviation": 25.0,
                "gaze_ratio": 0.5,
                "vertical_gaze": 0.5
            }
    
    def head_direction_estimate(self, face_landmarks, image_w: int, image_h: int) -> Dict[str, float]:
        """Calculate head pose angles from face landmarks."""
        try:
            nose = face_landmarks.landmark[1]
            chin = face_landmarks.landmark[152]
            left_eye = face_landmarks.landmark[33]
            right_eye = face_landmarks.landmark[263]
            
            yaw = np.degrees(np.arctan2(right_eye.y - left_eye.y, right_eye.x - left_eye.x))
            pitch = np.degrees(np.arctan2(nose.y - chin.y, 
                                          np.sqrt((nose.x - chin.x)**2 + (nose.z - chin.z)**2)))
            
            return {"yaw": float(yaw), "pitch": float(pitch)}
        except Exception as e:
            logger.debug(f"Head pose calculation error: {e}")
            return {"yaw": 0.0, "pitch": 0.0}
    
    def posture_slouch_estimate(self, pose_landmarks, image_w: int, image_h: int) -> float:
        """Calculate slouch angle from shoulders to hips."""
        try:
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
        except Exception as e:
            logger.debug(f"Posture calculation error: {e}")
            return 0.0
    
    def temporal_smooth_confidence(self, raw_score: float) -> float:
        """Apply weighted moving average for stable confidence scores."""
        self.confidence_history.append(raw_score)
        
        if len(self.confidence_history) == 0:
            return raw_score
        
        # Exponential weights - recent scores matter more
        weights = [1.0, 1.5, 2.0, 2.5, 3.0][:len(self.confidence_history)]
        weighted_sum = sum(s * w for s, w in zip(self.confidence_history, weights))
        weight_total = sum(weights)
        
        return weighted_sum / weight_total if weight_total > 0 else raw_score
    
    def detect_liveness(self, ear: float) -> Tuple[bool, bool]:
        """
        Detect if user is real (not a photo) by tracking blinks.
        Returns: (is_likely_real, eyes_currently_open)
        """
        now = time.time()
        eyes_open = ear > self.EAR_OPEN_THRESHOLD
        eyes_closed = ear < self.EAR_BLINK_THRESHOLD
        
        # Detect blink transition
        if self.eyes_were_closed and eyes_open:
            self.blink_count += 1
            self.last_blink_time = now
            
        self.eyes_were_closed = eyes_closed
        
        # Real person blinks every 2-10 seconds typically
        # If we've seen blinks, more likely to be real
        time_since_blink = now - self.last_blink_time
        is_likely_real = self.blink_count > 0 or time_since_blink < 15.0
        
        return is_likely_real, eyes_open
    
    def calculate_confidence_score(
        self,
        presence: bool,
        eye_contact: str,
        is_good_posture: bool,
        ear: float,
        gaze: Dict[str, float],
        is_likely_real: bool
    ) -> int:
        """
        Calculate confidence score starting from 0.
        Each positive behavior adds points.
        """
        score = 0
        
        # Face presence (0-20 points)
        if presence:
            score += 20
        
        # Eye contact based on gaze (0-30 points)
        gaze_deviation = max(gaze["horizontal_deviation"], gaze["vertical_deviation"])
        if gaze_deviation < 10:  # Looking directly at camera
            score += 30
            eye_contact = "good"
        elif gaze_deviation < 20:  # Close to camera
            score += 20
            eye_contact = "moderate"
        elif gaze_deviation < 35:  # Slightly off
            score += 10
            eye_contact = "moderate"
        else:  # Looking away
            eye_contact = "away"
        
        # Eyes open and liveness (0-20 points)
        if ear > self.EAR_OPEN_THRESHOLD:
            score += 10
        if is_likely_real:
            score += 10
        
        # Good posture (0-10 points)
        if is_good_posture:
            score += 10
        
        # Head pose bonus (0-10 points) - rewards facing camera
        # Already factored into presence, skip for now
        score += 0  # Reserved for future use
        
        # Clamp to 0-100
        return max(0, min(100, score))
    
    def draw_text_with_background(self, img, text, pos, font_scale=0.6, 
                                   thickness=2, text_color=(255, 255, 255), 
                                   bg_color=(0, 0, 0), padding=5):
        """Draw text with background rectangle."""
        font = cv2.FONT_HERSHEY_SIMPLEX
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        
        x, y = pos
        cv2.rectangle(img, 
                     (x - padding, y - text_height - padding),
                     (x + text_width + padding, y + baseline + padding),
                     bg_color, -1)
        cv2.putText(img, text, (x, y), font, font_scale, text_color, thickness)
        
    def draw_confidence_bar(self, img, confidence, x, y, width=200, height=20):
        """Draw confidence score as progress bar."""
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
        """Draw colored status circle with label."""
        colors = {
            'good': (0, 255, 0),
            'moderate': (0, 255, 255),
            'away': (0, 128, 255),
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
    
    def analyze_frame_with_visualization(self, frame):
        """Analyze frame and draw all metrics on it."""
        image_h, image_w = frame.shape[:2]
        now = time.time()
        
        # If mediapipe is not available, return default metrics
        if not self.enabled or self.holistic is None:
            return frame, {
                "presence": False,
                "eye_contact": "unknown",
                "confidence_score": 0,  # Start from 0, not 50
                "posture": {"slouch_angle": 0.0, "is_good": True},
                "head_pose": {"yaw": 0.0, "pitch": 0.0},
                "gaze": {"horizontal_deviation": 50.0, "vertical_deviation": 50.0},
                "ear": 0.0,
                "is_likely_real": False,
                "blink_count": 0,
                "feedback": ["⚠ Vision analysis unavailable (mediapipe not configured)"],
                "overall": "Vision analysis disabled",
                "timestamp": now
            }
        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.holistic.process(rgb)
        
        # Initialize metrics
        presence = False
        eye_contact = "unknown"
        slouch_angle = 0.0
        is_good_posture = True
        head_pose = {"yaw": 0.0, "pitch": 0.0}
        gaze = {"horizontal_deviation": 50.0, "vertical_deviation": 50.0, "gaze_ratio": 0.5, "vertical_gaze": 0.5}
        ear = 0.3
        is_likely_real = False
        eyes_open = True
        feedback_messages = []
        
        logger.debug(f"[VisionService] Frame: {image_w}x{image_h}, Face: {results.face_landmarks is not None}, Pose: {results.pose_landmarks is not None}")
        
        # Process face landmarks if detected
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
            
            # Calculate Eye Aspect Ratio
            left_ear = self.calculate_eye_aspect_ratio(self.LEFT_EYE_LANDMARKS, results.face_landmarks)
            right_ear = self.calculate_eye_aspect_ratio(self.RIGHT_EYE_LANDMARKS, results.face_landmarks)
            ear = (left_ear + right_ear) / 2.0
            
            # Detect liveness through blinking
            is_likely_real, eyes_open = self.detect_liveness(ear)
            
            # Calculate gaze direction using iris tracking
            gaze = self.calculate_gaze_direction(results.face_landmarks, image_w, image_h)
            
            # Calculate head pose
            head_pose = self.head_direction_estimate(results.face_landmarks, image_w, image_h)
            
            # Determine eye contact quality based on gaze
            gaze_deviation = max(gaze["horizontal_deviation"], gaze["vertical_deviation"])
            if gaze_deviation < 10:
                eye_contact = "good"
                feedback_messages.append("✓ Excellent eye contact")
            elif gaze_deviation < 25:
                eye_contact = "moderate"
                feedback_messages.append("⚠ Maintain eye contact with camera")
            else:
                eye_contact = "away"
                feedback_messages.append("✗ Looking away from camera")
            
            # Liveness feedback
            if not eyes_open:
                feedback_messages.append("⚠ Eyes appear closed")
            elif is_likely_real:
                feedback_messages.append(f"✓ Blink count: {self.blink_count}")
        else:
            if now - self.last_face_time > 2.0:
                feedback_messages.append("✗ Face not detected - check camera position")
        
        # Process pose if detected
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
            is_good_posture = slouch_angle <= self.GOOD_POSTURE_THRESHOLD
            
            if is_good_posture:
                feedback_messages.append("✓ Good posture")
            else:
                feedback_messages.append(f"✗ Slouching detected ({slouch_angle:.0f}°)")
        
        # Calculate raw confidence score
        raw_confidence = self.calculate_confidence_score(
            presence, eye_contact, is_good_posture, ear, gaze, is_likely_real
        )
        
        # Apply temporal smoothing
        confidence_score = int(self.temporal_smooth_confidence(raw_confidence))
        
        # Overall feedback message
        if confidence_score >= 80:
            overall = "😊 Excellent! Professional presence"
        elif confidence_score >= 60:
            overall = "🙂 Good, minor improvements needed"
        elif confidence_score >= 40:
            overall = "😐 Needs attention - improve eye contact"
        else:
            overall = "😟 Look at the camera and sit straight"
        
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
        self.draw_status_indicator(frame, 'good' if is_likely_real else 'moderate', 
                                   "Liveness", 10, y_offset + 90)
        
        # Metrics panel (right side)
        panel_x = image_w - 280
        panel_y = 80
        
        # Draw semi-transparent panel
        overlay = frame.copy()
        cv2.rectangle(overlay, (panel_x - 10, panel_y - 10), 
                     (image_w - 10, panel_y + 220), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Metrics text
        cv2.putText(frame, "DETAILED METRICS", (panel_x, panel_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        cv2.putText(frame, f"Head Yaw: {head_pose['yaw']:.1f}°", (panel_x, panel_y + 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Head Pitch: {head_pose['pitch']:.1f}°", (panel_x, panel_y + 55),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Gaze H-Dev: {gaze['horizontal_deviation']:.1f}%", (panel_x, panel_y + 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Gaze V-Dev: {gaze['vertical_deviation']:.1f}%", (panel_x, panel_y + 105),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Eye Aspect Ratio: {ear:.2f}", (panel_x, panel_y + 130),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Slouch Angle: {slouch_angle:.1f}°", (panel_x, panel_y + 155),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Blinks: {self.blink_count}", (panel_x, panel_y + 180),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        score_color = (0, 255, 0) if confidence_score >= 70 else (0, 255, 255) if confidence_score >= 40 else (0, 0, 255)
        cv2.putText(frame, f"Score: {confidence_score}/100", (panel_x, panel_y + 205),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, score_color, 2)
        
        # Feedback messages (bottom)
        feedback_y = image_h - 140
        cv2.rectangle(frame, (0, feedback_y - 10), (image_w, image_h), (0, 0, 0), -1)
        
        cv2.putText(frame, overall, (10, feedback_y + 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        for i, msg in enumerate(feedback_messages[:4]):
            color = (0, 255, 0) if msg.startswith("✓") else (0, 255, 255) if msg.startswith("⚠") else (100, 100, 255)
            cv2.putText(frame, msg, (10, feedback_y + 40 + i * 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
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
            "gaze": gaze,
            "ear": ear,
            "is_likely_real": is_likely_real,
            "blink_count": self.blink_count,
            "feedback": feedback_messages,
            "overall": overall,
            "timestamp": now
        }
    
    def process_base64_frame(self, base64_image: str) -> Dict:
        """Process base64 image and return metrics (for API)."""
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
            logger.error(f"Frame processing error: {e}")
            return {"error": str(e)}
    
    def reset_session(self):
        """Reset session-specific tracking (call when new interview starts)."""
        self.blink_count = 0
        self.last_blink_time = time.time()
        self.eyes_were_closed = False
        self.confidence_history.clear()
        self.ear_history.clear()
        self.gaze_history.clear()
    
    def close(self):
        """Cleanup resources."""
        if self.holistic:
            self.holistic.close()
