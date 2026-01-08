"use client";
import React, { useEffect, useState } from "react";
import { useSpeak } from "@/hooks/useSpeak";
import { API_BASE } from "../app/lib/api";

interface InterviewSummaryProps {
  sessionId: string;
  onNewInterview: () => void;
}

interface SummaryData {
  session_id: string;
  total_questions: number;
  total_rounds: number;
  overall_score: number;
  time_taken_minutes: number;
  round_summaries: Array<{
    round_title: string;
    questions_count: number;
    average_score: number;
    question_types: string[];
  }>;
  strengths: string[];
  areas_for_improvement: string[];
  recommendations: string[];
  overall_feedback: string;
}

export default function InterviewSummary({ sessionId, onNewInterview }: InterviewSummaryProps) {
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { speakIfEnabled } = useSpeak();

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/interview-summary/${sessionId}`);
        if (!response.ok) {
          throw new Error("Failed to fetch interview summary");
        }
        const data = await response.json();
        setSummary(data);
        
        // Auto-speak overall feedback if voice is enabled
        if (data.overall_feedback) {
          speakIfEnabled(`Interview Complete! ${data.overall_feedback}`);
        }
      } catch (err: unknown) {
        const message =
          err instanceof Error
            ? err.message
            : typeof err === "string"
              ? err
              : "Failed to fetch interview summary";
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    if (sessionId) {
      fetchSummary();
    }
  }, [sessionId, speakIfEnabled]);

  const getScoreColor = (score: number) => {
    if (score >= 8) return "text-green-600";
    if (score >= 6) return "text-yellow-600";
    return "text-red-600";
  };

  const getScoreBg = (score: number) => {
    if (score >= 8) return "bg-green-50 border-green-200";
    if (score >= 6) return "bg-yellow-50 border-yellow-200";
    return "bg-red-50 border-red-200";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100 p-4">
        <div className="w-full max-w-2xl p-8 bg-white rounded-lg shadow-md text-center">
          <div className="animate-spin h-8 w-8 text-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Generating your interview summary...</p>
        </div>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100 p-4">
        <div className="w-full max-w-2xl p-8 bg-white rounded-lg shadow-md text-center">
          <h1 className="text-3xl font-bold text-red-600 mb-4">Error</h1>
          <p className="text-gray-700 mb-6">{error || "Failed to load summary"}</p>
          <button
            onClick={onNewInterview}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors"
          >
            Start New Interview
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 p-4">
      <div className="w-full max-w-4xl p-8 bg-white rounded-lg shadow-md">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-green-600 mb-2">🎉 Interview Complete!</h1>
          <p className="text-gray-600">Here&apos;s your comprehensive performance summary</p>
        </div>

        {/* Overall Score */}
        <div className={`p-6 rounded-lg border-2 mb-8 ${getScoreBg(summary.overall_score)}`}>
          <div className="text-center">
            <div className={`text-6xl font-bold ${getScoreColor(summary.overall_score)} mb-2`}>
              {summary.overall_score.toFixed(1)}/10
            </div>
            <div className="text-lg text-gray-700 font-medium">Overall Score</div>
          </div>
        </div>

        {/* Interview Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="text-center p-4 bg-blue-50 rounded-lg border border-blue-200">
            <div className="text-2xl font-bold text-blue-600">{summary.total_questions}</div>
            <div className="text-sm text-gray-600">Questions</div>
          </div>
          <div className="text-center p-4 bg-purple-50 rounded-lg border border-purple-200">
            <div className="text-2xl font-bold text-purple-600">{summary.total_rounds}</div>
            <div className="text-sm text-gray-600">Rounds</div>
          </div>
          <div className="text-center p-4 bg-indigo-50 rounded-lg border border-indigo-200">
            <div className="text-2xl font-bold text-indigo-600">{summary.time_taken_minutes}</div>
            <div className="text-sm text-gray-600">Minutes</div>
          </div>
          <div className="text-center p-4 bg-green-50 rounded-lg border border-green-200">
            <div className="text-2xl font-bold text-green-600">
              {summary.round_summaries.length > 0 ? 
                (summary.round_summaries.reduce((acc, r) => acc + r.average_score, 0) / summary.round_summaries.length).toFixed(1) : 
                summary.overall_score.toFixed(1)
              }
            </div>
            <div className="text-sm text-gray-600">Avg/Round</div>
          </div>
        </div>

        {/* Round Performance */}
        {summary.round_summaries.length > 0 && (
          <div className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">📊 Round Performance</h2>
            <div className="space-y-4">
              {summary.round_summaries.map((round, idx) => (
                <div key={idx} className="p-4 bg-gray-50 rounded-lg border">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold text-gray-800">{round.round_title}</h3>
                      <p className="text-sm text-gray-600">
                        {round.questions_count} questions • {round.question_types.join(", ")}
                      </p>
                    </div>
                    <div className={`text-2xl font-bold ${getScoreColor(round.average_score)}`}>
                      {round.average_score.toFixed(1)}/10
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Feedback Sections */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {/* Strengths */}
          <div className="p-6 bg-green-50 rounded-lg border border-green-200">
            <h3 className="text-lg font-semibold text-green-700 mb-4">✅ Strengths</h3>
            <ul className="space-y-2">
              {summary.strengths.map((strength, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="text-green-500 mt-1">•</span>
                  <span>{strength}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Areas for Improvement */}
          <div className="p-6 bg-orange-50 rounded-lg border border-orange-200">
            <h3 className="text-lg font-semibold text-orange-700 mb-4">⚠️ Areas to Improve</h3>
            <ul className="space-y-2">
              {summary.areas_for_improvement.map((area, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="text-orange-500 mt-1">•</span>
                  <span>{area}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Recommendations */}
          <div className="p-6 bg-blue-50 rounded-lg border border-blue-200">
            <h3 className="text-lg font-semibold text-blue-700 mb-4">💡 Recommendations</h3>
            <ul className="space-y-2">
              {summary.recommendations.map((rec, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="text-blue-500 mt-1">•</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Overall Feedback */}
        <div className="p-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200 mb-8">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">📝 Overall Feedback</h3>
          <p className="text-gray-700 leading-relaxed">{summary.overall_feedback}</p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button
            onClick={() => speakIfEnabled(summary.overall_feedback)}
            className="px-6 py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 transition-colors"
          >
            🔊 Hear Feedback
          </button>
          <button
            onClick={() => window.print()}
            className="px-6 py-3 bg-gray-600 text-white rounded-lg font-semibold hover:bg-gray-700 transition-colors"
          >
            📄 Print Summary
          </button>
          <button
            onClick={onNewInterview}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors"
          >
            🚀 Start New Interview
          </button>
        </div>
      </div>
    </div>
  );
}
