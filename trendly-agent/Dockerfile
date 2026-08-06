# --- Stage 1: build the React frontend ---
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
# vite.config.js builds straight into ../static, i.e. /static at this stage

# --- Stage 2: Python backend + built frontend ---
FROM python:3.11-slim
WORKDIR /app

# Keep image lean; sentence-transformers needs a C compiler for some deps on
# certain platforms, but prebuilt wheels cover this on standard linux/amd64.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY --from=frontend-build /app/frontend/dist ./static

# Persist SQLite outside the image layer via a mounted volume in production
ENV TRENDLY_DB_PATH=/app/data/data_store.sqlite3
RUN mkdir -p /app/data

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
