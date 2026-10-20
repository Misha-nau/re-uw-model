FROM node:24-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 RE_UW_SCENARIOS_DIR=/data/scenarios RE_UW_FRONTEND_DIR=/app/frontend/dist
COPY backend/ ./backend/
RUN pip install --no-cache-dir ./backend
COPY scenarios/ ./seed-scenarios/
COPY --from=frontend /build/frontend/dist ./frontend/dist
COPY backend/deploy.py ./deploy.py
EXPOSE 1337
CMD ["python", "deploy.py"]
