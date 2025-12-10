#python -m streamlit run ttr_task_form.py
#http://localhost:8501/?product=DORADO
import streamlit as st
import pandas as pd
import os
from pathlib import Path
import plotly.express as px
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from st_aggrid.shared import JsCode
import json
import config
import json

from streamlit import session_state as ss
import uuid

st.set_page_config(page_title="Task View", layout="wide")
required_cols_plan = ['OPERATION', 'Task_name', 'Saving']
user_review_list = ["DISCARD", 'REVIEWED' ]  # Example list of users to ignore
ignore_user_review_list = ["DISCARD", ]  # Example list of users to ignore
# ---------------------------------------------------------
# Dummy data – replace with your own
# ---------------------------------------------------------
default_programs = ["DORADO", "MARLIN", "MARLIN BP", "SUMMIT", "MARLINBP"]
params = st.query_params
selected_product = params.get("product", [None])
if len(selected_product)>3:
    default_programs = [selected_product]


# Load data (will reload when session state changes)
current_tasks = pd.read_csv(config.PLAN_MASTER_FILE)
current_tasks_org = current_tasks.copy()

# Ensure required column exists
if 'User_Review' not in current_tasks.columns:
    current_tasks['User_Review'] = ""  # initialize with blank values

# Filter rows based on user_review_list
current_tasks = current_tasks[current_tasks['Program'].isin(default_programs)]


sub_task = pd.read_csv(config.JIRA_FILE_PATH)

def getPCOColumnOrder():
    selected = {}
    #pco_selected = {}
    pco_selected = []
    order_num = 0
    params_local = st.query_params  # safe to call here; independent of later parsing
    for idx in range(2):
        prog_raw = params_local.get(f"prog_{idx}", "NONE")
        cfg_raw = params_local.get(f"cfg_{idx}", "NONE")
        pco_raw = params_local.get(f"pco_{idx}", "NONE")
        # Handle list values (Streamlit may store as list) and normalize
        def _norm(v):
            if isinstance(v, list):
                return v[0] if v else "NONE"
            return v if isinstance(v, str) else "NONE"
        selected[idx] = {
            "program": _norm(prog_raw),
            "config": _norm(cfg_raw),
            "pco": _norm(pco_raw),
        }
        pco_selected.append(_norm(pco_raw))
        #pco_selected[_norm(pco_raw)] = order_num
        order_num += 1
    return pco_selected

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

st.title("Plan View")

# --- Current Task List + centered filter box -----------------
st.subheader("Current Plan List")

def getPlanIDfromTaskName(df, task_name):
    """Get Parent ID from Task Name"""

    matched_rows = df[df['Task_name'] == task_name]['PlanID']
    return matched_rows

def getParentIDfromTaskName(df, task_name):
    """Get Parent ID from Task Name"""
    matched_rows = df[df['Task_name'] == task_name]['ParentID']

    return matched_rows

def getDataFrameFromMasterPlan(df, task_name):
    """Get Parent ID from Task Name"""
    matched_rows = df[df['Task_name'] == task_name]['PlanID']

    dfSelectedTask = df[df['ParentID'].isin(matched_rows)].copy()
 
    return dfSelectedTask

c1, c1_1,c2, c3 = st.columns([1,1, 2, 1])
with c1:
    program_filter = st.multiselect(
        "Select Product(s)",
        ["DORADO", "MARLIN", "MARLIN BP", "SUMMIT"],
        default=[]
    )
    # Build master plan list: rows with empty Parent (top-level) and optional program filter
    if 'ParentID' not in current_tasks.columns:
        current_tasks['ParentID'] = ""  # ensure column exists
    if 'Task_name' not in current_tasks.columns:
        # Fallback: try common alternative naming
        alt_col = next((c for c in current_tasks.columns if c.lower() == 'task_name'), None)
        if alt_col and alt_col != 'Task_name':
            current_tasks.rename(columns={alt_col: 'Task_name'}, inplace=True)
        else:
            current_tasks['Task_name'] = ''

    base_df = current_tasks.copy()
    if program_filter:
        base_df = base_df[base_df['Program'].isin(program_filter)]
    base_df = base_df[base_df['ParentID'].isna() | (base_df['ParentID'] == "")]
    
    master_plan_list = base_df['Task_name'].dropna().unique().tolist()


with c1_1:
    master_plan_filter = st.multiselect(
        "Select Master Plan",
        master_plan_list,
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


if master_plan_filter:
    
    master_task_ParentID = getPlanIDfromTaskName(current_tasks ,master_plan_filter[0])

    current_tasks = current_tasks[current_tasks['ParentID'].isin(master_task_ParentID)]

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
with st.expander("Plan Validation", expanded=False):

    test_time_folder = config.TT_HISTORY_PATH

    def add_violin_labels(
        fig,
        df,
        x_col: str,
        y_col: str,
        color_col: str,
        label_metric: str = "mean",
    ):
        """
        Add one annotation per (x, color) subgroup, visually centered on
        each violin using xshift.

        label_metric: 'median' or 'mean'
        """
        # Determine how many sub-groups (colors) we have
        levels = list(df[color_col].dropna().unique())
        levels.sort()
        n_levels = len(levels)
        level_pos = {lv: i for i, lv in enumerate(levels)}

        base_xshift = 40  # pixels of horizontal separation between labels

        # Group by OPERATION + color (sub group)
        grouped = df.groupby([x_col, color_col], dropna=True)

        for (x_val, c_val), d in grouped:
            if d.empty:
                continue

            # Compute metric value (mean or median) but use PCO (color value) as label instead of generic name
            if label_metric == "mean":
                val = d[y_col].mean()
            else:
                val = d[y_col].median()
            metric_label = c_val  # Show the PCO/group value in the annotation
            metric_label = ""

            count = len(d)

            # Compute xshift so each label sits over *its* violin
            idx = level_pos[c_val]
            # center around 0 → e.g. for 2 levels: -0.5, +0.5 → -20, +20
            rel = idx - (n_levels - 1) / 2
            xshift = rel * base_xshift

            fig.add_annotation(
                x=x_val,
                y=val,
                xref="x",
                yref="y",
                text=f"{metric_label}{val:.1f}<br>{count}",  # e.g. PCO2=12.3
                showarrow=False,
                xshift=xshift,
                yshift=15,  # increase vertical gap above point
                align="center",
                font=dict(size=14, color="black"),  # larger label size
            )

        return fig

    # Function to get all programs (folders in test_time_folder)
    def get_all_programs() -> list:
        """Scan test_time_folder for all Program subdirectories."""
        if not os.path.isdir(test_time_folder):
            return ["NONE"]
        try:
            programs = [d for d in os.listdir(test_time_folder) if os.path.isdir(os.path.join(test_time_folder, d))]
            programs = sorted(programs) if programs else ["NONE"]
            return ["NONE"] + programs if programs else ["NONE"]
        except Exception as e:
            st.debug(f"Error scanning programs: {e}")
            return ["NONE"]

    # Function to get config options from folder structure
    def get_config_options_for_program(program: str) -> list:
        """Scan test_time_folder/Program for subdirectories (configs)."""
        if program == "NONE":
            return ["NONE"]
        program_path = os.path.join(test_time_folder, program)
        if not os.path.isdir(program_path):
            return ["NONE"]
        try:
            configs = [d for d in os.listdir(program_path) if os.path.isdir(os.path.join(program_path, d))]
            configs = sorted(configs) if configs else ["NONE"]
            return ["NONE"] + configs if configs else ["NONE"]
        except Exception as e:
            st.debug(f"Error scanning configs for {program}: {e}")
            return ["NONE"]

    # Function to get PCO options from folder structure
    def get_pco_options_for_config(program: str, config: str) -> list:
        """Scan test_time_folder/Program/Config for subdirectories (PCOs)."""
        if program == "NONE" or config == "NONE":
            return ["NONE"]
        config_path = os.path.join(test_time_folder, program, config)
        if not os.path.isdir(config_path):
            return ["NONE"]
        try:
            pcos = [d for d in os.listdir(config_path) if os.path.isdir(os.path.join(config_path, d))]
            pcos = sorted(pcos) if pcos else ["NONE"]
            return ["NONE"] + pcos if pcos else ["NONE"]
        except Exception as e:
            st.debug(f"Error scanning PCOs for {program}/{config}: {e}")
            return ["NONE"]
    # -------------------------------------------------------------------
    # Load and merge all DRV_INV.csv files from folder hierarchy
    # -------------------------------------------------------------------
    def load_merged_test_time_by_test():
        """
        Recursively find all TEST_TIME_BY_STATE_ALL_sum.csv files in test_time_folder.
        Read each file and add program, config, pco columns based on folder path.
        Map DRV_INV columns to filter-compatible names.
        Merge all into single dataframe.
        """
        dfs = []

        source_file = "TEST_TIME_BY_TEST_ALL_sum_operation_summary.csv"

        # Print user selected config for debugging
        # Collect selected values into a dict for easier access
        # Build selected map from current URL/query parameter defaults instead of session state
        # so it reflects the user's explicit selections (user settings) rather than transient session values.
        selected = {}
        params_local = st.query_params  # safe to call here; independent of later parsing
        for idx in range(2):
            prog_raw = params_local.get(f"prog_{idx}", "NONE")
            cfg_raw = params_local.get(f"cfg_{idx}", "NONE")
            pco_raw = params_local.get(f"pco_{idx}", "NONE")
            # Handle list values (Streamlit may store as list) and normalize
            def _norm(v):
                if isinstance(v, list):
                    return v[0] if v else "NONE"
                return v if isinstance(v, str) else "NONE"
            selected[idx] = {
                "program": _norm(prog_raw),
                "config": _norm(cfg_raw),
                "pco": _norm(pco_raw),
            }

        # Example: Check if path exists for each selected slot
        user_selected = []
        for idx, sel in selected.items():
            prog, cfg, pco = sel["program"], sel["config"], sel["pco"]
            if prog != "NONE" and cfg != "NONE" and pco != "NONE":
                path = os.path.join(test_time_folder, prog, cfg, pco, source_file)
                if path not in user_selected:
                    user_selected.append(path)
                #st.write("path :",path)

        
        for root, dirs, files in os.walk(test_time_folder):
            if source_file in files:
                filepath = os.path.join(root, source_file)
                
                # Extract hierarchy from path: R:\Test_Time_Hist\{program}\{config}\{pco}\DRV_INV.csv
                rel_path = os.path.relpath(filepath, test_time_folder)
                parts = rel_path.split(os.sep)


                
                if filepath in user_selected:  # program/config/pco/filename
                    try:
                        df = pd.read_csv(filepath)
                        # Add the three hierarchy columns at the front
                        df.insert(0, "program", parts[0])
                        df.insert(1, "config", parts[1])
                        df.insert(2, "pco", parts[2])
                        
                        # Map DRV_INV columns to filter-compatible names
                        # Use OPERATION as Category, SUB_BUILD_GROUP as SubCat for filtering
                        if "OPERATION" in df.columns:
                            df["Category"] = df["OPERATION"]
                        if "SUB_BUILD_GROUP" in df.columns:
                            df["SubCat"] = df["SUB_BUILD_GROUP"]
                        
                        dfs.append(df)
                    except Exception as e:
                        st.warning(f"Could not load {filepath}: {e}")
        
        if dfs:
            merged_df = pd.concat(dfs, ignore_index=True)
            return merged_df
        else:
            # Fallback to example data if no DRV_INV.csv files found
            #st.warning("No DRV_INV.csv files found. Using example data.")
            data = {
                "program":  ["SUMMIT"] * 4 + ["MARLIN"] * 4 + ["MARLIN"] * 4,
                "config":   ["CMR"] * 4 + ["SMR"] * 4 + ["HSMR"] * 4,
                "pco":      ["PYTHON_373"] * 4 + ["PCO2"] * 4 + ["PCO3"] * 4,
                "Category": ["CatA", "CatB", "CatC", "CatA"] * 3,
                "SubCat":   ["SC1", "SC2", "SC3", "SC4"] * 3,
                "TEST_TIME": [10, 12, 20, 16, 9, 11, 14, 13, 8, 10, 15, 18],
            }
            return pd.DataFrame(data)
    
    # -------------------------------------------------------------------
    # Load and merge all DRV_INV.csv files from folder hierarchy
    # -------------------------------------------------------------------
    def load_merged_test_time_by_state():
        """
        Recursively find all TEST_TIME_BY_STATE_ALL_sum.csv files in test_time_folder.
        Read each file and add program, config, pco columns based on folder path.
        Map DRV_INV columns to filter-compatible names.
        Merge all into single dataframe.
        """
        dfs = []

        source_file = "TEST_TIME_BY_STATE_ALL_sum_operation_summary.csv"

        # Print user selected config for debugging
        # Collect selected values into a dict for easier access
        # Build selected map from current URL/query parameter defaults instead of session state
        # so it reflects the user's explicit selections (user settings) rather than transient session values.
        selected = {}
        params_local = st.query_params  # safe to call here; independent of later parsing
        for idx in range(2):
            prog_raw = params_local.get(f"prog_{idx}", "NONE")
            cfg_raw = params_local.get(f"cfg_{idx}", "NONE")
            pco_raw = params_local.get(f"pco_{idx}", "NONE")
            # Handle list values (Streamlit may store as list) and normalize
            def _norm(v):
                if isinstance(v, list):
                    return v[0] if v else "NONE"
                return v if isinstance(v, str) else "NONE"
            selected[idx] = {
                "program": _norm(prog_raw),
                "config": _norm(cfg_raw),
                "pco": _norm(pco_raw),
            }

        # Example: Check if path exists for each selected slot
        user_selected = []
        for idx, sel in selected.items():
            prog, cfg, pco = sel["program"], sel["config"], sel["pco"]
            if prog != "NONE" and cfg != "NONE" and pco != "NONE":
                path = os.path.join(test_time_folder, prog, cfg, pco, source_file)
                if path not in user_selected:
                    user_selected.append(path)
                #st.write("path :",path)

        
        for root, dirs, files in os.walk(test_time_folder):
            if source_file in files:
                filepath = os.path.join(root, source_file)
                
                # Extract hierarchy from path: R:\Test_Time_Hist\{program}\{config}\{pco}\DRV_INV.csv
                rel_path = os.path.relpath(filepath, test_time_folder)
                parts = rel_path.split(os.sep)


                
                if filepath in user_selected:  # program/config/pco/filename
                    try:
                        df = pd.read_csv(filepath)
                        # Add the three hierarchy columns at the front
                        df.insert(0, "program", parts[0])
                        df.insert(1, "config", parts[1])
                        df.insert(2, "pco", parts[2])
                        
                        # Map DRV_INV columns to filter-compatible names
                        # Use OPERATION as Category, SUB_BUILD_GROUP as SubCat for filtering
                        if "OPERATION" in df.columns:
                            df["Category"] = df["OPERATION"]
                        if "SUB_BUILD_GROUP" in df.columns:
                            df["SubCat"] = df["SUB_BUILD_GROUP"]
                        
                        dfs.append(df)
                    except Exception as e:
                        st.warning(f"Could not load {filepath}: {e}")
        
        if dfs:
            merged_df = pd.concat(dfs, ignore_index=True)
            return merged_df
        else:
            # Fallback to example data if no DRV_INV.csv files found
            #st.warning("No DRV_INV.csv files found. Using example data.")
            data = {
                "program":  ["SUMMIT"] * 4 + ["MARLIN"] * 4 + ["MARLIN"] * 4,
                "config":   ["CMR"] * 4 + ["SMR"] * 4 + ["HSMR"] * 4,
                "pco":      ["PYTHON_373"] * 4 + ["PCO2"] * 4 + ["PCO3"] * 4,
                "Category": ["CatA", "CatB", "CatC", "CatA"] * 3,
                "SubCat":   ["SC1", "SC2", "SC3", "SC4"] * 3,
                "TEST_TIME": [10, 12, 20, 16, 9, 11, 14, 13, 8, 10, 15, 18],
            }
            return pd.DataFrame(data)

    # -------------------------------------------------------------------
    # Load and merge all DRV_INV.csv files from folder hierarchy
    # -------------------------------------------------------------------
    def load_merged_test_time_by_state_detail():
        """
        Recursively find all TEST_TIME_BY_STATE_ALL_sum.csv files in test_time_folder.
        Read each file and add program, config, pco columns based on folder path.
        Map DRV_INV columns to filter-compatible names.
        Merge all into single dataframe.
        """
        dfs = []

        source_file = "TEST_TIME_BY_STATE_ALL_sum.csv"

        # Print user selected config for debugging
        # Collect selected values into a dict for easier access
        # Build selected map from current URL/query parameter defaults instead of session state
        # so it reflects the user's explicit selections (user settings) rather than transient session values.
        selected = {}
        params_local = st.query_params  # safe to call here; independent of later parsing
        for idx in range(2):
            prog_raw = params_local.get(f"prog_{idx}", "NONE")
            cfg_raw = params_local.get(f"cfg_{idx}", "NONE")
            pco_raw = params_local.get(f"pco_{idx}", "NONE")
            # Handle list values (Streamlit may store as list) and normalize
            def _norm(v):
                if isinstance(v, list):
                    return v[0] if v else "NONE"
                return v if isinstance(v, str) else "NONE"
            selected[idx] = {
                "program": _norm(prog_raw),
                "config": _norm(cfg_raw),
                "pco": _norm(pco_raw),
            }

        # Example: Check if path exists for each selected slot
        user_selected = []
        for idx, sel in selected.items():
            prog, cfg, pco = sel["program"], sel["config"], sel["pco"]
            if prog != "NONE" and cfg != "NONE" and pco != "NONE":
                path = os.path.join(test_time_folder, prog, cfg, pco, source_file)
                if path not in user_selected:
                    user_selected.append(path)
                #st.write("path :",path)

        
        for root, dirs, files in os.walk(test_time_folder):
            if source_file in files:
                filepath = os.path.join(root, source_file)
                
                # Extract hierarchy from path: R:\Test_Time_Hist\{program}\{config}\{pco}\DRV_INV.csv
                rel_path = os.path.relpath(filepath, test_time_folder)
                parts = rel_path.split(os.sep)


                
                if filepath in user_selected:  # program/config/pco/filename
                    try:
                        df = pd.read_csv(filepath)
                        # Add the three hierarchy columns at the front
                        df.insert(0, "program", parts[0])
                        df.insert(1, "config", parts[1])
                        df.insert(2, "pco", parts[2])
                        
                        # Map DRV_INV columns to filter-compatible names
                        # Use OPERATION as Category, SUB_BUILD_GROUP as SubCat for filtering
                        if "OPERATION" in df.columns:
                            df["Category"] = df["OPERATION"]
                        if "SUB_BUILD_GROUP" in df.columns:
                            df["SubCat"] = df["SUB_BUILD_GROUP"]
                        
                        dfs.append(df)
                    except Exception as e:
                        st.warning(f"Could not load {filepath}: {e}")
        
        if dfs:
            merged_df = pd.concat(dfs, ignore_index=True)
            return merged_df
        else:
            # Fallback to example data if no DRV_INV.csv files found
            #st.warning("No DRV_INV.csv files found. Using example data.")
            data = {
                "program":  ["SUMMIT"] * 4 + ["MARLIN"] * 4 + ["MARLIN"] * 4,
                "config":   ["CMR"] * 4 + ["SMR"] * 4 + ["HSMR"] * 4,
                "pco":      ["PYTHON_373"] * 4 + ["PCO2"] * 4 + ["PCO3"] * 4,
                "Category": ["CatA", "CatB", "CatC", "CatA"] * 3,
                "SubCat":   ["SC1", "SC2", "SC3", "SC4"] * 3,
                "TEST_TIME": [10, 12, 20, 16, 9, 11, 14, 13, 8, 10, 15, 18],
            }
            return pd.DataFrame(data)
        
    # -------------------------------------------------------------------
    # Load and merge all DRV_INV.csv files from folder hierarchy
    # -------------------------------------------------------------------
    def load_merged_drv_inv():
        """
        Recursively find all DRV_INV.csv files in test_time_folder.
        Read each file and add program, config, pco columns based on folder path.
        Map DRV_INV columns to filter-compatible names.
        Merge all into single dataframe.
        """
        dfs = []

        # Print user selected config for debugging
        # Collect selected values into a dict for easier access
        # Build selected map from current URL/query parameter defaults instead of session state
        # so it reflects the user's explicit selections (user settings) rather than transient session values.
        selected = {}
        params_local = st.query_params  # safe to call here; independent of later parsing
        for idx in range(2):
            prog_raw = params_local.get(f"prog_{idx}", "NONE")
            cfg_raw = params_local.get(f"cfg_{idx}", "NONE")
            pco_raw = params_local.get(f"pco_{idx}", "NONE")
            # Handle list values (Streamlit may store as list) and normalize
            def _norm(v):
                if isinstance(v, list):
                    return v[0] if v else "NONE"
                return v if isinstance(v, str) else "NONE"
            selected[idx] = {
                "program": _norm(prog_raw),
                "config": _norm(cfg_raw),
                "pco": _norm(pco_raw),
            }

        # Example: Check if path exists for each selected slot
        user_selected = []
        for idx, sel in selected.items():
            prog, cfg, pco = sel["program"], sel["config"], sel["pco"]
            if prog != "NONE" and cfg != "NONE" and pco != "NONE":
                path = os.path.join(test_time_folder, prog, cfg, pco, "DRV_INV.csv")
                if path not in user_selected:
                    user_selected.append(path)
                #st.write("path :",path)

        
        for root, dirs, files in os.walk(test_time_folder):
            if "DRV_INV.csv" in files:
                filepath = os.path.join(root, "DRV_INV.csv")
                
                # Extract hierarchy from path: R:\Test_Time_Hist\{program}\{config}\{pco}\DRV_INV.csv
                rel_path = os.path.relpath(filepath, test_time_folder)
                parts = rel_path.split(os.sep)


                
                if filepath in user_selected:  # program/config/pco/filename
                    try:
                        df = pd.read_csv(filepath)
                        # Add the three hierarchy columns at the front
                        df.insert(0, "program", parts[0])
                        df.insert(1, "config", parts[1])
                        df.insert(2, "pco", parts[2])
                        
                        # Map DRV_INV columns to filter-compatible names
                        # Use OPERATION as Category, SUB_BUILD_GROUP as SubCat for filtering
                        if "OPERATION" in df.columns:
                            df["Category"] = df["OPERATION"]
                        if "SUB_BUILD_GROUP" in df.columns:
                            df["SubCat"] = df["SUB_BUILD_GROUP"]
                        
                        dfs.append(df)
                    except Exception as e:
                        st.warning(f"Could not load {filepath}: {e}")
        
        if dfs:
            merged_df = pd.concat(dfs, ignore_index=True)
            return merged_df
        else:
            # Fallback to example data if no DRV_INV.csv files found
            #st.warning("No DRV_INV.csv files found. Using example data.")
            data = {
                "program":  ["SUMMIT"] * 4 + ["MARLIN"] * 4 + ["MARLIN"] * 4,
                "config":   ["CMR"] * 4 + ["SMR"] * 4 + ["HSMR"] * 4,
                "pco":      ["PYTHON_373"] * 4 + ["PCO2"] * 4 + ["PCO3"] * 4,
                "Category": ["CatA", "CatB", "CatC", "CatA"] * 3,
                "SubCat":   ["SC1", "SC2", "SC3", "SC4"] * 3,
                "TEST_TIME": [10, 12, 20, 16, 9, 11, 14, 13, 8, 10, 15, 18],
            }
            return pd.DataFrame(data)

    df_raw = load_merged_drv_inv()

    # -------------------------------------------------------------------
    # Styles
    # -------------------------------------------------------------------
    st.markdown("""
    <style>
    .program-card {
        border: 2px solid #0d4f63;
        border-radius: 4px;
        padding: 0.8rem 1.0rem 0.8rem 1.0rem;
        margin-bottom: 1.0rem;
    }
    .program-title {
        font-size: 1.8rem;
        font-weight: 600;
        margin-bottom: 0.3rem;
    }
    .section-title {
        font-size: 1.8rem;
        font-weight: 600;
        margin-bottom: 0.2rem;
        margin-top: 0.6rem;
    }
    .footer-note {
        text-align: center;
        color: #6b6b6b;
        font-size: 0.75rem;
        margin-top: 1.2rem;
    }
    </style>
    """, unsafe_allow_html=True)

  
    # Parse URL query params for pre-filling selectors (prog_0, cfg_0, pco_0, prog_1, cfg_1, pco_1, prog_2, cfg_2, pco_2)
    params = st.query_params
    query_selections = {}
    has_query_params = False
    for slot_idx in range(2):
        prog_key = f"prog_{slot_idx}"
        cfg_key = f"cfg_{slot_idx}"
        pco_key = f"pco_{slot_idx}"
        prog_val = params.get(prog_key, ["NONE"])[0] if isinstance(params.get(prog_key, ["NONE"]), list) else params.get(prog_key, "NONE")
        cfg_val = params.get(cfg_key, ["NONE"])[0] if isinstance(params.get(cfg_key, ["NONE"]), list) else params.get(cfg_key, "NONE")
        pco_val = params.get(pco_key, ["NONE"])[0] if isinstance(params.get(pco_key, ["NONE"]), list) else params.get(pco_key, "NONE")
        query_selections[slot_idx] = (prog_val, cfg_val, pco_val)
        if any(v != "NONE" for v in (prog_val, cfg_val, pco_val)):
            has_query_params = True

    # -------------------------------------------------------------------
    # TOP BOX – combo boxes for Program / Config Type / PCO
    # -------------------------------------------------------------------

    program_options = ["NONE", "SUMMIT", "MARLIN", "MARLIN BP", "DORADO"]
    config_options  = ["NONE", "CMR", "SMR", "HSMR"]
    pco_options     = ["NONE", "PCO1", "PCO2", "PCO3"]

    # Dynamically load all programs from folder structure
    program_options = get_all_programs()

    # Initialize session state for program selection tracking (used to update config options dynamically)
    if "last_program_selected" not in st.session_state:
        st.session_state.last_program_selected = {}  # {slot_idx: program}



    with st.expander("Programs / Config / PCO", expanded=False):
        with st.container():
            st.markdown('<div class="program-card">', unsafe_allow_html=True)
            col1, col2 = st.columns(2)

            def program_block(col, idx: int):
                """One column: Program / Config / PCO as combo boxes."""
                with col:
                    st.subheader(f"Slot {idx+1}")

                    prog_default = query_selections.get(idx, ("NONE", "NONE", "NONE"))[0]
                    cfg_default = query_selections.get(idx, ("NONE", "NONE", "NONE"))[1]
                    pco_default = query_selections.get(idx, ("NONE", "NONE", "NONE"))[2]

                    prog_idx = program_options.index(prog_default) if prog_default in program_options else 0

                    prog = st.selectbox(
                        "Program",
                        program_options,
                        index=prog_idx,
                        key=f"prog_{idx}",
                    )

                    available_configs = get_config_options_for_program(prog)
                    cfg_idx = available_configs.index(cfg_default) if cfg_default in available_configs else 0
                    cfg = st.selectbox(
                        "Config Type",
                        available_configs,
                        index=cfg_idx,
                        key=f"cfg_{idx}",
                    )

                    available_pcos = get_pco_options_for_config(prog, cfg)
                    pco_idx = available_pcos.index(pco_default) if pco_default in available_pcos else 0
                    pco = st.selectbox(
                        "Eval",
                        available_pcos,
                        index=pco_idx,
                        key=f"pco_{idx}",
                    )
                    return prog, cfg, pco

            sel1 = program_block(col1, 0)
            sel2 = program_block(col2, 1)

            query_btn_pressed = st.button(
                "Query Data",
                key="query_data_btn",
                help="Apply current selections and update URL with non-NONE values"
            )
            if query_btn_pressed:



                param_pairs = []
                for idx, (prog, cfg, pco) in enumerate([sel1, sel2]):
                    if prog != "NONE":
                        param_pairs.append((f"prog_{idx}", prog))
                    if cfg != "NONE":
                        param_pairs.append((f"cfg_{idx}", cfg))
                    if pco != "NONE":
                        param_pairs.append((f"pco_{idx}", pco))
                try:
                    st.query_params.clear()
                    for k, v in param_pairs:
                        st.query_params[k] = v
                except Exception:
                    if param_pairs:
                        st.experimental_set_query_params(**{k: v for k, v in param_pairs})
                    else:
                        st.experimental_set_query_params()
                st.session_state.pop("tt_filtered", None)
                st.rerun()
            auto_query = has_query_params and "tt_filtered" not in st.session_state

            if query_btn_pressed or auto_query:
                def slot_mask(slot):
                    prog_v, cfg_v, pco_v = slot
                    m = pd.Series(True, index=df_raw.index)
                    if prog_v != "NONE":
                        m &= df_raw['program'] == prog_v
                    if cfg_v != "NONE":
                        m &= df_raw['config'] == cfg_v
                    if pco_v != "NONE":
                        m &= df_raw['pco'] == pco_v
                    return m
                masks = []
                for slot in (sel1, sel2):
                    if any(v != "NONE" for v in slot):
                        masks.append(slot_mask(slot))
                if masks:
                    combined = masks[0]
                    for m in masks[1:]:
                        combined |= m
                    filtered_df = df_raw[combined]
                else:
                    filtered_df = pd.DataFrame(columns=df_raw.columns)
                st.session_state.tt_filtered = filtered_df

            st.markdown('</div>', unsafe_allow_html=True)

    # (you can later use sel1/sel2 to filter df_raw)

    # -------------------------------------------------------------------
    # Filter helpers
    # -------------------------------------------------------------------
    def apply_filter(df, text, logic="OR", search_cols=None):
        if not text:
            return df
        if search_cols is None:
            search_cols = df.columns

        terms = [t.strip() for t in text.split() if t.strip()]
        if not terms:
            return df

        df_s = df.copy()
        df_s[search_cols] = df_s[search_cols].astype(str)

        mask = None
        for term in terms:
            term_mask = df_s[search_cols].apply(
                lambda c: c.str.contains(term, case=False, na=False)
            ).any(axis=1)
            if mask is None:
                mask = term_mask
            elif logic == "AND":
                mask &= term_mask
            else:
                mask |= term_mask
        return df[mask]

    def apply_filter_flex(df, text, logic="OR", search_cols=None, col_alias=None):
        """
        Flexible text filter:

        - Free terms (no ":") search across search_cols (or all columns if None).
        - Column-specific terms use the syntax COL:VALUE, e.g. STATE:PASS OP:10

        Parameters
        ----------
        df : pd.DataFrame
        text : str
            User input string.
        logic : "AND" or "OR"
            How to combine multiple free terms.
        search_cols : list[str] or None
            Columns for free-text search. If None, uses all df.columns.
        col_alias : dict[str,str] or None
            Optional mapping from short names to real column names,
            e.g. {"STATE": "STATE_NAME", "OP": "OPERATION"}.
        """
        import pandas as pd


        if not text:
            return df

        if search_cols is None:
            search_cols = list(df.columns)

        if col_alias is None:
            col_alias = {}

        # -------------------------------------------------
        # 1) Split into tokens: some may be COL:VALUE, others just VALUE
        # -------------------------------------------------
        tokens = [t.strip() for t in text.split() if t.strip()]
        if not tokens:
            return df

        df_s = df.copy()
        df_s = df_s.astype(str)

        # separate into targeted (col:value) and free terms
        targeted = []   # (column_name, value)
        free_terms = [] # just values

        for tok in tokens:
            if ":" in tok:
                key, val = tok.split(":", 1)
                key = key.strip()
                val = val.strip()
                if not val:
                    continue
                # map alias (e.g. "STATE" -> "STATE_NAME")
                col = col_alias.get(key, key)
                if col in df_s.columns:
                    targeted.append((col, val))
            else:
                free_terms.append(tok)

        # -------------------------------------------------
        # 2) Build mask for targeted column filters (all AND together)
        # -------------------------------------------------
        targeted_mask = None
        for col, val in targeted:
            m = df_s[col].str.contains(val, case=False, na=False)
            targeted_mask = m if targeted_mask is None else (targeted_mask & m)

        # -------------------------------------------------
        # 3) Build mask for free terms across search_cols
        # -------------------------------------------------
        free_mask = None
        if free_terms:
            sub = df_s[search_cols]
            for term in free_terms:
                m = sub.apply(lambda c: c.str.contains(term, case=False, na=False)).any(axis=1)
                if free_mask is None:
                    free_mask = m
                elif logic == "AND":
                    free_mask &= m
                else:  # "OR"
                    free_mask |= m

        # -------------------------------------------------
        # 4) Combine targeted + free
        # -------------------------------------------------
        if targeted_mask is not None and free_mask is not None:
            final_mask = targeted_mask & free_mask  # both must match
        elif targeted_mask is not None:
            final_mask = targeted_mask
        elif free_mask is not None:
            final_mask = free_mask
        else:
            return df

        return df[final_mask]

    def test_time_block(title, df, key_prefix, groupby_cols=None):
        st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            filter_text_tt_op = st.text_input(
            "Filter Text Box",
            "",
            placeholder="Search in all columns..."
            ,
            key=f"{key_prefix}_filter_text"
            )

        with c2:
            logic = st.radio(
            "Search Mode",
            ["OR", "AND"],
            horizontal=True,
            help="OR: Match any word | AND: Match all words, [col]_null to search for null values"
        ,
        key=f"{key_prefix}_search_mode"
        )
            
        df_f = apply_filter(
            df,
            filter_text_tt_op,
            logic,
            ["program", "config", "pco", "Category", "SubCat"],
        )

        # # If no data selected (empty df) show blank table immediately
        # if df_f.empty:
        #     st.dataframe(pd.DataFrame(), use_container_width=True, height=8*32)
        #     return
        # if not has_query_params:
        #     return

        if groupby_cols:
            # Create pivot table with specified rows, columns, and values
        
            df_view = df_f.pivot_table(
                index=[ "OPERATION"],
                columns=["program","pco", "config"],
                values="TEST_TIME",
                aggfunc=["mean", "count"],
                fill_value=0
            )
            # Flatten MultiIndex columns (mean_pco_config, count_pco_config)
            if isinstance(df_view.columns, pd.MultiIndex):
                flat_cols = []
                for col_tuple in df_view.columns:
                    # col_tuple like (aggfunc, pco, config)
                    agg = str(col_tuple[0])
                    rest = [str(x) for x in col_tuple[1:] if str(x) and str(x) != 'None']
                    flat = agg + (('_' + '_'.join(rest)) if rest else '')
                    flat_cols.append(flat)
                df_view.columns = flat_cols

            df_view.reset_index(inplace=True)


            # If exactly two TestTime columns, compute diff (first minus second)
            #Join from tt_plan to get Task_name and Saving columns
            # Build tt_plan dataframe with necessary columns
            

            if master_plan_filter:
                df_tt_plan = getDataFrameFromMasterPlan(current_tasks_org, master_plan_filter[0])
                df_tt_plan = df_tt_plan[required_cols_plan]

                #st.write(f"Filtered Master Plan tasks: {len(df_tt_plan)} rows")


            else:
                df_tt_plan = current_tasks_org[required_cols_plan]
                #st.write(f"Filtered Master Plan tasks else: {len(df_tt_plan)} rows")


            df_tt_plan = apply_filter(
            df_tt_plan,
            filter_text_tt_op,
            logic,
            required_cols_plan,
            ) 
            # st.write(f"Filtered Master Plan tasks apply_filter: {len(df_tt_plan)} rows")     
            # st.write(df_tt_plan)     

            # st.write(f"Filtered Master Plan tasks apply_filter: {len(df_tt_plan)} rows")      

            if 'OPERATION' in df_view.columns:
                df_view = pd.concat([df_view, df_tt_plan], ignore_index=True, sort=False)


                # 2) Build AgGrid options
            cols = df_view.columns.tolist()
            #st.write("Column cols:", cols, len(cols)) 
            if len(cols) >= 7:
                column_order = getPCOColumnOrder()
            
                #cols[4], cols[5],cols[6], cols[7]  = cols[6], cols[7], cols[4], cols[5]
                df_view = df_view[cols]
                #st.write("Column order:", column_order, len(column_order)) 
                if len(column_order) == 2:
                    cols = df_view.columns.tolist()
                    # Reorder TestTime and N columns based on column_order
                    #st.write("Columns before reordering:", cols, column_order)
                    if column_order[0] not in cols[1]:
                        #st.write("Reordering columns for display...")
                        cols[1], cols[2],cols[3], cols[4]  = cols[2], cols[1], cols[4], cols[3]
                        df_view = df_view[cols]

            gb = GridOptionsBuilder.from_dataframe(df_view)
            # Add blank value ("") to the end of the custom order
            custom_order = ["SCOPY", "PRE2", "LZR", "CAL", "NTZ", "CAL2", "FNC2", "SPSC2", "CRT2", "PWT", "FIN2", None, "TOTAL"]
            category_order_js = json.dumps(custom_order)

            js_comparator_code = f"""
            function(a, b) {{
                const order = {category_order_js};
                const ai = order.indexOf(a);
                const bi = order.indexOf(b);
                // If value not in the list, push it to the end relative ordering
                return (ai === -1 ? Number.MAX_SAFE_INTEGER : ai) - (bi === -1 ? Number.MAX_SAFE_INTEGER : bi);
            }}
            """
            
            
            gb.configure_column(
            "OPERATION",
            rowGroup=True,
            hide=True,
            sort="asc",
            sortIndex=0,
            comparator=JsCode(js_comparator_code)
            )

            group_name_list = []
            for col in df_view.columns:
                if col.startswith("mean_"):
                    group_name_list.append(col)

            if len(group_name_list) == 2:
                df_view["Diff"] = df_view[group_name_list[0]] - df_view[group_name_list[1]]
                gb.configure_column(
                    "Diff",
                    type=["numericColumn", "customNumericFormat"],
                    valueFormatter="x.toFixed(2)",
                    aggFunc="sum",
                )          
   

            # df_view['Expected'] = df_view['Diff'] - df_view['Saving']

            for col in group_name_list:
                    gb.configure_column(col, aggFunc="sum", type=["numericColumn", "customNumericFormat"], valueFormatter="x.toFixed(2)")

            # gb.configure_column("OPERATION", rowGroup=True, hide=True)
            gb.configure_column('Saving', aggFunc="sum", type=["numericColumn", "customNumericFormat"], valueFormatter="x.toFixed(2)")

            
            # df_view['Expected'] = df_view.apply(
            #     lambda row: row['Diff'] - row['Saving'] if pd.notnull(row.get('Saving')) and pd.notnull(row.get('Diff')) else None,
            #     axis=1
            # )
            #gb.configure_column('Expected',aggFunc="sum", type=["numericColumn", "customNumericFormat"], valueFormatter="x.toFixed(2)")

            # Add TOTAL row summing numeric columns of current display
            numeric_cols = [c for c in df_view.columns if pd.api.types.is_numeric_dtype(df_view[c])]
            if numeric_cols:
                total_row = {col: df_view[col].sum() for col in numeric_cols}
                # For non-numeric columns, set a label for the total row
                for col in df_view.columns:
                    if col not in numeric_cols:
                        if col == "OPERATION":
                            total_row[col] = "TOTAL"
                        else:
                            total_row[col] = ""
                df_view = pd.concat([df_view, pd.DataFrame([total_row])], ignore_index=True)
                # Optionally round float columns for consistency
                for col in numeric_cols:
                    if pd.api.types.is_float_dtype(df_view[col]):
                        df_view[col] = pd.to_numeric(df_view[col], errors='coerce').round(2)

            # General grid options
            gb.configure_grid_options(
                groupDisplayType="multipleColumns",  # show group columns instead of hiding
                groupDefaultExpanded=0,              # 0 = collapsed, -1 = fully expanded
                animateRows=True,
                suppressAggFuncInHeader=False,
            )


            # Autosize columns after grid loads

            # This JS code will autosize all columns after grid is ready
            auto_size_js = JsCode("""
            function(e) {
                let gridApi = e.api;
                gridApi.sizeColumnsToFit();
            }
            """)
            grid_options = gb.build()
            
            # 3) Display AgGrid
            grid_response = AgGrid(
                df_view,
                gridOptions=grid_options,
                enable_enterprise_modules=True,
                update_mode=GridUpdateMode.NO_UPDATE,
                fit_columns_on_grid_load=True,
                height=15*32,
                onGridReady=auto_size_js,
                allow_unsafe_jscode=True,
                custom_js=[
                    JsCode("""
                    function(e) {
                        e.api.sizeColumnsToFit();
                        e.api.gridOptions.api.gridOptionsWrapper.gridOptions.enableRangeSelection = true;
                        e.api.gridOptions.api.gridOptionsWrapper.gridOptions.enableClipboard = true;
                    }
                    """)
                ],
                enableRangeSelection=True,
                enableRowSelection=True,
                rowSelection='multiple',
                suppressRowClickSelection=False,

            )
         
        else:
            df_view = df_f

        
        # Order df_view OPERATION column to match the custom order
        custom_order = ["SCOPY", "PRE2", "LZR", "CAL", "NTZ", "CAL2", "FNC2", "SPSC2", "CRT2", "PWT", "FIN2"]
        if "OPERATION" in df_view.columns:
            df_view["OPERATION"] = pd.Categorical(df_view["OPERATION"], categories=custom_order, ordered=True)
            df_view = df_view.sort_values("OPERATION")
        
        # Download filtered data
        csv = df_f.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Data as CSV",
            data=csv,
            file_name="test_time_by_oper.csv",
            mime="text/csv",
            key=f"{key_prefix}_download_btn"
        )


        #st.dataframe(df_view, use_container_width=True, height=15*32)

        #st.write("MMM debug")
  
    # -------------------------------------------------------------------
    # Middle: Test Time
    # title, df, key_prefix, groupby_cols=None
    # -------------------------------------------------------------------
    df_raw['TEST_TIME'] = pd.to_numeric(df_raw['TEST_TIME'], errors='coerce').fillna(0)
    df_raw['TEST_TIME_org'] = pd.to_numeric(df_raw['TEST_TIME'], errors='coerce').fillna(0)
    df_raw['TEST_TIME'] = df_raw['TEST_TIME'] / 3600

    # Use filtered data if available; else blank when nothing selected
    source_df = st.session_state.get("tt_filtered", pd.DataFrame(columns=df_raw.columns))
    if "TEST_TIME_org" not in source_df.columns:
        source_df['TEST_TIME_org'] = pd.to_numeric(source_df['TEST_TIME'], errors='coerce').fillna(0)
        source_df['TEST_TIME'] = source_df['TEST_TIME_org'] / 3600   

    with st.expander("CMS Config", expanded=False):

        if not source_df.empty and "OPERATION" in source_df.columns and "pco" in source_df.columns and "TEST_TIME" in source_df.columns:
            custom_order = ["SCOPY", "PRE2", "LZR", "CAL", "NTZ", "CAL2", "FNC2", "SPSC2", "CRT2", "PWT", "FIN2"]

            pivot_df = source_df.pivot_table(
                index=["OPERATION"],
                columns=["pco",'CMS_CONFIG'] ,
                values="TEST_TIME",
                aggfunc="count",
                fill_value=0
            ).reset_index()

            column_order = getPCOColumnOrder()
            #st.write("Column order:", column_order, len(column_order))
            if len(column_order) >= 2:
        
                # Sort columns: keep index_cols first, then others by custom order
                index_cols = [["OPERATION", ""]]
                pivot_cols = [c for c in pivot_df.columns ]
                pivot_cols.pop(0)  # remove index col
                # Sort columns by column_order for pco, then by CMS_CONFIG
                sorted_cols = sorted(
                    pivot_cols,
                    key=lambda c: (
                        column_order.index(c[0]) if c[0] in column_order else len(column_order),
                        c[1]
                    )
                )
                #st.write(index_cols + sorted_cols)
                #st.write(pivot_df.columns)
                pivot_df = pivot_df[index_cols + sorted_cols]
                pass

            if "OPERATION" in pivot_df.columns:
                pivot_df["OPERATION"] = pd.Categorical(
                    pivot_df["OPERATION"], categories=custom_order, ordered=True
                )
                pivot_df = pivot_df.sort_values("OPERATION")

            st.dataframe(pivot_df, use_container_width=True)


    with st.expander("Test Time By Operation", expanded=False):
        test_time_block("Test Time", source_df, "tt_overall", groupby_cols=["program", "config", "pco", "Category"])


    # -------------------------------------------------------------------
    # Bottom: Distribution Charts for Selected Data
    # -------------------------------------------------------------------

    with st.expander("Test Time Distribution", expanded=False):
        if not has_query_params:
            st.stop()

        # Use filtered data if available
        if "tt_filtered" in st.session_state and not st.session_state.tt_filtered.empty:
            df_dist = df_raw.copy()
            # Ensure numeric TEST_TIME (already converted to hours earlier, but reconvert safely)

            df_dist['TEST_TIME'] = pd.to_numeric(df_dist['TEST_TIME'], errors='coerce')
            if "TEST_TIME_org" not in df_dist.columns:
                df_dist['TEST_TIME_org'] = pd.to_numeric(df_dist['TEST_TIME'], errors='coerce').fillna(0)
                df_dist['TEST_TIME'] = df_dist['TEST_TIME_org'] / 3600        
            df_dist = df_dist.dropna(subset=['TEST_TIME'])

            # Limit to operations of interest (optional) and remove labels with no data
            custom_order = ["SCOPY", "PRE2", "LZR", "CAL", "NTZ", "CAL2", "FNC2", "SPSC2", "CRT2", "PWT", "FIN2"]
            if "OPERATION" in df_dist.columns:
                df_dist = df_dist[df_dist['OPERATION'].isin(custom_order)]
                # After initial filter, keep only operations that actually have rows
                present_ops = [op for op in custom_order if op in df_dist['OPERATION'].unique()]
                # If user previously wanted reversed order, invert here (currently normal order retained)
                present_ops_display = present_ops  # change to list(reversed(present_ops)) if reversed becomes default again
                df_dist['OPERATION'] = pd.Categorical(df_dist['OPERATION'], categories=present_ops_display, ordered=True)

            # Default plot settings (no user controls): Violin chart, color by pco if available, linear scale, no clipping
            chart_type = "Violin"
            color_arg = "pco" if "pco" in df_dist.columns else None
            y_scale = "linear"

            hover_cols = [c for c in ["SERIAL_NUM", "TRANS_SEQ"] if c in df_dist.columns]

            if df_dist.empty or ("OPERATION" in df_dist.columns and len(df_dist['OPERATION'].cat.categories) == 0):
                st.warning("No data remains for selected filters / clip range.")
                st.stop()
            if chart_type == "Strip (Jitter)":  # unreachable with default violin but kept for easy future toggle
                # Manual jitter using scatter since px.strip doesn't support 'jitter' kwarg in current Plotly version
                # Map OPERATION categories to numeric positions then add random noise
                if "OPERATION" in df_dist.columns:
                    # Use only present operation categories for jitter mapping
                    op_categories = list(df_dist['OPERATION'].cat.categories if isinstance(df_dist['OPERATION'], pd.Categorical) else list(df_dist['OPERATION'].unique()))
                    op_index_map = {op: i for i, op in enumerate(op_categories)}
                    df_dist['_op_x'] = df_dist['OPERATION'].map(op_index_map).astype(float)
                    # Add jitter within +/-0.3 range
                    rng = np.random.default_rng(seed=42)  # deterministic for reproducibility per rerun
                    df_dist['_op_x_jitter'] = df_dist['_op_x'] + rng.uniform(-0.3, 0.3, size=len(df_dist))
                    fig = px.scatter(
                        df_dist,
                        x="_op_x_jitter",
                        y="TEST_TIME",
                        color=color_arg,
                        hover_data=hover_cols + ["OPERATION"],
                    )
                    # Replace numeric axis ticks with category labels
                    fig.update_xaxes(
                        tickmode='array',
                        tickvals=list(range(len(op_categories))),
                        ticktext=op_categories,
                        title_text="Operation"
                    )
                else:
                    fig = px.scatter(df_dist, y="TEST_TIME", color=color_arg, hover_data=hover_cols)
            elif chart_type == "Box":
                fig = px.box(
                    df_dist,
                    x="OPERATION",
                    y="TEST_TIME",
                    color=color_arg,
                    hover_data=hover_cols,
                )
                if "OPERATION" in df_dist.columns and isinstance(df_dist['OPERATION'], pd.Categorical):
                    fig.update_xaxes(categoryorder='array', categoryarray=list(df_dist['OPERATION'].cat.categories))
            else:  # Violin
                
                fig = px.violin(
                    df_dist,
                    x="OPERATION",
                    y="TEST_TIME",
                    color=color_arg,
                    hover_data=hover_cols,
                    box=True,
                    points="all"
                )

                fig = add_violin_labels(
                    fig,
                    df=df_dist,
                    x_col="OPERATION",
                    y_col="TEST_TIME",
                    color_col=color_arg,
                    label_metric="mean",  # or "mean"
                )
                if "OPERATION" in df_dist.columns and isinstance(df_dist['OPERATION'], pd.Categorical):
                    fig.update_xaxes(categoryorder='array', categoryarray=list(df_dist['OPERATION'].cat.categories))

            fig.update_layout(
                yaxis_title="Test Time (hours)",
                xaxis_title="Operation",
                yaxis_type=y_scale,
                legend_title=("pco" if color_arg == "pco" else None),
                margin=dict(l=10, r=10, t=40, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Distribution of TEST_TIME across selected operations and filters.")
        else:
            st.info("No filtered data available. Query data above to view distribution.")

    st.markdown("---")
    # -------------------------------------------------------------------
    # Bottom: Test Time By State
    # -------------------------------------------------------------------
    with st.expander("Test Time By State", expanded=True):
        
        st.markdown('<div class="section-title">Test Time By State</div>', unsafe_allow_html=True)

        if not has_query_params:
            st.info("No query parameters provided. Please select filters above.")
        else:
            df_state = load_merged_test_time_by_state_detail().copy()

            c1_tt, c2_tt, c3_tt = st.columns((3,1,1))
            with c1_tt:
                filter_text_tt_op_tt = st.text_input(
                "Filter Text Box",
                "",
                placeholder="Search in all columns...",
                help=f"- Free terms (no \":\") search across search_cols (or all columns if None).\n- Column-specific terms use the syntax COL:VALUE, e.g. STATE:ZAP \n- [STATE:STATE_NAME, OP:OPERATION, ttr_display]",
                key="filter_text_tt_op_tt_test"
                )

            with c2_tt:
                logic_tt = st.radio(
                "Search Mode",
                ["OR", "AND"],
                horizontal=True,
                help="OR: Match any word | AND: Match all words, [col]_null to search for null values",
                key="logic_tt_test"
                
            )

            with c3_tt:
                view_type_st = st.selectbox(
                        "View Type",
                        ["All State", "TTR State"],
                        index=0,
                        help="Choose how view the state data.",
                        key="view_type_st"
                    )
            # df_state = apply_filter_flex(
            #     df_state,
            #     filter_text_tt_op_tt,
            #     logic_tt,
            #     ["program", "config", "pco", "STATE_NAME", "OPERATION"],
            # )

            required_cols_plan_state = required_cols_plan + ["STATE_NAME",]
            # st.write(f"required_cols_plan_state:",required_cols_plan_state)            
            # st.write(f"Required cols plan state:",current_tasks_org)

            df_tt_plan = getDataFrameFromMasterPlan(current_tasks_org, master_plan_filter[0])
            
            df_tt_plan = df_tt_plan[required_cols_plan_state]
            
                #st.write(f"Filtered Master Plan tasks else: {len(df_tt_plan)} rows")
            def combine_text(row):
                return " | ".join(f"{t} ({s})" for t, s in zip(row["Task_name"], row["Saving"]))
    

            # df_tt_plan = apply_filter(
            #     df_tt_plan,
            #     filter_text_tt_op_tt,
            #     logic_tt,
            #     required_cols_plan_state,
            # ) 

            #st.write(f"Filtered Master Plan tasks: before {len(df_tt_plan)} rows")
            # Group and collect Task_name / Saving into separate list columns with new names
            # Allow OPERATION to be null, but STATE_NAME must not be null
            df_tt_plan_group = (
                df_tt_plan[df_tt_plan["STATE_NAME"].notna()]
                .groupby(["OPERATION", "STATE_NAME"], dropna=False)
                .agg(
                    Task_name_list=("Task_name", list),
                    Saving_list=("Saving", list),
                )
                .reset_index()
                
            )

            df_tt_plan_group = df_tt_plan_group[df_tt_plan_group["OPERATION"].notna() & df_tt_plan_group["STATE_NAME"].notna()]

            #st.write(f"Filtered Master Plan tasks: after {len(df_tt_plan_group)} rows")

            # Build display string safely (avoid returning list/Series which caused assignment ValueError)
            def build_display(task_list, saving_list):
                task_list = task_list if isinstance(task_list, list) else [task_list]
                saving_list = saving_list if isinstance(saving_list, list) else [saving_list]
                return " | ".join(
                    f"{t} ({s})" for t, s in zip(task_list, saving_list)
                )
            
            df_tt_plan_group["ttr_display"] = [
                build_display(t_list, s_list)
                for t_list, s_list in zip(
                    df_tt_plan_group["Task_name_list"], df_tt_plan_group["Saving_list"]
                )
            ]

            # Sum of savings per group (handle non-numeric gracefully)
            def _safe_sum(v):
                try:
                    return sum(x for x in v if pd.notnull(x))
                except TypeError:
                    return None
            df_tt_plan_group["saving_sum"] = df_tt_plan_group["Saving_list"].apply(_safe_sum)

            df_tt_plan_group = df_tt_plan_group.drop(['Task_name_list', 'Saving_list'], axis=1)

            st.write("TASK  ", df_tt_plan_group)
            
            

            if not df_state.empty:

                # Group by state and calculate mean and count
                if "STATE_NAME" in df_state.columns:
                    # Build pivot with multi-index columns (value, aggfunc, pco, config)
                    state_summary = df_state.pivot_table(
                        index=[ "OPERATION", "STATE_NAME"],
                        columns=["program","pco", "config"],
                        values=["TestTime(hrs)", "N"],
                        aggfunc={"TestTime(hrs)": "mean", "N": "sum"},
                        fill_value=0
                    ).reset_index()


                    # Flatten MultiIndex columns into readable single-level names
                    def _flatten(col):
                        if not isinstance(col, tuple):
                            return col
                        parts = [str(p) for p in col if p not in ("", None)]
                        return "_".join(parts)
                    state_summary.columns = [_flatten(c) for c in state_summary.columns]

                    fixed = ["OPERATION", "STATE_NAME"]
                    value_cols = [c for c in state_summary.columns if c not in fixed]

                    # Separate TestTime and N columns by prefix after flattening
                    tt_cols = [c for c in value_cols if c.startswith("TestTime(hrs)_")]
                    n_cols = [c for c in value_cols if c.startswith("N_")]

                    # Reorder columns: fixed + test time + counts
                    state_summary = state_summary[fixed + tt_cols + n_cols]


                    if len(df_tt_plan_group) > 0:
                        state_summary = pd.merge(
                            state_summary,
                            df_tt_plan_group,
                            on=["OPERATION", "STATE_NAME"],
                            how="left"
                        )

                    else:
                        state_summary['ttr_display'] = None
                        state_summary['saving_sum'] = None


                    # Ensure custom order is applied to OPERATION column and sort by STATE_NAME
                    custom_order = ["SCOPY", "PRE2", "LZR", "CAL", "NTZ", "CAL2", "FNC2", "SPSC2", "CRT2", "PWT", "FIN2"]
                    if "OPERATION" in state_summary.columns:
                        state_summary["OPERATION"] = pd.Categorical(
                            state_summary["OPERATION"], categories=custom_order, ordered=True
                        )
                    if "STATE_NAME" in state_summary.columns:
                        state_summary = state_summary.sort_values(by=["OPERATION", "STATE_NAME"])

                    # Display the summary table
                    # Round floating point (TestTime and diff) to 2 decimals

                    column_order = getPCOColumnOrder()
                    #st.write("Column order:", column_order)
                    cols = state_summary.columns.tolist()
                    #st.write("Column cols:", cols)
                    if len(column_order) == 2 and len(cols) >= 8:
                        # Reorder TestTime and N columns based on column_order
                        if column_order[0] not in cols[2]:
                            cols[2], cols[3],cols[4], cols[5]  = cols[3], cols[2], cols[5], cols[4]
                            state_summary = state_summary[cols]  
                    
                    # Separate TestTime and N columns by prefix after flattening
                    value_cols = [c for c in state_summary.columns if c not in fixed]
                    tt_cols = [c for c in value_cols if c.startswith("TestTime(hrs)_")]

                    if len(tt_cols) == 2:
                        state_summary["diff_TestTime(hrs)"] = state_summary[tt_cols[0]] - state_summary[tt_cols[1]]
                    elif len(tt_cols) > 2:
                        st.info("More than two TestTime groups present; diff not computed.")

                    float_like_cols = [c for c in state_summary.columns if c.startswith("TestTime(hrs)_") or c.startswith("diff_TestTime(hrs)")]
                    for c in float_like_cols:
                        if c in state_summary.columns:
                            state_summary[c] = pd.to_numeric(state_summary[c], errors='coerce').round(2)

                    #st.write(f"Before Applying flexible filter... {len(state_summary)}")

                    if view_type_st == "TTR State":
                        state_summary = state_summary[state_summary['ttr_display'].notna()]

                    col_alias_state = {
                        "STATE": "STATE_NAME",
                        "OP": "OPERATION",
                        "ttr": "ttr_display",
                    }
                    state_summary = apply_filter_flex(
                        state_summary,
                        filter_text_tt_op_tt,
                        logic_tt,
                        ["STATE_NAME", "OPERATION", "ttr_display"],
                        col_alias=col_alias_state
                    )
                    #st.write(f"After Applying flexible filter... {len(state_summary)}")

                    

                    # Add TOTAL row summing numeric columns of current display
                    fixed = ["program", "OPERATION", "STATE_NAME"]
                    numeric_cols = [c for c in state_summary.columns if c not in fixed and pd.api.types.is_numeric_dtype(state_summary[c])]
                    if numeric_cols:
                        total_row = {col: state_summary[col].sum() for col in numeric_cols}
                        total_row.update({ "OPERATION": "ALL", "STATE_NAME": "ALL"})
                        state_summary = pd.concat([state_summary, pd.DataFrame([total_row])], ignore_index=True)
                        # Re-round float columns for consistency
                        for c in float_like_cols:
                            if c in state_summary.columns:
                                state_summary[c] = pd.to_numeric(state_summary[c], errors='coerce').round(2)

                    # Display with st.dataframe (no row-level bold styling available); TOTAL row identifiable by ALL values
                    def highlight_last_row(row):
                        if row.name == len(state_summary) - 1:  # last row
                            return ['font-weight: bold; color: Black;'] * len(row)
                        return [''] * len(row)
                    

                    

                    styled = state_summary.style.apply(highlight_last_row, axis=1)

                    # st.dataframe(styled, use_container_width=True, height=15*32)

                    col_widths = {col: {"width": 100} for col in state_summary.columns[2:]}  # columns 1-5 (0-based, skip OPERATION)

                    st.dataframe(styled, use_container_width=True, column_config=col_widths, height=15*32)
                    
                else:
                    st.warning("The dataset does not contain a 'STATE' column.")
            else:
                st.info("No filtered data available. Query data above to view state-wise test time.")

            plot_graph = st.checkbox("Plot Graph", value=False)

            # Use filtered data if available
            if not df_state.empty and len(df_state) < 2500 and plot_graph:
                st.write(f"Generating distribution chart for {len(df_state)} rows.")
                df_dist = df_state.copy()

                df_dist['OP_STATE'] = df_dist['OPERATION'].astype(str) + " - " + df_dist['STATE_NAME'].astype(str)
                
                # Ensure numeric TEST_TIME (already converted to hours earlier, but reconvert safely)


                if "TEST_TIME" not in df_dist.columns:
                    df_dist['TEST_TIME'] = pd.to_numeric(df_dist['TestTime(hrs)'], errors='coerce').fillna(0)
                    

                df_dist['TEST_TIME'] = pd.to_numeric(df_dist['TEST_TIME'], errors='coerce')
                if "TEST_TIME_org" not in df_dist.columns:
                    df_dist['TEST_TIME_org'] = pd.to_numeric(df_dist['TEST_TIME'], errors='coerce').fillna(0)
                    df_dist['TEST_TIME'] = df_dist['TEST_TIME_org']     
                df_dist = df_dist.dropna(subset=['TEST_TIME'])


                # Default plot settings (no user controls): Violin chart, color by pco if available, linear scale, no clipping
                chart_type = "Violin"
                color_arg = "pco" if "pco" in df_dist.columns else None
                y_scale = "linear"

                hover_cols = [c for c in ["SERIAL_NUM", "TRANS_SEQ"] if c in df_dist.columns]
                # st.write(f"Hover columns: {hover_cols}")
                # st.write(f"Hover columns: {df_dist.columns}")


                if df_dist.empty or ("OP_STATE" not in df_dist.columns):
                    st.warning("No data remains for selected filters / clip range.")
                    st.stop()
                if chart_type == "Strip (Jitter)":  # unreachable with default violin but kept for easy future toggle
                    # Manual jitter using scatter since px.strip doesn't support 'jitter' kwarg in current Plotly version
                    # Map OPERATION categories to numeric positions then add random noise
                    if "OP_STATE" in df_dist.columns:
                        # Use only present operation categories for jitter mapping
                        op_categories = list(df_dist['OP_STATE'].cat.categories if isinstance(df_dist['OP_STATE'], pd.Categorical) else list(df_dist['OP_STATE'].unique()))
                        op_index_map = {op: i for i, op in enumerate(op_categories)}
                        df_dist['_op_x'] = df_dist['OP_STATE'].map(op_index_map).astype(float)
                        # Add jitter within +/-0.3 range
                        rng = np.random.default_rng(seed=42)  # deterministic for reproducibility per rerun
                        df_dist['_op_x_jitter'] = df_dist['_op_x'] + rng.uniform(-0.3, 0.3, size=len(df_dist))
                        fig = px.scatter(
                            df_dist,
                            x="_op_x_jitter",
                            y="TEST_TIME",
                            color=color_arg,
                            hover_data=hover_cols + ["STATE_NAME"],
                        )
                        # Replace numeric axis ticks with category labels
                        fig.update_xaxes(
                            tickmode='array',
                            tickvals=list(range(len(op_categories))),
                            ticktext=op_categories,
                            title_text="State Name"
                        )
                    else:
                        fig = px.scatter(df_dist, y="TEST_TIME", color=color_arg, hover_data=hover_cols)
                elif chart_type == "Box":
                    fig = px.box(
                        df_dist,
                        x="OP_STATE",
                        y="TEST_TIME",
                        color=color_arg,
                        hover_data=hover_cols,
                    )
                    if "OP_STATE" in df_dist.columns and isinstance(df_dist['OP_STATE'], pd.Categorical):
                        fig.update_xaxes(categoryorder='array', categoryarray=list(df_dist['OP_STATE'].cat.categories))
                else:  # Violin
                    
                    fig = px.violin(
                        df_dist,
                        x="OP_STATE",
                        y="TEST_TIME",
                        color=color_arg,
                        hover_data=hover_cols,
                        box=True,
                        points="all"
                    )

                    fig = add_violin_labels(
                        fig,
                        df=df_dist,
                        x_col="OP_STATE",
                        y_col="TEST_TIME",
                        color_col=color_arg,
                        label_metric="mean",  # or "mean"
                    )
                    if "OP_STATE" in df_dist.columns and isinstance(df_dist['OP_STATE'], pd.Categorical):
                        fig.update_xaxes(categoryorder='array', categoryarray=list(df_dist['OP_STATE'].cat.categories))

                fig.update_layout(
                    yaxis_title="Test Time (hours)",
                    xaxis_title="Operation",
                    yaxis_type=y_scale,
                    legend_title=("pco" if color_arg == "pco" else None),
                    margin=dict(l=10, r=10, t=40, b=10)
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption("Distribution of TEST_TIME across selected operations and filters.")
            else:
                st.info("No filtered data available. Query data above to view distribution.")

            csv = df_state.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Data as CSV",
                data=csv,
                file_name="test_time_by_state.csv",
                mime="text/csv",
                key="test_time_by_state_download_btn"
            )

    with st.expander("Test Time By Test", expanded=False):
        st.markdown('<div class="section-title">Test Time By Test</div>', unsafe_allow_html=True)

        if not has_query_params:
            st.info("No query parameters provided. Please select filters above.")
        else:
            df_test = load_merged_test_time_by_test().copy()

            c1_tt, c2_tt, c3_tt = st.columns(3)
            col_alias = {
                "STATE": "STATE_NAME",
                "OP": "OPERATION",
                "PARM": "PARAMETER_NAME",
                "TEST": "TEST_NUMBER",
            }
            with c1_tt:
                filter_text_tt_op_tt = st.text_input(
                "Filter Text Box",
                "",
                placeholder="Search in all columns...",
                help=f"- Free terms (no \":\") search across search_cols (or all columns if None).\n- Column-specific terms use the syntax COL:VALUE, e.g. STATE:ZAP TEST:275\n- [STATE:STATE_NAME, OP:OPERATION, ttr:ttr_display]",
                key="filter_text_tt_op_tt"
                )

            with c2_tt:
                view_type = st.selectbox(
                    "View Type",
                    ["By Test", "By Oper"],
                    index=0,
                    help="Choose how to group the test time data.",
                    key="view_type_tt_by_test"
                )
                
            with c3_tt:
                logic_tt_op_tt = st.radio(
                "Search Mode",
                ["OR", "AND"],
                horizontal=True,
                help="OR: Match any word | AND: Match all words, [col]_null to search for null values",
                key="logic_tt_op_tt"
                
                )


            df_test = apply_filter_flex(
                df_test,
                filter_text_tt_op_tt,
                logic_tt_op_tt,
                [ "STATE_NAME", "OPERATION", 'TEST_NUMBER', 'PARAMETER_NAME'],
                col_alias=col_alias
            )

            required_cols_plan_test = required_cols_plan + ["STATE_NAME",'TEST_NUMBER', 'PARAMETER_NAME']

            df_tt_test_plan = getDataFrameFromMasterPlan(current_tasks_org, master_plan_filter[0])
            
            df_tt_test_plan = df_tt_test_plan[required_cols_plan_test]

            df_tt_test_plan = df_tt_test_plan[df_tt_test_plan['TEST_NUMBER'].notna()]
            
            st.write(f"Filtered Master Plan tasks:  {len(df_tt_test_plan)} rows")
            st.write(df_tt_test_plan)

            
            if not df_test.empty:
                # Example: group by a column that exists, e.g. 'OPERATION' or 'STATE_NAME'
                total_group_operation = df_test.groupby(["pco", "config"]).size().reset_index(name='count')
                total_group_operation['GROUP_NAME'] = total_group_operation['pco'] + "_" + total_group_operation['config']
                group_name_list = total_group_operation['GROUP_NAME'].tolist()


                tt_summary = df_test.pivot_table(
                        index=['TEST_NUMBER', 'PARAMETER_NAME',"STATE_NAME", "OPERATION"],
                        columns=["pco", "config"],
                        values=["TestTime(hrs)", "N"],
                        aggfunc={"TestTime(hrs)": "sum", "N": "sum"},
                        fill_value=0
                    ).reset_index()

                # ---------------- Build AgGrid options ----------------
                tt_summary.columns = [
                    "_".join([str(c) for c in col]).strip("_") if isinstance(col, tuple) else col
                    for col in tt_summary.columns
                ]

                # Replace column names containing 'TestTime(hrs)_' with ''
                tt_summary.columns = [
                    col.replace('TestTime(hrs)_', 'TT_') if isinstance(col, str) else col
                    for col in tt_summary.columns
                ]

                test_time_cols = [c for c in tt_summary.columns if c.startswith("TT_")]

                cols = tt_summary.columns.tolist()
                if len(cols) >= 8:
                    column_order = getPCOColumnOrder()
                
                    cols[4], cols[5],cols[6], cols[7]  = cols[6], cols[7], cols[4], cols[5]
                    tt_summary = tt_summary[cols]
                    #st.write("Column order:", column_order, len(column_order)) 
                    if len(column_order) == 2:
                        cols = tt_summary.columns.tolist()
                        # Reorder TestTime and N columns based on column_order
                        #st.write("Columns before reordering:", cols, column_order)
                        if column_order[0] not in cols[4]:
                            #st.write("Reordering columns for display...")
                            cols[4], cols[5],cols[6], cols[7]  = cols[5], cols[4], cols[7], cols[6]
                            tt_summary = tt_summary[cols]

                    cols = tt_summary.columns.tolist()     
                    test_time_cols = [c for c in tt_summary.columns if c.startswith("TT_")]
                    if len(test_time_cols) == 2:
                        tt_summary["TT_Diff"] = tt_summary[test_time_cols[0]] - tt_summary[test_time_cols[1]]

                custom_order = ["SCOPY", "PRE2", "LZR", "CAL", "NTZ", "CAL2", "FNC2", "SPSC2", "CRT2", "PWT", "FIN2"]

                # 2) Build AgGrid options
                gb = GridOptionsBuilder.from_dataframe(tt_summary)

                gb.configure_column(
                    "OPERATION",
                    sortingOrder=["asc"],
                    comparator=f"""
                    function(a, b) {{
                        const order = {custom_order};
                        return order.indexOf(a) - order.indexOf(b);
                    }}
                    """
                )            

                # group by TEST_NUMBER (now a plain string column name)
                if view_type == "By Test":
                    gb.configure_column("TEST_NUMBER", rowGroup=True, hide=True)
                    gb.configure_column("PARAMETER_NAME", rowGroup=True, hide=True)
                elif view_type == "By Oper":
                    gb.configure_column("OPERATION", rowGroup=True, hide=True)
                    gb.configure_column("TEST_NUMBER", rowGroup=True, hide=True)

                if len(test_time_cols) == 2:
                    gb.configure_column('TT_Diff', aggFunc="sum", type=["numericColumn", "customNumericFormat"], valueFormatter="x.toFixed(2)")

                # Aggregation for numeric columns when grouped
                for col in group_name_list:
                    gb.configure_column('TT_' + col, aggFunc="sum", type=["numericColumn", "customNumericFormat"], valueFormatter="x.toFixed(2)")
                    gb.configure_column('N_' + col, aggFunc="sum", type=["numericColumn", "customNumericFormat"], valueFormatter="x.toFixed(2)")


                # General grid options
                gb.configure_grid_options(
                    groupDisplayType="multipleColumns",  # show group columns instead of hiding
                    groupDefaultExpanded=0,              # 0 = collapsed, -1 = fully expanded
                    animateRows=True,
                    suppressAggFuncInHeader=False,
                )

                grid_options = gb.build()

                # ---------------- Render AgGrid ----------------
                # grid_response = AgGrid(
                #     tt_summary,
                #     gridOptions=grid_options,
                #     enable_enterprise_modules=True,
                #     update_mode=GridUpdateMode.NO_UPDATE,
                #     fit_columns_on_grid_load=True,
                #     height=25*32,
                # ) 

                # Autosize columns after grid loads

                # This JS code will autosize all columns after grid is ready
                auto_size_js = JsCode("""
                function(e) {
                    let gridApi = e.api;
                    gridApi.sizeColumnsToFit();
                }
                """)

                # Render AgGrid with export button
                grid_response = AgGrid(
                    tt_summary,
                    gridOptions=grid_options,
                    enable_enterprise_modules=True,
                    update_mode=GridUpdateMode.NO_UPDATE,
                    fit_columns_on_grid_load=True,
                    height=19*32,
                    onGridReady=auto_size_js,
                    allow_unsafe_jscode=True,
                    custom_js=[
                        JsCode("""
                        function(e) {
                            e.api.sizeColumnsToFit();
                            e.api.gridOptions.api.gridOptionsWrapper.gridOptions.enableRangeSelection = true;
                            e.api.gridOptions.api.gridOptionsWrapper.gridOptions.enableClipboard = true;
                        }
                        """)
                    ],
                    enableRangeSelection=True,
                    enableRowSelection=True,
                    rowSelection='multiple',
                    suppressRowClickSelection=False,
                )

                # Export button for filtered data
                st.download_button(
                    label="Export to CSV",
                    data=tt_summary.to_csv(index=False).encode("utf-8"),
                    file_name="test_time_by_test.csv",
                    mime="text/csv",
                )


            else:
                st.info("No filtered data available. Query data above to view state-wise test time.")

