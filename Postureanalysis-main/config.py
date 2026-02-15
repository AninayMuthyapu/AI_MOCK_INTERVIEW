"""
Configuration module for the Behavioral Analysis Engine.
Contains all thresholds, parameters, and settings.
"""

# ============================================================================
# CAMERA SETTINGS
# ============================================================================
CAMERA_INDEX = 0
CAMERA_FPS = 30
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# ============================================================================
# FACE DETECTION SETTINGS
# ============================================================================
FACE_DETECTION_CONFIDENCE = 0.5
FACE_ABSENCE_TIMEOUT = 2.0  # seconds before marking as "away from screen"
DISTRACTION_TIMEOUT = 3.0   # seconds of no face before counting as distraction

# ============================================================================
# POSE DETECTION SETTINGS
# ============================================================================
POSE_DETECTION_CONFIDENCE = 0.5
POSE_TRACKING_CONFIDENCE = 0.5

# Posture angle thresholds (in degrees)
POSTURE_UPRIGHT_THRESHOLD = 10      # Max shoulder tilt for upright
POSTURE_SLOUCH_THRESHOLD = 15       # Shoulder drop indicating slouch
POSTURE_LEAN_FORWARD_THRESHOLD = 20 # Nose too far forward
POSTURE_LEAN_BACK_THRESHOLD = 15    # Nose too far back
POSTURE_HEAD_TILT_THRESHOLD = 15    # Head tilted sideways

# ============================================================================
# GAZE TRACKING SETTINGS
# ============================================================================
FACE_MESH_CONFIDENCE = 0.5
GAZE_CENTER_THRESHOLD = 0.15        # Max deviation to count as "center"
GAZE_OFF_CENTER_TIMEOUT = 3.0       # seconds before penalizing off-center gaze
GAZE_TOLERANCE_DURATION = 0.5       # Short glances are tolerated

# ============================================================================
# MOVEMENT ANALYSIS SETTINGS
# ============================================================================
MOVEMENT_WINDOW_SIZE = 30           # Frames for rolling average
CALM_MOVEMENT_THRESHOLD = 2.0       # Max displacement for "calm"
NERVOUS_MOVEMENT_THRESHOLD = 8.0    # Displacement threshold for "highly nervous"
MICRO_MOVEMENT_THRESHOLD = 0.5      # Threshold for micro-movements

# ============================================================================
# CONFIDENCE SCORING SETTINGS
# ============================================================================
CONFIDENCE_BASELINE = 70            # Starting confidence score
CONFIDENCE_MIN = 0
CONFIDENCE_MAX = 100

# Score change rates (per second)
CONFIDENCE_BOOST_RATE = 2.0         # Points gained per second of good behavior
CONFIDENCE_DECAY_RATE = 1.5         # Points lost per second of poor behavior
CONFIDENCE_AWAY_PENALTY = 5.0       # Points lost per second when away

# Contribution weights (must sum to 1.0)
WEIGHT_FACE_PRESENCE = 0.20
WEIGHT_EYE_CONTACT = 0.25
WEIGHT_POSTURE = 0.30
WEIGHT_MOVEMENT = 0.25

# Confidence labels
HIGH_CONFIDENCE_THRESHOLD = 85
MODERATE_CONFIDENCE_THRESHOLD = 65

# ============================================================================
# FEEDBACK SETTINGS
# ============================================================================
FEEDBACK_COOLDOWN = 8.0             # Minimum seconds between same feedback
FEEDBACK_MAX_ACTIVE = 2             # Maximum active feedback messages

# Feedback messages
FEEDBACK_MESSAGES = {
    "eye_contact": "Try to maintain eye contact with the camera.",
    "posture_slouch": "Sit up straight for a more professional posture.",
    "posture_lean": "Try to sit upright, you're leaning too much.",
    "head_tilt": "Keep your head level for better eye contact.",
    "stay_calm": "Take a breath and stay calm.",
    "away": "Please return to the camera view.",
    "looking_away": "Keep your focus on the screen.",
    "great_posture": "Great posture! Keep it up.",
    "good_eye_contact": "Excellent eye contact!"
}

# ============================================================================
# ANALYTICS SETTINGS
# ============================================================================
ANALYTICS_SAMPLE_RATE = 1.0         # Sample rate in seconds for time-series data
