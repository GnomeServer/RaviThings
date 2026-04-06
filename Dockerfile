FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY test_atlas_server.py .
COPY backend/ backend/
COPY osint/ osint/
COPY frontend/ frontend/

# Copy data files
COPY RED_TEAM_PROMPT.json .

# Runtime config
ENV PORT=8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "test_atlas_server.py"]
