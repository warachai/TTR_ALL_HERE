import streamlit as st
import pandas as pd
import config
import access_logging as access
from datetime import date

st.set_page_config(page_title="Site Access Summary", layout="wide")

st.title("Site Access Summary")

df = access.read_access_log()
if df.empty or 'timestamp' not in df.columns:
    st.info("No access records logged yet or log schema not initialized.")
    st.stop()

# Parse timestamps robustly (coerce errors) and drop invalid rows
ts = pd.to_datetime(df["timestamp"], errors="coerce")
df = df.assign(timestamp_dt=ts).dropna(subset=["timestamp_dt"])
if df.empty:
    st.info("All timestamp rows invalid - waiting for new accesses.")
    st.stop()

# Date filter (start date)
min_date = df["timestamp_dt"].min().date()
start_date = st.date_input("Start date", value=min_date, min_value=min_date)

df_filtered = df[df["timestamp_dt"].dt.date >= start_date]

st.caption(f"Total hits (filtered): {len(df_filtered)} | Total unique users: {df_filtered['user'].nunique()} | Total pages: {df_filtered['page'].nunique()}")

tab1, tab2, tab3 = st.tabs(["By User", "By Page", "Raw Log"])

with tab1:
    user_counts = df_filtered.groupby("user").size().reset_index(name="hits").sort_values("hits", ascending=False)
    st.dataframe(user_counts, hide_index=True)

with tab2:
    page_counts = df_filtered.groupby("page").size().reset_index(name="hits").sort_values("hits", ascending=False)
    st.dataframe(page_counts, hide_index=True)

with tab3:
    st.dataframe(df_filtered.drop(columns=["timestamp_dt"]), hide_index=True)

st.markdown("\n")
st.caption("Access logging based on query param ?user=NAME or OS user; session id persists for browser session.")
