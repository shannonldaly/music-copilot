"""
Structured logging for agent calls.

Provides @log_agent_call decorator that logs:
    agent_name, method, duration_ms, success, input_summary, output_summary

These field names map to a Postgres table in Phase 5.

Usage:
    from utils.logging import log_agent_call

    class MyAgent:
        @log_agent_call
        def my_method(self, data):
            ...

    # For standalone functions:
    @log_agent_call
    def generate_something_local(data):
        ...

Console output format:
    [TheoryValidator.validate_progression] 3ms success=True input="..." output="..."
"""

import functools
import logging
import time


# =============================================================================
# Formatter — renders structured fields inline in console
# =============================================================================

class AgentCallFormatter(logging.Formatter):
    """Formats agent_call log records with structured fields visible."""

    def format(self, record):
        agent = getattr(record, "agent_name", "?")
        method = getattr(record, "method", "?")
        duration = getattr(record, "duration_ms", 0)
        success = getattr(record, "success", True)
        inp = getattr(record, "input_summary", "")
        out = getattr(record, "output_summary", "")

        status = "success" if success else "FAILED"
        return f"[{agent}.{method}] {duration}ms {status} input=\"{inp}\" output=\"{out}\""


# =============================================================================
# Configure the agent_calls logger with the custom formatter
# =============================================================================

_agent_logger = logging.getLogger("agent_calls")
_agent_logger.setLevel(logging.INFO)

# Only add handler if none exist (prevent duplicates on reload)
if not _agent_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(AgentCallFormatter())
    _agent_logger.addHandler(_handler)
    _agent_logger.propagate = False  # Don't double-log via root logger


# =============================================================================
# Summarize helper
# =============================================================================

def _summarize(value, max_len=200):
    """Produce a short summary of a value for logging."""
    if value is None:
        return "None"
    if isinstance(value, str):
        if len(value) > max_len:
            return value[:max_len] + "..."
        return value
    if isinstance(value, dict):
        keys = list(value.keys())[:6]
        return f"dict({len(value)} keys: {keys})"
    if isinstance(value, list):
        return f"list({len(value)} items)"
    if isinstance(value, tuple):
        if len(value) <= 3:
            return f"tuple({', '.join(_summarize(v, 50) for v in value)})"
        return f"tuple({len(value)} items)"
    if isinstance(value, bool):
        return str(value)
    if hasattr(value, "passed"):
        return f"{type(value).__name__}(passed={value.passed})"
    if hasattr(value, "to_dict"):
        return f"{type(value).__name__}"
    return f"{type(value).__name__}"


# =============================================================================
# Decorator
# =============================================================================

def log_agent_call(func):
    """
    Decorator that logs structured entry/exit for agent methods.

    Logs to the 'agent_calls' logger with fields:
        agent_name, method, duration_ms, success, input_summary, output_summary

    Works on both instance methods (extracts class name from self) and
    standalone functions (uses module name).

    Does NOT replace domain-specific manual logger.info() calls.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Extract agent name
        if args and hasattr(args[0], "__class__") and hasattr(args[0].__class__, func.__name__):
            agent_name = args[0].__class__.__name__
            summarize_args = args[1:]  # Skip self
        else:
            agent_name = func.__module__.split(".")[-1] if func.__module__ else "unknown"
            summarize_args = args

        method = func.__name__

        # Build input summary
        input_parts = []
        for a in summarize_args:
            input_parts.append(_summarize(a, 80))
        for k, v in kwargs.items():
            input_parts.append(f"{k}={_summarize(v, 80)}")
        input_summary = ", ".join(input_parts)[:200]

        start = time.perf_counter()
        success = True
        output_summary = ""

        try:
            result = func(*args, **kwargs)
            output_summary = _summarize(result)[:200]
            return result
        except Exception as e:
            success = False
            output_summary = f"ERROR: {type(e).__name__}: {str(e)[:150]}"
            raise
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            _agent_logger.info(
                "agent_call",
                extra={
                    "agent_name": agent_name,
                    "method": method,
                    "duration_ms": duration_ms,
                    "success": success,
                    "input_summary": input_summary,
                    "output_summary": output_summary,
                },
            )

    return wrapper
