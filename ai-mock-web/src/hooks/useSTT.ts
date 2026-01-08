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
};

type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

interface UseSTTReturn {
  transcript: string;
  isListening: boolean;
  isSupported: boolean;
  startListening: () => void;
  stopListening: () => void;
  resetTranscript: () => void;
  error: string | null;
}

export function useSTT(): UseSTTReturn {
  const [transcript, setTranscript] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const recognitionRef = useRef<unknown>(null);

  useEffect(() => {
    // Check if speech recognition is supported
    if (typeof window !== 'undefined') {
      const SpeechRecognition =
        (window as unknown as { SpeechRecognition?: unknown }).SpeechRecognition ||
        (window as unknown as { webkitSpeechRecognition?: unknown }).webkitSpeechRecognition;
      
      if (SpeechRecognition) {
        setIsSupported(true);
        
        // Initialize recognition
        const RecognitionCtor = SpeechRecognition as SpeechRecognitionCtor;
        const recognition = new RecognitionCtor();
        recognition.continuous = true; // Keep listening
        recognition.interimResults = true; // Get interim results
        recognition.lang = 'en-US';
        recognition.maxAlternatives = 1;

        // Event handlers
        recognition.onstart = () => {
          setIsListening(true);
          setError(null);
        };

        recognition.onresult = (event: unknown) => {
          let finalTranscript = '';
          const maybeEvent = event as SpeechRecognitionEventLike;
          const resultIndex = typeof maybeEvent.resultIndex === "number" ? maybeEvent.resultIndex : 0;
          const results = maybeEvent.results;

          if (!results || typeof results.length !== "number") {
            return;
          }

          for (let i = resultIndex; i < results.length; i++) {
            const transcriptPart = results[i]?.[0]?.transcript;
            if (typeof transcriptPart !== "string") continue;
            if (results[i]?.isFinal) {
              finalTranscript += transcriptPart + ' ';
            }
          }

          // Update transcript with final results
          if (finalTranscript) {
            setTranscript(prev => prev + finalTranscript);
          }
        };

        recognition.onerror = (event: unknown) => {
          const maybeError = event as SpeechRecognitionErrorEventLike;
          const errorCode = typeof maybeError.error === "string" ? maybeError.error : "unknown";
          // Network errors are common and usually harmless - just means STT unavailable
          if (errorCode === 'network') {
            console.warn('Speech recognition unavailable (network error). You can still type your answers.');
            setError('Speech recognition unavailable. Please type your answer.');
          } else {
            console.error('Speech recognition error:', errorCode);
            setError(`Speech recognition error: ${errorCode}`);
          }
          setIsListening(false);
          
          // Auto-restart on some errors
          if (errorCode === 'no-speech' || errorCode === 'audio-capture') {
            // Don't auto-restart, let user manually restart
          }
        };

        recognition.onend = () => {
          setIsListening(false);
        };

        recognitionRef.current = recognition;
      }
    }

    return () => {
      if (recognitionRef.current) {
        try {
          (recognitionRef.current as SpeechRecognitionLike).stop();
        } catch (e) {
          // Ignore errors on cleanup
        }
      }
    };
  }, []);

  const startListening = useCallback(() => {
    const recognition = recognitionRef.current as { start?: () => void } | null;
    if (!isSupported || !recognition?.start) {
      setError('Speech recognition is not supported in this browser');
      return;
    }

    try {
      setError(null);
      recognition.start();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "";
      // If already started, ignore
      if (message.includes('already started')) {
        setIsListening(true);
      } else {
        setError('Failed to start speech recognition');
        console.error('Start listening error:', e);
      }
    }
  }, [isSupported]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current && isListening) {
      try {
        (recognitionRef.current as SpeechRecognitionLike).stop();
      } catch (e) {
        console.error('Stop listening error:', e);
      }
    }
  }, [isListening]);

  const resetTranscript = useCallback(() => {
    setTranscript("");
    setError(null);
  }, []);

  return {
    transcript,
    isListening,
    isSupported,
    startListening,
    stopListening,
    resetTranscript,
    error
  };
}
