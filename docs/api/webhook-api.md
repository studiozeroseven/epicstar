# Webhook API Documentation

## Overview

The epicstar receives webhooks from GitHub when repositories are starred.

## Endpoints

### POST /webhooks/github

Receives GitHub webhook events.

**Headers**:
- `X-GitHub-Event` (required): Event type (must be "watch")
- `X-GitHub-Delivery` (required): Unique delivery ID
- `X-Hub-Signature-256` (required): HMAC signature for verification
- `Content-Type`: application/json

**Request Body**:
```json
{
  "action": "started",
  "repository": {
    "id": 123456,
    "name": "example-repo",
    "full_name": "owner/example-repo",
    "owner": {
      "login": "owner",
      "type": "User"
    },
    "html_url": "https://github.com/owner/example-repo",
    "clone_url": "https://github.com/owner/example-repo.git",
    "default_branch": "main",
    "private": false,
    "size": 1024
  },
  "sender": {
    "login": "user"
  }
}
```

**Responses**:

**200 OK** - Success
```json
{
  "status": "success",
  "result": {
    "status": "success",
    "repository_id": 1,
    "onedev_url": "https://onedev.example.com/github-owner-example-repo",
    "duration_seconds": 45
  }
}
```

**200 OK** - Already synced
```json
{
  "status": "already_synced",
  "repository_id": 1,
  "onedev_url": "https://onedev.example.com/github-owner-example-repo"
}
```

**200 OK** - Ignored (non-watch event)
```json
{
  "status": "ignored",
  "reason": "not a watch event"
}
```

**200 OK** - Ignored (non-started action)
```json
{
  "status": "ignored",
  "reason": "action is deleted, not started"
}
```

**400 Bad Request** - Invalid payload
```json
{
  "error": "Invalid JSON payload"
}
```

**401 Unauthorized** - Invalid signature
```json
{
  "error": "Invalid signature"
}
```

**500 Internal Server Error** - Processing error
```json
{
  "error": "Internal server error"
}
```

## Signature Verification

GitHub signs all webhook payloads with HMAC-SHA256 using your webhook secret.

**Algorithm**:
```python
import hashlib
import hmac

signature = hmac.new(
    secret.encode('utf-8'),
    payload_bytes,
    hashlib.sha256
).hexdigest()

header_value = f"sha256={signature}"
```

**Verification**:
The service automatically verifies signatures. Invalid signatures are rejected with 401.

## Event Flow

1. **Receive Webhook**
   - Verify signature
   - Parse payload
   - Validate event type

2. **Store Event**
   - Save to `webhook_events` table
   - Record delivery ID and timestamp

3. **Check Duplicate**
   - Query `repositories` table
   - Return early if already synced

4. **Create Repository Record**
   - Insert into `repositories` table
   - Status: "pending"

5. **Create OneDev Repository**
   - Call OneDev API
   - Generate repository name
   - Update status: "cloning"

6. **Sync Git Repository**
   - Clone from GitHub
   - Push to OneDev
   - Update status: "completed"

7. **Log Result**
   - Insert into `sync_logs` table
   - Mark webhook as processed

## Error Handling

### Retry Logic

Failed syncs are retried with exponential backoff:
- Max retries: 3
- Backoff factor: 2
- Min wait: 4 seconds
- Max wait: 60 seconds

### Error States

- `pending`: Initial state
- `in_progress`: Currently syncing
- `cloning`: Git clone in progress
- `completed`: Successfully synced
- `failed`: Sync failed (check error_message)

## Rate Limiting

- Webhook endpoint: 100 requests/minute
- API endpoints: 60 requests/minute

## Testing

### Using curl

```bash
# Generate signature
SECRET="your_webhook_secret"
PAYLOAD='{"action":"started","repository":{"name":"test"}}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | sed 's/^.* //')

# Send webhook
curl -X POST http://localhost:8000/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: watch" \
  -H "X-GitHub-Delivery: test-$(date +%s)" \
  -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
  -d "$PAYLOAD"
```

### Using GitHub

1. Go to your GitHub App settings
2. Navigate to "Advanced" → "Recent Deliveries"
3. Click "Redeliver" on any watch event

## Monitoring

### Webhook Events Table

Query recent webhooks:
```sql
SELECT event_id, event_type, processed, received_at
FROM webhook_events
ORDER BY received_at DESC
LIMIT 10;
```

### Sync Logs Table

Query sync history:
```sql
SELECT r.github_full_name, sl.status, sl.duration_seconds, sl.created_at
FROM sync_logs sl
JOIN repositories r ON sl.repository_id = r.id
ORDER BY sl.created_at DESC
LIMIT 10;
```

## Best Practices

1. **Idempotency**: Webhooks may be delivered multiple times. The service handles duplicates gracefully.

2. **Timeouts**: GitHub expects a response within 10 seconds. Long operations are processed asynchronously.

3. **Logging**: All webhook events are logged for debugging and replay.

4. **Security**: Always verify signatures. Never disable signature verification in production.

5. **Monitoring**: Set up alerts for failed syncs and webhook errors.

