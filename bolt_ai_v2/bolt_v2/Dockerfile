FROM python:3.11-slim

LABEL maintainer="Bolt AI Content Creator v2.2"

# System deps: ffmpeg for video, curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    python -c "import nltk; nltk.download('punkt',quiet=True); \
               nltk.download('stopwords',quiet=True); \
               nltk.download('vader_lexicon',quiet=True)"

COPY code/ ./code/
COPY scripts/ ./scripts/

# Create runtime directories
RUN mkdir -p logs data/queue data/published data/analytics data/backups \
             content/audio content/video content/thumbnails assets

EXPOSE 8000

# Default: start the API server
# Override with: docker-compose run pipeline python3 code/content_automation_master.py --schedule
CMD ["uvicorn", "code.api:app", "--host", "0.0.0.0", "--port", "8000"]
