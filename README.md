# NEXUS

Autonomous Multi-Agent Production Failure Investigation & Recovery System.

A controlled multi-agent incident-response research platform. See [CLAUDE.md](CLAUDE.md)
for the full build rules and [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) for current
status.

## Quickstart (Phase 1)

```bash
docker compose up -d
```

Backend health: http://localhost:8000/health
Simulated production health: http://localhost:8001/health

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/EVENT_SCHEMA.md](docs/EVENT_SCHEMA.md)
- [docs/API_CONTRACT.md](docs/API_CONTRACT.md)
- [docs/EVALUATION.md](docs/EVALUATION.md)
