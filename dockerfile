##############################################################################
# Dockerfile — LINE Insurance Claim Bot
#
# 12-Factor notes:
#   V.   Build/Release/Run — dependencies pinned in requirements.txt; image is
#        the release artifact; config injected at run-time, never baked in.
#   IX.  Disposability     — fast start; SIGTERM handled by uvicorn gracefully.
##############################################################################

FROM python:3.11-slim

# Install system dependencies only (no dev tools in image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
 && update-ca-certificates \
 && rm -rf /var/lib/apt/lists/*

ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python dependencies (layer-cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Persistent data volume mount point (12-Factor: backing service / attachment)
VOLUME ["/data"]

# Expose port (12-Factor VII — port binding)
EXPOSE 8000

# Entrypoint handles optional git-pull, data-dir init, and then launches uvicorn
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
