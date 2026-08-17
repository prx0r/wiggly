# API Overview

The OpenPāṭala API is the primary way to get scholarly data programmatically. It's free and requires no authentication. The API is REST-based and returns JSON.

## Base URL

```
http://127.0.0.1:8801
```

## Endpoints

### Core entities
- `GET /v1/works` — List/search works
- `GET /v1/works/{id}` — Get a single work
- `GET /v1/people` — List people
- `GET /v1/institutions` — List institutions
- `GET /v1/editions` — List editions
- `GET /v1/witnesses` — List witnesses
- `GET /v1/etexts` — List e-texts
- `GET /v1/translations` — List translations
- `GET /v1/passages` — List passages

### Work subresources
- `GET /v1/works/{id}/assertions` — Get assertions about a work
- `GET /v1/works/{id}/editions` — Get editions of a work
- `GET /v1/works/{id}/translations` — Get translations of a work
- `GET /v1/works/{id}/completeness` — Get completeness status
- `GET /v1/bundle/{id}` — Get full dossier (the killer endpoint)

### Resolution and search
- `GET /v1/resolve?q=...` — Resolve a work name (EXACT/AMBIGUOUS/NONE)
- `GET /v1/search?q=...` — Search for works
- `GET /v1/autocomplete?q=...` — Fast autocomplete

### Frontier and changes
- `GET /v1/frontier/translations` — Works needing translations
- `GET /v1/changes?since=<cursor>` — Event feed

### Providers
- `GET /v1/providers` — List data providers
- `GET /v1/providers/{id}` — Get provider details

### Other
- `GET /v1/assertions?subject=...&predicate=...` — Filtered assertions
- `GET /v1/observations?entity=...` — Raw observations
- `GET /health` — System health

## Response format

All endpoints return a standard envelope:

```json
{
  "meta": {
    "count": 10,
    "schema_version": "1.0"
  },
  "results": [...]
}
```

For single entities:

```json
{
  "meta": {
    "schema_version": "1.0"
  },
  "data": { ... }
}
```

Errors:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Work xyz not found",
    "retryable": false
  }
}
```

## Example: Get a work bundle

```bash
curl http://127.0.0.1:8801/v1/bundle/PTW_00068039f45a7fe5
```

Response:

```json
{
  "meta": { "schema_version": "1.0" },
  "data": {
    "entity": { "id": "PTW_...", "preferred_title": "A Sanskrit-English Dictionary", ... },
    "aliases": [...],
    "external_ids": [...],
    "assertions": { "authorship": [...], "date": [...], "tradition": [...] },
    "editions": [...],
    "translations": [...],
    "witnesses": [...],
    "etexts": [...],
    "passages": [...],
    "provenance": [...],
    "completeness": { "identity": "RESOLVED", "translation": "NONE_KNOWN", ... }
  }
}
```

## Example: Resolve a work

```bash
curl "http://127.0.0.1:8801/v1/resolve?q=Vigrahavyavartani"
```

Response:

```json
{
  "meta": { "schema_version": "1.0" },
  "data": { "status": "EXACT", "entity": { "id": "PTW_...", "preferred_title": "Vigrahavyāvartanī" } }
}
```

## Example: Search for works

```bash
curl "http://127.0.0.1:8801/v1/search?q=sanskrit&limit=5"
```

## Client libraries

Currently no third-party client libraries. Use curl, Python requests, or any HTTP client.

## Rate limits

No rate limits currently. The API is local and designed for agent use.
