#!/usr/bin/env python3
"""Backtest several StatsForecast models on a time series, rank them, and
produce a forecast with prediction intervals from the winning model.

Usage:
    python3 backtest.py --csv sales.csv --date-col date --value-col revenue \
        --freq MS --season 12 --h 12 --windows 4

    python3 backtest.py --demo        # run on built-in AirPassengers dataset

Requires: pip install "statsforecast>=2.0" "utilsforecast>=0.2" pandas
Prints a model leaderboard (lower is better) and the final forecast to stdout;
optionally writes the forecast to --out.
"""
import argparse
import sys


def _load_models(season):
    from statsforecast.models import AutoARIMA, AutoETS, AutoTheta, SeasonalNaive
    return [
        AutoARIMA(season_length=season),
        AutoETS(season_length=season),
        AutoTheta(season_length=season),
        SeasonalNaive(season_length=season),  # baseline to beat
    ]


def _read_data(args):
    import pandas as pd
    if args.demo:
        from statsforecast.utils import AirPassengersDF
        return AirPassengersDF.copy(), "MS", 12
    if not args.csv:
        sys.exit("Provide --csv (with --date-col/--value-col) or use --demo")
    df = pd.read_csv(args.csv)
    df = df.rename(columns={args.date_col: "ds", args.value_col: "y"})
    df["ds"] = pd.to_datetime(df["ds"])
    if args.id_col and args.id_col in df.columns:
        df = df.rename(columns={args.id_col: "unique_id"})
    else:
        df["unique_id"] = "series_1"
    df = df[["unique_id", "ds", "y"]].sort_values(["unique_id", "ds"])
    return df, args.freq, args.season


def main():
    p = argparse.ArgumentParser(description="Backtest + forecast a time series with StatsForecast.")
    p.add_argument("--csv")
    p.add_argument("--date-col", default="date")
    p.add_argument("--value-col", default="value")
    p.add_argument("--id-col", default=None, help="optional series-id column for many series")
    p.add_argument("--freq", default="MS", help="pandas freq: D, W, MS, ME, QE, h ...")
    p.add_argument("--season", type=int, default=12, help="steps per seasonal cycle")
    p.add_argument("--h", type=int, default=12, help="forecast horizon")
    p.add_argument("--windows", type=int, default=4, help="rolling backtest windows")
    p.add_argument("--level", type=int, default=95, help="prediction-interval level")
    p.add_argument("--demo", action="store_true")
    p.add_argument("--out", default=None, help="write final forecast CSV here")
    args = p.parse_args()

    try:
        from statsforecast import StatsForecast
        from utilsforecast.evaluation import evaluate
        from utilsforecast.losses import mae, rmse, mape
    except ImportError as e:
        sys.exit(f"Missing dependency: {e}. Run: pip install 'statsforecast>=2.0' 'utilsforecast>=0.2' pandas")

    df, freq, season = _read_data(args)
    model_names = ["AutoARIMA", "AutoETS", "AutoTheta", "SeasonalNaive"]
    sf = StatsForecast(models=_load_models(season), freq=freq, n_jobs=-1)

    # 1. Rolling-origin backtest.
    cv = sf.cross_validation(
        df=df, h=args.h, n_windows=args.windows, step_size=args.h, level=[args.level]
    )
    scores = evaluate(cv.drop(columns="cutoff"), metrics=[mae, rmse, mape], models=model_names)
    leaderboard = scores.drop(columns="unique_id").groupby("metric").mean()
    print("=== Backtest leaderboard (lower is better) ===")
    print(leaderboard.to_string())

    # 2. Winner = lowest mean RMSE across windows/series.
    rmse_row = leaderboard.loc["rmse"]
    winner = rmse_row.astype(float).idxmin()
    print(f"\nWinning model by RMSE: {winner}")

    # 3. Final forecast from all models (winner column is the one to use).
    fcst = sf.forecast(df=df, h=args.h, level=[args.level])
    keep = ["unique_id", "ds", winner, f"{winner}-lo-{args.level}", f"{winner}-hi-{args.level}"]
    keep = [c for c in keep if c in fcst.columns]
    final = fcst[keep]
    print(f"\n=== Forecast ({winner}, {args.level}% interval) ===")
    print(final.to_string(index=False))

    if args.out:
        final.to_csv(args.out, index=False)
        print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
