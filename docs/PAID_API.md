# OpenJobsEU Paid API

**Prefix:** `/api/v1`

Provides access to compliance-enriched EU remote job data and labour market analytics. All endpoints require an API key issued by the OpenJobsEU administrator.

For the canonical data model (field definitions, enum values, lifecycle semantics) see `CANONICAL_MODEL.md`.

---

## Authentication

All requests must include an API key in the `Authorization` header:

```
Authorization: Bearer ojeu_<key>
```

Key format: `ojeu_` prefix followed by 32 URL-safe characters (total 37 characters). Keys are issued and managed by the administrator.

**401 Unauthorized** — returned when the header is absent, malformed, the key is unknown, or the key has been revoked:

```json
{ "detail": "Invalid or missing API key" }
```

---

## Rate Limiting

Quotas are enforced per calendar day (UTC). The counter resets automatically at the first request after UTC midnight.

| Tier         | Requests / day |
|--------------|---------------|
| `free`       | 500           |
| `pro`        | 10,000        |
| `enterprise` | Unlimited     |

**429 Too Many Requests** — returned when the daily quota is exceeded:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 86400
Content-Type: application/json

{ "detail": "Daily quota exceeded" }
```

`Retry-After: 86400` signals that the quota resets within 24 hours. Each HTTP request counts as 1 against the quota regardless of how many results are returned.

---

## Endpoints

### `GET /api/v1/jobs`

Returns a paginated list of job offers with the full set of canonical fields. Exposes all fields including taxonomy, compliance scores, and EUR-normalized salary — a superset of the public `feed.json`.

Visible jobs are those with `status = new` or `status = active` (see `JOB_LIFECYCLE.md`). There is no compliance score filter applied; all compliant and non-compliant records are accessible.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | — | `new`, `active`, or `expired` |
| `q` | string | — | Full-text search across `title` and `description` |
| `company` | string | — | Case-insensitive substring match on `company_name` |
| `title` | string | — | Case-insensitive substring match on `title` |
| `source` | string | — | Exact match on source identifier (e.g. `greenhouse:token`) |
| `remote_scope` | string | — | Substring match on `remote_scope` (source-provided text) |
| `remote_class` | string | — | Exact match: `remote_only`, `remote_region_locked`, `remote_optional`, `non_remote`, `unknown` |
| `geo_class` | string | — | Exact match: `eu_member_state`, `eu_explicit`, `eu_region`, `uk`, `non_eu`, `unknown` |
| `compliance_status` | string | — | Exact match: `approved`, `review`, `rejected` |
| `min_compliance_score` | int (0–100) | — | Minimum compliance score (inclusive) |
| `max_compliance_score` | int (0–100) | — | Maximum compliance score (inclusive) |
| `job_family` | string | — | Exact match on taxonomy `job_family` |
| `seniority` | string | — | Exact match on taxonomy `seniority` |
| `specialization` | string | — | Exact match on taxonomy `specialization` |
| `first_seen_after` | date (YYYY-MM-DD) | — | `first_seen_at >= date` |
| `first_seen_before` | date (YYYY-MM-DD) | — | `first_seen_at <= date` |
| `limit` | int (1–100) | `20` | Results per page |
| `offset` | int (0–50,000) | `0` | Pagination offset |

#### Response

```json
{
  "items": [
    {
      "job_id": "a1b2c3d4-e5f6-...",
      "source": "greenhouse:acme",
      "source_url": "https://boards.greenhouse.io/acme/jobs/12345",
      "title": "Senior Backend Engineer",
      "company_name": "Acme Corp",
      "remote_scope": "Europe",
      "status": "active",
      "remote_class": "remote_only",
      "geo_class": "eu_member_state",
      "compliance_status": "approved",
      "compliance_score": 87,
      "quality_score": 74,
      "description": "We are looking for...",
      "source_department": "Engineering",
      "job_family": "software_development",
      "job_role": "engineer",
      "seniority": "senior",
      "specialization": "backend",
      "salary_min": 80000,
      "salary_max": 120000,
      "salary_currency": "USD",
      "salary_period": "year",
      "salary_min_eur": 74000,
      "salary_max_eur": 111000,
      "first_seen_at": "2026-03-15T09:00:00Z",
      "last_seen_at": "2026-04-14T06:30:00Z"
    }
  ],
  "total": 1842,
  "limit": 20,
  "offset": 0
}
```

`total` reflects the count of all matching records without `limit`/`offset`. Use it to calculate page count: `ceil(total / limit)`. Maximum addressable `offset` is 50,000; for bulk exports beyond this limit contact the administrator.

Nullable fields (`remote_class`, `geo_class`, `compliance_status`, `compliance_score`, `quality_score`, `description`, `source_department`, all taxonomy fields, all salary fields, `last_seen_at`) are `null` when not yet enriched. Newly indexed jobs may lack some fields for up to 24 hours.

Enum values for `remote_class`, `geo_class`, `compliance_status`, taxonomy fields, and salary fields are defined in `CANONICAL_MODEL.md`.

#### Example

```bash
# Senior software development roles approved for EU, first seen in 2026
curl "https://api.openjobs.eu/api/v1/jobs?job_family=software_development&seniority=senior&compliance_status=approved&first_seen_after=2026-01-01&limit=50" \
     -H "Authorization: Bearer ojeu_your_key_here"
```

---

### `GET /api/v1/analytics/market`

Returns daily market statistics as a time series. Data is computed once per day by the market metrics worker and reflects the state of the `jobs` table at computation time.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | int (1–365) | `30` | Number of past calendar days to return |

#### Response

```json
{
  "days": 30,
  "count": 30,
  "data": [
    {
      "date": "2026-04-14",
      "jobs_active": 1842,
      "jobs_new": 47,
      "jobs_expired": 12,
      "compliance_rate": 0.73,
      "avg_salary_eur": 94500,
      "median_salary_eur": 88000
    }
  ]
}
```

`count` reflects the number of data points returned (may be less than `days` if history is shorter). Data is ordered chronologically, oldest first. `compliance_rate` is the share of active jobs with `compliance_status = approved` (0.0–1.0). Salary fields are `null` when no salary data was available on that date.

#### Example

```bash
curl "https://api.openjobs.eu/api/v1/analytics/market?days=90" \
     -H "Authorization: Bearer ojeu_your_key_here"
```

---

### `GET /api/v1/analytics/segments`

Returns the most recent market snapshot broken down by segment dimensions. Segments are computed by the market metrics worker alongside daily stats and represent a point-in-time breakdown, not a rolling aggregate.

Segment dimensions: `job_family`, `seniority`, `geo_class`.

#### Response

```json
{
  "count": 24,
  "data": [
    {
      "segment_type": "job_family",
      "value": "software_development",
      "jobs_active": 1102,
      "jobs_created": 38,
      "avg_salary_eur": 98000,
      "median_salary_eur": 92000
    },
    {
      "segment_type": "seniority",
      "value": "senior",
      "jobs_active": 743,
      "jobs_created": 21,
      "avg_salary_eur": 110000,
      "median_salary_eur": 104000
    }
  ]
}
```

Results are grouped by `segment_type`, then ordered by `jobs_active` descending within each group. Salary fields are `null` when no salary data exists for that segment.

#### Example

```bash
curl "https://api.openjobs.eu/api/v1/analytics/segments" \
     -H "Authorization: Bearer ojeu_your_key_here"
```

---

## Error Reference

| Status | Condition |
|--------|-----------|
| `400 Bad Request` | Invalid query parameter type or value out of allowed range |
| `401 Unauthorized` | Missing or invalid API key |
| `429 Too Many Requests` | Daily quota exceeded |
| `500 Internal Server Error` | Unexpected server error |

All error responses use the FastAPI default shape:

```json
{ "detail": "Human-readable message" }
```

---

## Quick Start

```bash
export OJEU_KEY="ojeu_your_key_here"

# Paginated job listing
curl "https://api.openjobs.eu/api/v1/jobs?limit=100&offset=0" \
     -H "Authorization: Bearer $OJEU_KEY"

# Approved fully-remote EU jobs
curl "https://api.openjobs.eu/api/v1/jobs?compliance_status=approved&remote_class=remote_only&geo_class=eu_member_state" \
     -H "Authorization: Bearer $OJEU_KEY"

# Last 7 days of market data
curl "https://api.openjobs.eu/api/v1/analytics/market?days=7" \
     -H "Authorization: Bearer $OJEU_KEY"

# Current segment breakdown
curl "https://api.openjobs.eu/api/v1/analytics/segments" \
     -H "Authorization: Bearer $OJEU_KEY"
```

---

## Notes

- All timestamps are UTC (ISO 8601, `Z` suffix).
- The daily quota counter resets at UTC midnight on the first request of each new day.
- The public `feed.json` (GCS/CDN) is a subset of this API: it returns jobs with `compliance_score >= 80` and a reduced field set. The `/api/v1/jobs` endpoint has no compliance score filter and includes all canonical fields.
- Market analytics data (`/market`, `/segments`) is updated once per day; intraday changes are not reflected until the next metrics run.
