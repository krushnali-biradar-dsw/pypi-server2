# Built from the root repository context
FROM python:3.10-slim

WORKDIR /app

# 1. Copy the strictly necessary build files
COPY component/requirements.txt /app/

# Build arguments for offline / private index configuration
ARG PYPI_INDEX_URL="http://host.docker.internal:8080/simple"
ARG OFFLINE_FIND_LINKS=""

# Optional copy of pyrepo if building via local folders (fallback)
# Using a wildcard copy makes this step optional and non-blocking if pyrepo doesn't exist
COPY pyrepo* /app/pyrepo/

# 2. STRICT OFFLINE INSTALL: Disable internet access for pip
# If OFFLINE_FIND_LINKS is set, use find-links. Otherwise, use the private local PyPI server.
# Using --index-url and no other options guarantees pip never accesses public PyPI.
RUN pip install --no-cache-dir --upgrade pip && \
    if [ -n "$OFFLINE_FIND_LINKS" ]; then \
      echo "Installing from local directory: $OFFLINE_FIND_LINKS" && \
      pip install --no-cache-dir --no-index --find-links=$OFFLINE_FIND_LINKS -r requirements.txt; \
    else \
      echo "Installing from private PyPI index: $PYPI_INDEX_URL" && \
      pip install --no-cache-dir --index-url $PYPI_INDEX_URL --trusted-host $(echo $PYPI_INDEX_URL | sed -E 's|https?://([^/:]+).*|\1|') -r requirements.txt; \
    fi

# Clean up any copied package directories inside the container to secure the image
RUN rm -rf /app/pyrepo

# 3. Copy ONLY the Pyarmor obfuscated code, never the raw source
COPY dist/ /app/

ENV PYTHONUNBUFFERED=1
ENV AIR_GAPPED=true

CMD ["python", "main.py"]