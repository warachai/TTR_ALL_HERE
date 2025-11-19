#python -m streamlit run ttr_task_form.py
#http://localhost:8501/?product=DORADO
import streamlit as st
import pandas as pd
import config

from streamlit import session_state as ss
import uuid

st.set_page_config(page_title="Feature Summary", layout="wide")

# ---------------------------------------------------------
# Dummy data – replace with your own
# ---------------------------------------------------------


# Load data (will reload when session state changes)
current_tasks = pd.read_csv(config.FEATURE_MASTER_FILE)




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

    st.dataframe(pivot_table, use_container_width=True)

    st.caption(f"Total rows: {len(pivot_table)}")
else:
    st.warning("Column 'Feature_Group' not found; pivot cannot be generated.")
