# syntax=docker/dockerfile:1
ARG TARGETPLATFORM
ARG VERSION=latest
ARG BASE_VERSION=${VERSION}

FROM python:3.12-slim AS builder

# Copy uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN mkdir -p /cert/

VOLUME /cert

RUN cp /cert/* /usr/local/share/ca-certificates/
RUN update-ca-certificates

# Set environment variables for SSL certificate verification
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Create non-root user for security early
RUN groupadd -r genai && useradd -r -g genai -d /app -s /bin/bash genai

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY main.py ./
COPY src/ ./src/

# Set ownership of app directory to genai user
RUN chown -R genai:genai /app

# Switch to non-root user before installing dependencies
USER genai

# Install dependencies using uv as the genai user
RUN uv sync --frozen --no-cache

# Set Python path
ENV PYTHONPATH=/app/src

# Expose ports
EXPOSE 8080 8081

CMD ["uv", "run", "kopf", "run", "main.py", "--all-namespaces", "--liveness", "http://0.0.0.0:8080/healthz", "--standalone"]
