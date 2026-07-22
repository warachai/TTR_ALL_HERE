#python -m streamlit run ttr_task_form.py
#http://localhost:8501/?product=DORADO
import streamlit as st
import pandas as pd
import config
from access_logging import log_access

from streamlit import session_state as ss
import uuid

st.set_page_config(page_title="Feature Summary", layout="wide")
# Log site access for this page
log_access("fe_group_summary")

# ---------------------------------------------------------
# Dummy data – replace with your own
# ---------------------------------------------------------

default_programs = ["DORADO", "MARLIN", "MARLIN BP", "SUMMIT", "TSR"]
# Load data (will reload when session state changes)
current_tasks = pd.read_csv(config.FEATURE_MASTER_FILE)

current_tasks = current_tasks[current_tasks['Program'].isin(default_programs)]




st.title("Feature Group by Product View")

# --- Current Task List + centered filter box -----------------
st.subheader("Current Feature List")
c1, c2= st.columns([2, 2])
with c1:
    filter_text = st.text_input(
        "Filter Text Box",
        "",
        placeholder="Search in all columns..."
    )

with c2:
    search_mode = st.radio(
        "Search Mode",
        ["OR", "AND"],
        index=1,  # default to AND
        horizontal=True,
        help="OR: Match any word | AND: Match all words, [col]_null to search for null values"
    )


df_filtered_tasks = current_tasks


# ---------------- Pivot Summary -----------------
# Assumption: user meant Feature_Group for rows ("feature_groupo" typo)
if 'Feature_Group' in df_filtered_tasks.columns:
    pivot_source = df_filtered_tasks.copy()
    # normalize empty group names
    pivot_source['Feature_Group'] = pivot_source['Feature_Group'].fillna('')
    pivot_table = (
        pivot_source
        .pivot_table(index='Feature_Group', columns='Program', values='Task_ID', aggfunc='count', fill_value=0)
        .sort_index()
    )
    # Add a total column
    pivot_table['Total'] = pivot_table.sum(axis=1)
    # Reorder columns putting Total at end already, ensure consistent order
    pivot_table = pivot_table[[c for c in pivot_table.columns if c != 'Total'] + ['Total']]

    st.subheader("Feature Group x Program (Task Count)")

    pivot_table = pivot_table.reset_index()


    if filter_text:
            # Split search text into words
            search_terms = filter_text.strip().split()
            
            if search_mode == "OR":
                # OR condition: match if ANY search term is found
                mask = pivot_table.astype(str).apply(
                    lambda row: any(
                        row.str.contains(term, case=False, na=False).any() 
                        for term in search_terms
                    ), 
                    axis=1
                )
            else:  # AND condition
                # AND condition: match if ALL search terms are found
                mask = pivot_table.astype(str).apply(
                    lambda row: all(
                        row.str.contains(term, case=False, na=False).any() 
                        for term in search_terms
                    ), 
                    axis=1
                )
            pivot_table = pivot_table[mask]

    # Fallback to simple HTML with links (minimal styling)
    base = "http://10.7.194.231:8501/ttr_feature_form_group"
    from urllib.parse import quote as _q
    program_cols = [c for c in pivot_table.columns if c not in ("Feature_Group", "Total")]
    html_rows = []
    header = ["Feature_Group"] + program_cols + ["Total"]
    html_rows.append("<tr>" + "".join(f"<th>{h}</th>" for h in header) + "</tr>")
    for _, row in pivot_table.iterrows():
        fg = row['Feature_Group']
        row_cells = [f"<td>{fg}</td>"]
        for prog in program_cols:
            val = row[prog]
            if val == 0:
                row_cells.append(f"<td>{val}</td>")
            else:
                url = f"{base}?feature_group={_q(str(fg))}&program={_q(str(prog))}"
                row_cells.append(f"<td><a href='{url}' target='_blank'>{val}</a></td>")
        total_val = row['Total']
        if total_val == 0:
            row_cells.append(f"<td>{total_val}</td>")
        else:
            url_total = f"{base}?feature_group={_q(str(fg))}"
            row_cells.append(f"<td><a href='{url_total}' target='_blank'>{total_val}</a></td>")
        html_rows.append("<tr>" + "".join(row_cells) + "</tr>")
    table_html = "<table>" + "".join(html_rows) + "</table>"
    st.markdown(table_html, unsafe_allow_html=True)

    st.caption(f"Total rows: {len(pivot_table)}")
else:
    st.warning("Column 'Feature_Group' not found; pivot cannot be generated.")


with st.expander("", expanded=False):
    # Display the pivot table as a dataframe
    st.dataframe(pivot_table, use_container_width=True)
    