"""Token usage tracker for Gemini API calls."""
from typing import Dict
from config import logger


class TokenTracker:
    """Tracks Gemini API token usage globally and per session."""

    def __init__(self):
        self.global_input_tokens = 0
        self.global_output_tokens = 0
        self.global_total_tokens = 0
        self.api_calls = 0
        self.session_tokens: Dict[str, Dict[str, int]] = {}

    def track(self, response, session_id: str = None) -> Dict[str, int]:
        """Extract token usage from a Gemini response and track it."""
        usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        try:
            if hasattr(response, 'usage_metadata'):
                metadata = response.usage_metadata
                usage["input_tokens"] = getattr(metadata, 'prompt_token_count', 0) or 0
                usage["output_tokens"] = getattr(metadata, 'candidates_token_count', 0) or 0
                usage["total_tokens"] = getattr(metadata, 'total_token_count', 0) or 0

                self.global_input_tokens += usage["input_tokens"]
                self.global_output_tokens += usage["output_tokens"]
                self.global_total_tokens += usage["total_tokens"]
                self.api_calls += 1

                if session_id:
                    if session_id not in self.session_tokens:
                        self.session_tokens[session_id] = {
                            "input_tokens": 0, "output_tokens": 0,
                            "total_tokens": 0, "api_calls": 0
                        }
                    self.session_tokens[session_id]["input_tokens"] += usage["input_tokens"]
                    self.session_tokens[session_id]["output_tokens"] += usage["output_tokens"]
                    self.session_tokens[session_id]["total_tokens"] += usage["total_tokens"]
                    self.session_tokens[session_id]["api_calls"] += 1

                logger.debug(f"Token usage: {usage}")
        except Exception as e:
            logger.warning(f"Failed to extract token usage: {e}")

        return usage

    def get_global_stats(self) -> Dict[str, int]:
        """Get global token usage statistics."""
        return {
            "input_tokens": self.global_input_tokens,
            "output_tokens": self.global_output_tokens,
            "total_tokens": self.global_total_tokens,
            "api_calls": self.api_calls
        }

    def get_session_stats(self, session_id: str) -> Dict[str, int]:
        """Get token usage for a specific session."""
        return self.session_tokens.get(session_id, {
            "input_tokens": 0, "output_tokens": 0,
            "total_tokens": 0, "api_calls": 0
        })


# Global singleton
token_tracker = TokenTracker()
