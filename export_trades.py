"""
Export Delta Exchange Trades to Excel (Desktop) - Basic
"""

import pandas as pd
import os
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

print("\n[Creating Excel file...]")

# Read the CSV
csv_file = 'delta_exchange_trades.csv'
if not os.path.exists(csv_file):
    print(f"ERROR: {csv_file} not found. Run delta_exchange_fees.py first.")
    exit(1)

trades_df = pd.read_csv(csv_file)

# Get Desktop path
desktop = Path.home() / "Desktop"
excel_file = desktop / "RSI_30_70_Trades_Jan_Apr_2026.xlsx"

print(f"[Reading trades from {csv_file}...]")
print(f"[Total trades: {len(trades_df)}]")

# Try multiple engines
engines_to_try = ['openpyxl', 'xlsxwriter', 'xlwt']

for engine in engines_to_try:
    try:
        print(f"[Attempting with engine: {engine}]")
        
        # Create Excel file
        with pd.ExcelWriter(excel_file, engine=engine) as writer:
            trades_df.to_excel(writer, sheet_name='Trades', index=False)
        
        print(f"[Excel file created successfully!]")
        print(f"[Location: {excel_file}]")
        print(f"[Total trades exported: {len(trades_df)}]")
        print(f"\nOK - File saved to Desktop: RSI_30_70_Trades_Jan_Apr_2026.xlsx\n")
        break
    
    except Exception as e:
        print(f"[{engine} failed: {str(e)[:60]}]")
        continue

else:
    print("\nERROR: No Excel engine available. Trying CSV export instead...")
    csv_output = desktop / "RSI_30_70_Trades_Jan_Apr_2026.csv"
    trades_df.to_csv(csv_output, index=False)
    print(f"CSV file saved to: {csv_output}\n")
