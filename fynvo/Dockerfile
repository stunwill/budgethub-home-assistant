FROM node:22-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json ./package.json
RUN npm install
COPY frontend ./
RUN npm run build

ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-python:3.12-alpine3.20
FROM ${BUILD_FROM}

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY --from=frontend-builder /frontend/dist /app/frontend/dist

ENV PYTHONUNBUFFERED=1
ENV FYNVO_DATA_DIR=/data

EXPOSE 8097

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8097"]
