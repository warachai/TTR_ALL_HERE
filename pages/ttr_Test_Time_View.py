import streamlit as st
import pandas as pd

df = pd.DataFrame({
    "name": ["A", "B"],
    'data': [123, 456],
    "link": [
        "http://localhost:8501/page2?item=A",
        "http://localhost:8501/page2?item=B"
    ]
})

st.dataframe(df)
df["link"] = df["name"].apply(
     lambda x: f"/Page2?item={x}"
)

st.dataframe(
    df,
    column_config={
        "link": st.column_config.LinkColumn("Open")
    }
)