FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Minimal OS deps
RUN apt-get update && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# Install only small runtime deps
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && pip cache purge

# App source
COPY . .

# Non-root
RUN useradd -m appuser
USER appuser

EXPOSE 8080

# Single worker to minimize memory; bind to $PORT on Render, 8080 locally
CMD ["bash","-lc","exec gunicorn -w 1 -k gthread --threads 8 --timeout 120 -b 0.0.0.0:${PORT:-8080} app:app"]
