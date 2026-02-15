"""
Camera capture module for the Behavioral Analysis Engine.
Handles webcam input, frame processing, and resource management.
"""

import cv2
import time
from typing import Optional, Tuple
import config


class CameraCapture:
    """
    Handles webcam capture with adaptive frame rate and resource management.
    """
    
    def __init__(
        self,
        camera_index: int = config.CAMERA_INDEX,
        width: int = config.CAMERA_WIDTH,
        height: int = config.CAMERA_HEIGHT,
        target_fps: int = config.CAMERA_FPS
    ):
        """
        Initialize camera capture.
        
        Args:
            camera_index: Camera device index (0 for default webcam)
            width: Frame width in pixels
            height: Frame height in pixels
            target_fps: Target frames per second
        """
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.last_frame_time = 0.0
        self.is_running = False
        self.frame_count = 0
        self.start_time = 0.0
    
    def start(self) -> bool:
        """
        Start the camera capture.
        
        Returns:
            True if camera started successfully, False otherwise.
        """
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            
            if not self.cap.isOpened():
                print(f"Error: Could not open camera {self.camera_index}")
                return False
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            
            # Verify actual settings
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            print(f"Camera started: {actual_width}x{actual_height} @ {actual_fps:.1f} FPS")
            
            self.is_running = True
            self.start_time = time.time()
            self.frame_count = 0
            
            return True
            
        except Exception as e:
            print(f"Error starting camera: {e}")
            return False
    
    def read_frame(self) -> Tuple[bool, Optional[any]]:
        """
        Read a frame from the camera with frame rate limiting.
        
        Returns:
            Tuple of (success, frame). Frame is None if capture failed.
        """
        if not self.is_running or self.cap is None:
            return False, None
        
        # Frame rate limiting
        current_time = time.time()
        elapsed = current_time - self.last_frame_time
        
        if elapsed < self.frame_interval:
            time.sleep(self.frame_interval - elapsed)
        
        ret, frame = self.cap.read()
        
        if ret:
            self.last_frame_time = time.time()
            self.frame_count += 1
            # Flip horizontally for mirror effect
            frame = cv2.flip(frame, 1)
        
        return ret, frame
    
    def get_fps(self) -> float:
        """
        Get the actual FPS based on frame count and elapsed time.
        
        Returns:
            Current frames per second.
        """
        if self.start_time == 0:
            return 0.0
        
        elapsed = time.time() - self.start_time
        if elapsed > 0:
            return self.frame_count / elapsed
        return 0.0
    
    def get_frame_dimensions(self) -> Tuple[int, int]:
        """
        Get the current frame dimensions.
        
        Returns:
            Tuple of (width, height).
        """
        if self.cap is not None:
            return (
                int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            )
        return (self.width, self.height)
    
    def stop(self):
        """
        Stop the camera capture and release resources.
        """
        self.is_running = False
        
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        elapsed = time.time() - self.start_time if self.start_time > 0 else 0
        print(f"Camera stopped. Processed {self.frame_count} frames in {elapsed:.1f}s")
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
