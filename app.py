import streamlit as st
import pandas as pd
from io import BytesIO

def create_download_file(df, supplier_name):
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return output

def normalize_part_number(x):
    return str(x).strip().upper()
# ---- SIMPLE PASSWORD PROTECTION ----
PASSWORD = "$Saifuddin123"  # Change this to your own password

def check_password():
    def password_entered():
        if st.session_state["password"] == PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Enter Password", type="password", key="password", on_change=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Enter Password", type="password", key="password", on_change=password_entered)
        st.error("Incorrect Password")
        return False
    else:
        return True


if not check_password():
    st.stop()
import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Auto Parts Quote Comparator", layout="wide")


def normalize_part(part) -> str:
    """Normalize part numbers so 90915-5M015 == 909155M015."""
    if part is None:
        return ""
    part = str(part).upper().strip()
    part = re.sub(r"[^A-Z0-9]", "", part)  # remove hyphens/spaces/anything not alnum
    return part


st.title("Auto Spare Parts Quotation Comparator")
st.caption("Comparison is done ONLY by part number (normalized). Descriptions are ignored.")

uploaded_files = st.file_uploader(
    "Upload supplier quotation files (CSV/XLSX/XLS)",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True
)

all_rows = []

if uploaded_files:
    st.info("For each file: enter supplier name → select Part Number column → select Price column.")

    for f in uploaded_files:
        st.subheader(f"File: {f.name}")

        supplier = st.text_input(
            f"Supplier name for {f.name}",
            value=f.name.split(".")[0],
            key=f"sup_{f.name}"
        )

        # Read file
        if f.name.lower().endswith(".csv"):
            df = pd.read_csv(f)
        else:
            df = pd.read_excel(f)

        st.write("Preview:")
        st.dataframe(df.head(20), use_container_width=True)

        # Column selection
        cols = list(df.columns)
        if not cols:
            st.error("This file has no columns.")
            continue

        part_col = st.selectbox("Select Part Number column", cols, key=f"part_{f.name}")
        price_col = st.selectbox("Select Price column", cols, key=f"price_{f.name}")

        temp = df[[part_col, price_col]].copy()
        temp.columns = ["part_number_raw", "price"]

        temp["supplier"] = supplier
        temp["part_number_normalized"] = temp["part_number_raw"].apply(normalize_part)

        # Convert price to numeric
        temp["price"] = pd.to_numeric(temp["price"], errors="coerce")

        # Remove invalid rows
        temp = temp.dropna(subset=["part_number_normalized", "price"])
        temp = temp[temp["part_number_normalized"] != ""]

        all_rows.append(temp)

    if all_rows:
        data = pd.concat(all_rows, ignore_index=True)

        # Count how many suppliers each part appears in
        supplier_count = (
            data.groupby("part_number_normalized")["supplier"]
                .nunique()
                .reset_index(name="supplier_count")
        )
        data = data.merge(supplier_count, on="part_number_normalized", how="left")

        # MAIN: parts that appear in 2+ supplier files
        multi_supplier = data[data["supplier_count"] >= 2].copy()

        # SECOND: parts that appear in only 1 supplier file
        single_supplier = data[data["supplier_count"] == 1].copy()

        # ---------------- MAIN TABLE ----------------
        st.markdown("## Cheapest supplier per part number (Only parts present in 2+ files)")

        if len(multi_supplier) == 0:
            st.warning("No part numbers are common across 2 or more supplier files.")
        else:
            cheapest = (
                multi_supplier.sort_values(["part_number_normalized", "price"])
                    .groupby("part_number_normalized", as_index=False)
                    .first()
                    .rename(columns={
                        "part_number_normalized": "part_number",
                        "supplier": "cheapest_supplier",
                        "price": "cheapest_price"
                    })
            )

            st.dataframe(cheapest, use_container_width=True)

            # Win count (based only on common parts)
            wins = cheapest["cheapest_supplier"].value_counts().reset_index()
            wins.columns = ["supplier", "parts_won"]

            st.markdown("## Supplier Win Count (2+ file parts only)")
            st.dataframe(wins, use_container_width=True)

            csv_main = cheapest.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download Cheapest Results (CSV)",
                csv_main,
                "cheapest_results.csv",
                "text/csv"
            )

        # ---------------- SECOND TABLE ----------------
        st.markdown("## Part numbers that exist in only one file")

        if len(single_supplier) == 0:
            st.success("All part numbers appear in at least 2 supplier files.")
        else:
            only_exists = (
                single_supplier.sort_values(["part_number_normalized", "supplier"])
                    .groupby("part_number_normalized", as_index=False)
                    .first()[["part_number_normalized", "supplier", "price"]]
                    .rename(columns={
                        "part_number_normalized": "part_number",
                        "supplier": "only_exists_in",
                        "price": "price_in_that_supplier"
                    })
            )

            # Add the "ONLY EXISTS IN ..." text you asked for
            only_exists["status"] = only_exists["only_exists_in"].apply(lambda x: f"ONLY EXISTS IN {x}")

            # Display columns in a nice order
            only_exists = only_exists[["part_number", "status", "price_in_that_supplier"]]

            st.dataframe(only_exists, use_container_width=True)

            csv_single = only_exists.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download 'Only Exists In' (CSV)",
                csv_single,
                "only_exists_in_one_file.csv",
                "text/csv"
            )

else:
    st.write("Upload quotation files to start comparing.")
all_parts = []

for supplier_name, df in supplier_data.items():
    df["Part Number"] = df["Part Number"].apply(normalize_part_number)
    df = df[["Part Number", "Price"]].copy()
    df.rename(columns={"Price": supplier_name}, inplace=True)
    all_parts.append(df)

# Merge all suppliers
merged = all_parts[0]
for df in all_parts[1:]:
    merged = pd.merge(merged, df, on="Part Number", how="outer")

# Count how many suppliers have this part
merged["supplier_count"] = merged.drop(columns=["Part Number"]).notna().sum(axis=1)

# Only keep parts in 2+ suppliers
filtered = merged[merged["supplier_count"] >= 2].copy()

# --- CHEAPEST ---
filtered["Cheapest Supplier"] = filtered.drop(columns=["Part Number", "supplier_count"]).idxmin(axis=1)
filtered["Cheapest Price"] = filtered.drop(columns=["Part Number", "supplier_count"]).min(axis=1)

# --- SECOND CHEAPEST ---
def second_cheapest(row):
    prices = row.drop(["Part Number", "supplier_count"])
    prices = prices.dropna().sort_values()
    if len(prices) >= 2:
        return prices.index[1], prices.iloc[1]
    return None, None

filtered[["Second Supplier", "Second Price"]] = filtered.apply(
    lambda row: pd.Series(second_cheapest(row)), axis=1
)
cheapest_counts = filtered["Cheapest Supplier"].value_counts().reset_index()
cheapest_counts.columns = ["Supplier", "Win Count"]

st.subheader("Cheapest Supplier Win Count (2+ files only)")
st.dataframe(cheapest_counts)
selected_supplier = st.selectbox("Select supplier (Cheapest)", cheapest_counts["Supplier"])

if selected_supplier:
    supplier_df = filtered[filtered["Cheapest Supplier"] == selected_supplier][["Part Number", "Cheapest Price"]]
    
    file = create_download_file(supplier_df, selected_supplier)
    
    st.download_button(
        label="Download Cheapest Parts",
        data=file,
        file_name=f"{selected_supplier}_cheapest.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    second_counts = filtered["Second Supplier"].value_counts().reset_index()
second_counts.columns = ["Supplier", "Second Win Count"]

st.subheader("Second Cheapest Supplier Win Count")
st.dataframe(second_counts)
selected_second = st.selectbox("Select supplier (Second Cheapest)", second_counts["Supplier"])

if selected_second:
    second_df = filtered[filtered["Second Supplier"] == selected_second][["Part Number", "Second Price"]]
    
    file2 = create_download_file(second_df, selected_second)
    
    st.download_button(
        label="Download Second Cheapest Parts",
        data=file2,
        file_name=f"{selected_second}_second_cheapest.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
