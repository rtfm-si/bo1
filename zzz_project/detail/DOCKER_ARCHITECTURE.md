# Docker Architecture for Board of One

## Executive Summary

Board of One is now **Docker-first** for maximum portability and cloud readiness. All development, testing, and deployment happens in containers.

---

## Why Docker-First?

✅ **Portability**: Works identically on macOS, Linux, Windows, and cloud platforms
✅ **Cloud-Ready**: Deploy to AWS ECS, Google Cloud Run, Azure without changes
✅ **Consistency**: Same environment for all developers and CI/CD
✅ **Isolation**: No conflicts with local Python installations
✅ **Reproducibility**: Exact same dependencies every time
✅ **Easy Onboarding**: `make setup && make build && make up` - done!

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Docker Host                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │                  Docker Network (bo1-network)              │     │
│  ├────────────────────────────────────────────────────────────┤     │
│  │                                                             │     │
│  │  ┌──────────────────────┐       ┌──────────────────────┐  │     │
│  │  │   bo1-app            │       │   bo1-redis          │  │     │
│  │  │                      │       │                      │  │     │
│  │  │ Python 3.12          │◄─────►│ Redis 7-alpine       │  │     │
│  │  │ ├─ bo1/              │       │                      │  │     │
│  │  │ ├─ anthropic SDK     │       │ Port: 6379          │  │     │
│  │  │ ├─ langchain         │       │                      │  │     │
│  │  │ ├─ voyageai          │       │ Health check:       │  │     │
│  │  │ └─ rich              │       │   redis-cli ping    │  │     │
│  │  │                      │       │                      │  │     │
│  │  │ Ports: 8000 (future) │       │ Volume: redis-data   │  │     │
│  │  │ TTY: Yes             │       │ Restart: always     │  │     │
│  │  │ STDIN: Open          │       │                      │  │     │
│  │  └──────────────────────┘       └──────────────────────┘  │     │
│  │           │                                                 │     │
│  │           │ Volume Mounts (Development)                    │     │
│  │           ▼                                                 │     │
│  │  ┌─────────────────────────────────────────────────────┐  │     │
│  │  │  Host Machine                                        │  │     │
│  │  │  ├─ ./bo1/           → /app/bo1 (hot reload)        │  │     │
│  │  │  ├─ ./exports/       → /app/exports (persist)       │  │     │
│  │  │  ├─ ./zzz_important/ → /app/zzz_important           │  │     │
│  │  │  └─ ./tests/         → /app/tests                   │  │     │
│  │  └─────────────────────────────────────────────────────┘  │     │
│  │                                                             │     │
│  │  Optional: Redis Commander (--profile debug)               │     │
│  │  ┌──────────────────────┐                                 │     │
│  │  │ redis-commander      │                                 │     │
│  │  │ Port: 8081           │                                 │     │
│  │  │ http://localhost:8081│                                 │     │
│  │  └──────────────────────┘                                 │     │
│  └────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Multi-Stage Dockerfile Strategy

### Stage 1: `base`
- **Purpose**: Foundation layer
- **Contents**: Python 3.12-slim, system dependencies, uv
- **Size**: ~200 MB
- **Rebuild**: Rarely (only when base image updates)

### Stage 2: `dependencies`
- **Purpose**: Cached dependencies layer
- **Contents**: Virtual environment, Python packages
- **Size**: ~400 MB (adds ~200 MB to base)
- **Rebuild**: Only when `pyproject.toml` changes
- **Key Optimization**: This is heavily cached!

### Stage 3: `development`
- **Purpose**: Development environment
- **Contents**: Dev dependencies (pytest, ruff, mypy)
- **Size**: ~500 MB (adds ~100 MB to dependencies)
- **Rebuild**: When Dockerfile changes
- **Volume Mounts**: Source code mounted for hot reload

### Stage 4: `production`
- **Purpose**: Production-optimized image
- **Contents**: Minimal dependencies, non-root user
- **Size**: ~400 MB (smaller than dev)
- **Rebuild**: For releases
- **Immutable**: No volume mounts, all code baked in

### Stage 5: `testing`
- **Purpose**: CI/CD automated testing
- **Contents**: Test files, pytest config
- **Size**: ~550 MB
- **Rebuild**: For CI/CD runs
- **Usage**: GitHub Actions, GitLab CI, etc.

---

## Layer Caching Strategy

```dockerfile
# Layer 1: Base (rarely changes)
FROM python:3.12-slim AS base
RUN apt-get update && apt-get install -y curl git

# Layer 2: Package manager (rarely changes)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Layer 3: Dependencies (changes only with pyproject.toml)
COPY pyproject.toml .
RUN uv venv && uv pip install -e .
# ⚡ This layer is HEAVILY cached

# Layer 4: Source code (changes frequently in dev, not in prod)
COPY bo1/ ./bo1/
# ⚡ This layer rebuilds often in dev (but volume-mounted anyway)
```

**Result**: Rebuilds in dev take ~10 seconds (only last layer changes)

---

## Development vs Production

| Aspect | Development | Production |
|--------|-------------|------------|
| **Dockerfile Stage** | `development` | `production` |
| **User** | root | bo1user (non-root) |
| **Source Code** | Volume-mounted (hot reload) | Baked into image |
| **Dependencies** | All + dev tools | Minimal only |
| **Debug Tools** | Included | Excluded |
| **Redis Password** | None | Required |
| **Resource Limits** | None | CPU: 2, Memory: 2G |
| **Health Checks** | Basic | Comprehensive |
| **Restart Policy** | unless-stopped | always |
| **Size** | ~500 MB | ~400 MB |

---

## Volume Strategy

### Development Volumes

```yaml
volumes:
  # Source code (hot reload)
  - ./bo1:/app/bo1                    # Application code
  - ./zzz_important:/app/zzz_important # Personas, prompts
  - ./zzz_project:/app/zzz_project     # Tasks, docs
  - ./tests:/app/tests                 # Tests

  # Persistent data
  - ./exports:/app/exports             # Generated reports

  # Named volumes
  - redis-data:/data                   # Redis persistence
```

**Why**: Changes to Python files immediately available in container. No rebuild needed!

### Production Volumes

```yaml
volumes:
  # Only persistent data
  - ./exports:/app/exports             # Generated reports

  # Named volumes
  - redis-data:/data                   # Redis persistence
```

**Why**: Immutable deployment. All code baked into image for consistency.

---

## Network Architecture

### Development

```yaml
networks:
  bo1-network:
    driver: bridge
```

- All containers on private bridge network
- Redis accessible only to bo1-app (not host)
- Port 6379 exposed to host for debugging
- Port 8081 exposed for Redis Commander

### Production

```yaml
networks:
  bo1-network:
    driver: bridge
```

- Redis accessible only to bo1-app
- Port 6379 bound to 127.0.0.1 (localhost only)
- No external access to Redis
- No Redis Commander in production

---

## Redis Configuration

### Development

```bash
redis-server \
  --appendonly yes              # AOF persistence
  --maxmemory 256mb            # Memory limit
  --maxmemory-policy allkeys-lru # Eviction policy
  --save 60 1000               # Snapshot every 60s if 1000 writes
```

### Production

```bash
redis-server \
  --appendonly yes              # AOF persistence
  --maxmemory 512mb            # Higher memory limit
  --maxmemory-policy allkeys-lru # Eviction policy
  --save 300 10                # Less frequent snapshots
  --requirepass ${REDIS_PASSWORD} # Password auth
```

---

## Environment Variable Flow

```
1. .env file (gitignored)
   ↓
2. docker-compose.yml (loads from .env)
   ↓
3. Container environment variables
   ↓
4. bo1/config.py (reads from os.environ)
   ↓
5. Application code
```

**Security**:
- Secrets in `.env` (never committed)
- Production: Use cloud secrets manager (AWS Secrets Manager, etc.)
- `.env.example` shows required variables (safe to commit)

---

## Cloud Deployment Paths

### AWS ECS (Fargate)

```
1. Push image to ECR
2. Create ECS task definition
3. Create ECS service
4. Configure Application Load Balancer (v2)
5. Set environment variables via Secrets Manager
```

**Cost**: ~$30-50/month for small workload

### Google Cloud Run

```
1. Build image (or let Cloud Run build from Dockerfile)
2. Deploy with gcloud run deploy
3. Set environment variables via Secret Manager
4. Configure Cloud SQL for Redis (or Cloud Memorystore)
```

**Cost**: ~$20-40/month for small workload (serverless pricing)

### Azure Container Instances

```
1. Push image to Azure Container Registry
2. Create container instance via Azure CLI or Portal
3. Configure environment variables
4. Use Azure Cache for Redis
```

**Cost**: ~$25-45/month for small workload

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test and Build

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build test image
        run: docker build --target testing -t bo1:test .
      - name: Run tests
        run: docker run bo1:test

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build production image
        run: docker build --target production -t bo1:prod .
      - name: Push to registry
        run: |
          docker tag bo1:prod ${{ secrets.REGISTRY }}/bo1:${{ github.sha }}
          docker push ${{ secrets.REGISTRY }}/bo1:${{ github.sha }}
```

---

## Performance Optimizations

### 1. Layer Caching
- Dependencies cached (rebuild only when pyproject.toml changes)
- Base image cached (rarely changes)
- Source code layer small (fast to rebuild)

### 2. Multi-Stage Builds
- Development: All tools included
- Production: Minimal size (~400 MB)
- Testing: Optimized for CI/CD

### 3. Volume Mounts
- Source code hot-reloads (no rebuild during dev)
- Redis data persists across restarts
- Exports accessible on host machine

### 4. Parallel Builds
```bash
# Build stages in parallel
docker buildx build --target development --target production .
```

---

## Security Hardening (Production)

### 1. Non-Root User
```dockerfile
RUN useradd -m -u 1000 bo1user
USER bo1user
```

### 2. Read-Only Filesystem (Future)
```yaml
security_opt:
  - no-new-privileges:true
read_only: true
```

### 3. Resource Limits
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
```

### 4. Network Segmentation
- Redis not exposed externally
- App-to-Redis communication internal only

### 5. Secrets Management
- Never hardcode secrets
- Use cloud provider secrets managers
- Rotate credentials regularly

---

## Monitoring & Observability

### Container Metrics

```bash
# Resource usage
make stats

# Health status
make status

# Logs
make logs-app
```

### Redis Metrics

```bash
# Redis CLI
make redis-cli

# Inside CLI:
INFO           # Full stats
INFO stats     # Specific stats
MONITOR        # Real-time commands
```

### Application Metrics (Future v2)

- Prometheus metrics endpoint
- Grafana dashboards
- CloudWatch / Stackdriver integration

---

## Cost Analysis

### Development (Local)

- **Cost**: $0 (runs on your machine)
- **Resources**: 2-4 GB RAM, minimal CPU

### Production (Cloud)

#### Small Workload (1-10 deliberations/day)
- **AWS ECS Fargate**: ~$30/month (0.25 vCPU, 0.5 GB RAM)
- **Google Cloud Run**: ~$20/month (serverless, pay per use)
- **Azure Container Instances**: ~$25/month (1 vCPU, 1 GB RAM)

#### Medium Workload (50-100 deliberations/day)
- **AWS ECS Fargate**: ~$50/month (0.5 vCPU, 1 GB RAM)
- **Google Cloud Run**: ~$40/month (more invocations)
- **Azure Container Instances**: ~$45/month (2 vCPU, 2 GB RAM)

**Note**: LLM API costs (Anthropic + Voyage) will be much higher than infrastructure costs (~$0.10 per deliberation).

---

## Migration Path to v2 (Web API)

Current: Console-based in Docker
Future v2: FastAPI web API in Docker

**Changes needed**:
1. Add FastAPI to dependencies
2. Create `bo1/api/` module
3. Expose port 8000 in Dockerfile
4. Update health checks to use HTTP endpoint
5. Add nginx reverse proxy (optional)

**No architecture changes needed** - Docker setup already supports this!

---

## Summary

✅ **Fully containerized**: Everything runs in Docker
✅ **Cloud-ready**: Deploy to any cloud platform
✅ **Developer-friendly**: Hot reload, easy debugging
✅ **Production-optimized**: Minimal images, security hardened
✅ **Portable**: Works identically everywhere

**Next Steps**: Follow `zzz_project/TASKS.md` starting with Day 1-2 Docker setup tasks.
