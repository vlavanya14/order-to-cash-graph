#!/usr/bin/env python3
"""
Helper script to organize your downloaded JSONL folders into the backend/data directory.
Run this from the project root: python setup_data.py <path_to_your_downloaded_data>
"""
import os
import shutil
import sys

EXPECTED_FOLDERS = [
    "billing_document_cancellations",
    "billing_document_headers",
    "billing_document_items",
    "business_partner_addresses",
    "business_partners",
    "customer_company_assignments",
    "customer_sales_area_assignments",
    "journal_entry_items_accounts_receivable",
    "outbound_delivery_headers",
    "outbound_delivery_items",
    "payments_accounts_receivable",
    "plants",
    "product_descriptions",
    "product_plants",
    "product_storage_locations",
    "products",
    "sales_order_headers",
    "sales_order_items",
    "sales_order_schedule_lines",
]

def setup_data(source_dir):
    dest_dir = os.path.join("backend", "data")
    os.makedirs(dest_dir, exist_ok=True)

    found = []
    missing = []

    for folder in EXPECTED_FOLDERS:
        # Try exact match or partial match
        src = os.path.join(source_dir, folder)
        
        # Try to find with partial name match (e.g. journal_entry_items_accounts_receivab...)
        if not os.path.exists(src):
            for item in os.listdir(source_dir):
                if item.startswith(folder[:20]):
                    src = os.path.join(source_dir, item)
                    break

        if os.path.exists(src):
            dest = os.path.join(dest_dir, folder)
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
            files = len([f for f in os.listdir(dest) if f.endswith(".jsonl")])
            print(f"  ✅ {folder} ({files} files)")
            found.append(folder)
        else:
            print(f"  ⚠️  Not found: {folder}")
            missing.append(folder)

    print(f"\n✅ Copied {len(found)} folders to backend/data/")
    if missing:
        print(f"⚠️  Missing {len(missing)} folders: {missing}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python setup_data.py <path_to_downloaded_data_directory>")
        print("Example: python setup_data.py ~/Downloads/order_to_cash_data")
        sys.exit(1)
    
    source = sys.argv[1]
    if not os.path.exists(source):
        print(f"❌ Directory not found: {source}")
        sys.exit(1)

    print(f"📦 Setting up data from: {source}")
    setup_data(source)
