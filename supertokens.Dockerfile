# SuperTokens Core 10.1.4 (compatible with Python SDK 0.30.x - CDI 5.3)
# Core 10.x adds WebAuthn/Passkeys support matching Python SDK 0.30.x
FROM registry.supertokens.io/supertokens/supertokens-postgresql:10.1.4

# Install curl for healthcheck
USER root
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
USER supertokens
