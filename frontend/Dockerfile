# Development Dockerfile for SvelteKit Frontend
FROM node:20-alpine

WORKDIR /app

# Copy package files first
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:5173 || exit 1

# Run dev server with host 0.0.0.0 to allow external connections
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
