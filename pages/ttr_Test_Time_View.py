# http://localhost:8501/ttr_Test_Time_View?prog_0=SUMMIT&cfg_0=CMR&pco_0=PYTHON_374&prog_1=SUMMIT&cfg_1=CMR&pco_1=PYTHON_373
# http://localhost:8501/ttr_Test_Time_View?prog_0=MARLIN&cfg_0=SMR&pco_0=PCO2&prog_1=DORADO&cfg_1=HSMR&pco_1=PCO3

import streamlit as st
import pandas as pd
import os
from pathlib import Path
import plotly.express as px
import numpy as np


st.set_page_config(page_title="Test Time View", layout="wide")

test_time_folder = r"R:\Test_Time_Hist"

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
    for idx in range(3):
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
        query_btn_pressed = st.button(
            "Query Data",
            key="query_data_btn",
            help="Apply current selections and update URL with non-NONE values"
        )
        if query_btn_pressed:
            # Build parameter dict from current live selections (user setting)
            param_pairs = []
            for idx, (prog, cfg, pco) in enumerate([sel1, sel2, sel3]):
                if prog != "NONE":
                    param_pairs.append((f"prog_{idx}", prog))
                if cfg != "NONE":
                    param_pairs.append((f"cfg_{idx}", cfg))
                if pco != "NONE":
                    param_pairs.append((f"pco_{idx}", pco))

            # Update URL query params (new API if available, fallback to experimental)
            try:
                st.query_params.clear()
                for k, v in param_pairs:
                    st.query_params[k] = v
            except Exception:
                if param_pairs:
                    st.experimental_set_query_params(**{k: v for k, v in param_pairs})
                else:
                    # Clear params if all NONE
                    st.experimental_set_query_params()

            # Clear previous filtered data so next block recomputes with new params
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
                # All selections are NONE: treat as "no data selected" and return blank DataFrame
                filtered_df = pd.DataFrame(columns=df_raw.columns)
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

    # If no data selected (empty df) show blank table immediately
    if df_f.empty:
        st.dataframe(pd.DataFrame(), use_container_width=True, height=8*32)
        return
    if not has_query_params:
        return
    if groupby_cols:
        # Create pivot table with specified rows, columns, and values
        df_view = df_f.pivot_table(
            index=["program", "OPERATION"],
            columns=["pco", "config"],
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

        # Add TOTAL summary row (sum counts, weighted mean for means)
        if not df_view.empty:
            total_row = {}
            for col in df_view.columns:
                if col in ["program", "OPERATION"]:
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
            total_row["program"] = "ALL"
            total_row["OPERATION"] = "ALL"
            df_view = pd.concat([df_view, pd.DataFrame([total_row])], ignore_index=True)
    else:
        df_view = df_f

    
    # Order df_view OPERATION column by custom order if present
    custom_order = ["SCOPY", "PRE2", "LZR", "CAL", "NTZ", "CAL2", "FNC2", "SPSC2", "CRT2", "PWT", "FIN2"]
    if "OPERATION" in df_view.columns:
        df_view["OPERATION"] = pd.Categorical(df_view["OPERATION"], categories=custom_order, ordered=True)
        df_view = df_view.sort_values("OPERATION")
    st.dataframe(df_view, use_container_width=True, height=15*32)


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
test_time_block("Test Time", source_df, "tt_overall", groupby_cols=["program", "config", "pco", "Category"])


st.markdown("---")

# -------------------------------------------------------------------
# Bottom: Distribution Charts for Selected Data
# -------------------------------------------------------------------

with st.expander("Test Time Distribution", expanded=True):
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

        hover_cols = [c for c in ["program", "config", "pco", "Category", "SubCat"] if c in df_dist.columns]

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

