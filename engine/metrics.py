from __future__ import annotations

import numpy as np
import pandas as pd

from .backtest import Result


def max_drawdown(eq: pd.Series) -> float:
    return float((eq / eq.cummax() - 1).min())


def summarize(res: Result, bench: pd.Series) -> dict:
    eq = res.equity
    pnls = np.array([t.pnl for t in res.trades])
    wins, losses = pnls[pnls > 0], pnls[pnls <= 0]
    gross_loss = -losses.sum()
    total = eq.iloc[-1] / eq.iloc[0] - 1
    bh = bench.iloc[-1] / bench.iloc[0] - 1
    return {
        "total_return": total,
        "max_drawdown": max_drawdown(eq),
        "win_rate": len(wins) / len(pnls) if len(pnls) else np.nan,
        "profit_factor": wins.sum() / gross_loss if gross_loss > 0 else (np.inf if len(wins) else np.nan),
        "trades": len(pnls),
        "fees_paid": res.total_fees,
        "bh_return": bh,
        "bh_max_drawdown": max_drawdown(bench),
        "vs_bh": total - bh,
        "beats_bh": bool(total > bh),
    }


def period_split(res: Result, bench: pd.Series, parts: int = 3) -> list[dict]:
    """Return per-sub-period strategy vs buy-and-hold, to catch one-lucky-period winners."""
    idx = res.equity.index
    out = []
    for chunk in np.array_split(np.arange(len(idx)), parts):
        if len(chunk) < 2:
            continue
        e, b = res.equity.iloc[chunk], bench.iloc[chunk]
        out.append({"start": idx[chunk[0]].date(), "end": idx[chunk[-1]].date(),
                    "ret": e.iloc[-1] / e.iloc[0] - 1, "bh": b.iloc[-1] / b.iloc[0] - 1})
    return out
