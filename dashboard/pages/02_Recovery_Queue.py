import streamlit as st
from dashboard.app import api_get

st.title("Recovery Queue")
status = st.selectbox("Status", ["failed", "abandoned", "success"])
data = api_get("/transactions", {"status": status, "limit": 100})
st.dataframe(data["items"], use_container_width=True, hide_index=True)
