# Logging Configuration

All demo scripts in the `bo1/` directory now respect environment variables from `.env` for logging control.

## Environment Variables

### DEBUG (true/false)
Controls whether internal `bo1.*` module logs are shown.

- `DEBUG=true`: Shows all logs from bo1 modules (decomposer, selector, broker, etc.)
- `DEBUG=false`: Suppresses internal bo1 logs, only shows demo-level output

**Default**: `true`

### LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
Controls the minimum log level for all loggers.

- `DEBUG`: Most verbose, shows all debug messages
- `INFO`: Shows informational messages and above
- `WARNING`: Only warnings, errors, and critical messages (cleanest output)
- `ERROR`: Only errors and critical messages
- `CRITICAL`: Only critical messages

**Default**: `INFO`

## Usage Examples

### Example 1: Clean Output (for demos)
```bash
# .env
DEBUG=false
LOG_LEVEL=WARNING
```

This gives you clean, minimal output - perfect for showcasing the system without debug noise.

### Example 2: Debugging Issues
```bash
# .env
DEBUG=true
LOG_LEVEL=DEBUG
```

This shows everything - useful when tracking down bugs or understanding flow.

### Example 3: Production-like (recommended for testing)
```bash
# .env
DEBUG=false
LOG_LEVEL=INFO
```

This shows high-level info without internal module noise - good balance for testing.

## What Gets Logged

### Always Suppressed (regardless of settings):
- `httpx` - HTTP client library (always WARNING level)
- `anthropic` - Anthropic SDK (always WARNING level)

### Controlled by DEBUG:
- `bo1.agents.*` - Agent operations (decomposer, selector, facilitator, moderator)
- `bo1.llm.*` - LLM calls, broker operations, caching
- `bo1.orchestration.*` - Deliberation engine operations
- `bo1.data.*` - Data loading operations

### Controlled by LOG_LEVEL:
- Root logger and all other loggers respect this setting

## Quick Switching

To quickly switch between modes without editing `.env`:

```bash
# Temporarily override for one run
DEBUG=false LOG_LEVEL=WARNING make demo

# Or with Docker
DEBUG=true LOG_LEVEL=DEBUG docker-compose exec bo1 python bo1/demo_multiround.py
```

## Files Using This Configuration

- `bo1/demo.py` - Days 8-11 demo
- `bo1/demo_multiround.py` - Days 12-13 multi-round demo

All future demo scripts should follow this same pattern for consistency.
