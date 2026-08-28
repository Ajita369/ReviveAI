# ReviveAI

ReviveAI is a local, policy-bounded payment recovery demonstration using FastAPI, SQLite, and Streamlit.

## Requirements

- Python 3.11 or newer
- Windows PowerShell, macOS Terminal, or Linux shell
- Two terminal windows for running the API and dashboard

## First-time setup

From the repository root:

```text
python --version
```

Create an isolated environment and install all dependencies. On Windows, use:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On macOS or Linux, use:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run this once in that terminal, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Run locally

From the repository root, with `.venv` activated, seed the database once:

```powershell
python -m data.generator
```

Keep the first terminal open and start the API:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Open a second terminal, change to the repository root, activate `.venv`, and start the dashboard:

```powershell
.\.venv\Scripts\Activate.ps1
python -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8501
```

Open the dashboard at <http://127.0.0.1:8501> and API documentation at <http://127.0.0.1:8000/docs>.

Check that the API is ready at <http://127.0.0.1:8000/health>; it should return `{"status":"ok"}`.

To use the commands on macOS or Linux, replace the Windows activation command with `source .venv/bin/activate`; the `python -m uvicorn` and `python -m streamlit` commands stay the same.

To reset the demo data, stop both running servers first, then run `python -m data.generator` again. Stopping the servers matters on Windows because SQLite cannot replace a database file while the API is using it.


## Tests

```powershell
python -m pytest -q
```
