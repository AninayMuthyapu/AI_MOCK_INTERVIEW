"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type SpeechRecognitionResultLike = {
  isFinal?: boolean;
  0?: { transcript?: string };
};

type SpeechRecognitionEventLike = {
  resultIndex?: number;
  results?: ArrayLike<SpeechRecognitionResultLike>;
};

type SpeechRecognitionErrorEventLike = {
  error?: string;
};

type SpeechRecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  onstart: null | (() => void);
  onend: null | (() => void);
  onresult: null | ((event: unknown) => void);
  onerror: null | ((event: unknown) => void);
  start: () => void;
  stop: () => void;
  abort: () => void;
};

type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

interface UseSTTReturn {
  transcript: string;
  interimTranscript: string;
  isListening: boolean;
  isSupported: boolean;
  hasPermission: boolean | null;
  startListening: () => Promise<void>;
  stopListening: () => void;
  resetTranscript: () => void;
  error: string | null;
}

export function useSTT(): UseSTTReturn {
  const [transcript, setTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const shouldContinueListeningRef = useRef(false);
  const retryCountRef = useRef(0);
  const MAX_RETRIES = 3;

  // Request microphone permission explicitly
  const requestMicrophonePermission = useCallback(async (): Promise<boolean> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Stop all tracks immediately - we just needed to check permission
      stream.getTracks().forEach(track => track.stop());
      setHasPermission(true);
      return true;
    } catch (e) {
      console.error("Microphone permission denied:", e);
      setHasPermission(false);
      setError("Microphone access denied. Please enable microphone permission in your browser settings.");
      return false;
    }
  }, []);

  // Initialize speech recognition
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition =
        (window as unknown as { SpeechRecognition?: SpeechRecognitionCtor }).SpeechRecognition ||
        (window as unknown as { webkitSpeechRecognition?: SpeechRecognitionCtor }).webkitSpeechRecognition;

      if (SpeechRecognition) {
        setIsSupported(true);

        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
          console.log("🎤 Speech recognition started");
          setIsListening(true);
          setError(null);
          retryCountRef.current = 0;
        };

        recognition.onresult = (event: unknown) => {
          const maybeEvent = event as SpeechRecognitionEventLike;
          const resultIndex = typeof maybeEvent.resultIndex === "number" ? maybeEvent.resultIndex : 0;
          const results = maybeEvent.results;

          if (!results || typeof results.length !== "number") {
            return;
          }

          let finalTranscript = '';
          let interimText = '';

          for (let i = resultIndex; i < results.length; i++) {
            const transcriptPart = results[i]?.[0]?.transcript;
            if (typeof transcriptPart !== "string") continue;

            if (results[i]?.isFinal) {
              finalTranscript += transcriptPart + ' ';
            } else {
              interimText += transcriptPart;
            }
          }

          // Update interim transcript for live feedback
          setInterimTranscript(interimText);

          // Append final results to transcript
          if (finalTranscript) {
            setTranscript(prev => prev + finalTranscript);
            setInterimTranscript("");
          }
        };

        recognition.onerror = (event: unknown) => {
          const maybeError = event as SpeechRecognitionErrorEventLike;
          const errorCode = typeof maybeError.error === "string" ? maybeError.error : "unknown";

          console.warn("🎤 Speech recognition error:", errorCode);

          switch (errorCode) {
            case 'network':
              // Network errors are common - try to auto-restart
              if (retryCountRef.current < MAX_RETRIES && shouldContinueListeningRef.current) {
                retryCountRef.current++;
                console.log(`🔄 Retrying speech recognition (attempt ${retryCountRef.current}/${MAX_RETRIES})`);
                setError(`Network error. Retrying... (${retryCountRef.current}/${MAX_RETRIES})`);
                setTimeout(() => {
                  if (shouldContinueListeningRef.current && recognitionRef.current) {
                    try {
                      recognitionRef.current.start();
                    } catch (e) {
                      console.error("Retry failed:", e);
                    }
                  }
                }, 1000 * retryCountRef.current);
                return;
              } else {
                setError("Speech recognition unavailable due to network issues. Please type your answer.");
              }
              break;

            case 'not-allowed':
            case 'permission-denied':
              setHasPermission(false);
              setError("Microphone access denied. Please enable microphone permission.");
              break;

            case 'no-speech':
              // No speech detected - this is normal, don't show error
              console.log("No speech detected, restarting...");
              if (shouldContinueListeningRef.current) {
                setTimeout(() => {
                  if (shouldContinueListeningRef.current && recognitionRef.current) {
                    try {
                      recognitionRef.current.start();
                    } catch (e) {
                      console.error("Restart after no-speech failed:", e);
                    }
                  }
                }, 100);
                return;
              }
              break;

            case 'audio-capture':
              setError("No microphone detected. Please connect a microphone and try again.");
              break;

            case 'aborted':
              // User or system aborted - not an error
              console.log("Speech recognition aborted");
              break;

            default:
              setError(`Speech recognition error: ${errorCode}`);
          }

          setIsListening(false);
        };

        recognition.onend = () => {
          console.log("🎤 Speech recognition ended, shouldContinue:", shouldContinueListeningRef.current);

          // Auto-restart if we should still be listening
          if (shouldContinueListeningRef.current) {
            console.log("🔄 Auto-restarting speech recognition");
            setTimeout(() => {
              if (shouldContinueListeningRef.current && recognitionRef.current) {
                try {
                  recognitionRef.current.start();
                } catch (e) {
                  const message = e instanceof Error ? e.message : "";
                  if (!message.includes('already started')) {
                    console.error("Auto-restart failed:", e);
                    setIsListening(false);
                    shouldContinueListeningRef.current = false;
                  }
                }
              }
            }, 100);
          } else {
            setIsListening(false);
          }
        };

        recognitionRef.current = recognition;
      }
    }

    return () => {
      shouldContinueListeningRef.current = false;
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {
          // Ignore cleanup errors
        }
      }
    };
  }, []);

  const startListening = useCallback(async () => {
    if (!isSupported) {
      setError('Speech recognition is not supported in this browser. Please use Chrome or Edge.');
      return;
    }

    // First, ensure we have microphone permission
    if (hasPermission === null || hasPermission === false) {
      const granted = await requestMicrophonePermission();
      if (!granted) {
        return;
      }
    }

    if (!recognitionRef.current) {
      setError('Speech recognition not initialized');
      return;
    }

    try {
      setError(null);
      shouldContinueListeningRef.current = true;
      retryCountRef.current = 0;
      recognitionRef.current.start();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "";
      if (message.includes('already started')) {
        setIsListening(true);
      } else {
        setError('Failed to start speech recognition');
        console.error('Start listening error:', e);
        shouldContinueListeningRef.current = false;
      }
    }
  }, [isSupported, hasPermission, requestMicrophonePermission]);

  const stopListening = useCallback(() => {
    console.log("🛑 Stopping speech recognition");
    shouldContinueListeningRef.current = false;

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        console.error('Stop listening error:', e);
      }
    }
    setIsListening(false);
    setInterimTranscript("");
  }, []);

  const resetTranscript = useCallback(() => {
    setTranscript("");
    setInterimTranscript("");
    setError(null);
  }, []);

  return {
    transcript,
    interimTranscript,
    isListening,
    isSupported,
    hasPermission,
    startListening,
    stopListening,
    resetTranscript,
    error
  };
}
