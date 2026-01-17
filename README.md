# BookBazaar — Starter Auth UI

This is a minimal starter for the BookBazaar capstone: a Flask app with a sliding sign-in / sign-up UI.

Quick start

1. Create a Python environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install flask
```

2. Run the app:

```powershell
set FLASK_APP=app.py
python app.py
```

3. Open http://127.0.0.1:5000/ in your browser.

Notes

- User accounts are stored in an in-memory Python dictionary for this starter (no persistence across restarts).
- For production, replace with a proper database (DynamoDB / RDS) and a secure secret.
