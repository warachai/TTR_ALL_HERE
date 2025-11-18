#python -m streamlit run ttr_task_form.py
#http://localhost:8501/?product=DORADO
import streamlit as st
import pandas as pd
import config

from streamlit import session_state as ss
import uuid

st.set_page_config(page_title="Task View", layout="wide")

user_review_list = ["DISCARD", 'REVIEWED' ]  # Example list of users to ignore
ignore_user_review_list = ["DISCARD", ]  # Example list of users to ignore
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
current_tasks = current_tasks[current_tasks['Improvement_Type'] == "TTR"]

# Filter rows based on user_review_list

current_tasks = current_tasks[~current_tasks['User_Review'].isin(ignore_user_review_list)]
current_tasks = current_tasks[current_tasks['Program'].isin(default_programs)]


sub_task = pd.read_csv(config.JIRA_FILE_PATH)


# Define modal function at top level
@st.dialog("Edit Tasks", width="large")
def show_edit_modal(selected_rows):
    st.write("## Edit Task Details")

    # Create a dataframe for editing
    edit_df = pd.DataFrame(selected_rows)

    # Use data_editor for better editing experience with full width
    edited_df = st.data_editor(
        edit_df,
        key="task_editor",
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
        "User_Review": st.column_config.SelectboxColumn(
            "User_Review",
            options=user_review_list,    # 👈 allowed values only
            required=True,
        )
        },

        height=300
    )

    # Button row
    col_save, col_cancel, col_space = st.columns([1, 1, 8])
    with col_save:
        if st.button("💾 Save Changes", key="save_edit"):
            # Update the dataframe with new values from edited_df
            for index, row in edited_df.iterrows():
                task_id = row['Task_ID']
                for col_name in edited_df.columns:
                    current_tasks.loc[
                        current_tasks['Task_ID'] == task_id,
                        col_name
                    ] = row[col_name]

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
        help="OR: Match any word | AND: Match all words, [col]_null to search for null values"
    )

# Apply program filter
if program_filter:  # If any programs are selected
    df_filtered_tasks = current_tasks[current_tasks['Program'].isin(program_filter)]
else:  # If nothing selected, show all
    df_filtered_tasks = current_tasks


# Use filter_text to specify the column name
if filter_text:
    if filter_text.find("_null") != -1:
        colNull = filter_text.replace("_null","")
        if colNull in current_tasks.columns:
            # Filter rows where the specified column has null values
            df_filtered_tasks = df_filtered_tasks[df_filtered_tasks[colNull].isna()]


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





# Display editable dataframe with column configuration
master_tasks = st.dataframe(
    df_filtered_tasks, 
    height=300,
    hide_index=True,
    key="edited_tasks",
    on_select="rerun" # Rerun the app when a selection changes
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


# --- Edit Button and Full Page Modal ---
col1, col2 = st.columns([1, 5])
with col1:
    if rows:
        selected_rows = df_filtered_tasks.iloc[rows].to_dict(orient="records")
        if st.button("✏️ Edit Selected Rows", key="edit_button"):
            show_edit_modal(selected_rows)
    else:
        st.button("✏️ Edit Selected Rows", disabled=True, help="Select rows first", key="edit_button")


st.markdown("")
   


# --- Bottom row: Sub Task (left) and Feature (right) ----------
with st.expander("Sub Task", expanded=False):
    if df_filteredSubTask is not None:
        st.dataframe(df_filteredSubTask, width="stretch", height=150)
    else:
        st.dataframe(sub_task, width="stretch", height=150)