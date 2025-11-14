import pandas as pd

print("Loading train_transaction.csv ...")
txn = pd.read_csv("data/raw/train_transaction.csv")

print("Loading train_identity.csv ...")
idt = pd.read_csv("data/raw/train_identity.csv")

print("Merging...")
df = txn.merge(idt, on="TransactionID", how="left")

output_path = "data/raw/ieee-fraud.csv"
df.to_csv(output_path, index=False)

print("Merged dataset saved to:", output_path)
print("Shape:", df.shape)
