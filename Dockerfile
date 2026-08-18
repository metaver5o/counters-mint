# Stage 1: Build Svelte 5 frontend
FROM node:22-slim AS frontend
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
# vite outputs to ../counters_proto/server/static (emptyOutDir:false, keeps existing assets)
COPY counters_proto/server/static/ /build/counters_proto/server/static/
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim
WORKDIR /app

COPY pyproject.toml .
COPY counters_proto/ counters_proto/
COPY --from=frontend /build/counters_proto/server/static/ counters_proto/server/static/

RUN pip install --no-cache-dir -e .

ENV COUNTER_DATA_DIR=/data
ENV PYTHONUNBUFFERED=1

ARG GIT_COMMIT=dev
ENV COUNTER_GIT_COMMIT=$GIT_COMMIT

EXPOSE 8082
VOLUME ["/data"]

ENTRYPOINT ["counters-proto"]
CMD ["server", "--host", "0.0.0.0", "--port", "8082"]
