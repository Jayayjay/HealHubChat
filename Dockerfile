FROM python:3.11-slim-bookworm  # Debian base per prior

WORKDIR /app

# Install system deps + llama.cpp build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    cmake \
    && git clone https://github.com/ggerganov/llama.cpp && \
    cd llama.cpp && make -j && cd .. && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Models dir (assume model in repo via git LFS or download in entrypoint)
RUN mkdir -p /models

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]