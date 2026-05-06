"""
ml_pipeline.py — Improved ML pipeline for stock outperformance prediction.

Key improvements over v1:
  - 14 features vs 8: adds RSI(14), MACD, Bollinger Band %B, 52w high/low distance,
    normalised volume spike (90d), relative strength vs Nifty 500 index
  - True time-based train/test split (no data leakage)
  - Binary classification: will stock outperform Nifty 500 over next 20 days?
  - Regression + classification models per horizon
  - Auto-triggered by price_scheduler after daily refresh
"""

import json
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, date
from typing import Optional

from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import mean_absolute_error, r2_score, accuracy_score, roc_auc_score
import joblib

from config import DATA_DIR
from data_store import DataStore

logger = logging.getLogger(__name__)

MODELS_DIR = DATA_DIR / "ml_models"
PREDICTIONS_FILE = DATA_DIR / "ml_predictions.json"
METRICS_FILE = DATA_DIR / "oot_metrics.json"

MODELS_DIR.mkdir(exist_ok=True)

# Train on data before this date, test on data from this date onward
# Updated to ~10 months ago to give reasonable test window
TRAIN_CUTOFF = "2025-07-01"

FEATURE_COLS = [
    # Price momentum
    "ret_1d", "ret_5d", "ret_20d", "ret_90d",
    # Volatility
    "vol_20d",
    # SMA distance
    "dist_sma_20", "dist_sma_50",
    # Volume
    "vol_ratio_5d", "vol_spike_90d",
    # Technical indicators
    "rsi_14", "macd_signal", "bb_pct_b",
    # Breakout signals
    "dist_52w_high", "dist_52w_low",
    # Relative strength vs Nifty 500 index
    "rel_strength_20d",
]


# ─── Feature Engineering ──────────────────────────────────────────────────────

def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def extract_features_targets(prices_df: pd.DataFrame, index_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Given a dataframe of prices for a single stock (sorted by date ascending),
    compute 14 technical features and forward return + outperformance targets.

    Args:
        prices_df: columns = [date, open, high, low, close, volume]
        index_df: Nifty 500 daily prices [date, close] for relative-strength feature.
                  If None, rel_strength_20d is set to 0.
    """
    df = prices_df.copy().sort_values("date").reset_index(drop=True)

    # ── Momentum ───────────────────────────────────────────────────────────────
    df["ret_1d"]  = df["close"].pct_change(1)
    df["ret_5d"]  = df["close"].pct_change(5)
    df["ret_20d"] = df["close"].pct_change(20)
    df["ret_90d"] = df["close"].pct_change(90)

    # ── Volatility ─────────────────────────────────────────────────────────────
    df["vol_20d"] = df["ret_1d"].rolling(20).std() * np.sqrt(252)

    # ── SMA distance ───────────────────────────────────────────────────────────
    sma_20 = df["close"].rolling(20).mean()
    sma_50 = df["close"].rolling(50).mean()
    df["dist_sma_20"] = (df["close"] - sma_20) / sma_20.replace(0, np.nan)
    df["dist_sma_50"] = (df["close"] - sma_50) / sma_50.replace(0, np.nan)

    # ── Volume ─────────────────────────────────────────────────────────────────
    vol_ma_5  = df["volume"].rolling(5).mean()
    vol_ma_20 = df["volume"].rolling(20).mean()
    vol_ma_90 = df["volume"].rolling(90).mean()
    df["vol_ratio_5d"]  = vol_ma_5  / (vol_ma_20  + 1e-5)
    df["vol_spike_90d"] = df["volume"] / (vol_ma_90 + 1e-5)

    # ── RSI (14) ───────────────────────────────────────────────────────────────
    delta = df["close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # ── MACD (12, 26, 9) signal line position ──────────────────────────────────
    ema12  = _ema(df["close"], 12)
    ema26  = _ema(df["close"], 26)
    macd   = ema12 - ema26
    signal = _ema(macd, 9)
    # Normalise by price so it's scale-invariant
    df["macd_signal"] = (macd - signal) / df["close"].replace(0, np.nan)

    # ── Bollinger Band %B ──────────────────────────────────────────────────────
    bb_mid   = df["close"].rolling(20).mean()
    bb_std   = df["close"].rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    bb_range = (bb_upper - bb_lower).replace(0, np.nan)
    df["bb_pct_b"] = (df["close"] - bb_lower) / bb_range

    # ── 52-week high / low distance ────────────────────────────────────────────
    high_252 = df["high"].rolling(252, min_periods=60).max()
    low_252  = df["low"].rolling(252, min_periods=60).min()
    df["dist_52w_high"] = (df["close"] - high_252) / high_252.replace(0, np.nan)
    df["dist_52w_low"]  = (df["close"] - low_252)  / low_252.replace(0, np.nan)

    # ── Relative strength vs Nifty 500 index (20d) ────────────────────────────
    if index_df is not None and not index_df.empty:
        idx = index_df.set_index("date")["close"].rename("idx_close")
        df = df.join(idx, on="date", how="left")
        df["idx_close"] = df["idx_close"].ffill()
        idx_ret_20d = df["idx_close"].pct_change(20)
        df["rel_strength_20d"] = df["ret_20d"] - idx_ret_20d
    else:
        df["rel_strength_20d"] = 0.0

    # ── Forward return targets (regression) ───────────────────────────────────
    df["target_1d"] = df["close"].shift(-1)  / df["close"] - 1
    df["target_1w"] = df["close"].shift(-5)  / df["close"] - 1
    df["target_1m"] = df["close"].shift(-20) / df["close"] - 1

    # ── Classification target: outperforms Nifty 500 over next 20 days ─────────
    if index_df is not None and not index_df.empty and "idx_close" in df.columns:
        idx_ret_fwd = df["idx_close"].shift(-20) / df["idx_close"] - 1
        df["target_outperform"] = (df["target_1m"] > idx_ret_fwd).astype(float)
    else:
        df["target_outperform"] = (df["target_1m"] > 0).astype(float)  # vs zero return

    # Drop rows without enough history
    return df.dropna(subset=["ret_90d", "dist_sma_50", "rsi_14", "macd_signal"])


# ─── Dataset Builder ──────────────────────────────────────────────────────────

def build_dataset(store: DataStore) -> dict:
    """Build the full training dataset from all stocks + index data."""
    logger.info("Building ML dataset...")

    # Load Nifty 500 index data for relative strength feature
    index_rows = store.conn.execute(
        "SELECT date, close FROM index_data WHERE index_name = 'Nifty 500' ORDER BY date"
    ).fetchall()
    index_df = pd.DataFrame([dict(r) for r in index_rows]) if index_rows else pd.DataFrame()
    if not index_df.empty:
        index_df["date"] = pd.to_datetime(index_df["date"])

    stocks = store.get_all_stocks()
    all_rows = []          # (date, features, targets)
    latest_features = {}   # symbol → latest feature vector for prediction

    for stock in stocks:
        prices = store.get_price_series(stock.symbol, days=800)
        if len(prices) < 120:
            continue

        df = pd.DataFrame(prices)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        feat_df = extract_features_targets(df, index_df)
        if feat_df.empty:
            continue

        # Save latest row for today's predictions
        last = feat_df.iloc[-1]
        if all(pd.notna(last[c]) for c in FEATURE_COLS):
            latest_features[stock.symbol] = last[FEATURE_COLS].to_dict()

        # Collect training rows (non-NaN targets)
        for _, row in feat_df.iterrows():
            all_rows.append({
                "date": row["date"],
                **{c: row[c] for c in FEATURE_COLS},
                "target_1d":        row["target_1d"],
                "target_1w":        row["target_1w"],
                "target_1m":        row["target_1m"],
                "target_outperform": row["target_outperform"],
            })

    full_df = pd.DataFrame(all_rows).sort_values("date").reset_index(drop=True)
    logger.info(f"Dataset: {len(full_df):,} rows from {len(stocks)} stocks.")
    return {"df": full_df, "latest_features": latest_features}


# ─── Model Training ───────────────────────────────────────────────────────────

def train_models(store: Optional[DataStore] = None) -> dict:
    """
    Train regression models (1d, 1w, 1m) and a classification model
    (outperforms Nifty 500 over 20 days) with proper temporal train/test split.
    """
    if store is None:
        store = DataStore()

    data = build_dataset(store)
    full_df: pd.DataFrame = data["df"]
    latest_features: dict = data["latest_features"]

    if full_df.empty:
        logger.error("Empty dataset — cannot train.")
        return {"error": "Empty dataset"}

    # ── Temporal train / test split ───────────────────────────────────────────
    train_df = full_df[full_df["date"] < TRAIN_CUTOFF]
    test_df  = full_df[full_df["date"] >= TRAIN_CUTOFF]

    logger.info(f"Train: {len(train_df):,} rows (before {TRAIN_CUTOFF}), "
                f"Test: {len(test_df):,} rows (after {TRAIN_CUTOFF})")

    if len(train_df) < 1000 or len(test_df) < 100:
        logger.warning("Insufficient data for proper split — using 80/20 fallback.")
        split = int(len(full_df) * 0.8)
        train_df = full_df.iloc[:split]
        test_df  = full_df.iloc[split:]

    # ── Scaler ────────────────────────────────────────────────────────────────
    X_train_raw = train_df[FEATURE_COLS].values
    X_test_raw  = test_df[FEATURE_COLS].values

    scaler = RobustScaler()
    X_train = scaler.fit_transform(X_train_raw)
    X_test  = scaler.transform(X_test_raw)
    joblib.dump(scaler, MODELS_DIR / "scaler.pkl")

    all_metrics = []

    # ── Regression models: 1d, 1w, 1m ────────────────────────────────────────
    for horizon, target_col in [("1d", "target_1d"), ("1w", "target_1w"), ("1m", "target_1m")]:
        y_train = train_df[target_col].values
        y_test  = test_df[target_col].values

        valid_train = ~np.isnan(y_train)
        valid_test  = ~np.isnan(y_test)

        model = HistGradientBoostingRegressor(
            max_iter=200,
            max_depth=5,
            learning_rate=0.05,
            min_samples_leaf=20,
            random_state=42,
        )
        model.fit(X_train[valid_train], y_train[valid_train])
        joblib.dump(model, MODELS_DIR / f"model_{horizon}.pkl")

        preds = model.predict(X_test[valid_test])
        mae = mean_absolute_error(y_test[valid_test], preds)
        r2  = r2_score(y_test[valid_test], preds)

        metrics = {
            "model": f"regression_{horizon}",
            "train_samples": int(valid_train.sum()),
            "test_samples":  int(valid_test.sum()),
            "MAE":  round(float(mae), 5),
            "R2":   round(float(r2),  4),
            "trained_at": datetime.now().isoformat(),
        }
        all_metrics.append(metrics)
        logger.info(f"[{horizon}] MAE={metrics['MAE']:.5f}  R2={metrics['R2']:.4f}")

    # ── Classification: outperforms Nifty 500 over 20d ─────────────────────────
    y_train_cls = train_df["target_outperform"].values
    y_test_cls  = test_df["target_outperform"].values

    valid_train_cls = ~np.isnan(y_train_cls)
    valid_test_cls  = ~np.isnan(y_test_cls)

    clf = HistGradientBoostingClassifier(
        max_iter=200,
        max_depth=4,
        learning_rate=0.05,
        min_samples_leaf=20,
        random_state=42,
    )
    clf.fit(X_train[valid_train_cls], y_train_cls[valid_train_cls])
    joblib.dump(clf, MODELS_DIR / "model_outperform_clf.pkl")

    cls_preds = clf.predict(X_test[valid_test_cls])
    cls_proba = clf.predict_proba(X_test[valid_test_cls])[:, 1]
    acc  = accuracy_score(y_test_cls[valid_test_cls], cls_preds)
    auc  = roc_auc_score(y_test_cls[valid_test_cls], cls_proba)

    cls_metrics = {
        "model": "classification_outperform_20d",
        "train_samples": int(valid_train_cls.sum()),
        "test_samples":  int(valid_test_cls.sum()),
        "accuracy": round(float(acc), 4),
        "roc_auc":  round(float(auc), 4),
        "trained_at": datetime.now().isoformat(),
    }
    all_metrics.append(cls_metrics)
    logger.info(f"[outperform_clf] Accuracy={cls_metrics['accuracy']:.4f}  AUC={cls_metrics['roc_auc']:.4f}")

    # Save metrics
    with open(METRICS_FILE, "w") as f:
        json.dump(all_metrics, f, indent=2)

    # Generate predictions with fresh models
    _generate_and_save_predictions(latest_features)

    logger.info("All models trained and saved.")
    return {"metrics": all_metrics, "stocks_with_predictions": len(latest_features)}


# ─── Prediction Generation ────────────────────────────────────────────────────

def _generate_and_save_predictions(latest_features: dict) -> None:
    """Score all stocks with the trained models and save to JSON."""
    if not latest_features:
        logger.warning("No latest features available for prediction.")
        return

    try:
        scaler   = joblib.load(MODELS_DIR / "scaler.pkl")
        model_1d = joblib.load(MODELS_DIR / "model_1d.pkl")
        model_1w = joblib.load(MODELS_DIR / "model_1w.pkl")
        model_1m = joblib.load(MODELS_DIR / "model_1m.pkl")
        clf_out  = joblib.load(MODELS_DIR / "model_outperform_clf.pkl")
    except Exception as e:
        logger.error(f"Cannot load models for prediction: {e}")
        return

    symbols = list(latest_features.keys())
    X_raw = np.array([[latest_features[s].get(c, 0) for c in FEATURE_COLS] for s in symbols])
    X = scaler.transform(X_raw)

    pred_1d = model_1d.predict(X)
    pred_1w = model_1w.predict(X)
    pred_1m = model_1m.predict(X)
    outperform_proba = clf_out.predict_proba(X)[:, 1]
    is_outperformer  = clf_out.predict(X)

    # Percentile rank → 0-100 score
    rank_1d = pd.Series(pred_1d).rank(pct=True).values * 100
    rank_1w = pd.Series(pred_1w).rank(pct=True).values * 100
    rank_1m = pd.Series(pred_1m).rank(pct=True).values * 100

    predictions = {}
    for i, symbol in enumerate(symbols):
        predictions[symbol] = {
            # Percentile scores (0-100)
            "ml_1d_score": round(float(rank_1d[i]), 1),
            "ml_1w_score": round(float(rank_1w[i]), 1),
            "ml_1m_score": round(float(rank_1m[i]), 1),
            # Raw predicted returns
            "predicted_return_1d": round(float(pred_1d[i]) * 100, 3),
            "predicted_return_1w": round(float(pred_1w[i]) * 100, 3),
            "predicted_return_1m": round(float(pred_1m[i]) * 100, 3),
            # Outperformance classification
            "outperform_probability": round(float(outperform_proba[i]), 3),
            "is_likely_outperformer": bool(is_outperformer[i]),
            "generated_at": datetime.now().isoformat(),
        }

    with open(PREDICTIONS_FILE, "w") as f:
        json.dump(predictions, f, indent=2)

    logger.info(f"Predictions saved for {len(predictions)} stocks.")


def generate_predictions():
    """Public entry point: generate fresh predictions from saved models (no retrain)."""
    store = DataStore()
    data = build_dataset(store)
    _generate_and_save_predictions(data["latest_features"])


def get_ml_predictions() -> dict:
    """Return saved predictions. Fast — reads JSON file, no DB query."""
    if PREDICTIONS_FILE.exists():
        with open(PREDICTIONS_FILE) as f:
            return json.load(f)
    return {}


def get_ml_metrics() -> list:
    """Return last training metrics."""
    if METRICS_FILE.exists():
        with open(METRICS_FILE) as f:
            return json.load(f)
    return []


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    train_models()
