"use client";

import { Mic, MicOff, Loader2, AlertCircle } from "lucide-react";
import { useState, useEffect } from "react";

interface MicrophoneButtonProps {
  isListening: boolean;
  isSupported: boolean;
  hasPermission?: boolean | null;
  onStart: () => Promise<void> | void;
  onStop: () => void;
  disabled?: boolean;
  error?: string | null;
}

export default function MicrophoneButton({
  isListening,
  isSupported,
  hasPermission,
  onStart,
  onStop,
  disabled = false,
  error
}: MicrophoneButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);

  const handleClick = async () => {
    if (isListening) {
      onStop();
    } else {
      setIsLoading(true);
      try {
        await onStart();
      } finally {
        setIsLoading(false);
      }
    }
  };

  // Auto-hide tooltip after 3 seconds
  useEffect(() => {
    if (showTooltip) {
      const timer = setTimeout(() => setShowTooltip(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [showTooltip]);

  // Not supported in this browser
  if (!isSupported) {
    return (
      <div className="relative">
        <button
          disabled
          className="p-3 rounded-full bg-gray-500/50 cursor-not-allowed"
          title="Speech recognition not supported in this browser. Please use Chrome or Edge."
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
        >
          <MicOff className="w-5 h-5 text-white/60" />
        </button>
        {showTooltip && (
          <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 px-3 py-2 bg-black/90 text-white text-xs rounded-lg whitespace-nowrap z-50">
            Use Chrome or Edge for voice input
            <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-black/90" />
          </div>
        )}
      </div>
    );
  }

  // Permission denied
  if (hasPermission === false) {
    return (
      <div className="relative">
        <button
          onClick={handleClick}
          className="p-3 rounded-full bg-orange-500/80 hover:bg-orange-600/80 transition-all duration-200"
          title="Click to request microphone permission"
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
        >
          <AlertCircle className="w-5 h-5 text-white" />
        </button>
        {showTooltip && (
          <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 px-3 py-2 bg-orange-500 text-white text-xs rounded-lg whitespace-nowrap z-50">
            Click to request mic permission
            <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-orange-500" />
          </div>
        )}
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <button
        disabled
        className="p-3 rounded-full bg-blue-500/80 cursor-wait"
      >
        <Loader2 className="w-5 h-5 text-white animate-spin" />
      </button>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={handleClick}
        disabled={disabled}
        className={`p-3 rounded-full transition-all duration-200 relative ${isListening
            ? "bg-red-500 hover:bg-red-600 shadow-lg shadow-red-500/30"
            : disabled
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-blue-500 hover:bg-blue-600 shadow-lg shadow-blue-500/30"
          }`}
        title={isListening ? "Stop listening" : "Start voice input"}
        onMouseEnter={() => !isListening && setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        {isListening ? (
          <>
            <Mic className="w-5 h-5 text-white" />
            {/* Pulse rings for recording indication */}
            <span className="absolute inset-0 rounded-full bg-red-400/50 animate-ping" />
            <span className="absolute inset-0 rounded-full bg-red-400/30 animate-pulse" style={{ animationDelay: "0.5s" }} />
          </>
        ) : (
          <Mic className="w-5 h-5 text-white" />
        )}
      </button>

      {/* Tooltip */}
      {showTooltip && !isListening && (
        <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 px-3 py-2 bg-black/90 text-white text-xs rounded-lg whitespace-nowrap z-50">
          Click to speak your answer
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-black/90" />
        </div>
      )}

      {/* Error indicator */}
      {error && (
        <div className="absolute top-full mt-2 left-1/2 transform -translate-x-1/2 px-3 py-2 bg-red-500/90 text-white text-xs rounded-lg max-w-xs text-center z-50">
          {error}
        </div>
      )}
    </div>
  );
}
