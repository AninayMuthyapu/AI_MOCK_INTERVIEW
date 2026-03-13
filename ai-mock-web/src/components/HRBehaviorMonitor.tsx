"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { FilesetResolver, FaceLandmarker, DrawingUtils, PoseLandmarker } from "@mediapipe/tasks-vision";

interface HRBehaviorMonitorProps {
  onScoreUpdate: (scores: HRBehaviorScores) => void;
  isActive: boolean;
}

export interface HRBehaviorScores {
  eyeContact: number; // 0-100
  attention: number; // 0-100
  stability: number; // 0-100
}

export default function HRBehaviorMonitor({ onScoreUpdate, isActive }: HRBehaviorMonitorProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const faceLandmarkerRef = useRef<FaceLandmarker | null>(null);
  const poseLandmarkerRef = useRef<PoseLandmarker | null>(null);
  const requestRef = useRef<number>(0);

  const [isInitializing, setIsInitializing] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const lastVideoTimeRef = useRef<number>(-1);

  // Accumulated scores
  const scoreHistory = useRef<{
    eyeContact: number[];
    attention: number[];
    stability: number[];
  }>({
    eyeContact: [],
    attention: [],
    stability: [],
  });

  // Calculate moving average
  const updateAverages = useCallback(() => {
    if (!isActive) return;

    const hist = scoreHistory.current;
    if (hist.eyeContact.length === 0) return;

    const avg = (arr: number[]) =>
      arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;

    onScoreUpdate({
      eyeContact: avg(hist.eyeContact),
      attention: avg(hist.attention),
      stability: avg(hist.stability),
    });
  }, [isActive, onScoreUpdate]);

  useEffect(() => {
    const updateInterval = setInterval(updateAverages, 2000);
    return () => clearInterval(updateInterval);
  }, [updateAverages]);

  useEffect(() => {
    let stream: MediaStream | null = null;
    let isActiveMount = true;

    async function initializeMediaPipe() {
      try {
        setIsInitializing(true);
        const vision = await FilesetResolver.forVisionTasks(
          "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.3/wasm"
        );

        faceLandmarkerRef.current = await FaceLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: `https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task`,
            delegate: "GPU"
          },
          outputFaceBlendshapes: true,
          runningMode: "VIDEO",
          numFaces: 1
        });

        poseLandmarkerRef.current = await PoseLandmarker.createFromOptions(vision, {
             baseOptions: {
                modelAssetPath: `https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task`,
                delegate: "GPU"
              },
              runningMode: "VIDEO",
              numPoses: 1
        });


        stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480, facingMode: "user" }
        });

        if (videoRef.current && isActiveMount) {
          videoRef.current.srcObject = stream;
          videoRef.current.play();
        }

        setIsInitializing(false);
      } catch (err: unknown) {
        console.error("Initialization error:", err);
        const errorMessage = err instanceof Error ? err.message : "Camera access denied";
        if (isActiveMount) setError(errorMessage);
      }
    }

    initializeMediaPipe();

    return () => {
      isActiveMount = false;
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
      if (faceLandmarkerRef.current) {
         faceLandmarkerRef.current.close()
      }
      if (poseLandmarkerRef.current) {
          poseLandmarkerRef.current.close()
      }
    };
  }, []);

  const renderLoop = useCallback(() => {
    if (!videoRef.current || !canvasRef.current || !faceLandmarkerRef.current || !poseLandmarkerRef.current || !isActive) {
      requestRef.current = requestAnimationFrame(renderLoop);
      return;
    }

    const video = videoRef.current;
    if (video.readyState >= 2 && video.currentTime !== lastVideoTimeRef.current) {
      lastVideoTimeRef.current = video.currentTime;
      const timestampMs = performance.now();
      
      const faceResults = faceLandmarkerRef.current.detectForVideo(video, timestampMs);
      const poseResults = poseLandmarkerRef.current.detectForVideo(video, timestampMs);

      const canvasCtx = canvasRef.current.getContext("2d");
      if (canvasCtx) {
        canvasCtx.save();
        canvasCtx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);

        let eyeContactScore = 0;
        let attentionScore = 0;
        let stabilityScore = 100; // Assume stable initially

         const drawingUtils = new DrawingUtils(canvasCtx);

        // Attention is basically: is there a face?
        if (faceResults.faceLandmarks.length > 0) {
          attentionScore = 100;
          const landmarks = faceResults.faceLandmarks[0];

          // Simplified eye contact estimation (looking mostly forward)
          const leftEye = landmarks[159]; // Top of left eye
          const rightEye = landmarks[386]; // Top of right eye
          const nose = landmarks[1]; // Nose tip

          // Very rudimentary Euler angle proxy using face landmarks
          // Assuming nose x is normally right between the eyes when looking straight
          const midX = (leftEye.x + rightEye.x) / 2;
          const deltaX = Math.abs(midX - nose.x);
          
          if (deltaX < 0.05) eyeContactScore = 100;
          else if (deltaX < 0.1) eyeContactScore = 80;
          else if (deltaX < 0.15) eyeContactScore = 50;
          else eyeContactScore = 20;

          // Optional: draw face mesh for debugging/visuals
          drawingUtils.drawConnectors(
               landmarks,
               FaceLandmarker.FACE_LANDMARKS_TESSELATION,
               { color: "#C0C0C070", lineWidth: 1 }
           );
        }

        // Stability proxy using shoulders
        if (poseResults.landmarks.length > 0) {
            const pose = poseResults.landmarks[0];
            const leftShoulder = pose[11];
            const rightShoulder = pose[12];

             // Check vertical alignment of shoulders (should be roughly level)
             const shoulderTilt = Math.abs(leftShoulder.y - rightShoulder.y);
             if (shoulderTilt > 0.1) stabilityScore -= 30; // Severe tilt
             else if (shoulderTilt > 0.05) stabilityScore -= 10;
        }


        // Store in history
        if (scoreHistory.current.attention.length > 100) {
           scoreHistory.current.attention.shift();
           scoreHistory.current.eyeContact.shift();
           scoreHistory.current.stability.shift();
        }

        scoreHistory.current.attention.push(attentionScore);
        scoreHistory.current.eyeContact.push(eyeContactScore);
        scoreHistory.current.stability.push(stabilityScore);

        canvasCtx.restore();
      }
    }
    requestRef.current = requestAnimationFrame(renderLoop);
  }, [isActive]);


  useEffect(() => {
    if (!isInitializing && isActive) {
      requestRef.current = requestAnimationFrame(renderLoop);
    }
    return () => {
      if (requestRef.current) {
        cancelAnimationFrame(requestRef.current);
      }
    };
  }, [isInitializing, isActive, renderLoop]);


  if (error) {
    return (
      <div className="w-full h-48 bg-red-50 flex items-center justify-center rounded-lg border border-red-200">
        <p className="text-red-500 font-medium">Camera Error: {error}</p>
      </div>
    );
  }

  return (
    <div className="relative w-full rounded-xl overflow-hidden bg-black shadow-lg">
      <video
        ref={videoRef}
        muted
        playsInline
        className="w-full h-full object-cover transform scale-x-[-1]"
        style={{ opacity: isInitializing ? 0.5 : 1 }}
      />
      <canvas
        ref={canvasRef}
        width={640}
        height={480}
        className="absolute top-0 left-0 w-full h-full object-cover transform scale-x-[-1] pointer-events-none"
      />
      
      {isInitializing && (
         <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/60 backdrop-blur-sm z-10">
            <div className="animate-spin h-8 w-8 text-blue-500 mx-auto mb-4 border-4 border-blue-500/30 border-t-blue-500 rounded-full"></div>
            <p className="text-white text-sm font-medium">Loading AI Models...</p>
         </div>
      )}

       {/* Debug / Status Indicator */}
       {!isInitializing && isActive && (
        <div className="absolute top-4 right-4 flex items-center gap-2 bg-black/50 backdrop-blur px-3 py-1.5 rounded-full z-20">
          <div className="w-2.5 h-2.5 bg-green-500 rounded-full animate-pulse" />
          <span className="text-white text-xs font-semibold">Live Analysis</span>
        </div>
      )}
    </div>
  );
}
