import streamlit as st
from dashboard.app import api_get, api_post

st.title("Transaction Detail")
transaction_id = st.text_input("Transaction ID")
if transaction_id:
    try:
        detail = api_get(f"/transactions/{transaction_id}")
        st.json(detail)
        analyze_col, recover_col = st.columns(2)
        with analyze_col:
            analyze_clicked = st.button("Analyze")
        with recover_col:
            recover_clicked = st.button("Trigger Recovery")
        if analyze_clicked:
            st.json(api_post(f"/analyze/{transaction_id}"))
        if recover_clicked:
            try:
                recovery = api_post(f"/recover/{transaction_id}")
                if recovery["status"] == "recovered":
                    st.success(f"Recovery succeeded: {recovery['action']} (attempt {recovery['attempt_number']})")
                elif recovery["status"] == "accepted":
                    st.warning(f"Attempt recorded but not recovered yet: {recovery['action']} (attempt {recovery['attempt_number']})")
                elif recovery["status"] == "already_recovered":
                    st.info(f"This transaction was already recovered on attempt {recovery['attempt_number']}.")
                else:
                    st.warning(f"Recovery blocked by policy: {recovery['validation']['checks']}")
                st.json(recovery)
                updated_detail = api_get(f"/transactions/{transaction_id}")
                updated_metrics = api_get("/metrics")
                st.subheader("Updated transaction state")
                st.write(
                    f"Status: `{updated_detail['transaction']['recovery_status']}` | "
                    f"Attempts: `{updated_detail['transaction']['total_recovery_attempts']}`"
                )
                st.write(
                    f"Recovered revenue: ₹{updated_metrics['revenue_recovered_paise'] / 100:,.0f} | "
                    f"Recovery rate: {updated_metrics['recovery_rate']:.2f}%"
                )
                st.caption("Go to Overview and click Refresh dashboard to update the KPI cards.")
            except Exception as exc:
                st.error(str(exc))
    except Exception as exc:
        st.error(str(exc))
