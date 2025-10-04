# Use Case: Basic Repository Synchronization

## Overview

**Title**: Live AI Mentor for Soldering Practice (Initial Use Case)

**Objective**: Automatically synchronize starred GitHub repositories to a private OneDev instance for offline access, backup, and integration with internal development workflows.

## User Story

**As a** developer with a private OneDev instance  
**I want** my starred GitHub repositories to be automatically cloned to OneDev  
**So that** I can have a private backup and integrate them with my internal workflows

## Actors

- **Primary Actor**: Developer (repository owner)
- **Secondary Actors**: 
  - GitHub (source repository host)
  - OneDev (destination repository host)
  - Middleware Service (automation service)

## Preconditions

1. GitHub App is configured and installed on user's account
2. Middleware service is running and accessible
3. OneDev instance is accessible and has API access enabled
4. User has permissions to create repositories in OneDev
5. Webhook endpoint is configured in GitHub App

## Basic Flow

### Step 1: User Stars a Repository

**Actor**: Developer

**Action**: User navigates to a GitHub repository and clicks the "Star" button

**Example**: User stars `https://github.com/fastapi/fastapi`

**System Response**: GitHub records the star event

---

### Step 2: GitHub Sends Webhook

**Actor**: GitHub

**Action**: GitHub sends a webhook POST request to the configured endpoint

**Webhook Payload Example**:
```json
{
  "action": "started",
  "starred_at": "2025-10-04T10:30:00Z",
  "repository": {
    "id": 123456789,
    "name": "fastapi",
    "full_name": "fastapi/fastapi",
    "owner": {
      "login": "fastapi",
      "type": "Organization"
    },
    "html_url": "https://github.com/fastapi/fastapi",
    "clone_url": "https://github.com/fastapi/fastapi.git",
    "default_branch": "master",
    "private": false,
    "size": 12345
  },
  "sender": {
    "login": "your-username"
  }
}
```

**Headers**:
```
X-GitHub-Event: watch
X-GitHub-Delivery: 12345678-1234-1234-1234-123456789abc
X-Hub-Signature-256: sha256=abc123...
Content-Type: application/json
```

---

### Step 3: Middleware Receives and Validates Webhook

**Actor**: Middleware Service

**Actions**:
1. Receive POST request at `/webhooks/github`
2. Extract signature from `X-Hub-Signature-256` header
3. Verify signature using webhook secret
4. Validate payload structure
5. Extract repository information

**Validation Checks**:
- ✅ Signature matches expected HMAC-SHA256
- ✅ Event type is "watch"
- ✅ Action is "started" (not "deleted")
- ✅ Repository URL is valid
- ✅ Payload contains required fields

**Success Response**: `200 OK`

**Failure Responses**:
- `401 Unauthorized` - Invalid signature
- `400 Bad Request` - Invalid payload
- `500 Internal Server Error` - Processing error

---

### Step 4: Check Database for Existing Sync

**Actor**: Middleware Service

**Action**: Query database to check if repository is already synchronized

**Query**:
```sql
SELECT id, sync_status, last_synced_at
FROM repositories
WHERE github_url = 'https://github.com/fastapi/fastapi';
```

**Scenarios**:

**A. Repository Not Found** (New Sync):
- Proceed to Step 5

**B. Repository Found - Status: Completed**:
- Log: "Repository already synchronized"
- Update `last_synced_at` timestamp
- Return `200 OK` (idempotent)
- **End workflow**

**C. Repository Found - Status: In Progress**:
- Log: "Sync already in progress"
- Return `200 OK` (idempotent)
- **End workflow**

**D. Repository Found - Status: Failed**:
- Log: "Retrying failed sync"
- Proceed to Step 5

---

### Step 5: Create Database Record

**Actor**: Middleware Service

**Action**: Create or update repository record in database

**SQL**:
```sql
INSERT INTO repositories (
    github_url,
    github_repo_name,
    github_owner,
    github_full_name,
    github_repo_id,
    github_default_branch,
    github_is_private,
    sync_status,
    created_at,
    updated_at
) VALUES (
    'https://github.com/fastapi/fastapi',
    'fastapi',
    'fastapi',
    'fastapi/fastapi',
    123456789,
    'master',
    false,
    'pending',
    NOW(),
    NOW()
)
ON CONFLICT (github_url) DO UPDATE
SET sync_status = 'pending',
    retry_count = repositories.retry_count + 1,
    updated_at = NOW();
```

**Log Entry**:
```json
{
  "timestamp": "2025-10-04T10:30:01Z",
  "level": "INFO",
  "event": "sync_initiated",
  "github_repo": "fastapi/fastapi",
  "repository_id": 1
}
```

---

### Step 6: Create Repository in OneDev

**Actor**: Middleware Service → OneDev API Client

**Action**: Create a new repository in OneDev

**API Call**:
```http
POST /api/projects
Content-Type: application/json
Authorization: Bearer <onedev_api_token>

{
  "name": "fastapi-fastapi",
  "description": "Synced from GitHub: fastapi/fastapi",
  "codeManagement": true,
  "issueManagement": false
}
```

**Naming Strategy**:
- Format: `{owner}-{repo}` (e.g., `fastapi-fastapi`)
- Alternative: `github-{owner}-{repo}`
- Configurable via environment variable

**Conflict Handling**:

**If repository already exists**:
- Option A: Use existing repository (default)
- Option B: Append timestamp: `fastapi-fastapi-20251004`
- Option C: Return error and mark sync as failed

**Success Response**:
```json
{
  "id": 42,
  "name": "fastapi-fastapi",
  "url": "https://onedev.example.com/projects/fastapi-fastapi"
}
```

**Update Database**:
```sql
UPDATE repositories
SET onedev_url = 'https://onedev.example.com/projects/fastapi-fastapi',
    onedev_repo_name = 'fastapi-fastapi',
    onedev_project_id = 42,
    sync_status = 'in_progress',
    updated_at = NOW()
WHERE id = 1;
```

---

### Step 7: Clone Repository from GitHub

**Actor**: Git Operations Module

**Action**: Clone the repository from GitHub to a temporary directory

**Command**:
```bash
git clone --mirror https://github.com/fastapi/fastapi.git /tmp/sync-{uuid}/fastapi.git
```

**Options**:
- `--mirror`: Clone all branches, tags, and refs
- `--depth 1`: Shallow clone (optional, for large repos)
- `--single-branch`: Clone only default branch (optional)

**Authentication**:
- Public repos: No authentication needed
- Private repos: Use GitHub App token or personal access token

**Progress Tracking**:
```python
# Pseudo-code
def clone_with_progress(url, path):
    process = subprocess.Popen(
        ['git', 'clone', '--progress', url, path],
        stderr=subprocess.PIPE
    )
    for line in process.stderr:
        # Parse progress: "Receiving objects: 50% (1234/2468)"
        log_progress(line)
```

**Timeout**: 30 minutes (configurable)

**Error Handling**:
- Network timeout → Retry with exponential backoff
- Authentication failure → Mark as permanent failure
- Disk space full → Alert and mark as failed

---

### Step 8: Push Repository to OneDev

**Actor**: Git Operations Module

**Action**: Push the cloned repository to OneDev

**Commands**:
```bash
cd /tmp/sync-{uuid}/fastapi.git
git remote add onedev https://onedev.example.com/git/fastapi-fastapi.git
git push --mirror onedev
```

**Authentication**:
- HTTPS: Use OneDev API token
- SSH: Use SSH key (requires key setup)

**Progress Tracking**: Similar to clone operation

**Timeout**: 30 minutes (configurable)

**Error Handling**:
- Network timeout → Retry
- Authentication failure → Mark as permanent failure
- Remote rejected → Check OneDev permissions

---

### Step 9: Update Database and Clean Up

**Actor**: Middleware Service

**Actions**:
1. Update repository status to "completed"
2. Record sync completion time
3. Log success
4. Clean up temporary directory

**SQL**:
```sql
UPDATE repositories
SET sync_status = 'completed',
    last_synced_at = NOW(),
    error_message = NULL,
    retry_count = 0,
    updated_at = NOW()
WHERE id = 1;

INSERT INTO sync_logs (
    repository_id,
    event_type,
    status,
    duration_seconds,
    created_at
) VALUES (
    1,
    'sync_completed',
    'success',
    45.2,
    NOW()
);
```

**Cleanup**:
```bash
rm -rf /tmp/sync-{uuid}
```

**Log Entry**:
```json
{
  "timestamp": "2025-10-04T10:30:46Z",
  "level": "INFO",
  "event": "sync_completed",
  "github_repo": "fastapi/fastapi",
  "onedev_repo": "fastapi-fastapi",
  "duration_seconds": 45.2,
  "repository_id": 1
}
```

---

### Step 10: Notification (Optional)

**Actor**: Notification Service

**Action**: Send notification to user (optional feature)

**Channels**:
- Email
- Slack
- Discord
- Webhook to custom endpoint

**Message Example**:
```
✅ Repository Synced Successfully

GitHub: fastapi/fastapi
OneDev: https://onedev.example.com/projects/fastapi-fastapi
Duration: 45 seconds
Synced at: 2025-10-04 10:30:46 UTC
```

---

## Postconditions

### Success Scenario

1. ✅ Repository is cloned to OneDev
2. ✅ Database record shows status "completed"
3. ✅ Sync log entry created
4. ✅ Temporary files cleaned up
5. ✅ User can access repository in OneDev

### Failure Scenario

1. ❌ Database record shows status "failed"
2. ❌ Error message recorded in database
3. ❌ Sync log entry created with error details
4. ❌ Temporary files cleaned up
5. ❌ Retry scheduled (if retry count < max retries)

---

## Alternative Flows

### Alternative Flow 1: Repository Already Exists in OneDev

**Trigger**: OneDev API returns "repository already exists" error

**Actions**:
1. Check configuration for conflict resolution strategy
2. If strategy is "use_existing":
   - Use existing repository
   - Update remote URL
   - Proceed with push
3. If strategy is "append_timestamp":
   - Create new repository with timestamp suffix
   - Proceed with push
4. If strategy is "fail":
   - Mark sync as failed
   - Log error
   - End workflow

---

### Alternative Flow 2: Large Repository (>1GB)

**Trigger**: Repository size exceeds threshold

**Actions**:
1. Log warning about large repository
2. Use shallow clone (`--depth 1`)
3. Increase timeout to 60 minutes
4. Monitor disk space during clone
5. If disk space low, abort and mark as failed

---

### Alternative Flow 3: Private Repository

**Trigger**: Repository is private

**Actions**:
1. Check if GitHub App has access to private repos
2. Use GitHub App token for authentication
3. Proceed with clone using authenticated URL:
   ```
   https://x-access-token:{token}@github.com/owner/repo.git
   ```
4. Ensure OneDev repository is also private

---

## Exception Flows

### Exception 1: Invalid Webhook Signature

**Trigger**: Signature verification fails

**Actions**:
1. Log security warning
2. Return `401 Unauthorized`
3. Do not process webhook
4. Alert administrator (potential security issue)

---

### Exception 2: GitHub API Rate Limit Exceeded

**Trigger**: GitHub API returns 429 Too Many Requests

**Actions**:
1. Extract `X-RateLimit-Reset` header
2. Calculate wait time
3. Schedule retry after rate limit reset
4. Log rate limit event
5. Return `200 OK` to GitHub (acknowledge webhook)

---

### Exception 3: OneDev API Unavailable

**Trigger**: OneDev API returns 500 or connection timeout

**Actions**:
1. Mark sync as "failed"
2. Schedule retry with exponential backoff
3. Log error with full details
4. Return `200 OK` to GitHub (acknowledge webhook)
5. Alert administrator if multiple failures

---

## Performance Metrics

### Target Metrics

- **Webhook Processing Time**: <500ms (p95)
- **Small Repo Sync (<100MB)**: <2 minutes
- **Medium Repo Sync (100MB-1GB)**: <10 minutes
- **Large Repo Sync (>1GB)**: <30 minutes
- **Success Rate**: >95%

### Monitoring

Track the following metrics:
- Webhook delivery latency
- Clone duration
- Push duration
- Total sync duration
- Success/failure rate
- Retry rate

---

## Security Considerations

1. **Webhook Signature**: Always verify before processing
2. **API Tokens**: Never log or expose in error messages
3. **Temporary Files**: Clean up immediately after sync
4. **Private Repos**: Ensure OneDev repo has same privacy level
5. **Rate Limiting**: Respect GitHub API rate limits

---

## Future Enhancements

1. **Incremental Updates**: Detect changes and only sync diffs
2. **Selective Sync**: Filter by language, stars, or topics
3. **Bi-directional Sync**: Push changes from OneDev back to GitHub
4. **Conflict Resolution**: Handle diverged repositories
5. **Batch Sync**: Sync all starred repos at once

---

**Last Updated**: 2025-10-04  
**Version**: 1.0

