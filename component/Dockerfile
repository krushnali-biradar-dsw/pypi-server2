# Built from the root repository context
FROM python:3.10-slim

WORKDIR /app

# 1. Copy the strictly necessary build files
COPY component/requirements.txt /app/

# 2. Copy the offline package repository
COPY pyrepo/ /app/pyrepo/

# 3. STRICT OFFLINE INSTALL: Disable internet access for pip
# We force pip to only look inside /app/pyrepo. If a package isn't there, the build FAILS.
RUN pip install --no-index --find-links=/app/pyrepo -r requirements.txt

# Clean up the repository cache to minimize image size
RUN rm -rf /app/pyrepo

# 4. Copy ONLY the Pyarmor obfuscated code, never the raw source
COPY dist/ /app/

CMD ["python", "main.py"]