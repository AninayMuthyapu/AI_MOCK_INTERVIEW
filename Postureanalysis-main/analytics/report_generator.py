"""
Report Generator module.
Generates structured session reports in JSON format.
"""

import json
import time
from typing import Dict, Any, Optional
from datetime import datetime


class ReportGenerator:
    """
    Generates structured session reports for analysis and integration.
    """
    
    def __init__(self):
        """Initialize report generator."""
        self.session_id: Optional[str] = None
    
    def generate_report(
        self,
        analytics_summary: Dict[str, Any],
        time_series_data: Optional[Dict] = None,
        include_time_series: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive session report.
        
        Args:
            analytics_summary: Summary from SessionAnalytics.get_summary()
            time_series_data: Optional time-series data from SessionAnalytics
            include_time_series: Whether to include detailed time-series data
            
        Returns:
            Structured report dictionary.
        """
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "report_version": "1.0",
                "session_id": self.session_id or self._generate_session_id()
            },
            "session_summary": {
                "duration_seconds": analytics_summary.get("session_duration_seconds", 0),
                "frames_analyzed": analytics_summary.get("total_frames_analyzed", 0)
            },
            "behavioral_metrics": {
                "confidence": {
                    "average_score": analytics_summary.get("average_confidence_score", 0),
                    "label": self._get_confidence_label(
                        analytics_summary.get("average_confidence_score", 0)
                    )
                },
                "eye_contact": {
                    "percentage": analytics_summary.get("eye_contact_percentage", 0),
                    "rating": self._get_rating(
                        analytics_summary.get("eye_contact_percentage", 0)
                    )
                },
                "posture": {
                    "quality_score": analytics_summary.get("posture_quality_score", 0),
                    "rating": self._get_rating(
                        analytics_summary.get("posture_quality_score", 0)
                    )
                },
                "stability": {
                    "movement_score": analytics_summary.get("movement_stability_score", 0),
                    "rating": self._get_rating(
                        analytics_summary.get("movement_stability_score", 0)
                    )
                }
            },
            "behavioral_events": {
                "distraction_events": analytics_summary.get("distraction_events", 0)
            },
            "overall_assessment": {
                "readiness_score": analytics_summary.get("overall_readiness_score", 0),
                "readiness_label": self._get_readiness_label(
                    analytics_summary.get("overall_readiness_score", 0)
                ),
                "recommendations": self._generate_recommendations(analytics_summary)
            }
        }
        
        if include_time_series and time_series_data:
            report["time_series"] = time_series_data
        
        return report
    
    def generate_json_report(
        self,
        analytics_summary: Dict[str, Any],
        time_series_data: Optional[Dict] = None,
        include_time_series: bool = False,
        pretty: bool = True
    ) -> str:
        """
        Generate JSON-formatted report string.
        
        Args:
            analytics_summary: Summary from SessionAnalytics
            time_series_data: Optional time-series data
            include_time_series: Whether to include time-series
            pretty: Whether to format JSON nicely
            
        Returns:
            JSON string.
        """
        report = self.generate_report(
            analytics_summary, 
            time_series_data, 
            include_time_series
        )
        
        if pretty:
            return json.dumps(report, indent=2, default=str)
        return json.dumps(report, default=str)
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        timestamp = int(time.time() * 1000)
        return f"session_{timestamp}"
    
    def _get_confidence_label(self, score: float) -> str:
        """Get descriptive label for confidence score."""
        if score >= 85:
            return "High Confidence"
        elif score >= 65:
            return "Moderate Confidence"
        else:
            return "Low Confidence"
    
    def _get_rating(self, score: float) -> str:
        """Get rating label for percentage scores."""
        if score >= 80:
            return "Excellent"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Fair"
        else:
            return "Needs Improvement"
    
    def _get_readiness_label(self, score: float) -> str:
        """Get overall readiness label."""
        if score >= 80:
            return "Highly Ready"
        elif score >= 60:
            return "Moderately Ready"
        elif score >= 40:
            return "Partially Ready"
        else:
            return "Needs Preparation"
    
    def _generate_recommendations(self, summary: Dict[str, Any]) -> list:
        """Generate personalized recommendations based on metrics."""
        recommendations = []
        
        eye_contact = summary.get("eye_contact_percentage", 100)
        if eye_contact < 60:
            recommendations.append(
                "Practice maintaining eye contact with the camera. "
                "Try placing a small sticker near your webcam as a focus point."
            )
        
        posture = summary.get("posture_quality_score", 100)
        if posture < 60:
            recommendations.append(
                "Work on your sitting posture. Sit with your back straight, "
                "shoulders relaxed, and ensure your screen is at eye level."
            )
        
        movement = summary.get("movement_stability_score", 100)
        if movement < 60:
            recommendations.append(
                "Try to minimize unnecessary movements. Take deep breaths "
                "before speaking to help stay calm and composed."
            )
        
        distractions = summary.get("distraction_events", 0)
        if distractions > 3:
            recommendations.append(
                "You looked away from the screen multiple times. "
                "In a real interview, maintain consistent attention to show engagement."
            )
        
        if not recommendations:
            recommendations.append(
                "Great job! Continue practicing to maintain this level of performance."
            )
        
        return recommendations
    
    def set_session_id(self, session_id: str):
        """Set a custom session ID."""
        self.session_id = session_id
