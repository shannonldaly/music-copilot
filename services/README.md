# /services/ — External Integrations

All external service integrations live in this folder. Never inline
external service calls in agents or API endpoints.

## Convention

Each service gets its own file. The file exports a client or wrapper
that the rest of the codebase imports. Configuration (URLs, keys,
timeouts) comes from environment variables, never hardcoded.

## Current services

None yet. Planned:

- **MCP client** (Phase 4) — Ableton MCP integration via `ableton-mcp`
- **Supabase client** (Phase 5) — session storage, episodic logging
- **Stripe client** (Phase 5+) — payment processing

## Future projects

When reusing this pattern in new projects, add:
- Webhook handlers (with signature verification)
- Third-party API clients (with timeout and retry)
- Database connections
