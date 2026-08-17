# Works

Works are the core scholarly entities in OpenPāṭala. A Work represents a distinct intellectual creation — a text, treatise, or composition.

## Work object

```json
{
  "id": "PTW_00068039f45a7fe5",
  "preferred_title": "A Sanskrit-English Dictionary",
  "work_type": "TEXT",
  "current_title_assertion_id": null,
  "external_ids": [],
  "created_at": "2026-08-17T06:51:13+00:00",
  "schema_uri": "https://patala.org/schemas/atlas/work/1.0.0",
  "state_cursor": 3959
}
```

### Fields

| Field | Type | Description |
|---|---|---|
| `id` | string | UUIDv7 with prefix (PTW_) — opaque, never encodes title/source/SHA |
| `preferred_title` | string | The current best title (projection from TitleAssertions) |
| `work_type` | string | TEXT, COMMENTARY, TANTRA, SUTRA, etc. |
| `current_title_assertion_id` | string | Which assertion produced this title |
| `external_ids` | array | Cross-references to PANDiT, GRETIL, OpenAlex, etc. |
| `created_at` | datetime | When the entity was created |
| `schema_uri` | string | Which schema version was used |
| `state_cursor` | integer | Monotonic cursor for change tracking |

### Design principles

Per newbuildmainspec §11: "Keep Work deliberately small. Do not store directly: author, date, tradition, school. Those are scholarly assertions."

The Work entity is intentionally minimal. Authorship, dating, and tradition are stored as **assertions** — separate records that can be contested, superseded, or augmented without modifying the Work itself.

## Endpoints

- `GET /v1/works` — List works
- `GET /v1/works/{id}` — Get a single work
- `GET /v1/works/{id}/assertions` — Get assertions about a work
- `GET /v1/works/{id}/editions` — Get editions
- `GET /v1/works/{id}/translations` — Get translations
- `GET /v1/works/{id}/completeness` — Get completeness status
- `GET /v1/bundle/{id}` — Get full dossier

## Examples

```bash
# List works
curl http://127.0.0.1:8801/v1/works?limit=5

# Get a work
curl http://127.0.0.1:8801/v1/works/PTW_00068039f45a7fe5

# Get full bundle
curl http://127.0.0.1:8801/v1/bundle/PTW_00068039f45a7fe5

# Search
curl "http://127.0.0.1:8801/v1/search?q=sanskrit"

# Resolve
curl "http://127.0.0.1:8801/v1/resolve?q=Vigrahavyavartani"
```
