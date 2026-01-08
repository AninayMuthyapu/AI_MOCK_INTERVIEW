"use client";
import React, { useEffect, useMemo, useState } from "react";
import { useVoice } from "@/contexts/VoiceContext";
import { API_BASE } from "@/app/lib/api";

export default function VoiceToggle() {
  const { settings, setEnabled, setVoice } = useVoice();
  const [voices, setVoices] = useState<Record<string, string>>({
    rachel: "21m00Tcm4TlvDq8ikWAM",
    domi: "AZnzlk1XvdvUeBnXmlld",
    bella: "EXAVITQu4vr4xnSDxMaL",
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    fetch(`${API_BASE}/api/voices`)
      .then((r) => (r.ok ? r.json() : {}))
      .then((data: unknown) => {
        if (mounted && data && typeof data === "object" && !Array.isArray(data)) {
          setVoices(data as Record<string, string>);
        }
      })
      .catch(() => {})
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
  }, []);

  const voiceOptions = useMemo(() => Object.keys(voices), [voices]);

  return (
    <div className="flex items-center gap-3 text-sm">
      <label className="flex items-center gap-2 cursor-pointer select-none">
        <input
          type="checkbox"
          className="h-4 w-4"
          checked={settings.enabled}
          onChange={(e) => setEnabled(e.target.checked)}
        />
        <span className="font-medium">Voice</span>
      </label>

      <select
        className="border rounded px-2 py-1 bg-white disabled:bg-gray-100 disabled:text-gray-400"
        value={settings.voice}
        disabled={!settings.enabled}
        onChange={(e) => setVoice(e.target.value)}
        title={loading ? "Loading voices..." : "Select voice"}
      >
        {voiceOptions.map((v) => (
          <option key={v} value={v}>
            {v}
          </option>
        ))}
      </select>
    </div>
  );
}
