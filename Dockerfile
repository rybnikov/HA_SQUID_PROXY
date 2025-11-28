ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.19
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV LANG C.UTF-8

RUN apk add --no-cache squid apache2-utils python3 py3-pip openssl ca-certificates jq

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY app /app
COPY run.sh /run.sh
RUN chmod +x /run.sh

EXPOSE 3128

CMD ["/run.sh"]
