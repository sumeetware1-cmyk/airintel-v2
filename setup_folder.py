import pandas as pd
import os

# ============================================================
# 1. CREATE FOLDER STRUCTURE
# ============================================================
os.makedirs('data/raw', exist_ok=True)
os.makedirs('data/cleaned', exist_ok=True)
os.makedirs('data/output', exist_ok=True)

print("[*] Created folders: data/raw, data/cleaned, data/output")

# ============================================================
# 2. LOAD YOUR NEW COMBINED DATASET
# ============================================================
source_file = 'Vedanti-Sumeet_data_with_Akasa.csv'
if not os.path.exists(source_file):
    raise FileNotFoundError(f"Could not find {source_file}. Make sure it's in your project folder!")

df = pd.read_csv(source_file, low_memory=False)

# ============================================================
# 3. POPULATE RAW FOLDER
# ============================================================
raw_path = 'data/raw/airfare_collected.csv'
df.to_csv(raw_path, index=False, encoding='utf-8-sig')
print(f"[+] Saved raw backup to: {raw_path}")

# ============================================================
# 4. POPULATE CLEANED FOLDER
# ============================================================
# Drop empty or invalid pricing rows
df_clean = df.dropna(subset=['total_fare', 'origin', 'destination', 'departure_date'])
cleaned_path = 'data/cleaned/airfare_collected_clean.csv'
df_clean.to_csv(cleaned_path, index=False, encoding='utf-8-sig')
print(f"[+] Saved cleaned dataset to: {cleaned_path} ({len(df_clean)} records)")

# ============================================================
# 5. POPULATE OUTPUT FOLDER (Pre-calculated Dashboard Summaries)
# ============================================================
# A. Route-wise APIx Summary Table
route_summary = df_clean.groupby(['origin', 'destination']).agg(
    observations=('total_fare', 'count'),
    average_fare=('total_fare', 'mean'),
    base_average_fare=('base_fare', lambda x: x.mean() if x.notna().sum() > 0 else 0)
).reset_index()

# Compute route index relative to overall average baseline (Base 100)
overall_mean = route_summary['average_fare'].mean()
route_summary['route_index'] = (route_summary['average_fare'] / overall_mean) * 100
route_summary['weight'] = 1 / len(route_summary)
route_summary.insert(0, 'collection_date', pd.Timestamp.today().strftime('%Y-%m-%d'))

route_output_path = 'data/output/apix_route_results.csv'
route_summary.to_csv(route_output_path, index=False, encoding='utf-8-sig')
print(f"[+] Generated route summary output: {route_output_path}")

# B. Lead-Time Analysis Summary Table
if 'advance_days' in df_clean.columns:
    lead_summary = df_clean.groupby('advance_days').agg(
        observations=('total_fare', 'count'),
        average_fare=('total_fare', 'mean')
    ).reset_index()
    
    lead_output_path = 'data/output/lead_time_analysis.csv'
    lead_summary.to_csv(lead_output_path, index=False, encoding='utf-8-sig')
    print(f"[+] Generated lead-time analysis output: {lead_output_path}")

print("\n" + "="*50)
print("SUCCESS! All folders and files are generated and ready for Git & Render.")
print("="*50)