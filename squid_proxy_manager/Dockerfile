# Squid Proxy Manager Add-on Dockerfile
# PRODUCTION IMAGE - Minimal, lean, no test/dev tools
# Base: alpine (5MB) with only production dependencies

ARG BUILD_ARCH=aarch64
ARG BUILD_FROM=homeassistant/${BUILD_ARCH}-base:latest

# Frontend build stage - separate, discarded in final image
FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci && npm cache clean --force
COPY frontend/ .
RUN npm run build && rm -rf node_modules

# Production stage - minimal, lean
# hadolint ignore=DL3006
FROM ${BUILD_FROM}

# Metadata
LABEL \
    io.hass.name="Squid Proxy Manager" \
    io.hass.description="Manage multiple Squid proxy instances" \
    io.hass.type="addon" \
    io.hass.version="1.4.5"

# Set working directory
WORKDIR /app

# Install ONLY production dependencies (no dev tools)
# hadolint ignore=DL3018
RUN apk add --no-cache \
    python3 \
    py3-pip \
    openssl \
    bash \
    curl \
    squid

# Ensure non-root user exists for running the app
RUN addgroup -g 1000 -S app 2>/dev/null || true \
    && adduser -S -D -u 1000 -G app app 2>/dev/null || true

# Install Python production dependencies only (no dev/test packages)
RUN pip3 install --no-cache-dir \
    aiohttp==3.13.3 \
    aiolimiter==1.2.1 \
    cryptography==46.0.4 \
    bcrypt==5.0.0

# Create necessary directories for Squid
RUN mkdir -p /var/cache/squid /var/log/squid /etc/squid/ssl_cert \
    && chown -R squid:squid /var/cache/squid /var/log/squid /etc/squid/ssl_cert

# Copy application files (production only - no tests, no dev scripts)
COPY rootfs/ /
COPY --from=frontend-build /frontend/dist /app/static

# Set strict permissions for security
RUN chmod a+x /app/main.py \
    && chmod a+x /app/proxy_manager.py \
    && chmod a+x /app/squid_config.py \
    && chmod a+x /app/cert_manager.py \
    && chmod a+x /app/auth_manager.py \
    && chmod a+x /etc/services.d/squid-proxy-manager/run \
    && chmod a+x /etc/services.d/squid-proxy-manager/finish \
    && mkdir -p /data/squid_proxy_manager \
    && chown -R 1000:1000 /app /etc/services.d /data/squid_proxy_manager \
    && chmod -R go-w /app /etc/services.d \
    && chmod -R go-rx /data/squid_proxy_manager

# Ensure app directory is in Python path
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8099/health || exit 1
