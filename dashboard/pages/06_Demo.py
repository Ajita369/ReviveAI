import streamlit as st
from dashboard.app import api_get, api_post

st.title("Recovery Demo")
st.caption("Stubborn Gateway: bounded retries followed by human escalation.")
reset_col, step_col = st.columns(2)
with reset_col:
	reset_clicked = st.button("Reset Demo")
with step_col:
	step_clicked = st.button("Run Next Attempt")

if reset_clicked:
	api_post("/demo/reset")
	st.success("Demo reset.")
if step_clicked:
	result = api_post("/demo/step")
	if result["status"] == "escalated":
		st.warning(result["message"])
	else:
		st.info(result["message"])
	st.write(f"Attempts: {result['attempts']} / 3")

try:
	detail = api_get("/transactions/txn_fail_demo")
	st.metric("Current attempts", f"{detail['transaction']['total_recovery_attempts']} / 3")
	st.write(f"Status: `{detail['transaction']['recovery_status']}`")
	st.dataframe(detail["attempts"], use_container_width=True, hide_index=True)
except Exception:
	st.info("Click Reset Demo to create the demo transaction.")
