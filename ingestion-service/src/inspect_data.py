from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

file_path = (
    ROOT / "data" / "raw"/
    "AAPL_2012-06-21_34200000_57600000_message_1.csv"
)

columns = [
    "time",
    "event_type",
    "order_id",
    "size",
    "price",
    "direction",
]

df =pd.read_csv(file_path, header= None, names=columns)

print("DATASET SUMMARY")
print("-" *40)
print("Total records:",len(df))
print("Total Columns:", len(df.columns))
print("Exact duplicate rows:", df.duplicated().sum())

print("\nEvent type counts:")
print(df["event_type"].value_counts().sort_index())

print("\nDirection counts: ")
print(df["direction"].value_counts(dropna=False))

print("\nMissing values:")
print(df.isna().sum())



print("\nFirst five records: ")
print(df.head())

print("\nPrice range in source units:")
print(df["price"].min(),"to", df["price"].max())
