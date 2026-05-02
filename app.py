import streamlit as st
import pandas as pd
import pdfplumber
import io
from weasyprint import HTML

st.set_page_config(page_title="Transaction Processor", layout="wide")

# Custom CSS for Premium Fintech Look
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { background-color: #1e293b; color: white; border-radius: 5px; }
    .stHeader { color: #0f172a; }
    </style>
""", unsafe_allow_html=True)

st.title("ðŸ“‘ PDF Transaction Separator & Export")

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
    
    # Simple header detection: use first row as columns
    df = pd.DataFrame(all_data[1:], columns=all_data[0])
    return df

def create_pdf_report(df):
    # Constructing rows for HTML table
    rows_html = ""
    for _, row in df.iterrows():
        cells = "".join([f"<td>{str(val)}</td>" for val in row])
        rows_html += f"<tr>{cells}</tr>"
        
    headers_html = "".join([f"<th>{col}</th>" for col in df.columns])

    html_content = f"""
    <html>
    <head>
        <style>
            @page {{ size: A4; margin: 15mm; background-color: #ffffff; }}
            body {{ font-family: 'Helvetica', sans-serif; color: #333; }}
            h2 {{ color: #1a365d; border-bottom: 2px solid #1a365d; padding-bottom: 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 9pt; }}
            th {{ background-color: #1e293b; color: white; padding: 8px; text-align: left; }}
            td {{ border-bottom: 1px solid #e2e8f0; padding: 8px; }}
            tr:nth-child(even) {{ background-color: #f8fafc; }}
            .footer {{ margin-top: 30px; font-size: 8pt; text-align: center; color: #94a3b8; }}
        </style>
    </head>
    <body>
        <h2>Filtered Transaction Report</h2>
        <table>
            <thead><tr>{headers_html}</tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        <div class="footer">Generated via Professional Transaction Processor</div>
    </body>
    </html>
    """
    return HTML(string=html_content).write_pdf()

if uploaded_file:
    df = extract_pdf_data(uploaded_file)
    
    if not df.empty:
        st.sidebar.header("Filter Transactions")
        
        # Search filter
        search_query = st.sidebar.text_input("Global Search (Branch, Particulars, etc.)")
        if search_query:
            df = df[df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]
        
        st.subheader("Preview Filtered Data")
        st.dataframe(df, use_container_width=True)
        
        if st.button("Generate PDF Output"):
            with st.spinner("Generating PDF..."):
                pdf_bytes = create_pdf_report(df)
                st.download_button(
                    label="Download Result PDF",
                    data=pdf_bytes,
                    file_name="filtered_statement.pdf",
                    mime="application/pdf"
                )
    else:
        st.error("Could not extract tabular data from this PDF. Ensure it contains a clear table structure.")
