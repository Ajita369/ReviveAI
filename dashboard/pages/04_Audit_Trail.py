import streamlit as st
from dashboard.app import api_get

st.title("Audit Trail")
transaction_id = st.text_input("Filter by transaction ID")
params = {"limit": 200}
if transaction_id:
	params["transaction_id"] = transaction_id
events = api_get("/audit", params)["items"]
if events:
	st.dataframe(events, use_container_width=True, hide_index=True)
else:
	st.info("No audit events found for this filter.")
