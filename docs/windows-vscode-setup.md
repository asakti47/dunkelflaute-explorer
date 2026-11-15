# Run on Windows with VS Code

## Prerequisites

- Install Python 3.11 or 3.12 for Windows, including pip and the Python launcher.
- Install Git for Windows and Visual Studio Code.
- In VS Code, install the **Python** extension published by Microsoft.
- Internet access is needed to install Python packages. The dashboard uses the
  data included in the repository; downloading NASA data again is optional.

## Open the project and create `.venv`

Clone the repository, or open your existing checkout with **File > Open Folder**
in VS Code. Open the folder containing `requirements.txt` and `streamlit_app.py`.
For a new checkout, run these commands in PowerShell:

```powershell
git clone https://github.com/asakti47/dunkelflaute-explorer.git
cd dunkelflaute-explorer
code .
```

In VS Code, choose **Terminal > New Terminal** and use a PowerShell terminal.
Run all commands below from the project root. Create a virtual environment
inside the project and install its dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Use `py -3.11` instead if you installed Python 3.11. If `py` is unavailable but
`python --version` reports Python 3.11 or 3.12, use `python -m venv .venv`.
If neither command works, install Python and reopen VS Code so its terminal picks
up the updated PATH. For a Python installation at a known path, PowerShell can
invoke it directly, for example:

```powershell
& 'C:\path\to\Python312\python.exe' -m venv .venv
```

Press **Ctrl+Shift+P**, choose **Python: Select Interpreter**, and select
`.venv\Scripts\python.exe`. If it is missing from the list, choose
**Enter interpreter path** and browse to that file. This makes VS Code use the
project environment for Python editing and execution.

The commands in this guide call the environment's interpreter explicitly, so
activation is optional. To activate it in PowerShell, run:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks `Activate.ps1`, continue with the explicit interpreter
commands below; changing the execution policy is unnecessary.

## Start and check the dashboard

```powershell
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

Open <http://127.0.0.1:8501> if a browser does not open automatically. Wait for
the initial data loading and calculations, then confirm the **Dunkelflaute
Explorer** heading, sidebar controls, and dashboard charts appear without an
exception. The first run reconstructs `data/power_*.csv.gz` from the included
base64 parts; keep those parts and `data/nao_monthly.csv` in place.

In a second PowerShell terminal, this checks that the server is responding:

```powershell
(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8501/_stcore/health).Content
```

It should return `ok`. This checks the server; the browser check also verifies
that the dashboard's data and calculations load. Stop the server with **Ctrl+C**
in its terminal. Repeat the start command whenever you reopen the project.

If port 8501 is already in use, change `--server.port 8501` to
`--server.port 8502` and use that port in the browser and health-check URL.
For `No module named streamlit`, rerun the dependency-install command using
`.\.venv\Scripts\python.exe` and check the selected VS Code interpreter.

## Optional commands

Run these from the project root using the same environment:

```powershell
# Run the existing test suite (pytest is a separate development dependency).
.\.venv\Scripts\python.exe -m pip install pytest
.\.venv\Scripts\python.exe -m pytest -q tests

# Write analysis tables to results/.
.\.venv\Scripts\python.exe scripts/run_analysis.py

# Re-download NASA POWER and NAO data (requires internet; may take a while).
.\.venv\Scripts\python.exe scripts/fetch_data.py
```

The repository ignores `.venv/`, Python caches, reconstructed compressed data,
and generated `results/` so local setup and analysis outputs stay out of commits.

## Startup verification

Verified on Windows on 2026-11-15 using Python 3.12.14 and Streamlit 1.67.0,
installed from `requirements.txt` into a fresh project-local `.venv`:

- The Streamlit server bound to `127.0.0.1:8501`, returned HTTP 200 for `/`, and
  returned `ok` for `/_stcore/health`.
- Streamlit's `AppTest` executed `streamlit_app.py` with the bundled data and
  default controls: no app exceptions, four metrics, and five Plotly charts.
- `python -m pip check` reported no broken requirements.

These checks verify server startup and application execution; the browser check
above remains the way to confirm the visual layout on your machine.
