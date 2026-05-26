"""
Data processing template — verification-driven.

Copy this file, adapt the TRANSFORM section to the user's task,
keep all the logging and assertion structure intact.

Anti-hallucination contract:
- Every transformation logs row count before, after, and delta.
- Every assumption is asserted at the end.
- The script prints a verified sample of the output.
"""

from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# CONFIG  — fill in per task
# ---------------------------------------------------------------------------
INPUT_PATH = Path("input.csv")
OUTPUT_PATH = Path("output.csv")

KEY_COLUMNS = ["id"]                       # for dedup / join
REQUIRED_COLUMNS = ["id", "value"]         # must be non-null after processing
EXPECTED_OUTPUT_ROWS = None                # set after first run; assert thereafter


# ---------------------------------------------------------------------------
# 1. LOAD + INSPECT
# ---------------------------------------------------------------------------
def load_and_inspect(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    print(f"[load] {path}: shape={df.shape}")
    print(f"[load] dtypes:\n{df.dtypes}\n")
    print(f"[load] null counts:\n{df.isna().sum()}\n")
    print(f"[load] sample:\n{df.head()}\n")
    return df


# ---------------------------------------------------------------------------
# 2. TRANSFORM  — log delta on every step
# ---------------------------------------------------------------------------
def log_delta(label: str, before: int, after: int) -> None:
    delta = before - after
    pct = (delta / before * 100) if before else 0.0
    print(f"[transform] {label}: {before} -> {after} ({delta:+d} rows, {pct:.1f}% removed)")


def transform(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates(subset=KEY_COLUMNS)
    log_delta(f"dedupe on {KEY_COLUMNS}", before, len(df))

    before = len(df)
    df = df.dropna(subset=REQUIRED_COLUMNS)
    log_delta(f"drop null in {REQUIRED_COLUMNS}", before, len(df))

    # ADD TRANSFORMS HERE.
    # Pattern:
    #   before = len(df)
    #   df = df. ... (some operation)
    #   log_delta("<short label>", before, len(df))

    return df


# ---------------------------------------------------------------------------
# 3. VALIDATE  — assert invariants explicitly
# ---------------------------------------------------------------------------
def validate(df: pd.DataFrame) -> None:
    for col in KEY_COLUMNS:
        assert df[col].is_unique, f"[validate] {col} not unique after dedup"
    for col in REQUIRED_COLUMNS:
        assert df[col].notna().all(), f"[validate] null values remain in {col}"
    if EXPECTED_OUTPUT_ROWS is not None:
        assert len(df) == EXPECTED_OUTPUT_ROWS, (
            f"[validate] expected {EXPECTED_OUTPUT_ROWS} rows, got {len(df)}"
        )
    print(f"[validate] all assertions passed (rows={len(df)})")


# ---------------------------------------------------------------------------
# 4. WRITE + SAMPLE
# ---------------------------------------------------------------------------
def write_and_sample(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False)
    print(f"[write] {path}: shape={df.shape}")
    print(f"[write] sample:\n{df.head()}\n")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    df = load_and_inspect(INPUT_PATH)
    df = transform(df)
    validate(df)
    write_and_sample(df, OUTPUT_PATH)
