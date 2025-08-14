# Base image
FROM python:3.11-slim

# Prevent Python from writing .pyc files & using stdin buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System deps (optional but helpful for reportlab fonts)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libfreetype6-dev \
    libjpeg62-turbo-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Copy requirement spec first for layer caching
COPY requirements.txt /app/requirements.txt

# Install Python deps
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy app
COPY . /app

# Expose the port Hugging Face expects
EXPOSE 7860

# Start Streamlit on the expected interface/port
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
