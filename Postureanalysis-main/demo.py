"""
Demo Application for Behavioral Analysis Engine.
Provides live visualization with real-time overlays.
"""

import cv2
import numpy as np
import time
import json
from engine import BehaviorAnalysisEngine


class BehaviorAnalysisDemo:
    """
    Demo application with live visualization.
    Shows confidence score, posture status, and feedback overlays.
    """
    
    # Colors (BGR format)
    COLOR_GREEN = (0, 255, 0)
    COLOR_YELLOW = (0, 255, 255)
    COLOR_RED = (0, 0, 255)
    COLOR_WHITE = (255, 255, 255)
    COLOR_BLACK = (0, 0, 0)
    COLOR_BLUE = (255, 150, 0)
    
    def __init__(self):
        """Initialize the demo application."""
        self.engine = BehaviorAnalysisEngine(use_camera=True)
        self.window_name = "Behavioral Analysis Engine - Demo"
        self.last_analysis = None
        
        # UI settings
        self.show_landmarks = True
        self.show_metrics = True
        self.show_feedback = True
    
    def run(self):
        """Run the demo application."""
        print("\n" + "="*60)
        print("Behavioral Analysis Engine - Demo")
        print("="*60)
        print("\nControls:")
        print("  'q' - Quit and generate report")
        print("  'l' - Toggle landmarks display")
        print("  'm' - Toggle metrics display")
        print("  'f' - Toggle feedback display")
        print("  'r' - Reset session")
        print("\n" + "="*60 + "\n")
        
        # Start camera
        if not self.engine.camera.start():
            print("Error: Could not start camera")
            return
        
        # Start session
        self.engine.start_session()
        
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 960, 720)
        
        try:
            while True:
                # Capture frame
                ret, frame = self.engine.camera.read_frame()
                
                if not ret:
                    print("Error: Could not read frame")
                    break
                
                # Analyze frame
                analysis = self.engine.analyze_frame(frame)
                self.last_analysis = analysis
                
                # Draw overlays
                display_frame = self._draw_overlays(frame, analysis)
                
                # Show frame
                cv2.imshow(self.window_name, display_frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    break
                elif key == ord('l'):
                    self.show_landmarks = not self.show_landmarks
                    print(f"Landmarks: {'ON' if self.show_landmarks else 'OFF'}")
                elif key == ord('m'):
                    self.show_metrics = not self.show_metrics
                    print(f"Metrics: {'ON' if self.show_metrics else 'OFF'}")
                elif key == ord('f'):
                    self.show_feedback = not self.show_feedback
                    print(f"Feedback: {'ON' if self.show_feedback else 'OFF'}")
                elif key == ord('r'):
                    self.engine.reset()
                    self.engine.start_session()
                    print("Session reset")
        
        finally:
            # End session and get report
            report = self.engine.end_session()
            
            # Cleanup
            cv2.destroyAllWindows()
            self.engine.close()
            
            # Print report
            self._print_report(report)
    
    def _draw_overlays(self, frame: np.ndarray, analysis: dict) -> np.ndarray:
        """Draw all overlays on the frame."""
        display = frame.copy()
        h, w = display.shape[:2]
        
        # Draw landmarks if enabled
        if self.show_landmarks:
            display = self._draw_landmarks(display, analysis)
        
        # Draw metrics panel if enabled
        if self.show_metrics:
            display = self._draw_metrics_panel(display, analysis)
        
        # Draw feedback if enabled
        if self.show_feedback:
            display = self._draw_feedback(display, analysis)
        
        # Draw confidence bar
        display = self._draw_confidence_bar(display, analysis)
        
        # Draw status indicators
        display = self._draw_status_indicators(display, analysis)
        
        return display
    
    def _draw_landmarks(self, frame: np.ndarray, analysis: dict) -> np.ndarray:
        """Draw pose and face landmarks on the frame."""
        h, w = frame.shape[:2]
        
        # Draw face bounding box
        face_data = analysis["detections"]["face"]
        if face_data.get("face_present"):
            bb = face_data["bounding_box"]
            x = int(bb["x"] * w)
            y = int(bb["y"] * h)
            bw = int(bb["width"] * w)
            bh = int(bb["height"] * h)
            cv2.rectangle(frame, (x, y), (x + bw, y + bh), self.COLOR_GREEN, 2)
        
        # Draw pose landmarks
        pose_data = analysis["detections"]["pose"]
        if pose_data.get("pose_detected"):
            landmarks = pose_data.get("landmarks", {})
            for name, lm in landmarks.items():
                if lm is not None:
                    x = int(lm["x"] * w)
                    y = int(lm["y"] * h)
                    cv2.circle(frame, (x, y), 5, self.COLOR_BLUE, -1)
            
            # Draw shoulder line
            if landmarks.get("left_shoulder") and landmarks.get("right_shoulder"):
                ls = landmarks["left_shoulder"]
                rs = landmarks["right_shoulder"]
                cv2.line(
                    frame,
                    (int(ls["x"] * w), int(ls["y"] * h)),
                    (int(rs["x"] * w), int(rs["y"] * h)),
                    self.COLOR_YELLOW, 2
                )
        
        return frame
    
    def _draw_metrics_panel(self, frame: np.ndarray, analysis: dict) -> np.ndarray:
        """Draw metrics panel on the right side."""
        h, w = frame.shape[:2]
        
        # Semi-transparent panel
        panel_w = 200
        panel_h = 180
        panel_x = w - panel_w - 10
        panel_y = 10
        
        overlay = frame.copy()
        cv2.rectangle(
            overlay, 
            (panel_x, panel_y), 
            (panel_x + panel_w, panel_y + panel_h),
            self.COLOR_BLACK, -1
        )
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Draw border
        cv2.rectangle(
            frame,
            (panel_x, panel_y),
            (panel_x + panel_w, panel_y + panel_h),
            self.COLOR_WHITE, 1
        )
        
        # Draw title
        cv2.putText(
            frame, "Metrics",
            (panel_x + 10, panel_y + 25),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLOR_WHITE, 1
        )
        
        # Draw metrics
        scores = analysis.get("scores", {})
        metrics = [
            ("Attention", scores.get("attention_score", 0.5)),
            ("Eye Contact", scores.get("eye_contact_score", 0.5)),
            ("Posture", scores.get("posture_score", 0.5)),
            ("Stability", scores.get("movement_score", 0.5)),
        ]
        
        y_offset = panel_y + 50
        for name, score in metrics:
            # Draw label
            cv2.putText(
                frame, f"{name}:",
                (panel_x + 10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.COLOR_WHITE, 1
            )
            
            # Draw bar
            bar_x = panel_x + 90
            bar_w = 100
            bar_h = 12
            
            # Background bar
            cv2.rectangle(
                frame,
                (bar_x, y_offset - 10),
                (bar_x + bar_w, y_offset + 2),
                (50, 50, 50), -1
            )
            
            # Score bar
            score_w = int(bar_w * score)
            color = self._get_score_color(score)
            cv2.rectangle(
                frame,
                (bar_x, y_offset - 10),
                (bar_x + score_w, y_offset + 2),
                color, -1
            )
            
            y_offset += 30
        
        return frame
    
    def _draw_confidence_bar(self, frame: np.ndarray, analysis: dict) -> np.ndarray:
        """Draw large confidence score bar at the bottom."""
        h, w = frame.shape[:2]
        
        confidence = analysis["scores"]["confidence"]
        score = confidence.get("score", 70)
        level = confidence.get("level")
        
        if hasattr(level, 'value'):
            level_text = level.value.replace("_", " ").title()
        else:
            level_text = str(level).replace("_", " ").title()
        
        # Bar dimensions
        bar_y = h - 50
        bar_h = 30
        margin = 20
        bar_w = w - 2 * margin
        
        # Background
        cv2.rectangle(
            frame,
            (margin, bar_y),
            (margin + bar_w, bar_y + bar_h),
            (40, 40, 40), -1
        )
        
        # Score bar
        score_w = int(bar_w * (score / 100))
        color = self._get_confidence_color(score)
        cv2.rectangle(
            frame,
            (margin, bar_y),
            (margin + score_w, bar_y + bar_h),
            color, -1
        )
        
        # Border
        cv2.rectangle(
            frame,
            (margin, bar_y),
            (margin + bar_w, bar_y + bar_h),
            self.COLOR_WHITE, 1
        )
        
        # Score text
        score_text = f"Confidence: {score:.0f}% - {level_text}"
        text_size = cv2.getTextSize(score_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
        text_x = (w - text_size[0]) // 2
        cv2.putText(
            frame, score_text,
            (text_x, bar_y + 22),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLOR_WHITE, 2
        )
        
        return frame
    
    def _draw_feedback(self, frame: np.ndarray, analysis: dict) -> np.ndarray:
        """Draw feedback message at the top."""
        feedback = analysis["feedback"]["primary"]
        
        if feedback:
            h, w = frame.shape[:2]
            
            # Background
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (w, 40), self.COLOR_BLACK, -1)
            cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
            
            # Text
            text_size = cv2.getTextSize(feedback, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
            text_x = (w - text_size[0]) // 2
            cv2.putText(
                frame, feedback,
                (text_x, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLOR_YELLOW, 1
            )
        
        return frame
    
    def _draw_status_indicators(self, frame: np.ndarray, analysis: dict) -> np.ndarray:
        """Draw status indicators in top-left corner."""
        h, w = frame.shape[:2]
        
        attention = analysis["analysis"]["attention"]
        state = attention.get("state")
        
        if hasattr(state, 'value'):
            state_value = state.value
        else:
            state_value = str(state)
        
        # Attention indicator
        if state_value == "fully_attentive":
            color = self.COLOR_GREEN
            text = "Attentive"
        elif state_value == "temporarily_distracted":
            color = self.COLOR_YELLOW
            text = "Distracted"
        else:
            color = self.COLOR_RED
            text = "Away"
        
        cv2.circle(frame, (30, 60), 10, color, -1)
        cv2.putText(
            frame, text,
            (50, 65),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.COLOR_WHITE, 1
        )
        
        # Posture indicator
        posture = analysis["analysis"]["posture"]
        quality = posture.get("posture_quality")
        
        if hasattr(quality, 'value'):
            quality_value = quality.value
        else:
            quality_value = str(quality)
        
        if quality_value == "good":
            color = self.COLOR_GREEN
            text = "Good Posture"
        elif quality_value == "acceptable":
            color = self.COLOR_YELLOW
            text = "OK Posture"
        else:
            color = self.COLOR_RED if quality_value == "poor" else (128, 128, 128)
            text = "Poor Posture" if quality_value == "poor" else "Calibrating..."
        
        cv2.circle(frame, (30, 90), 10, color, -1)
        cv2.putText(
            frame, text,
            (50, 95),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.COLOR_WHITE, 1
        )
        
        # FPS indicator
        fps = self.engine.camera.get_fps()
        cv2.putText(
            frame, f"FPS: {fps:.1f}",
            (10, h - 60),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1
        )
        
        return frame
    
    def _get_score_color(self, score: float) -> tuple:
        """Get color based on score (0-1)."""
        if score >= 0.7:
            return self.COLOR_GREEN
        elif score >= 0.4:
            return self.COLOR_YELLOW
        else:
            return self.COLOR_RED
    
    def _get_confidence_color(self, score: float) -> tuple:
        """Get color based on confidence score (0-100)."""
        if score >= 85:
            return self.COLOR_GREEN
        elif score >= 65:
            return self.COLOR_YELLOW
        else:
            return self.COLOR_RED
    
    def _print_report(self, report: dict):
        """Print the final session report."""
        print("\n" + "="*60)
        print("SESSION REPORT")
        print("="*60 + "\n")
        
        summary = report.get("session_summary", {})
        print(f"Duration: {summary.get('duration_seconds', 0):.1f} seconds")
        print(f"Frames Analyzed: {summary.get('frames_analyzed', 0)}")
        
        print("\n" + "-"*40)
        print("BEHAVIORAL METRICS")
        print("-"*40)
        
        metrics = report.get("behavioral_metrics", {})
        
        conf = metrics.get("confidence", {})
        print(f"\nConfidence Score: {conf.get('average_score', 0):.1f}%")
        print(f"  Label: {conf.get('label', 'N/A')}")
        
        eye = metrics.get("eye_contact", {})
        print(f"\nEye Contact: {eye.get('percentage', 0):.1f}%")
        print(f"  Rating: {eye.get('rating', 'N/A')}")
        
        posture = metrics.get("posture", {})
        print(f"\nPosture Quality: {posture.get('quality_score', 0):.1f}%")
        print(f"  Rating: {posture.get('rating', 'N/A')}")
        
        stability = metrics.get("stability", {})
        print(f"\nStability Score: {stability.get('movement_score', 0):.1f}%")
        print(f"  Rating: {stability.get('rating', 'N/A')}")
        
        events = report.get("behavioral_events", {})
        print(f"\nDistraction Events: {events.get('distraction_events', 0)}")
        
        print("\n" + "-"*40)
        print("OVERALL ASSESSMENT")
        print("-"*40)
        
        assessment = report.get("overall_assessment", {})
        print(f"\nReadiness Score: {assessment.get('readiness_score', 0):.1f}%")
        print(f"Readiness Level: {assessment.get('readiness_label', 'N/A')}")
        
        print("\nRecommendations:")
        for i, rec in enumerate(assessment.get("recommendations", []), 1):
            print(f"  {i}. {rec}")
        
        print("\n" + "="*60)
        
        # Also save JSON report
        json_report = json.dumps(report, indent=2, default=str)
        with open("session_report.json", "w") as f:
            f.write(json_report)
        print(f"\nFull report saved to: session_report.json")
        print("="*60 + "\n")


def main():
    """Main entry point."""
    demo = BehaviorAnalysisDemo()
    demo.run()


if __name__ == "__main__":
    main()
