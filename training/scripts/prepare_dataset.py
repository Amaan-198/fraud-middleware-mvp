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
    Build the 15 features from FEATURE_CONTRACT.md.

    This function expects a DataFrame with raw IEEE-CIS columns and produces
    a DataFrame with exactly 15 feature columns matching the contract.

    Args:
        df: Raw transaction DataFrame with columns:
            - TransactionAmt: float (transaction amount)
            - TransactionDT: int (timestamp seconds from epoch)
            - card1-card6: card identifiers
            - addr1, addr2: location identifiers
            - P_emaildomain, R_emaildomain: email domains
            - DeviceInfo, DeviceType: device information
            - ... (other IEEE-CIS columns)

    Returns:
        DataFrame with 15 feature columns
    """
    features_df = pd.DataFrame()

    # === Transaction Features (4) ===

    # amount: log-normalized
    features_df["amount"] = np.log1p(df["TransactionAmt"])

    # amount_pct: percentile vs user's 30d history [0,1]
    # TODO: Implement proper rolling percentile calculation
    # For now, use simple global percentile as proxy
    features_df["amount_pct"] = df["TransactionAmt"].rank(pct=True)

    # tod: hour of day [0-23]
    # TransactionDT is seconds from epoch, convert to hour of day
    dt_seconds = df["TransactionDT"]
    features_df["tod"] = ((dt_seconds % 86400) // 3600).astype(int)

    # dow: day of week [0-6], 0=Monday
    # Convert to day of week (TransactionDT starts at some epoch)
    features_df["dow"] = ((dt_seconds // 86400) % 7).astype(int)

    # === Device/Location Features (3) ===

    # device_new: First seen in 30d (bool -> int)
    # TODO: Implement proper device first-seen logic with 30d window
    # For now, use simple heuristic: assume new if DeviceInfo is present and rare
    device_counts = df["card1"].map(df["card1"].value_counts())
    features_df["device_new"] = (device_counts <= 2).astype(int)

    # km_dist: Distance from mode location, capped at 10000
    # TODO: Calculate actual geographic distance if lat/lon available
    # For now, use addr1 as proxy for location distance
    if "addr1" in df.columns:
        mode_addr = df["addr1"].mode()[0] if len(df["addr1"].mode()) > 0 else 0
        features_df["km_dist"] = np.abs(df["addr1"].fillna(0) - mode_addr).clip(0, 10000)
    else:
        features_df["km_dist"] = 0

    # ip_asn_risk: IP reputation score [0,1]
    # TODO: Map actual IP/ASN to risk scores
    # For now, use hash-based mock from email domain
    def email_risk(email):
        if pd.isna(email):
            return 0.5
        email_hash = int(hashlib.md5(str(email).encode()).hexdigest(), 16)
        return (email_hash % 100) / 100.0

    features_df["ip_asn_risk"] = df.get("P_emaildomain", pd.Series([None] * len(df))).apply(email_risk)

    # === Velocity Features (2) ===

    # velocity_1h: Transaction count last hour, capped at 50
    # TODO: Implement proper rolling window velocity
    # For now, count transactions per card1 in each hour bucket
    df_temp = df.copy()
    df_temp["hour_bucket"] = dt_seconds // 3600
    velocity_1h = df_temp.groupby(["card1", "hour_bucket"]).size()
    features_df["velocity_1h"] = df_temp.set_index(["card1", "hour_bucket"]).index.map(
        lambda x: min(velocity_1h.get(x, 1), 50)
    ).values

    # velocity_1d: Transaction count last day, capped at 500
    df_temp["day_bucket"] = dt_seconds // 86400
    velocity_1d = df_temp.groupby(["card1", "day_bucket"]).size()
    features_df["velocity_1d"] = df_temp.set_index(["card1", "day_bucket"]).index.map(
        lambda x: min(velocity_1d.get(x, 1), 500)
    ).values

    # === Account Features (2) ===

    # acct_age_days: Days since account creation, capped at 3650
    # TODO: Use actual account creation date if available
    # For now, use first transaction as proxy for account age
    card_first_seen = df.groupby("card1")["TransactionDT"].transform("min")
    features_df["acct_age_days"] = ((dt_seconds - card_first_seen) // 86400).clip(0, 3650).astype(int)

    # failed_logins_15m: Failed auth attempts, capped at 10
    # IEEE-CIS doesn't have this field, use mock value
    features_df["failed_logins_15m"] = 0

    # === Historical Features (2) ===

    # spend_avg_30d: 30-day average spend, log-normalized
    # TODO: Implement proper 30d rolling average per user
    # For now, use global average as proxy
    avg_spend = df.groupby("card1")["TransactionAmt"].transform("mean")
    features_df["spend_avg_30d"] = np.log1p(avg_spend.fillna(100.0))

    # spend_std_30d: 30-day std deviation, log-normalized
    std_spend = df.groupby("card1")["TransactionAmt"].transform("std")
    features_df["spend_std_30d"] = np.log1p(std_spend.fillna(50.0))

    # === Graph-lite Features (2) ===

    # nbr_risky_30d: Fraction risky neighbors [0,1]
    # Mock for MVP as specified in contract
    features_df["nbr_risky_30d"] = 0.1

    # device_reuse_cnt: Unique users on device
    # Count unique card1 per device (using card2 as device proxy)
    device_reuse = df.groupby("card2")["card1"].transform("nunique")
    features_df["device_reuse_cnt"] = device_reuse.fillna(1).astype(int)

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
