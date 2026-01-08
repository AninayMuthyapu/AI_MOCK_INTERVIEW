"use client";

import { useState, FormEvent, ChangeEvent, useEffect } from "react";
import { useRouter } from "next/navigation";
import { API_BASE } from "../lib/api";

export default function ResumeUploadPage() {
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState<string>("");
  const [yearsOfExperience, setYearsOfExperience] = useState<number | ''>('');
  const [jobRole, setJobRole] = useState<string>("");
  const [companyName, setCompanyName] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isPreviewLoading, setIsPreviewLoading] = useState<boolean>(false);
  const [planPreview, setPlanPreview] = useState<
    | {
        inferred_role: string;
        inferred_years_of_experience: number;
        inferred_company: string;
        rounds: { title: string; type: string; question_count: number; estimated_minutes: number }[];
        total_questions: number;
        total_estimated_minutes: number;
        is_ai_generated: boolean;
        generation_source: string;
      }
    | null
  >(null);
  const [atsReview, setAtsReview] = useState<{
    ats_score: number;
    strengths: string[];
    weaknesses: string[];
    recommendations: string[];
    keyword_match_percentage: number;
    overall_feedback: string;
  } | null>(null);
  const [isAtsLoading, setIsAtsLoading] = useState(false);
  const [showAtsReview, setShowAtsReview] = useState(false);
  const router = useRouter();

  // Load saved form data on component mount
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem('interviewData');
      if (saved) {
        const data = JSON.parse(saved);
        setJobRole(data.jobRole || '');
        setCompanyName(data.companyName || '');
        setYearsOfExperience(data.yearsOfExperience || '');
        setJobDescription(data.jobDescription || '');
      }
    } catch (e) {
      // Ignore parsing errors
    }
  }, []);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      const file = event.target.files[0];
      if (
        file.type !== "application/pdf" &&
        file.type !== "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      ) {
        setError("Please upload a PDF or DOCX file.");
        setResumeFile(null);
      } else {
        setResumeFile(file);
        setError(null);
      }
    }
  };

  const handlePreviewPlan = async () => {
    setError(null);
    if (!jobRole || yearsOfExperience === '' || !companyName) {
      setError("Please provide Role, Years of Experience, and Company to preview the plan.");
      return;
    }

    setIsPreviewLoading(true);
    setPlanPreview(null);
    const formData = new FormData();
    if (resumeFile) formData.append("resumeFile", resumeFile);
    if (jobDescription) formData.append("jobDescription", jobDescription);
    formData.append("yearsOfExperience", String(yearsOfExperience || 0));
    formData.append("jobRole", jobRole);
    formData.append("companyName", companyName);

    try {
      const res = await fetch(`${API_BASE}/api/preview-plan`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to preview plan.');
      }
      const data = await res.json();
      setPlanPreview(data);
    } catch (e: unknown) {
      const message =
        e instanceof Error
          ? e.message
          : typeof e === "string"
            ? e
            : "Failed to preview plan.";
      setError(message);
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const handleATSReview = async () => {
    setError(null);
    if (!resumeFile || !jobDescription.trim()) {
      setError("Please upload a resume and provide job description for ATS review.");
      return;
    }

    setIsAtsLoading(true);
    setAtsReview(null);
    const formData = new FormData();
    formData.append("resumeFile", resumeFile);
    formData.append("jobDescription", jobDescription);

    try {
      const res = await fetch(`${API_BASE}/api/ats-review`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to analyze resume.');
      }
      const data = await res.json();
      setAtsReview(data);
      setShowAtsReview(true);
    } catch (e: unknown) {
      const message =
        e instanceof Error
          ? e.message
          : typeof e === "string"
            ? e
            : "Failed to analyze resume.";
      setError(message);
    } finally {
      setIsAtsLoading(false);
    }
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);

    if (yearsOfExperience === '' || !jobRole || !companyName) {
      setError("Please provide Role, Years of Experience, and Company.");
      return;
    }

    setIsSubmitting(true);

    const formData = new FormData();
    if (resumeFile) formData.append("resumeFile", resumeFile);
    if (jobDescription) formData.append("jobDescription", jobDescription);
    formData.append("yearsOfExperience", String(yearsOfExperience));
    formData.append("jobRole", jobRole);
    formData.append("companyName", companyName);

    try {
      const response = await fetch(`${API_BASE}/api/start-interview`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to start interview session.');
      }

      const data = await response.json();
      console.log("Backend response:", data);
      // Persist session payload for Interview page to pick up immediately
      try {
        sessionStorage.setItem('interviewSession', JSON.stringify(data));
      } catch {}
      
      // Store form data in sessionStorage to avoid re-filling
      sessionStorage.setItem('interviewData', JSON.stringify({
        jobRole,
        companyName,
        yearsOfExperience,
        jobDescription
      }));
      
      router.push("/Interview");

    } catch (err: unknown) {
      console.error(err);
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(`Error: ${message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative min-h-screen p-4 flex items-center justify-center">
      <div className="animated-grid" />
      <div className="relative w-full max-w-2xl p-8 rounded-lg glass-effect neon-border">
        <h1 className="page-title text-center mb-6 text-white">Prepare for Your Interview</h1>
        <p className="text-white/80 text-center mb-8">Upload your resume and the job details to get started.</p>

        <form className="space-y-6" onSubmit={handleSubmit}>
          {/* Resume Upload Section */}
          <div>
            <label htmlFor="resume" className="block text-lg font-medium text-white mb-2">
              1. Upload Your Resume (PDF or DOCX)
            </label>
            <div
              className={`flex items-center justify-center w-full h-32 border-2 border-dashed rounded-lg ${
                resumeFile ? "border-green-500" : "border-gray-300"
              }`}
            >
              <input
                id="resume"
                type="file"
                className="hidden"
                onChange={handleFileChange}
                accept=".pdf,.docx"
              />
              <label
                htmlFor="resume"
                className="flex flex-col items-center justify-center w-full h-full text-center text-white/80 cursor-pointer"
              >
                {resumeFile ? (
                  <p className="text-green-300 font-medium">{resumeFile.name} uploaded.</p>
                ) : (
                  <p>Drag and drop or click to upload</p>
                )}
              </label>
            </div>
          </div>

          {/* Job Description Section */}
          <div>
            <label htmlFor="jobDescription" className="block text-lg font-medium text-white mb-2">
              2. Paste Job Description
            </label>
            <textarea
              id="jobDescription"
              rows={8}
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              className="w-full p-4 border rounded-lg resize-y focus:outline-none focus:ring-2 focus:ring-blue-500 text-white placeholder-white/60 bg-white/5 border-white/20"
              placeholder="Paste the job description here..."
            />
          </div>

          {/* Job Role, Years of Experience, Company Name */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label htmlFor="companyName" className="block text-lg font-medium text-white mb-2">
                3. Company Name
              </label>
              <select
                id="companyName"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                className="w-full p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white bg-white/5 border-white/20"
              >
                <option value="">Select a company</option>
                <option>Amazon</option>
                <option>Google</option>
                <option>Microsoft</option>
                <option>Meta</option>
                <option>Apple</option>
                <option>Netflix</option>
                <option>Uber</option>
                <option>Airbnb</option>
                <option>Stripe</option>
                <option>NVIDIA</option>
                <option>OpenAI</option>
                <option>Adobe</option>
                <option>Other</option>
              </select>
            </div>
            <div>
              <label htmlFor="jobRole" className="block text-lg font-medium text-white mb-2">
                4. Your Job Role
              </label>
              <select
                id="jobRole"
                value={jobRole}
                onChange={(e) => setJobRole(e.target.value)}
                className="w-full p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white bg-white/5 border-white/20"
              >
                <option value="">Select a role</option>
                <option>Software Engineer</option>
                <option>SDE 1</option>
                <option>SDE 2</option>
                <option>Senior SDE</option>
                <option>Frontend Engineer</option>
                <option>Backend Engineer</option>
                <option>Full Stack Engineer</option>
                <option>Data Scientist</option>
                <option>ML Engineer</option>
                <option>DevOps Engineer</option>
                <option>Product Manager</option>
                <option>Other</option>
              </select>
            </div>
            <div>
              <label htmlFor="yearsOfExperience" className="block text-lg font-medium text-white mb-2">
                5. Years of Experience
              </label>
              <select
                id="yearsOfExperience"
                value={yearsOfExperience === '' ? '' : String(yearsOfExperience)}
                onChange={(e) => setYearsOfExperience(e.target.value === '' ? '' : Number(e.target.value))}
                className="w-full p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white bg-white/5 border-white/20"
              >
                <option value="">Select years</option>
                <option value="0">0</option>
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
                <option value="4">4</option>
                <option value="5">5</option>
                <option value="6">6</option>
                <option value="7">7</option>
                <option value="8">8</option>
                <option value="10">10</option>
                <option value="12">12</option>
              </select>
            </div>
          </div>

          {error && <p className="text-red-500 text-sm text-center">{error}</p>}

          {/* ATS Review Section */}
          <div className="border-t border-white/20 pt-6">
            <h3 className="card-title mb-3 text-white">📊 Resume Analysis (Optional)</h3>
            <p className="text-sm text-white/80 mb-4">
              Get an ATS (Applicant Tracking System) score and detailed feedback on how well your resume matches the job description.
            </p>
            <button
              type="button"
              onClick={handleATSReview}
              className={`w-full py-3 rounded-lg text-white font-semibold transition-colors duration-300 ${
                isAtsLoading ? "bg-gray-400 cursor-not-allowed" : "bg-green-600 hover:bg-green-700"
              }`}
              disabled={isAtsLoading || !resumeFile || !jobDescription.trim()}
            >
              {isAtsLoading ? "Analyzing Resume..." : "🔍 Get ATS Score & Feedback"}
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <button
              type="button"
              onClick={handlePreviewPlan}
              className={`w-full py-3 rounded-lg text-white font-semibold transition-colors duration-300 ${
                isPreviewLoading ? "bg-gray-400 cursor-not-allowed" : "bg-indigo-600 hover:bg-indigo-700"
              }`}
              disabled={isPreviewLoading}
            >
              {isPreviewLoading ? "Generating Plan..." : "Preview Interview Plan"}
            </button>
            <button
              type="submit"
              className={`w-full py-3 rounded-lg text-white font-semibold transition-colors duration-300 ${
                isSubmitting ? "bg-gray-400 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-700"
              }`}
              disabled={isSubmitting}
            >
              {isSubmitting ? "Starting..." : "🚀 Start Interview"}
            </button>
          </div>
        </form>

        {/* ATS Review Results */}
        {showAtsReview && atsReview && (
          <div className="mt-8 p-6 bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-lg">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-800">📊 ATS Resume Analysis</h2>
              <button 
                onClick={() => setShowAtsReview(false)}
                className="text-gray-500 hover:text-gray-700 text-xl"
              >
                ×
              </button>
            </div>
            
            {/* Score Section */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div className="p-4 bg-white rounded-lg border">
                <h3 className="font-semibold text-gray-700 mb-2">ATS Score</h3>
                <div className="flex items-center gap-3">
                  <div className={`text-3xl font-bold ${
                    atsReview.ats_score >= 80 ? 'text-green-600' : 
                    atsReview.ats_score >= 60 ? 'text-yellow-600' : 'text-red-600'
                  }`}>
                    {atsReview.ats_score}
                  </div>
                  <div className="text-gray-500">/ 100</div>
                </div>
              </div>
              <div className="p-4 bg-white rounded-lg border">
                <h3 className="font-semibold text-gray-700 mb-2">Keyword Match</h3>
                <div className="flex items-center gap-3">
                  <div className={`text-3xl font-bold ${
                    atsReview.keyword_match_percentage >= 70 ? 'text-green-600' : 
                    atsReview.keyword_match_percentage >= 50 ? 'text-yellow-600' : 'text-red-600'
                  }`}>
                    {atsReview.keyword_match_percentage}%
                  </div>
                </div>
              </div>
            </div>

            {/* Feedback Sections */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div className="p-4 bg-white rounded-lg border">
                <h3 className="font-semibold text-green-700 mb-2">✅ Strengths</h3>
                <ul className="text-sm text-gray-700 space-y-1">
                  {atsReview.strengths.map((strength, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-green-500 mt-1">•</span>
                      <span>{strength}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="p-4 bg-white rounded-lg border">
                <h3 className="font-semibold text-red-700 mb-2">⚠️ Areas to Improve</h3>
                <ul className="text-sm text-gray-700 space-y-1">
                  {atsReview.weaknesses.map((weakness, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-red-500 mt-1">•</span>
                      <span>{weakness}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="p-4 bg-white rounded-lg border">
                <h3 className="font-semibold text-blue-700 mb-2">💡 Recommendations</h3>
                <ul className="text-sm text-gray-700 space-y-1">
                  {atsReview.recommendations.map((rec, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-blue-500 mt-1">•</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Overall Feedback */}
            <div className="p-4 bg-white rounded-lg border">
              <h3 className="font-semibold text-gray-700 mb-2">📝 Overall Feedback</h3>
              <p className="text-gray-700 text-sm leading-relaxed">{atsReview.overall_feedback}</p>
            </div>
          </div>
        )}

        {planPreview && (
          <div className="mt-8 p-6 rounded-lg border border-white/20 bg-white/5">
            <h2 className="section-title text-white">Interview Plan Preview</h2>
            <p className="mt-2 text-white/90">
              <span className="font-medium">Role:</span> {planPreview.inferred_role || '—'} | {" "}
              <span className="font-medium">Experience:</span> {planPreview.inferred_years_of_experience} yrs | {" "}
              <span className="font-medium">Company:</span> {planPreview.inferred_company || '—'}
            </p>
            
            {/* Generation Source Indicator */}
            <div className="mt-3 p-3 rounded-lg border border-white/20 bg-white/5">
              <div className="flex items-center gap-2 text-white">
                {planPreview.is_ai_generated ? (
                  <>
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm font-medium text-green-700">AI Generated</span>
                  </>
                ) : (
                  <>
                    <div className="w-2 h-2 bg-orange-500 rounded-full"></div>
                    <span className="text-sm font-medium text-orange-700">Fallback Plan</span>
                  </>
                )}
              </div>
              <p className="text-xs text-gray-600 mt-1">{planPreview.generation_source}</p>
            </div>

            <div className="mt-4 space-y-3">
              {planPreview.rounds.map((r, idx) => (
                <div key={idx} className="p-4 rounded-lg border border-white/20 bg-white/5 flex items-center justify-between">
                  <div>
                    <p className="font-medium text-white">{r.title} <span className="ml-2 text-xs uppercase tracking-wide text-white/70">{r.type}</span></p>
                    <p className="text-white/80 text-sm">Questions: {r.question_count}</p>
                  </div>
                  <p className="text-white font-medium">~ {r.estimated_minutes} min</p>
                </div>
              ))}
            </div>
            <div className="mt-4 flex items-center justify-between text-gray-800">
              <p className="font-medium text-white">Total Questions: {planPreview.total_questions}</p>
              <p className="font-semibold text-white">Estimated Duration: ~ {planPreview.total_estimated_minutes} minutes</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}