"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Mic, MicOff, Send, MessageSquare, Loader2, PlayCircle, StopCircle, RefreshCcw, Volume2 } from "lucide-react";
import { API_BASE } from "../lib/api";
import { useTTS } from "@/hooks/useTTS";
import HRBehaviorMonitor, { HRBehaviorScores } from "@/components/HRBehaviorMonitor";
import SoftSkillsFeedback from "@/components/SoftSkillsFeedback";
import InterviewSummary from "@/components/InterviewSummary";

// Import types for SoftSkillsFeedback
interface SoftSkillMetric {
    name: string;
    score: number;
    feedback: string;
    source: string;
}

interface SoftSkillsFeedbackData {
    overallScore: number;
    metrics: SoftSkillMetric[];
    details?: Record<string, unknown>;
    openSmileFeatures?: Record<string, unknown>;
}

interface FeedbackData {
    feedback_text: string;
    score: number;
    strengths: string[];
    weaknesses: string[];
}

export default function HRInterviewPage() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [isInterviewing, setIsInterviewing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [questionNumber, setQuestionNumber] = useState(1);
  const [feedback, setFeedback] = useState<FeedbackData | null>(null);
  const [softSkills, setSoftSkills] = useState<SoftSkillsFeedbackData | null>(null);
  const [behaviorScores, setBehaviorScores] = useState<HRBehaviorScores>({ eyeContact: 0, attention: 0, stability: 0 });

  const { speak, stop: stopTTS } = useTTS();
  const [userAnswer, setUserAnswer] = useState("");
  const [openSmileFeatures, setOpenSmileFeatures] = useState<Record<string, unknown> | null>(null);

  // Custom audio STT state
  const [isRecordingAudio, setIsRecordingAudio] = useState(false);
  const [sttError, setSttError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Speak when new question arrives
  useEffect(() => {
    if (currentQuestion) {
      speak(currentQuestion);
    }
  }, [currentQuestion, speak]);

  const startRecordingAudio = async () => {
    try {
      setSttError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        setIsSubmitting(true);
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append('audio_file', audioBlob, 'recording.webm');
        if (sessionId) formData.append('sessionId', sessionId);

        try {
          const response = await fetch(`${API_BASE}/api/stt`, {
            method: 'POST',
            body: formData,
          });
          if (!response.ok) throw new Error("STT failed");
          
          const data = await response.json();
          if (data.text) {
             setUserAnswer((prev) => prev ? prev + " " + data.text : data.text);
          }
        } catch (err) {
          console.error("STT error:", err);
          setSttError("Failed to transcribe audio.");
        } finally {
          setIsSubmitting(false);
        }
      };

      mediaRecorderRef.current.start();
      setIsRecordingAudio(true);
    } catch (err) {
      console.error("Microphone access denied:", err);
      setSttError("Please grant microphone access.");
    }
  };

  const stopRecordingAudio = () => {
    if (mediaRecorderRef.current && isRecordingAudio) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(t => t.stop());
      setIsRecordingAudio(false);
    }
  };

  const startInterview = async () => {
    try {
      setIsInterviewing(true);
      const res = await fetch(`${API_BASE}/api/start-hr-interview`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to start HR interview");
      const data = await res.json();
      setSessionId(data.sessionId);
      setCurrentQuestion(data.questionData.question);
      setQuestionNumber(1);
      setFeedback(null);
      setSoftSkills(null);
    } catch (err) {
      console.error(err);
      alert("Error starting interview. Please check server connection.");
    }
  };

  const handleScoreUpdate = (scores: HRBehaviorScores) => {
    setBehaviorScores(scores);
  };

  const submitAnswer = async () => {
    if (!sessionId || !currentQuestion || !userAnswer.trim()) {
       alert("Please type or record an answer first.");
       return;
    }

    try {
      setIsSubmitting(true);
      const res = await fetch(`${API_BASE}/api/submit-answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sessionId,
          userAnswer: userAnswer,
          behaviorData: behaviorScores,
        }),
      });

      if (!res.ok) throw new Error("Failed to submit answer");
      const data = await res.json();
      
      setFeedback(data.feedback);
      setSoftSkills(data.softSkills);

      if (data.isComplete || questionNumber >= 5) {
         setIsComplete(true);
      } else {
         setCurrentQuestion(data.questionData.question);
         setQuestionNumber((prev) => prev + 1);
         setUserAnswer("");
      }
    } catch (err) {
      console.error(err);
      alert("Error submitting answer.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isComplete && sessionId) {
    return (
       <>
         <div className="pt-20 min-h-screen bg-gray-50">
           <InterviewSummary sessionId={sessionId} onNewInterview={() => {
              setIsComplete(false);
              setSessionId(null);
              startInterview();
           }} />
         </div>
       </>
    );
  }

  return (
    <>
      <div className="min-h-screen bg-gray-50 pt-24 px-4 pb-12">
        <div className="max-w-7xl auto mx-auto">
          {!isInterviewing ? (
             <div className="flex flex-col items-center justify-center min-h-[60vh]">
               <h1 className="text-4xl font-bold text-gray-900 mb-4">HR Interview Prep</h1>
               <p className="text-lg text-gray-600 mb-8 max-w-2xl text-center">
                 Practice 5 essential HR behavioral questions. Your camera and microphone will be used to track your <strong>eye contact</strong>, <strong>posture</strong>, and <strong>vocal delivery</strong> in real-time.
               </p>
               <button
                 onClick={startInterview}
                 className="flex items-center gap-2 px-8 py-4 bg-primary text-white rounded-full font-semibold hover:bg-primary/90 transition-all shadow-lg hover:shadow-xl hover:-translate-y-1"
               >
                 <PlayCircle className="w-5 h-5" />
                 Start Interview
               </button>
             </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              {/* Left Column: Video & Behavior */}
              <div className="lg:col-span-5 space-y-6">
                <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100">
                  <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    Live Analysis
                  </h3>
                  <div className="aspect-video bg-black rounded-lg overflow-hidden border border-gray-200">
                    <HRBehaviorMonitor onScoreUpdate={handleScoreUpdate} isActive={!isComplete} />
                  </div>
                   <div className="mt-4 grid grid-cols-3 gap-2">
                     <div className="bg-gray-50 p-3 rounded-lg text-center border">
                        <div className="text-xs text-gray-500 mb-1">Eye Contact</div>
                        <div className="font-bold text-primary">{behaviorScores.eyeContact.toFixed(0)}%</div>
                     </div>
                     <div className="bg-gray-50 p-3 rounded-lg text-center border">
                         <div className="text-xs text-gray-500 mb-1">Attention</div>
                         <div className="font-bold text-green-600">{behaviorScores.attention.toFixed(0)}%</div>
                     </div>
                     <div className="bg-gray-50 p-3 rounded-lg text-center border">
                         <div className="text-xs text-gray-500 mb-1">Stability</div>
                         <div className="font-bold text-blue-600">{behaviorScores.stability.toFixed(0)}%</div>
                     </div>
                   </div>
                </div>
              </div>

              {/* Right Column: Q&A */}
              <div className="lg:col-span-7 space-y-6">
                 {/* Progress & Question */}
                 <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                    <div className="flex justify-between items-center mb-4">
                       <span className="text-xs font-semibold px-3 py-1 bg-primary/10 text-primary rounded-full uppercase tracking-wider">
                         Question {questionNumber} / 5
                       </span>
                    </div>
                    <div className="flex items-start gap-4">
                      <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                        <MessageSquare className="w-5 h-5 text-blue-600" />
                      </div>
                      <h2 className="text-2xl font-semibold text-gray-800 leading-tight">
                        {currentQuestion}
                      </h2>
                      <button
                        onClick={() => speak(currentQuestion)}
                        className="ml-auto p-2 text-primary hover:bg-primary/10 rounded-full transition-colors"
                        title="Repeat Question"
                      >
                        <Volume2 className="w-5 h-5" />
                      </button>
                    </div>
                 </div>

                 {/* Recording Section */}
                 <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                    <div className="flex justify-between items-center mb-4">
                       <h3 className="font-semibold text-gray-700">Your Answer</h3>
                       {isRecordingAudio && (
                          <div className="flex items-center gap-2 text-red-500 text-sm font-medium">
                            <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                            Recording...
                          </div>
                       )}
                    </div>
                    <div className="relative mb-4">
                      <textarea
                        id="answer"
                        value={userAnswer}
                        onChange={(e) => setUserAnswer(e.target.value)}
                        className="w-full p-4 border border-gray-200 rounded-lg resize-y focus:outline-none focus:ring-2 focus:ring-primary text-gray-800 placeholder-gray-400 shadow-sm"
                        placeholder="Type your answer, or use the microphone to speak..."
                        disabled={isRecordingAudio}
                        rows={6}
                      />
                    </div>

                    <div className="flex items-center gap-4">
                       {!isRecordingAudio ? (
                          <button
                            onClick={startRecordingAudio}
                            disabled={isSubmitting}
                            className="flex items-center gap-2 px-6 py-3 bg-red-50 text-red-600 rounded-full font-medium hover:bg-red-100 transition-colors border border-red-200 disabled:opacity-50"
                          >
                            <Mic className="w-5 h-5" />
                            Record Answer
                          </button>
                       ) : (
                           <button
                             onClick={stopRecordingAudio}
                             className="flex items-center gap-2 px-6 py-3 bg-red-600 text-white rounded-full font-medium hover:bg-red-700 transition-colors shadow-md"
                           >
                             <StopCircle className="w-5 h-5" />
                             Stop Recording
                           </button>
                       )}

                       {userAnswer && !isRecordingAudio && (
                           <button
                             onClick={() => {
                                setUserAnswer("");
                             }}
                             disabled={isSubmitting}
                             className="flex items-center gap-2 px-4 py-3 text-gray-600 hover:text-gray-900 transition-colors disabled:opacity-50"
                           >
                             <RefreshCcw className="w-4 h-4" />
                             Retry
                           </button>
                       )}

                       <div className="flex-1" />

                       <button
                          onClick={submitAnswer}
                          disabled={!userAnswer.trim() || isRecordingAudio || isSubmitting}
                          className="flex items-center gap-2 px-8 py-3 bg-primary text-white rounded-full font-semibold hover:bg-primary/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
                       >
                          {isSubmitting ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                          {questionNumber >= 5 ? "Finish Interview" : "Submit & Next"}
                       </button>
                    </div>
                    {sttError && <p className="text-red-500 mt-2 text-sm">{sttError}</p>}
                 </div>

                 {/* Feedback Section (if previous question had feedback) */}
                 {feedback && (
                    <div className="bg-blue-50/50 p-6 rounded-xl border border-blue-100">
                       <h3 className="font-semibold text-blue-800 mb-2">Previous Answer Feedback</h3>
                       <p className="text-gray-700">{feedback.feedback_text}</p>
                    </div>
                 )}
                 {softSkills && (
                    <SoftSkillsFeedback data={softSkills} roundName="HR Interview" roundType="behavioral" />
                 )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
