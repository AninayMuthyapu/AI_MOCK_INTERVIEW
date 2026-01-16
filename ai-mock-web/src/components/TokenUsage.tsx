"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Zap, TrendingUp, ChevronDown, ChevronUp } from "lucide-react";
import { API_BASE } from "@/app/lib/api";

interface TokenStats {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    api_calls: number;
}

interface TokenUsageProps {
    sessionId?: string | null;
    refreshInterval?: number; // ms, default 10000
}

export default function TokenUsage({ sessionId, refreshInterval = 10000 }: TokenUsageProps) {
    const [sessionStats, setSessionStats] = useState<TokenStats | null>(null);
    const [globalStats, setGlobalStats] = useState<TokenStats | null>(null);
    const [isExpanded, setIsExpanded] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchStats = async () => {
        try {
            if (sessionId) {
                const response = await fetch(`${API_BASE}/api/token-stats/${sessionId}`);
                if (response.ok) {
                    const data = await response.json();
                    setSessionStats(data.session);
                    setGlobalStats(data.global);
                    setError(null);
                }
            } else {
                const response = await fetch(`${API_BASE}/api/token-stats`);
                if (response.ok) {
                    const data = await response.json();
                    setGlobalStats(data);
                    setError(null);
                }
            }
        } catch (err) {
            setError("Failed to fetch token stats");
        }
    };

    useEffect(() => {
        fetchStats();
        const interval = setInterval(fetchStats, refreshInterval);
        return () => clearInterval(interval);
    }, [sessionId, refreshInterval]);

    const formatNumber = (num: number): string => {
        if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
        if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
        return num.toString();
    };

    // Use session stats, global stats, or default to zeros
    const stats = sessionStats || globalStats || {
        input_tokens: 0,
        output_tokens: 0,
        total_tokens: 0,
        api_calls: 0
    };

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="fixed bottom-4 right-4 z-50"
        >
            <div className="rounded-xl border border-purple-500/30 bg-gradient-to-br from-purple-900/80 to-indigo-900/80 backdrop-blur-md shadow-lg overflow-hidden">
                {/* Compact Header - Always visible */}
                <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="w-full px-4 py-2 flex items-center gap-3 hover:bg-white/5 transition-colors"
                >
                    <div className="p-1.5 rounded-lg bg-purple-500/30">
                        <Zap className="w-4 h-4 text-purple-300" />
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-xs font-medium text-white/90">
                            {formatNumber(stats.total_tokens)} tokens
                        </span>
                        <span className="text-[10px] text-white/50">
                            ({stats.api_calls} calls)
                        </span>
                    </div>
                    <div className="ml-auto text-white/50">
                        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
                    </div>
                </button>

                {/* Expanded Details */}
                {isExpanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="px-4 pb-3 space-y-2 border-t border-white/10"
                    >
                        <div className="pt-2 text-[10px] text-white/50 uppercase tracking-wide">
                            {sessionId ? "Session Usage" : "Global Usage"}
                        </div>

                        {/* Input/Output breakdown */}
                        <div className="flex gap-4 text-xs">
                            <div className="flex items-center gap-1.5">
                                <div className="w-2 h-2 rounded-full bg-blue-400"></div>
                                <span className="text-white/70">Input:</span>
                                <span className="text-white font-medium">{formatNumber(stats.input_tokens)}</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                                <div className="w-2 h-2 rounded-full bg-green-400"></div>
                                <span className="text-white/70">Output:</span>
                                <span className="text-white font-medium">{formatNumber(stats.output_tokens)}</span>
                            </div>
                        </div>

                        {/* Progress bar visualization */}
                        <div className="h-2 rounded-full bg-white/10 overflow-hidden flex">
                            <div
                                className="h-full bg-blue-500"
                                style={{ width: `${(stats.input_tokens / stats.total_tokens) * 100}%` }}
                            />
                            <div
                                className="h-full bg-green-500"
                                style={{ width: `${(stats.output_tokens / stats.total_tokens) * 100}%` }}
                            />
                        </div>

                        {/* Global stats if viewing session */}
                        {sessionId && globalStats && (
                            <div className="pt-2 border-t border-white/10">
                                <div className="text-[10px] text-white/40 flex items-center gap-1">
                                    <TrendingUp className="w-3 h-3" />
                                    Global: {formatNumber(globalStats.total_tokens)} total
                                </div>
                            </div>
                        )}
                    </motion.div>
                )}
            </div>
        </motion.div>
    );
}
