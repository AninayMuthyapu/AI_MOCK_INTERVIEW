"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, AlertCircle, CheckCircle } from "lucide-react";

import { API_BASE } from "@/app/lib/api";

interface BehaviorFeedback {
  presence: boolean;
  eye_contact: string;
  confidence_score: number;
  posture: {
    slouch_angle: number;
    is_good: boolean;
  };
  head_pose: {
    yaw: number;
    pitch: number;
  };
  feedback: string[];
  overall: string;
  timestamp: number;
  // Enhanced fields from posture engine
  attention_score?: number;
  attention_state?: string;
  posture_quality?: string;
  posture_score?: number;
  eye_contact_score?: number;
  gaze_direction?: string;
  movement_score?: number;
  nervousness_level?: string;
  confidence_level?: string;
}

interface BehaviorMonitorProps {
  sessionId?: string;
  isActive?: boolean;
  onFeedbackUpdate?: (feedback: BehaviorFeedback) => void;
}

export default function BehaviorMonitor({
  sessionId,
  isActive = true,
  onFeedbackUpdate
}: BehaviorMonitorProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [feedback, setFeedback] = useState<BehaviorFeedback | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const isAnalyzingRef = useRef(false);
  const errorCountRef = useRef(0);
  const maxConsecutiveErrors = 5;
  const isMountedRef = useRef(true);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  // Store callback in a ref so it never triggers effect restarts
  const onFeedbackUpdateRef = useRef(onFeedbackUpdate);
  onFeedbackUpdateRef.current = onFeedbackUpdate;

  // Track mount/unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => { isMountedRef.current = false; };
  }, []);

  // Force initialization to complete after 3 seconds
  useEffect(() => {
    const timer = setTimeout(() => {
      if (isInitializing) {
        setIsInitializing(false);
      }
    }, 3000);
    return () => clearTimeout(timer);
  }, [isInitializing]);

  // Start webcam
  useEffect(() => {
    let stream: MediaStream | null = null;

    const startWebcam = async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480 }
        });

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.onloadedmetadata = () => {
            setIsInitializing(false);
          };
        }
      } catch (err) {
        console.error("Error accessing webcam:", err);
        setError("Unable to access webcam. Please grant camera permission.");
        setIsInitializing(false);
      }
    };

    if (isActive) {
      startWebcam();
    }

    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, [isActive]);

  // Capture and analyze frames using chained setTimeout
  // (next frame only starts AFTER previous analysis finishes + delay)
  useEffect(() => {
    if (!isActive) return;
    if (!videoRef.current || !canvasRef.current) return;

    let cancelled = false;

    const analyzeFrame = async () => {
      if (cancelled || !isMountedRef.current) return;
      if (!videoRef.current || !canvasRef.current) return;

      try {
        const canvas = canvasRef.current;
        const video = videoRef.current;

        // Check if video is ready
        if (!video.videoWidth || !video.videoHeight) {
          scheduleNext();
          return;
        }

        if (isInitializing) {
          setIsInitializing(false);
        }

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        const ctx = canvas.getContext("2d");
        if (!ctx) {
          scheduleNext();
          return;
        }

        ctx.drawImage(video, 0, 0);
        const imageData = canvas.toDataURL("image/jpeg", 0.7);

        const controller = new AbortController();
        const fetchTimeout = setTimeout(() => controller.abort(), 15000);

        const response = await fetch(`${API_BASE}/api/analyze-behavior`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ image: imageData, sessionId }),
          signal: controller.signal,
        });

        clearTimeout(fetchTimeout);

        if (!response.ok) {
          throw new Error(`Analysis failed: ${response.status}`);
        }

        const data: BehaviorFeedback = await response.json();

        if (!cancelled && data && typeof data.confidence_score === 'number') {
          setFeedback(data);
          errorCountRef.current = 0;
          setError(null);
        }

        if (!cancelled && onFeedbackUpdateRef.current) {
          onFeedbackUpdateRef.current(data);
        }
      } catch (err) {
        if (cancelled) return;
        // Suppress AbortError — it's an expected timeout, not a real error
        if (err instanceof Error && err.name === 'AbortError') return;
        errorCountRef.current += 1;
        console.error(`[BehaviorMonitor] Error #${errorCountRef.current}:`, err);
        if (errorCountRef.current >= maxConsecutiveErrors) {
          setError(`Analysis error: ${err instanceof Error ? err.message : 'Unknown error'}`);
        }
      }

      // Always schedule next frame, even after errors
      scheduleNext();
    };

    const scheduleNext = () => {
      if (cancelled || !isMountedRef.current) return;
      timeoutRef.current = setTimeout(analyzeFrame, 1500);
    };

    // Initial delay then start
    timeoutRef.current = setTimeout(analyzeFrame, 500);

    return () => {
      cancelled = true;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [isActive, sessionId]); // No onFeedbackUpdate — stored in ref

  if (!isActive) {
    return (
      <div className="p-3 bg-gray-500/10 border border-gray-500/20 rounded-lg">
        <p className="text-sm text-gray-400">Behavior monitoring inactive</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Hidden video and canvas for capture */}
      <div className="hidden">
        <video ref={videoRef} autoPlay playsInline muted />
        <canvas ref={canvasRef} />
      </div>

      {/* Initializing State */}
      {isInitializing && !error && (
        <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
          <div className="flex items-center gap-3">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-400"></div>
            <div>
              <p className="text-sm text-blue-300 font-medium">Initializing camera...</p>
              <p className="text-xs text-blue-200/70">Please grant camera permission</p>
            </div>
          </div>
        </div>
      )}

      {/* Feedback Display */}
      <AnimatePresence mode="wait">
        {feedback && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="p-4 rounded-lg glass-effect border border-blue-500/30"
          >
            {/* Header with confidence score */}
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Eye className="w-4 h-4" />
                Behavior Analysis
              </h3>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-400">Confidence:</span>
                <div className="flex items-center gap-1">
                  <div className="w-20 h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all ${feedback.confidence_score >= 70
                        ? "bg-green-500"
                        : feedback.confidence_score >= 50
                          ? "bg-yellow-500"
                          : "bg-red-500"
                        }`}
                      style={{ width: `${feedback.confidence_score}%` }}
                    />
                  </div>
                  <span className="text-xs font-semibold text-white">
                    {feedback.confidence_score}%
                  </span>
                </div>
              </div>
            </div>

            {/* Overall feedback */}
            <div className="mb-3 p-2 bg-blue-500/10 rounded border border-blue-500/20">
              <p className="text-sm text-blue-200">{feedback.overall}</p>
            </div>

            {/* Detailed feedback messages */}
            <div className="space-y-2">
              {feedback.feedback.map((msg, idx) => {
                const isPositive = msg.startsWith("✓");
                const isWarning = msg.startsWith("⚠");
                const isError = msg.startsWith("❌");

                return (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    className={`flex items-start gap-2 p-2 rounded ${isPositive
                      ? "bg-green-500/10 border border-green-500/20"
                      : isWarning
                        ? "bg-yellow-500/10 border border-yellow-500/20"
                        : isError
                          ? "bg-red-500/10 border border-red-500/20"
                          : "bg-gray-500/10 border border-gray-500/20"
                      }`}
                  >
                    {isPositive && <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />}
                    {(isWarning || isError) && <AlertCircle className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />}
                    <span className="text-xs text-gray-200">{msg}</span>
                  </motion.div>
                );
              })}
            </div>

            {/* Metrics */}
            <div className="mt-3 pt-3 border-t border-gray-700 grid grid-cols-3 gap-2 text-xs">
              <div>
                <span className="text-gray-400">Eye Contact:</span>
                <span className={`ml-1 font-semibold ${feedback.eye_contact === "good" ? "text-green-400" : "text-yellow-400"
                  }`}>
                  {feedback.eye_contact === "good" ? "Good" : "Away"}
                </span>
              </div>
              <div>
                <span className="text-gray-400">Posture:</span>
                <span className={`ml-1 font-semibold ${feedback.posture.is_good ? "text-green-400" : "text-yellow-400"
                  }`}>
                  {feedback.posture.is_good ? "Good" : "Slouching"}
                </span>
              </div>
              <div>
                <span className="text-gray-400">Presence:</span>
                <span className={`ml-1 font-semibold ${feedback.presence ? "text-green-400" : "text-red-400"
                  }`}>
                  {feedback.presence ? "Yes" : "No"}
                </span>
              </div>
            </div>

            {/* Enhanced Metrics from Posture Engine */}
            {(feedback.attention_score !== undefined || feedback.posture_score !== undefined || feedback.movement_score !== undefined) && (
              <div className="mt-3 pt-3 border-t border-gray-700">
                <div className="text-xs text-gray-400 mb-2 font-semibold">🎯 Behavioral Analysis</div>
                <div className="space-y-2">
                  {feedback.attention_score !== undefined && (
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-400">Attention</span>
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all ${feedback.attention_score >= 70 ? 'bg-green-500' : feedback.attention_score >= 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                            style={{ width: `${feedback.attention_score}%` }}
                          />
                        </div>
                        <span className="text-xs font-mono text-white w-8 text-right">{feedback.attention_score?.toFixed(0)}%</span>
                      </div>
                    </div>
                  )}
                  {feedback.posture_score !== undefined && (
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-400">Posture</span>
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all ${feedback.posture_score >= 70 ? 'bg-green-500' : feedback.posture_score >= 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                            style={{ width: `${feedback.posture_score}%` }}
                          />
                        </div>
                        <span className="text-xs font-mono text-white w-8 text-right">{feedback.posture_score?.toFixed(0)}%</span>
                      </div>
                    </div>
                  )}
                  {feedback.eye_contact_score !== undefined && (
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-400">Eye Contact</span>
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all ${feedback.eye_contact_score >= 70 ? 'bg-green-500' : feedback.eye_contact_score >= 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                            style={{ width: `${feedback.eye_contact_score}%` }}
                          />
                        </div>
                        <span className="text-xs font-mono text-white w-8 text-right">{feedback.eye_contact_score?.toFixed(0)}%</span>
                      </div>
                    </div>
                  )}
                  {feedback.movement_score !== undefined && (
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-400">Stability</span>
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all ${feedback.movement_score >= 70 ? 'bg-green-500' : feedback.movement_score >= 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                            style={{ width: `${feedback.movement_score}%` }}
                          />
                        </div>
                        <span className="text-xs font-mono text-white w-8 text-right">{feedback.movement_score?.toFixed(0)}%</span>
                      </div>
                    </div>
                  )}
                </div>
                {/* Status Tags */}
                <div className="flex flex-wrap gap-1 mt-2">
                  {feedback.posture_quality && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${feedback.posture_quality === 'good' ? 'bg-green-500/20 text-green-300' :
                      feedback.posture_quality === 'acceptable' ? 'bg-yellow-500/20 text-yellow-300' :
                        'bg-red-500/20 text-red-300'
                      }`}>
                      {feedback.posture_quality}
                    </span>
                  )}
                  {feedback.nervousness_level && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${feedback.nervousness_level === 'calm' ? 'bg-green-500/20 text-green-300' :
                      feedback.nervousness_level === 'slightly_nervous' ? 'bg-yellow-500/20 text-yellow-300' :
                        'bg-red-500/20 text-red-300'
                      }`}>
                      {feedback.nervousness_level.replace(/_/g, ' ')}
                    </span>
                  )}
                  {feedback.gaze_direction && feedback.gaze_direction !== 'unknown' && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${feedback.gaze_direction === 'center' ? 'bg-green-500/20 text-green-300' :
                      'bg-yellow-500/20 text-yellow-300'
                      }`}>
                      gaze: {feedback.gaze_direction}
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Legacy Detailed Angles (shown when engine metrics not available) */}
            {feedback.attention_score === undefined && (
              <div className="mt-3 pt-3 border-t border-gray-700">
                <div className="text-xs text-gray-400 mb-2 font-semibold">📐 Detailed Metrics</div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-gray-800/50 p-2 rounded">
                    <span className="text-gray-400">Head Yaw:</span>
                    <span className="ml-1 text-blue-300 font-mono">{feedback.head_pose?.yaw?.toFixed(1) || '0.0'}°</span>
                  </div>
                  <div className="bg-gray-800/50 p-2 rounded">
                    <span className="text-gray-400">Head Pitch:</span>
                    <span className="ml-1 text-blue-300 font-mono">{feedback.head_pose?.pitch?.toFixed(1) || '0.0'}°</span>
                  </div>
                  <div className="bg-gray-800/50 p-2 rounded col-span-2">
                    <span className="text-gray-400">Slouch Angle:</span>
                    <span className={`ml-1 font-mono ${feedback.posture.slouch_angle <= 20 ? "text-green-400" : "text-yellow-400"
                      }`}>
                      {feedback.posture.slouch_angle?.toFixed(1) || '0.0'}°
                    </span>
                    <span className="ml-2 text-gray-500 text-xs">(≤20° is good)</span>
                  </div>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Waiting for first analysis */}
      {!feedback && !error && !isInitializing && (
        <div className="p-3 bg-gray-500/10 border border-gray-500/20 rounded-lg">
          <div className="flex items-center gap-2">
            <div className="animate-pulse h-2 w-2 bg-blue-400 rounded-full"></div>
            <p className="text-sm text-gray-300">Starting analysis...</p>
          </div>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {/* Analyzing indicator */}
      {isAnalyzingRef.current && feedback && (
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-400"></div>
          <span>Analyzing behavior...</span>
        </div>
      )}
    </div>
  );
}
