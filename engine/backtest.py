"""Bar-by-bar backtester with fees, slippage and no look-ahead.

Contract with strategies
------------------------
A strategy is a function `signals(df, **params) -> pd.DataFrame` returning, per bar,
columns computed ONLY from data up to and including that bar's close:

    entry_long, exit_long            (bool)  -- required
    entry_short, exit_short          (bool)  -- optional
    stop                              (float) -- optional, absolute stop price for a new entry

Execution rules (fixed, not per-strategy, so every run is comparable):
  * A signal on bar t is filled at the OPEN of bar t+1, adjusted by slippage.
  * A stop is checked intrabar from the bar after entry; if the bar opens through the
    stop, the fill is the open (gap), otherwise the stop price, then slippage.
  * Fees are charged on the notional of every fill (entry and exit).
  * Position sizing: fixed fraction of current equity per trade (default 100%), no leverage.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class Costs:
    fee_rate: float = 0.001      # 0.10% per fill (typical taker fee)
    slippage: float = 0.0005     # 0.05% adverse price per fill


@dataclass
class Trade:
    side: int
    entry_time: pd.Timestamp
    entry_price: float
    exit_time: pd.Timestamp | None = None
    exit_price: float | None = None
    qty: float = 0.0
    fees: float = 0.0
    pnl: float = 0.0
    reason: str = ""


@dataclass
class Result:
    equity: pd.Series
    trades: list[Trade] = field(default_factory=list)
    costs: Costs = field(default_factory=Costs)
    total_fees: float = 0.0


def run(df: pd.DataFrame, sig: pd.DataFrame, costs: Costs | None = None,
        capital: float = 10_000.0, fraction: float = 1.0) -> Result:
    costs = costs or Costs()
    sig = sig.reindex(df.index)
    n = len(df)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    get = lambda k: sig[k].fillna(False).to_numpy(bool) if k in sig else np.zeros(n, bool)
    el, xl, es, xs = get("entry_long"), get("exit_long"), get("entry_short"), get("exit_short")
    stops = sig["stop"].to_numpy(float) if "stop" in sig else np.full(n, np.nan)

    cash, pos, trade = capital, None, None
    equity = np.empty(n)
    trades: list[Trade] = []
    fees_total = 0.0
    pending = None  # ("enter", side, stop) or ("exit",)
    stop_px = np.nan

    def fill(px, side):  # side +1 buy, -1 sell: slippage always adverse
        return px * (1 + costs.slippage * side)

    def close(i, px_raw, reason):
        nonlocal cash, trade, pos, fees_total
        px = fill(px_raw, -trade.side)
        fee = abs(trade.qty * px) * costs.fee_rate
        gross = trade.side * trade.qty * (px - trade.entry_price)
        cash += trade.qty * px if trade.side > 0 else gross  # shorts: only P&L moves cash
        cash -= fee
        trade.exit_time, trade.exit_price = df.index[i], px
        trade.fees += fee
        trade.pnl = gross - trade.fees
        trade.reason = reason
        fees_total += fee
        trades.append(trade)
        trade, pos = None, None

    for i in range(n):
        # 1) execute orders decided on the previous bar's close, at this bar's open
        if pending is not None:
            kind = pending[0]
            if kind in ("exit", "flip") and trade is not None:
                close(i, o[i], "signal")
            if kind in ("enter", "flip") and trade is None:
                side, stp = pending[1], pending[2]
                px = fill(o[i], side)
                budget = cash * fraction
                qty = budget / (px * (1 + costs.fee_rate))
                fee = qty * px * costs.fee_rate
                cash -= fee
                if side > 0:
                    cash -= qty * px
                trade = Trade(side, df.index[i], px, qty=qty, fees=fee)
                fees_total += fee
                pos, stop_px = side, stp
            pending = None

        # 2) intrabar stop check (from the entry bar onwards; entry was at the open)
        if trade is not None and not np.isnan(stop_px):
            if trade.side > 0 and l[i] <= stop_px:
                close(i, min(o[i], stop_px), "stop")
            elif trade.side < 0 and h[i] >= stop_px:
                close(i, max(o[i], stop_px), "stop")

        # 3) mark to market at close
        if trade is None:
            equity[i] = cash
        elif trade.side > 0:
            equity[i] = cash + trade.qty * c[i]
        else:
            equity[i] = cash + trade.qty * (trade.entry_price - c[i])

        # 4) decide on this bar's close; executes next bar
        if i == n - 1:
            break
        if pos == 1 and (xl[i] or es[i]):
            pending = ("flip", -1, stops[i]) if es[i] else ("exit",)
        elif pos == -1 and (xs[i] or el[i]):
            pending = ("flip", 1, stops[i]) if el[i] else ("exit",)
        elif pos is None:
            if el[i]:
                pending = ("enter", 1, stops[i])
            elif es[i]:
                pending = ("enter", -1, stops[i])

    # Close any open trade at the last close so its cost is counted.
    if trade is not None:
        close(n - 1, c[n - 1], "end")
        equity[n - 1] = cash
    return Result(pd.Series(equity, index=df.index), trades, costs, fees_total)


def buy_and_hold(df: pd.DataFrame, costs: Costs | None = None, capital: float = 10_000.0) -> pd.Series:
    """Benchmark with the same costs: buy at the first bar's open, sell at the last close."""
    costs = costs or Costs()
    entry = df["open"].iloc[0] * (1 + costs.slippage)
    qty = capital / (entry * (1 + costs.fee_rate))
    eq = capital - qty * entry * (1 + costs.fee_rate) + qty * df["close"]
    exit_px = df["close"].iloc[-1] * (1 - costs.slippage)
    eq.iloc[-1] = capital - qty * entry * (1 + costs.fee_rate) + qty * exit_px * (1 - costs.fee_rate)
    return eq
