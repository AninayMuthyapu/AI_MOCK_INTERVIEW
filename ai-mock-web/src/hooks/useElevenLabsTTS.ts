"use client";

import { useCallback, useRef, useState } from "react";
import { API_BASE } from "@/app/lib/api";

interface UseElevenLabsTTSReturn {
    speak: (text: string, voice?: string) => Promise<void>;
    stop: () => void;
    isSpeaking: boolean;
    isLoading: boolean;
    error: string | null;
}

/**
 * High-quality TTS using ElevenLabs via backend API.
 * Use this for important audio like interview questions.
 * Falls back to browser TTS if API fails.
 */
export function useElevenLabsTTS(): UseElevenLabsTTSReturn {
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const audioRef = useRef<HTMLAudioElement | null>(null);

    const stop = useCallback(() => {
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current.currentTime = 0;
            audioRef.current = null;
        }
        setIsSpeaking(false);
    }, []);

    const speak = useCallback(async (text: string, voice: string = "rachel") => {
        if (!text.trim()) return;

        // Stop any current playback
        stop();
        setError(null);
        setIsLoading(true);

        try {
            const response = await fetch(`${API_BASE}/api/tts`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text, voice }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'TTS API request failed');
            }

            // Get audio blob from response
            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);

            // Create and play audio
            const audio = new Audio(audioUrl);
            audioRef.current = audio;

            audio.onplay = () => {
                setIsLoading(false);
                setIsSpeaking(true);
            };

            audio.onended = () => {
                setIsSpeaking(false);
                URL.revokeObjectURL(audioUrl);
                audioRef.current = null;
            };

            audio.onerror = (e) => {
                console.error("Audio playback error:", e);
                setError("Failed to play audio");
                setIsSpeaking(false);
                setIsLoading(false);
                URL.revokeObjectURL(audioUrl);
                audioRef.current = null;
            };

            await audio.play();

        } catch (err) {
            console.error("ElevenLabs TTS error:", err);
            setError(err instanceof Error ? err.message : "TTS failed");
            setIsLoading(false);

            // Fallback to browser TTS
            if ('speechSynthesis' in window) {
                console.log("Falling back to browser TTS");
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.rate = 0.9;
                utterance.onstart = () => setIsSpeaking(true);
                utterance.onend = () => setIsSpeaking(false);
                window.speechSynthesis.speak(utterance);
            }
        }
    }, [stop]);

    return {
        speak,
        stop,
        isSpeaking,
        isLoading,
        error
    };
}
