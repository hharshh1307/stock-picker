import pandas as pd
import numpy as np
import joblib
from datetime import timedelta
from sklearn.preprocessing import RobustScaler

from config import DATA_DIR
from data_store import DataStore
from ml_pipeline import extract_features_targets, MODELS_DIR

def run_simulation(frequency: str, iterations: int = 10, top_n: int = 5) -> dict:
    """
    Run a historical simulation of the strategy.
    For each past iteration, it uses the ML model to pick the top_n stocks,
    simulates buying them, holding for the frequency period, and selling.
    """
    print(f"Running historical simulation for {frequency} over {iterations} iterations...")
    
    freq_map = {
        "Daily": 1,
        "Weekly": 5,
        "Monthly": 20,
        "Yearly": 252
    }
    
    model_map = {
        "Daily": "1d",
        "Weekly": "1w",
        "Monthly": "1m",
        "Yearly": "1y"
    }
    
    days_to_hold = freq_map.get(frequency, 5)
    model_name = model_map.get(frequency, "1w")
    
    try:
        model = joblib.load(MODELS_DIR / f"model_{model_name}.pkl")
        scaler = joblib.load(MODELS_DIR / "scaler.pkl")
    except Exception as e:
        return {"error": f"ML models not trained yet. {e}"}
        
    store = DataStore()
    stocks = store.get_all_stocks()
    
    # We need to build a dataframe of all stocks, predicting back in time.
    # To do this efficiently, we'll grab the last (iterations * days_to_hold + days_to_hold + 90) days of data
    days_needed = (iterations * days_to_hold) + 120
    
    simulation_results = []
    
    all_stock_dfs = {}
    for stock in stocks:
        prices = store.get_price_series(stock.symbol, days=days_needed)
        if len(prices) < 100:
            continue
        df = pd.DataFrame(prices)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # We only need the features and the forward targets
        feat_df = extract_features_targets(df)
        if len(feat_df) == 0:
            continue
            
        all_stock_dfs[stock.symbol] = feat_df

    if not all_stock_dfs:
        return {"error": "Not enough historical data to run simulation."}
        
    # Get a common date index (using the first valid stock)
    sample_df = list(all_stock_dfs.values())[0]
    valid_dates = sample_df['date'].tolist()
    
    if len(valid_dates) < iterations * days_to_hold:
        return {"error": "Not enough overlapping dates to run requested iterations."}
        
    feature_cols = ['ret_1d', 'ret_5d', 'ret_20d', 'ret_90d', 'vol_20d', 'dist_sma_20', 'dist_sma_50', 'vol_ratio']
    target_col = f'target_{model_name}'
    
    # Walk backward from the most recent valid date that has a known forward target
    # Wait, the target is known if date is before (today - days_to_hold)
    # We will just iterate through the last N dates separated by days_to_hold
    
    # The last date in the dataframe has NaN for the target. We need dates where the target is NOT NaN.
    available_dates_for_sim = sample_df.dropna(subset=[target_col])['date'].tolist()
    
    if len(available_dates_for_sim) < iterations * days_to_hold:
        # Fallback if we don't have enough data
        dates_to_test = available_dates_for_sim[-(iterations):]
    else:
        # Step back by days_to_hold to simulate sequential non-overlapping trades
        dates_to_test = available_dates_for_sim[-(iterations * days_to_hold)::days_to_hold]
        
    if not dates_to_test:
        return {"error": "No valid historical periods found for simulation."}

    total_trades = 0
    winning_trades = 0
    all_gains = []
    
    period_logs = []
    
    for sim_date in dates_to_test:
        # For this date, gather features for all stocks
        period_features = []
        period_symbols = []
        actual_returns = []
        
        for symbol, df in all_stock_dfs.items():
            row = df[df['date'] == sim_date]
            if len(row) > 0 and not pd.isna(row.iloc[0][target_col]):
                features = row.iloc[0][feature_cols].values
                period_features.append(features)
                period_symbols.append(symbol)
                actual_returns.append(row.iloc[0][target_col])
                
        if not period_features:
            continue
            
        X = np.array(period_features)
        X_scaled = scaler.transform(X)
        preds = model.predict(X_scaled)
        
        # Rank by predictions
        ranked_indices = np.argsort(preds)[::-1][:top_n]
        
        period_gain = 0
        picks = []
        for idx in ranked_indices:
            ret = actual_returns[idx] * 100 # Convert to percentage
            period_gain += ret
            all_gains.append(ret)
            total_trades += 1
            if ret > 0:
                winning_trades += 1
                
            picks.append({
                "symbol": period_symbols[idx],
                "predicted_score": float(preds[idx]),
                "actual_gain_pct": round(float(ret), 2)
            })
            
        avg_period_gain = period_gain / len(ranked_indices)
        
        period_logs.append({
            "date": sim_date.strftime("%Y-%m-%d"),
            "average_gain_pct": round(float(avg_period_gain), 2),
            "top_picks": picks
        })
        
    if not all_gains:
        return {"error": "Simulation failed to execute any trades."}
        
    avg_total_gain = sum(all_gains) / len(all_gains)
    max_gain = max(all_gains)
    max_drawdown = min(all_gains)
    win_rate = (winning_trades / total_trades) * 100
    
    # Calculate compounded return
    # Assuming equal weight portfolio reinvested every period
    compounded_growth = 1.0
    for p in period_logs:
        compounded_growth *= (1 + (p["average_gain_pct"] / 100))
        
    total_compounded_return = (compounded_growth - 1) * 100
    
    return {
        "frequency": frequency,
        "iterations_tested": len(dates_to_test),
        "total_trades_simulated": total_trades,
        "win_rate_pct": round(win_rate, 1),
        "average_gain_per_trade_pct": round(avg_total_gain, 2),
        "max_single_trade_gain_pct": round(max_gain, 2),
        "worst_single_trade_loss_pct": round(max_drawdown, 2),
        "total_compounded_strategy_return_pct": round(total_compounded_return, 2),
        "period_logs": period_logs
    }

if __name__ == "__main__":
    import json
    res = run_simulation("Weekly", 10)
    print(json.dumps(res, indent=2))
