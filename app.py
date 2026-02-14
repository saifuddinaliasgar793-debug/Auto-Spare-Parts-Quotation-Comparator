import streamlit as st

# ---- SIMPLE PASSWORD PROTECTION ----
PASSWORD = "$Saifuddin@123"  # Change this to your own password

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
