import streamlit as st
import pandas as pd
import pdfplumber
import io
from weasyprint import HTML
from datetime import datetime
import time

st.set_page_config(page_title="STMNT Processor", layout="wide")

# Custom UI Styling (Fintech Theme)
st.markdown("""
    <style>
    .main { background-color: #f1f5f9; }
    .stDataFrame { border: 1px solid #e2e8f0; border-radius: 8px; background: white; }
    [data-testid="stSidebar"] { background-color: #0f172a; color: white; }
    .stButton>button { width: 100%; background-color: #1e3a8a; color: white; border-radius: 8px; }
    h1 { color: #1e3a8a; }
    /* Mobile-friendly adjustments */
    @media (max-width: 640px) {
        .main { padding: 10px; }
    }
    </style>
""", unsafe_allow_html=True)

st.title("📑 STMNT: Transaction Processor")

uploaded_file = st.file_uploader("Upload Bank Statement (PDF)", type=['pdf'])

def extract_pdf_data(file):
    all_data = []
    # Visual feedback for processing
    with st.spinner("🔍 Accessing PDF layers..."):
        with pdfplumber.open(file) as pdf:
            total_pages = len(pdf.pages)
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, page in enumerate(pdf.pages):
                # Update progress indicators
                current_progress = (i + 1) / total_pages
                progress_bar.progress(current_progress)
                status_text.text(f"Processing page {i+1} of {total_pages}...")
                
                table = page.extract_table()
                if table:
                    all_data.extend(table)
            
            # Clean up progress indicators
            progress_bar.empty()
            status_text.empty()
            
    if not all_data:
        return pd.DataFrame()
    
    # Use first row as headers and clean them
    df = pd.DataFrame(all_data[1:], columns=all_data[0])
    df.columns = [str(c).replace('\n', ' ').strip() if c else f"Column_{i}" for i, c in enumerate(df.columns)]
    return df

def generate_output_pdf(df):
    table_html = df.to_html(index=False, classes='report-table')
    html_content = f"""
    <html>
    <head>
        <style>
            @page {{ size: A4 landscape; margin: 10mm; background-color: #ffffff; }}
            body {{ font-family: 'Helvetica', sans-serif; font-size: 8pt; color: #333; }}
            h2 {{ color: #1e3a8a; text-align: center; border-bottom: 2px solid #1e3a8a; padding-bottom: 5px; }}
            .report-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            .report-table th {{ background-color: #1e3a8a; color: white; padding: 6px; text-align: left; }}
            .report-table td {{ border-bottom: 1px solid #cbd5e1; padding: 6px; }}
            tr:nth-child(even) {{ background-color: #f8fafc; }}
        </style>
    </head>
    <body>
        <h2>Transaction Separation Report</h2>
        {table_html}
        <div style='text-align: right; margin-top: 20px; font-size: 7pt; color: #666;'>
            Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </div>
    </body>
    </html>
    """
    return HTML(string=html_content).write_pdf()

if uploaded_file:
    # Use session state to cache data so switching apps doesn't trigger a re-parse immediately
    if 'raw_df' not in st.session_state:
        st.session_state.raw_df = extract_pdf_data(uploaded_file)
    
    df = st.session_state.raw_df.copy()
    
    if not df.empty:
        st.sidebar.header("🎯 Filter Panel")
        
        # 1. Date Filter (Fuzzy Search)
        date_col = next((c for c in df.columns if 'date' in c.lower()), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            df = df.dropna(subset=[date_col])
            start_date = st.sidebar.date_input("From Date", df[date_col].min())
            end_date = st.sidebar.date_input("To Date", df[date_col].max())
            df = df[(df[date_col] >= pd.to_datetime(start_date)) & (df[date_col] <= pd.to_datetime(end_date))]

        # 2. Branch Filter
        branch_col = next((c for c in df.columns if 'branch' in c.lower()), None)
        if branch_col:
            branches = sorted(df[branch_col].unique().tolist())
            sel_branches = st.sidebar.multiselect("Select Branch", branches)
            if sel_branches:
                df = df[df[branch_col].isin(sel_branches)]

        # 3. Transaction Type (Dr/Cr)
        type_col = next((c for c in df.columns if any(x in c.lower() for x in ['type', 'dr/cr', 'status'])), None)
        if type_col:
            types = sorted(df[type_col].unique().tolist())
            sel_types = st.sidebar.multiselect("Debit/Credit Type", types)
            if sel_types:
                df = df[df[type_col].isin(sel_types)]

        # 4. Amount Filter
        amt_col = next((c for c in df.columns if any(x in c.lower() for x in ['amount', 'balance', 'debit', 'credit'])), None)
        if amt_col:
            df[amt_col] = pd.to_numeric(df[amt_col].astype(str).replace(r'[^\d.]', '', regex=True), errors='coerce')
            min_v, max_v = float(df[amt_col].min()), float(df[amt_col].max())
            amt_range = st.sidebar.slider("Amount Range", min_v, max_v, (min_v, max_v))
            df = df[(df[amt_col] >= amt_range[0]) & (df[amt_col] <= amt_range[1])]

        # 5. Search
        search = st.sidebar.text_input("Particulars Search")
        if search:
            df = df[df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]

        st.subheader(f"📊 {len(df)} transactions isolated")
        st.dataframe(df, use_container_width=True)
        
        if st.button("🚀 Export Filtered Results (PDF)"):
            with st.spinner("Generating PDF..."):
                pdf_bytes = generate_output_pdf(df)
                st.download_button("📥 Download PDF", pdf_bytes, "filtered_stmnt.pdf", "application/pdf")
    else:
        st.error("Table data extraction failed.")
else:
    # Clear cache if no file is present
    if 'raw_df' in st.session_state:
        del st.session_state.raw_df
