"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface UseTTSReturn {
  speak: (text: string) => void;
  stop: () => void;
  isSpeaking: boolean;
  isSupported: boolean;
  voicesLoaded: boolean;
  currentVoice: string | null;
}

// Priority list of natural-sounding voices
const PREFERRED_VOICES = [
  // Google voices (Chrome)
  'Google US English',
  'Google UK English Female',
  'Google UK English Male',
  // Microsoft voices (Edge)
  'Microsoft Zira Online (Natural)',
  'Microsoft David Online (Natural)',
  'Microsoft Aria Online (Natural)',
  'Microsoft Jenny Online (Natural)',
  // Apple voices (Safari)
  'Samantha',
  'Karen',
  'Daniel',
  'Moira',
  // Fallback Microsoft voices
  'Microsoft Zira',
  'Microsoft David',
];

export function useTTS(): UseTTSReturn {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [voicesLoaded, setVoicesLoaded] = useState(false);
  const [currentVoice, setCurrentVoice] = useState<string | null>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const selectedVoiceRef = useRef<SpeechSynthesisVoice | null>(null);

  // Select the best available voice
  const selectBestVoice = useCallback(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return null;

    const voices = window.speechSynthesis.getVoices();
    if (voices.length === 0) return null;

    // Try to find a preferred voice
    for (const preferredName of PREFERRED_VOICES) {
      const voice = voices.find(v =>
        v.name.toLowerCase().includes(preferredName.toLowerCase())
      );
      if (voice) {
        console.log("🔊 Selected TTS voice:", voice.name);
        return voice;
      }
    }

    // Fallback: find any English voice
    const englishVoice = voices.find(v => v.lang.startsWith('en'));
    if (englishVoice) {
      console.log("🔊 Fallback to English voice:", englishVoice.name);
      return englishVoice;
    }

    // Last resort: use first available voice
    console.log("🔊 Using first available voice:", voices[0].name);
    return voices[0];
  }, []);

  // Initialize and wait for voices to load
  useEffect(() => {
    if (typeof window === 'undefined') return;

    if ('speechSynthesis' in window) {
      setIsSupported(true);

      const loadVoices = () => {
        const voices = window.speechSynthesis.getVoices();
        if (voices.length > 0) {
          setVoicesLoaded(true);
          const best = selectBestVoice();
          selectedVoiceRef.current = best;
          setCurrentVoice(best?.name || null);
        }
      };

      // Voices may already be loaded
      loadVoices();

      // Or they may load asynchronously (especially in Chrome)
      window.speechSynthesis.onvoiceschanged = loadVoices;

      // Some browsers need a small delay
      setTimeout(loadVoices, 100);
    }
  }, [selectBestVoice]);

  const stop = useCallback(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, []);

  const speak = useCallback((text: string) => {
    if (!isSupported || !text.trim()) return;

    // Stop any ongoing speech
    stop();

    // Create utterance
    const utterance = new SpeechSynthesisUtterance(text);
    utteranceRef.current = utterance;

    // Use the pre-selected best voice
    if (selectedVoiceRef.current) {
      utterance.voice = selectedVoiceRef.current;
    } else {
      // Try selecting again if voice wasn't ready
      const voice = selectBestVoice();
      if (voice) {
        utterance.voice = voice;
        selectedVoiceRef.current = voice;
      }
    }

    // Optimized settings for clarity
    utterance.rate = 0.92;      // Slightly slower for better understanding
    utterance.pitch = 1.0;      // Natural pitch
    utterance.volume = 1.0;     // Full volume

    // Event handlers
    utterance.onstart = () => {
      console.log("🔊 TTS started speaking");
      setIsSpeaking(true);
    };

    utterance.onend = () => {
      console.log("🔊 TTS finished speaking");
      setIsSpeaking(false);
    };

    utterance.onerror = (event) => {
      console.error('🔊 TTS error:', event.error);
      setIsSpeaking(false);

      // Try to recover by re-selecting voice
      if (event.error === 'voice-unavailable') {
        selectedVoiceRef.current = selectBestVoice();
      }
    };

    // Chrome has a bug where long texts get interrupted
    // Split into chunks if needed
    if (text.length > 200) {
      // Chrome fix: prevent speech from getting stuck
      const resumeSpeech = () => {
        if (window.speechSynthesis.speaking && !window.speechSynthesis.paused) {
          window.speechSynthesis.pause();
          window.speechSynthesis.resume();
        }
      };

      // Keep-alive timer to prevent Chrome from stopping
      const keepAlive = setInterval(() => {
        if (!window.speechSynthesis.speaking) {
          clearInterval(keepAlive);
        } else {
          resumeSpeech();
        }
      }, 10000); // Every 10 seconds

      utterance.onend = () => {
        clearInterval(keepAlive);
        setIsSpeaking(false);
      };

      utterance.onerror = (event) => {
        clearInterval(keepAlive);
        console.error('🔊 TTS error:', event.error);
        setIsSpeaking(false);
      };
    }

    // Speak!
    window.speechSynthesis.speak(utterance);
  }, [isSupported, stop, selectBestVoice]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stop();
    };
  }, [stop]);

  return {
    speak,
    stop,
    isSpeaking,
    isSupported,
    voicesLoaded,
    currentVoice
  };
}
