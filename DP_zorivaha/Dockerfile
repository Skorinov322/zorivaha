# Stage 1: builder
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements/base.txt requirements/base.txt
COPY requirements/dev.txt  requirements/dev.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements/dev.txt


# Stage 2: runtime
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    default-mysql-client curl fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

WORKDIR /app

COPY . .

RUN mkdir -p /app/staticfiles /app/media /app/logs

ENV DJANGO_SETTINGS_MODULE=config.settings.dev
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
