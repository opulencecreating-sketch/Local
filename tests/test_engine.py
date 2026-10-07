import numpy as np
import pandas as pd

from engine.backtest import Costs, buy_and_hold, run


def bars(closes):
    idx = pd.date_range("2020-01-01", periods=len(closes), freq="D", tz="UTC")
    c = np.array(closes, float)
    o = np.r_[c[0], c[:-1]]
    return pd.DataFrame({"open": o, "high": np.maximum(o, c), "low": np.minimum(o, c),
                         "close": c, "volume": 1.0}, index=idx)


def sig(df, entries=(), exits=()):
    s = pd.DataFrame(False, index=df.index, columns=["entry_long", "exit_long"])
    s.iloc[list(entries), 0] = True
    s.iloc[list(exits), 1] = True
    return s


def test_fill_is_next_bar_open():
    df = bars([100, 100, 110, 120, 130])
    r = run(df, sig(df, [1], [3]), Costs(0, 0))
    t = r.trades[0]
    assert t.entry_price == df.open.iloc[2] and t.exit_price == df.open.iloc[4]


def test_no_lookahead_future_changes_do_not_alter_past_equity():
    rng = np.random.default_rng(0)
    a = 100 * np.cumprod(1 + rng.normal(0, 0.02, 300))
    b = a.copy(); b[200:] *= 3  # change only the future
    strat = lambda d: pd.DataFrame({"entry_long": d.close > d.close.rolling(10).mean(),
                                    "exit_long": d.close < d.close.rolling(10).mean()})
    da, db = bars(a), bars(b)
    ea, eb = run(da, strat(da)).equity, run(db, strat(db)).equity
    assert np.allclose(ea.iloc[:199], eb.iloc[:199])


def test_costs_reduce_returns():
    df = bars([100, 100, 100, 100, 100])
    r = run(df, sig(df, [0], [2]), Costs(0.001, 0.0005))
    assert r.equity.iloc[-1] < 10_000 and r.total_fees > 0


def test_stop_loss_and_gap():
    df = bars([100, 100, 100, 80, 80])  # bar 3 opens at 100, low 80
    s = sig(df, [1]); s["stop"] = 95.0
    t = run(df, s, Costs(0, 0)).trades[0]
    assert t.reason == "stop" and t.exit_price == 95.0


def test_short_pnl():
    df = bars([100, 100, 90, 80, 80])
    s = pd.DataFrame(False, index=df.index, columns=["entry_long", "exit_long", "entry_short", "exit_short"])
    s.iloc[1, 2] = True; s.iloc[3, 3] = True  # short at open[2]=100, cover at open[4]=80
    r = run(df, s, Costs(0, 0))
    assert np.isclose(r.equity.iloc[-1], 12_000)


def test_buy_and_hold_includes_costs():
    df = bars([100, 100])
    assert buy_and_hold(df, Costs(0.001, 0.0005)).iloc[-1] < 10_000
