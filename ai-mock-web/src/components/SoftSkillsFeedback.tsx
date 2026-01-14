"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronUp, Mic, MessageSquare, User, Star, Award } from "lucide-react";

interface SoftSkillMetric {
    name: string;
    score: number; // 0-5
    feedback: string;
    source: string; // "ai" | "openSMILE" | "behavior_monitor"
}

interface SoftSkillsFeedbackData {
    overallScore: number; // 0-100
    metrics: SoftSkillMetric[];
    details?: Record<string, unknown>;
    openSmileFeatures?: Record<string, unknown>;
}

interface SoftSkillsFeedbackProps {
    data: SoftSkillsFeedbackData | null;
    roundName?: string;
    roundType?: string; // "behavioral" | "technical" | "dsa" | "mcq"
}

const getScoreColor = (score: number, max: number = 5): string => {
    const percentage = (score / max) * 100;
    if (percentage >= 80) return "text-green-400";
    if (percentage >= 60) return "text-yellow-300";
    if (percentage >= 40) return "text-orange-400";
    return "text-red-400";
};

const getProgressColor = (score: number, max: number = 5): string => {
    const percentage = (score / max) * 100;
    if (percentage >= 80) return "bg-green-500";
    if (percentage >= 60) return "bg-yellow-500";
    if (percentage >= 40) return "bg-orange-500";
    return "bg-red-500";
};

const getOverallScoreColor = (score: number): string => {
    if (score >= 80) return "from-green-500 to-emerald-600";
    if (score >= 60) return "from-yellow-500 to-amber-600";
    if (score >= 40) return "from-orange-500 to-orange-600";
    return "from-red-500 to-red-600";
};

const getMetricIcon = (name: string) => {
    switch (name.toLowerCase()) {
        case "communication":
            return <MessageSquare className="w-4 h-4" />;
        case "voice":
            return <Mic className="w-4 h-4" />;
        case "speech delivery":
            return <Mic className="w-4 h-4" />;
        case "body language":
            return <User className="w-4 h-4" />;
        case "confidence":
            return <Star className="w-4 h-4" />;
        default:
            return <Star className="w-4 h-4" />;
    }
};

const getSourceBadge = (source: string) => {
    if (source === "openSMILE") {
        return (
            <span className="px-1.5 py-0.5 text-[10px] bg-purple-500/20 text-purple-300 rounded-full">
                Voice AI
            </span>
        );
    }
    if (source === "behavior_monitor") {
        return (
            <span className="px-1.5 py-0.5 text-[10px] bg-blue-500/20 text-blue-300 rounded-full">
                CV
            </span>
        );
    }
    return null;
};

// Check if round type requires speech/soft skills feedback
const isSpeechBasedRound = (roundType?: string, roundName?: string): boolean => {
    if (!roundType && !roundName) return true; // Default to showing if unknown

    const type = roundType?.toLowerCase() || "";
    const name = roundName?.toLowerCase() || "";

    // Don't show for coding/technical/MCQ rounds
    if (type === "dsa" || type === "mcq" || type === "technical") {
        return false;
    }

    // Check round name for coding keywords
    if (name.includes("coding") || name.includes("algorithm") || name.includes("mcq") || name.includes("assessment")) {
        return false;
    }

    // Show for behavioral, HR, managerial, culture fit rounds
    return true;
};

export default function SoftSkillsFeedback({ data, roundName, roundType }: SoftSkillsFeedbackProps) {
    const [isExpanded, setIsExpanded] = useState(false);

    // Don't render for non-speech-based rounds
    if (!isSpeechBasedRound(roundType, roundName)) {
        return null;
    }

    if (!data) {
        return null;
    }

    const { overallScore, metrics, openSmileFeatures } = data;

    return (
        <div className="rounded-xl border border-white/10 bg-gradient-to-br from-white/5 to-white/[0.02] backdrop-blur-sm overflow-hidden">
            {/* Collapsible Header - Always Visible */}
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full p-4 flex items-center justify-between hover:bg-white/5 transition-colors"
            >
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-purple-500/20">
                        <Star className="w-4 h-4 text-purple-400" />
                    </div>
                    <div className="text-left">
                        <h3 className="text-sm font-semibold text-white">Soft Skills Feedback</h3>
                        {roundName && (
                            <span className="text-xs text-white/50">{roundName}</span>
                        )}
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    {/* Quick Score Preview */}
                    <div className={`px-3 py-1 rounded-full bg-gradient-to-r ${getOverallScoreColor(overallScore)} text-white text-sm font-bold`}>
                        {overallScore}/100
                    </div>

                    {/* Expand/Collapse Icon */}
                    <div className="text-white/60">
                        {isExpanded ? (
                            <ChevronUp className="w-5 h-5" />
                        ) : (
                            <ChevronDown className="w-5 h-5" />
                        )}
                    </div>
                </div>
            </button>

            {/* Expandable Content */}
            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.3 }}
                        className="overflow-hidden"
                    >
                        <div className="px-4 pb-4 space-y-4">
                            {/* Metrics Grid */}
                            <div className="space-y-2">
                                {metrics.map((metric, idx) => (
                                    <div key={idx} className="flex items-center gap-3 p-2 rounded-lg bg-white/5">
                                        {/* Icon */}
                                        <div className="text-white/60">
                                            {getMetricIcon(metric.name)}
                                        </div>

                                        {/* Metric Name */}
                                        <div className="w-28 text-xs text-white/80 truncate font-medium">
                                            {metric.name}
                                        </div>

                                        {/* Progress Bar */}
                                        <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                                            <motion.div
                                                initial={{ width: 0 }}
                                                animate={{ width: `${(metric.score / 5) * 100}%` }}
                                                transition={{ duration: 0.5, delay: idx * 0.1 }}
                                                className={`h-full rounded-full ${getProgressColor(metric.score)}`}
                                            />
                                        </div>

                                        {/* Score */}
                                        <div className={`w-10 text-right text-xs font-semibold ${getScoreColor(metric.score)}`}>
                                            {metric.score.toFixed(1)}/5
                                        </div>

                                        {/* Source Badge */}
                                        <div className="w-14">
                                            {getSourceBadge(metric.source)}
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Feedback Summary */}
                            <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                                <h4 className="text-xs font-semibold text-white/80 mb-2">Quick Feedback</h4>
                                <div className="space-y-1">
                                    {metrics.map((metric, idx) => (
                                        <div key={idx} className="text-xs text-white/60">
                                            <span className="text-white/80 font-medium">{metric.name}:</span>{" "}
                                            {metric.feedback !== "--" ? metric.feedback : "N/A"}
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* openSMILE Voice Analysis (if available) */}
                            {openSmileFeatures ? (
                                <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/20">
                                    <h4 className="text-xs font-semibold text-purple-300 mb-3 flex items-center gap-1">
                                        <Mic className="w-3 h-3" />
                                        Voice Analysis (openSMILE)
                                    </h4>
                                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-[11px]">
                                        {/* Pitch */}
                                        <div className="p-2 rounded bg-white/5">
                                            <span className="text-white/50 block mb-1">Pitch</span>
                                            <span className="text-white/90 font-medium">
                                                {typeof openSmileFeatures.pitch === 'object' &&
                                                    openSmileFeatures.pitch !== null &&
                                                    'mean' in (openSmileFeatures.pitch as object)
                                                    ? `${((openSmileFeatures.pitch as { mean: number }).mean).toFixed(1)} Hz`
                                                    : "--"}
                                            </span>
                                        </div>

                                        {/* Energy */}
                                        <div className="p-2 rounded bg-white/5">
                                            <span className="text-white/50 block mb-1">Energy</span>
                                            <span className="text-white/90 font-medium">
                                                {typeof openSmileFeatures.energy === 'object' &&
                                                    openSmileFeatures.energy !== null &&
                                                    'mean' in (openSmileFeatures.energy as object)
                                                    ? ((openSmileFeatures.energy as { mean: number }).mean).toFixed(3)
                                                    : "--"}
                                            </span>
                                        </div>

                                        {/* Pause Ratio */}
                                        <div className="p-2 rounded bg-white/5">
                                            <span className="text-white/50 block mb-1">Pause Ratio</span>
                                            <span className="text-white/90 font-medium">
                                                {typeof openSmileFeatures.temporal === 'object' &&
                                                    openSmileFeatures.temporal !== null &&
                                                    'pause_ratio' in (openSmileFeatures.temporal as object)
                                                    ? `${(((openSmileFeatures.temporal as { pause_ratio: number }).pause_ratio) * 100).toFixed(0)}%`
                                                    : "--"}
                                            </span>
                                        </div>

                                        {/* Jitter */}
                                        <div className="p-2 rounded bg-white/5">
                                            <span className="text-white/50 block mb-1">Jitter</span>
                                            <span className="text-white/90 font-medium">
                                                {typeof openSmileFeatures.voice_quality === 'object' &&
                                                    openSmileFeatures.voice_quality !== null &&
                                                    'jitter' in (openSmileFeatures.voice_quality as object)
                                                    ? ((openSmileFeatures.voice_quality as { jitter: number }).jitter).toFixed(4)
                                                    : "--"}
                                            </span>
                                        </div>

                                        {/* Shimmer */}
                                        <div className="p-2 rounded bg-white/5">
                                            <span className="text-white/50 block mb-1">Shimmer</span>
                                            <span className="text-white/90 font-medium">
                                                {typeof openSmileFeatures.voice_quality === 'object' &&
                                                    openSmileFeatures.voice_quality !== null &&
                                                    'shimmer' in (openSmileFeatures.voice_quality as object)
                                                    ? ((openSmileFeatures.voice_quality as { shimmer: number }).shimmer).toFixed(4)
                                                    : "--"}
                                            </span>
                                        </div>

                                        {/* Derived Confidence */}
                                        <div className="p-2 rounded bg-purple-500/20">
                                            <span className="text-purple-300/70 block mb-1">Voice Confidence</span>
                                            <span className="text-purple-200 font-bold">
                                                {typeof openSmileFeatures.derived_scores === 'object' &&
                                                    openSmileFeatures.derived_scores !== null &&
                                                    'confidence' in (openSmileFeatures.derived_scores as object)
                                                    ? `${((openSmileFeatures.derived_scores as { confidence: number }).confidence).toFixed(1)}/5`
                                                    : "--"}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            ) : null}

                            {/* Overall Score - Prominent at Bottom */}
                            <div className={`p-4 rounded-lg bg-gradient-to-r ${getOverallScoreColor(overallScore)} text-white`}>
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <Award className="w-6 h-6" />
                                        <div>
                                            <div className="text-sm font-medium opacity-90">Overall Soft Skills Score</div>
                                            <div className="text-xs opacity-75">Based on communication, voice, and presence</div>
                                        </div>
                                    </div>
                                    <div className="text-3xl font-bold">
                                        {overallScore}<span className="text-lg opacity-75">/100</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
