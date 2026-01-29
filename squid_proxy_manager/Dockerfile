# Squid Proxy Manager Add-on Dockerfile
ARG BUILD_FROM=homeassistant/aarch64-base:latest
FROM ${BUILD_FROM}

# Set working directory
WORKDIR /app

# Install dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    openssl \
    bash \
    curl \
    squid \
    && pip3 install --no-cache-dir \
    cryptography>=41.0.0 \
    bcrypt>=4.0.0 \
    aiohttp

# Create necessary directories for Squid
RUN mkdir -p /var/cache/squid /var/log/squid /etc/squid/ssl_cert \
    && chown -R squid:squid /var/cache/squid /var/log/squid /etc/squid/ssl_cert

# Copy application files
COPY rootfs/ /

# Set permissions
RUN chmod a+x /app/main.py \
    && chmod a+x /app/proxy_manager.py \
    && chmod a+x /app/squid_config.py \
    && chmod a+x /app/cert_manager.py \
    && chmod a+x /app/auth_manager.py \
    && chmod a+x /etc/services.d/squid-proxy-manager/run \
    && chmod a+x /etc/services.d/squid-proxy-manager/finish \
    && mkdir -p /data/squid_proxy_manager

# Ensure app directory is in Python path
ENV PYTHONPATH=/app

# Labels
LABEL \
    io.hass.name="Squid Proxy Manager" \
    io.hass.description="Manage multiple Squid proxy instances" \
    io.hass.type="addon" \
    io.hass.version="1.1.11"
