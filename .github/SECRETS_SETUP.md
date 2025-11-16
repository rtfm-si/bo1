# GitHub Secrets Configuration for CI/CD

This document explains how to configure GitHub Secrets for the Board of One CI/CD pipeline.

## Overview

The CI/CD pipeline is designed to work **without real API keys** for non-LLM tests. However, if you want to run the full test suite (including LLM integration tests), you'll need to configure the following secrets.

## Required Secrets (Optional for CI)

The following secrets are **optional** for CI to pass. The pipeline uses placeholder values (`test-key-placeholder`) when secrets are not configured, which is sufficient for non-LLM tests:

### 1. ANTHROPIC_API_KEY
- **Purpose**: Anthropic API key for Claude LLM calls
- **Required for**: Tests marked with `@pytest.mark.requires_llm`
- **Get it from**: https://console.anthropic.com/
- **Default value**: `test-key-placeholder` (allows CI to pass without real key)

### 2. VOYAGE_API_KEY
- **Purpose**: Voyage AI API key for embeddings (semantic similarity, research caching)
- **Required for**: Tests marked with `@pytest.mark.requires_llm` that use embeddings
- **Get it from**: https://www.voyageai.com/
- **Default value**: `test-key-placeholder` (allows CI to pass without real key)

### 3. CODECOV_TOKEN
- **Purpose**: Codecov upload token for coverage reports
- **Required for**: Coverage report uploads (doesn't block CI if missing)
- **Get it from**: https://codecov.io/ (after linking your repository)
- **Default behavior**: Coverage upload fails silently if token is missing

## How to Configure Secrets

1. Go to your GitHub repository
2. Navigate to: **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with the following details:

### Adding ANTHROPIC_API_KEY
- **Name**: `ANTHROPIC_API_KEY`
- **Value**: Your Anthropic API key (starts with `sk-ant-...`)

### Adding VOYAGE_API_KEY
- **Name**: `VOYAGE_API_KEY`
- **Value**: Your Voyage AI API key

### Adding CODECOV_TOKEN
- **Name**: `CODECOV_TOKEN`
- **Value**: Your Codecov upload token

## CI/CD Behavior

### Without Secrets (Default)
- CI runs **non-LLM tests only**: `pytest -m "not requires_llm"`
- All basic functionality tests pass
- No API costs incurred
- No coverage reports uploaded to Codecov

### With Secrets
- CI can run **full test suite**: `pytest` (all tests)
- LLM integration tests execute
- API costs are incurred (approximately $0.10-0.50 per CI run)
- Coverage reports uploaded to Codecov

## Local Development

For local development, create a `.env` file from `.env.example`:

```bash
cp .env.example .env
# Edit .env and add your real API keys
```

Your local `.env` file is gitignored and will never be committed.

## Security Best Practices

1. **Never commit API keys** to the repository
2. **Rotate keys regularly** if you suspect they've been exposed
3. **Use separate keys** for CI/CD vs local development
4. **Monitor API usage** in Anthropic and Voyage AI dashboards
5. **Set spending limits** in provider dashboards to prevent unexpected costs

## Cost Considerations

If you configure real API keys for CI:
- Each CI run with LLM tests costs approximately **$0.10-0.50**
- Consider using the **AI_OVERRIDE** feature to use cheaper models for testing
- Limit LLM test runs to main branch or release branches

## Troubleshooting

### CI is failing with "ANTHROPIC_API_KEY not set"
- **Solution**: This shouldn't happen anymore. The code now allows empty API keys for non-LLM tests. If you're seeing this, please report it as a bug.

### Coverage reports not appearing on Codecov
- **Solution**: Add the `CODECOV_TOKEN` secret. This is optional and doesn't block CI.

### I want to run LLM tests in CI
- **Solution**: Add `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY` secrets, then update the workflow to run `pytest` instead of `pytest -m "not requires_llm"`.

## Questions?

If you have questions about configuring secrets, please open an issue or contact the maintainers.
