"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import CodeEditor from "../components/CodeEditor";
import { API_BASE } from "../lib/api";
import { useSpeak } from "@/hooks/useSpeak";
import InterviewSummary from "@/components/InterviewSummary";
import UserVideoFeed from "@/components/UserVideoFeed";
import AvatarVideo from "@/components/AvatarVideo";
import AvatarChatBox from "@/components/AvatarChatBox";
import MicrophoneButton from "@/components/MicrophoneButton";
import BehaviorMonitor from "@/components/BehaviorMonitor";
import SoftSkillsFeedback from "@/components/SoftSkillsFeedback";
import { db } from "@/lib/db";
import { useTTS } from "@/hooks/useTTS";
import { useSTT } from "@/hooks/useSTT";
import { generateAvatar } from "@/lib/avatar";
import { motion, AnimatePresence } from "framer-motion";
import { Volume2, Video, Lightbulb, X } from "lucide-react";

export default function InterviewPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [initialCode, setInitialCode] = useState("");
  const [mcqOptions, setMcqOptions] = useState<string[] | null>(null);
  const [selectedMcqOption, setSelectedMcqOption] = useState<string | null>(null);
  const [roundTitle, setRoundTitle] = useState("");
  const [userAnswer, setUserAnswer] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [roundType, setRoundType] = useState<string | null>(null);
  const [language] = useState<string>("python");
  const [isRecording, setIsRecording] = useState(false);

  // Timer and feedback states
  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  const [isTimerActive, setIsTimerActive] = useState(false);
  const [feedback, setFeedback] = useState<{
    score?: number;
    strengths?: string[];
    weaknesses?: string[];
    feedback_text?: string;
  } | null>(null);
  const [softSkills, setSoftSkills] = useState<{
    overallScore: number;
    metrics: Array<{ name: string; score: number; feedback: string; source: string }>;
    details?: Record<string, unknown>;
    openSmileFeatures?: Record<string, unknown>;
  } | null>(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const router = useRouter();
  const { speakIfEnabled } = useSpeak();

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Avatar and chat states
  const [avatarMessages, setAvatarMessages] = useState<{ text: string; timestamp: number }[]>([]);
  const [isAvatarSpeaking, setIsAvatarSpeaking] = useState(false);

  // Avatar mode states
  const [interviewMode, setInterviewMode] = useState<'audio' | 'avatar'>('audio');
  const [avatarVideoUrl, setAvatarVideoUrl] = useState<string | null>(null);
  const [isGeneratingAvatar, setIsGeneratingAvatar] = useState(false);
  const [avatarError, setAvatarError] = useState<string | null>(null);

  // Hint states
  const [currentHint, setCurrentHint] = useState<string | null>(null);
  const [isLoadingHint, setIsLoadingHint] = useState(false);
  const [showHint, setShowHint] = useState(false);

  // When switching to avatar mode, generate avatar for current question
  useEffect(() => {
    if (interviewMode === 'avatar' && question && !avatarVideoUrl && !isGeneratingAvatar) {
      console.log('🎭 Switching to Avatar Mode - generating video for current question');
      handleAvatarGeneration(question);
    }
  }, [interviewMode]); // Only trigger when mode changes

  // Web Speech API hooks
  const { speak: speakTTS, stop: stopTTS, isSpeaking: isTTSSpeaking } = useTTS();
  const {
    transcript,
    interimTranscript,
    isListening,
    isSupported: isSTTSupported,
    hasPermission: hasSTTPermission,
    startListening,
    stopListening,
    resetTranscript,
    error: sttError
  } = useSTT();

  // Sync TTS speaking state with avatar
  useEffect(() => {
    setIsAvatarSpeaking(isTTSSpeaking);
  }, [isTTSSpeaking]);

  // Update answer field with STT transcript
  useEffect(() => {
    if (transcript && roundType !== 'dsa' && roundType !== 'technical') {
      setUserAnswer(prev => prev + transcript);
      resetTranscript();
    }
  }, [transcript, roundType, resetTranscript]);

  // Stop TTS when STT starts listening (avoid feedback)
  useEffect(() => {
    if (isListening) {
      stopTTS();
    }
  }, [isListening, stopTTS]);

  // Handle avatar generation
  const handleAvatarGeneration = useCallback(async (text: string) => {
    console.log('🎬 handleAvatarGeneration called:', { interviewMode, hasText: !!text });

    if (interviewMode !== 'avatar' || !text) {
      console.log('⏭️  Skipping avatar generation:', { interviewMode, hasText: !!text });
      return;
    }

    console.log('🎭 Starting avatar generation for text:', text.substring(0, 50) + '...');
    setIsGeneratingAvatar(true);
    setAvatarError(null);
    setAvatarVideoUrl(null);

    try {
      const result = await generateAvatar({ text });
      const fullUrl = `${API_BASE}${result.video_url}`;
      console.log('✅ Avatar video generated:', fullUrl);
      setAvatarVideoUrl(fullUrl);
      setIsAvatarSpeaking(true);
    } catch (error) {
      console.error('❌ Avatar generation failed:', error);
      setAvatarError('Avatar generation failed. Falling back to audio.');
      // Fallback to TTS
      speakTTS(text);
    } finally {
      setIsGeneratingAvatar(false);
    }
  }, [interviewMode, speakTTS]);

  // Handle avatar video end
  const handleAvatarVideoEnd = useCallback(() => {
    setIsAvatarSpeaking(false);
    setAvatarVideoUrl(null);
  }, []);

  // Handle hint request
  const handleGetHint = async () => {
    if (!sessionId) return;

    setIsLoadingHint(true);
    try {
      const response = await fetch(`${API_BASE}/api/get-hint`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId,
          currentAnswer: userAnswer
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        console.error('Hint API error:', response.status, errorData);
        throw new Error(`Failed to get hint: ${errorData.detail || response.statusText}`);
      }

      const data = await response.json();
      setCurrentHint(data.hint);
      setShowHint(true);

      // Speak the hint if in audio mode
      if (interviewMode === 'audio') {
        speakTTS(data.hint);
      }

      // Add hint to avatar chat
      setAvatarMessages(prev => [...prev, {
        text: `💡 Hint: ${data.hint}`,
        timestamp: Date.now()
      }]);

    } catch (error) {
      console.error('Error getting hint:', error);
      setCurrentHint("Try thinking about a specific situation from your experience. What was the context? What actions did you take?");
      setShowHint(true);
    } finally {
      setIsLoadingHint(false);
    }
  };

  // Timer functions
  const startTimer = (minutes: number) => {
    setTimeRemaining(minutes * 60);
    setIsTimerActive(true);
  };

  const stopTimer = () => {
    setIsTimerActive(false);
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  useEffect(() => {
    if (isTimerActive && timeRemaining > 0) {
      timerRef.current = setInterval(() => {
        setTimeRemaining((prev) => {
          if (prev <= 1) {
            setIsTimerActive(false);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isTimerActive]); // Intentionally exclude timeRemaining from deps to avoid re-creating interval

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const updateQuestionState = useCallback((data: {
    questionData: {
      question: string;
      type: string;
      options?: string[];
      initial_code?: string;
    };
    roundTitle: string;
    isComplete: boolean;
    feedback?: {
      feedback_text?: string;
      score?: number;
      strengths?: string[];
      weaknesses?: string[];
    };
    softSkills?: {
      overallScore: number;
      metrics: Array<{ name: string; score: number; feedback: string; source: string }>;
      details?: Record<string, unknown>;
      openSmileFeatures?: Record<string, unknown>;
    };
  }) => {
    setQuestion(data.questionData.question);
    setRoundTitle(data.roundTitle);
    setRoundType(data.questionData.type);
    setIsComplete(data.isComplete);
    setUserAnswer("");
    setFeedback(data.feedback ?? null);
    setSoftSkills(data.softSkills ?? null);
    setShowFeedback(!!data.feedback);

    // Add question to avatar chat and speak with TTS or Avatar
    if (data.questionData.question) {
      setAvatarMessages(prev => [...prev, {
        text: data.questionData.question,
        timestamp: Date.now()
      }]);

      // Use Avatar Mode or TTS based on setting
      if (interviewMode === 'avatar') {
        handleAvatarGeneration(data.questionData.question);
      } else {
        speakTTS(data.questionData.question);
      }
    }

    // Add feedback to avatar chat and speak
    if (data.feedback?.feedback_text) {
      setAvatarMessages(prev => [...prev, {
        text: data.feedback?.feedback_text || "",
        timestamp: Date.now()
      }]);

      // Use Avatar Mode or TTS based on setting
      if (interviewMode === 'avatar') {
        handleAvatarGeneration(data.feedback.feedback_text);
      } else {
        speakTTS(data.feedback.feedback_text);
      }
    }

    // Start timer based on question type
    if (data.questionData.type === "technical" || data.questionData.type === "dsa") {
      startTimer(45); // 45 minutes for coding questions
    } else if (data.questionData.type === "mcq") {
      startTimer(2); // 2 minutes per MCQ
    } else {
      startTimer(8); // 8 minutes for behavioral questions
    }

    if (data.questionData.type === "mcq" && data.questionData.options) {
      setMcqOptions(data.questionData.options);
      setSelectedMcqOption(null);
    } else {
      setMcqOptions(null);
      setSelectedMcqOption(null);
    }

    if (data.questionData.type === "technical" || data.questionData.type === "dsa") {
      setInitialCode(data.questionData.initial_code ?? "");
      setUserAnswer(data.questionData.initial_code ?? "");
    } else {
      setInitialCode("");
    }
  }, [speakIfEnabled]);

  // Removed unused handlePlayQuestion to satisfy no-unused-vars

  // Initialize from sessionStorage set by /resume page after start-interview
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem('interviewSession');
      const resumeDataRaw = sessionStorage.getItem('interviewData');

      if (raw) {
        const data = JSON.parse(raw);
        if (data?.sessionId) {
          setSessionId(data.sessionId);
          updateQuestionState(data);

          // Save to database
          if (resumeDataRaw) {
            const resumeData = JSON.parse(resumeDataRaw);
            db.saveInterviewData({
              sessionId: data.sessionId,
              resumeData: {
                jobRole: resumeData.jobRole || '',
                companyName: resumeData.companyName || '',
                yearsOfExperience: resumeData.yearsOfExperience || 0,
                jobDescription: resumeData.jobDescription || ''
              },
              currentQuestion: data.questionData?.question,
              currentRound: data.roundTitle,
              timestamp: Date.now()
            });
          }
          return;
        }
      }
    } catch {
      // ignore JSON errors
    }
    // Fallback to resume if nothing is present
    router.push('/resume');
  }, [router, updateQuestionState]);

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const handleRecording = () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      setIsRecording(false);
    } else {
      navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
          mediaRecorderRef.current = new MediaRecorder(stream);
          mediaRecorderRef.current.ondataavailable = (e) => {
            audioChunksRef.current.push(e.data);
          };
          mediaRecorderRef.current.onstop = async () => {
            const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
            audioChunksRef.current = [];

            const audioFormData = new FormData();
            audioFormData.append('audio_file', audioBlob);
            // Pass sessionId to store openSMILE features
            if (sessionId) {
              audioFormData.append('sessionId', sessionId);
            }

            try {
              const response = await fetch(`${API_BASE}/api/stt`, {
                method: 'POST',
                body: audioFormData,
              });
              const data = await response.json();
              setUserAnswer(data.text);

              // Log openSMILE features if returned
              if (data.openSmileFeatures) {
                console.log('🎤 openSMILE features extracted:', data.openSmileFeatures);
              }
            } catch (err) {
              console.error("STT error:", err);
              setError("Failed to transcribe audio.");
            }
          };
          mediaRecorderRef.current.start();
          setIsRecording(true);
        })
        .catch(err => {
          console.error("Microphone access denied:", err);
          setError("Please grant microphone access to use voice mode.");
        });
    }
  };


  const handleSubmitAnswer = async () => {
    if (!sessionId) {
      return;
    }

    let answerToSubmit = userAnswer;
    if (roundType === 'mcq' && selectedMcqOption) {
      answerToSubmit = selectedMcqOption;
    } else if (roundType === 'mcq' && !selectedMcqOption) {
      setError("Please select an option.");
      return;
    }

    if (!answerToSubmit.trim() && roundType !== 'mcq') {
      return;
    }

    stopTimer(); // Stop timer when submitting
    setIsLoading(true);
    setShowFeedback(false);

    try {
      const response = await fetch(`${API_BASE}/api/submit-answer`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ sessionId, userAnswer: answerToSubmit }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to submit answer.');
      }

      const data = await response.json();
      updateQuestionState(data);
    } catch (err: unknown) {
      console.error("Error submitting answer:", err);
      const message =
        err instanceof Error
          ? err.message
          : typeof err === "string"
            ? err
            : "Failed to submit answer.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  // Remove local voice toggle - using global voice context now

  if (isComplete && sessionId) {
    return (
      <InterviewSummary
        sessionId={sessionId}
        onNewInterview={() => router.push("/resume")}
      />
    );
  }

  if (error && !sessionId) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100 p-4">
        <div className="w-full max-w-2xl p-8 bg-white rounded-lg shadow-md text-center">
          <h1 className="text-3xl font-bold text-red-600 mb-4">Error 😞</h1>
          <p className="text-gray-700">{error}</p>
          <button
            onClick={() => setError(null)}
            className="mt-6 px-6 py-3 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 transition-colors"
          >
            Dismiss
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen p-4">
      <div className="animated-grid" />
      <div className="relative w-full max-w-7xl mx-auto">
        {sessionId ? (
          <>
            <h1 className="page-title text-center mb-6">{roundTitle}</h1>

            {isLoading ? (
              <div className="text-center text-white/80 flex flex-col items-center">
                <svg className="animate-spin h-8 w-8 text-blue-500 mb-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <p>Loading question...</p>
              </div>
            ) : (
              <div className="flex flex-col lg:flex-row gap-6">
                {/* Left Section - 75% - Interview Interface */}
                <div className="flex-1 lg:w-3/4 space-y-6 p-8 rounded-lg glass-effect neon-border">

                  {/* User Video - Compact at top of left section */}
                  <div className="w-full max-w-xs">
                    <h3 className="text-sm font-semibold text-white mb-2">Your Video</h3>
                    <UserVideoFeed />
                  </div>

                  {/* Interview Mode Toggle */}
                  <div className="flex items-center justify-center space-x-4 p-4 rounded-lg border border-white/15 bg-white/5">
                    <span className="text-sm text-white/80 font-medium">Interview Mode:</span>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => setInterviewMode('audio')}
                        className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all ${interviewMode === 'audio'
                          ? 'bg-blue-500 text-white shadow-lg'
                          : 'bg-white/10 text-white/60 hover:bg-white/20'
                          }`}
                      >
                        <Volume2 className="w-4 h-4" />
                        <span className="text-sm font-medium">🎙️ Audio Mode</span>
                      </button>
                      <button
                        onClick={() => setInterviewMode('avatar')}
                        className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all ${interviewMode === 'avatar'
                          ? 'bg-purple-500 text-white shadow-lg'
                          : 'bg-white/10 text-white/60 hover:bg-white/20'
                          }`}
                      >
                        <Video className="w-4 h-4" />
                        <span className="text-sm font-medium">🎭 Avatar Mode</span>
                      </button>
                    </div>
                  </div>

                  {/* Timer and Progress Bar */}
                  <div className="flex items-center justify-between p-4 rounded-lg border border-white/15 bg-white/5">
                    <div className="flex items-center space-x-4">
                      <div className="text-sm text-white/80">
                        <span className="font-medium text-white">Round:</span> {roundTitle}
                      </div>
                      <div className="text-sm text-white/80">
                        <span className="font-medium text-white">Type:</span> {roundType?.toUpperCase()}
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <div className={`text-lg font-bold ${timeRemaining <= 60 ? 'text-red-400' : timeRemaining <= 180 ? 'text-orange-300' : 'text-green-300'}`}>
                        ⏱️ {formatTime(timeRemaining)}
                      </div>
                      {isTimerActive && (
                        <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                      )}
                    </div>
                  </div>

                  <div className="p-6 rounded-lg border border-white/15 bg-white/5">
                    <h2 className="section-title mb-2 text-white">Question:</h2>
                    <p className="text-white whitespace-pre-wrap">{question}</p>
                  </div>

                  {/* Feedback Display - Collapsible Dropdown */}
                  {feedback && (
                    <div className="rounded-xl border border-white/10 bg-gradient-to-br from-white/5 to-white/[0.02] backdrop-blur-sm overflow-hidden">
                      {/* Collapsible Header */}
                      <button
                        onClick={() => setShowFeedback(!showFeedback)}
                        className="w-full p-4 flex items-center justify-between hover:bg-white/5 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-lg bg-blue-500/20">
                            <span className="text-lg">📊</span>
                          </div>
                          <div className="text-left">
                            <h3 className="text-sm font-semibold text-white">Answer Feedback</h3>
                            <span className="text-xs text-white/50">Previous answer analysis</span>
                          </div>
                        </div>

                        <div className="flex items-center gap-3">
                          {/* Score Preview */}
                          <div className={`px-3 py-1 rounded-full ${(feedback?.score ?? 0) >= 8 ? 'bg-green-500' : (feedback?.score ?? 0) >= 6 ? 'bg-yellow-500' : 'bg-red-500'} text-white text-sm font-bold`}>
                            {feedback?.score ?? 0}/10
                          </div>

                          {/* Expand/Collapse Icon */}
                          <div className="text-white/60">
                            {showFeedback ? (
                              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                              </svg>
                            ) : (
                              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                              </svg>
                            )}
                          </div>
                        </div>
                      </button>

                      {/* Expandable Content */}
                      {showFeedback && (
                        <div className="px-4 pb-4 space-y-4">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
                              <h4 className="font-medium text-green-300 mb-2 text-sm">✅ Strengths</h4>
                              <ul className="text-sm text-white/90 space-y-1">
                                {feedback.strengths?.map((strength: string, idx: number) => (
                                  <li key={idx} className="text-xs">• {strength}</li>
                                ))}
                              </ul>
                            </div>
                            <div className="p-3 rounded-lg bg-orange-500/10 border border-orange-500/20">
                              <h4 className="font-medium text-orange-300 mb-2 text-sm">🔧 Areas to Improve</h4>
                              <ul className="text-sm text-white/90 space-y-1">
                                {feedback.weaknesses?.map((weakness: string, idx: number) => (
                                  <li key={idx} className="text-xs">• {weakness}</li>
                                ))}
                              </ul>
                            </div>
                          </div>
                          <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                            <p className="text-sm text-white/90">{feedback.feedback_text}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Soft Skills Feedback - Only for speech-based rounds */}
                  {softSkills && (
                    <SoftSkillsFeedback
                      data={softSkills}
                      roundName={roundTitle}
                      roundType={roundType || undefined}
                    />
                  )}

                  <div className="flex space-x-4 items-center">
                    <button
                      onClick={() => speakTTS(question)}
                      className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors"
                    >
                      🔊 Repeat Question
                    </button>
                  </div>

                  {/* STT Error Display */}
                  {sttError && (
                    <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                      <p className="text-sm text-red-300">{sttError}</p>
                    </div>
                  )}

                  {/* Conditional rendering for the code editor, MCQ options, or textarea */}
                  {roundType === "dsa" || roundType === "technical" ? (
                    <CodeEditor
                      initialCode={userAnswer || initialCode}
                      onCodeChange={setUserAnswer}
                      language={language}
                    />
                  ) : roundType === "mcq" && mcqOptions ? (
                    <div className="space-y-4">
                      {mcqOptions.map((option, index) => (
                        <div
                          key={index}
                          onClick={() => setSelectedMcqOption(option)}
                          className={`p-4 border rounded-lg cursor-pointer transition-all duration-200 ${selectedMcqOption === option
                            ? "border-blue-400 bg-white/10 shadow-md"
                            : "border-white/20 bg-white/5 hover:border-blue-300"
                            } text-white`}
                        >
                          <p className="text-white">{option}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {/* Answer Input with Microphone */}
                      <div className="relative">
                        <textarea
                          id="answer"
                          rows={10}
                          value={userAnswer}
                          onChange={(e) => setUserAnswer(e.target.value)}
                          className="w-full p-4 pr-16 border rounded-lg resize-y focus:outline-none focus:ring-2 focus:ring-blue-500 text-white placeholder-white/50 bg-white/5 border-white/20"
                          placeholder="Type your answer or use the microphone to speak..."
                          disabled={isListening}
                        />
                        {/* Microphone Button */}
                        <div className="absolute bottom-4 right-4">
                          <MicrophoneButton
                            isListening={isListening}
                            isSupported={isSTTSupported}
                            hasPermission={hasSTTPermission}
                            onStart={startListening}
                            onStop={stopListening}
                            disabled={isLoading}
                            error={sttError}
                          />
                        </div>
                      </div>
                      {/* Listening Indicator with Interim Transcript */}
                      {isListening && (
                        <div className="flex flex-col space-y-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                          <div className="flex items-center space-x-2">
                            <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse" />
                            <span className="text-sm text-red-300 font-medium">Listening... Speak now</span>
                          </div>
                          {interimTranscript && (
                            <div className="text-sm text-white/60 italic">
                              {`"${interimTranscript}"`}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Hint Section */}
                  {showHint && currentHint && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg relative"
                    >
                      <button
                        onClick={() => setShowHint(false)}
                        className="absolute top-2 right-2 text-yellow-300 hover:text-yellow-100"
                      >
                        <X className="w-4 h-4" />
                      </button>
                      <div className="flex items-start space-x-3">
                        <Lightbulb className="w-5 h-5 text-yellow-400 mt-0.5 flex-shrink-0" />
                        <div>
                          <h4 className="text-sm font-semibold text-yellow-300 mb-1">Hint</h4>
                          <p className="text-sm text-yellow-100/90">{currentHint}</p>
                        </div>
                      </div>
                    </motion.div>
                  )}

                  {/* Action Buttons */}
                  <div className="flex gap-3">
                    <button
                      onClick={handleGetHint}
                      disabled={isLoadingHint || isComplete}
                      className="flex-1 py-3 rounded-lg bg-yellow-600 hover:bg-yellow-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-semibold transition-colors duration-300 flex items-center justify-center space-x-2"
                    >
                      {isLoadingHint ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                          <span>Getting Hint...</span>
                        </>
                      ) : (
                        <>
                          <Lightbulb className="w-4 h-4" />
                          <span>Need a Hint?</span>
                        </>
                      )}
                    </button>

                    <button
                      onClick={handleSubmitAnswer}
                      disabled={(!userAnswer.trim() && !selectedMcqOption) || isLoading}
                      className={`flex-1 py-3 rounded-lg text-white font-semibold transition-colors duration-300 ${(userAnswer.trim() || selectedMcqOption) && !isLoading
                        ? "bg-blue-600 hover:bg-blue-700"
                        : "bg-gray-400 cursor-not-allowed"
                        }`}
                    >
                      Submit Answer
                    </button>
                  </div>
                </div>

                {/* Right Section - 25% - Avatar Video and Chat */}
                <div className="lg:w-1/4 space-y-4">
                  {/* Avatar Video */}
                  <div className="p-4 rounded-lg glass-effect neon-border">
                    <h3 className="text-sm font-semibold text-white mb-3">AI Interviewer</h3>

                    {/* Avatar Generation Loader */}
                    <AnimatePresence mode="wait">
                      {isGeneratingAvatar && (
                        <motion.div
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          exit={{ opacity: 0 }}
                          className="flex flex-col items-center justify-center h-full min-h-[200px] space-y-3"
                        >
                          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
                          <p className="text-sm text-white/80">Interviewer is speaking...</p>
                        </motion.div>
                      )}

                      {!isGeneratingAvatar && (
                        <motion.div
                          initial={{ opacity: 0, scale: 0.95 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 0.95 }}
                          transition={{ duration: 0.3 }}
                        >
                          <AvatarVideo
                            isSpeaking={isAvatarSpeaking}
                            videoUrl={avatarVideoUrl || undefined}
                            onEnded={handleAvatarVideoEnd}
                          />
                        </motion.div>
                      )}
                    </AnimatePresence>

                    {/* Avatar Error Display */}
                    {avatarError && (
                      <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mt-2 p-2 bg-yellow-500/10 border border-yellow-500/20 rounded-lg"
                      >
                        <p className="text-xs text-yellow-300">{avatarError}</p>
                      </motion.div>
                    )}
                  </div>

                  {/* Avatar Chat Box */}
                  <div className="p-4 rounded-lg glass-effect neon-border" style={{ height: '400px' }}>
                    <AvatarChatBox messages={avatarMessages} />
                  </div>

                  {/* Behavior Monitor - CV Analysis */}
                  <div className="p-4 rounded-lg glass-effect neon-border">
                    <h3 className="text-sm font-semibold text-white mb-3">📹 Behavior Analysis</h3>
                    <BehaviorMonitor
                      sessionId={sessionId || undefined}
                      isActive={!isComplete}
                      onFeedbackUpdate={(feedback) => {
                        console.log('Behavior feedback:', feedback);
                      }}
                    />
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="text-center">
            <div className="animate-spin h-8 w-8 text-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading interview session...</p>
          </div>
        )}
      </div>
    </div>
  );
}
