# Squid Proxy Manager Add-on Dockerfile
ARG BUILD_ARCH=aarch64
ARG BUILD_FROM=homeassistant/${BUILD_ARCH}-base:latest

FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# hadolint ignore=DL3006
FROM ${BUILD_FROM}

# Set working directory
WORKDIR /app

# Install dependencies
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
RUN pip3 install --no-cache-dir \
    aiohttp==3.13.3 \
    aiolimiter==1.2.1 \
    cryptography==46.0.4 \
    bcrypt==5.0.0

# Create necessary directories for Squid
RUN mkdir -p /var/cache/squid /var/log/squid /etc/squid/ssl_cert \
    && chown -R squid:squid /var/cache/squid /var/log/squid /etc/squid/ssl_cert

# Copy application files
COPY rootfs/ /
COPY --from=frontend-build /frontend/dist /app/static

# Set permissions
RUN chmod a+x /app/main.py \
    && chmod a+x /app/proxy_manager.py \
    && chmod a+x /app/squid_config.py \
    && chmod a+x /app/cert_manager.py \
    && chmod a+x /app/auth_manager.py \
    && chmod a+x /etc/services.d/squid-proxy-manager/run \
    && chmod a+x /etc/services.d/squid-proxy-manager/finish \
    && mkdir -p /data/squid_proxy_manager \
    && chown -R 1000:1000 /app /etc/services.d /data/squid_proxy_manager \
    && chmod -R go-w /app /etc/services.d

# Ensure app directory is in Python path
ENV PYTHONPATH=/app

# Labels
LABEL \
    io.hass.name="Squid Proxy Manager" \
    io.hass.description="Manage multiple Squid proxy instances" \
    io.hass.type="addon" \
    io.hass.version="1.3.1"
