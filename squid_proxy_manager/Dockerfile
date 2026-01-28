# Squid Proxy Manager Add-on Dockerfile
ARG BUILD_FROM
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

# Copy application files
COPY rootfs /

# Set permissions
RUN chmod a+x /app/run.sh \
    && chmod a+x /app/main.py

# Labels
LABEL \
    io.hass.name="Squid Proxy Manager" \
    io.hass.description="Manage multiple Squid proxy instances" \
    io.hass.type="addon" \
    io.hass.version="1.0.0"
