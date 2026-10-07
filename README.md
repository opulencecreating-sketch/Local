# Strategy research pipeline (backtest only)

> Research only. Not financial advice. No live orders anywhere in this code.

Pipeline: **01 collect → 02 spec → 03 engine → 04 rank → 05 verify → 06 forward**.

| Step | Where | Status |
|---|---|---|
| 01 Collect | `strategies/source/` — drop your Pine Scripts / Stonehill / QuantConnect / Quantpedia files here | **empty — waiting for your files** |
| 02 Spec | `strategies/specs/<name>.md` (copy `_TEMPLATE.md`) + `strategies/<name>.py` | template ready |
| 03 Engine | `engine/` — fees, slippage, next-bar-open fills, stops, no look-ahead (tested) | done |
| 04 Rank | `python run.py` → `REPORT.md` (winners, losers, vs buy-and-hold, sub-period check) | done |
| 05 Verify | Pine Script versions of the winners, for TradingView's Strategy Tester | after ranking |
| 06 Forward | paper → small real size → scale | yours |

## Run
```
python -m pytest -q tests        # engine correctness tests
python run.py                     # your strategies
python run.py --include-examples  # + SMA-cross smoke test (not a real pick)
```
Set assets, timeframes, costs and ranking in `config.json`. Crypto (`BTC-USD`, etc.) downloads
from Coinbase. For stocks or forex, put a CSV at `data/<SYMBOL>_<TF>.csv`
(`time,open,high,low,close,volume`); there is no free source here that reliably serves them.

## Adding a strategy
`strategies/<name>.py` must define `SPEC = {"name", "source", "params"}` and
`signals(df, **params)` returning `entry_long`/`exit_long` (optional `entry_short`/`exit_short`/`stop`),
using only data up to each bar's close.
