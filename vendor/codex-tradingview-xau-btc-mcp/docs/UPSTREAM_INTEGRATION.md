# Upstream Integration Notes

This repository is a custom integration built from several public MIT-licensed TradingView MCP projects.

## Primary Base

- `ulianbass/tradingview-mcp`

Used as the main engine because it has the broadest Desktop/CDP tool surface, Codex compatibility, safety hardening, tests, and consent-gated trading tools.

## Borrowed Ideas

- `CryptoStig/tradingview-mcp-codex`: Windows/Codex setup flow.
- `iliaal/tradingview-mcp`: comparison point for rich TradingView MCP tooling.
- `karthikg-git/tradingview-claude-mcp`: packaging and Windows setup ideas.
- `alexandremaciel-ai/tradingview-mcp-self-learning`: journal, wiki and learning-loop ideas.
- `harshil1502/tradingview-mcp`: type-safety, input validation and doctor-style diagnostics as future direction.

## Custom Additions

- `session_start`
- `session_status`
- `session_scan_now`
- `session_pause`
- `session_resume`
- `session_stop`
- `risk_calculate_position`
- `trade_validate_plan`
- XAU/USD profile
- BTC/USD profile
- generic multi-asset profile
- Paper Trading guardrails
- human validation rules
- journal directory under the user home folder
