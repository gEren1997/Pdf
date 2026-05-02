import streamlit as st
import pandas as pd
import pdfplumber
import io
from weasyprint import HTML
from datetime import datetime
import re

st.set_page_config(page_title="STMNT Processor Pro", layout="wide")

# High-Contrast UI Styling for Visibility
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    /* Sidebar Styling: Navy Background with White Text */
    [data-testid="stSidebar"] {
        background-color: #1e293b !important;
        color: white !important;
    }
    /* Ensure all text in sidebar is white */
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span {
        color: white !important;
    }
    /* Input box styling for visibility */
    .stTextInput input, .stNumberInput input {
        background-color: #f1f5f9 !important;
        color: #0f172a !important;
    }
    .stButton>button { width: 100%; background-color: #1e3a8a; color: white; border-radius: 8px; }
    h1 { color: #1e3a8a; }
    </style>
""", unsafe_allow_html=True)

st.title("📑 STMNT: Advanced Transaction Processor")

uploaded_file = st.file_uploader("Upload Bank Statement (PDF)", type=['pdf'])

def extract_pdf_data(file):
    all_data = []
    with st.spinner("🔍 Extracting Data..."):
        with pdfplumber.open(file) as pdf:
            total_pages = len(pdf.pages)
            progress_bar = st.progress(0)
            for i, page in enumerate(pdf.pages):
                progress_bar.progress((i + 1) / total_pages)
                table = page.extract_table()
                if table: all_data.extend(table)
            progress_bar.empty()
    if not all_data: return pd.DataFrame()
    df = pd.DataFrame(all_data[1:], columns=all_data[0])
    df.columns = [str(c).replace('\n', ' ').strip() if c else f"Column_{i}" for i, c in enumerate(df.columns)]
    return df

def generate_output_pdf(df, total_dr, total_cr):
    table_html = df.to_html(index=False, classes='report-table')
    html_content = f"""
    <html>
    <head>
        <style>
            @page {{ size: A4 landscape; margin: 10mm; }}
            body {{ font-family: 'Helvetica', sans-serif; font-size: 8pt; color: #333; }}
            h2 {{ color: #1e3a8a; text-align: center; border-bottom: 2px solid #1e3a8a; }}
            .summary-box {{ margin: 20px 0; padding: 10px; border: 1px solid #1e3a8a; background: #f8fafc; border-radius: 5px; }}
            .report-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            .report-table th {{ background-color: #1e3a8a; color: white; padding: 6px; text-align: left; }}
            .report-table td {{ border-bottom: 1px solid #cbd5e1; padding: 6px; }}
            tr:nth-child(even) {{ background-color: #f1f5f9; }}
        </style>
    </head>
    <body>
        <h2>Transaction Separation Report</h2>
        <div class="summary-box">
            <table style="width: 100%;">
                <tr>
                    <td><strong>Total Debit:</strong> {total_dr:,.2f}</td>
                    <td><strong>Total Credit:</strong> {total_cr:,.2f}</td>
                    <td style="text-align: right;"><strong>Filtered Transactions:</strong> {len(df)}</td>
                </tr>
            </table>
        </div>
        {table_html}
    </body>
    </html>
    """
    return HTML(string=html_content).write_pdf()

if uploaded_file:
    if 'raw_df' not in st.session_state:
        st.session_state.raw_df = extract_pdf_data(uploaded_file)
    
    df = st.session_state.raw_df.copy()
    
    if not df.empty:
        st.sidebar.header("🎯 Advanced Filters")
        
        # 1. DATE FILTER (Now visible at the top)
        date_col = next((c for c in df.columns if 'date' in c.lower()), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            df = df.dropna(subset=[date_col])
            st.sidebar.subheader("📅 Date Range")
            start_date = st.sidebar.date_input("From", df[date_col].min())
            end_date = st.sidebar.date_input("To", df[date_col].max())
            df = df[(df[date_col] >= pd.to_datetime(start_date)) & (df[date_col] <= pd.to_datetime(end_date))]

        # 2. TYPE FILTER
        st.sidebar.subheader("🔄 Transaction Type")
        tran_type = st.sidebar.radio("Show:", ["Both", "Debit Only", "Credit Only"])
        
        # 3. AMOUNT FILTER (Typed inputs)
        st.sidebar.subheader("💰 Amount Range")
        amt_col = next((c for c in df.columns if any(x in c.lower() for x in ['amount', 'balance', 'value'])), None)
        dr_col = next((c for c in df.columns if 'debit' in c.lower()), None)
        cr_col = next((c for c in df.columns if 'credit' in c.lower()), None)
        target_amt_col = amt_col or dr_col or cr_col
        
        def clean_num(v):
            if pd.isna(v) or str(v).strip() == '': return 0.0
            num_str = re.sub(r'[^\d.]', '', str(v))
            return float(num_str) if num_str else 0.0

        if target_amt_col:
            df['temp_amt'] = df[target_amt_col].apply(clean_num)
            col1, col2 = st.sidebar.columns(2)
            min_input = col1.number_input("Min", value=0.0)
            max_input = col2.number_input("Max", value=float(df['temp_amt'].max()) if not df.empty else 100000.0)
            df = df[(df['temp_amt'] >= min_input) & (df['temp_amt'] <= max_input)]

        # 4. BRANCH FILTER
        branch_col = next((c for c in df.columns if 'branch' in c.lower()), None)
        if branch_col:
            st.sidebar.subheader("🏢 Branch")
            branches = sorted(df[branch_col].unique().tolist())
            sel_branches = st.sidebar.multiselect("Select Branches", branches)
            if sel_branches:
                df = df[df[branch_col].isin(sel_branches)]

        # 5. PARTICULARS FILTER (Multiple keywords)
        particulars_col = next((c for c in df.columns if any(x in c.lower() for x in ['particulars', 'description', 'details'])), None)
        if particulars_col:
            st.sidebar.subheader("🔍 Particulars")
            kw_input = st.sidebar.text_input("Search (comma separated)", "")
            keywords = [k.strip() for k in kw_input.split(',') if k.strip()]
            if keywords:
                pattern = '|'.join([re.escape(k) for k in keywords])
                df = df[df[particulars_col].astype(str).str.contains(pattern, case=False, na=False)]

        # Post-filter Dr/Cr logic
        if dr_col and cr_col:
            if tran_type == "Debit Only":
                df = df[df[dr_col].apply(clean_num) > 0]
            elif tran_type == "Credit Only":
                df = df[df[cr_col].apply(clean_num) > 0]
            total_dr = df[dr_col].apply(clean_num).sum()
            total_cr = df[cr_col].apply(clean_num).sum()
        else:
            total_dr = total_cr = 0.0

        st.subheader(f"📊 Results: {len(df)} transactions")
        st.dataframe(df.drop(columns=['temp_amt'], errors='ignore'), width="stretch")
        
        if st.button("🚀 Export to PDF with Summary"):
            pdf_bytes = generate_output_pdf(df.drop(columns=['temp_amt'], errors='ignore'), total_dr, total_cr)
            st.download_button("📥 Download PDF Report", pdf_bytes, "summary_report.pdf", "application/pdf")
