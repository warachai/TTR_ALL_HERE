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

def submit_request_gui():
    text = request_text.strip()
    if not text:
        st.warning("Please enter a description before submitting.")
    else:

        if 1:
            req_id = str(uuid.uuid4())
            ss.last_request_id = req_id
            ss.data_request_text = text

            # Persist each line as a separate entry in the log file
            try:
                log_path = config.QUERY_REQUEST_LOG_FILE
                lines = [line for line in text.splitlines() if line.strip()]
                
                # Append or create
                try:
                    with open(log_path, "a+", encoding="utf-8") as f:
                        for line in lines:
                            f.write(f"{line}\n")
                except Exception as e:
                    st.error(f"Failed to write to log file: {e}")
                
            except Exception as e:
                st.error(f"Failed to record request: {e}")

            clear_text()
# Show warnings/success from submit callback
if "submit_warning" in st.session_state:
    st.warning(st.session_state["submit_warning"])
    del st.session_state["submit_warning"]

if "submit_success" in st.session_state:
    st.success(st.session_state["submit_success"])
    del st.session_state["submit_success"]
if 0:    
    st.markdown("Enter your request details below. You can paste multiple lines.")
    with st.expander("Text Request", expanded=False):
        # Big text box
        request_text = st.text_area(
            label="Request Description",
            value=ss.data_request_text,
            help=(
                "Describe your data request here.\n"
                "Example:\n"
                "plt={'FEATURE_CHECKING':'', 'JSL_SCRIPT':'ExecutePythonScript', "
                "'PY_SCRIPT':'getSN_SBR_input.py', 'SBR_REQ':{'PRODUCT':'DORADO', 'SBR':'TKDRH434H'}, "
                "'ATTR_FILTER': {'MEDIA_FORMAT':'HSMR', 'NUM_HEADS':'20'}, "
                "'SAVE_NAME':'DRD_20HD_HSMR_TKDRH434H', 'MAX_QTY':15000 }"
            ),
            height=300,
            key="data_request_text_area",
        )

        # Character count / simple validation
        st.caption(f"Characters: {len(request_text)}")

            
        def submit_request():
            
            text = request_text.strip()
            if not text:
                st.warning("Please enter a description before submitting.")
            else:

                if 1:
                    req_id = str(uuid.uuid4())
                    ss.last_request_id = req_id
                    ss.data_request_text = text

                    # Persist each line as a separate entry in the log file
                    try:
                        log_path = config.QUERY_REQUEST_LOG_FILE
                        lines = [line for line in text.splitlines() if line.strip()]
                        
                        # Append or create
                        try:
                            with open(log_path, "a+", encoding="utf-8") as f:
                                for line in lines:
                                    f.write(f"{line}\n")
                        except Exception:
                            pass
                        
                    except Exception as e:
                        st.error(f"Failed to record request: {e}")

                    clear_text()


        st.divider()


        
        colA, colB = st.columns([1, 7])
        with colA:
            submit = st.button("Submit Request", type="secondary", on_click=submit_request)
        with colB:
            st.button("Clear", on_click=clear_text)

        st.success(f"Request submitted. ID: {ss.last_request_id}")       



with st.expander("Gui Request", expanded=True):
    
    # Product input as combobox

    site_filter = st.selectbox(
        "Select Site",
        ["Korat", "SSDC", "LCO", "WUXI"],
        index=0
    )
                
    product = st.selectbox(
        "Product",
        options=["DORADO", "MARLIN", "MARLIN BP", "SUMMIT", "OSPREY", "CIMMARON_BP", "V15"],  # Add more as needed
        key="gui_product"
    )

    
    # SBR input as text box
    sbr = st.text_input(
        "SBR#",
        value="",
        key="gui_sbr"
    )

    colA, colB, colC, colD, colE = st.columns([3, 2, 2, 2, 2])
    with colA:
        # HD_Count as combo box
        hd_count = st.selectbox(
            "HD Count",
            options=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10,11,12, 20],  # Example values
            key="gui_hd_count",
            help=("Select 0 for all heads on SBR#."),
        )

    with colB:

        st.markdown(
            """
            <style>
            div[data-testid="stCheckbox"] {
                margin-top: 28px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        exclude_powerloss = st.checkbox(
            "Exclude PowerLoss",
            key="gui_exclude_powerloss",
            value=True,
        )

    with colC:
        st.markdown(
            """
            <style>
            div[data-testid="stCheckbox"] {
                margin-top: 28px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        exclude_ir = st.checkbox(
            "Exclude IR",
            key="gui_exclude_ir",
            value=True
        )

    with colD:
        st.markdown(
            """
            <style>
            div[data-testid="stCheckbox"] {
                margin-top: 28px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        validate_feature = st.checkbox(
            "Validate PCO Feature",
            key="gui_validate_feature",
            help="Validate that the PCO feature is based on the most loaded PCO, and only CMR."
        )        
    # Config as checkbox group
    configs = st.multiselect(
        "Config",
        options=["CMR", "SMR", "HSMR"],
        key="gui_config"
    )

     # SBR input as text box
    sbr_info = st.text_input(
        "SBR# DESCRIPTION",
        value="",
        key="gui_sbr_info"
    )
    
    template_string = "plt={'FEATURE_CHECKING':'', 'JSL_SCRIPT':'ExecutePythonScript', 'PY_SCRIPT':'getSN_SBR_input.py', 'SBR_REQ':{'PRODUCT':'DORADO', 'SBR':'TKDRH434H'}, 'ATTR_FILTER': {'MEDIA_FORMAT':'HSMR', 'NUM_HEADS':'20'}, 'SAVE_NAME':'DRD_20HD_HSMR_TKDRH434H', 'MAX_QTY':15000, 'DESCRIPTION' : 'DORADO PCO 3.7' }"
    # Button to submit GUI request
    def submit_gui_request():

        query_hist  = config.QUERY_REQUEST_LOG_FILE_HISTORY
        query_hist_header = config.QUERY_REQUEST_LOG_FILE_HISTORY_HEADER
     
        # Build request string from GUI selections
        attr_filter = {}
        if not configs:
            st.warning("Please select at least one Config before submitting.")
            return

        # Find short name from value in product config.PROGRAM_NAME_MAP
        short_name = product
        for k, v in config.PROGRAM_SHORT_NAME_MAP.items():
            if v == product:
                short_name = k
                break


        # Loop through selected configs and create a request for each
        for cfg in configs:
            attr_filter_single = attr_filter.copy()
            attr_filter_single["MEDIA_FORMAT"] = cfg
            if hd_count:
                attr_filter_single["NUM_HEADS"] = str(hd_count)
            elif "NUM_HEADS" in attr_filter_single:
                del attr_filter_single["NUM_HEADS"]
            # If SBR contains a comma, wrap it in double quotes

            if exclude_powerloss:
                attr_filter_single["POWER_LOSS_DRIVE"] = "N"
            if exclude_ir:
                attr_filter_single["IR_DRIVE"] = "N"    
            if validate_feature:
                attr_filter_single["PCO_FEATURE_CHECK"] = "Y"

            sbr_value = sbr.strip().upper()

            sbr_req = {
                "PRODUCT": product,
                "SBR": sbr_value,
            }

            sbr_save_name = sbr.replace(',', '_').strip().upper()
            sbr_save_name = sbr_save_name.replace(' ', ',').strip().upper()
            st.write(f"sbr_save_name: {sbr_save_name}")
            request_dict = {
                "FEATURE_CHECKING": "",
                "JSL_SCRIPT": "ExecutePythonScript",
                "PY_SCRIPT": "getSN_SBR_input.py",
                "SBR_REQ": sbr_req,
                "ATTR_FILTER": attr_filter_single,
                "SAVE_NAME": f"{short_name}_{hd_count:02d}H_{cfg[0]}_{sbr_save_name}",
                "MAX_QTY": config.MAX_QUERY_QTY,
                "DESCRIPTION": sbr_info.strip(),
                "SITE": site_filter
            }
            request_str = f"plt={request_dict}"
            # Save to log file
            try:
                log_path = config.QUERY_REQUEST_LOG_FILE
                # Read all existing lines to avoid duplicates
                with open(log_path, "a+", encoding="utf-8") as f:
                    f.seek(0)
                    existing_lines = set(line.strip() for line in f.readlines())
                    if request_str.strip() not in existing_lines:
                        f.write(f"{request_str}\n")

                with open(query_hist, "a+", encoding="utf-8") as f_hist:
                    # If file is new, write header
                    f_hist.seek(0)
                    if f_hist.readline() == "":
                        f_hist.write(",".join(query_hist_header) + "\n")
                    from datetime import datetime
                    user = st.session_state.get("user_name", "anonymous")
                    dt_str = datetime.utcnow().isoformat(timespec="seconds")
                    row = [
                        user,
                        dt_str,
                        product,
                        cfg,
                        str(hd_count),
                        f'"{sbr.strip().upper()}"',
                        f"{short_name}_{hd_count:02d}H_{cfg[0]}_{sbr_save_name}",
                        f'"{sbr_info.strip()}"',
                        f'"{request_str}"'
                    ]
                    f_hist.write(",".join(row) + "\n")

            except Exception as e:
                st.error(f"Failed to record GUI request: {e}")
        st.success("All GUI requests submitted. MMM")

    def clear_gui_fields():
        ss.gui_product = "DORADO"
        ss.gui_sbr = ""
        ss.gui_hd_count = 0
        ss.gui_config = []
        ss.gui_sbr_info = ""

    def submit_gui_request_and_clear():
        submit_gui_request()
        clear_gui_fields()

    st.button("Submit GUI Request", on_click=submit_gui_request_and_clear)


with st.expander("SN Upload Request", expanded=False):
    # File uploader for CSV
    uploaded_file = st.file_uploader(
        "Upload CSV file (must contain SERIAL_NUM, TRANS_SEQ, GROUP_NAME columns)",
        type=['csv'],
        key="sn_upload_file"
    )

    # Description text box for SN Upload
    sn_upload_description = st.text_input(
        "Description",
        value="",
        key="sn_upload_description",
        help="Enter a description for this SN upload request"
    )
    
    if uploaded_file is not None:
        try:
            # Read the CSV file
            df = pd.read_csv(uploaded_file)
            
            # Validate required columns
            required_cols = ['SERIAL_NUM', 'TRANS_SEQ', 'GROUP_NAME']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"Missing required columns: {', '.join(missing_cols)}")
            else:
                st.success(f"File uploaded successfully! Total rows: {len(df)}")
                
                st.subheader("Summary by Group")
                group_summary = df.groupby('GROUP_NAME').agg({ 'SERIAL_NUM': 'count',}).reset_index()
                group_summary.columns = ['GROUP_NAME', 'Count']
                
                # Display summary table
                st.dataframe(group_summary)
                
                # Display total count
                st.metric("Total Records", len(df))
                st.metric("Total Groups", df['GROUP_NAME'].nunique())

                # Button to show total row count
                if st.button("Submit Request", key="count_rows_btn"):
  
                    template_string = "plt={'FEATURE_CHECKING':"",'JSL_SCRIPT':'ExecutePythonScript','PY_SCRIPT':'getSN_TS_input.py', 'CSV_SN_LOC':r'R:\SU373GE_02-14495', 'ATTR_FILTER': {}, 'MAX_QTY': 15000 }"
                    # Button to submit GUI request
                    if 1:

                        query_hist  = config.QUERY_REQUEST_LOG_FILE_HISTORY
                        query_hist_header = config.QUERY_REQUEST_LOG_FILE_HISTORY_HEADER
                        for group_name in group_summary['GROUP_NAME'].unique():

                            df_filtered = df[df['GROUP_NAME'] == group_name]
                            # Check if folder exists, create if not
                            folder_path = os.path.join("r:/", group_name)
                            if not os.path.exists(folder_path):
                                os.makedirs(folder_path)
                            
                            # Save filtered dataframe to CSV in the group folder
                            csv_filename = f"SN.csv"
                            csv_path = os.path.join(folder_path, csv_filename)
                            df_filtered.to_csv(csv_path, index=False)
  

                            sbr_save_name = sbr.replace(',', '_').strip().upper()
                            sbr_save_name = sbr_save_name.replace(' ', '').strip().upper()
                            st.write(f"sbr_save_name: {sbr_save_name}")
                            request_dict = {
                                "FEATURE_CHECKING": "",
                                "JSL_SCRIPT": "ExecutePythonScript",
                                "PY_SCRIPT": "getSN_SN_TS_input.py",
                                "CSV_SN_LOC": folder_path,
                                "ATTR_FILTER": {},
                                "MAX_QTY": config.MAX_QUERY_QTY,
                                "DESCRIPTION": sn_upload_description.strip(),
                            }

                            request_str = f"plt={request_dict}"
                            # Save to log file
                            try:
                                log_path = config.QUERY_REQUEST_LOG_FILE
                                # Read all existing lines to avoid duplicates
                                with open(log_path, "a+", encoding="utf-8") as f:
                                    f.seek(0)
                                    existing_lines = set(line.strip() for line in f.readlines())
                                    if request_str.strip() not in existing_lines:
                                        pass
                                        f.write(f"{request_str}\n")

                                with open(query_hist, "a+", encoding="utf-8") as f_hist:
                                    # If file is new, write header
                                    f_hist.seek(0)
                                    if f_hist.readline() == "":
                                        f_hist.write(",".join(query_hist_header) + "\n")
                                    from datetime import datetime

                                    user = st.session_state.get("user_name", "anonymous")
                                    dt_str = datetime.utcnow().isoformat(timespec="seconds")
                                    row = [
                                        user,
                                        dt_str,
                                        "",
                                        "",
                                        "",
                                        group_name,
                                        group_name,
                                        sn_upload_description,
                                        f'"{request_str}"'
                                    ]
                                    f_hist.write(",".join(row) + "\n")

                            except Exception as e:
                                st.error(f"Failed to record GUI request: {e}")
                        st.success("Requests submitted.")                    
                
        except Exception as e:
            st.error(f"Error reading file: {e}")
            pass

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


def count_test_time_hist_info(product,media_format,save_name):
    
    if pd.isna(product) or pd.isna(media_format) or pd.isna(save_name):
        return 0
    
    currnet_config_file = os.path.join( config.TT_HISTORY_PATH,str(product),str(media_format),str(save_name), config.GROUP_INFO_FILE_NAME)
    if os.path.exists(currnet_config_file):
        try:
            with open(currnet_config_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            line_count = 0
            pass

        return len(lines)

    else:

        return 0


def TestTime_Hist_block(title, df, groupby_cols=None):
    
    with st.expander(f"{title}", expanded=False):

        c0, c1, c2 = st.columns(3)
        default_programs = ["DORADO", "MARLIN", "MARLIN BP", "SUMMIT", "TSR"]
        default_sites = ["Korat", "SSDC", "LCO", "WUXI"]
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

        KEY_COL = "REQUEST_STRING"

        def prepare_editor_df(df_f: pd.DataFrame) -> pd.DataFrame:
            df = df_f.copy()

            # calculate / refresh Total Data every time
            df["Rows"] = df.apply(
                lambda row: count_test_time_hist_info(
                    row["Product"],
                    row["MEDIA_FORMAT"],
                    row["SAVE_NAME"]
                ),
                axis=1
            )

            if "Selected" not in df.columns:
                df["Selected"] = False



            if "df_editor" in st.session_state:
                old_df = st.session_state.df_editor.copy()

                if KEY_COL in old_df.columns and KEY_COL in df.columns:
                    selected_map = old_df.set_index(KEY_COL)["Selected"].to_dict()
                    df["Selected"] = df[KEY_COL].map(selected_map).fillna(False)
                    
            cols = ["Selected", "Rows"] + [col for col in df.columns if col not in ["Selected", "Rows"]]
            df = df[cols]

            return df

        st.session_state.df_editor = prepare_editor_df(df_f)
        # show editor
        edited_df = st.data_editor(
            st.session_state.df_editor,
            key="table",
            disabled=[col for col in st.session_state.df_editor.columns if col != "Selected"],
            use_container_width=True,
            height=15 * 30
        )
        # always sync latest UI back into session_state
        st.session_state.df_editor = edited_df.copy()
        st.metric("Total Selected", st.session_state.df_editor["Selected"].sum())
        if st.button("Request Refresh Data."):
            
            #clicked_rows = edited_df[edited_df["Selected"] == True]
            clicked_rows = st.session_state.df_editor[
                            st.session_state.df_editor["Selected"] == True
                            ]

            if not clicked_rows.empty:
                log_path = config.QUERY_REQUEST_LOG_FILE
                # Read all existing lines to avoid duplicates
                with open(log_path, "a+", encoding="utf-8") as f:
                    f.seek(0)
                    existing_lines = set(line.strip() for line in f.readlines())

                    for i, row in clicked_rows.iterrows():
                        request_str = row['REQUEST_STRING']
                        st.write(f"Running code for {request_str}")

                        if request_str.strip() not in existing_lines:
                            pass
                            f.write(f"{request_str}\n")
                        st.session_state.df_editor.at[i, "Selected"] = False

                st.rerun()  # Refresh the page to reset checkboxes and reflect any changes



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
    
source_df = load_test_time_hist_info()
TestTime_Hist_block("Test Time Hist", source_df)

st.caption(f"Total requests in queue: {lineCount()}")