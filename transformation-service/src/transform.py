from pathlib import Path
import pandas as pd

ROOT =Path(__file__).resolve().parents[2]

INPUT_FILE =ROOT / "data" / "processed" / "ingested_messages.csv"
OUTPUT_DIR =ROOT /"data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "transformed_messages.csv"
REJECTED_FILE =ROOT / "data" / "rejected" / "rejected_messages.csv"

def transform_data():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    df =pd.read_csv(INPUT_FILE)
    original_count =len(df)

    required_columns =[
        "source_record_number", "time", "event_type",
        "order_id", "size" , "price", "direction"

    ]

    missing_columns =[
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(f"Missing columns: {missing_columns}")

    numeric_columns =[
        "time", "event_type", "order_id",
        "size", "price", "direction"
    ]

    for column in numeric_columns:
        df[column]=pd.to_numeric(df[column],errors="coerce")


    valid =(
        df[numeric_columns].notna().all(axis=1)
        & (df["time"]>=0)
        & (df["event_type"].isin([1,2,3,4,5]))
        & (df["size"]>0)
        & (df["price"]>=0)
        & (df["direction"].isin([-1,1]))
    )

    rejected = df.loc[~valid].copy()
    clean = df.loc[valid].copy()

    clean ["price_dollars"] =clean["price"]/10000

    OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
    REJECTED_FILE.parent.mkdir(parents=True,exist_ok=True)

    clean.to_csv(OUTPUT_FILE, index=False)
    rejected.to_csv(REJECTED_FILE,index=False)

    print("TRANSFORMATION COMPLETED")
    print("-"*35)
    print("Input records:",original_count)
    print("Valid records:", len(clean))
    print("Rejected records:",len(rejected))
    print("Output file:",OUTPUT_FILE)
    print("Rejected file:", REJECTED_FILE)

if __name__ == "__main__":
    transform_data()
    