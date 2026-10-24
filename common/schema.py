PIPELINE_VERSION = "1.0.0"

RAW_COLUMNS = ["time", "event_type", "order_id", "size", "price", "direction"]
BUSINESS_COLUMNS = RAW_COLUMNS

PRICE_SCALE = 10000
SECONDS_PER_DAY = 86400
HALT_EVENT_TYPE = 7

EVENT_LABELS = {
    1: "SUBMIT",
    2: "CANCEL_PARTIAL",
    3: "DELETE",
    4: "EXECUTE_VISIBLE",
    5: "EXECUTE_HIDDEN",
    6: "CROSS_TRADE",
    7: "HALT",
}

VALID_EVENT_TYPES = sorted(EVENT_LABELS)

INGESTED_COLUMNS = [
    "source_record_number",
    *RAW_COLUMNS,
    "source_file",
    "trading_date",
    "file_sha256",
    "batch_id",
    "ingestion_timestamp",
]

TRANSFORMED_COLUMNS = [
    *INGESTED_COLUMNS,
    "price_dollars",
    "event_timestamp",
    "event_label",
    "is_duplicate",
    "pipeline_version",
    "transformations_applied",
    "transformed_at",
]

REQUIRED_LINEAGE_COLUMNS = [
    "source_record_number",
    "source_file",
    "file_sha256",
    "batch_id",
]