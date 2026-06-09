# Docker — Specification

## Overview
Docker management across local and NAS hosts, plus a Docker Hub browser. Four instruments: Local Docker, NAS Docker, Docker Hub, Settings.

- **Port:** 3744
- **Container:** `wcp-widget-docker`
- **Image:** `docker.io/penrithbeacon/wcp-widget-docker`

## Version
- **Widget:** 1.4.0
- **WCP:** 2.1.0
- **Docker tag:** `1.4.0-wcp2.1.0`

## Controls (HTML Templates)

| Template | Route | Purpose | Default Size |
|----------|-------|---------|--------------|
| widget.html | `/widget/` | Compact overview card | (compact) |
| local.html | `/widget/local` | Local Docker containers + images | 12×12 |
| nas.html | `/widget/nas` | NAS Docker containers + images | 12×12 |
| hub.html | `/widget/hub` | Docker Hub repository browser | 12×12 |
| settings.html | `/widget/settings` | NAS + Hub configuration | 12×12 |

## Components

| ID | Name | Role | Size |
|----|------|------|------|
| docker-local | Local Docker | widget | 12×12 |
| docker-nas | NAS Docker | widget | 12×12 |
| docker-hub | Docker Hub | widget | 12×12 |
| docker-settings | Docker Settings | widget | 12×12 |

## API Endpoints

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/wcp` | Container directory |
| GET | `/widget/wcp` | Widget manifest |
| GET | `/widget/index` | Widget index directory |
| GET | `/widget/` | Compact view |
| GET | `/widget/local` | Local Docker view |
| GET | `/widget/nas` | NAS Docker view |
| GET | `/widget/hub` | Docker Hub browser |
| GET | `/widget/settings` | Settings page |
| GET | `/widget/health` | Health check |
| GET | `/widget/icon.svg` | Widget icon |
| GET | `/widget/api/guids` | Component UUIDs |
| GET | `/widget/export.wcp` | WCP export package |
| GET | `/widget/api/local/containers` | List local containers |
| GET | `/widget/api/local/images` | List local images |
| POST | `/widget/api/local/containers/<cid>/<action>` | Container actions (start/stop/restart) |
| GET | `/widget/api/nas/containers` | List NAS containers |
| GET | `/widget/api/nas/images` | List NAS images |
| POST | `/widget/api/nas/test` | Test NAS connection |
| POST | `/widget/api/nas/containers/<cid>/<action>` | NAS container actions |
| GET | `/widget/api/hub/repos` | List Docker Hub repos |
| GET | `/widget/api/hub/repos/<name>/description` | Get repo description |
| GET | `/widget/api/hub/repos/<name>/tags` | List repo tags |
| GET/POST | `/widget/api/settings` | Get/save settings |
| POST | `/widget/publish` | Publish SPA |
| DELETE | `/widget/publish` | Remove published SPA |
| GET | `/` | Serve published SPA |

## Features
- Local Docker: containers list with start/stop/restart, images list
- NAS Docker: remote Docker management via docker-agent proxy
- Docker Hub: browse penrithbeacon repos, view tags, descriptions
- Settings: NAS host/port/token config, Docker Hub username
- Container status indicators (running/stopped/paused)
- Publish to Web support

## Configuration
- NAS connection settings (host, port, bearer token)
- Docker Hub username
- Persisted via `/widget/api/settings`

## Data Persistence
- Settings stored in container (uses Docker socket mount for local, HTTP for NAS)

## Dependencies
- Python: `flask`, `docker` (Docker SDK), `requests`
- Local: Docker socket (`/var/run/docker.sock`)
- Remote: docker-agent on NAS (port 3745)
- External API: Docker Hub API
