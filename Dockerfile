# syntax=docker/dockerfile:1
ARG TARGETPLATFORM
ARG VERSION=latest
ARG BASE_VERSION=${VERSION}

FROM python:3.12-slim AS builder

# Copy uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

VOLUME /cert

# Set environment variables for SSL certificate verification
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Create non-root user
RUN groupadd -r genai && useradd -r -g genai -d /app -s /bin/bash genai

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY main.py ./
COPY src/ ./src/

# Set ownership of app directory to genai user
RUN chown -R genai:genai /app

# Install dependencies as non-root
USER genai
RUN uv sync --frozen --no-cache

# Return to root so entrypoint can manage certs, then it will drop privileges
USER root

# Set Python path
ENV PYTHONPATH=/app/src

# Expose ports
EXPOSE 8080 8081

# Add runtime entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uv", "run", "kopf", "run", "main.py", "--all-namespaces", "--liveness", "http://0.0.0.0:8080/healthz", "--standalone"]
