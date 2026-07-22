#python -m streamlit run ttr_task_form.py
#http://localhost:8501/?product=DORADO
import streamlit as st
import pandas as pd
import config

from streamlit import session_state as ss
import uuid

st.set_page_config(page_title="Task View", layout="wide")



# ---------------------------------------------------------
# Dummy data – replace with your own
# ---------------------------------------------------------
default_programs = ["DORADO", "MARLIN", "MARLIN BP", "SUMMIT"]
params = st.query_params
selected_product = params.get("product", [None])
if len(selected_product)>3:
    default_programs = [selected_product]


# Load data (will reload when session state changes)
current_tasks = pd.read_csv(config.TASK_MASTER_FILE)
current_tasks = current_tasks[current_tasks['Improvement_Type'] == "TTR"]
current_tasks = current_tasks[current_tasks['Program'].isin(default_programs)]


sub_task = pd.read_csv(config.JIRA_FILE_PATH)


# Define modal function at top level
@st.dialog("Edit Task", width="large")
def show_edit_modal(row_data, task_id):
    st.write(f"## Edit Task Details - {task_id}")
    
    # Create a single-row dataframe for editing
    edit_df = pd.DataFrame([row_data])
    
    # Use data_editor for better editing experience with full width
    edited_df = st.data_editor(
        edit_df,
        key="task_editor",
        use_container_width=True,
        hide_index=True,
        num_rows=1,
        height=200
    )
    
    # Button row
    col_save, col_cancel, col_space = st.columns([1, 1, 8])
    with col_save:
        if st.button("💾 Save Changes", key="save_edit"):
            # Update the dataframe with new values from edited_df
            for col_name in edited_df.columns:
                current_tasks.loc[
                    current_tasks['Task_ID'] == task_id,
                    col_name
                ] = edited_df[col_name].iloc[0]
            
            # Save to CSV
            current_tasks.to_csv(config.TASK_MASTER_FILE, index=False)
            
            st.success("✅ Saved successfully!")
            st.rerun()
    
    with col_cancel:
        if st.button("❌ Cancel", key="cancel_edit"):
            st.rerun()


# ---------------------------------------------------------
# Layout
# ---------------------------------------------------------

st.title("Task View")

# --- Current Task List + centered filter box -----------------
st.subheader("Current Task List")

c1, c2, c3 = st.columns([1, 2, 1])
with c1:
    program_filter = st.multiselect(
        "Select Product(s)",
        ["DORADO", "MARLIN", "MARLIN BP", "SUMMIT"],
        default=[]
    )

with c2:
    filter_text = st.text_input(
        "Filter Text Box",
        "",
        placeholder="Search in all columns..."
    )

with c3:
    search_mode = st.radio(
        "Search Mode",
        ["OR", "AND"],
        horizontal=True,
        help="OR: Match any word | AND: Match all words"
    )

# Apply program filter
if program_filter:  # If any programs are selected
    df_filtered_tasks = current_tasks[current_tasks['Program'].isin(program_filter)]
else:  # If nothing selected, show all
    df_filtered_tasks = current_tasks

# Apply text filter across all columns
if filter_text:
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


# Display editable dataframe with column configuration
master_tasks = st.dataframe(
    df_filtered_tasks, 
    height=300,
    hide_index=True,
    key="edited_tasks",
    selection_mode="single-row",
    on_select="rerun" # Rerun the app when a selection changes
)

# Show row count
st.caption(f"Total rows: {len(df_filtered_tasks)}")

selection = st.session_state["edited_tasks"].get("selection", {})
rows = selection.get("rows", [])

filtered = None
selected_row = None
selected_row_index = None

if rows:
    selected_row_index = rows[0] # Get the first selected row index
    selected_row = df_filtered_tasks.iloc[selected_row_index]
    # st.write("Selected Row:")
    #st.write(f"Selected Row Task_ID:{selected_row['Task_ID']}")
    # st.write(selected_row)
    filtered = sub_task[sub_task["Key"] == selected_row["Task_ID"]]


# --- Edit Button and Full Page Modal ---
col1, col2 = st.columns([1, 5])
with col1:
    if selected_row is not None:
        if st.button("✏️ Edit Selected Row", key="edit_button"):
            show_edit_modal(selected_row, selected_row['Task_ID'])
    else:
        st.button("✏️ Edit Selected Row", disabled=True, help="Select a row first", key="edit_button")


st.markdown("")
   


# --- Bottom row: Sub Task (left) and Feature (right) ----------
with st.expander("Sub Task", expanded=False):
    if filtered is not None:
        st.dataframe(filtered, width="stretch", height=150)
    else:
        st.dataframe(sub_task, width="stretch", height=150)