# Interview Coach in a container.
# Build:  docker build -t interview-coach .
# Run:    docker run --rm -p 8501:8501 -v interview-coach-data:/data --env-file .env interview-coach
# Demo:   docker run --rm -p 8501:8501 interview-coach

# 1. Start from a small official Python 3.11 image (Linux)
FROM python:3.11-slim

# 2. Settings used inside the container
#    DATA_DIR / BACKUP_FOLDER: keep progress.db and backups in /data (a volume that survives restarts)
#    OLLAMA_HOST: Ollama runs on your computer, not in the container, so point at the host
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data \
    BACKUP_FOLDER=/data/backups \
    OLLAMA_HOST=http://host.docker.internal:11434

WORKDIR /app

# 3. Install packages first, so this slow step is cached when only the code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the app (.dockerignore keeps out .env, databases and the venv)
COPY . .

# 5. Run as a normal user, not root, and give it the /data folder
RUN useradd --create-home coach && mkdir -p /data && chown coach /data
USER coach

# 6. Streamlit listens on port 8501
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
