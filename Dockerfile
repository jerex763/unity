FROM node:22-bookworm-slim AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim AS python-build

ENV PATH="/opt/venv/bin:${PATH}"
RUN python -m venv /opt/venv
COPY backend/ /build/backend/
RUN pip install --no-cache-dir "/build/backend[prod]"


FROM python:3.12-slim AS runtime

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

RUN groupadd --system unity \
    && useradd --system --gid unity --home-dir /app --shell /usr/sbin/nologin unity

WORKDIR /app/backend
COPY --from=python-build /opt/venv /opt/venv
COPY backend/ ./
COPY --from=frontend-build /build/frontend/dist ./frontend_dist
COPY ops/deploy/start.sh /app/ops/start.sh

RUN DJANGO_SECRET_KEY=build-only-secret \
    DATABASE_URL=postgresql://build:build@localhost/build \
    DJANGO_ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput \
    && chmod 755 /app/ops/start.sh \
    && chown -R unity:unity /app

USER unity
EXPOSE 10000

ENTRYPOINT ["/app/ops/start.sh"]
