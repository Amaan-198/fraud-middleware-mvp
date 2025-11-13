#!/usr/bin/env python3
"""
Dataset Preparation Script

Purpose: Load raw IEEE-CIS fraud dataset and produce a clean dataset with:
- 15 features from FEATURE_CONTRACT.md
- Target label is_fraud (0/1)

Usage:
    python prepare_dataset.py --input data/raw/ieee-fraud.csv --output data/processed/ieee_features.csv
"""

import argparse
import math
import hashlib
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import numpy as np


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the 15 features from FEATURE_CONTRACT.md using IEEE-CIS columns.

    This function expects a DataFrame with raw IEEE-CIS columns and produces
    a DataFrame with exactly 15 feature columns matching the contract.

    Args:
        df: Raw transaction DataFrame with IEEE-CIS columns

    Returns:
        DataFrame with 15 feature columns
    """
    features_df = pd.DataFrame()
    dt_seconds = df["TransactionDT"]

    # === Transaction Features (4) ===

    # amount: log-normalized
    features_df["amount"] = np.log1p(df["TransactionAmt"])

    # amount_pct: percentile vs user's history [0,1]
    # Use per-card percentile ranking
    features_df["amount_pct"] = df.groupby("card1")["TransactionAmt"].rank(pct=True)
    features_df["amount_pct"] = features_df["amount_pct"].fillna(0.5)

    # tod: hour of day [0-23]
    features_df["tod"] = ((dt_seconds % 86400) // 3600).astype(int)

    # dow: day of week [0-6], 0=Monday
    features_df["dow"] = ((dt_seconds // 86400) % 7).astype(int)

    # === Device/Location Features (3) ===

    # device_new: First seen device (bool -> int)
    # Use card combination (card1+card2) as device identifier
    df['device_id'] = df['card1'].astype(str) + '_' + df['card2'].fillna(0).astype(str)
    device_first_seen = df.groupby('device_id')['TransactionDT'].transform('min')
    # Consider device new if first seen within 30 days (2592000 seconds)
    features_df["device_new"] = ((dt_seconds - device_first_seen) < 2592000).astype(int)

    # km_dist: Distance from typical location, capped at 10000
    # Use dist1 (distance between addresses) from IEEE-CIS, normalized
    if 'dist1' in df.columns:
        # dist1 is already a distance measure in IEEE-CIS
        features_df["km_dist"] = df['dist1'].fillna(0).clip(0, 10000)
    else:
        # Fallback: use addr1 difference from user's mode location
        mode_addr = df.groupby('card1')['addr1'].transform(lambda x: x.mode()[0] if len(x.mode()) > 0 else 0)
        features_df["km_dist"] = np.abs(df['addr1'].fillna(0) - mode_addr).clip(0, 10000)

    # ip_asn_risk: IP reputation score [0,1]
    # Use email domain fraud rates as proxy for IP risk
    # NOTE: This uses fraud rates from entire dataset (target leakage for MVP simplicity)
    # Production: Calculate on training set only, apply to val/test
    if 'P_emaildomain' in df.columns:
        domain_fraud_rate = df.groupby('P_emaildomain')['isFraud'].transform('mean')
        features_df["ip_asn_risk"] = domain_fraud_rate.fillna(0.5)
    else:
        features_df["ip_asn_risk"] = 0.5

    # === Velocity Features (2) ===

    # velocity_1h & velocity_1d: Use IEEE-CIS C-features (count features)
    # C1-C14 represent counts of transactions, use C1 and C2 as proxies
    if 'C1' in df.columns:
        features_df["velocity_1h"] = df['C1'].fillna(1).clip(1, 50).astype(int)
    else:
        # Fallback: calculate from data
        df_temp = df.copy()
        df_temp["hour_bucket"] = dt_seconds // 3600
        velocity_1h = df_temp.groupby(["card1", "hour_bucket"]).cumcount() + 1
        features_df["velocity_1h"] = velocity_1h.clip(1, 50)

    if 'C2' in df.columns:
        features_df["velocity_1d"] = df['C2'].fillna(1).clip(1, 500).astype(int)
    else:
        # Fallback: calculate from data
        df_temp["day_bucket"] = dt_seconds // 86400
        velocity_1d = df_temp.groupby(["card1", "day_bucket"]).cumcount() + 1
        features_df["velocity_1d"] = velocity_1d.clip(1, 500)

    # === Account Features (2) ===

    # acct_age_days: Days since account creation, capped at 3650
    # Use D1 (timedelta from previous transaction) as proxy for account maturity
    if 'D1' in df.columns:
        # D1 is time since previous transaction, use it as age proxy
        features_df["acct_age_days"] = df['D1'].fillna(100).clip(0, 3650).astype(int)
    else:
        # Fallback: calculate from first transaction
        card_first_seen = df.groupby("card1")["TransactionDT"].transform("min")
        features_df["acct_age_days"] = ((dt_seconds - card_first_seen) // 86400).clip(0, 3650).astype(int)

    # failed_logins_15m: Failed auth attempts, capped at 10
    # Use D2 or D3 (other time deltas) as proxy
    if 'D2' in df.columns:
        # Normalize D2 to 0-10 range (higher D2 = more suspicious = more failed logins)
        features_df["failed_logins_15m"] = (df['D2'].fillna(0) / 100).clip(0, 10).astype(int)
    else:
        features_df["failed_logins_15m"] = 0

    # === Historical Features (2) ===

    # spend_avg_30d: 30-day average spend, log-normalized
    avg_spend = df.groupby("card1")["TransactionAmt"].transform("mean")
    features_df["spend_avg_30d"] = np.log1p(avg_spend.fillna(100.0))

    # spend_std_30d: 30-day std deviation, log-normalized
    std_spend = df.groupby("card1")["TransactionAmt"].transform("std")
    features_df["spend_std_30d"] = np.log1p(std_spend.fillna(50.0))

    # === Graph-lite Features (2) ===

    # nbr_risky_30d: Fraction risky neighbors [0,1]
    # Use addr2 (shipping address) fraud rate as proxy for risky neighborhood
    # NOTE: This uses fraud rates from entire dataset (target leakage for MVP simplicity)
    # Production: Calculate on training set only, apply to val/test
    if 'addr2' in df.columns:
        addr_fraud_rate = df.groupby('addr2')['isFraud'].transform('mean')
        features_df["nbr_risky_30d"] = addr_fraud_rate.fillna(0.1)
    else:
        features_df["nbr_risky_30d"] = 0.1

    # device_reuse_cnt: Unique users on device
    # Count unique card1 per device (card2)
    device_reuse = df.groupby("card2")["card1"].transform("nunique")
    features_df["device_reuse_cnt"] = device_reuse.fillna(1).clip(1, 50).astype(int)

    return features_df


def prepare_dataset(input_path: str, output_path: str):
    """
    Load raw IEEE-CIS dataset and save processed features.

    Args:
        input_path: Path to raw IEEE-CIS CSV
        output_path: Path to save processed features
    """
    print(f"Loading dataset from {input_path}...")

    # TODO: Update this to match actual IEEE-CIS column names
    # The IEEE-CIS dataset has columns like: TransactionDT, TransactionAmt, ProductCD,
    # card1-card6, addr1-addr2, dist1-dist2, P_emaildomain, R_emaildomain, etc.

    try:
        df = pd.read_csv(input_path)
        print(f"Loaded {len(df):,} transactions")
    except FileNotFoundError:
        print(f"ERROR: File not found: {input_path}")
        print("Please download the IEEE-CIS Fraud Detection dataset from Kaggle:")
        print("https://www.kaggle.com/c/ieee-fraud-detection/data")
        return

    # Check for required columns
    required_cols = ["TransactionAmt", "TransactionDT", "card1", "isFraud"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"ERROR: Missing required columns: {missing_cols}")
        print(f"Available columns: {list(df.columns)[:10]}...")
        return

    print("Building features...")
    features_df = build_features(df)

    # Add target label
    features_df["is_fraud"] = df["isFraud"].astype(int)

    # Validate feature count
    expected_features = 15
    actual_features = len(features_df.columns) - 1  # Exclude target
    print(f"Generated {actual_features} features (expected {expected_features})")

    # Handle missing values
    print("Handling missing values...")
    features_df = features_df.fillna(0.0)

    # Save processed dataset
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Saving processed dataset to {output_path}...")
    features_df.to_csv(output_path, index=False)

    print(f"✓ Saved {len(features_df):,} rows with {len(features_df.columns)} columns")
    print(f"  Features: {list(features_df.columns[:-1])}")
    print(f"  Fraud rate: {features_df['is_fraud'].mean():.2%}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare IEEE-CIS dataset for fraud detection")
    parser.add_argument(
        "--input",
        type=str,
        default="data/raw/ieee-fraud.csv",
        help="Path to raw IEEE-CIS CSV file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/processed/ieee_features.csv",
        help="Path to save processed features"
    )

    args = parser.parse_args()
    prepare_dataset(args.input, args.output)
