import pandas as pd
import sqlite3
import glob
import os

# Database file
db_file = "doe_contracts.db"
data_dir = "data"

# Important columns to keep (out of 200+)
cols_to_keep = [
    "contract_transaction_unique_key",
    "award_id_piid",
    "action_date",
    "action_date_fiscal_year",
    "federal_action_obligation",
    "total_dollars_obligated",
    "awarding_agency_name",
    "awarding_sub_agency_name",
    "recipient_name",
    "recipient_city_name",
    "recipient_state_name",
    "primary_place_of_performance_city_name",
    "primary_place_of_performance_state_name",
    "transaction_description",
    "product_or_service_code_description",
    "naics_description",
    "award_type",
    "extent_competed"
]

def ingest_data():
    conn = sqlite3.connect(db_file)
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    
    # Sort files to process in chronological order
    csv_files.sort()
    
    print(f"Found {len(csv_files)} files. Starting ingestion...")
    
    for i, file in enumerate(csv_files):
        print(f"[{i+1}/{len(csv_files)}] Processing {os.path.basename(file)}...")
        
        # Read only specific columns to save memory
        # We use low_memory=False to avoid DtypeWarning
        df = pd.read_csv(file, usecols=lambda x: x in cols_to_keep, low_memory=False)
        
        # Ensure action_date is datetime
        df['action_date'] = pd.to_datetime(df['action_date'], errors='coerce')
        
        # Append to SQLite
        # If it's the first file, replace the table (to ensure clean start)
        if i == 0:
            df.to_sql("contracts", conn, if_exists="replace", index=False)
        else:
            df.to_sql("contracts", conn, if_exists="append", index=False)
            
    # Create indexes for faster querying
    print("Creating indexes...")
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_award_id ON contracts(award_id_piid)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipient ON contracts(recipient_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fy ON contracts(action_date_fiscal_year)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agency ON contracts(awarding_agency_name)")
    
    conn.commit()
    conn.close()
    print("Ingestion complete.")

if __name__ == "__main__":
    ingest_data()
