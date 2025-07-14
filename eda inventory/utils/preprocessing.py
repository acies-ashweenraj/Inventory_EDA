import pandas as pd
import numpy as np

def preprocess_inventory(orders_df, master_df):
    orders_df['Order Date'] = pd.to_datetime(orders_df['Order Date'])
    agg_df = orders_df.groupby('SKU ID').agg(
        **{
            'Order Quantity sum': ('Order Quantity', 'sum'),
            'Order Quantity mean': ('Order Quantity', 'mean'),
            'Order Quantity std': ('Order Quantity', 'std'),
            'Last Order Date': ('Order Date', 'max'),
            'Median Days Between Orders': ('Order Date', lambda x: x.diff().median().days if len(x) > 1 else 0)
        }).reset_index()

    df = pd.merge(agg_df, master_df, on='SKU ID', how='left')

    df['Last Order Date'] = pd.to_datetime(df['Last Order Date'], errors='coerce')
    latest_date = df['Last Order Date'].max()
    df['Days Since Last Movement'] = (latest_date - df['Last Order Date']).dt.days.fillna(-1)

    df['Avg Daily Demand'] = df['Order Quantity sum'] / df['Average Lead Time'].replace(0, np.nan)
    df['Avg Daily Demand'] = df['Avg Daily Demand'].fillna(0)
    df['Reorder Point'] = df['Avg Daily Demand'] * df['Average Lead Time'] + df['Safety Stock']

    df['Inventory Turnover Ratio'] = df['Order Quantity sum'] / df['Current Stock Quantity'].replace(0, np.nan)
    df['Inventory Turnover Ratio'] = df['Inventory Turnover Ratio'].fillna(0)

    df['Consumption Value'] = df['Order Quantity sum'] * df['Unit Price']
    df = df.sort_values('Consumption Value', ascending=False)
    df['Cumulative %'] = 100 * df['Consumption Value'].cumsum() / df['Consumption Value'].sum()
    df['ABC Class'] = df['Cumulative %'].apply(lambda x: 'A' if x <= 70 else ('B' if x <= 90 else 'C'))

    df['CV'] = df['Order Quantity std'] / df['Order Quantity mean'].replace(0, np.nan)
    df['CV'] = df['CV'].fillna(0)
    df['XYZ Class'] = df['CV'].apply(lambda x: 'X' if x <= 0.5 else ('Y' if x <= 1 else 'Z'))
    df['ABC-XYZ Class'] = df['ABC Class'] + '-' + df['XYZ Class']

    df['Movement Category'] = df.apply(lambda row: classify_movement(row, df), axis=1)

    return df

def classify_movement(row, df):
    if row['Order Quantity sum'] == 0:
        return 'Non-moving'
    elif pd.notnull(row['Median Days Between Orders']) and row['Median Days Between Orders'] < 30 and \
         row['Order Quantity sum'] >= df['Order Quantity sum'].quantile(0.75):
        return 'Fast-moving'
    else:
        return 'Slow-moving'
