"""
Token tracking and API cost logging.

Every API call is logged with:
- Agent name
- Model used
- Input/output tokens
- Timestamp
- Cost estimate

This enables cost monitoring and optimization.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

# Approximate costs per 1M tokens (as of 2024)
# Update these as pricing changes
MODEL_COSTS = {
    # Claude 3.5 family
    'claude-3-5-sonnet-20241022': {'input': 3.00, 'output': 15.00},
    'claude-sonnet-4-5-20250929': {'input': 3.00, 'output': 15.00},
    'claude-3-5-haiku-20241022': {'input': 0.80, 'output': 4.00},
    'claude-haiku-4-5-20251001': {'input': 0.80, 'output': 4.00},

    # Claude 4 family
    'claude-opus-4-5-20251101': {'input': 15.00, 'output': 75.00},

    # Aliases
    'sonnet': {'input': 3.00, 'output': 15.00},
    'haiku': {'input': 0.80, 'output': 4.00},
    'opus': {'input': 15.00, 'output': 75.00},
}

# Default budget per request (in tokens)
DEFAULT_REQUEST_BUDGET = 4000


@dataclass
class APICallLog:
    """Single API call log entry."""
    timestamp: str
    agent: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    request_type: str = ""
    notes: str = ""


@dataclass
class TokenTracker:
    """
    Track token usage across a session.

    Usage:
        tracker = TokenTracker()
        tracker.log_call("orchestrator", "haiku", 150, 50)
        tracker.log_call("theory_agent", "sonnet", 800, 400)
        print(tracker.summary())
    """
    logs: List[APICallLog] = field(default_factory=list)
    request_budget: int = DEFAULT_REQUEST_BUDGET
    session_id: str = ""
    log_file: Optional[Path] = None

    def __post_init__(self):
        if not self.session_id:
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def log_call(
        self,
        agent: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        request_type: str = "",
        notes: str = ""
    ) -> APICallLog:
        """Log an API call."""
        cost = self._calculate_cost(model, input_tokens, output_tokens)

        entry = APICallLog(
            timestamp=datetime.now().isoformat(),
            agent=agent,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            request_type=request_type,
            notes=notes
        )

        self.logs.append(entry)

        # Persist to file if configured
        if self.log_file:
            self._append_to_file(entry)

        return entry

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for an API call."""
        if model not in MODEL_COSTS:
            # Default to sonnet pricing if unknown
            model = 'sonnet'

        costs = MODEL_COSTS[model]
        input_cost = (input_tokens / 1_000_000) * costs['input']
        output_cost = (output_tokens / 1_000_000) * costs['output']
        return round(input_cost + output_cost, 6)

    def _append_to_file(self, entry: APICallLog):
        """Append log entry to file."""
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(asdict(entry)) + '\n')

    @property
    def total_input_tokens(self) -> int:
        return sum(log.input_tokens for log in self.logs)

    @property
    def total_output_tokens(self) -> int:
        return sum(log.output_tokens for log in self.logs)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def total_cost(self) -> float:
        return round(sum(log.cost_usd for log in self.logs), 6)

    @property
    def is_over_budget(self) -> bool:
        return self.total_tokens > self.request_budget

    @property
    def remaining_budget(self) -> int:
        return max(0, self.request_budget - self.total_tokens)

    def summary(self) -> Dict:
        """Get a summary of token usage."""
        by_agent = {}
        for log in self.logs:
            if log.agent not in by_agent:
                by_agent[log.agent] = {'calls': 0, 'tokens': 0, 'cost': 0.0}
            by_agent[log.agent]['calls'] += 1
            by_agent[log.agent]['tokens'] += log.input_tokens + log.output_tokens
            by_agent[log.agent]['cost'] += log.cost_usd

        return {
            'session_id': self.session_id,
            'total_calls': len(self.logs),
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_tokens': self.total_tokens,
            'total_cost_usd': self.total_cost,
            'budget': self.request_budget,
            'remaining_budget': self.remaining_budget,
            'over_budget': self.is_over_budget,
            'by_agent': by_agent
        }

    def reset_for_request(self):
        """Reset tracking for a new user request."""
        self.logs = []


def log_api_call(
    tracker: Optional[TokenTracker],
    agent: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    **kwargs
) -> Optional[APICallLog]:
    """
    Convenience function to log an API call.

    Returns the log entry, or None if no tracker provided.
    """
    if tracker:
        return tracker.log_call(agent, model, input_tokens, output_tokens, **kwargs)
    return None
