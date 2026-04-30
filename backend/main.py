"""
Compatibility entrypoint.

Use the new deterministic compliance pipeline app from `app.py`.
This keeps `uvicorn main:app` working while serving the same new API.
"""

from app import app
