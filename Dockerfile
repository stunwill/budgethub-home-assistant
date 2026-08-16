ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-python:3.12-alpine3.20
FROM ${BUILD_FROM}

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend

ENV PYTHONUNBUFFERED=1
ENV BUDGETHUB_DATA_DIR=/data

EXPOSE 8097

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8097"]
