# save as app.py and run: streamlit run app.py
# pip install streamlit streamlit-aggrid

import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import os

st.markdown("""
<style>



/* Hide 4th page in sidebar nav */
[data-testid="stSidebarNav"] ul li:nth-of-type(4) {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# Function to check user access based on user_access_control_list.csv
def check_user_access(page_name):
    if "user" in st.session_state:
        user_gid = st.session_state["user"].get("gid")
        if user_gid:
            # Load the access control list
            acl = pd.read_csv("MASTER/user_access_control_list.csv")
            # Check if the user has access to the specified page
            user_access = acl[(acl["GID"] == int(user_gid)) & ((acl["Page"] == page_name) | (acl["Page"] == "All"))]
            st.write(user_access)
            if user_access.empty:

                st.markdown("""
                <style>
                section[data-testid="stSidebarNav"] {display: none;}
                </style>
                """, unsafe_allow_html=True)

                st.write("You do not have access to this page. kkkk")
                st.stop()
        else:
            st.success("Access granted.")
            st.stop()
                

    else:
        st.markdown("""
            <style>
            section[data-testid="stSidebarNav"] {display: none;}
            </style>
            """, unsafe_allow_html=True)

        st.write("You do not have access to this page. MMMM")
        st.stop()

page_name = os.path.basename(__file__).replace(".py", "")
check_user_access(page_name)


st.set_page_config(page_title="Grouped Table Example", layout="wide")

# ---------------- Sample data ----------------
def load_data():
    return pd.DataFrame({
        "Program":   ["P1", "P1", "P1", "P2", "P2", "P3"],
        "Operation": ["OP1", "OP1", "OP2", "OP1", "OP2", "OP1"],
        "State":     ["PASS", "FAIL", "PASS", "PASS", "FAIL", "PASS"],
        "TestTime":  [10.5, 12.0, 9.8, 11.2, 13.4, 8.9],
        "N":         [100, 50, 80, 120, 60, 90],
    })

df = load_data()

st.title("Row Grouped Table (Program + Operation visible)")

st.subheader("Raw Data")
st.dataframe(df, use_container_width=True)

st.subheader("Grouped Table (expand/collapse by Program & Operation)")

# ---------------- Build AgGrid options ----------------
gb = GridOptionsBuilder.from_dataframe(df)

# Group by Program and Operation, but keep them visible
gb.configure_column("Program", rowGroup=True, hide=True)
gb.configure_column("Operation", rowGroup=True, hide=True)

# Aggregation for numeric columns when grouped
gb.configure_column("TestTime", aggFunc="avg")
gb.configure_column("N", aggFunc="sum")

# General grid options
gb.configure_grid_options(
    groupDisplayType="multipleColumns",  # show group columns instead of hiding
    groupDefaultExpanded=0,              # 0 = collapsed, -1 = fully expanded
    animateRows=True,
    suppressAggFuncInHeader=False,
)

grid_options = gb.build()

# ---------------- Render AgGrid ----------------
grid_response = AgGrid(
    df,
    gridOptions=grid_options,
    enable_enterprise_modules=True,
    update_mode=GridUpdateMode.NO_UPDATE,
    fit_columns_on_grid_load=True,
    height=420,
)

# If you want to inspect data after user filters/sorts:
# updated_df = grid_response["data"]
# st.write(updated_df)
