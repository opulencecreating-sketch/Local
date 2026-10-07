"""Run every strategy across every asset/timeframe in config.json and write REPORT.md.

    python run.py                    # your strategies only (strategies/*.py)
    python run.py --include-examples # also the engine smoke test
"""
from __future__ import annotations

import argparse
import importlib
import json
import math
import pkgutil
from pathlib import Path

import pandas as pd

from engine import data
from engine.backtest import Costs, buy_and_hold, run
from engine.metrics import period_split, summarize

ROOT = Path(__file__).resolve().parent


def discover(include_examples: bool):
    pkgs = ["strategies"] + (["strategies.examples"] if include_examples else [])
    for pkg in pkgs:
        path = ROOT / pkg.replace(".", "/")
        for m in pkgutil.iter_modules([str(path)]):
            if m.ispkg or m.name.startswith("_"):
                continue
            mod = importlib.import_module(f"{pkg}.{m.name}")
            if hasattr(mod, "signals") and hasattr(mod, "SPEC"):
                yield m.name, mod


def pct(x):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:+.1%}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-examples", action="store_true")
    ap.add_argument("--refresh", action="store_true", help="re-download market data")
    args = ap.parse_args()
    cfg = json.loads((ROOT / "config.json").read_text())
    costs = Costs(cfg["fee_rate"], cfg["slippage"])

    strategies = list(discover(args.include_examples))
    if not strategies:
        print("No strategies found in strategies/. Add one .py per strategy (see README).")
        return

    rows, splits, failures = [], {}, []
    for asset in cfg["assets"]:
        for tf in cfg["timeframes"]:
            try:
                df = data.load(asset, tf, cfg["start"], refresh=args.refresh)
            except Exception as e:
                failures.append(f"DATA {asset} {tf}: {e}")
                continue
            bench = buy_and_hold(df, costs)
            for key, mod in strategies:
                try:
                    sig = mod.signals(df, **mod.SPEC.get("params", {}))
                    res = run(df, sig, costs)
                except Exception as e:
                    failures.append(f"RUN {key} {asset} {tf}: {e}")
                    continue
                m = summarize(res, bench)
                rows.append({"strategy": mod.SPEC["name"], "key": key, "asset": asset, "tf": tf,
                             "from": df.index[0].date(), "to": df.index[-1].date(), **m})
                splits[(key, asset, tf)] = period_split(res, bench)

    out = pd.DataFrame(rows)
    write_report(out, splits, failures, cfg)
    print((ROOT / "REPORT.md").read_text())


def write_report(df, splits, failures, cfg):
    L = ["# Backtest report", "",
         "> Research only. Not financial advice. Backtests are not live results.", "",
         f"Costs in every run: fee {cfg['fee_rate']:.2%} + slippage {cfg['slippage']:.2%} per fill. "
         "Signals on bar close, fills on next bar open.", ""]
    if failures:
        L += ["## Failures (not hidden)", ""] + [f"- {f}" for f in failures] + [""]
    if df.empty:
        (ROOT / "REPORT.md").write_text("\n".join(L + ["No results."]))
        return
    sort = {"low_drawdown": ("max_drawdown", False), "high_return": ("total_return", False),
            "low_maintenance": ("trades", True)}[cfg.get("rank_by", "low_drawdown")]
    df = df.sort_values(sort[0], ascending=sort[1])

    def table(d):
        t = ["| Strategy | Asset | TF | Return | Max DD | Win % | PF | Trades | B&H | vs B&H |",
             "|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in d.iterrows():
            wr = "n/a" if math.isnan(r.win_rate) else f"{r.win_rate:.0%}"
            pf = "n/a" if math.isnan(r.profit_factor) else f"{r.profit_factor:.2f}"
            t.append(f"| {r.strategy} | {r.asset} | {r.tf} | {pct(r.total_return)} | "
                     f"{r.max_drawdown:.1%} | {wr} | {pf} | {r.trades} | {pct(r.bh_return)} | {pct(r.vs_bh)} |")
        return t

    win = df[(df.total_return > 0) & df.beats_bh & (df.trades >= 20)]
    lose = df[df.total_return <= 0]
    L += [f"## Top picks (profitable, beat buy-and-hold, ≥20 trades) — ranked by {cfg.get('rank_by')}", ""]
    L += table(win) if len(win) else ["None. No strategy made money AND beat buy-and-hold with enough trades."]
    L += ["", "## Lost money", ""] + (table(lose) if len(lose) else ["None."])
    L += ["", "## All runs", ""] + table(df)
    L += ["", "## Final check", ""]
    L += [f"- Fees and slippage in every run: yes (total fees range "
          f"${df.fees_paid.min():,.0f}–${df.fees_paid.max():,.0f} on $10k start)."]
    L += [f"- Runs that beat buy-and-hold: {int(df.beats_bh.sum())} of {len(df)}."]
    for _, r in win.iterrows():
        sp = splits[(r.key, r.asset, r.tf)]
        good = sum(s["ret"] > s["bh"] for s in sp)
        detail = "; ".join(f"{s['start']}→{s['end']}: {pct(s['ret'])} vs B&H {pct(s['bh'])}" for s in sp)
        flag = "consistent" if good == len(sp) else "⚠️ possibly one lucky period"
        L.append(f"- {r.strategy} {r.asset} {r.tf}: beat B&H in {good}/{len(sp)} sub-periods ({flag}). {detail}")
    L += ["", "## WHY THIS COULD STOP WORKING", "",
          "- Every number above is in-sample on one history; regimes change.",
          "- Real fills on 4H/1D crypto can be worse than the modelled slippage in fast markets.",
          "- Strategies built from indicators had trade rules added (see each spec's assumptions).",
          "- Forward-test order is fixed: paper first, then small real size, then scale."]
    (ROOT / "REPORT.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
