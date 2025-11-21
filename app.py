import streamlit as st
import getpass
user = getpass.getuser()

st.title("📌 Welcome user :" + user )
st.write("This page shows summary charts and KPIs.")

