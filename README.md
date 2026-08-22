# ReviveAI

ReviveAI is a local, policy-bounded payment recovery demonstration using FastAPI, SQLite, and Streamlit.

## Run locally

From the repository root:

```powershell
python -c "from data.generator import generate_and_seed; print(generate_and_seed())"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
python -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8501
```

Open the dashboard at <http://127.0.0.1:8501> and API documentation at <http://127.0.0.1:8000/docs>.

## Demo flow

Open **Demo**, click **Reset Demo**, then click **Run Next Attempt** three times. The simulated gateway failure remains bounded at 3 attempts and transitions to `escalated`. The attempts and audit events are persisted in SQLite and can be inspected on **Audit Trail** by filtering for `txn_fail_demo`.

The demo bypasses real cooldown time only for presentation; it records each attempt and never bypasses the maximum retry policy.

## Tests

```powershell
python -m pytest -q
```
