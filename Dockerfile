FROM python:3.11-slim

# Install system dependencies first
RUN apt-get update && apt-get install -y \
    libx11-6 \
    libx11-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    cmake \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Force dlib to compile from source against the libs above
RUN pip install --upgrade pip && \
    pip install --no-binary dlib dlib && \
    pip install -r requirements.txt

COPY . .

CMD ["python", "app.py"]