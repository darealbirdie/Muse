<<<<<<< HEAD
FROM python:3.9-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    python3-pyaudio \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "muse.py"]
=======
FROM python:3.9-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    python3-pyaudio \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "muse.py"]
>>>>>>> 8cb2224a06ea476519007e91777e55e915b74ae8
