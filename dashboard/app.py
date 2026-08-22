from __future__ import annotations

import os
import requests
import streamlit as st


API_URL = os.getenv("REVIVEAI_API_URL", "http://127.0.0.1:8000")


def api_get(path: str, params: dict | None = None) -> dict:
    response = requests.get(f"{API_URL}{path}", params=params, timeout=5)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict | None = None) -> dict:
    response = requests.post(f"{API_URL}{path}", json=payload, timeout=5)
    response.raise_for_status()
    return response.json()


def main() -> None:
    st.set_page_config(page_title="ReviveAI Operations Console", layout="wide")
    st.title("ReviveAI Operations Console")
    if st.button("Refresh dashboard"):
        st.rerun()
    try:
        metrics = api_get("/metrics")
    except requests.RequestException as exc:
        st.error(f"API unavailable: {exc}")
        st.code("uvicorn backend.main:app --reload")
        return
    first, second, third = st.columns(3)
    first.metric("Revenue at risk", f"₹{metrics['revenue_at_risk_paise'] / 100:,.0f}")
    second.metric("Recovered", f"₹{metrics['revenue_recovered_paise'] / 100:,.0f}")
    third.metric("Recovery rate", f"{metrics['recovery_rate']:.1f}%")
    st.subheader("Recovery queue")
    queue = api_get("/transactions", {"status": "failed", "limit": 25})
    st.dataframe(queue["items"], use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
