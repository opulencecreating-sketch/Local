"""ENGINE SMOKE TEST ONLY - not one of your collected strategies.

A textbook 50/200 moving-average cross, used to prove the engine runs end to end.
It is excluded from the ranking unless you pass --include-examples.
"""
import pandas as pd

SPEC = {
    "name": "Example: SMA 50/200 cross (smoke test)",
    "source": "Textbook example, added by Claude (not from your folder)",
    "params": {"fast": 50, "slow": 200},
}


def signals(df: pd.DataFrame, fast: int = 50, slow: int = 200) -> pd.DataFrame:
    f, s = df["close"].rolling(fast).mean(), df["close"].rolling(slow).mean()
    above = f > s
    return pd.DataFrame({
        "entry_long": above & ~above.shift(1, fill_value=False),
        "exit_long": ~above & above.shift(1, fill_value=False),
    }, index=df.index)
