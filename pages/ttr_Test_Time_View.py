# http://localhost:8501/ttr_Test_Time_View?prog_0=SUMMIT&cfg_0=CMR&pco_0=PYTHON_374&prog_1=SUMMIT&cfg_1=CMR&pco_1=PYTHON_373
# http://localhost:8501/ttr_Test_Time_View?prog_0=MARLIN&cfg_0=SMR&pco_0=PCO2&prog_1=DORADO&cfg_1=HSMR&pco_1=PCO3

import streamlit as st
import pandas as pd
import os
from pathlib import Path

st.set_page_config(page_title="Test Time View", layout="wide")

test_time_folder = r"R:\Test_Time_Hist"

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
@st.cache_data
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
    selected = {}
    for idx in range(3):
        selected[idx] = {
            "program": st.session_state.get(f"prog_{idx}", "NONE"),
            "config": st.session_state.get(f"cfg_{idx}", "NONE"),
            "pco": st.session_state.get(f"pco_{idx}", "NONE"),
        }

    # Example: Check if path exists for each selected slot
    user_selected = []
    for idx, sel in selected.items():
        prog, cfg, pco = sel["program"], sel["config"], sel["pco"]
        if prog != "NONE" and cfg != "NONE" and pco != "NONE":
            path = os.path.join(test_time_folder, prog, cfg, pco, "DRV_INV.csv")
            if path not in user_selected:
                user_selected.append(path)
            st.write("path :",path)

    
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
        st.warning("No DRV_INV.csv files found. Using example data.")
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
for slot_idx in range(3):
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

        col1, col2, col3 = st.columns(3)

        def program_block(col, idx: int):
            """One column: Program / Config / PCO as combo boxes."""
            with col:
                st.subheader(f"Slot {idx+1}")

                # Determine default index from query params or NONE
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

                # Dynamically get config options based on selected program
                available_configs = get_config_options_for_program(prog)
                cfg_idx = available_configs.index(cfg_default) if cfg_default in available_configs else 0

                cfg = st.selectbox(
                    "Config Type",
                    available_configs,
                    index=cfg_idx,
                    key=f"cfg_{idx}",
                )

                # Dynamically get PCO options based on selected program and config
                available_pcos = get_pco_options_for_config(prog, cfg)
                pco_idx = available_pcos.index(pco_default) if pco_default in available_pcos else 0

                pco = st.selectbox(
                    "PCO",
                    available_pcos,
                    index=pco_idx,
                    key=f"pco_{idx}",
                )

                return prog, cfg, pco

        sel1 = program_block(col1, 0)
        sel2 = program_block(col2, 1)
        sel3 = program_block(col3, 2)


        # Query Data button filters df_raw by selected slots (OR logic between the two)
        # Auto-query if URL params detected
        query_btn_pressed = st.button("Query Data", key="query_data_btn", help="Filter data using selected Program/Config/PCO slots (NONE means no filter)")
        if query_btn_pressed:
            # Clear previous filtered data so next block uses new selection
            if "tt_filtered" in st.session_state:
                del st.session_state.tt_filtered
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
                # Ignore completely NONE slot (keeps all True) unless other slot narrows
                return m
            masks = []
            for slot in (sel1, sel2, sel3):
                if any(v != "NONE" for v in slot):
                    masks.append(slot_mask(slot))
            if masks:
                combined = masks[0]
                for m in masks[1:]:
                    combined |= m
                filtered_df = df_raw[combined]
            else:
                filtered_df = df_raw  # all NONE selected -> no filtering
            st.session_state.tt_filtered = filtered_df

        st.markdown('</div>', unsafe_allow_html=True)

# (you can later use sel1/sel2/sel3 to filter df_raw)

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


def test_time_block(title, df, key_prefix, groupby_cols=None):
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

    if groupby_cols:
        # Create pivot table with specified rows, columns, and values
        df_view = df_f.pivot_table(
            index=["program", "OPERATION"],
            columns=["pco", "config"],
            values="TEST_TIME",
            aggfunc=["mean", "count"],
            fill_value=0
        )
        df_view.reset_index(inplace=True)
    else:
        df_view = df_f

    
    # Order df_view OPERATION column by custom order if present
    custom_order = ["SCOPY", "PRE2", "LZR", "CAL", "NTZ", "CAL2", "FNC2", "SPSC2", "CRT2", "PWT", "FIN2"]
    if "OPERATION" in df_view.columns:
        df_view["OPERATION"] = pd.Categorical(df_view["OPERATION"], categories=custom_order, ordered=True)
        df_view = df_view.sort_values("OPERATION")
    st.dataframe(df_view, use_container_width=True, height=20*32)


# -------------------------------------------------------------------
# Middle: Test Time
# title, df, key_prefix, groupby_cols=None
# -------------------------------------------------------------------
df_raw['TEST_TIME'] = pd.to_numeric(df_raw['TEST_TIME'], errors='coerce').fillna(0)
df_raw['TEST_TIME_org'] = pd.to_numeric(df_raw['TEST_TIME'], errors='coerce').fillna(0)
df_raw['TEST_TIME'] = df_raw['TEST_TIME'] / 3600
test_time_block("Test Time", df_raw, "tt_overall", groupby_cols=["program", "config", "pco", "Category"])


st.markdown("---")

