#python -m streamlit run ttr_task_form.py
#http://localhost:8501/?product=DORADO
import streamlit as st
import pandas as pd
import config

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
                except Exception:
                    pass
                
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
                "'SAVE_NAME':'DRD_20HD_HSMR_TKDRH434H', 'MAX_QTY':500 }"
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
    product = st.selectbox(
        "Product",
        options=["DORADO", "MARLIN", "MARLIN BP", "SUMMIT"],  # Add more as needed
        key="gui_product"
    )

    
    # SBR input as text box
    sbr = st.text_input(
        "SBR#",
        value="",
        key="gui_sbr"
    )

    # HD_Count as combo box
    hd_count = st.selectbox(
        "HD Count",
        options=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10,11,12, 20],  # Example values
        key="gui_hd_count",
        help=("Select 0 for all heads on SBR#."),
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
    
    template_string = "plt={'FEATURE_CHECKING':'', 'JSL_SCRIPT':'ExecutePythonScript', 'PY_SCRIPT':'getSN_SBR_input.py', 'SBR_REQ':{'PRODUCT':'DORADO', 'SBR':'TKDRH434H'}, 'ATTR_FILTER': {'MEDIA_FORMAT':'HSMR', 'NUM_HEADS':'20'}, 'SAVE_NAME':'DRD_20HD_HSMR_TKDRH434H', 'MAX_QTY':500, 'DESCRIPTION' : 'DORADO PCO 3.7' }"
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
            sbr_value = sbr.strip().upper()

            sbr_req = {
                "PRODUCT": product,
                "SBR": sbr_value,
            }

            sbr_save_name = sbr.replace(',', '_').strip().upper()
            sbr_save_name = sbr_save_name.replace(' ', '').strip().upper()
            st.write(f"sbr_save_name: {sbr_save_name}")
            request_dict = {
                "FEATURE_CHECKING": "",
                "JSL_SCRIPT": "ExecutePythonScript",
                "PY_SCRIPT": "getSN_SBR_input.py",
                "SBR_REQ": sbr_req,
                "ATTR_FILTER": attr_filter_single,
                "SAVE_NAME": f"{short_name}_{hd_count:02d}H_{cfg[0]}_{sbr_save_name}",
                "MAX_QTY": 500,
                "DESCRIPTION": sbr_info.strip(),
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

st.caption(f"Total requests in queue: {lineCount()}")