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
                if recovery["status"] == "accepted":
                    st.success(f"Recovery accepted: {recovery['action']} (attempt {recovery['attempt_number']})")
                else:
                    st.warning(f"Recovery blocked by policy: {recovery['validation']['checks']}")
                st.json(recovery)
            except Exception as exc:
                st.error(str(exc))
    except Exception as exc:
        st.error(str(exc))
