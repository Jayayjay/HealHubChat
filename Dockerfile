FROM nvidia/cuda:12.1-runtime-ubuntu20.04

WORKDIR /app

# Use cache for apt with retry logic
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y \
    python3.11 \
    python3-pip \
    python3.11-venv \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create symlink for python3.11
RUN ln -sf /usr/bin/python3.11 /usr/bin/python3

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with cache and retry
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Copy app code (changes here break cache)
COPY . .

RUN mkdir -p models

EXPOSE 7860

# Set environment variable to enable GPU
ENV CUDA_VISIBLE_DEVICES=0

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]