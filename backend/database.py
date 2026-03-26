import sqlite3
import json
import os
import glob

DB_PATH = "order_to_cash.db"
DATA_DIR = "./data"

# Maps folder name → table name
FOLDER_TABLE_MAP = {
    "sales_order_headers":                      "sales_order_headers",
    "sales_order_items":                        "sales_order_items",
    "sales_order_schedule_lines":               "sales_order_schedule_lines",
    "outbound_delivery_headers":                "outbound_delivery_headers",
    "outbound_delivery_items":                  "outbound_delivery_items",
    "billing_document_headers":                 "billing_document_headers",
    "billing_document_items":                   "billing_document_items",
    "billing_document_cancellations":           "billing_document_cancellations",
    "journal_entry_items_accounts_receivable":  "journal_entries",
    "payments_accounts_receivable":             "payments",
    "business_partners":                        "business_partners",
    "business_partner_addresses":               "business_partner_addresses",
    "customer_company_assignments":             "customer_company_assignments",
    "customer_sales_area_assignments":          "customer_sales_area_assignments",
    "products":                                 "products",
    "product_descriptions":                     "product_descriptions",
    "plants":                                   "plants",
    "product_plants":                           "product_plants",
    "product_storage_locations":                "product_storage_locations",
}

def get_connection():
    return sqlite3.connect(DB_PATH)

def load_jsonl_folder(conn, folder_path, table_name):
    """Load all JSONL files in a folder into a SQLite table."""
    jsonl_files = glob.glob(os.path.join(folder_path, "*.jsonl"))
    if not jsonl_files:
        print(f"  ⚠️  No JSONL files in {folder_path}")
        return 0

    all_records = []
    for filepath in jsonl_files:
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        # Flatten nested dicts (e.g. creationTime: {hours, minutes, seconds})
                        flat = {}
                        for k, v in record.items():
                            if isinstance(v, dict):
                                flat[k] = json.dumps(v)
                            else:
                                flat[k] = v
                        all_records.append(flat)
                    except json.JSONDecodeError:
                        continue

    if not all_records:
        return 0

    # Get all unique keys
    all_keys = list(all_records[0].keys())

    # Create table
    cols_def = ", ".join(f'"{k}" TEXT' for k in all_keys)
    conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
    conn.execute(f'CREATE TABLE "{table_name}" ({cols_def})')

    # Insert records
    placeholders = ", ".join("?" for _ in all_keys)
    col_names = ", ".join(f'"{k}"' for k in all_keys)
    for record in all_records:
        values = [str(record.get(k, "")) if record.get(k) is not None else None for k in all_keys]
        conn.execute(f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})', values)

    conn.commit()
    return len(all_records)

def load_all_data():
    """Load all folders from DATA_DIR into SQLite."""
    conn = get_connection()
    print("📦 Loading data into SQLite...")

    for folder_name, table_name in FOLDER_TABLE_MAP.items():
        folder_path = os.path.join(DATA_DIR, folder_name)
        if os.path.exists(folder_path):
            count = load_jsonl_folder(conn, folder_path, table_name)
            print(f"  ✅ {folder_name} → {table_name} ({count} records)")
        else:
            print(f"  ⚠️  Folder not found: {folder_path}")

    conn.close()
    print("✅ All data loaded!\n")

def get_schema():
    """Returns schema dict for LLM prompt."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    schema = {}
    for (table,) in tables:
        cursor.execute(f'PRAGMA table_info("{table}")')
        cols = cursor.fetchall()
        schema[table] = [col[1] for col in cols]

    conn.close()
    return schema

def db_exists():
    return os.path.exists(DB_PATH)
