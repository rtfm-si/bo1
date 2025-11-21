# SuperTokens Core 9.3.0 (compatible with Python SDK 0.29.x - CDI 5.2)
FROM registry.supertokens.io/supertokens/supertokens-postgresql:9.3.0

# Install curl for healthcheck
USER root
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
USER supertokens
