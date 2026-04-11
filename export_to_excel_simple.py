"""
Export Delta Exchange Trades to Excel (Desktop) - Simple Version
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

# Create Excel writer
try:
    with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Write trades sheet
        trades_df.to_excel(writer, sheet_name='Trades', index=False)
        worksheet = writer.sheets['Trades']
        
        # Define formats
        header_format = workbook.add_format({
            'bg_color': '#366092',
            'font_color': 'white',
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        money_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'align': 'center',
            'border': 1
        })
        
        percent_format = workbook.add_format({
            'num_format': '0.00%',
            'align': 'center',
            'border': 1
        })
        
        center_format = workbook.add_format({
            'align': 'center',
            'border': 1
        })
        
        win_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'bg_color': '#C6EFCE',
            'font_color': '#006100',
            'bold': True,
            'align': 'center',
            'border': 1
        })
        
        loss_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'bg_color': '#FFC7CE',
            'font_color': '#9C0006',
            'bold': True,
            'align': 'center',
            'border': 1
        })
        
        # Write headers
        for col_num, value in enumerate(trades_df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Write data rows
        for row_num, row_data in enumerate(trades_df.values, 1):
            for col_num, value in enumerate(row_data):
                col_name = trades_df.columns[col_num]
                
                if col_name in ['Entry_Price', 'Exit_Price']:
                    worksheet.write(row_num, col_num, value, money_format)
                elif col_name in ['Gross_PnL', 'Entry_Cost', 'Exit_Cost', 'Total_Cost', 'Cumulative_PnL']:
                    worksheet.write(row_num, col_num, value, money_format)
                elif col_name == 'Net_PnL':
                    if value > 0:
                        worksheet.write(row_num, col_num, value, win_format)
                    elif value < 0:
                        worksheet.write(row_num, col_num, value, loss_format)
                    else:
                        worksheet.write(row_num, col_num, value, money_format)
                elif col_name == 'Return_%':
                    worksheet.write(row_num, col_num, value, percent_format)
                else:
                    worksheet.write(row_num, col_num, value, center_format)
        
        # Adjust column widths
        worksheet.set_column('A:A', 20)  # Date
        worksheet.set_column('B:B', 8)   # Type
        worksheet.set_column('C:C', 13)  # Entry_Price
        worksheet.set_column('D:D', 13)  # Exit_Price
        worksheet.set_column('E:E', 7)   # Result
        worksheet.set_column('F:F', 11)  # Entry_RSI
        worksheet.set_column('G:G', 10)  # Exit_RSI
        worksheet.set_column('H:H', 12)  # Gross_PnL
        worksheet.set_column('I:I', 12)  # Entry_Cost
        worksheet.set_column('J:J', 11)  # Exit_Cost
        worksheet.set_column('K:K', 12)  # Total_Cost
        worksheet.set_column('L:L', 12)  # Net_PnL
        worksheet.set_column('M:M', 10)  # Return_%
        worksheet.set_column('N:N', 13)  # Duration_hrs
        worksheet.set_column('O:O', 15)  # Cumulative_PnL
        
        # Freeze panes
        worksheet.freeze_panes(1, 0)
        
        # Add summary sheet
        summary_sheet = workbook.add_worksheet('Summary')
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'bg_color': '#366092',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        label_format = workbook.add_format({
            'bold': True,
            'align': 'left',
            'border': 1
        })
        
        value_format = workbook.add_format({
            'align': 'right',
            'border': 1
        })
        
        value_money_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'align': 'right',
            'border': 1
        })
        
        value_percent_format = workbook.add_format({
            'num_format': '0.0%',
            'align': 'right',
            'border': 1
        })
        
        summary_sheet.merge_cells('A1:B1')
        summary_sheet.write('A1', 'RSI 30/70 STRATEGY - SUMMARY', title_format)
        
        row = 3
        
        summary_data = [
            ['PERIOD', 'Jan 1 - Apr 10, 2026', 'text'],
            ['POSITION SIZE', '0.1 BTC per trade', 'text'],
            ['', '', ''],
            ['TOTAL TRADES', len(trades_df), 'number'],
            ['WINNING TRADES', len(trades_df[trades_df['Net_PnL'] > 0]), 'number'],
            ['LOSING TRADES', len(trades_df[trades_df['Net_PnL'] < 0]), 'number'],
            ['WIN RATE', len(trades_df[trades_df['Net_PnL'] > 0])/len(trades_df), 'percent'],
            ['', '', ''],
            ['GROSS P&L', trades_df['Gross_PnL'].sum(), 'money'],
            ['TOTAL FEES', trades_df['Total_Cost'].sum(), 'money'],
            ['NET P&L', trades_df['Net_PnL'].sum(), 'money'],
            ['', '', ''],
            ['AVERAGE WIN', trades_df[trades_df['Net_PnL'] > 0]['Net_PnL'].mean(), 'money'],
            ['AVERAGE LOSS', trades_df[trades_df['Net_PnL'] < 0]['Net_PnL'].mean(), 'money'],
            ['PROFIT FACTOR', (trades_df[trades_df['Net_PnL'] > 0]['Net_PnL'].sum() / abs(trades_df[trades_df['Net_PnL'] < 0]['Net_PnL'].sum())), 'number'],
            ['BEST TRADE', trades_df['Net_PnL'].max(), 'money'],
            ['WORST TRADE', trades_df['Net_PnL'].min(), 'money'],
            ['', '', ''],
            ['LONG TRADES', len(trades_df[trades_df['Type'] == 'LONG']), 'number'],
            ['LONG WIN RATE', len(trades_df[(trades_df['Type'] == 'LONG') & (trades_df['Net_PnL'] > 0)]) / len(trades_df[trades_df['Type'] == 'LONG']), 'percent'],
            ['LONG P&L', trades_df[trades_df['Type'] == 'LONG']['Net_PnL'].sum(), 'money'],
            ['', '', ''],
            ['SHORT TRADES', len(trades_df[trades_df['Type'] == 'SHORT']), 'number'],
            ['SHORT WIN RATE', len(trades_df[(trades_df['Type'] == 'SHORT') & (trades_df['Net_PnL'] > 0)]) / len(trades_df[trades_df['Type'] == 'SHORT']), 'percent'],
            ['SHORT P&L', trades_df[trades_df['Type'] == 'SHORT']['Net_PnL'].sum(), 'money'],
        ]
        
        for item in summary_data:
            summary_sheet.write(row, 0, item[0], label_format)
            
            if item[0] != '':
                if item[2] == 'money':
                    summary_sheet.write(row, 1, item[1], value_money_format)
                elif item[2] == 'percent':
                    summary_sheet.write(row, 1, item[1], value_percent_format)
                elif item[2] == 'number':
                    summary_sheet.write(row, 1, item[1], value_format)
                else:
                    summary_sheet.write(row, 1, item[1], value_format)
            
            row += 1
        
        summary_sheet.set_column('A:A', 20)
        summary_sheet.set_column('B:B', 25)

    print(f"\n[Excel file created successfully!]")
    print(f"[Location: {excel_file}]")
    print(f"[Total trades exported: {len(trades_df)}]")
    print(f"\nOK - File saved to Desktop: RSI_30_70_Trades_Jan_Apr_2026.xlsx\n")

except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
