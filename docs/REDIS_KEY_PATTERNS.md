# Redis Key Patterns & TTL Strategy

**Redis Version**: 7.x
**Purpose**: LLM prompt caching, session state, rate limiting
**Status**: Week 3.5 Complete

---

## Redis Usage Strategy

Redis serves three primary purposes in Board of One:

1. **LLM Prompt Caching** (Anthropic SDK automatic) - 90% cost reduction
2. **Session State Storage** (v1 only, v2 uses PostgreSQL + Redis checkpoints)
3. **Rate Limiting** (v2+, Week 8)

---

## Key Patterns

### 1. Session State (v1 Console Mode)

**Pattern**: `session:{session_id}`
**Type**: Hash
**TTL**: 24 hours (86400 seconds)
**Purpose**: Store deliberation state for v1 console sessions

**Fields**:
- `problem_statement`: User's problem (TEXT)
- `current_phase`: DeliberationPhase enum (STRING)
- `round_number`: Current round (INTEGER)
- `personas`: Selected persona codes (JSON array)
- `contributions`: All contributions (JSON array)
- `facilitator_decision`: Latest decision (JSON object)
- `total_cost`: Running cost (FLOAT)
- `created_at`: Session creation timestamp (ISO8601)
- `updated_at`: Last update timestamp (ISO8601)

**Example**:
```redis
HSET session:abc-123-def problem_statement "Should we invest $500K in expansion?"
HSET session:abc-123-def current_phase "deliberation"
HSET session:abc-123-def round_number "3"
EXPIRE session:abc-123-def 86400
```

**When to Use**:
- v1 console mode ONLY
- Temporary storage for pause/resume
- Automatically expires after 24 hours

**Migration Note**: v2 uses PostgreSQL for sessions, Redis only for checkpoints

---

### 2. LangGraph Checkpoints (v2+, Week 4)

**Pattern**: `checkpoint:{session_id}:{step_number}`
**Type**: String (serialized state)
**TTL**: 7 days (604800 seconds)
**Purpose**: LangGraph checkpoint recovery for pause/resume

**Example**:
```redis
SET checkpoint:abc-123-def:5 <serialized_graph_state>
EXPIRE checkpoint:abc-123-def:5 604800
```

**When to Use**:
- v2 web mode with LangGraph
- Allows pause/resume across days
- Longer TTL than v1 (7 days vs 24 hours)

**Cleanup**: Automatic expiration after 7 days

---

### 3. LLM Prompt Cache (Anthropic Automatic)

**Pattern**: Managed by Anthropic SDK (opaque keys)
**Type**: Internal to Anthropic SDK
**TTL**: Managed by Anthropic (typically 5 minutes)
**Purpose**: Cache persona system prompts for 90% cost reduction

**How It Works**:
1. Anthropic SDK uses Redis as cache backend (if configured)
2. SDK automatically caches long system prompts (>1024 tokens)
3. Subsequent calls with same prompt are 90% cheaper
4. Cache TTL managed by SDK (typically 5 minutes)

**Configuration**:
```python
# Anthropic SDK automatically uses Redis if REDIS_URL is set
# No manual key management required
```

**Monitoring**:
```bash
# View cache hit rate in Redis
redis-cli INFO stats | grep keyspace_hits
redis-cli INFO stats | grep keyspace_misses
```

**Cost Impact**:
- Uncached: $0.015 per persona call (Sonnet 4.5, 1500 tokens)
- Cached: $0.0015 per persona call (90% reduction)
- For 35 persona calls per deliberation: **$0.525 → $0.0525** (saves $0.47)

---

### 4. Rate Limiting (v2+, Week 8)

**Pattern**: `ratelimit:{user_id}:{action}:{window}`
**Type**: String (counter)
**TTL**: Depends on window (60 seconds for per-minute limits)
**Purpose**: Prevent abuse and manage API quotas

**Examples**:

**Per-Minute Limits**:
```redis
# Free tier: 10 sessions/min
INCR ratelimit:user_123:session_create:2025-11-14-17-05
EXPIRE ratelimit:user_123:session_create:2025-11-14-17-05 60
```

**Per-Hour Limits**:
```redis
# Free tier: 100 sessions/hour
INCR ratelimit:user_123:session_create:2025-11-14-17
EXPIRE ratelimit:user_123:session_create:2025-11-14-17 3600
```

**Per-Day Limits**:
```redis
# Free tier: 1000 sessions/day
INCR ratelimit:user_123:session_create:2025-11-14
EXPIRE ratelimit:user_123:session_create:2025-11-14 86400
```

**Rate Limit Tiers** (Week 8):

| Tier | Sessions/Min | Sessions/Hour | Sessions/Day | Cost/Session |
|------|--------------|---------------|--------------|--------------|
| Free | 10 | 100 | 1000 | $0.10 |
| Pro | 50 | 500 | 10000 | $0.08 |
| Enterprise | Unlimited | Unlimited | Unlimited | $0.05 |

**Implementation**:
```python
def check_rate_limit(user_id: str, action: str, limit: int, window: int) -> bool:
    key = f"ratelimit:{user_id}:{action}:{current_window}"
    count = redis.incr(key)
    if count == 1:
        redis.expire(key, window)
    return count <= limit
```

---

### 5. Generic Cache (v2+, Week 9)

**Pattern**: `cache:{namespace}:{key}`
**Type**: String (any serialized data)
**TTL**: Configurable (default 30 days)
**Purpose**: Cache expensive computations (persona recommendations, embeddings)

**Examples**:

**Cached Persona Recommendations**:
```redis
# Cache persona recommendations for common problems
SET cache:personas:fintech_saas <persona_codes_json>
EXPIRE cache:personas:fintech_saas 2592000  # 30 days
```

**Cached Embeddings** (Week 5+):
```redis
# Cache Voyage embeddings for similarity search
SET cache:embedding:sha256_of_text <embedding_vector>
EXPIRE cache:embedding:sha256_of_text 2592000  # 30 days
```

**When to Use**:
- Expensive operations (LLM calls, embeddings)
- Data that changes infrequently
- Trade-off: Stale data vs performance

---

### 6. Background Job Queue (Future, Week 11+)

**Pattern**: `queue:{queue_name}`
**Type**: List (job payloads)
**TTL**: No expiration (processed jobs removed)
**Purpose**: Asynchronous task processing (email sends, analytics)

**Example**:
```redis
# Enqueue email send job
RPUSH queue:email_send '{"to": "user@example.com", "template": "welcome"}'

# Worker pops job
LPOP queue:email_send
```

---

## TTL Strategy

| Key Pattern | TTL | Reason |
|-------------|-----|--------|
| `session:{id}` | 24 hours | v1 temporary storage, auto-cleanup |
| `checkpoint:{id}:{step}` | 7 days | Allow pause/resume across days |
| `ratelimit:{user}:{action}:{window}` | 60-86400s | Varies by window (minute/hour/day) |
| `cache:{namespace}:{key}` | 30 days | Expensive computations, infrequent changes |
| LLM prompt cache | ~5 min | Managed by Anthropic SDK |

---

## Redis Configuration

### Development

```yaml
# docker-compose.yml
redis:
  image: redis:7-alpine
  command: >
    redis-server
    --appendonly yes
    --maxmemory 256mb
    --maxmemory-policy allkeys-lru
    --save 60 1000
```

**Settings**:
- **AOF (Append-Only File)**: Persistence for session state
- **Max Memory**: 256MB (enough for dev, increase in prod)
- **Eviction Policy**: LRU (Least Recently Used) for cache keys
- **Save**: Snapshot every 60 seconds if 1000+ keys changed

### Production (Week 13)

```yaml
redis:
  image: redis:7-alpine
  command: >
    redis-server
    --appendonly yes
    --maxmemory 2gb
    --maxmemory-policy allkeys-lru
    --save 300 100
    --requirepass <REDIS_PASSWORD>
```

**Changes for Production**:
- **Max Memory**: 2GB (handle 1000s of sessions)
- **Password**: Required for security
- **Save**: Less frequent snapshots (every 5 min if 100+ changes)
- **Monitoring**: RedisInsight or Prometheus exporter

---

## Redis Cleanup Jobs

### Manual Cleanup (Development)

```bash
# Clear all session keys older than 24 hours
redis-cli --scan --pattern "session:*" | xargs redis-cli DEL

# Clear all checkpoint keys older than 7 days
redis-cli --scan --pattern "checkpoint:*" | xargs redis-cli DEL

# Clear all cache keys
redis-cli --scan --pattern "cache:*" | xargs redis-cli DEL

# Clear rate limit keys
redis-cli --scan --pattern "ratelimit:*" | xargs redis-cli DEL
```

### Automated Cleanup (Week 10)

**Cron job** to clean up expired keys:
```python
# scripts/redis_cleanup.py
import redis
from datetime import datetime, timedelta

r = redis.from_url(os.getenv("REDIS_URL"))

# Delete expired sessions (24h TTL)
for key in r.scan_iter("session:*"):
    ttl = r.ttl(key)
    if ttl == -1:  # No expiration set (shouldn't happen)
        r.expire(key, 86400)

# Delete old checkpoints (7 days TTL)
for key in r.scan_iter("checkpoint:*"):
    ttl = r.ttl(key)
    if ttl == -1:
        r.expire(key, 604800)
```

**Run daily**: `0 2 * * * python scripts/redis_cleanup.py`

---

## Redis Monitoring

### Key Metrics

```bash
# Total keys
redis-cli DBSIZE

# Memory usage
redis-cli INFO memory

# Cache hit rate
redis-cli INFO stats | grep keyspace_hits
redis-cli INFO stats | grep keyspace_misses

# Connected clients
redis-cli INFO clients
```

### Redis Commander (Development)

```bash
# Start Redis Commander web UI
docker-compose --profile debug up redis-commander

# Access at http://localhost:8081
```

### Alerts (Week 10)

- **Memory usage > 80%**: Alert admin (risk of eviction)
- **Keyspace hit rate < 50%**: Cache not effective
- **Connected clients > 100**: Possible connection leak

---

## Redis Backup Strategy

### Development Backups

```bash
# Manual backup
make backup-redis

# Creates: backups/redis_backup_YYYYMMDD_HHMMSS.rdb
```

### Production Backups (Week 13)

1. **AOF Persistence**: Enabled (durability for crashes)
2. **RDB Snapshots**: Every 5 minutes (if 100+ changes)
3. **Daily Backups**: Copy AOF + RDB to S3/DigitalOcean Spaces
4. **Retention**: Keep 7 days of backups

**Backup Script**:
```bash
#!/bin/bash
# scripts/backup_redis.sh
DATE=$(date +%Y%m%d_%H%M%S)
docker exec bo1-redis redis-cli BGSAVE
sleep 10  # Wait for BGSAVE to complete
docker cp bo1-redis:/data/dump.rdb backups/redis_backup_$DATE.rdb
# Upload to S3/Spaces
```

---

## Redis vs PostgreSQL

| Data Type | Redis | PostgreSQL | Reason |
|-----------|-------|------------|--------|
| Session state (v1) | ✅ | ❌ | Temporary, fast reads/writes |
| Session state (v2) | ❌ | ✅ | Persistent, relational queries |
| LangGraph checkpoints | ✅ | ❌ | Large blobs, fast recovery |
| LLM prompt cache | ✅ | ❌ | SDK automatic, short TTL |
| Rate limiting | ✅ | ❌ | Atomic increments, fast |
| User accounts | ❌ | ✅ | Persistent, relational |
| Contributions | ❌ | ✅ | Historical data, analytics |
| Votes | ❌ | ✅ | Historical data, analytics |
| Audit log | ❌ | ✅ | Compliance, long retention |

**Rule of Thumb**:
- **Redis**: Fast, temporary, cache, counters
- **PostgreSQL**: Persistent, relational, analytics

---

## Future Enhancements

- **Week 4**: LangGraph checkpoint storage
- **Week 8**: Rate limiting implementation
- **Week 9**: Generic caching layer (embeddings, personas)
- **Week 10**: Redis monitoring dashboard (Grafana)
- **Week 11**: Background job queue (email sends)
- **Week 13**: Production Redis cluster (HA setup)
