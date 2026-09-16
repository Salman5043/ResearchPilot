import os
import time

from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq


MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-safeguard-20b")
DEFAULT_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "1400"))
MIN_REQUEST_INTERVAL = float(os.getenv("GROQ_MIN_REQUEST_INTERVAL", "0.5"))


llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model=MODEL,
    temperature=0,
    max_tokens=DEFAULT_MAX_TOKENS,
)

_last_request_at = 0.0


def _rate_limit_pause() -> None:
    global _last_request_at
    now = time.monotonic()
    wait = MIN_REQUEST_INTERVAL - (now - _last_request_at)
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.monotonic()


def _retry_delay(error_text: str, attempt: int) -> float:
    delay = min(2 ** attempt, 30.0)
    lower = error_text.lower()
    for marker in ("try again in ", "retry after "):
        if marker in lower:
            try:
                value = lower.split(marker, 1)[1].split("s", 1)[0].strip()
                delay = max(delay, min(float(value), 60.0))
            except (ValueError, IndexError):
                pass
            break
    return delay


def invoke_llm(prompt: str, retries: int = 4, max_tokens: int | None = None):
    """Invoke Groq with conservative output budgets and retry/backoff.

    The free/on-demand Groq tier can reject requests when prompt + completion
    demand exceeds the TPM budget. Callers should keep prompts compact and pass
    a task-specific max_tokens value.
    """
    requested_tokens = max_tokens or DEFAULT_MAX_TOKENS

    for attempt in range(retries):
        try:
            _rate_limit_pause()
            return llm.invoke(
                [HumanMessage(content=prompt)],
                max_tokens=requested_tokens,
            )
        except Exception as exc:
            error_text = str(exc)
            lower = error_text.lower()
            is_rate_limit = "429" in error_text or "rate_limit_exceeded" in lower or "tokens per minute" in lower
            if not is_rate_limit or attempt == retries - 1:
                raise

            delay = _retry_delay(error_text, attempt)
            print(f"Groq rate limit reached; retrying in {delay:.1f}s...")
            time.sleep(delay)

    raise RuntimeError("LLM request failed after retries.")
