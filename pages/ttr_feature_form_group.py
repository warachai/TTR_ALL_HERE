#python -m streamlit run ttr_task_form.py
#http://localhost:8501/?product=DORADO
import streamlit as st
import pandas as pd
import config
from access_logging import log_access

from streamlit import session_state as ss
import uuid

st.set_page_config(page_title="Feature View", layout="wide")
# Log site access for this page
log_access("feature_form_group")

# ---------------------------------------------------------
# Dummy data – replace with your own
# ---------------------------------------------------------
default_programs = ["DORADO", "MARLIN", "MARLIN BP", "SUMMIT", "TSR"]
params = st.query_params

# --- URL driven filtering (program & feature_group) ---
# Accept ?program=MARLIN or ?program=MARLIN,SUMMIT or legacy ?product=DORADO
raw_program_params = params.get("program", params.get("product", []))
if raw_program_params:
    # Streamlit returns list; handle comma-separated values inside first element
    if isinstance(raw_program_params, list):
        program_list = []
        for entry in raw_program_params:
            program_list.extend([p.strip() for p in str(entry).split(',') if p.strip()])
    else:
        program_list = [p.strip() for p in str(raw_program_params).split(',') if p.strip()]
    # Validate against known programs
    program_list = [p for p in program_list if p in default_programs]
    if program_list:
        default_programs = program_list

# Feature_Group parameter: ?feature_group=MyGroup (single or comma list)
raw_fg_params = params.get("feature_group", [])
feature_group_filter_values = []
if raw_fg_params:
    if isinstance(raw_fg_params, list):
        for entry in raw_fg_params:
            feature_group_filter_values.extend([g.strip() for g in str(entry).split(',') if g.strip()])
    else:
        feature_group_filter_values = [g.strip() for g in str(raw_fg_params).split(',') if g.strip()]



# Load data (will reload when session state changes)
current_tasks = pd.read_csv(config.FEATURE_MASTER_FILE)
# Build list of available improvement types for dynamic filtering
available_types = sorted(current_tasks['Improvement_Type'].dropna().unique().tolist())
if not available_types:
    available_types = ["TTR", "Other"]  # fallback if column empty


# Filter rows based on user_review_list
current_tasks = current_tasks[current_tasks['Program'].isin(default_programs)]


sub_task = pd.read_csv(config.JIRA_FILE_PATH)


st.title("Feature View")

# --- Current Task List + centered filter box -----------------
st.subheader("Current Feature List")

# Top filter row: Products and Improvement Types side-by-side, then text + search mode
filter_row_1_col1, filter_row_1_col2, filter_row_1_col3, filter_row_1_col4 = st.columns([1.4, 1.2, 2, 1])
with filter_row_1_col1:
    program_filter = st.multiselect(
        "Select Product(s)",
        ["DORADO", "MARLIN", "MARLIN BP", "SUMMIT", "TSR"],
        default=default_programs if raw_program_params else []
    )
with filter_row_1_col2:
    improvement_type_filter = st.multiselect(
        "Improvement Type(s)",
        available_types,
        default=[],
        help="Default shows TTR only; select more to expand."
    )
with filter_row_1_col3:
    # Prefill filter textbox with feature_group_filter_values (space-separated) if present
    prefill_filter_text = " ".join(feature_group_filter_values) if 'feature_group_filter_values' in globals() and feature_group_filter_values else ""
    filter_text = st.text_input(
        "Filter Text Box",
        prefill_filter_text,
        placeholder="Search across all columns..."
    )
with filter_row_1_col4:
    search_mode = st.radio(
        "Search Mode",
        ["OR", "AND"],
        index=1,  # default to AND
        horizontal=True,
        help="OR: any word | AND: all words | add [col]_null or [col]_nnull for null/not null"
    )

# Apply program filter
if program_filter:  # If any programs are selected
    df_filtered_tasks = current_tasks[current_tasks['Program'].isin(program_filter)]
else:  # If nothing selected, show all programs
    df_filtered_tasks = current_tasks

# Apply improvement type filter (default TTR)
if improvement_type_filter:
    df_filtered_tasks = df_filtered_tasks[df_filtered_tasks['Improvement_Type'].isin(improvement_type_filter)]


# Use filter_text to specify the column name
if filter_text:
    if filter_text.find("_null") != -1:
        colNull = filter_text.replace("_null","")
        if colNull in current_tasks.columns:
            # Filter rows where the specified column has null values
            df_filtered_tasks = df_filtered_tasks[df_filtered_tasks[colNull].isna()]

    elif filter_text.find("_nnull") != -1:
        colNull = filter_text.replace("_nnull","")
        if colNull in current_tasks.columns:
            # Filter rows where the specified column has null values
            df_filtered_tasks = df_filtered_tasks[df_filtered_tasks[colNull].notna()]

    # Apply text filter across all columns
    elif filter_text:
        # Split search text into words
        search_terms = filter_text.strip().split()
        
        if search_mode == "OR":
            # OR condition: match if ANY search term is found
            mask = df_filtered_tasks.astype(str).apply(
                lambda row: any(
                    row.str.contains(term, case=False, na=False).any() 
                    for term in search_terms
                ), 
                axis=1
            )
        else:  # AND condition
            # AND condition: match if ALL search terms are found
            mask = df_filtered_tasks.astype(str).apply(
                lambda row: all(
                    row.str.contains(term, case=False, na=False).any() 
                    for term in search_terms
                ), 
                axis=1
            )
        
        df_filtered_tasks = df_filtered_tasks[mask]

# Reorder columns in the table
# Sort by Task_ID (uses numeric portion if present) before column reordering
import re
def _extract_task_num(val: str):
    m = re.search(r'(\d+)$', str(val))
    return int(m.group(1)) if m else 10**9  # large sentinel for non-numeric IDs

# Order by Program then numeric part of Task_ID (then Task_ID as tie-breaker)
df_filtered_tasks = (
    df_filtered_tasks
        .assign(_task_num=df_filtered_tasks['Task_ID'].map(_extract_task_num))
        .sort_values(['Program', 'Source', '_task_num', 'Task_ID'], ascending=[True, False, False, False])
        .drop(columns=['_task_num'])
)
#### MMM need link to DISC
# Construct issue hyperlink column (Jira by default; DISC Korat for CR IDs)
if 'Task_ID' in df_filtered_tasks.columns:
    import re as _re
    def _make_issue_link(task_id: str):
        if pd.isna(task_id):
            return ""
        s = str(task_id).strip()
        m = _re.match(r'^CR(\d+)', s, flags=_re.IGNORECASE)
        if m:
            # DISC Korat request link expects just the numeric part
            return f"{config.DISC_REQUEST_BASE_URL}/{m.group(1)}/"
        # Fallback to Jira browse URL (JIRA_BASE_URL already ends with /browse/)
        return f"{config.JIRA_BASE_URL}{s}"
    df_filtered_tasks['Jira_Link'] = df_filtered_tasks['Task_ID'].apply(_make_issue_link)

df_filtered_tasks = df_filtered_tasks[
    [
        "Feature_Group",
        "Program",
        "Task_ID",
        "Jira_Link",
        "Status",
        "Feature_Name",
        "Task_Name",
        "User_Review",
        "Source",
        "User_Name",
        "Date_Time",
        "Improvement_Type",
        "Feature_Parent"
    ]
]

# Display editable dataframe with column configuration
master_tasks = st.dataframe(
    df_filtered_tasks, 
    height=300,
    hide_index=True,
    key="edited_tasks",
    on_select="rerun", # Rerun the app when a selection changes
    column_config={
        "Jira_Link": st.column_config.LinkColumn(label="Jira", help="Open Jira issue", display_text="View")
    }
)

# Show row count
st.caption(f"Total rows: {len(df_filtered_tasks)}")

selection = st.session_state["edited_tasks"].get("selection", {})
rows = selection.get("rows", [])

df_filteredSubTask = None
selected_row = None
selected_row_index = None

if rows:
    selected_row_index = rows[0] # Get the first selected row index
    selected_row = df_filtered_tasks.iloc[selected_row_index]
    # st.write("Selected Row:")
    #st.write(f"Selected Row Task_ID:{selected_row['Task_ID']}")
    # st.write(selected_row)
    df_filteredSubTask = sub_task[sub_task["Key"] == selected_row["Task_ID"]]



# Map filtered indices back to original DataFrame
original_indices = df_filtered_tasks.index[rows]

# Update grouping functionality
col1, col2 = st.columns([1, 1])

with col1:
# Display selected Task_IDs below the group name input
    group_name = st.text_input("Enter group name:")
    if st.button("Group Selected Rows"):
        if rows:
            if group_name:
                current_tasks.loc[original_indices, 'Feature_Group'] = group_name
                
                # Add error handling for file write operations
                try:
                    current_tasks.to_csv(config.FEATURE_MASTER_FILE, index=False)
                    st.success(f"Grouped {len(rows)} features into '{group_name}'.")
                    # Refresh the page after grouping using session state
                    st.rerun()      
                except Exception as e:
                    st.error(f"Failed to save changes: {e}")
            else:
                st.error("Please enter a group name.")
        else:
            st.error("Please select rows to group.")

with col2:
    list_txt = ""
    if rows:
        selected_task_ids = df_filtered_tasks["Task_ID"].iloc[rows].to_list()
        list_txt = str(selected_task_ids)
        
        st.text_input("Selected Task_IDs:", list_txt)  
    else:
        st.text_input("Selected Task_IDs:")
    if st.button("Ungroup Selected Rows"):
        if rows:
            
            current_tasks.loc[original_indices, 'Feature_Group'] = ""
            
            # Ungroup operation with error handling
            try:
                current_tasks.to_csv(config.FEATURE_MASTER_FILE, index=False)
                st.success(f"Ungrouped {len(rows)} features.")
                st.rerun()      
            except Exception as e:
                st.error(f"Failed to save changes: {e}")
        else:
            st.error("Please select rows to ungroup.")



st.markdown("")
   


# --- Bottom row: Sub Task (left) and Feature (right) ----------
with st.expander("Sub Task", expanded=False):
    if df_filteredSubTask is not None:
        st.dataframe(df_filteredSubTask, width="stretch", height=150)
    else:
        st.dataframe(sub_task, width="stretch", height=150)