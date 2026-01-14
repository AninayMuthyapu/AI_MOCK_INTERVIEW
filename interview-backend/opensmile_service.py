"""
openSMILE Voice Feature Extraction Service

Extracts acoustic features from audio for soft skills voice analysis:
- Pitch (F0): mean, variance, range for tone/intonation
- Energy: loudness statistics for emphasis/volume  
- Jitter/Shimmer: voice quality markers for confidence
- Pauses: silence detection for hesitation markers
"""

import os
import tempfile
import logging
from typing import Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Try to import opensmile - graceful fallback if not available
try:
    import opensmile
    OPENSMILE_AVAILABLE = True
    logger.info("openSMILE package loaded successfully")
except ImportError:
    OPENSMILE_AVAILABLE = False
    logger.warning("openSMILE not installed. Voice features will use AI estimation.")

# Try to import librosa as fallback for basic audio analysis
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False


class OpenSmileFeatures:
    """Container for extracted openSMILE voice features."""
    
    def __init__(self):
        # Pitch features
        self.pitch_mean: float = 0.0
        self.pitch_variance: float = 0.0
        self.pitch_range: float = 0.0
        
        # Energy features
        self.energy_mean: float = 0.0
        self.energy_variance: float = 0.0
        self.loudness_peaks: int = 0
        
        # Voice quality (confidence markers)
        self.jitter: float = 0.0  # Pitch cycle-to-cycle variation
        self.shimmer: float = 0.0  # Amplitude cycle-to-cycle variation
        
        # Temporal features
        self.speech_rate: float = 0.0  # Estimated syllables per second
        self.pause_ratio: float = 0.0  # Ratio of silence to speech
        self.pause_count: int = 0
        
        # Derived scores (0-5 scale)
        self.tone_score: float = 0.0
        self.confidence_score: float = 0.0
        self.pace_score: float = 0.0
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pitch": {
                "mean": round(self.pitch_mean, 2),
                "variance": round(self.pitch_variance, 2),
                "range": round(self.pitch_range, 2)
            },
            "energy": {
                "mean": round(self.energy_mean, 4),
                "variance": round(self.energy_variance, 6),
                "loudness_peaks": self.loudness_peaks
            },
            "voice_quality": {
                "jitter": round(self.jitter, 4),
                "shimmer": round(self.shimmer, 4)
            },
            "temporal": {
                "speech_rate": round(self.speech_rate, 2),
                "pause_ratio": round(self.pause_ratio, 3),
                "pause_count": self.pause_count
            },
            "derived_scores": {
                "tone": round(self.tone_score, 1),
                "confidence": round(self.confidence_score, 1),
                "pace": round(self.pace_score, 1)
            }
        }


class OpenSmileService:
    """Service for extracting voice features using openSMILE."""
    
    def __init__(self):
        self.smile = None
        if OPENSMILE_AVAILABLE:
            try:
                # Use eGeMAPSv02 feature set - optimized for voice analysis
                self.smile = opensmile.Smile(
                    feature_set=opensmile.FeatureSet.eGeMAPSv02,
                    feature_level=opensmile.FeatureLevel.Functionals
                )
                logger.info("openSMILE initialized with eGeMAPSv02 feature set")
            except Exception as e:
                logger.error(f"Failed to initialize openSMILE: {e}")
                self.smile = None
    
    def extract_features(self, audio_path: str) -> Optional[OpenSmileFeatures]:
        """
        Extract voice features from audio file.
        
        Args:
            audio_path: Path to audio file (wav, mp3, webm)
            
        Returns:
            OpenSmileFeatures object or None if extraction fails
        """
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return None
            
        features = OpenSmileFeatures()
        
        # Try openSMILE first
        if self.smile is not None:
            try:
                return self._extract_with_opensmile(audio_path, features)
            except Exception as e:
                logger.warning(f"openSMILE extraction failed: {e}, falling back to librosa")
        
        # Fallback to librosa for basic features
        if LIBROSA_AVAILABLE:
            try:
                return self._extract_with_librosa(audio_path, features)
            except Exception as e:
                logger.error(f"Librosa extraction failed: {e}")
        
        return None
    
    def _extract_with_opensmile(self, audio_path: str, features: OpenSmileFeatures) -> OpenSmileFeatures:
        """Extract features using openSMILE."""
        df = self.smile.process_file(audio_path)
        
        # Extract pitch features (F0)
        if 'F0semitoneFrom27.5Hz_sma3nz_amean' in df.columns:
            features.pitch_mean = float(df['F0semitoneFrom27.5Hz_sma3nz_amean'].iloc[0])
        if 'F0semitoneFrom27.5Hz_sma3nz_stddevNorm' in df.columns:
            features.pitch_variance = float(df['F0semitoneFrom27.5Hz_sma3nz_stddevNorm'].iloc[0])
        if 'F0semitoneFrom27.5Hz_sma3nz_percentile80.0' in df.columns and 'F0semitoneFrom27.5Hz_sma3nz_percentile20.0' in df.columns:
            features.pitch_range = float(df['F0semitoneFrom27.5Hz_sma3nz_percentile80.0'].iloc[0] - 
                                         df['F0semitoneFrom27.5Hz_sma3nz_percentile20.0'].iloc[0])
        
        # Extract energy features
        if 'loudness_sma3_amean' in df.columns:
            features.energy_mean = float(df['loudness_sma3_amean'].iloc[0])
        if 'loudness_sma3_stddevNorm' in df.columns:
            features.energy_variance = float(df['loudness_sma3_stddevNorm'].iloc[0])
        
        # Extract jitter/shimmer (voice quality)
        if 'jitterLocal_sma3nz_amean' in df.columns:
            features.jitter = float(df['jitterLocal_sma3nz_amean'].iloc[0])
        if 'shimmerLocaldB_sma3nz_amean' in df.columns:
            features.shimmer = float(df['shimmerLocaldB_sma3nz_amean'].iloc[0])
        
        # Calculate derived scores
        features = self._calculate_derived_scores(features)
        
        return features
    
    def _extract_with_librosa(self, audio_path: str, features: OpenSmileFeatures) -> OpenSmileFeatures:
        """Fallback: Extract basic features using librosa."""
        import librosa
        
        # Load audio
        y, sr = librosa.load(audio_path, sr=None)
        
        # Extract pitch using pyin
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7')
        )
        f0_valid = f0[~np.isnan(f0)]
        
        if len(f0_valid) > 0:
            features.pitch_mean = float(np.mean(f0_valid))
            features.pitch_variance = float(np.var(f0_valid))
            features.pitch_range = float(np.max(f0_valid) - np.min(f0_valid))
        
        # Extract RMS energy
        rms = librosa.feature.rms(y=y)[0]
        features.energy_mean = float(np.mean(rms))
        features.energy_variance = float(np.var(rms))
        features.loudness_peaks = int(np.sum(rms > np.mean(rms) + np.std(rms)))
        
        # Estimate pause ratio (silence detection)
        silence_threshold = 0.01
        is_silence = rms < silence_threshold
        features.pause_ratio = float(np.mean(is_silence))
        
        # Count pauses (transitions from speech to silence)
        silence_transitions = np.diff(is_silence.astype(int))
        features.pause_count = int(np.sum(silence_transitions == 1))
        
        # Estimate speech rate (rough approximation using onset detection)
        onsets = librosa.onset.onset_detect(y=y, sr=sr)
        duration = len(y) / sr
        features.speech_rate = len(onsets) / duration if duration > 0 else 0
        
        # Calculate derived scores
        features = self._calculate_derived_scores(features)
        
        return features
    
    def _calculate_derived_scores(self, features: OpenSmileFeatures) -> OpenSmileFeatures:
        """Calculate 0-5 scores from raw features."""
        
        # Tone score: Based on pitch variation (good variation = expressive)
        # Ideal pitch variance is moderate (not monotone, not erratic)
        if features.pitch_variance > 0:
            # Normalize variance to 0-5 (typical variance range 0-0.5)
            normalized_var = min(features.pitch_variance / 0.3, 1.0)
            # Inverted U: best score at moderate variance
            features.tone_score = 5.0 * (1.0 - abs(normalized_var - 0.5) * 2)
        else:
            features.tone_score = 2.5
        
        # Confidence score: Based on jitter/shimmer (lower = more confident)
        # High jitter/shimmer indicates nervousness
        jitter_penalty = min(features.jitter * 50, 2.5)  # Max 2.5 point penalty
        shimmer_penalty = min(features.shimmer * 2, 1.5)  # Max 1.5 point penalty
        features.confidence_score = max(0, 5.0 - jitter_penalty - shimmer_penalty)
        
        # Pace score: Based on pause ratio and speech rate
        # Ideal: moderate pauses, not too fast or slow
        pause_score = 5.0 * (1.0 - abs(features.pause_ratio - 0.2) * 3)  # Ideal ~20% pauses
        rate_score = 5.0 if 2.0 < features.speech_rate < 4.0 else 3.0  # Ideal 2-4 syllables/sec
        features.pace_score = (pause_score + rate_score) / 2
        
        # Clamp all scores to 0-5
        features.tone_score = max(0, min(5, features.tone_score))
        features.confidence_score = max(0, min(5, features.confidence_score))
        features.pace_score = max(0, min(5, features.pace_score))
        
        return features
    
    def extract_from_bytes(self, audio_bytes: bytes, format: str = "wav") -> Optional[OpenSmileFeatures]:
        """Extract features from audio bytes."""
        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name
        
        try:
            return self.extract_features(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


# Singleton instance
_service_instance: Optional[OpenSmileService] = None

def get_opensmile_service() -> OpenSmileService:
    """Get or create the openSMILE service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = OpenSmileService()
    return _service_instance
