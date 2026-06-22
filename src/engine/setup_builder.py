import pandas as pd
import sqlite3
import json
import os

def ingest_and_normalize(csv_path: str, json_path: str, db_path: str):
    """Parses CSV, normalizes relational data, and caches to SQLite."""
    
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Missing patch file: {json_path}. Run patch.py first.")
        
    with open(json_path, 'r', encoding='utf-8') as f:
        company_patch = json.load(f)

    print(f"Reading flat data from {csv_path}...")
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()
    df = df.fillna('') 

    def get_sub_label(comp: str) -> str:
        if not comp: return 'Independent'
        return str(comp).split('|')[0].strip().title()

    def get_parent_company(comp: str) -> str:
        if not comp: return 'Independent'
        primary = str(comp).split('|')[0].strip().lower()
        # Fallback to the sub-label if no parent exists in the patch
        return company_patch.get(primary, primary).title()

    # Create two distinct columns for the hierarchy
    df['Company_Sub'] = df['Company'].apply(get_sub_label)
    df['Company_Parent'] = df['Company'].apply(get_parent_company)

    # Clean Group strings
    df['Group'] = df['Group'].str.strip().str.title()
    df['Other Group'] = df['Other Group'].str.strip().str.title()
    df['Former Group'] = df['Former Group'].str.strip().str.title()

    # FIX 1: Explicitly state dayfirst=True to handle DD/MM/YYYY formatting silently
    df['Debut_Date'] = pd.to_datetime(df['Debut'], errors='coerce', dayfirst=True)
    df['Debut_Year'] = df['Debut_Date'].dt.year.fillna(0).astype(int)

    df = df.drop(columns=['Debut_Date'])

    print(f"Caching normalized data to {db_path}...")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    
    df.to_sql('idols', conn, if_exists='replace', index=False)
    
    cursor = conn.cursor()
    
    # FIX 2: Wrap "Group" in double quotes because it is a reserved SQL keyword
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_group ON idols("Group");')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_label ON idols("Company_Sub");')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_company ON idols("Company_Parent");')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_debut ON idols("Debut_Year");')
    
    conn.commit()
    conn.close()
    
    print(f"Success: Processed {len(df)} idols. Database ready for Adjacency List conversion.")

if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, "..", "data")
    
    csv_file = os.path.join(data_dir, "idols_full.csv")
    json_file = os.path.join(data_dir, "companies.json")
    db_file = os.path.join(data_dir, "processed_idols.db")
    
    ingest_and_normalize(csv_file, json_file, db_file)