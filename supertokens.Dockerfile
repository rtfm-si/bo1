# Extend SuperTokens image to add curl for healthcheck
FROM registry.supertokens.io/supertokens/supertokens-postgresql:9.2.2

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
