"""Market data loading.

Sources, in order of preference:
  1. A local CSV at data/<SYMBOL>_<TF>.csv with columns time,open,high,low,close,volume
     (use this for stocks/forex — export from TradingView or your broker).
  2. Coinbase public candles for crypto symbols like BTC-USD (no API key).

4H bars are built by resampling 1H bars, because Coinbase has no 4H granularity.
Nothing here fills gaps or invents bars; missing data raises an error.
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
COINBASE = "https://api.exchange.coinbase.com/products/{sym}/candles?granularity={g}&start={s}&end={e}"
TF_SECONDS = {"1H": 3600, "4H": 14400, "6H": 21600, "1D": 86400}


def _csv_path(symbol: str, tf: str) -> Path:
    return DATA_DIR / f"{symbol.replace('/', '-')}_{tf}.csv"


def _fetch_coinbase(symbol: str, gran: int, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    rows, step = [], gran * 300  # Coinbase returns at most 300 candles per call
    t = int(start.timestamp())
    stop = int(end.timestamp())
    while t < stop:
        e = min(t + step, stop)
        url = COINBASE.format(sym=symbol, g=gran,
                              s=pd.Timestamp(t, unit="s").isoformat(),
                              e=pd.Timestamp(e, unit="s").isoformat())
        req = urllib.request.Request(url, headers={"User-Agent": "backtest-research"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    batch = json.load(r)
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        if isinstance(batch, dict):
            raise RuntimeError(f"Coinbase error for {symbol}: {batch}")
        rows.extend(batch)
        t = e
        time.sleep(0.15)
    if not rows:
        raise RuntimeError(f"No data returned for {symbol}")
    df = pd.DataFrame(rows, columns=["time", "low", "high", "open", "close", "volume"])
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    return (df.drop_duplicates("time").sort_values("time").set_index("time")
              [["open", "high", "low", "close", "volume"]].astype(float))


def _resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    out = df.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    return out.dropna()


def load(symbol: str, tf: str, start: str = "2019-01-01", end: str | None = None,
         refresh: bool = False) -> pd.DataFrame:
    tf = tf.upper()
    path = _csv_path(symbol, tf)
    if path.exists() and not refresh:
        df = pd.read_csv(path, parse_dates=["time"]).set_index("time")
        df.index = pd.to_datetime(df.index, utc=True)
        return df.sort_index()[["open", "high", "low", "close", "volume"]].astype(float)

    if "-" not in symbol:
        raise FileNotFoundError(
            f"No data for {symbol} {tf}. Put a CSV at {path} "
            "(columns: time,open,high,low,close,volume).")

    s = pd.Timestamp(start, tz="UTC")
    e = pd.Timestamp(end, tz="UTC") if end else pd.Timestamp.now(tz="UTC").floor("h")
    if tf == "4H":
        df = _resample(_fetch_coinbase(symbol, 3600, s, e), "4h")
    elif tf in TF_SECONDS:
        df = _fetch_coinbase(symbol, TF_SECONDS[tf], s, e)
    else:
        raise ValueError(f"Unsupported timeframe {tf}")
    # Drop the last bar: it may still be forming.
    df = df.iloc[:-1]
    DATA_DIR.mkdir(exist_ok=True)
    df.reset_index().to_csv(path, index=False)
    return df
