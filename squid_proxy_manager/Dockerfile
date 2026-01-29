# Squid Proxy Manager Add-on Dockerfile
ARG BUILD_FROM=homeassistant/aarch64-base:latest
FROM ${BUILD_FROM}

# Set working directory
WORKDIR /app

# Install dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    docker-cli \
    openssl \
    bash \
    curl \
    && pip3 install --no-cache-dir \
    docker>=6.0.0 \
    cryptography>=41.0.0 \
    bcrypt>=4.0.0 \
    aiohttp

# Copy application files (including Dockerfile.squid)
COPY rootfs/ /
COPY Dockerfile.squid /app/Dockerfile.squid

# Set permissions
RUN chmod a+x /run.sh \
    && chmod a+x /app/main.py \
    && chmod a+x /app/proxy_manager.py \
    && chmod a+x /app/squid_config.py \
    && chmod a+x /app/cert_manager.py \
    && chmod a+x /app/auth_manager.py \
    && chmod a+x /app/build_squid_image.sh \
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
    io.hass.version="1.0.24"
