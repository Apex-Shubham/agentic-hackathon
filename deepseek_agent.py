"""
DeepSeek LLM Agent (via Groq)
Integrates with Groq-hosted DeepSeek/Mixtral for AI-powered trading decisions
"""
import json
import time
from typing import Dict

import requests
from config import (
    GROQ_API_KEY,
    GROQ_API_URL,
    GROQ_MODEL,
    GROQ_TEMPERATURE,
    GROQ_MAX_TOKENS,
    GROQ_TIMEOUT,
    SYSTEM_PROMPT,
    MAX_API_RETRIES,
    RETRY_BACKOFF_MULTIPLIER,
)


class DeepSeekAgent:
    """AI agent using Groq (DeepSeek/Mixtral) for trading decisions"""

    def __init__(self):
        self.api_key = GROQ_API_KEY
        self.api_url = GROQ_API_URL
        self.model = GROQ_MODEL
        self.decision_cache: Dict[str, Dict] = {}
        self.total_api_calls = 0
        self.failed_api_calls = 0

    # --------------------------------------------------------------------- #
    # PUBLIC API
    # --------------------------------------------------------------------- #
    def get_decision(
        self,
        market_data: Dict,
        portfolio: Dict,
        day_number: int,
        context_override: str | None = None,
    ) -> Dict:
        """
        Main entry point – returns a validated decision dict.
        If anything goes wrong we return a safe HOLD.
        """
        try:
            # Build the prompt
            if context_override:
                context = context_override
            else:
                from market_analyzer import get_analyzer

                analyzer = get_analyzer()
                context = analyzer.build_llm_context(market_data, portfolio, day_number)

            # Query Groq
            response_text = self._query_groq(context)

            # Parse & validate
            decision = self._parse_json_response(response_text)
            if self._validate_decision(decision):
                return decision
            else:
                return self._hold_decision("LLM response failed validation")

        except Exception as exc:  # pylint: disable=broad-except
            print(f"[DeepSeekAgent] Error getting decision: {exc}")
            self.failed_api_calls += 1
            return self._hold_decision(f"Exception: {exc}")

    # --------------------------------------------------------------------- #
    # PRIVATE HELPERS
    # --------------------------------------------------------------------- #
    def _query_groq(self, prompt: str) -> str:
        """Call Groq with exponential back-off."""
        self.total_api_calls += 1

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": GROQ_TEMPERATURE,
            "max_tokens": GROQ_MAX_TOKENS,
            "response_format": {"type": "json_object"},
        }

        for attempt in range(MAX_API_RETRIES):
            try:
                resp = requests.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=GROQ_TIMEOUT,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]

                # non-200 → log & retry
                err = f"Groq API error {resp.status_code}: {resp.text}"
                print(err)

            except requests.exceptions.Timeout:
                print(f"Groq timeout (attempt {attempt + 1}/{MAX_API_RETRIES})")
            except Exception as exc:  # pylint: disable=broad-except
                print(f"Groq request exception: {exc}")

            # back-off before next try
            if attempt < MAX_API_RETRIES - 1:
                wait = RETRY_BACKOFF_MULTIPLIER ** attempt
                print(f"Retrying in {wait}s...")
                time.sleep(wait)

        raise RuntimeError("Groq API max retries exceeded")

    # --------------------------------------------------------------------- #
    def _parse_json_response(self, text: str) -> Dict:
        """Robust JSON extraction – handles markdown fences, stray text, etc."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # try markdown code blocks
        for fence in ("```json", "```"):
            if fence in text:
                start = text.find(fence) + len(fence)
                end = text.find("```", start)
                if end != -1:
                    try:
                        return json.loads(text[start:end].strip())
                    except json.JSONDecodeError:
                        pass

        # last-ditch: grab first { … } block
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

        print(f"[DeepSeekAgent] Could not parse response: {text[:200]}")
        return self._hold_decision("Unparsable LLM output")

    # --------------------------------------------------------------------- #
    def _validate_decision(self, decision: Dict) -> bool:
        """Strict validation – mirrors SYSTEM_PROMPT constraints."""
        required = {
            "action",
            "confidence",
            "position_size_percent",
            "leverage",
            "entry_reason",
            "stop_loss_percent",
            "take_profit_percent",
            "urgency",
        }
        missing = required - decision.keys()
        if missing:
            print(f"Missing fields: {missing}")
            return False

        # action
        if decision["action"] not in {"LONG", "SHORT", "CLOSE", "HOLD"}:
            print(f"Invalid action: {decision['action']}")
            return False

        # numeric ranges
        try:
            conf = float(decision["confidence"])
            if not (0 <= conf <= 100):
                return False
        except Exception:
            return False

        try:
            size = float(decision["position_size_percent"])
            if not (0 <= size <= 10):
                return False
        except Exception:
            return False

        try:
            lev = int(decision["leverage"])
            if not (1 <= lev <= 5):
                return False
        except Exception:
            return False

        try:
            sl = float(decision["stop_loss_percent"])
            if not (2 <= sl <= 8):
                return False
        except Exception:
            return False

        try:
            tp = float(decision["take_profit_percent"])
            if not (5 <= tp <= 30):
                return False
        except Exception:
            return False

        if decision["urgency"] not in {"LOW", "MEDIUM", "HIGH"}:
            return False

        return True

    # --------------------------------------------------------------------- #
    def _hold_decision(self, reason: str) -> Dict:
        return {
            "action": "HOLD",
            "confidence": 0,
            "position_size_percent": 0,
            "leverage": 1,
            "entry_reason": reason,
            "stop_loss_percent": 3,
            "take_profit_percent": 10,
            "urgency": "LOW",
        }

    # --------------------------------------------------------------------- #
    def get_fallback_decision(self, market_data: Dict, portfolio: Dict) -> Dict:
        """Simple rule-based fallback when Groq is unreachable."""
        print("Using fallback decision logic")
        for pos in portfolio.get("positions", []):
            if pos.get("pnl_percent", 0) < -5:
                return {
                    "action": "CLOSE",
                    "confidence": 80,
                    "position_size_percent": 0,
                    "leverage": 1,
                    "entry_reason": "Fallback: closing losing position",
                    "stop_loss_percent": 3,
                    "take_profit_percent": 10,
                    "urgency": "HIGH",
                }
        return self._hold_decision("Fallback: API unavailable")

    # --------------------------------------------------------------------- #
    def get_stats(self) -> Dict:
        success = (
            (self.total_api_calls - self.failed_api_calls) / self.total_api_calls * 100
            if self.total_api_calls
            else 0
        )
        return {
            "total_api_calls": self.total_api_calls,
            "failed_api_calls": self.failed_api_calls,
            "success_rate_%": round(success, 2),
        }


# ------------------------------------------------------------------------- #
# Singleton accessor
# ------------------------------------------------------------------------- #
_agent_instance: DeepSeekAgent | None = None


def get_deepseek_agent() -> DeepSeekAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = DeepSeekAgent()
    return _agent_instance