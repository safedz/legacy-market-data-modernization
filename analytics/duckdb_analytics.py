import json
import os
import sys
from pathlib import Path
import duckdb
def sql_string(value):
    return "'" + value.replace("'", "''") + "'"
def main():
    source = os.getenv("ANALYTICS_SOURCE", "local").lower()
    extension_directory = Path(
        os.getenv("DUCKDB_EXTENSION_DIRECTORY", "../duckdb_extensions")
    ).resolve()
    connection = duckdb.connect(
        ":memory:",
        config={
            "extension_directory": str(extension_directory)
        }
    )
    try:
        if source == "local":
            if len(sys.argv) < 2:
                raise ValueError("Local mode requires a Parquet file path.")
            parquet_file = Path(sys.argv[1]).resolve()
            if not parquet_file.exists():
                raise FileNotFoundError(
                    f"Parquet file not found: {parquet_file}"
                )
            parquet_source = str(parquet_file)
        elif source == "r2":
            bucket = os.getenv("R2_BUCKET")
            account_id = os.getenv("R2_ACCOUNT_ID")
            access_key = os.getenv("R2_ACCESS_KEY_ID")
            secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
            object_key = os.getenv("R2_OBJECT_KEY")
            required = {
                "R2_BUCKET": bucket,
                "R2_ACCOUNT_ID": account_id,
                "R2_ACCESS_KEY_ID": access_key,
                "R2_SECRET_ACCESS_KEY": secret_key,
                "R2_OBJECT_KEY": object_key
            }
            missing = [
                name for name, value in required.items()
                if not value
            ]
            if missing:
                raise ValueError(
                    "Missing R2 environment variables: "
                    + ", ".join(missing)
                )
            connection.execute("LOAD httpfs")
            connection.execute(
                """
                CREATE OR REPLACE SECRET r2_secret (
                    TYPE r2,
                    KEY_ID {},
                    SECRET {},
                    ACCOUNT_ID {}
                )
                """.format(
                    sql_string(access_key),
                    sql_string(secret_key),
                    sql_string(account_id)
                )
            )
            parquet_source = f"r2://{bucket}/{object_key}"
        else:
            raise ValueError(
                f"Unsupported analytics source: {source}"
            )
        summary = connection.execute(
            """
            SELECT
                COUNT(*) AS total_records,
                ROUND(AVG(price_dollars), 4) AS average_price,
                MAX(price_dollars) AS highest_price,
                ROUND(AVG(size), 2) AS average_order_size,
                MAX(size) AS largest_order
            FROM read_parquet(?)
            """,
            [parquet_source]
        ).fetchone()
        events = connection.execute(
            """
            SELECT
                event_label,
                COUNT(*) AS record_count
            FROM read_parquet(?)
            GROUP BY event_label
            ORDER BY record_count DESC
            """,
            [parquet_source]
        ).fetchall()
        result = {
            "totalRecords": summary[0],
            "averagePrice": float(summary[1]) if summary[1] is not None else 0,
            "highestPrice": float(summary[2]) if summary[2] is not None else 0,
            "averageOrderSize": float(summary[3]) if summary[3] is not None else 0,
            "largestOrder": summary[4],
            "eventDistribution": [
                {"eventLabel": row[0], "count": row[1]}
                for row in events
            ]
        }
        print(json.dumps(result))
    finally:
        connection.close()
if __name__ == "__main__":
    main()
