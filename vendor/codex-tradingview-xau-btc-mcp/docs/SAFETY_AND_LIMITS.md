# Safety and Limits

This project is an assistant and automation bridge. It does not guarantee profitability.

## Absolute Rules

- No trade without stop-loss.
- Risk must be calculated before entry.
- Default risk is 1% of capital.
- Paper Trading first.
- Live execution requires explicit human validation.
- R:R below 1:2 is refused unless a specific exception is approved.
- High-impact news can make a setup invalid even if technicals look good.

## Demo Autonomy

Paper Trading can be more autonomous, but only inside predefined limits:

- max 4 trades per day;
- optimal 2 to 3 trades per day;
- stop after daily drawdown of 3%;
- pause after 2 consecutive losses;
- every setup must be journaled.

## Live Mode

Live mode is semi-automatic:

- Codex may analyze;
- Codex may calculate;
- Codex may prepare;
- Codex may refuse;
- Codex must not execute without explicit human validation and consent-gated tool payloads.
