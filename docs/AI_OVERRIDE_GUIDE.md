# AI_OVERRIDE Quick Start Guide

## What is AI_OVERRIDE?

AI_OVERRIDE is a testing feature that allows you to override ALL AI model calls with a cheaper model (typically Haiku) to avoid expensive Sonnet costs during development and testing.

## Quick Start

### 1. Enable AI_OVERRIDE in your .env file

```bash
# Add these lines to your .env file
AI_OVERRIDE=true
AI_OVERRIDE_MODEL=haiku  # or "claude-3-5-haiku-latest"
```

### 2. Verify it's working

Run any deliberation and check the logs for override messages:

```bash
make run
```

You should see log messages like:
```
🔄 AI_OVERRIDE enabled: sonnet → haiku (using cheaper model for testing)
```

### 3. Check your costs

- **Before (Sonnet)**: ~$0.10 per deliberation
- **After (Haiku)**: ~$0.03 per deliberation
- **Savings**: 67% cheaper!

## When to Use

### ✅ DO use AI_OVERRIDE:

- **Local development**: Avoid expensive costs while building features
- **Testing**: Run integration tests without breaking the bank
- **CI/CD pipelines**: Keep automated test costs low
- **Debugging**: Iterate quickly without worrying about API costs

### ❌ DON'T use AI_OVERRIDE:

- **Production**: Real users should get the best models (Sonnet)
- **Quality validation**: When you need to verify actual model performance
- **Benchmarking**: When comparing model outputs
- **Final pre-launch testing**: Validate with production models

## Environment Variable Reference

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AI_OVERRIDE` | Boolean | `false` | Enable model override |
| `AI_OVERRIDE_MODEL` | String | `claude-3-5-haiku-latest` | Model to use when override is enabled |

## Examples

### Example 1: Local Development

```bash
# .env file
AI_OVERRIDE=true
AI_OVERRIDE_MODEL=haiku
```

**Result**: All models (persona, facilitator, decomposer, etc.) use Haiku

### Example 2: CI/CD Testing

```bash
# GitHub Actions workflow
env:
  AI_OVERRIDE: true
  AI_OVERRIDE_MODEL: claude-3-5-haiku-latest
```

**Result**: Automated tests use the cheapest model

### Example 3: Production (Disable Override)

```bash
# .env.production
AI_OVERRIDE=false
```

**Result**: Models use their configured values (Sonnet for personas, etc.)

## How It Works

1. When `AI_OVERRIDE=true`, the `resolve_model_alias()` function checks the override setting
2. ALL model resolution is intercepted at this central function
3. Instead of using the requested model (e.g., "sonnet"), it uses `AI_OVERRIDE_MODEL`
4. A log message confirms each override: `🔄 AI_OVERRIDE enabled: X → Y`

This happens **before** any API call is made, so it affects:
- Persona contributions (normally Sonnet)
- Facilitator decisions (normally Sonnet)
- Decomposition (normally Sonnet)
- Summarization (normally Haiku - but can override to even cheaper models)
- All other LLM calls

## Cost Comparison

### Typical Deliberation (5 personas, 3 rounds, 35 LLM calls)

| Configuration | Input Tokens | Cost per 1M | Total Cost |
|---------------|--------------|-------------|------------|
| **Production (Sonnet + caching)** | ~300K | $3.00 | ~$0.10 |
| **With AI_OVERRIDE (Haiku)** | ~300K | $1.00 | ~$0.03 |

### Monthly Costs (100 deliberations)

| Configuration | Monthly Cost | Annual Cost |
|---------------|--------------|-------------|
| **Production** | $10 | $120 |
| **With AI_OVERRIDE** | $3 | $36 |
| **Savings** | **$7/month** | **$84/year** |

## Troubleshooting

### Override not working?

1. Check your `.env` file has `AI_OVERRIDE=true`
2. Restart your application to reload environment variables
3. Check logs for `🔄 AI_OVERRIDE enabled` messages
4. Verify `AI_OVERRIDE_MODEL` is a valid model alias or ID

### Costs still high?

1. Verify override is actually enabled (check logs)
2. Make sure you're using a cheaper model (e.g., "haiku")
3. Check that you don't have other expensive API calls (embeddings, etc.)

### Want to use different override model?

```bash
# Use the latest Haiku
AI_OVERRIDE_MODEL=claude-3-5-haiku-latest

# Use the model alias
AI_OVERRIDE_MODEL=haiku

# Use a specific version
AI_OVERRIDE_MODEL=claude-haiku-4-5-20251001
```

## Best Practices

1. **Always enable for local dev**: Add to your personal `.env` file
2. **Enable for CI/CD**: Add to GitHub Actions secrets
3. **Disable for production**: Set to `false` in production env
4. **Monitor your costs**: Check Anthropic usage dashboard regularly
5. **Test with production models occasionally**: Verify quality before launch

## Related Documentation

- [Environment Variables](/docs/ENVIRONMENT_VARIABLES.md) - Full environment variable reference
- [Configuration](/bo1/config.py) - Model configuration source code
- [Prompt Engineering](/zzz_important/PROMPT_ENGINEERING_FRAMEWORK.md) - How models are used

## Questions?

Check the main [ENVIRONMENT_VARIABLES.md](/docs/ENVIRONMENT_VARIABLES.md) documentation or open an issue on GitHub.
