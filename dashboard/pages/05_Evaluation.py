import streamlit as st
from dashboard.app import api_get

st.title("Evaluation")
metrics = api_get("/metrics")
first, second, third = st.columns(3)
first.metric("Transactions", metrics["transactions"])
second.metric("Revenue at risk", f"₹{metrics['revenue_at_risk_paise'] / 100:,.0f}")
third.metric("Observed recovery rate", f"{metrics['recovery_rate']:.1f}%")
st.subheader("Recovery status counts")
st.dataframe(
	[{"status": status, "count": count} for status, count in metrics["recovery_status_counts"].items()],
	use_container_width=True,
	hide_index=True,
)
