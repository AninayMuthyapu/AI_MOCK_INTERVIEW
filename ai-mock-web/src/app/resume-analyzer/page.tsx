"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import Link from "next/link";
import { API_BASE } from "../lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────
interface AnalysisResult {
    ats_score: number;
    content_relevance: number;
    clarity_score: number;
    professional_language: number;
    formatting_score: number;
    jd_match_score: number | null;
    keyword_match_percentage: number;
    strengths: string[];
    weaknesses: string[];
    recommendations: string[];
    overall_feedback: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function scoreLabel(score: number): { label: string; color: string; bg: string } {
    if (score >= 85) return { label: "Excellent", color: "text-emerald-600", bg: "bg-emerald-50" };
    if (score >= 70) return { label: "Strong", color: "text-blue-600", bg: "bg-blue-50" };
    if (score >= 50) return { label: "Average", color: "text-amber-600", bg: "bg-amber-50" };
    return { label: "Weak", color: "text-red-500", bg: "bg-red-50" };
}

// ─── Circular Gauge ───────────────────────────────────────────────────────────
function CircularGauge({
    score,
    label,
    size = 120,
    animated = false,
}: {
    score: number;
    label: string;
    size?: number;
    animated?: boolean;
}) {
    const [displayScore, setDisplayScore] = useState(0);
    const radius = (size - 16) / 2;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (displayScore / 100) * circumference;
    const { label: statusLabel, color } = scoreLabel(score);

    useEffect(() => {
        if (!animated) { setDisplayScore(score); return; }
        let start = 0;
        const step = score / 40;
        const timer = setInterval(() => {
            start += step;
            if (start >= score) { setDisplayScore(score); clearInterval(timer); }
            else setDisplayScore(Math.round(start));
        }, 20);
        return () => clearInterval(timer);
    }, [score, animated]);

    const strokeColor =
        displayScore >= 85 ? "#10b981" :
            displayScore >= 70 ? "#3b82f6" :
                displayScore >= 50 ? "#f59e0b" : "#ef4444";

    return (
        <div className="flex flex-col items-center gap-2">
            <div className="relative" style={{ width: size, height: size }}>
                <svg width={size} height={size} className="-rotate-90">
                    <circle
                        cx={size / 2} cy={size / 2} r={radius}
                        fill="none" stroke="currentColor"
                        strokeWidth="8" className="text-border/30"
                    />
                    <circle
                        cx={size / 2} cy={size / 2} r={radius}
                        fill="none" stroke={strokeColor}
                        strokeWidth="8" strokeLinecap="round"
                        strokeDasharray={circumference}
                        strokeDashoffset={strokeDashoffset}
                        style={{ transition: "stroke-dashoffset 0.05s linear" }}
                    />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-xl font-bold text-foreground">{displayScore}</span>
                    <span className="text-[10px] text-muted-foreground font-medium">/100</span>
                </div>
            </div>
            <div className="text-center">
                <p className="text-sm font-semibold text-foreground">{label}</p>
                <span className={`text-xs font-medium ${color}`}>{statusLabel}</span>
            </div>
        </div>
    );
}

// ─── Animated Loading Panel ───────────────────────────────────────────────────
function LoadingPanel({ mode }: { mode: "jd" | "ats" }) {
    const steps = [
        "Extracting resume content…",
        "Evaluating content relevance…",
        "Checking clarity & language…",
        "Analyzing formatting & layout…",
        mode === "jd" ? "Matching against job description…" : "Computing ATS compatibility…",
        "Generating feedback…",
    ];
    const [activeStep, setActiveStep] = useState(0);

    useEffect(() => {
        const timer = setInterval(() => {
            setActiveStep((prev) => (prev < steps.length - 1 ? prev + 1 : prev));
        }, 1400);
        return () => clearInterval(timer);
    }, []);

    return (
        <div className="bg-card border border-border rounded-[20px] p-8 shadow-md mt-6">
            <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                    <svg className="w-5 h-5 text-primary animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                    </svg>
                </div>
                <div>
                    <p className="font-semibold text-foreground">Analyzing your resume…</p>
                    <p className="text-sm text-muted-foreground">AI is evaluating content, clarity, and formatting.</p>
                </div>
            </div>
            <div className="space-y-3">
                {steps.map((step, i) => (
                    <div key={i} className="flex items-center gap-3">
                        <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-500 ${i < activeStep ? "bg-primary" : i === activeStep ? "bg-primary/30 animate-pulse" : "bg-border/40"
                            }`}>
                            {i < activeStep && (
                                <svg className="w-3 h-3 text-primary-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                </svg>
                            )}
                        </div>
                        <span className={`text-sm transition-colors duration-300 ${i <= activeStep ? "text-foreground font-medium" : "text-muted-foreground"
                            }`}>{step}</span>
                    </div>
                ))}
            </div>
            {/* Progress bar */}
            <div className="mt-6 h-1.5 bg-border/30 rounded-full overflow-hidden">
                <div
                    className="h-full bg-gradient-to-r from-primary to-accent rounded-full transition-all duration-700"
                    style={{ width: `${((activeStep + 1) / steps.length) * 100}%` }}
                />
            </div>
        </div>
    );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function ResumeAnalyzerPage() {
    const [resumeFile, setResumeFile] = useState<File | null>(null);
    const [jobDescription, setJobDescription] = useState("");
    const [isDragging, setIsDragging] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [loadingMode, setLoadingMode] = useState<"jd" | "ats">("ats");
    const [result, setResult] = useState<AnalysisResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [analysisMode, setAnalysisMode] = useState<"jd" | "ats" | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const resultsRef = useRef<HTMLDivElement>(null);

    const handleFile = (file: File) => {
        if (file.type !== "application/pdf" &&
            file.type !== "application/vnd.openxmlformats-officedocument.wordprocessingml.document") {
            setError("Please upload a PDF or DOCX file.");
            return;
        }
        setResumeFile(file);
        setError(null);
        setResult(null);
    };

    const onDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
    }, []);

    const analyze = async (mode: "jd" | "ats") => {
        if (!resumeFile) { setError("Please upload a resume first."); return; }
        if (mode === "jd" && !jobDescription.trim()) {
            setError("Please paste a job description to use this mode.");
            return;
        }
        setError(null);
        setResult(null);
        setIsLoading(true);
        setLoadingMode(mode);
        setAnalysisMode(mode);

        const formData = new FormData();
        formData.append("resumeFile", resumeFile);
        if (jobDescription.trim()) formData.append("jobDescription", jobDescription);

        try {
            const res = await fetch(`${API_BASE}/api/analyze-resume`, {
                method: "POST",
                body: formData,
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Analysis failed.");
            }
            const data: AnalysisResult = await res.json();
            setResult(data);
            setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Analysis failed. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    const downloadSuggestions = () => {
        if (!result) return;
        const lines = [
            "RESUME ANALYSIS REPORT",
            "======================",
            "",
            `ATS Score: ${result.ats_score}/100`,
            result.jd_match_score != null ? `JD Match Score: ${result.jd_match_score}/100` : "",
            "",
            "METRIC SCORES",
            `Content Relevance: ${result.content_relevance}/100`,
            `Clarity & Conciseness: ${result.clarity_score}/100`,
            `Professional Language: ${result.professional_language}/100`,
            `Formatting & Layout: ${result.formatting_score}/100`,
            "",
            "STRENGTHS",
            ...result.strengths.map((s) => `• ${s}`),
            "",
            "AREAS TO IMPROVE",
            ...result.weaknesses.map((w) => `• ${w}`),
            "",
            "RECOMMENDATIONS",
            ...result.recommendations.map((r) => `• ${r}`),
            "",
            "OVERALL FEEDBACK",
            result.overall_feedback,
        ].filter(Boolean).join("\n");

        const blob = new Blob([lines], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = "resume-analysis.txt"; a.click();
        URL.revokeObjectURL(url);
    };

    const metrics = result ? [
        { label: "Content Relevance", score: result.content_relevance },
        { label: "Clarity & Conciseness", score: result.clarity_score },
        { label: "Professional Language", score: result.professional_language },
        { label: "Formatting & Layout", score: result.formatting_score },
    ] : [];

    return (
        <div className="min-h-screen bg-background">
            {/* Nav */}
            <nav className="sticky top-0 z-40 bg-background/80 backdrop-blur-md border-b border-border/50">
                <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
                    <Link href="/" className="flex items-center gap-2 group">
                        <div className="w-8 h-8 bg-gradient-to-br from-primary to-accent rounded-lg flex items-center justify-center">
                            <span className="text-primary-foreground font-bold text-sm">H</span>
                        </div>
                        <span className="font-bold text-foreground">HackInterview</span>
                    </Link>
                    <Link
                        href="/resume"
                        className="text-sm text-muted-foreground hover:text-primary transition-colors flex items-center gap-1"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                        Back to Interview Setup
                    </Link>
                </div>
            </nav>

            <div className="max-w-5xl mx-auto px-6 py-12">
                {/* Header */}
                <div className="text-center mb-12">
                    <div className="inline-flex items-center gap-2 bg-primary/10 text-primary rounded-full px-4 py-1.5 text-sm font-semibold mb-4">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        AI-Powered
                    </div>
                    <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-foreground mb-4">
                        Resume{" "}
                        <span className="bg-clip-text text-transparent bg-gradient-to-r from-primary to-accent">
                            Analyzer
                        </span>
                    </h1>
                    <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                        Upload your resume to get ATS score, AI feedback, and job-specific insights.
                    </p>
                </div>

                {/* Upload Card */}
                <div className="bg-card border border-border rounded-[20px] p-8 shadow-md mb-6">
                    <label className="block text-sm font-semibold text-foreground mb-3 uppercase tracking-wider">
                        Upload your resume (PDF or DOCX)
                    </label>
                    <div
                        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                        onDragLeave={() => setIsDragging(false)}
                        onDrop={onDrop}
                        onClick={() => fileInputRef.current?.click()}
                        className={`relative flex flex-col items-center justify-center w-full h-44 border-2 border-dashed rounded-2xl cursor-pointer transition-all duration-300 ${isDragging
                                ? "border-primary bg-primary/5 scale-[1.01]"
                                : resumeFile
                                    ? "border-emerald-400 bg-emerald-50/50 dark:bg-emerald-950/20"
                                    : "border-border/60 bg-muted/30 hover:border-primary/50 hover:bg-primary/5"
                            }`}
                    >
                        <input
                            ref={fileInputRef}
                            type="file"
                            className="hidden"
                            accept=".pdf,.docx"
                            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
                        />
                        {resumeFile ? (
                            <div className="flex flex-col items-center gap-2">
                                <div className="w-12 h-12 bg-emerald-100 dark:bg-emerald-900/40 rounded-xl flex items-center justify-center">
                                    <svg className="w-6 h-6 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                </div>
                                <p className="font-semibold text-emerald-700 dark:text-emerald-400">{resumeFile.name}</p>
                                <p className="text-xs text-muted-foreground">
                                    {(resumeFile.size / 1024).toFixed(0)} KB ·{" "}
                                    <span className="text-primary underline cursor-pointer">Replace file</span>
                                </p>
                            </div>
                        ) : (
                            <div className="flex flex-col items-center gap-3">
                                <div className="w-14 h-14 bg-primary/10 rounded-2xl flex items-center justify-center">
                                    <svg className="w-7 h-7 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                                            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                    </svg>
                                </div>
                                <div className="text-center">
                                    <p className="font-semibold text-foreground">
                                        Drag & drop or{" "}
                                        <span className="text-primary underline">browse</span>
                                    </p>
                                    <p className="text-sm text-muted-foreground mt-1">PDF or DOCX · Max 10 MB</p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Job Description */}
                <div className="bg-card border border-border rounded-[20px] p-8 shadow-md mb-6">
                    <div className="flex items-center justify-between mb-3">
                        <label className="block text-sm font-semibold text-foreground uppercase tracking-wider">
                            Job Description
                        </label>
                        <span className="text-xs bg-muted text-muted-foreground rounded-full px-3 py-1 font-medium">
                            Optional
                        </span>
                    </div>
                    <textarea
                        rows={6}
                        value={jobDescription}
                        onChange={(e) => setJobDescription(e.target.value)}
                        placeholder="Paste job description to compare your resume with a specific role…"
                        className="w-full px-4 py-3 bg-background border border-border rounded-xl text-sm text-foreground placeholder:text-muted-foreground resize-y focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
                    />
                    <p className="text-xs text-muted-foreground mt-2">
                        Adding a JD enables role-specific keyword matching and a JD Match Score.
                    </p>
                </div>

                {/* Action Buttons */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                    <button
                        onClick={() => analyze("jd")}
                        disabled={isLoading}
                        className="group flex items-center justify-center gap-3 px-6 py-4 bg-gradient-to-r from-primary to-accent text-primary-foreground font-semibold rounded-2xl shadow-lg shadow-primary/20 hover:shadow-primary/35 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed disabled:scale-100"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                        </svg>
                        Analyze with Job Description
                    </button>
                    <button
                        onClick={() => analyze("ats")}
                        disabled={isLoading}
                        className="group flex items-center justify-center gap-3 px-6 py-4 bg-card border-2 border-primary/30 text-primary font-semibold rounded-2xl shadow-md hover:bg-primary/5 hover:border-primary/60 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed disabled:scale-100"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                        Get ATS Review
                    </button>
                </div>
                <p className="text-center text-xs text-muted-foreground mb-8">
                    <span className="font-medium text-foreground">Get ATS Review</span> works without a job description — great for a general resume health check.
                </p>

                {/* Error */}
                {error && (
                    <div className="flex items-center gap-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 rounded-2xl px-5 py-4 mb-6 text-sm">
                        <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        {error}
                    </div>
                )}

                {/* Loading */}
                {isLoading && <LoadingPanel mode={loadingMode} />}

                {/* Results Dashboard */}
                {result && !isLoading && (
                    <div ref={resultsRef} className="space-y-6 mt-2">
                        {/* Score Hero Row */}
                        <div className={`grid gap-4 ${result.jd_match_score != null ? "grid-cols-1 sm:grid-cols-2" : "grid-cols-1"}`}>
                            {/* ATS Score */}
                            <div className="bg-card border-2 border-primary/30 rounded-[20px] p-8 shadow-lg flex items-center gap-6"
                                style={{ boxShadow: "0 0 0 1px oklch(0.6 0.18 45 / 0.15), 0 8px 32px oklch(0.6 0.18 45 / 0.12)" }}>
                                <div className="relative w-28 h-28 flex-shrink-0">
                                    <svg width="112" height="112" className="-rotate-90">
                                        <circle cx="56" cy="56" r="48" fill="none" stroke="currentColor"
                                            strokeWidth="10" className="text-border/20" />
                                        <circle cx="56" cy="56" r="48" fill="none"
                                            stroke={result.ats_score >= 70 ? "#f97316" : result.ats_score >= 50 ? "#f59e0b" : "#ef4444"}
                                            strokeWidth="10" strokeLinecap="round"
                                            strokeDasharray={2 * Math.PI * 48}
                                            strokeDashoffset={2 * Math.PI * 48 * (1 - result.ats_score / 100)}
                                        />
                                    </svg>
                                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                                        <span className="text-2xl font-extrabold text-foreground">{result.ats_score}</span>
                                        <span className="text-xs text-muted-foreground font-medium">/100</span>
                                    </div>
                                </div>
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-widest text-primary mb-1">ATS Score</p>
                                    <p className="text-3xl font-extrabold text-foreground">{result.ats_score}<span className="text-lg text-muted-foreground font-normal">/100</span></p>
                                    <p className={`text-sm font-semibold mt-1 ${scoreLabel(result.ats_score).color}`}>
                                        {scoreLabel(result.ats_score).label}
                                    </p>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        Keyword match: <span className="font-semibold text-foreground">{result.keyword_match_percentage}%</span>
                                    </p>
                                </div>
                            </div>

                            {/* JD Match Score */}
                            {result.jd_match_score != null && (
                                <div className="bg-card border border-border rounded-[20px] p-8 shadow-md flex items-center gap-6">
                                    <div className="relative w-28 h-28 flex-shrink-0">
                                        <svg width="112" height="112" className="-rotate-90">
                                            <circle cx="56" cy="56" r="48" fill="none" stroke="currentColor"
                                                strokeWidth="10" className="text-border/20" />
                                            <circle cx="56" cy="56" r="48" fill="none"
                                                stroke={result.jd_match_score >= 70 ? "#10b981" : result.jd_match_score >= 50 ? "#3b82f6" : "#f59e0b"}
                                                strokeWidth="10" strokeLinecap="round"
                                                strokeDasharray={2 * Math.PI * 48}
                                                strokeDashoffset={2 * Math.PI * 48 * (1 - result.jd_match_score / 100)}
                                            />
                                        </svg>
                                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                                            <span className="text-2xl font-extrabold text-foreground">{result.jd_match_score}</span>
                                            <span className="text-xs text-muted-foreground font-medium">/100</span>
                                        </div>
                                    </div>
                                    <div>
                                        <p className="text-xs font-bold uppercase tracking-widest text-accent mb-1">JD Match Score</p>
                                        <p className="text-3xl font-extrabold text-foreground">{result.jd_match_score}<span className="text-lg text-muted-foreground font-normal">/100</span></p>
                                        <p className={`text-sm font-semibold mt-1 ${scoreLabel(result.jd_match_score).color}`}>
                                            {scoreLabel(result.jd_match_score).label}
                                        </p>
                                        <p className="text-xs text-muted-foreground mt-1">Role-specific alignment</p>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Four Metric Gauges */}
                        <div className="bg-card border border-border rounded-[20px] p-8 shadow-md">
                            <h2 className="text-lg font-bold text-foreground mb-6">Resume Quality Metrics</h2>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 justify-items-center">
                                {metrics.map((m) => (
                                    <CircularGauge key={m.label} score={m.score} label={m.label} animated />
                                ))}
                            </div>
                        </div>

                        {/* Strengths & Weaknesses */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="bg-card border border-border rounded-[20px] p-6 shadow-md">
                                <h3 className="font-bold text-foreground mb-4 flex items-center gap-2">
                                    <span className="w-6 h-6 bg-emerald-100 dark:bg-emerald-900/40 rounded-lg flex items-center justify-center">
                                        <svg className="w-3.5 h-3.5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                                        </svg>
                                    </span>
                                    Strengths
                                </h3>
                                <ul className="space-y-2.5">
                                    {result.strengths.map((s, i) => (
                                        <li key={i} className="flex items-start gap-2.5 text-sm text-foreground">
                                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-2 flex-shrink-0" />
                                            {s}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                            <div className="bg-card border border-border rounded-[20px] p-6 shadow-md">
                                <h3 className="font-bold text-foreground mb-4 flex items-center gap-2">
                                    <span className="w-6 h-6 bg-amber-100 dark:bg-amber-900/40 rounded-lg flex items-center justify-center">
                                        <svg className="w-3.5 h-3.5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                    </span>
                                    Areas to Improve
                                </h3>
                                <ul className="space-y-2.5">
                                    {result.weaknesses.map((w, i) => (
                                        <li key={i} className="flex items-start gap-2.5 text-sm text-foreground">
                                            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-2 flex-shrink-0" />
                                            {w}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        {/* Overall Feedback */}
                        <div className="bg-card border border-border rounded-[20px] p-6 shadow-md">
                            <h3 className="font-bold text-foreground mb-4 flex items-center gap-2">
                                <span className="w-6 h-6 bg-primary/10 rounded-lg flex items-center justify-center">
                                    <svg className="w-3.5 h-3.5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                </span>
                                Overall Feedback
                            </h3>
                            <p className="text-sm text-foreground leading-relaxed mb-5">{result.overall_feedback}</p>
                            <div className="border-t border-border/50 pt-4">
                                <h4 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">
                                    Recommendations
                                </h4>
                                <ul className="space-y-2">
                                    {result.recommendations.map((r, i) => (
                                        <li key={i} className="flex items-start gap-3 text-sm text-foreground">
                                            <span className="flex-shrink-0 w-5 h-5 bg-primary/10 text-primary rounded-md flex items-center justify-center text-xs font-bold">
                                                {i + 1}
                                            </span>
                                            {r}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex flex-wrap gap-3 justify-center pb-8">
                            <button
                                onClick={downloadSuggestions}
                                className="flex items-center gap-2 px-5 py-2.5 bg-card border border-border rounded-xl text-sm font-semibold text-foreground hover:bg-muted/50 hover:border-primary/30 transition-all"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                </svg>
                                Download Suggestions
                            </button>
                            <Link
                                href="/resume"
                                className="flex items-center gap-2 px-5 py-2.5 bg-card border border-border rounded-xl text-sm font-semibold text-foreground hover:bg-muted/50 hover:border-primary/30 transition-all"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                </svg>
                                Improve Resume
                            </Link>
                            <button
                                onClick={() => { setResult(null); setAnalysisMode(null); window.scrollTo({ top: 0, behavior: "smooth" }); }}
                                className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-primary to-accent text-primary-foreground rounded-xl text-sm font-semibold shadow-md hover:shadow-primary/30 hover:scale-[1.02] transition-all"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                </svg>
                                Re-analyze
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
