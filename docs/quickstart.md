# Quickstart Tutorial

Get started with OpenPāṭala in 5 minutes.

## Prerequisites

- Python 3.10+
- PostgreSQL running
- OpenPāṭala API running on port 8801

## Step 1: Start the API

```bash
cd /root/openpatalanew
PYTHONPATH=. python3 -m uvicorn patala.api:app --host 127.0.0.1 --port 8801
```

## Step 2: Check health

```bash
curl http://127.0.0.1:8801/health
```

Response:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "counts": {
    "works": 613,
    "assertions": 77,
    "external_identifiers": 38,
    "events": 613
  }
}
```

## Step 3: List works

```bash
curl http://127.0.0.1:8801/v1/works?limit=5
```

## Step 4: Get a work bundle

```bash
# Get the first work ID
WID=$(curl -s http://127.0.0.1:8801/v1/works?limit=1 | python3 -c "import sys,json; print(json.load(sys.stdin)['results'][0]['id'])")

# Get the full bundle
curl http://127.0.0.1:8801/v1/bundle/$WID
```

The bundle returns:
- The canonical work
- Alternative titles (from external IDs)
- Authorship uncertainty (from assertions)
- Editions, translations, witnesses, etexts
- Provenance (from events)
- Completeness (computed)

## Step 5: Search for works

```bash
curl "http://127.0.0.1:8801/v1/search?q=sanskrit&limit=5"
```

## Step 6: Resolve a work name

```bash
curl "http://127.0.0.1:8801/v1/resolve?q=Vigrahavyavartani"
```

Returns: `EXACT`, `AMBIGUOUS`, or `NONE`

## Step 7: Check frontier

```bash
curl "http://127.0.0.1:8801/v1/frontier/translations"
```

Returns works that need translations.

## Step 8: Run conformance test

```bash
cd /root/openpatalanew
PYTHONPATH=. python3 patala/conformance_test.py
```

All 12 steps should pass.

## Step 9: Make a hermes call

```bash
hermes -z "What is the Vigrahavyavartani by Nagarjuna?" -m mimo-v2.5 --provider opencode-go
```

The call is logged to `data/runs/hermes-calls.jsonl` with content-addressed records.

## What's next?

- Read the [API Overview](api/api-overview.md) for all endpoints
- Read the [Works](entities/works.md) entity docs
- Read the [Recipes](../recipes.md) for copy-paste how-tos
- Read the [Agentic Runbook](../agentic.md) for Hermes integration
