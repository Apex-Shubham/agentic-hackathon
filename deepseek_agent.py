"""
LLM Agent (via OpenRouter)
Integrates with OpenRouter for AI-powered trading decisions
"""
import json
import os
import time
from typing import Dict

import requests
from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_API_URL,
    OPENROUTER_MODEL,
    OPENROUTER_TEMPERATURE,
    OPENROUTER_MAX_TOKENS,
    OPENROUTER_TIMEOUT,
    SYSTEM_PROMPT,
    MAX_API_RETRIES,
    RETRY_BACKOFF_MULTIPLIER,
)


class DeepSeekAgent:
    """AI agent using OpenRouter for trading decisions"""

    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        self.api_url = OPENROUTER_API_URL
        self.model = OPENROUTER_MODEL
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

            # Query OpenRouter
            response_text = self._query_openrouter(context)

            # Parse & normalize, then validate
            decision = self._parse_json_response(response_text)
            decision = self._normalize_decision(decision)
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
    def _query_openrouter(self, prompt: str) -> str:
        """Call OpenRouter with exponential back-off."""
        self.total_api_calls += 1

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": OPENROUTER_TEMPERATURE,
            "max_tokens": OPENROUTER_MAX_TOKENS,
            "response_format": {"type": "json_object"},
        }

        for attempt in range(MAX_API_RETRIES):
            try:
                resp = requests.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        # Optional but recommended per OpenRouter docs
                        "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "http://localhost"),
                        "X-Title": os.getenv("OPENROUTER_TITLE", "AI Trading Bot"),
                    },
                    json=payload,
                    timeout=OPENROUTER_TIMEOUT,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]

                # non-200 → log & retry
                err = f"OpenRouter API error {resp.status_code}: {resp.text}"
                print(err)

            except requests.exceptions.Timeout:
                print(f"OpenRouter timeout (attempt {attempt + 1}/{MAX_API_RETRIES})")
            except Exception as exc:  # pylint: disable=broad-except
                print(f"OpenRouter request exception: {exc}")

            # back-off before next try
            if attempt < MAX_API_RETRIES - 1:
                wait = RETRY_BACKOFF_MULTIPLIER ** attempt
                print(f"Retrying in {wait}s...")
                time.sleep(wait)

        raise RuntimeError("OpenRouter API max retries exceeded")

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
    def _normalize_decision(self, decision: Dict) -> Dict:
        """Fill missing fields with safe defaults and map alternate keys."""
        if not isinstance(decision, dict):
            return self._hold_decision("Invalid decision format")

        # Map alternate keys
        if "position_size_percent" not in decision:
            if "position_size" in decision:
                decision["position_size_percent"] = decision.get("position_size")
            elif "size_percent" in decision:
                decision["position_size_percent"] = decision.get("size_percent")

        # Safe defaults
        action = decision.get("action", "HOLD")
        try:
            confidence = float(decision.get("confidence", 0))
        except Exception:
            confidence = 0
        # If size missing, derive 1-10 from confidence
        if decision.get("position_size_percent") in (None, "", []):
            derived_size = max(1, min(10, int(confidence // 10)))
            decision["position_size_percent"] = derived_size

        decision.setdefault("leverage", 2)
        decision.setdefault("entry_reason", "Auto-normalized")
        decision.setdefault("stop_loss_percent", 4)
        decision.setdefault("take_profit_percent", 12)
        decision.setdefault("urgency", "LOW")
        decision["action"] = action if action in {"LONG", "SHORT", "CLOSE", "HOLD"} else "HOLD"

        # Clamp ranges
        decision["confidence"] = max(0, min(100, float(confidence)))
        try:
            decision["position_size_percent"] = max(0, min(10, float(decision["position_size_percent"])))
        except Exception:
            decision["position_size_percent"] = 1
        try:
            decision["leverage"] = max(1, min(5, int(decision["leverage"])))
        except Exception:
            decision["leverage"] = 2
        try:
            decision["stop_loss_percent"] = max(2, min(8, float(decision["stop_loss_percent"])))
        except Exception:
            decision["stop_loss_percent"] = 4
        try:
            decision["take_profit_percent"] = max(5, min(30, float(decision["take_profit_percent"])))
        except Exception:
            decision["take_profit_percent"] = 12

        return decision

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
        """Simple rule-based fallback when OpenRouter is unreachable."""
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