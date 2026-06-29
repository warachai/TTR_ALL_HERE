#python -m streamlit run ttr_task_form.py
#http://localhost:8501/?product=DORADO
import streamlit as st
import pandas as pd
import config
import os
from streamlit import session_state as ss
import uuid

st.set_page_config(page_title="SBR Query Data Request", layout="wide")

st.title("Query Data Request")

# Initialize session keys
if "data_request_text" not in ss:
	ss.data_request_text = ""
if "last_request_id" not in ss:
	ss.last_request_id = None

def lineCount():
    lines = []
    try:
        with open(config.QUERY_REQUEST_LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
         line_count = 0
         pass

    return len(lines)

def clear_text():
    st.session_state["data_request_text_area"] = ""

def apply_filter(df, text, logic="OR", search_cols=None):
    #st.write(f"origianl df length: {len(df)}, columns: {df.columns}")
    if not text:
        return df
    if search_cols is None:
        search_cols = df.columns
        #st.write(f"origianl2 df length: {len(df)}, columns: {df.columns}")

    terms = [t.strip() for t in text.split() if t.strip()]
    if not terms:
        return df

    #st.write(f"Applying filter with terms: {terms} and logic: {logic}, columns: {search_cols}")
    #return df
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

def TestTime_Hist_block(title, df, groupby_cols=None, expand=False):
    
    with st.expander(f"{title}", expanded=expand):
        #st.write(f"Total Records Original : {len(df)}")
        c0, c1, c2 = st.columns(3)
        default_programs = ["DORADO", "MARLIN", "MARLIN BP", "SUMMIT", "TSR"]
        params = st.query_params

        raw_program_params = params.get("program", params.get("product", params.get("PRODUCT", [])))
        with c0:
            program_filter = st.multiselect(
                "Select Product(s)",
                ["DORADO", "MARLIN", "MARLINBP", "SUMMIT"],
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
            st.write(f'Product is in { "PRODUCT" in df.columns }')
            df = df[df['PRODUCT'].isin(program_filter)]
        else:  # If nothing selected, show all programs
            df = df_org

        #st.write(f"Total Records Before : {len(df)}")
        df_f = apply_filter(
            df,
            filter_text_tt_hist,
            logic_tt_hist,
            
        )
        #st.write(f"Total Records After : {len(df_f)}")



        df_f['Link'] = df_f.apply(
                            lambda row: f"http://10.7.194.231:8501/ttr_Test_Time_Compare_View?prog_0={row['PRODUCT']}&cfg_0={row['MEDIA_FORMAT']}&pco_0={row['GROUP_NAME']}&attr_1=NUM_HEADS&val_1={int(row['NUM_HEADS'])}",
                            axis=1
                            )
        cols = ["Link"] + [col for col in df_f.columns if col not in ["Link",]] 
        df_f = df_f[cols]
        st.dataframe(df_f, 
                     use_container_width=True,
                     column_config={
                    "Link": st.column_config.LinkColumn("Open", display_text="View")}, 
                    height=15*32)



def load_test_time_hist_info():
    
    all_data_hist_path = config.TT_HISTORY_PATH
    group_file = config.GROUP_INFO_FILE_NAME

    if os.path.exists(all_data_hist_path):
        pass
        try:
            _path = os.path.join(all_data_hist_path, group_file)
            df_hist = pd.DataFrame()
            
            for root, dirs, files in os.walk(all_data_hist_path):
                for file in files:
                    if group_file in file:
                        current_folder = os.path.basename(root)
                        #st.write(f"Loading historical data from {current_folder}...")
                        file_path = os.path.join(root, file)
                        df_temp = pd.read_csv(file_path)
                        df_temp['GROUP_NAME'] = current_folder

                        if 'PRODUCT' not in df_temp.columns:
                            st.write(f"Warning: 'PRODUCT' column not found in {file_path}. Adding with default value 0.")
                        try:
                            df_temp = df_temp.groupby(['PRODUCT','GROUP_NAME', 'CMS_CONFIG', 'MEDIA_FORMAT', 'OPERATION', 'SUB_BUILD_GROUP', 'NUM_HEADS']).size().reset_index(name='count')
                        except Exception as e:
                            continue
                            st.error(f"Error grouping data: {e}")
                        
                        df_hist = pd.concat([df_hist, df_temp], ignore_index=True)
            
            
            # df_hist = (df_hist.groupby()["OPERATION"]
            #         .agg(lambda s: ", ".join(s.astype(str)))
            #         .reset_index())

            df_hist = (df_hist.assign(OP_CNT=df_hist["OPERATION"].astype(str) + "-" + df_hist["count"].astype(int).astype(str))
                    .groupby(['PRODUCT','GROUP_NAME', 'CMS_CONFIG', 'MEDIA_FORMAT', 'SUB_BUILD_GROUP', 'NUM_HEADS'], as_index=False)
                    .agg({"count": "sum","OP_CNT": lambda s: ", ".join(s)})
                    .rename(columns={"count": "TOTAL_COUNT","OP_CNT": "OPERATION"}))

            oper_list = config.HAMR_OPER_LIST
            df_hist["MISS_OPER"] = df_hist["OPERATION"].apply(lambda x: ", ".join([op for op in oper_list if op != "Total" and op not in [item.split("-")[0] for item in x.split(", ")]]))
            
            df_hist["MISS_OPER"] = df_hist["MISS_OPER"].apply(lambda x: f"{len(x.split(', ')) if x else 0}: {x}")
            # Reorder: MISS_OPER before TOTAL_COUNT
            cols = df_hist.columns.tolist()
            cols.remove("MISS_OPER")
            tc_idx = cols.index("TOTAL_COUNT")
            cols.insert(tc_idx, "MISS_OPER")
            df_hist = df_hist[cols]
            
            return df_hist
        except Exception as e:
            st.error(f"Error loading historical data: {e}")

    else:
        st.info(f"No historical test time data found ")
        return pd.DataFrame()



#if st.button("Load DataFrame"):

source_df = load_test_time_hist_info()

#st.write(f"Loaded historical data with {len(source_df)} records.")

TestTime_Hist_block("Test Time Hist", source_df, expand=True)        
