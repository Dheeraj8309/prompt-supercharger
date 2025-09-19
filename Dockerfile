# Use slim Python base image
FROM python:3.11-slim

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install build essentials only for compilation, then clean up
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for Docker caching)
COPY requirements.txt /tmp/requirements.txt

# Install dependencies (CPU-only PyTorch to save space)
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    torch==2.3.1+cpu torchvision==0.18.1+cpu torchaudio==2.3.1+cpu \
    -f https://download.pytorch.org/whl/cpu/torch_stable.html \
 && pip cache purge

# Copy app code
COPY . .

# Expose the port Flask will run on
EXPOSE 8080

# Start the app with Gunicorn (production WSGI server)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
