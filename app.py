import streamlit as st
import pandas as pd

st.set_page_config(page_title="Transaction Separator", layout="wide")

st.title("📊 Statement Transaction Filter")

uploaded_file = st.file_uploader("Upload your statement (CSV or Excel)", type=['csv', 'xlsx'])

if uploaded_file:
    # Load data
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.sidebar.header("Filter Options")

    # Dynamic Filters
    cols = df.columns.tolist()
    
    # Date Range Filter (Assuming a 'Date' column exists)
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        start_date = st.sidebar.date_input("Start Date", df['Date'].min())
        end_date = st.sidebar.date_input("End Date", df['Date'].max())
        df = df[(df['Date'] >= pd.to_datetime(start_date)) & (df['Date'] <= pd.to_datetime(end_date))]

    # Text-based filters (Branch, Particulars)
    search_branch = st.sidebar.text_input("Filter by Branch")
    if search_branch:
        df = df[df['Branch'].str.contains(search_branch, case=False, na=False)]

    search_particulars = st.sidebar.text_input("Filter by Particulars")
    if search_particulars:
        df = df[df['Particulars'].str.contains(search_particulars, case=False, na=False)]

    # Numeric filters (Amount)
    min_amt = st.sidebar.number_input("Min Amount", value=0.0)
    max_amt = st.sidebar.number_input("Max Amount", value=float(df.iloc[:, -1].max()) if not df.empty else 100000.0)
    # Note: Adjust logic based on your specific 'Debit/Credit' column names
    
    # Display Results
    st.subheader("Filtered Transactions")
    st.dataframe(df, use_container_width=True)

    # Export options
    st.download_button(
        label="Download Filtered Data as CSV",
        data=df.to_csv(index=False),
        file_name="filtered_transactions.csv",
        mime="text/csv",
    )
