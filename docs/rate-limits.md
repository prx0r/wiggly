# Rate Limits and Authentication

## Authentication

The OpenPāṭala API is free and requires no authentication. It's designed for local agent use.

## Rate Limits

Currently no rate limits. The API runs locally and is designed for:
- Agent-driven ingestion
- Developer testing
- Hermes integration

## Production considerations

For production deployment, consider:
- Adding API key authentication
- Rate limiting per client
- Request logging
- CORS configuration

## Polite pool (future)

If deployed publicly, add your email to requests for better performance:

```bash
curl "http://your-domain/v1/works?mailto=your@email.com"
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://patala:patala@127.0.0.1:5432/openpatala` | PostgreSQL connection |
| `PORT` | `8801` | API port |
| `HOST` | `127.0.0.1` | API host |
