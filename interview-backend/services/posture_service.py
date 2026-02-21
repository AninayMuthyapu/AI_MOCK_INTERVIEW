"""
Posture Analysis Service — runs the BehaviorAnalysisEngine in a background
daemon thread with its own camera capture.  Exposes start / stop / report
per interview session.
"""
from __future__ import annotations

import os
import sys
import threading
import time
import importlib
from typing import Any, Dict, Optional

from config import logger, POSTURE_ENGINE_PATH

# ---------------------------------------------------------------------------
# Import the engine carefully.
#
# The engine's own `config.py` (with CAMERA_INDEX, thresholds, etc.) clashes
# with the backend's `config.py`.  We temporarily swap the sys.modules entry
# so the engine picks up its own config during import, then restore ours.
# ---------------------------------------------------------------------------
ENGINE_AVAILABLE = False
_EngineClass: Any = None  # will hold BehaviorAnalysisEngine class if available

try:
    # Save and remove backend config from sys.modules
    _backend_config = sys.modules.pop("config", None)

    # Make sure the engine path is first so it finds *its* config
    sys.path.insert(0, POSTURE_ENGINE_PATH)

    from engine import BehaviorAnalysisEngine  # type: ignore[import]
    _EngineClass = BehaviorAnalysisEngine
    ENGINE_AVAILABLE = True
    logger.info("BehaviorAnalysisEngine imported for posture service")
except Exception as e:
    ENGINE_AVAILABLE = False
    logger.warning(f"Posture engine unavailable: {e}")
finally:
    # Restore backend config module no matter what
    if "_backend_config" in dir() and _backend_config is not None:
        sys.modules["config"] = _backend_config  # type: ignore[possibly-undefined]
    # Remove the engine path we inserted (keep sys.path clean)
    if POSTURE_ENGINE_PATH in sys.path:
        sys.path.remove(POSTURE_ENGINE_PATH)


class _SessionEntry:
    """Internal bookkeeping for one background session."""
    __slots__ = ("thread", "engine", "stop_event", "report")

    def __init__(self, thread: threading.Thread, engine: Any, stop_event: threading.Event):
        self.thread = thread
        self.engine = engine
        self.stop_event = stop_event
        self.report: Optional[Dict[str, Any]] = None


class PostureService:
    """Manages background posture-analysis sessions, one per interview."""

    def __init__(self):
        self._sessions: Dict[str, _SessionEntry] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def start_background(self, session_id: str) -> bool:
        """
        Spawn a daemon thread that starts a session and analyzes frames
        sent from the browser (via /api/analyze-behavior).
        Does NOT open the physical camera — the browser streams frames directly.
        """
        if not ENGINE_AVAILABLE or _EngineClass is None:
            logger.warning("Posture engine not available — skipping background analysis")
            return False

        with self._lock:
            if session_id in self._sessions:
                logger.warning(f"Posture session {session_id} already running")
                return False

            stop_event = threading.Event()

            try:
                # use_camera=False: do NOT open /dev/video0 — browser sends frames
                engine = _EngineClass(use_camera=False)
            except Exception as e:
                logger.error(f"Failed to create posture engine: {e}")
                return False

            t = threading.Thread(
                target=self._capture_loop,
                args=(session_id, engine, stop_event),
                daemon=True,
                name=f"posture-{session_id[:12]}",
            )

            entry = _SessionEntry(thread=t, engine=engine, stop_event=stop_event)
            self._sessions[session_id] = entry

        t.start()
        logger.info(f"Posture background analysis started for session {session_id}")
        return True

    def stop_background(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Signal the capture thread to stop, wait for it, and return the
        final posture report dict.
        """
        with self._lock:
            entry = self._sessions.get(session_id)
            if entry is None:
                return None

        entry.stop_event.set()
        entry.thread.join(timeout=5.0)

        report = getattr(entry.thread, '_posture_report', None)
        if report is None:
            try:
                report = entry.engine.end_session()
            except Exception:
                report = None

        with self._lock:
            self._sessions.pop(session_id, None)

        logger.info(f"Posture analysis stopped for session {session_id}, report={'yes' if report else 'no'}")
        return report

    def get_report(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return a cached report if the session already ended."""
        with self._lock:
            entry = self._sessions.get(session_id)
            if entry and entry.report:
                return entry.report
        return None

    def is_running(self, session_id: str) -> bool:
        with self._lock:
            entry = self._sessions.get(session_id)
            return entry is not None and entry.thread.is_alive()

    # ------------------------------------------------------------------ #
    # Background thread target
    # ------------------------------------------------------------------ #
    @staticmethod
    def _capture_loop(session_id: str, engine: Any,
                      stop_event: threading.Event):
        """
        Runs in a daemon thread. Since use_camera=False, we do NOT capture
        frames here — the browser sends frames via /api/analyze-behavior.
        We just start the session and wait for the stop signal.
        """
        try:
            engine.start_session()
            logger.info(f"[posture-{session_id[:8]}] Session started (browser-fed mode)")

            # Wait until interview ends
            stop_event.wait()

            report = engine.end_session()
            threading.current_thread()._posture_report = report  # type: ignore[attr-defined]

        except Exception as e:
            logger.error(f"[posture-{session_id[:8]}] Session error: {e}")
        finally:
            try:
                engine.close()
            except Exception:
                pass
            logger.info(f"[posture-{session_id[:8]}] Session exited")


# Global singleton
posture_service = PostureService()
