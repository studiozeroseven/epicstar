# Database Schema

## Overview

The database schema is designed to track repository synchronization state, provide audit trails, and support operational queries.

## Entity Relationship Diagram

```mermaid
erDiagram
    REPOSITORIES ||--o{ SYNC_LOGS : has
    REPOSITORIES {
        int id PK
        string github_url UK
        string github_repo_name
        string github_owner
        string github_full_name
        string onedev_url
        string onedev_repo_name
        string sync_status
        text error_message
        timestamp created_at
        timestamp updated_at
        timestamp last_synced_at
        int retry_count
        json metadata
    }
    
    SYNC_LOGS {
        int id PK
        int repository_id FK
        string event_type
        string status
        text error_message
        json payload
        timestamp created_at
        float duration_seconds
    }
    
    WEBHOOK_EVENTS {
        int id PK
        string event_id UK
        string event_type
        string delivery_id
        json payload
        string signature
        boolean processed
        timestamp received_at
        timestamp processed_at
    }
```

## Table Definitions

### 1. repositories

Stores information about synchronized repositories.

```sql
CREATE TABLE repositories (
    id SERIAL PRIMARY KEY,
    
    -- GitHub information
    github_url VARCHAR(500) NOT NULL UNIQUE,
    github_repo_name VARCHAR(255) NOT NULL,
    github_owner VARCHAR(255) NOT NULL,
    github_full_name VARCHAR(255) NOT NULL,  -- owner/repo
    github_repo_id BIGINT,  -- GitHub's internal ID
    github_default_branch VARCHAR(100),
    github_is_private BOOLEAN DEFAULT FALSE,
    github_size_kb INTEGER,
    
    -- OneDev information
    onedev_url VARCHAR(500),
    onedev_repo_name VARCHAR(255),
    onedev_project_id INTEGER,
    
    -- Sync status
    sync_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    -- Values: pending, in_progress, completed, failed, permanent_failure
    
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_synced_at TIMESTAMP,
    next_retry_at TIMESTAMP,
    
    -- Additional metadata (JSON for flexibility)
    metadata JSONB,
    
    -- Constraints
    CONSTRAINT valid_sync_status CHECK (
        sync_status IN ('pending', 'in_progress', 'completed', 'failed', 'permanent_failure')
    )
);

-- Indexes for common queries
CREATE INDEX idx_repositories_sync_status ON repositories(sync_status);
CREATE INDEX idx_repositories_github_url ON repositories(github_url);
CREATE INDEX idx_repositories_github_owner ON repositories(github_owner);
CREATE INDEX idx_repositories_updated_at ON repositories(updated_at DESC);
CREATE INDEX idx_repositories_next_retry ON repositories(next_retry_at) 
    WHERE sync_status = 'failed' AND next_retry_at IS NOT NULL;

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_repositories_updated_at
    BEFORE UPDATE ON repositories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### 2. sync_logs

Audit trail for all synchronization operations.

```sql
CREATE TABLE sync_logs (
    id SERIAL PRIMARY KEY,
    repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    
    -- Event information
    event_type VARCHAR(50) NOT NULL,
    -- Values: sync_started, sync_completed, sync_failed, retry_attempted, etc.
    
    status VARCHAR(50) NOT NULL,
    -- Values: success, failure, in_progress
    
    error_message TEXT,
    error_code VARCHAR(50),
    
    -- Performance metrics
    duration_seconds FLOAT,
    bytes_transferred BIGINT,
    
    -- Additional context
    payload JSONB,
    
    -- Timestamp
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_event_type CHECK (
        event_type IN (
            'sync_started', 'sync_completed', 'sync_failed', 
            'retry_attempted', 'clone_started', 'clone_completed',
            'push_started', 'push_completed', 'onedev_repo_created'
        )
    ),
    CONSTRAINT valid_status CHECK (
        status IN ('success', 'failure', 'in_progress')
    )
);

-- Indexes
CREATE INDEX idx_sync_logs_repository_id ON sync_logs(repository_id);
CREATE INDEX idx_sync_logs_created_at ON sync_logs(created_at DESC);
CREATE INDEX idx_sync_logs_event_type ON sync_logs(event_type);
CREATE INDEX idx_sync_logs_status ON sync_logs(status);
```

### 3. webhook_events

Stores raw webhook events for debugging and replay.

```sql
CREATE TABLE webhook_events (
    id SERIAL PRIMARY KEY,
    
    -- GitHub webhook information
    event_id VARCHAR(100) UNIQUE,  -- GitHub's X-GitHub-Delivery header
    event_type VARCHAR(50) NOT NULL,  -- watch, push, etc.
    delivery_id VARCHAR(100),
    
    -- Payload
    payload JSONB NOT NULL,
    signature VARCHAR(100) NOT NULL,
    
    -- Processing status
    processed BOOLEAN DEFAULT FALSE,
    processing_error TEXT,
    
    -- Timestamps
    received_at TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP,
    
    -- Link to repository (if processed)
    repository_id INTEGER REFERENCES repositories(id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX idx_webhook_events_event_id ON webhook_events(event_id);
CREATE INDEX idx_webhook_events_processed ON webhook_events(processed);
CREATE INDEX idx_webhook_events_received_at ON webhook_events(received_at DESC);
CREATE INDEX idx_webhook_events_event_type ON webhook_events(event_type);
```

## Sample Queries

### Get all pending synchronizations

```sql
SELECT 
    id,
    github_full_name,
    sync_status,
    retry_count,
    created_at,
    error_message
FROM repositories
WHERE sync_status = 'pending'
ORDER BY created_at ASC;
```

### Get failed syncs ready for retry

```sql
SELECT 
    id,
    github_full_name,
    retry_count,
    next_retry_at,
    error_message
FROM repositories
WHERE sync_status = 'failed'
    AND retry_count < max_retries
    AND next_retry_at <= NOW()
ORDER BY next_retry_at ASC;
```

### Get sync statistics

```sql
SELECT 
    sync_status,
    COUNT(*) as count,
    AVG(retry_count) as avg_retries
FROM repositories
GROUP BY sync_status;
```

### Get recent sync activity

```sql
SELECT 
    r.github_full_name,
    sl.event_type,
    sl.status,
    sl.duration_seconds,
    sl.created_at
FROM sync_logs sl
JOIN repositories r ON sl.repository_id = r.id
ORDER BY sl.created_at DESC
LIMIT 50;
```

### Get unprocessed webhooks

```sql
SELECT 
    id,
    event_type,
    received_at,
    payload->>'repository'->>'full_name' as repo_name
FROM webhook_events
WHERE processed = FALSE
ORDER BY received_at ASC;
```

## Data Retention Policy

### Retention Periods

| Table | Retention | Cleanup Strategy |
|-------|-----------|------------------|
| `repositories` | Indefinite | Manual cleanup or archive |
| `sync_logs` | 90 days | Automated cleanup job |
| `webhook_events` | 30 days | Automated cleanup job |

### Cleanup Queries

```sql
-- Clean up old sync logs (older than 90 days)
DELETE FROM sync_logs
WHERE created_at < NOW() - INTERVAL '90 days';

-- Clean up old webhook events (older than 30 days)
DELETE FROM webhook_events
WHERE received_at < NOW() - INTERVAL '30 days'
    AND processed = TRUE;

-- Archive completed repositories (optional)
-- Move to archive table or export to file
INSERT INTO repositories_archive
SELECT * FROM repositories
WHERE sync_status = 'completed'
    AND last_synced_at < NOW() - INTERVAL '1 year';
```

## Backup Strategy

### Full Backup

```bash
# Daily full backup
pg_dump -U user -d syncdb -F c -f backup_$(date +%Y%m%d).dump

# Restore from backup
pg_restore -U user -d syncdb -c backup_20251004.dump
```

### Incremental Backup

```bash
# Enable WAL archiving in postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'cp %p /path/to/archive/%f'

# Point-in-time recovery
pg_basebackup -U user -D /path/to/backup -Fp -Xs -P
```

## Migration Strategy

### Using Alembic

```python
# alembic/versions/001_initial_schema.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

def upgrade():
    op.create_table(
        'repositories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('github_url', sa.String(500), nullable=False),
        sa.Column('github_repo_name', sa.String(255), nullable=False),
        # ... other columns
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('github_url')
    )
    
    op.create_index('idx_repositories_sync_status', 'repositories', ['sync_status'])
    # ... other indexes

def downgrade():
    op.drop_table('repositories')
```

### Migration Commands

```bash
# Create a new migration
alembic revision -m "Add new column"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

## Performance Considerations

### Indexing Strategy

1. **Primary Keys**: Automatic B-tree indexes
2. **Foreign Keys**: Indexed for join performance
3. **Status Columns**: Indexed for filtering
4. **Timestamp Columns**: Indexed for time-based queries
5. **JSONB Columns**: GIN indexes for JSON queries (if needed)

### Query Optimization

```sql
-- Add GIN index for JSONB queries (if needed)
CREATE INDEX idx_repositories_metadata ON repositories USING GIN (metadata);

-- Example JSONB query
SELECT * FROM repositories
WHERE metadata @> '{"language": "Python"}';

-- Analyze query performance
EXPLAIN ANALYZE
SELECT * FROM repositories WHERE sync_status = 'pending';
```

### Connection Pooling

```python
# SQLAlchemy connection pool configuration
from sqlalchemy import create_engine

engine = create_engine(
    'postgresql://user:pass@localhost/syncdb',
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

## Security Considerations

### Access Control

```sql
-- Create read-only user for monitoring
CREATE USER monitor WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE syncdb TO monitor;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO monitor;

-- Create application user with limited permissions
CREATE USER app_user WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE syncdb TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
```

### Encryption

```sql
-- Enable SSL connections
-- In postgresql.conf:
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'

-- Require SSL for connections
-- In pg_hba.conf:
hostssl all all 0.0.0.0/0 md5
```

### Sensitive Data

- Never store GitHub tokens or OneDev API tokens in the database
- Use environment variables or secret management systems
- Sanitize error messages before storing (remove tokens/passwords)

---

**Last Updated**: 2025-10-04  
**Version**: 1.0

