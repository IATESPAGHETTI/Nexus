"""Test-session setup for the root test suite.

Forces the backend's incident store onto an in-memory SQLite database BEFORE
any test module imports `backend/app`, so running the tests can never read or
wipe a real `backend/.data/nexus.db`. (`incident_store.clear()` additionally
refuses to run against a file-backed database.)
"""

import os

os.environ["NEXUS_DB_PATH"] = ":memory:"
