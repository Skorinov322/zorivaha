# Deploy to Yandex Cloud with Docker

## 1. Copy env file

On the server, inside the project directory:

```bash
cp .env.prod.example .env
nano .env
```

Replace:

- `SECRET_KEY`
- `POSTGRES_PASSWORD`
- password inside `DATABASE_URL`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`

For first launch by IP only:

```env
ALLOWED_HOSTS=YOUR_SERVER_IP
CSRF_TRUSTED_ORIGINS=http://YOUR_SERVER_IP
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
```

After HTTPS is configured for a domain, set `SESSION_COOKIE_SECURE=True` and
`CSRF_COOKIE_SECURE=True`.

## 2. Start containers

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## 3. Prepare database

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
docker compose -f docker-compose.prod.yml exec web python manage.py createcachetable
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

## 4. Check status

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f web
```

Open:

```text
http://YOUR_SERVER_IP:8000
```

After nginx is configured, open:

```text
http://YOUR_SERVER_IP
```

## 5. Useful commands

Restart:

```bash
docker compose -f docker-compose.prod.yml restart
```

Stop:

```bash
docker compose -f docker-compose.prod.yml down
```

Backup PostgreSQL:

```bash
docker compose -f docker-compose.prod.yml exec db pg_dump -U zorivaha_user zorivaha > backup.sql
```
