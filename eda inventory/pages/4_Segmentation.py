# 📊 File: pages/3_Metrics.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(layout="wide")
def format_number_short(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    else:
        return str(int(n))

st.markdown("""
    <style>
        body {
            background-color: #0E1117;
            color: white;
        }
        .metric-box {
            background-color: #1f1f1f;
            color: white;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #444;
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>SKU Segmentation & Inactivity Analysis</h1>", unsafe_allow_html=True)

if 'merged_df' not in st.session_state:
    st.warning("Please upload and submit data in the Upload page first.")
    st.stop()

df = st.session_state['merged_df'].copy()

# Rename and fill missing columns
if 'Average Lead Time' in df.columns:
    df.rename(columns={'Average Lead Time': 'Average Lead Time (days)'}, inplace=True)
if 'Safety Stock' not in df.columns:
    df['Safety Stock'] = 0

if 'Last Order Date' in df.columns and 'First Order Date' in df.columns and 'Active Order Days' in df.columns:
    df['Median Days Between Orders'] = df['Active Order Days'] / df['Order Quantity sum'].replace(0, np.nan)
    df['Median Days Between Orders'] = df['Median Days Between Orders'].fillna(0)

# Process dates and assign movement categories
try:
    df['Last Order Date'] = pd.to_datetime(df['Last Order Date'], errors='coerce')
    latest_data_date = df['Last Order Date'].max()
    df['Days Since Last Movement'] = (latest_data_date - df['Last Order Date']).dt.days.fillna(-1)

    def classify_movement(row):
        if row['Order Quantity sum'] == 0:
            return 'Non-moving'
        elif pd.notnull(row['Median Days Between Orders']) and row['Median Days Between Orders'] < 30 and \
             row['Order Quantity sum'] >= df['Order Quantity sum'].quantile(0.75):
            return 'Fast-moving'
        else:
            return 'Slow-moving'

    df['Movement Category'] = df.apply(classify_movement, axis=1)

    df_inactivity = df[df['Days Since Last Movement'] <= 730]

    df['Avg Daily Demand'] = df['Order Quantity sum'] / df['Average Lead Time (days)'].replace(0, np.nan)
    df['Avg Daily Demand'] = df['Avg Daily Demand'].fillna(0)
    df['Reorder Point'] = df['Avg Daily Demand'] * df['Average Lead Time (days)'] + df['Safety Stock']
    df['Inventory Turnover Ratio'] = df['Order Quantity sum'] / df['Current Stock Quantity'].replace(0, np.nan)
    df['Inventory Turnover Ratio'] = df['Inventory Turnover Ratio'].fillna(0)

    # ABC-XYZ Classification
    df['Consumption Value'] = df['Order Quantity sum'] * df['Unit Price']
    df = df.sort_values('Consumption Value', ascending=False)
    df['Cumulative %'] = 100 * df['Consumption Value'].cumsum() / df['Consumption Value'].sum()
    df['ABC Class'] = df['Cumulative %'].apply(lambda x: 'A' if x <= 70 else ('B' if x <= 90 else 'C'))
    df['CV'] = df['Order Quantity std'] / df['Order Quantity mean'].replace(0, np.nan)
    df['CV'] = df['CV'].fillna(0)
    df['XYZ Class'] = df['CV'].apply(lambda x: 'X' if x <= 0.5 else ('Y' if x <= 1 else 'Z'))
    df['ABC-XYZ Class'] = df['ABC Class'] + '-' + df['XYZ Class']

    # -------------------- KPI and PIE CHART Section ----------------------
    status_counts = df['Movement Category'].value_counts().reset_index()
    status_counts.columns = ['Stock Status', 'Count']

    col1, col2, col3 = st.columns(3)
    col1.markdown(f"<div class='metric-box'><h3>{df['SKU ID'].nunique()}</h3><p>SKU Count</p></div>", unsafe_allow_html=True)
    inventory_value = df['Consumption Value'].sum()
    col2.markdown(f"<div class='metric-box'><h3>₹{format_number_short(inventory_value)}</h3><p>Total Inventory Value</p></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='metric-box'><h3>{df['Order Quantity mean'].mean():.2f}</h3><p>Average Order Quantity</p></div>", unsafe_allow_html=True)

    st.plotly_chart(px.pie(status_counts, names='Stock Status', values='Count', hole=0.5), use_container_width=True)

    # --------------------- Filters (AFTER KPI) -----------------------
    
    selected_status = st.selectbox("Filter by Movement Category:", ['All'] + list(status_counts['Stock Status']))

    filtered_df = df if selected_status == 'All' else df[df['Movement Category'] == selected_status]
    filtered_df_inactivity = df_inactivity if selected_status == 'All' else df_inactivity[df_inactivity['Movement Category'] == selected_status]

    # --------------------- Heatmap -------------------------
    st.markdown("<h3 style='color:black'>ABC-XYZ Heatmap</h3>", unsafe_allow_html=True)
    abc_xyz_df = filtered_df.groupby(['ABC Class', 'XYZ Class']).size().reset_index(name='Count')
    pivot_df = abc_xyz_df.pivot(index='XYZ Class', columns='ABC Class', values='Count').fillna(0).sort_index(ascending=False)
    fig_heatmap = go.Figure(go.Heatmap(
        z=pivot_df.values,
        x=list(pivot_df.columns),
        y=list(pivot_df.index),
        text=pivot_df.values,
        texttemplate="%{text}",
        colorscale='earth',
        colorbar=dict(title='No. of SKUs')
    ))
    st.plotly_chart(fig_heatmap, use_container_width=True)

    # ---------------------- Inactivity Buckets ---------------------
    st.markdown("<hr><h3 style='color:black'>Inactivity Buckets</h3><p style='color:white'>How long since SKUs were last ordered?</p>", unsafe_allow_html=True)
    bucket_view = st.selectbox("", ['Weeks', 'Months', 'Days'])

    def get_bucket_label(days):
        if days < 0:
            return 'No Movement'
        if bucket_view == 'Weeks':
            return f"{int(days // 7)}-{int(days // 7 + 1)} weeks"
        elif bucket_view == 'Months':
            return f"{int(days // 30)}-{int(days // 30 + 1)} months"
        else:
            return f"{int(days)}-{int(days + 1)} days"

    filtered_df_inactivity['Inactivity Bucket'] = filtered_df_inactivity['Days Since Last Movement'].apply(get_bucket_label)

    if selected_status == 'Non-moving':
        st.info("Non-moving SKUs have no recorded last order date, so they're not bucketed by inactivity.")
    else:
        inactive_summary = filtered_df_inactivity['Inactivity Bucket'].value_counts().reset_index()
        inactive_summary.columns = ['Inactivity Period', 'Inactive SKU Count']
        st.bar_chart(inactive_summary.set_index('Inactivity Period'))

    # --------------------- Export Section -------------------
    st.markdown("<h3 style='color:black'>Export Metrics to Excel</h3>", unsafe_allow_html=True)
    options = st.multiselect("Choose data to export:", [
        "ABC Inventory Classification",
        "XYZ Classification",
        "Inventory Turnover Ratio",
        "Reorder points",
        "Stock Status Classification"
    ])
    if st.button("Export to Excel"):
        export_df = pd.DataFrame()
        export_df["SKU ID"] = df["SKU ID"]
        if "ABC Inventory Classification" in options:
            export_df["ABC Class"] = df["ABC Class"]
        if "XYZ Classification" in options:
            export_df["XYZ Class"] = df["XYZ Class"]
        if "Inventory Turnover Ratio" in options:
            export_df["Inventory Turnover Ratio"] = df["Inventory Turnover Ratio"]
        if "Reorder points" in options:
            export_df["Reorder Point"] = df["Reorder Point"]
        if "Stock Status Classification" in options:
            export_df["Stock Status"] = df["Movement Category"]
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name="Metrics Export")
        st.download_button("Download Excel", data=buffer.getvalue(), file_name="inventory_metrics_export.xlsx")

except Exception as e:
    st.error(f"Analysis Error: {e}")
