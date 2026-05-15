# GitLab Webhook Live Dashboard (Python + FastAPI)

A complete webhook receiver and UI dashboard for GitLab events.

## Features

- CORS-enabled webhook API endpoint
- Optional GitLab token verification
- Live event stream with WebSocket updates
- Dynamic dashboard with:
  - Total events
  - Live WebSocket client count
  - Event type counts
  - Source counts
  - Recent webhook logs
- Dockerized runtime with Docker Compose

## Project Structure

```text
.
|-- app/
|   |-- main.py
|   `-- store.py
|-- static/
|   |-- index.html
|   |-- styles.css
|   `-- app.js
|-- .env.example
|-- .gitignore
|-- Dockerfile
|-- docker-compose.yml
|-- requirements.txt
`-- README.md
```

## 1) Local Run (Python)

### Prerequisites

- Python 3.11+ (3.12 recommended)

### Setup

```bash
# from project root
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

### Start server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Open dashboard

- UI: `http://localhost:8000/`
- Health: `http://localhost:8000/health`
- Logs API: `http://localhost:8000/api/logs`

## 2) Docker Run

### Prerequisites

- Docker
- Docker Compose

### Setup and start

```bash
# from project root
copy .env.example .env
docker compose up --build -d
```

### Stop

```bash
docker compose down
```

### Access

- UI: `http://localhost:8000/`
- API: `http://localhost:8000/webhook/gitlab`

## 3) Environment Configuration

Create `.env` from `.env.example` and adjust:

```env
CORS_ALLOW_ORIGINS=*
WEBHOOK_SECRET=replace-me
MAX_EVENTS=1000
```

### Notes

- `CORS_ALLOW_ORIGINS` supports comma-separated origins.
  - Example: `http://localhost:3000,http://localhost:5173`
- If `WEBHOOK_SECRET` is set, incoming header `X-Gitlab-Token` must match.
- `MAX_EVENTS` controls in-memory retention limit.

## 4) GitLab Webhook Configuration

1. In GitLab, open your project.
2. Go to **Settings -> Webhooks**.
3. Set **URL**:
   - `http://<your-host>:8000/webhook/gitlab`
4. Set **Secret token**:
   - Use the same value as `WEBHOOK_SECRET` in `.env`.
5. Select trigger events (recommended):
   - Push events
   - Merge request events
   - Tag push events
   - Pipeline events
6. Save webhook.
7. Click **Test** and choose an event.
8. Verify dashboard updates at `http://<your-host>:8000/`.

## 5) Local Testing with curl

### Windows PowerShell example

```powershell
$body = @{
  object_kind = "push"
  event_name = "push"
  user_name = "Demo User"
  user_username = "demo"
  project = @{
    name = "sample-project"
    path_with_namespace = "group/sample-project"
    web_url = "https://gitlab.example.com/group/sample-project"
  }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Uri "http://localhost:8000/webhook/gitlab" `
  -Method Post `
  -Headers @{ "X-Gitlab-Event" = "Push Hook"; "X-Gitlab-Token" = "replace-me" } `
  -ContentType "application/json" `
  -Body $body
```

## 6) Exposing Localhost to GitLab (Optional)

If GitLab cannot reach your local machine:

- Use a tunnel (for example, ngrok or cloudflared)
- Point GitLab webhook URL to your HTTPS tunnel endpoint
- Keep path as `/webhook/gitlab`

## 7) Production Considerations

- Run behind reverse proxy (Nginx/Traefik/Caddy)
- Restrict CORS origins
- Use a strong webhook secret
- Add persistent storage if long-term log history is required
- Add authentication if dashboard is exposed publicly
