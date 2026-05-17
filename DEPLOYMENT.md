# VPS Docker Compose Deployment

This repository can be deployed as a single FastAPI app that also serves the built frontend.

## What it does

- Builds the frontend with Vite
- Copies `frontend/dist` into the runtime image
- Runs FastAPI with Uvicorn
- Uses Nginx as the public entry point on port 80
- Persists SQLite data in `./data`
- Persists uploaded/generated media in `./backend/media`

## Local build

```bash
docker compose up -d --build
docker-compose up -d --build

```

## Production notes

- Put this repo on your VPS
- Make sure Docker and Docker Compose are installed
- Point the DNS A record for `exam.791127.xyz` to your VPS public IP
- Open port 80 in your firewall
- If you want HTTPS, add a TLS-enabled Nginx or use a reverse proxy in front of this stack

## Important paths

- Database: `./data/word_exam_bank.db`
- Media files: `./backend/media`
- Public site: `http://exam.791127.xyz/`
