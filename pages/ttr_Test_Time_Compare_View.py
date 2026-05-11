# http://localhost:8501/ttr_Test_Time_View?prog_0=SUMMIT&cfg_0=CMR&pco_0=PYTHON_374&prog_1=SUMMIT&cfg_1=CMR&pco_1=PYTHON_373
# http://localhost:8501/ttr_Test_Time_View?prog_0=MARLIN&cfg_0=SMR&pco_0=PCO2&prog_1=DORADO&cfg_1=HSMR&pco_1=PCO3
# http://localhost:8501/ttr_Test_Time_Compare_View?prog_0=SUMMIT&cfg_0=CMR&pco_0=PYTHON_373&prog_1=SUMMIT&cfg_1=CMR&pco_1=PYTHON_374

# Numpy compatibility shim for packages expecting np.bool8
import numpy as np  # must run before other imports
if not hasattr(np, "bool8"):
    np.bool8 = np.bool_

import textwrap
import streamlit as st
import pandas as pd
import os
from pathlib import Path
import plotly.express as px
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from st_aggrid.shared import JsCode
import config
import plotly.graph_objects as go
import re
import ast

from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from bokeh.events import ButtonClick
from streamlit_bokeh_events import streamlit_bokeh_events

st.set_page_config(page_title="Test Time View", layout="wide")


test_time_folder = config.TT_HISTORY_PATH
test_group_folder = config.TT_SUMMARY_CSV
test_time_by_test = config.TT_BY_TEST
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

    count_loaded = 0
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
                    df.insert(0, "program", str(count_loaded) + parts[0])
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
        count_loaded += 1
    
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
# Load and merge all test_parameter_info.csv files from folder hierarchy
# -------------------------------------------------------------------
def load_merged_test_time_by_test_parm():
    """
    Recursively find all test_parameter_info.csv files in test_time_folder.
    Read each file and add program, config, pco columns based on folder path.
    Map DRV_INV columns to filter-compatible names.
    Merge all into single dataframe.
    """
    dfs = []

    source_file = "test_parameter_info.csv"

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

    count_loaded = 0
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
                    df.insert(0, "program", str(count_loaded) + parts[0])
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
        count_loaded += 1
    
    if dfs:
        merged_df = pd.concat(dfs, ignore_index=True)
        return merged_df
    else:
        #return empty dataframe if no files found, so caller can handle "no data" case separately from "data with zero rows"
        return pd.DataFrame()

# -------------------------------------------------------------------
# Load and merge all DRV_INV.csv files from folder hierarchy
# -------------------------------------------------------------------
def load_merged_max_cyl():
    """
    """
    dfs = []

    source_file = "P172_MAX_CYL_VBAR@FNC2.csv"

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

    count_loaded = 0
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

            count_loaded += 1
    
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

st.markdown('<div class="program-title">Test Time View</div>', unsafe_allow_html=True)

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

program_options = ["NONE", "SUMMIT", "MARLIN", "MARLIN BP", "DORADO", "OSPREY"]
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
                    "Group",
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

def to_two_level_dataframe(df: pd.DataFrame):
    new_cols = []

    for c in df.columns:
        if c == "OPERATION":
            # OPERATION อยู่เดี่ยว
            new_cols.append(("OPERATION", ""))
        else:
            m = re.match(r"^(mean|count)_(.+)$", c)
            if m:
                top, sub = m.groups()
                new_cols.append((top, sub))
            else:
                new_cols.append(("", c))

    df2 = df.copy()
    df2.columns = pd.MultiIndex.from_tuples(new_cols)
    return df2

def test_time_block(title, df, key_prefix, groupby_cols=None, group_by=None):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        filter_text_tt_op = st.text_input(
        "Filter Text Box",
        "",
        placeholder="Search in all columns..."
        )

    with c2:
        logic = st.radio(
        "Search Mode",
        ["OR", "AND"],
        horizontal=True,
        help="OR: Match any word | AND: Match all words, [col]_null to search for null values"
    )


    df_f = apply_filter(
        df,
        filter_text_tt_op,
        logic,
        ["program", "config", "pco", "Category", "SubCat"],
    )

    # If no data selected (empty df) show blank table immediately
    
    if df_f.empty:
        st.dataframe(pd.DataFrame(), use_container_width=True, height=8*32)
        return
    if not has_query_params:
        return
    if groupby_cols:
        #st.write("Grouping by:", groupby_cols)    
        
        select_col = ["program","pco", "config"]
        if group_by != "GROUP_NAME" and group_by in group_list:
            select_col = [group_by]

        df_view = df_f.pivot_table(
            index=[ "OPERATION"],
            columns= select_col,
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

        # Add TOTAL summary row (sum counts, weighted mean for means)
        if not df_view.empty:
            total_row = {}
            for col in df_view.columns:
                if col in [ "OPERATION",]:
                    continue
                if col.startswith("count_"):
                    total_row[col] = df_view[col].sum()
                elif col.startswith("mean_"):
                    # Derive matching count column suffix
                    suffix = col[len("mean_"):]
                    count_col = f"count_{suffix}"
                    if count_col in df_view.columns and df_view[count_col].sum() > 0:
                        #total_row[col] = (df_view[col] * df_view[count_col]).sum() / df_view[count_col].sum()
                        total_row[col] = (df_view[col]).sum() 
                    else:
                        total_row[col] = df_view[col].mean()
                else:
                    # Generic numeric sum or leave blank
                    total_row[col] = df_view[col].sum() if pd.api.types.is_numeric_dtype(df_view[col]) else None
            total_row["OPERATION"] = "Total"
            df_view = pd.concat([df_view, pd.DataFrame([total_row])], ignore_index=True)

            if group_by == "GROUP_NAME":
                column_order = getPCOColumnOrder()
                #st.write("Column order:", column_order, len(column_order)) 
                if len(column_order) == 2:
                    cols = df_view.columns.tolist()
                    # Reorder TestTime and N columns based on column_order
                    #st.write("Columns before reordering:", cols, column_order)
                    if column_order[0] not in cols[1]:
                        st.write("Reordering columns for display...")
                        cols[1], cols[2],cols[3], cols[4]  = cols[2], cols[1], cols[4], cols[3]
                        df_view = df_view[cols]            

                tt_cols = [c for c in df_view.columns if c.startswith("mean_")]
                if len(tt_cols) == 2:
                    df_view["Diff(Hrs.)"] = df_view[tt_cols[0]] - df_view[tt_cols[1]]            
    else:
        df_view = df_f

    
    # Order df_view OPERATION column to match the custom order
    custom_order = ["SCOPY", "PRE2", "LZR", "CAL", "NTZ", "CAL2", "FNC2", "SPSC2", "CRT2", "PWT", "FIN2", "Total"]
    if "OPERATION" in df_view.columns:
        df_view["OPERATION"] = pd.Categorical(df_view["OPERATION"], categories=custom_order, ordered=True)
        df_view = df_view.sort_values("OPERATION")
    
    order_cols = ['OPERATION']

    for col in df_view.columns:
        if col not in order_cols and col.startswith("mean_"):
            order_cols.append(col)

    df_view.columns = order_cols + [col for col in df_view.columns if col not in order_cols]


    # Set fixed width for columns 1-5 (after OPERATION)
    col_widths = {col: {"width": 120, 'help': col} for col in df_view.columns[1:6]}  # columns 1-5 (0-based, skip OPERATION)


    df_view2 = to_two_level_dataframe(df_view)
    # Add option to toggle between text and table view
    view_mode = st.radio(
        "Display Mode",
        ["Table", "Text"],
        horizontal=True,
        key=f"{key_prefix}_view_mode"
    )
    
    if view_mode == "Table":
        st.dataframe(df_view2, use_container_width=False, column_config=col_widths, height=15*32)
    else:
        # Display df_view2 as code for debugging/inspection
        csv = df_view2.to_csv(index=False).encode('utf-8')
        st.code(df_view2.to_string(), language="text")


    
    #st.write(tsv_json)
    # Download filtered data
    csv = df_f.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Data as CSV",
        data=csv,
        file_name="test_time_by_oper.csv",
        mime="text/csv",
        key=f"{key_prefix}_download_btn"
    )

    with st.expander("Track Info", expanded=False):

        df_cyl_data =  load_merged_max_cyl()

        # Plot MAX_CYL_DEC by STATE_NAME and GROUP_NAME
        if not df_cyl_data.empty and "MAX_CYL_DEC" in df_cyl_data.columns:
            df_cyl_plot = df_cyl_data.copy()
            
            # Ensure numeric MAX_CYL_DEC
            df_cyl_plot['MAX_CYL_DEC'] = pd.to_numeric(df_cyl_plot['MAX_CYL_DEC'], errors='coerce')
            df_cyl_plot = df_cyl_plot.dropna(subset=['MAX_CYL_DEC'])
            
            if not df_cyl_plot.empty:
                # Display mean for each group
                group_means = df_cyl_plot.groupby(["GROUP_NAME", "STATE_NAME"])["MAX_CYL_DEC"].mean().sort_values(ascending=False)
                st.subheader("Mean MAX_CYL_DEC by Group")
                
                group_means_pivot = group_means.reset_index().pivot(index="STATE_NAME", columns="GROUP_NAME", values="MAX_CYL_DEC")

                # Add ratio column
                if len(group_means_pivot.columns) >= 2:
                    #st.write("columns for ratio:", group_means_pivot.columns.tolist())
                    g0_col = group_means_pivot.columns[0]
                    g1_col = group_means_pivot.columns[1]
                    group_means_pivot['Ratio%'] = (group_means_pivot[g0_col] - group_means_pivot[g1_col]) / group_means_pivot[g1_col] * 100
                
                st.dataframe(group_means_pivot, use_container_width=True)
                
                fig_cyl = px.box(
                    df_cyl_plot,
                    x="STATE_NAME",
                    y="MAX_CYL_DEC",
                    color="GROUP_NAME",
                    hover_data=["program", "config", "pco"],
                    title="MAX_CYL_DEC by State and Group"
                )
                fig_cyl.update_layout(
                    yaxis_title="MAX_CYL_DEC",
                    xaxis_title="State Name",
                    margin=dict(l=10, r=10, t=40, b=10)
                )
                st.plotly_chart(fig_cyl, use_container_width=True)

        pass

    return select_col

def _get_attr_default(idx):
    """Get attribute default from query params."""
    attr_val = filter_params.get(f"attr_{idx}", "")
    if isinstance(attr_val, list):
        attr_val = attr_val[0] if attr_val else ""
    # Validate it's in filter_columns
    if attr_val in filter_columns:
        return filter_columns.index(attr_val)
    return 0

def _get_val_default(idx):
    """Get value default list from query params."""
    val_raw = filter_params.get_all(f"val_{idx}")

    if isinstance(val_raw, str):
        # Single value stored as string
        return [val_raw] if val_raw else []
    elif isinstance(val_raw, list):
        return val_raw
    return []

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

with st.expander("Data Filter", expanded=False):
    pass
    # Add 3 sets of attribute/value filters (row-based, no program/config selection)

    st.write("**Attribute Filters:**")

    # Attribute Filters with improved layout
    cols = st.columns(3)
    filter_columns = config.TTR_ATTR_WEB_FILTER_LIST

    def get_unique_values(df, col):
        if col in df.columns:
            vals = df[col].dropna().unique()
            vals = sorted([str(v) for v in vals])
            return [""] + vals
        return [""]
    
    # Read filter parameters from query_params if available
    filter_params = st.query_params


    with cols[0]:
        st.markdown("**Filter Set 1**")
        attr_1 = st.selectbox("Attribute", filter_columns, index=_get_attr_default(1), key="attr_1")
        val_options_1 = get_unique_values(source_df, attr_1)
        val_1 = st.multiselect("Value", val_options_1, default=_get_val_default(1), key="val_1")

    with cols[1]:
        st.markdown("**Filter Set 2**")
        attr_2 = st.selectbox("Attribute", filter_columns, index=_get_attr_default(2), key="attr_2")
        val_options_2 = get_unique_values(source_df, attr_2)
        val_2 = st.multiselect("Value", val_options_2, default=_get_val_default(2), key="val_2")

    with cols[2]:
        st.markdown("**Filter Set 3**")
        attr_3 = st.selectbox("Attribute", filter_columns, index=_get_attr_default(3), key="attr_3")
        val_options_3 = get_unique_values(source_df, attr_3)
        val_3 = st.multiselect("Value", val_options_3, default=_get_val_default(3), key="val_3")

    # Editable table for SERIAL_NUM, TRANS_SEQ
    st.markdown("")


    with st.expander("**Filter out SERIAL_NUM and TRANS_SEQ**", expanded=False):
        editable_cols = ["SERIAL_NUM", "TRANS_SEQ"]

        # Persistent store for pasted rows so they survive reruns
        if "_sn_ts_rows" not in st.session_state:
            st.session_state._sn_ts_rows = []  # list of {SERIAL_NUM, TRANS_SEQ}

        st.markdown("Paste rows from Excel (two columns: SERIAL_NUM, TRANS_SEQ). Accepts tab, comma, or whitespace separated values.")
        paste_text = st.text_area(
            "Paste here",
            placeholder="SERIAL_NUM\tTRANS_SEQ\n12345\t678\n12346\t679",
            height=120,
            key="sn_ts_paste_area",
        )
        cpa, cpb = st.columns([1,1])
        with cpa:
            add_paste = st.button("Add Pasted Rows", key="add_pasted_sn_ts")
        with cpb:
            clear_paste = st.button("Clear Rows", key="clear_sn_ts_rows")

        def _parse_paste(text: str):
            rows = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                # Try tab, then comma, then whitespace
                if "\t" in line:
                    parts = line.split("\t")
                elif "," in line:
                    parts = line.split(",")
                else:
                    parts = line.split()
                if len(parts) >= 2:
                    sn = str(parts[0]).strip()
                    ts = str(parts[1]).strip()
                    if sn or ts:
                        rows.append({"SERIAL_NUM": sn, "TRANS_SEQ": ts})
            return rows

        if add_paste and paste_text:
            new_rows = _parse_paste(paste_text)
            if new_rows:
                # Merge with existing, de-duplicate
                existing = {(r.get("SERIAL_NUM",""), r.get("TRANS_SEQ","")) for r in st.session_state._sn_ts_rows}
                for r in new_rows:
                    key = (r.get("SERIAL_NUM",""), r.get("TRANS_SEQ",""))
                    if key not in existing:
                        st.session_state._sn_ts_rows.append(r)
                        existing.add(key)
                st.toast(f"Added {len(new_rows)} pasted rows", icon="✅")

        if clear_paste:
            st.session_state._sn_ts_rows = []
            st.toast("Cleared rows", icon="🗑️")

        # Build initial DataFrame for the editor from session rows
        if st.session_state._sn_ts_rows:
            editable_df = pd.DataFrame(st.session_state._sn_ts_rows, columns=editable_cols)
        else:
            editable_df = pd.DataFrame(columns=editable_cols)

        editable_df = editable_df.dropna(how='all')

        edited_df = st.data_editor(
            editable_df,
            num_rows="dynamic",
            use_container_width=False,
            key="serial_num_trans_seq_editor"
        )

        # Persist any changes from the editor back to session
        if isinstance(edited_df, pd.DataFrame):
            try:
                # Normalize NaNs to empty strings for consistency
                tmp = edited_df.copy()[editable_cols].astype(str)
                tmp = tmp.replace({"nan": ""})
                st.session_state._sn_ts_rows = tmp.to_dict(orient="records")
            except Exception:
                pass



    query_btn_pressed = st.button(
        "Filter Data",
        key="filter_data_btn",
        help="Apply Filter"
    )

    # Filter source_df based on user selected filters
    filtered_df = source_df.copy()
    # Only filter if attribute is not empty and value(s) are selected
    if query_btn_pressed:
        # Do NOT reset user selections after filtering
        # (removed code that reset attr/val selections)
        if attr_1 and val_1 and "" not in val_1:
            filtered_df = filtered_df[filtered_df[attr_1].astype(str).isin(val_1)]
        if attr_2 and val_2 and "" not in val_2:
            filtered_df = filtered_df[filtered_df[attr_2].astype(str).isin(val_2)]
        if attr_3 and val_3 and "" not in val_3:
            filtered_df = filtered_df[filtered_df[attr_3].astype(str).isin(val_3)]

        if edited_df is not None and not edited_df.empty and len(edited_df) > 0:
            # Remove rows matching
            for _, row in edited_df.iterrows():
                sn = str(row.get("SERIAL_NUM", "")).strip()
                ts = str(row.get("TRANS_SEQ", "")).strip()
                if sn and ts:
                    filtered_df = filtered_df[~((filtered_df['SERIAL_NUM'].astype(str) == sn) & (filtered_df['TRANS_SEQ'].astype(str) == ts))]
                    # Clear data in serial_num_trans_seq_editor
                    #st.session_state["serial_num_trans_seq_editor"] = pd.DataFrame(columns=["SERIAL_NUM", "TRANS_SEQ"])
                    
        # Update query_params with filter settings
        # Keep existing prog/cfg/pco params and add/update filter params
        if val_1 and "" not in val_1:
            st.query_params["attr_1"] = attr_1
            st.query_params["val_1"] = val_1
        if val_2 and "" not in val_2:
            st.query_params["attr_2"] = attr_2
            st.query_params["val_2"] = val_2
        if val_3 and "" not in val_3:
            st.query_params["attr_3"] = attr_3
            st.query_params["val_3"] = val_3


                
        st.session_state.tt_filtered = filtered_df
        st.rerun()

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

        pivot_df_cms = source_df.pivot_table(
            index=["program","CMS_CONFIG"],
            columns=["pco"] ,
            values="TEST_TIME",
            aggfunc="count",
            fill_value=0
        ).reset_index()

        st.dataframe(pivot_df_cms, use_container_width=False)
m_select_col = None
groupby_cols=["program", "config", "pco", "Category"]
# Add a selectbox to choose what to plot on x-axis
group_list = ["GROUP_NAME", "CMS_CONFIG", "NUM_HEADS", "CAPACITY", "HEAD", "PN3", 
            "IR_DRIVE", "POWER_LOSS_DRIVE", "WAFER_TYPE", "HGA_SORT_06", "CAL2_FPW", "SUB_BUILD_GROUP", "STATE_NAME","GROUP_NAME", 'config']

group_by = st.selectbox(
    "Test Time By Attr",
    group_list,
    index=0,
    key=
    "plot_by_operation_chart"
)

with st.expander("Test Time By Operation", expanded=False):
    m_select_col = test_time_block("Test Time", source_df, "tt_overall", groupby_cols, group_by)


# -------------------------------------------------------------------
# Bottom: Distribution Charts for Selected Data
# -------------------------------------------------------------------

with st.expander("Test Time Distribution", expanded=False):

    if not has_query_params:
        pass
     # Use filtered data if available
       
    elif "tt_filtered" in st.session_state and not st.session_state.tt_filtered.empty:

        #df_dist = df_raw.copy()
        df_dist = st.session_state.tt_filtered.copy()
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

        if m_select_col is not None and len(m_select_col) == 1 and m_select_col[0] in df_dist.columns:
            color_arg = m_select_col[0]
        else:
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

        # Set default selection mode to "select" (user select mode)
        fig.update_layout(
            dragmode="select",  # Default to user selection mode
            yaxis_title="Test Time (hours)",
            xaxis_title="Operation",
            yaxis_type=y_scale,
            legend_title=("pco" if color_arg == "pco" else None),
            margin=dict(l=10, r=10, t=40, b=10)
        )

        
        event = st.plotly_chart(fig, use_container_width=True,key="violin",on_select="rerun",)
        st.caption("Distribution of TEST_TIME across selected operations and filters.")

        pts = event.selection.points  # Streamlit PlotlySelectionState.points :contentReference[oaicite:2]{index=2}

        # Extract SN, TS, OPER, Test Time, Group_Name from pts
        if pts:
            st.write("Total selected points:", len(pts))
            violin_points_data = []
            for pt in pts:
                SN = pt.get("customdata", [None, None])[0]
                TS = pt.get("customdata", [None, None])[1]
                OPER = pt.get("x")
                Test_Time = pt.get("y")
                Group_Name = pt.get("legendgroup")
                violin_points_data.append({
                "SN": SN,
                "TS": TS,
                "OPER": OPER,
                "Group_Name": Group_Name,
                "Test Time": Test_Time                
                })

            violin_points_df = pd.DataFrame(violin_points_data)
            # Set fixed width for columns in violin_points_df display
            col_widths = {col: {"width": 120, 'help': col} for col in violin_points_df.columns}
            if len(violin_points_df.columns) > 0:
                last_col = violin_points_df.columns[-1]
                col_widths[last_col] = {"width": 240, 'help': last_col}
            # Add index column starting from 1
            violin_points_df.index = violin_points_df.index + 1
            violin_points_df.reset_index(inplace=True)
            violin_points_df.rename(columns={"index": "No."}, inplace=True)
            st.dataframe(violin_points_df, use_container_width=False, column_config=col_widths, height=8*32, hide_index=True)

            
        
    else:
        st.info("No filtered data available. Query data above to view distribution.")

st.markdown("---")
# -------------------------------------------------------------------
# Bottom: Test Time By State
# -------------------------------------------------------------------
with st.expander("Test Time By State", expanded=False):
    
    st.markdown('<div class="section-title">Test Time By State</div>', unsafe_allow_html=True)

    if not has_query_params:
        st.info("No query parameters provided. Please select filters above.")
    else:
        df_state = load_merged_test_time_by_state_detail().copy()
        # st.write(f"Filtering {attr_1} in {val_1}, remaining rows: {len(df_state)}")
        # st.write(df_state.columns)

        if attr_1 and val_1 and "" not in val_1 and attr_1 in df_state.columns:
            df_state = df_state[df_state[attr_1].astype(str).isin(val_1)]
            st.write(f"Filtering {attr_1} in {val_1}, remaining rows: {len(df_state)}")
        if attr_2 and val_2 and "" not in val_2 and attr_2 in df_state.columns:
            df_state = df_state[df_state[attr_2].astype(str).isin(val_2)]
        if attr_3 and val_3 and "" not in val_3 and attr_3 in df_state.columns:
            df_state = df_state[df_state[attr_3].astype(str).isin(val_3)]

        if edited_df is not None and not edited_df.empty and len(edited_df) > 0:
            # Remove rows matching
            for _, row in edited_df.iterrows():
                sn = str(row.get("SERIAL_NUM", "")).strip()
                ts = str(row.get("TRANS_SEQ", "")).strip()
                if sn and ts:
                    df_state = df_state[~((df_state['SERIAL_NUM'].astype(str) == sn) & (df_state['TRANS_SEQ'].astype(str) == ts))]

        c1_tt, c2_tt, c3_tt = st.columns(3)
        with c1_tt:
            filter_text_tt_op_tt = st.text_input(
            "Filter Text Box",
            "",
            placeholder="Search in all columns...",
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
            avg_mode = st.radio(
            "Avg Mode",
            ["Normal", "Weighted"],
            horizontal=True,
            help="Normal: Regular average | Weighted: Weighted average based on counts",
            key="avg_mode_test"
            
        )

        group_cols_cnt =  ["SERIAL_NUM", "TRANS_SEQ", "OPERATION", "GROUP_NAME"]
        df_cnt = df_state.groupby(group_cols_cnt, dropna=False).agg(N=('SERIAL_NUM', 'size')).reset_index()
        total_rows = len(df_cnt)
        print(f"[summary] Total rows in df_cnt: {total_rows}")

        group_cols_opr_cnt = ["OPERATION", "GROUP_NAME"]
        df_opr_cnt = df_cnt.groupby(group_cols_opr_cnt, dropna=False).agg(OPER_CNT=('SERIAL_NUM', 'size')).reset_index()

        df_state = apply_filter(
            df_state,
            filter_text_tt_op_tt,
            logic_tt,
            ["program", "config", "pco", "STATE_NAME", "OPERATION"],
        )


        if not df_state.empty:

            # Group by state and calculate mean and count
            if "STATE_NAME" in df_state.columns and len(m_select_col) > 1:

                
                df_state = pd.merge(df_state, df_opr_cnt, on=["OPERATION", "GROUP_NAME"], how="left")
                state_summary = df_state.pivot_table(
                    index=[ "OPERATION", "STATE_NAME"],
                    columns=["pco",], #"program","pco", "config"
                    values=["TestTime(hrs)", "N", 'OPER_CNT',"SERIAL_NUM"],
                    aggfunc={"TestTime(hrs)": "mean", "N": "sum", 'OPER_CNT': 'mean', "SERIAL_NUM": "size"},
                    fill_value=0
                ).reset_index() 

                # st.write(state_summary.columns)
                # st.write(state_summary)

                if avg_mode == "Weighted":
                    state_summary['TestTime(hrs)'] = (state_summary['TestTime(hrs)']  * state_summary['SERIAL_NUM']) / state_summary['OPER_CNT'].replace(0, np.nan)  # avoid division by zero
                    state_summary['N'] = state_summary['OPER_CNT'].replace(0, np.nan).round().astype("Int64")

                state_summary = state_summary.drop(columns=['OPER_CNT', 'SERIAL_NUM'])

                # Flatten MultiIndex columns into readable single-level names
                def _flatten(col):
                    if not isinstance(col, tuple):
                        return col
                    parts = [str(p) for p in col if p not in ("", None)]
                    return "_".join(parts)
                state_summary.columns = [_flatten(c) for c in state_summary.columns]

                column_order = getPCOColumnOrder()
                
                cols = state_summary.columns.tolist()
                if len(column_order) == 2 and len(cols) >= 6:
                    # Reorder TestTime and N columns based on column_order
                    if column_order[0] not in cols[2]:
                        cols[2], cols[3],cols[4], cols[5]  = cols[3], cols[2], cols[5], cols[4]
                        state_summary = state_summary[cols]

                fixed = ["OPERATION", "STATE_NAME"]
                value_cols = [c for c in state_summary.columns if c not in fixed]

                # Separate TestTime and N columns by prefix after flattening
                tt_cols = [c for c in value_cols if c.startswith("TestTime(hrs)_")]
                n_cols = [c for c in value_cols if c.startswith("N_")]

                # Reorder columns: fixed + test time + counts
                state_summary = state_summary[fixed + tt_cols + n_cols]

                # If exactly two TestTime columns, compute diff (first minus second)
                if len(tt_cols) == 2:
                    state_summary["diff_TestTime(hrs)"] = state_summary[tt_cols[0]] - state_summary[tt_cols[1]]
                elif len(tt_cols) > 2:
                    st.info("More than two TestTime groups present; diff not computed.")

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
                float_like_cols = [c for c in state_summary.columns if c.startswith("TestTime(hrs)_") or c.startswith("diff_TestTime(hrs)")]
                for c in float_like_cols:
                    if c in state_summary.columns:
                        state_summary[c] = pd.to_numeric(state_summary[c], errors='coerce').round(2)

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

                # column_order = getPCOColumnOrder()
                # if len(column_order) == 2:
                #     cols = state_summary.columns.tolist()
                #     # Reorder TestTime and N columns based on column_order
                #     if column_order[0] not in cols[2]:
                #         cols[2], cols[3],cols[4], cols[5]  = cols[3], cols[2], cols[5], cols[4]
                #         state_summary = state_summary[cols]
                        
                styled = state_summary.style.apply(highlight_last_row, axis=1)

                col_widths = {col: {"width": 120, 'help': col} for col in state_summary.columns[1:6]}  # columns 1-5 (0-based, skip OPERATION)

                st.dataframe(styled, use_container_width=True, column_config=col_widths, height=15*32)

            elif m_select_col is not None and len(m_select_col) == 1 and m_select_col[0] in df_dist.columns:
                color_arg = m_select_col[0]

                state_summary = df_state.pivot_table(
                    index=[ "OPERATION", "STATE_NAME"],
                    columns= m_select_col[0], #"program","pco", "config"
                    values=["TestTime(hrs)", "N"],
                    aggfunc={"TestTime(hrs)": "mean", "N": "sum"},
                    fill_value=0
                ).rename(columns={"N": "RecordCount"}, level=0).reset_index()

                
                state_summary = state_summary[
                    ["OPERATION", "STATE_NAME", "TestTime(hrs)", "RecordCount"]
                ]


                #st.dataframe(state_summary, use_container_width=True, column_config=col_widths, height=15*32)
                st.dataframe(state_summary, use_container_width=True, height=15*32)

            else:
                st.warning("The dataset does not contain a 'STATE' column.")
        else:
            st.info("No filtered data available. Query data above to view state-wise test time.")

        csv = df_state.to_csv(index=False).encode('utf-8')
        st.download_button(
        label="Download Data as CSV",
        data=csv,
        file_name="test_time_by_state.csv",
        mime="text/csv",
        key="test_time_by_state_download_btn"
        )

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




            hover_cols = [c for c in ["SERIAL_NUM", "TRANS_SEQ"] if c in df_dist.columns]
            # st.write(f"Hover columns: {hover_cols}")
            # st.write(f"Hover columns: {df_dist.columns}")

            # Add a selectbox to choose what to plot on x-axis

            plot_list = ["OP_STATE", "CMS_CONFIG", "NUM_HEADS", "CAPACITY", "HEAD", "PN3", 
                 "IR_DRIVE", "POWER_LOSS_DRIVE", "WAFER_TYPE", "HGA_SORT_06", "CAL2_FPW", "SBR", "STATE_NAME","GROUP_NAME", 'config']
            
            plot_by = m_select_col[0] if m_select_col is not None and len(m_select_col) == 1 and m_select_col[0] in df_dist.columns else "OP_STATE"
            # plot_by = st.selectbox(
            #     "Plot by",
            #     plot_list,
            #     index=0,
            #     key="plot_by_state_chart"
            # )

            # Default plot settings (no user controls): Violin chart, color by pco if available, linear scale, no clipping
            chart_type = "Violin"
            # Set color based on plot_by selection
            # If plotting by OP_STATE, color by pco; otherwise color by plot_by column
            if plot_by == "OP_STATE":
                color_arg = "pco" if "pco" in df_dist.columns else None
            else:
                color_arg = plot_by if plot_by in df_dist.columns else None
            y_scale = "linear"

            # Create the appropriate column based on selection
            if plot_by == "OP_STATE":
                df_dist['plot_column'] = df_dist['OPERATION'].astype(str) + " - " + df_dist['STATE_NAME'].astype(str)
            elif plot_by in plot_list:
                df_dist['plot_column'] = df_dist[plot_by].astype(str) if plot_by in df_dist.columns else "Unknown"
            if df_dist.empty or ("plot_column" not in df_dist.columns):
                st.warning("No data remains for selected filters / clip range.")
                st.write(df_dist.columns)
                st.write(len(df_dist))
                st.write(("plot_column" not in df_dist.columns))
                st.write(df_dist.empty )
                st.stop()
            if chart_type == "Strip (Jitter)":  # unreachable with default violin but kept for easy future toggle
                # Manual jitter using scatter since px.strip doesn't support 'jitter' kwarg in current Plotly version
                # Map OPERATION categories to numeric positions then add random noise
                if "plot_column" in df_dist.columns:
                    # Use only present operation categories for jitter mapping
                    op_categories = list(df_dist['plot_column'].cat.categories if isinstance(df_dist['plot_column'], pd.Categorical) else list(df_dist['plot_column'].unique()))
                    op_index_map = {op: i for i, op in enumerate(op_categories)}
                    df_dist['_op_x'] = df_dist['plot_column'].map(op_index_map).astype(float)
                    # Add jitter within +/-0.3 range
                    rng = np.random.default_rng(seed=42)  # deterministic for reproducibility per rerun
                    df_dist['_op_x_jitter'] = df_dist['_op_x'] + rng.uniform(-0.3, 0.3, size=len(df_dist))
                    fig = px.scatter(
                        df_dist,
                        x="_op_x_jitter",
                        y="TEST_TIME",
                        color=color_arg,
                        hover_data=hover_cols + plot_by,
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
                    x="plot_column",
                    y="TEST_TIME",
                    color=color_arg,
                    hover_data=hover_cols,
                )
                if "plot_column" in df_dist.columns and isinstance(df_dist['plot_column'], pd.Categorical):
                    fig.update_xaxes(categoryorder='array', categoryarray=list(df_dist['plot_column'].cat.categories))
            else:  # Violin
                
                fig = px.violin(
                    df_dist,
                    x="plot_column",
                    y="TEST_TIME",
                    color=color_arg,
                    hover_data=hover_cols,
                    box=True,
                    points="all"
                )

                fig = add_violin_labels(
                    fig,
                    df=df_dist,
                    x_col="plot_column",
                    y_col="TEST_TIME",
                    color_col=color_arg,
                    label_metric="mean",  # or "mean"
                )
                if "plot_column" in df_dist.columns and isinstance(df_dist['plot_column'], pd.Categorical):
                    fig.update_xaxes(categoryorder='array', categoryarray=list(df_dist['plot_column'].cat.categories))

            fig.update_layout(
                 dragmode="select",  # Default to user selection mode
                yaxis_title="Test Time (hours)",
                xaxis_title=color_arg,
                yaxis_type=y_scale,
                legend_title=(color_arg),
                margin=dict(l=10, r=10, t=40, b=10)
            )
            event_state = st.plotly_chart(fig, use_container_width=True,key="violin_state",on_select="rerun")
            st.caption(f"Distribution of TEST_TIME across selected operations and filters.")

            pts_state = event_state.selection.points  # Streamlit PlotlySelectionState.points :contentReference[oaicite:2]{index=2}

            # Extract SN, TS, OPER, Test Time, Group_Name from pts
            if pts_state:
                st.write("Total selected points:", len(pts_state))
                violin_points_data = []
                for pt in pts_state:
                    SN = pt.get("customdata", [None, None])[0]
                    TS = pt.get("customdata", [None, None])[1]
                    OPER = pt.get("x")
                    OPER2 = pt.get("x")
                    Test_Time = pt.get("y")
                    Group_Name = pt.get("legendgroup")
                    violin_points_data.append({
                    "SN": SN,
                    "TS": TS,
                    f"{color_arg}_1": OPER.split(" - ")[0] if " - " in OPER else OPER,  # extract state name if OP_STATE format
                    "Group_Name": Group_Name,                    
                    f"{color_arg}_2": OPER.split(" - ")[1] if " - " in OPER else OPER,  # extract state name if OP_STATE format                    
                    "Test Time": Test_Time

                    })
                violin_points_df = pd.DataFrame(violin_points_data)
                # Set fixed width for columns in violin_points_df display
                col_widths = {col: {"width": 120} for col in violin_points_df.columns}
                if len(violin_points_df.columns) > 0:
                    last_col = violin_points_df.columns[-1]
                    col_widths[last_col] = {"width": 240}
                # Add index column starting from 1
                violin_points_df.index = violin_points_df.index + 1
                violin_points_df.reset_index(inplace=True)
                violin_points_df.rename(columns={"index": "No."}, inplace=True)
                st.dataframe(violin_points_df, use_container_width=False, column_config=col_widths, height=8*32, hide_index=True)
        else:
            st.info("No filtered data available. Query data above to view distribution.")
    
        with st.expander("Test Time By Category", expanded=False):    # Test Time By Category
            # Copy df_state 
            df_raw_state = df_state.copy()

            if "OPER_CNT" in df_raw_state.columns:
                df_raw_state = df_raw_state.pivot_table(
                    index=["OPERATION", "STATE_NAME", "GROUP_NAME", "OPER_CNT"],
                    aggfunc={"TestTime(hrs)": "mean", "SERIAL_NUM": "size"},
                ).reset_index() 

                # force to weighted 
                if avg_mode == "Weighted":
                    df_raw_state['TestTime(hrs)'] = (df_raw_state['TestTime(hrs)']  * df_raw_state['SERIAL_NUM']) / df_raw_state['OPER_CNT'].replace(0, np.nan)  # avoid division by zero
            else:
                df_raw_state = df_raw_state.pivot_table(
                    index=["OPERATION", "STATE_NAME", "GROUP_NAME"],
                    aggfunc={"TestTime(hrs)": "mean", "SERIAL_NUM": "size"},
                ).reset_index()
            # st.write(df_raw_state)
            st.write(test_group_folder)

            df_dorado_all_state = pd.read_csv(test_group_folder)
            join_test_group_result = pd.merge(df_raw_state, df_dorado_all_state, on=['OPERATION' , 'STATE_NAME'], how='left')
            join_test_group_result['Test Group'] = join_test_group_result['Test Group'].fillna('UNKNOW')


            st.write(f"Raw State {len(df_raw_state.index)} row, Dorado All State {len(df_dorado_all_state)} row, Raw State After Join {len(join_test_group_result)} row.")

            # st.write(df_dorado_all_state)
            # st.write(join_test_group_result)

            # join_test_group_result = join_test_group_result.pivot_table(
            #     index=[ "Test Group" ],
            #     columns=["GROUP_NAME",],
            #     values=["TestTime(hrs)", "STATE_NAME"],
            #     aggfunc={"TestTime(hrs)": "sum", "STATE_NAME": "size"},
            #     fill_value=0
            # ).reset_index()
            # st.write(join_test_group_result)

            
            df_tt_by_category = join_test_group_result.pivot_table(
                index=["Test Group"],
                columns=["GROUP_NAME"],
                values=["TestTime(hrs)", "STATE_NAME"],
                aggfunc={"TestTime(hrs)": "sum", "STATE_NAME": "size"},
                fill_value=0,
                sort=False
            )



            chart_ttbc = df_tt_by_category.copy()

            metrics = list(dict.fromkeys(df_tt_by_category.columns.get_level_values(0)))
            groups  = list(dict.fromkeys(df_tt_by_category.columns.get_level_values(1)))

            for m in metrics:
                df_tt_by_category[(m, "sum")] = df_tt_by_category[m].sum(axis=1)

            base_groups = [g for g in groups if g != "sum"]
            swapped_groups = base_groups[::-1]

            metric_order = ["TestTime(hrs)", "STATE_NAME"]

            new_cols = []
            for m in metric_order:
                for g in swapped_groups:
                    new_cols.append((m, g))
                new_cols.append((m, "sum"))

            df_tt_by_category = df_tt_by_category.reindex(columns=pd.MultiIndex.from_tuples(new_cols))
            df_tt_by_category.loc["Total"] = df_tt_by_category.sum()
            df_tt_by_category = df_tt_by_category.reset_index()
            st.write(df_tt_by_category)

            # Download Data After join
            df_tt_by_category_csv = df_tt_by_category.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Data as CSV",
                data=df_tt_by_category_csv,
                file_name="df_tt_by_category.csv",
                mime="text/csv",
                key="df_tt_by_category_download_btn"
            )

            plot_graph_ttbc = st.checkbox("Plot Graph Test Time By Category", value=False)

            if plot_graph_ttbc:
            
                groups_order = swapped_groups
                x_order = list(chart_ttbc.index)

                # bar chart TestTime(hrs)
                df_tt = (chart_ttbc["TestTime(hrs)"].reset_index().melt(id_vars="Test Group", var_name="GROUP_NAME", value_name="TestTime(hrs)"))

                fig_tt = px.bar(
                    df_tt,
                    x="Test Group", y="TestTime(hrs)",
                    color="GROUP_NAME",
                    barmode="group",
                    category_orders={"GROUP_NAME": groups_order, "Test Group": x_order},
                    title="TestTime(hrs) by Test Group and GROUP_NAME"
                )
                st.plotly_chart(fig_tt, use_container_width=True)

                # # bar chart STATE_NAME
                # df_sn = (chart_ttbc["STATE_NAME"].reset_index().melt(id_vars="Test Group", var_name="GROUP_NAME", value_name="STATE_NAME"))

                # fig_sn = px.bar(
                #     df_sn,
                #     x="Test Group", y="STATE_NAME",
                #     color="GROUP_NAME",
                #     barmode="group",
                #     category_orders={"GROUP_NAME": groups_order, "Test Group": x_order},
                #     title="STATE_NAME (count) by Test Group and GROUP_NAME"
                # )
                # st.plotly_chart(fig_sn, use_container_width=True)

with st.expander("Test Time By Test org", expanded=False):
    st.markdown('<div class="section-title">Test Time By Test</div>', unsafe_allow_html=True)

    if not has_query_params:
        st.info("No query parameters provided. Please select filters above.")
    else:
        df_test = load_merged_test_time_by_test().copy()

        c1_tt, c2_tt, c3_tt, c4_tt = st.columns(4)
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
            help=f"- Free terms (no \":\") search across search_cols (or all columns if None).\n- Column-specific terms use the syntax COL:VALUE, e.g. STATE:ZAP TEST:275\n- [STATE:STATE_NAME, OP:OPERATION, PARM:PARAMETER_NAME, TEST:TEST_NUMBER]",
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

        with c4_tt:
            avg_mode_tt_op_tt = st.radio(
            "Avg Mode",
            ["Normal", "Weighted"],
            horizontal=True,
            help="Normal: Regular average | Weighted: Weighted average",
            key="avg_mode_tt_op_tt"
            
            )

        df_test = apply_filter_flex(
            df_test,
            filter_text_tt_op_tt,
            logic_tt_op_tt,
            [ "STATE_NAME", "OPERATION", 'TEST_NUMBER', 'PARAMETER_NAME'],
            col_alias=col_alias
        )

        st.write(f"Filtered rows: {len(df_test)}")
        
        if not df_test.empty and len(df_test) < 3000:
            # Example: group by a column that exists, e.g. 'OPERATION' or 'STATE_NAME'
            total_group_operation = df_test.groupby(["pco", "config"]).size().reset_index(name='count')
            total_group_operation['GROUP_NAME'] = total_group_operation['pco'] + "_" + total_group_operation['config']
            group_name_list = total_group_operation['GROUP_NAME'].tolist()

            #st.write("all operations mmm:", group_name_list)
            # column_order = getPCOColumnOrder()
            # df_test["pco"] = pd.Categorical(df_test["pco"], categories=column_order, ordered=True)
            if avg_mode_tt_op_tt == "Weighted":
                if "TestTime(hrs)_wgt" in df_test.columns:
                    df_test["TestTime(hrs)"] = df_test["TestTime(hrs)_wgt"]
                    df_test["N"] = df_test["OPER_CNT"]
                else:
                    st.warning("Weighted average column 'TestTime(hrs)_wgt' not found. Using unweighted 'TestTime(hrs)' instead.")
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

            try:
                if len(test_time_cols) == 2:
                    gb.configure_column('TT_Diff', aggFunc="sum", type=["numericColumn", "customNumericFormat"], valueFormatter="x.toFixed(2)")
            except:
                pass
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

            #grid_options = gb.build()

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



            # Render AgGrid with export button and fixed column widths
            # Set column widths for key columns
            col_widths = {
                "TEST_NUMBER": 100,
                "PARAMETER_NAME": 180,
                "STATE_NAME": 120,
                "OPERATION": 110,
            }
            # Add widths for TT_ and N_ columns
            for col in tt_summary.columns:
                if col.startswith("TT_") or col.startswith("N_") or col == "TT_Diff":
                    col_widths[col] = 110

            # Extract the list of column fields from columnDefs
            for col, width in col_widths.items():
                if col in tt_summary.columns:
                    gb.configure_column(col, width=width,autoHeaderHeight=True,headerTooltip = col  )

            grid_options = gb.build()

            grid_response = AgGrid(
                tt_summary,
                gridOptions=grid_options,
                enable_enterprise_modules=True,
                update_mode=GridUpdateMode.NO_UPDATE,
                fit_columns_on_grid_load=False,  # Don't auto-fit, use our widths
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

            # csv = df_test.to_csv(index=False).encode('utf-8')
            # st.download_button(
            # label="Download Data as CSV",
            # data=csv,
            # file_name="test_time_by_test.csv",
            # mime="text/csv",
            # key="test_time_by_test_download_btn"
            # )

        else:
            st.info("No filtered data available. Query data above to view state-wise test time.")

def TestTime_Hist_block(title, df, groupby_cols=None):
    
    with st.expander(f"{title}", expanded=False):

        c0, c1, c2 = st.columns(3)
        default_programs = ["DORADO", "MARLIN", "MARLIN BP", "SUMMIT", "TSR"]
        params = st.query_params

        raw_program_params = params.get("program", params.get("product", []))
        with c0:
            program_filter = st.multiselect(
                "Select Product(s)",
                ["DORADO", "MARLIN", "MARLIN BP", "SUMMIT"],
                default=default_programs if raw_program_params else []
            )
        with c1:
            filter_text_tt_hist = st.text_input(
            "Filter Text Box",
            "",
            placeholder="Search in all columns...",
            key="filter_text_tt_hist"
            )

        with c2:
            logic_tt_hist = st.radio(
            "Search Mode",
            ["OR", "AND"],
            horizontal=True,
            key="logic_tt_hist",
            help="OR: Match any word | AND: Match all words, [col]_null to search for null values"
        )
        df_org = df.copy()
        if program_filter:  # If any programs are selected
            df = df[df['Product'].isin(program_filter)]
        else:  # If nothing selected, show all programs
            df = df_org
        df_f = apply_filter(
            df,
            filter_text_tt_hist,
            logic_tt_hist,
            config.QUERY_REQUEST_LOG_FILE_HISTORY_HEADER,
        )


        st.dataframe(df_f, use_container_width=True, height=15*32)
def load_test_time_hist_info():
    
    hist_fil = config.QUERY_REQUEST_LOG_FILE_HISTORY
    if os.path.exists(hist_fil):

        try:
            df_hist = pd.read_csv(hist_fil)
            
            return df_hist
        except Exception as e:
            st.error(f"Error loading historical data: {e}")

    else:
        st.info(f"No historical test time data found at {hist_fil}")
        return pd.DataFrame()
    



def extract_dict_from_test_parameters(tp) -> dict:
    if tp is None or (isinstance(tp, float) and np.isnan(tp)):
        return {}

    if isinstance(tp, dict):
        return tp

    if isinstance(tp, (list, tuple)):
        for x in tp:
            if isinstance(x, dict):
                return x
        return {}

    if isinstance(tp, str):
        m = re.search(r"\{.*?\}", tp, flags=re.DOTALL)  # non-greedy
        if not m:
            return {}
        try:
            return ast.literal_eval(m.group(0))
        except Exception:
            return {}

    return {}


def build_compare_table(d1: dict, d2: dict, name1: str, name2: str, tt1: str, tt2: str) -> pd.DataFrame:
    df_test_time = pd.DataFrame({
        "PARAMETERS": ["TEST_TIME_HR"],
        name1: [tt1],
        name2: [tt2],
    })
    keys = sorted(set(d1.keys()) | set(d2.keys()))
    df_parameters = pd.DataFrame({
        "PARAMETERS": keys,
        name1: [d1.get(k, None) for k in keys],
        name2: [d2.get(k, None) for k in keys],
    })
    df = pd.concat([df_test_time, df_parameters], ignore_index=True)
    return df


def build_ttp_table(d1: dict, name1: str, tt1: str) -> pd.DataFrame:
    df_test_time = pd.DataFrame({
        "PARAMETERS": ["TEST_TIME_HR"],
        name1: [tt1],
    })
    keys = sorted(set(d1.keys()))
    df_parameters = pd.DataFrame({
        "PARAMETERS": keys,
        name1: [d1.get(k, None) for k in keys],
    })
    df = pd.concat([df_test_time, df_parameters], ignore_index=True)
    return df


with st.expander("Test Time By Test Parameter", expanded=False):
    st.markdown('<div class="section-title">Test Time By Test Parameter</div>', unsafe_allow_html=True)

    # if not has_query_params:
    # force condition
    df_test_parameter = load_merged_test_time_by_test_parm().copy()
    st.write(f"Total rows before filter: {len(df_test_parameter)}")
    if df_test_parameter.empty:
        st.info("No data available. Please run query to load data.")
    else:

        c1_tt, c2_tt, c3_tt = st.columns(3)
        col_alias = {
            "STATE": "STATE_NAME",
            "OP": "OPERATION",
            "PARM": "PARAMETER_NAME",
            "TEST": "TEST_NUMBER",
        }
        with c1_tt:
            filter_text_tt_op_tt_detail = st.text_input(
            "Filter Text Box",
            "",
            placeholder="Search in all columns...",
            help=f"- Free terms (no \":\") search across search_cols (or all columns if None).\n- Column-specific terms use the syntax COL:VALUE, e.g. STATE:ZAP TEST:275\n- [STATE:STATE_NAME, OP:OPERATION, PARM:PARAMETER_NAME, TEST:TEST_NUMBER]",
            key="filter_text_tt_op_tt_detail"
            )

            
        with c2_tt:
            logic_tt_op_tt_detail = st.radio(
            "Search Mode",
            ["AND","OR"],
            horizontal=True,
            help="OR: Match any word | AND: Match all words, [col]_null to search for null values",
            key="logic_tt_op_tt_detail"
            )

        df_test = apply_filter_flex(
            df_test_parameter,
            filter_text_tt_op_tt_detail,
            logic_tt_op_tt_detail,
            [ "OPERATION", "STATE_NAME", 'TEST_NUMBER', 'PARAMETER_NAME', 'SPC_ID'],
            col_alias=col_alias
        )

        with c3_tt:
            st.success(f"Filtered rows: {len(df_test)}")

        if len(df_test) > 3000:
            st.warning("Too many rows after filtering. Please refine your filter to less than 3000 rows for better performance.")
            st.stop()
        
        KEY_COLS = ["OPERATION", "STATE_NAME", "PARAMETER_NAME", "TEST_NUMBER", "SPC_ID"]
        SHOW_COLS = ["check","STATE_NAME", "PARAMETER_NAME", "SPC_ID" ,"TEST_TIME_HR" ,"TEST_PARAMETERS"]

        def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
            if isinstance(df.columns, pd.MultiIndex):
                df = df.copy()
                df.columns = [
                    "_".join([str(x) for x in col if x not in (None, "", "nan")]).strip("_")
                    for col in df.columns
                ]
            return df

        if not df_test.empty:
            

            df_test_parameter_full_data = df_test.copy()

            df_test_parameter_pivot = df_test.pivot_table(
                index=KEY_COLS,
                columns=["GROUP_NAME"],
                values=[ "TEST_TIME_HR","TEST_PARAMETERS"],
                aggfunc={"TEST_TIME_HR": "sum", "TEST_PARAMETERS": "size"},
                fill_value=0
            ).reset_index()

            df_pivot_show = flatten_columns(df_test_parameter_pivot)

            # =========================== ORDER GROUP NAME BY COPILOT ======================
            value_cols = [c for c in df_pivot_show.columns if c not in KEY_COLS]
            groups = sorted(set("_".join(c.split("_")[2:]) for c in value_cols))
            ordered_cols = []
            for g in groups:
                tp = f"TEST_PARAMETERS_{g}"
                tt = f"TEST_TIME_HR_{g}"
                if tp in value_cols:
                    ordered_cols.append(tp)
                if tt in value_cols:
                    ordered_cols.append(tt)
            # final column order
            df_pivot_show = df_pivot_show[KEY_COLS + ordered_cols]
            # ==============================================================================


            # checkbox
            df_select = df_pivot_show.copy()
            if "check" not in df_select.columns:
                df_select.insert(0, "check", False)

            edited = st.data_editor(
                df_select,
                width="stretch",
                hide_index=True,
                column_config={
                    "check": st.column_config.CheckboxColumn(
                        "check",
                        help="select rows for compare parameter.",
                        default=False,
                    )
                },
                disabled=[c for c in df_select.columns if c != "check"],
                key="pivot_selector",
            )

            # filter only check rows
            selected_rows = edited[edited["check"] == True]

            st.write(f"Selected {len(selected_rows)} rows.")

            if selected_rows.empty:
                st.info("Please select row.")
            else:
                # remove duplicates rows
                selected_keys = selected_rows[KEY_COLS].drop_duplicates()

                filtered_full = df_test_parameter_full_data.merge(
                    selected_keys,
                    on=KEY_COLS,
                    how="inner"
                )

                # debug
                # st.write(selected_keys)
                # st.write(filtered_full)

                if "check" not in filtered_full.columns:
                    filtered_full.insert(0, "check", False)


                # GROUP_NAME
                if "GROUP_NAME" not in filtered_full.columns:
                    st.warning("Can not find columns GROUP_NAME in dataframe.")
                    st.dataframe(filtered_full, width="stretch")
                else:
                    groups = list(filtered_full["GROUP_NAME"].dropna().unique())

                    if len(groups) == 0:
                        st.warning("No GROUP_NAME")
                        st.dataframe(filtered_full, width="stretch")

                    elif len(groups) == 1:
                        st.subheader(f"Group: {groups[0]}")
                        # st.dataframe(
                        #     filtered_full[filtered_full["GROUP_NAME"] == groups[0]],
                        #     width="stretch"
                        # )
                        edited_parameter1 = st.data_editor(
                            filtered_full[filtered_full["GROUP_NAME"] == groups[0]][SHOW_COLS],
                            width="stretch",
                            hide_index=True,
                            column_config={
                                "check": st.column_config.CheckboxColumn(
                                    "check",
                                    help="select row for compare parameter.",
                                    default=False,
                                )
                            },
                            key="parameter1_selector",
                        )

                        sel1 = edited_parameter1[edited_parameter1["check"] == True]

                        if sel1.empty:
                            st.info("Please select at least one row.")
                        else:
                            tp1 = sel1.iloc[0]["TEST_PARAMETERS"]
                            tt1 = sel1.iloc[0]["TEST_TIME_HR"]
                            d1 = extract_dict_from_test_parameters(tp1)
                            df_parameter_table = build_ttp_table(d1, groups[0], tt1)
                            st.markdown("## Parameter Compare Table")
                            st.dataframe(df_parameter_table, width="stretch")

                    else:
                        if len(groups) == 2:
                            g1, g2 = groups[0], groups[1]
                            col1, col2 = st.columns(2)

                            df_g1 = filtered_full[filtered_full["GROUP_NAME"] == g1][SHOW_COLS].copy()
                            df_g2 = filtered_full[filtered_full["GROUP_NAME"] == g2][SHOW_COLS].copy()

                            
                            # if "check" not in df_g1.columns:
                            #     df_g1.insert(0, "check", False)
                            # if "check" not in df_g2.columns:
                            #     df_g2.insert(0, "check", False)

                            # auto select if df_g1 and df_g2 have a row.
                            default_value = len(df_g1) == 1 and len(df_g2) == 1

                            df_g1 = df_g1.assign(check=default_value)
                            df_g2 = df_g2.assign(check=default_value)

                            with col1:
                                st.markdown(f"### {g1}")
                                edited_parameter1 = st.data_editor(
                                    df_g1,
                                    width="stretch",
                                    hide_index=True,
                                    column_config={
                                        "check": st.column_config.CheckboxColumn(
                                            "check",
                                            help="select row for compare parameter.",
                                        )
                                    },
                                    disabled=[c for c in df_g1.columns if c != "check"],
                                    key="parameter1_selector",
                                )

                            with col2:
                                st.markdown(f"### {g2}")
                                edited_parameter2 = st.data_editor(
                                    df_g2,
                                    width="stretch",
                                    hide_index=True,
                                    column_config={
                                        "check": st.column_config.CheckboxColumn(
                                            "check",
                                            help="select row for compare parameter.",
                                        )
                                    },
                                    disabled=[c for c in df_g2.columns if c != "check"],
                                    key="parameter2_selector",
                                )

                            # --- select rows ---
                            sel1 = edited_parameter1[edited_parameter1["check"] == True]
                            sel2 = edited_parameter2[edited_parameter2["check"] == True]

                            st.write(f"Selected: {g1} = {len(sel1)} | {g2} = {len(sel2)}")

                            if sel1.empty and sel2.empty:
                                st.info("Please select at least one row.")
                            elif (not sel1.empty) and sel2.empty:
                                tp1 = sel1.iloc[0]["TEST_PARAMETERS"]
                                tt1 = sel1.iloc[0]["TEST_TIME_HR"]
                                d1 = extract_dict_from_test_parameters(tp1)
                                df_parameter_table = build_ttp_table(d1, g1, tt1)
                                st.markdown("## Parameter Compare Table1")
                                st.dataframe(df_parameter_table, width="stretch")
                            elif sel1.empty and (not sel2.empty):
                                tp2 = sel2.iloc[0]["TEST_PARAMETERS"]
                                tt2 = sel2.iloc[0]["TEST_TIME_HR"]
                                d2 = extract_dict_from_test_parameters(tp2)
                                df_parameter_table = build_ttp_table(d2, g2, tt2)
                                st.markdown("## Parameter Compare Table2")
                                st.dataframe(df_parameter_table, width="stretch")
                            else:
                                # compare only first row.
                                tp1 = sel1.iloc[0]["TEST_PARAMETERS"]
                                tp2 = sel2.iloc[0]["TEST_PARAMETERS"]

                                tt1 = sel1.iloc[0]["TEST_TIME_HR"]
                                tt2 = sel2.iloc[0]["TEST_TIME_HR"]

                                d1 = extract_dict_from_test_parameters(tp1)
                                d2 = extract_dict_from_test_parameters(tp2)

                                df_compare = build_compare_table(d1, d2, g1, g2, tt1, tt2)

                                st.markdown("## Parameter Compare Table")
                                # st.dataframe(df_compare, width="stretch")
                                # hightligh different data
                                mask = df_compare[g1] != df_compare[g2]
                                st.dataframe(
                                    df_compare.style.apply(
                                        lambda x: ['background-color: #ad9709' if mask[i] else '' for i in range(len(df_compare))],
                                        axis=0
                                    ),
                                    width="stretch"
                                )

                                st.write(f"Test time: {g1} = {tt1} hours | {g2} = {tt2} hours")
        else:
            st.info("No filtered data available. Query data above to view state-wise test time.")


        # if not df_test.empty:
        #     st.write(f"Filtered rows: {len(df_test)}")
            
        #     # Show ALL Data frame after fillter
        #     # st.write(df_test)

        #     df_test_parameter_full_data = df_test.copy()

        #     df_test_parameter_pivot = df_test.pivot_table(
        #         index=[ "OPERATION", "STATE_NAME", "PARAMETER_NAME", "TEST_NUMBER", "SPC_ID" ],
        #         columns=["GROUP_NAME",],
        #         values=["TEST_PARAMETERS"],
        #         aggfunc={"TEST_PARAMETERS": "size"},
        #         fill_value=0
        #     ).reset_index()

        #     st.write(df_test_parameter_pivot)
        # else:
        #     st.info("No filtered data available. Query data above to view state-wise test time.")



source_df = load_test_time_hist_info()
TestTime_Hist_block("Test Time Hist", source_df)