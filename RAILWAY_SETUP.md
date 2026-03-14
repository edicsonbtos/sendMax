# Sendmax Monorepo Deployment Guide (Railway)

This repository is a monorepo containing multiple separate applications. Because of this, it is critical that they are deployed as separate services in Railway to avoid routing conflicts (like `404 Not Found` errors) and dependency issues.

## 1. Create a New Service for Each Application
You will need to create separate services within your Railway Project pointing to this exact same GitHub repository, but with different configurations.

### Service 1: Sendmax Bot & Public API
This is the main Telegram bot and the API consumed by the operator tools.
- **Source:** GitHub Repo (`sendmax-bot`)
- **Root Directory:** `/` (leave empty or set to root)
- **Environment Variables Required:**
  - `TELEGRAM_BOT_TOKEN`
  - `DATABASE_URL`
  - `WEBHOOK_URL` (The public URL of this specific Railway service)
  - `PORT` (Provided by Railway)
- **Start Command:** `uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8080}`

### Service 2: Backoffice API
This is the protected HTTP backend used by the Admin panel.
- **Source:** GitHub Repo (`sendmax-bot`)
- **Root Directory:** `/backoffice_api`
- **Environment Variables Required:**
  - `DATABASE_URL`
  - `SECRET_KEY` (or `JWT_SECRET`)
  - `BACKOFFICE_API_KEY`
  - `ALLOWED_ORIGINS` (Comma-separated list of allowed frontend URLs, e.g., `https://backoffice.midominio.com,http://localhost:3000`)
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}` (Defined in its Dockerfile)

### Service 3: Backoffice Web (Admin Panel)
This is the Next.js frontend for administrators.
- **Source:** GitHub Repo (`sendmax-bot`)
- **Root Directory:** `/backoffice_web`
- **Environment Variables Required:**
  - `NEXT_PUBLIC_API_URL`: **Must point directly to the URL of Service 2 (Backoffice API).** Do not point this to the bot's URL.

### Service 4: Operator Web (If applicable)
This is the frontend used by operators.
- **Source:** GitHub Repo (`sendmax-bot`)
- **Root Directory:** `/operator-web`
- **Environment Variables Required:**
  - Update any environment variables to point to the correct public API endpoints (Service 1) if necessary.

## 2. Important Checks
- **CORS:** Ensure `ALLOWED_ORIGINS` in the Backoffice API matches the actual URL assigned by Railway to your Backoffice Web service.
- **Healthchecks:**
  - Bot API: Visit `https://<bot-url>/health` -> Should return `{"status": "ok", "service": "sendmax-bot"}`.
  - Backoffice API: Visit `https://<backoffice-url>/health` -> Should return a detailed JSON with `{"ok": true, ... "service": "backoffice-api"}`.
