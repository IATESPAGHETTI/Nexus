"""Bounded configuration for the NEXUS MCP diagnostic layer.

No secrets live here. These tools never touch GROQ_API_KEY or any credential —
they only read from the simulated production HTTP API and, for get_git_diff,
the NEXUS repo's own git history under an explicit path allowlist.
"""

import os
from pathlib import Path

# Simulated production service (Phase 2). Overridable for docker-compose networking
# (service name "production") vs. local dev (localhost).
PRODUCTION_BASE_URL = os.environ.get("PRODUCTION_BASE_URL", "http://127.0.0.1:8001")  # 127.0.0.1 not "localhost": on Windows "localhost" costs ~2 s per request (IPv6 tried first)

# All outbound HTTP calls to the production simulation are bounded.
HTTP_TIMEOUT_SECONDS = 5.0

REPO_ROOT = Path(__file__).resolve().parents[1]

# get_git_diff may only inspect these top-level paths of the NEXUS repo itself —
# never arbitrary paths, never outside the repo, never dotfiles/secrets.
GIT_DIFF_ALLOWED_PATHS = ("production", "backend", "mcp", "docs")
GIT_DIFF_MAX_COMMITS = 5
GIT_DIFF_MAX_OUTPUT_CHARS = 4000
GIT_TIMEOUT_SECONDS = 5.0

# run_diagnostic only accepts these named, pre-approved diagnostics — never
# arbitrary code/SQL/shell input from a caller.
DIAGNOSTIC_NAMES = ("connectivity_check", "error_rate_check", "order_status_check")
