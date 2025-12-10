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

st.markdown("Enter your request details below. You can paste multiple lines.")

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

# Show warnings/success from submit callback
if "submit_warning" in st.session_state:
    st.warning(st.session_state["submit_warning"])
    del st.session_state["submit_warning"]

if "submit_success" in st.session_state:
    st.success(st.session_state["submit_success"])
    del st.session_state["submit_success"]

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
	submit = st.button("Submit Request", type="primary", on_click=submit_request)
with colB:
	st.button("Clear", on_click=clear_text)

st.success(f"Request submitted. ID: {ss.last_request_id}")       
st.caption(f"Total requests in queue: {lineCount()}")
