import streamlit as st
import pandas as pd
import pdfplumber
import io
from weasyprint import HTML
from datetime import datetime

st.set_page_config(page_title="STMNT Processor", layout="wide")

# Custom UI Styling (Fintech Theme)
st.markdown("""
    <style>
    .main { background-color: #f1f5f9; }
    .stDataFrame { border: 1px solid #e2e8f0; border-radius: 8px; background: white; }
    [data-testid="stSidebar"] { background-color: #0f172a; color: white; }
    .stButton>button { width: 100%; background-color: #1e3a8a; color: white; border-radius: 8px; }
    h1 { color: #1e3a8a; }
    </style>
""", unsafe_allow_html=True)

st.title("📑 STMNT: Multi-Filter Transaction Processor")

uploaded_file = st.file_uploader("Upload Bank Statement (PDF)", type=['pdf'])

def extract_pdf_data(file):
    all_data = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                all_data.extend(table)
    if not all_data:
        return pd.DataFrame()
    
    # Use first row as headers and clean them
    df = pd.DataFrame(all_data[1:], columns=all_data[0])
    df.columns = [str(c).replace('\n', ' ').strip() if c else f"Column_{i}" for i, c in enumerate(df.columns)]
    return df

def generate_output_pdf(df):
    # Convert dataframe to HTML for PDF generation
    table_html = df.to_html(index=False, classes='report-table')
    html_content = f"""
    <html>
    <head>
        <style>
            @page {{ size: A4 landscape; margin: 10mm; }}
            body {{ font-family: 'Helvetica', sans-serif; font-size: 8pt; color: #333; }}
            h2 {{ color: #1e3a8a; text-align: center; border-bottom: 2px solid #1e3a8a; }}
            .report-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            .report-table th {{ background-color: #1e3a8a; color: white; padding: 6px; text-align: left; }}
            .report-table td {{ border-bottom: 1px solid #cbd5e1; padding: 6px; }}
            tr:nth-child(even) {{ background-color: #f8fafc; }}
        </style>
    </head>
    <body>
        <h2>Transaction Separation Report</h2>
        {table_html}
        <p style='text-align: right; margin-top: 20px;'>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </body>
    </html>
    """
    return HTML(string=html_content).write_pdf()

if uploaded_file:
    df_raw = extract_pdf_data(uploaded_file)
    
    if not df_raw.empty:
        df = df_raw.copy()
        st.sidebar.header("🎯 Filter Controls")
        
        # --- DYNAMIC MULTI-FILTERING ---
        
        # 1. Date Filter (Fuzzy Search for 'Date')
        date_col = next((c for c in df.columns if 'date' in c.lower()), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            df = df.dropna(subset=[date_col])
            start_date = st.sidebar.date_input("Start Date", df[date_col].min())
            end_date = st.sidebar.date_input("End Date", df[date_col].max())
            df = df[(df[date_col] >= pd.to_datetime(start_date)) & (df[date_col] <= pd.to_datetime(end_date))]

        # 2. Branch Filter
        branch_col = next((c for c in df.columns if 'branch' in c.lower()), None)
        if branch_col:
            branches = sorted(df[branch_col].unique().tolist())
            selected_branches = st.sidebar.multiselect("Filter by Branch", branches)
            if selected_branches:
                df = df[df[branch_col].isin(selected_branches)]

        # 3. Transaction Type (Debit/Credit)
        type_col = next((c for c in df.columns if any(x in c.lower() for x in ['type', 'dr/cr', 'status'])), None)
        if type_col:
            types = sorted(df[type_col].unique().tolist())
            selected_types = st.sidebar.multiselect("Filter by Type (Dr/Cr)", types)
            if selected_types:
                df = df[df[type_col].isin(selected_types)]

        # 4. Amount Range
        amt_col = next((c for c in df.columns if any(x in c.lower() for x in ['amount', 'balance', 'debit', 'credit'])), None)
        if amt_col:
            # Clean numeric data from currency symbols
            df[amt_col] = pd.to_numeric(df[amt_col].astype(str).replace(r'[^\d.]', '', regex=True), errors='coerce')
            min_val, max_val = float(df[amt_col].min()), float(df[amt_col].max())
            amount_range = st.sidebar.slider("Transaction Amount Range", min_val, max_val, (min_val, max_val))
            df = df[(df[amt_col] >= amount_range[0]) & (df[amt_col] <= amount_range[1])]

        # 5. Global Keyword Search (Particulars)
        search_query = st.sidebar.text_input("Search Particulars / Description")
        if search_query:
            df = df[df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]

        # Display results
        st.subheader(f"📊 Filtered Data: {len(df)} records found")
        st.dataframe(df, use_container_width=True)
        
        if st.button("🚀 Process & Download PDF"):
            with st.spinner("Generating PDF Report..."):
                pdf_output = generate_output_pdf(df)
                st.download_button(
                    label="📥 Download Resulting PDF",
                    data=pdf_output,
                    file_name="filtered_statement.pdf",
                    mime="application/pdf"
                )
    else:
        st.error("Could not find table data in the PDF. Please check the document format.")
