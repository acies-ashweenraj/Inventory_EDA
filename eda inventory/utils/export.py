import pandas as pd
from io import BytesIO

def generate_export(df, options):
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
        export_df.to_excel(writer, index=False, sheet_name="Selected Metrics")
    return buffer
