import streamlit as st
import pandas as pd

df = pd.DataFrame({
    "Task": ["AA", "BB", "CC"],
    "Owner": ["Tom", "Jane", "John"],
    "Status": ["Done", "Pending", "Review"]
})

# generate link column dynamically for each row
df["Dynamic Link"] = df.apply(
    lambda row: f"https://aaa.com/{row['Task']}/{row['Status']}",
    axis=1
)

st.data_editor(
    df,
    column_config={
        "Dynamic Link": st.column_config.LinkColumn(
            "Detail",
            display_text="Open"
        )
    },
    hide_index=True
)
