import streamlit as st

st.set_page_config(layout="wide", page_title="Inventory Assistant")

# Title and logo side-by-side
col1, col2 = st.columns([6, 1])
with col1:
    st.markdown("##  Inventory Analytics & Assistant")
with col2:
    st.image("acies_global_logo.jpeg", width=80)  # Make sure this file is in the same folder

st.markdown("---")

# App Description
st.markdown("""


This platform helps you:
-  Upload and analyze your order and stock data.
-  Detect overstocked and understocked SKUs with Root Cause Analysis.
-  Understand SKU performance through segmentation (ABC, XYZ).
-  Monitor inventory turnover, reorder points, and inactivity patterns.
- Use GenAI to interpret stock health and make data-driven decisions.

>  Use the sidebar to explore: Upload Data → View Dashboard → Get Recommendations.
""")
