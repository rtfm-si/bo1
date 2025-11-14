# Environment Variables Documentation

**Version**: Week 3.5
**Last Updated**: 2025-11-14
**Configuration File**: `.env.example`

---

## Overview

Board of One uses environment variables for configuration across development, staging, and production environments. All variables are documented below with their purpose, type, default values, and required status.

---

## Required Variables

These variables MUST be set for the application to function.

### LLM API Keys

| Variable | Type | Required | Description | Example |
|----------|------|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | String | ✅ Yes | Anthropic API key for Claude models | `sk-ant-...` |
| `VOYAGE_API_KEY` | String | ✅ Yes | Voyage AI API key for embeddings (convergence detection) | `pa-...` |

**How to Get**:
- Anthropic: https://console.anthropic.com/
- Voyage AI: https://www.voyageai.com/

---

## Database Configuration

### PostgreSQL

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `DATABASE_URL` | String | ✅ Yes | - | Full PostgreSQL connection string |
| `POSTGRES_HOST` | String | ✅ Yes | `localhost` | PostgreSQL server hostname |
| `POSTGRES_PORT` | Integer | ✅ Yes | `5432` | PostgreSQL server port |
| `POSTGRES_DB` | String | ✅ Yes | `boardofone` | Database name |
| `POSTGRES_USER` | String | ✅ Yes | `bo1` | Database user |
| `POSTGRES_PASSWORD` | String | ✅ Yes | - | Database password (change in production!) |

**Example**:
```bash
DATABASE_URL=postgresql://bo1:your_password@localhost:5432/boardofone
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=boardofone
POSTGRES_USER=bo1
POSTGRES_PASSWORD=your_secure_password_here
```

**Security Notes**:
- Never commit real passwords to version control
- Use different passwords for dev/staging/production
- Consider using secrets management (Doppler, AWS Secrets Manager)

### Redis

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `REDIS_HOST` | String | ✅ Yes | `localhost` | Redis server hostname |
| `REDIS_PORT` | Integer | ✅ Yes | `6379` | Redis server port |
| `REDIS_DB` | Integer | ✅ Yes | `0` | Redis database number (0-15) |
| `REDIS_URL` | String | ✅ Yes | - | Full Redis connection string |
| `REDIS_SESSION_TTL` | Integer | No | `604800` | Session TTL in seconds (7 days) |
| `REDIS_CHECKPOINT_TTL` | Integer | No | `604800` | Checkpoint TTL in seconds (7 days) |
| `REDIS_CACHE_TTL` | Integer | No | `2592000` | Cache TTL in seconds (30 days) |
| `REDIS_RATELIMIT_TTL` | Integer | No | `60` | Rate limit window in seconds (1 minute) |

**Example**:
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL=redis://localhost:6379/0
```

**TTL Strategy**: See `docs/REDIS_KEY_PATTERNS.md` for detailed key patterns and TTL strategy.

---

## Application Settings

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `ENVIRONMENT` | String | No | `development` | Environment name (development, staging, production) |
| `DEBUG` | Boolean | No | `false` | Enable debug-level logging for bo1 modules |
| `LOG_LEVEL` | String | No | `INFO` | Overall log verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `VERBOSE_LIBS` | Boolean | No | `false` | Show debug logs from third-party libraries (anthropic, httpx, etc.) |

**Log Levels**:
- `INFO`: Clean output with key events (recommended for most users)
- `DEBUG`: Detailed bo1 internal logs (useful for debugging)
- `WARNING`: Minimal output, only warnings and errors

**Example**:
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
VERBOSE_LIBS=false
```

---

## Cost & Safety Limits

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `MAX_COST_PER_SESSION` | Float | No | `1.00` | Hard limit per session (USD) |
| `MAX_COST_PER_SUBPROBLEM` | Float | No | `0.15` | Target per sub-problem (USD) |
| `DELIBERATION_RECURSION_LIMIT` | Integer | No | `55` | Max graph steps (15 rounds × 3 nodes + overhead) |
| `DELIBERATION_TIMEOUT` | Integer | No | `3600` | Max session duration in seconds (1 hour) |

**Example**:
```bash
MAX_COST_PER_SESSION=1.00
MAX_COST_PER_SUBPROBLEM=0.15
DELIBERATION_RECURSION_LIMIT=55
DELIBERATION_TIMEOUT=3600
```

**Safety Notes**:
- Cost limits prevent runaway sessions
- Recursion limit prevents infinite loops (5-layer safety system)
- Timeout provides hard kill switch for long-running sessions

---

## Model Configuration

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `DEFAULT_MODEL_PERSONA` | String | No | `claude-sonnet-4-5-20250929` | Model for persona contributions |
| `DEFAULT_MODEL_FACILITATOR` | String | No | `claude-sonnet-4-5-20250929` | Model for facilitator decisions |
| `DEFAULT_MODEL_SUMMARIZER` | String | No | `claude-haiku-4-5-20250929` | Model for round summarization |
| `DEFAULT_MODEL_DECOMPOSER` | String | No | `claude-sonnet-4-5-20250929` | Model for problem decomposition |
| `DEFAULT_MODEL_MODERATOR` | String | No | `claude-haiku-4-5-20250929` | Model for moderator interventions |

**Available Models**:
- `claude-sonnet-4-5-20250929` - Sonnet 4.5 (high quality, moderate cost)
- `claude-haiku-4-5-20250929` - Haiku 4.5 (fast, low cost)
- `claude-opus-4-5-20250929` - Opus 4.5 (highest quality, highest cost)

**Cost Optimization**:
- Use **Sonnet** for personas (prompt caching = 90% cost reduction)
- Use **Haiku** for summarization (background tasks)
- Local dev: Set all to Haiku for faster/cheaper testing

**Example**:
```bash
DEFAULT_MODEL_PERSONA=claude-sonnet-4-5-20250929
DEFAULT_MODEL_FACILITATOR=claude-sonnet-4-5-20250929
DEFAULT_MODEL_SUMMARIZER=claude-haiku-4-5-20250929
```

### AI Model Override (Testing Mode)

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `AI_OVERRIDE` | Boolean | No | `false` | Override ALL model calls with cheaper model (testing mode) |
| `AI_OVERRIDE_MODEL` | String | No | `claude-3-5-haiku-latest` | Model to use when AI_OVERRIDE is true |

**Purpose**: Prevent expensive Sonnet costs during testing and development by forcing all LLM calls to use a cheaper model (typically Haiku).

**When to Use**:
- ✅ **Local testing**: Set to `true` to avoid expensive API costs
- ✅ **CI/CD pipelines**: Set to `true` to keep test costs low
- ❌ **Production**: Should always be `false`

**Example**:
```bash
# Enable override for local testing
AI_OVERRIDE=true
AI_OVERRIDE_MODEL=haiku  # or "claude-3-5-haiku-latest"
```

**How It Works**:
- When `AI_OVERRIDE=true`, ALL model calls (persona, facilitator, decomposer, etc.) use `AI_OVERRIDE_MODEL` instead
- The override happens at the `resolve_model_alias()` level, so it affects all parts of the system
- Logs will show: `🔄 AI_OVERRIDE enabled: sonnet → haiku (using cheaper model for testing)`

**Cost Savings**:
- Sonnet: $3/1M input tokens → Haiku: $1/1M input tokens (**67% cheaper**)
- Typical deliberation: ~$0.10 with Sonnet → ~$0.03 with Haiku

---

## Feature Flags

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `ENABLE_PROMPT_CACHING` | Boolean | No | `true` | Enable Anthropic prompt caching (90% cost reduction) |
| `ENABLE_CONVERGENCE_DETECTION` | Boolean | No | `true` | Enable early stopping based on semantic similarity |
| `ENABLE_DRIFT_DETECTION` | Boolean | No | `true` | Prevent off-topic contributions |
| `ENABLE_EARLY_STOPPING` | Boolean | No | `true` | Stop when consensus reached |
| `AB_TESTING_ENABLED` | Boolean | No | `true` | Enable A/B testing for experimental features |

**Example**:
```bash
ENABLE_PROMPT_CACHING=true
ENABLE_CONVERGENCE_DETECTION=true
ENABLE_DRIFT_DETECTION=true
ENABLE_EARLY_STOPPING=true
```

**Performance Impact**:
- Prompt caching: 90% cost reduction on persona calls
- Convergence detection: 20-40% faster deliberations
- Drift detection: Prevents wasted rounds

---

## Authentication (Week 7+)

Not required for Week 3.5. Uncomment when implementing Supabase Auth in Week 7.

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `SUPABASE_URL` | String | No (Week 7+) | - | Supabase project URL |
| `SUPABASE_ANON_KEY` | String | No (Week 7+) | - | Supabase anonymous key |
| `SUPABASE_SERVICE_ROLE_KEY` | String | No (Week 7+) | - | Supabase service role key (admin operations) |
| `JWT_SECRET` | String | No (Week 7+) | - | JWT signing secret |
| `JWT_ALGORITHM` | String | No (Week 7+) | `HS256` | JWT algorithm |
| `JWT_EXPIRE_MINUTES` | Integer | No (Week 7+) | `1440` | JWT expiration (24 hours) |

**Example** (Week 7+):
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
JWT_SECRET=your_jwt_secret_here
```

---

## Admin & Monitoring (Week 9-10+)

Not required for Week 3.5. Uncomment when implementing admin features.

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `ADMIN_API_KEY` | String | No (Week 9+) | - | Admin API key for kill switches, monitoring |
| `GRAFANA_PASSWORD` | String | No (Week 10+) | - | Grafana dashboard password |
| `PROMETHEUS_PORT` | Integer | No (Week 10+) | `9090` | Prometheus metrics port |
| `NTFY_URL` | String | No (Week 9+) | `https://ntfy.sh` | ntfy.sh server URL |
| `NTFY_TOPIC` | String | No (Week 9+) | - | ntfy.sh topic for alerts |

**Example** (Week 9+):
```bash
ADMIN_API_KEY=your_admin_api_key_here
NTFY_URL=https://ntfy.sh
NTFY_TOPIC=boardofone-alerts
```

---

## Email (Week 12+)

Not required for Week 3.5. Uncomment when implementing Resend integration.

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `RESEND_API_KEY` | String | No (Week 12+) | - | Resend API key for transactional emails |

**Example** (Week 12+):
```bash
RESEND_API_KEY=re_...
```

---

## Payments (Week 8+)

Not required for Week 3.5. Uncomment when implementing Stripe.

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `STRIPE_SECRET_KEY` | String | No (Week 8+) | - | Stripe secret key |
| `STRIPE_PUBLISHABLE_KEY` | String | No (Week 8+) | - | Stripe publishable key |
| `STRIPE_WEBHOOK_SECRET` | String | No (Week 8+) | - | Stripe webhook signing secret |

**Example** (Week 8+):
```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

---

## Rate Limiting (Week 8+)

Not required for Week 3.5. Uncomment when implementing rate limiting.

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `RATE_LIMIT_PER_MINUTE` | Integer | No (Week 8+) | `10` | Free tier rate limit per minute |
| `RATE_LIMIT_PER_HOUR` | Integer | No (Week 8+) | `100` | Free tier rate limit per hour |
| `RATE_LIMIT_PER_DAY` | Integer | No (Week 8+) | `500` | Free tier rate limit per day |

**Example** (Week 8+):
```bash
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_PER_HOUR=100
RATE_LIMIT_PER_DAY=500
```

---

## Secrets Management

### Development

For local development, use `.env` file:

```bash
cp .env.example .env
# Edit .env with your actual values
```

### Staging/Production

**Recommended Options**:

1. **Doppler** (Recommended)
   - Centralized secrets management
   - Easy rotation, auditing
   - Free tier available
   - https://www.doppler.com/

2. **AWS Secrets Manager**
   - Native AWS integration
   - Automatic rotation
   - Pay per secret

3. **1Password Secrets Automation**
   - Team password manager integration
   - CLI access
   - https://developer.1password.com/

**NEVER**:
- ❌ Commit `.env` files to git
- ❌ Hardcode secrets in code
- ❌ Use same secrets for dev/staging/production

---

## Environment-Specific Configuration

### Development

```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE_URL=postgresql://bo1:bo1_dev_password@localhost:5432/boardofone
REDIS_URL=redis://localhost:6379/0
```

### Staging

```bash
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=postgresql://bo1:staging_password@staging-db:5432/boardofone
REDIS_URL=redis://staging-redis:6379/0
```

### Production

```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
DATABASE_URL=postgresql://bo1:production_password@prod-db:5432/boardofone
REDIS_URL=redis://prod-redis:6379/0
MAX_COST_PER_SESSION=0.50  # Lower limit for production
```

---

## Validation

To validate your environment configuration:

```bash
# Check required variables are set
python -c "from bo1.config import settings; print('Config valid!')"

# Test database connection
make test-db-connection

# Test Redis connection
make test-redis-connection

# Run full environment validation
pytest tests/test_environment_config.py -v
```

---

## Troubleshooting

### Error: "ANTHROPIC_API_KEY not set"

**Solution**:
```bash
cp .env.example .env
# Add your Anthropic API key to .env
```

### Error: "Database connection refused"

**Solution**:
```bash
# Start PostgreSQL
make up
# Verify connection
docker-compose exec postgres psql -U bo1 -d boardofone -c "SELECT 1"
```

### Error: "Redis connection refused"

**Solution**:
```bash
# Start Redis
make up
# Verify connection
docker-compose exec redis redis-cli ping
```

---

## See Also

- `docs/DATABASE_SCHEMA.md` - Database schema documentation
- `docs/REDIS_KEY_PATTERNS.md` - Redis key patterns and TTL strategy
- `.env.example` - Example environment configuration
- `zzz_project/MVP_IMPLEMENTATION_ROADMAP.md` - Implementation roadmap
