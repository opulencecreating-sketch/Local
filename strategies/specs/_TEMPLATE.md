# <Strategy name>

| Field | Value |
|---|---|
| Source | TradingView / Stonehill Forex / QuantConnect / Quantpedia — link or file name |
| Original type | Complete strategy / indicator only (trade rules added) |
| Assets | e.g. BTC-USD, ETH-USD |
| Timeframes | e.g. 4H, 1D |
| Implementation | `strategies/<file>.py` |

## Entry rules
- Long: …
- Short: … (or "none")

## Exit rules
- …

## Stop loss
- e.g. 1.5 × ATR(14) from entry, fixed at entry

## Position sizing
- Default engine sizing: 100% of equity per trade, no leverage, one position at a time.

## NNFX structure (Stonehill only)
- Baseline: …
- Confirmation: …
- Volatility filter: …
- Exit indicator: …

## Assumptions and additions  ⚠️
Everything here was NOT in the original and was added to make it testable:
- …

## Execution assumptions (same for every strategy)
- Signals use only data up to the bar's close; fills at the next bar's open.
- Fees 0.10% per fill, slippage 0.05% per fill (see `config.json`).
