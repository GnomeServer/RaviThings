# Stage 1: Build SvelteKit
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY --from=frontend-build /app/frontend/build /app/frontend/build

ENV DB_PATH=/data/doe_contracts.db
ENV GRAPH_PATH=/data/graph.pkl
ENV CHROMA_PATH=/data/chroma_db
ENV OLLAMA_HOST=http://host.docker.internal:11434
ENV OLLAMA_MODEL=dolphin3
ENV STATIC_DIR=/app/frontend/build

EXPOSE 8000
CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000"]
