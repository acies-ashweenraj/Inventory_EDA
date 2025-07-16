import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- Streamlit Page Setup ---
st.set_page_config(page_title="Inventory Analysis", layout="wide")
st.title("Inventory Health & RCA Analysis")

# --- Load Data ---
if "merged_df" not in st.session_state:
    st.warning("Please upload and submit your data in the Upload tab.")
    st.stop()

df = st.session_state["merged_df"].copy()
df.columns = df.columns.str.strip()

# --- Basic Column Validations ---
required_cols = ['SKU ID', 'Current Stock Quantity', 'Unit Price']
for col in required_cols:
    if col not in df.columns:
        st.error(f"Missing column: {col}")
        st.stop()

# --- Generate Missing Columns ---
if "Order Quantity sum" not in df.columns:
    df["Order Quantity sum"] = df["Current Stock Quantity"] * 0.7 + np.random.normal(0, 0.2, len(df)) * df["Current Stock Quantity"]
    df["Order Quantity sum"] = df["Order Quantity sum"].clip(lower=0).round()

if "Average Lead Time (days)" not in df.columns:
    df["Average Lead Time (days)"] = 7
if "Maximum Lead Time (days)" not in df.columns:
    df["Maximum Lead Time (days)"] = 10
if "Safety Stock" not in df.columns:
    df["Safety Stock"] = df["Current Stock Quantity"] * 0.1

# --- Derived Columns ---
df["Stock Value"] = df["Current Stock Quantity"] * df["Unit Price"]
df["Avg Daily Demand"] = df["Order Quantity sum"] / 365

# --- Stock Health Classification ---
def classify(row):
    demand = row["Order Quantity sum"]
    stock = row["Current Stock Quantity"]
    gap = 0.1 * demand
    if demand == 0:
        return "Overstocked" if stock > 0 else "Ideal"
    if abs(stock - demand) <= gap:
        return "Ideal"
    elif stock > demand:
        return "Overstocked"
    else:
        return "Understocked"

df["Stock Status"] = df.apply(classify, axis=1)
def format_number_short(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    elif n >= 1_000:
        return f"{n/1_000:.2f}K"
    else:
        return str(int(n))


# --- KPI Metrics ---
total_skus = df["SKU ID"].nunique()
total_stock = int(df["Current Stock Quantity"].sum())
total_value = df["Stock Value"].sum()

col1, col2, col3 = st.columns(3)
col1.metric("Total SKUs", total_skus)
col2.metric("Total Stock Quantity", total_stock)
col3.metric("Inventory Value (₹)", f"{format_number_short(total_value)}")

# --- Smooth Expand Transition for Inventory Health ---
summary = df["Stock Status"].value_counts().to_dict()

with st.expander("Show Inventory Stock Health (Under / Over / Ideal)"):
    col4, col5, col6 = st.columns(3)
    col4.metric("Understocked", summary.get("Understocked", 0))
    col5.metric("Overstocked", summary.get("Overstocked", 0))
    col6.metric("Ideal Stock", summary.get("Ideal", 0))

# --- Filter Section with "ALL" Option ---
st.markdown("### Filter by Stock Health")

stock_status_options = ["ALL"] + df["Stock Status"].unique().tolist()
selected_status = st.multiselect(
    "Select Stock Status",
    options=stock_status_options,
    default=["ALL"]
)

# Ensure "ALL" is exclusive
if "ALL" in selected_status and len(selected_status) > 1:
    selected_status = [s for s in selected_status if s != "ALL"]

# Filter the dataframe
if "ALL" in selected_status:
    df_filtered = df.copy()
else:
    df_filtered = df[df["Stock Status"].isin(selected_status)]

st.markdown("---")

# --- Chart 1: Stock vs Safety Stock ---
st.subheader("Stock vs Safety Stock (Top SKUs at Risk)")
top15 = df_filtered.sort_values("Current Stock Quantity", ascending=False).head(15)
fig1 = go.Figure()
fig1.add_trace(go.Bar(x=top15["SKU ID"], y=top15["Current Stock Quantity"], name="Current Stock", marker_color="#4e79a7"))
fig1.add_trace(go.Scatter(x=top15["SKU ID"], y=top15["Safety Stock"], name="Safety Stock", mode="lines+markers", line=dict(color="#e15759", width=2)))
fig1.update_layout(barmode='group', xaxis_title="Top SKUs", yaxis_title="Quantity", height=400)
st.plotly_chart(fig1, use_container_width=True)

st.markdown("---")

# --- Chart 2: RCA Scatter Plot ---
st.subheader("Root Cause Analysis (Stock vs Demand)")
fig_rca = px.scatter(
    df_filtered,
    x="Order Quantity sum",
    y="Current Stock Quantity",
    color="Stock Status",
    hover_data=["SKU ID", "Avg Daily Demand", "Safety Stock"],
    color_discrete_map={"Understocked": "red", "Overstocked": "blue", "Ideal": "green"},
    labels={"Order Quantity sum": "Total Demand", "Current Stock Quantity": "Current Stock"},
    title="SKU Inventory Positioning"
)
fig_rca.update_layout(height=450)
st.plotly_chart(fig_rca, use_container_width=True)

# --- RCA Explanation for a Selected SKU ---
st.subheader("RCA Explanation by SKU")
sku_selected = st.selectbox("Select a SKU:", options=df_filtered["SKU ID"].unique())
sku_row = df_filtered[df_filtered["SKU ID"] == sku_selected].iloc[0]

st.write(f"**SKU ID:** `{sku_selected}`")
st.write(f"**Stock Status:** `{sku_row['Stock Status']}`")
st.write(f"**Current Stock:** {sku_row['Current Stock Quantity']:.0f}")
st.write(f"**Total Demand (Year):** {sku_row['Order Quantity sum']:.0f}")
st.write(f"**Average Daily Demand:** {sku_row['Avg Daily Demand']:.2f}")
st.write(f"**Safety Stock:** {sku_row['Safety Stock']:.2f}")
st.write(f"**Lead Time:** {sku_row['Average Lead Time (days)']} days")

# --- RCA Narrative ---
st.markdown("### Root Cause & Recommendation")
if sku_row["Stock Status"] == "Understocked":
    st.error("This SKU has **Low DOS**. You're at risk of stockouts.")
    st.markdown("""
    - **Cause**: Demand is exceeding your current inventory.
    - **Recommended Stock**: Add buffer above lead time demand.
    - **Action**: Increase order frequency or safety stock.
    - **Hint**: Check supplier delays or inaccurate forecasts.
    """)
elif sku_row["Stock Status"] == "Overstocked":
    st.info("This SKU has **High DOS**. You may have tied up too much capital.")
    st.markdown("""
    - **Cause**: Current stock significantly exceeds demand.
    - **Risk**: Higher holding cost, obsolescence.
    - **Action**: Pause reorders, clear slow-movers.
    - **Hint**: Check outdated demand forecast.
    """)
else:
    st.success("This SKU has **Adequate DOS**.")
    st.markdown("""
    - You’ve balanced stock and demand efficiently.
    - Keep monitoring lead time and demand trends.
    """)

st.markdown("---")

# --- Chart 3: Top SKUs by Order Value ---
st.subheader("Top SKUs by Order Value")
df_filtered["Order Value"] = df_filtered["Order Quantity sum"] * df_filtered["Unit Price"]
top_value = df_filtered.sort_values(by="Order Value", ascending=False).head(15)
fig3 = px.bar(top_value, x="Order Value", y="SKU ID", orientation="h", color="Order Value", color_continuous_scale="Viridis")
fig3.update_layout(height=450, yaxis_title="SKU ID", xaxis_title="Order Value (₹)")
st.plotly_chart(fig3, use_container_width=True)
