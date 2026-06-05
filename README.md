# WCP Widget — Docker

A [Widget Context Protocol (WCP)](https://widgetcontextprotocol.com) widget container
that brings Docker management into any WCP-compatible dashboard. Monitor and control
containers and images on your local machine and remote NAS, browse your Docker Hub
repositories, and configure credentials — all without leaving your dashboard.

**Specification:** [widgetcontextprotocol.com](https://widgetcontextprotocol.com)  
**Part of the** [Penrith Beacon WCP](https://penrithbeacon.com) widget suite.

> **WCP 2.1.0 certified.** This widget implements the full
> [Widget Context Protocol 2.1.0](https://widgetcontextprotocol.com) specification,
> including Container Directory (`GET /wcp`), all `Wcp-*` request headers,
> context-scoped state isolation, JSON-LD structured data, `wcp:ready` / `wcp:context`
> postMessage signals, and Publish to Web (`POST /widget/publish`).

---

## Components

All four components are sized at `12 × 6` by default — a full stave in standard
Penrith Beacon WCP layout. Each can be placed independently on separate staves or
combined in any arrangement.

| Component | Default size | What it shows |
|-----------|:------------:|---------------|
| **Local Docker** | 12 × 6 | Containers (left) and images (right) on the local machine. Start / stop / restart per container row. |
| **NAS Docker** | 12 × 6 | Containers (left) and images (right) on a remote NAS running [wcp-docker-agent](https://github.com/penrithbeacon/wcp-docker-agent). Start / stop / restart per container row. |
| **Docker Hub** | 12 × 6 | Lists all `penrithbeacon/wcp-widget-*` repositories auto-discovered from Docker Hub. Click any repo to see its tags, sizes, and dates. Open on Docker Hub or GitHub in one click. |
| **Settings** | 12 × 6 | NAS agent URL and Bearer token, optional Docker Hub PAT. Test connection button. |

All cards use sticky headers with refresh buttons and themed scrollbars throughout.

---

## Requirements

- Docker and Docker Compose
- For NAS Docker: [wcp-docker-agent](https://github.com/penrithbeacon/wcp-docker-agent) running on your NAS

---

## Quick Start

```bash
docker run -d \
  --name wcp-widget-docker \
  -p 3744:3744 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v docker_data:/app/data \
  --restart unless-stopped \
  penrithbeacon/wcp-widget-docker:latest
```

Then add it to your WCP dashboard at `http://localhost:3744`.

---

## Docker Compose

```yaml
services:
  docker-widget:
    image: penrithbeacon/wcp-widget-docker:latest
    container_name: wcp-widget-docker
    ports:
      - "3744:3744"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:rw
      - docker_data:/app/data
    restart: unless-stopped

volumes:
  docker_data:
```

> The Docker socket mount (`/var/run/docker.sock`) is required for the Local Docker
> instrument to list and control containers on the host machine.

---

## NAS Docker Setup

The NAS Docker instrument connects to a lightweight authenticated proxy —
[`wcp-docker-agent`](https://github.com/penrithbeacon/wcp-docker-agent) — that you
deploy on your NAS. It exposes your NAS Docker socket over HTTP protected by a
Bearer token.

**Deploy the agent on your NAS:**

```yaml
services:
  wcp-docker-agent:
    image: penrithbeacon/wcp-docker-agent:latest
    container_name: wcp-docker-agent
    ports:
      - "3745:3745"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:rw
      - agent_data:/app/data
    restart: unless-stopped

volumes:
  agent_data:
```

**Get the Bearer token:**

```bash
docker logs wcp-docker-agent
# [wcp-docker-agent] *** Bearer token (save this): <token> ***
```

**Configure the widget:** Open the **Settings** instrument and paste the agent URL
(e.g. `http://nas.local:3745`) and token, then click **Save**.

---

## Docker Hub Instrument

The Docker Hub instrument auto-discovers all repositories under the `penrithbeacon`
namespace using the public Docker Hub v2 API — no token required. New containers
automatically appear as they are published.

Optionally set a Docker Hub PAT in Settings to view pull counts for private images.

---

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /wcp` | GET | WCP 2.1.0 Container Directory |
| `GET /widget/` | GET | Widget index page |
| `GET /widget/wcp` | GET | WCP 2.1.0 manifest (includes `web.published`) |
| `GET /widget/health` | GET | `{"status":"ok","name":"Docker"}` |
| `GET /widget/icon.svg` | GET | Widget icon (SVG) |
| `GET /widget/local` | GET | Local Docker instrument (iframe) |
| `GET /widget/nas` | GET | NAS Docker instrument (iframe) |
| `GET /widget/hub` | GET | Docker Hub instrument (iframe) |
| `GET /widget/settings` | GET | Settings instrument (iframe) |
| `GET /widget/api/local/containers` | GET | Local container list (15 s cache) |
| `GET /widget/api/local/images` | GET | Local image list (15 s cache) |
| `POST /widget/api/local/containers/<id>/<action>` | POST | Start / stop / restart local container |
| `GET /widget/api/nas/containers` | GET | NAS container list via agent (15 s cache) |
| `GET /widget/api/nas/images` | GET | NAS image list via agent (15 s cache) |
| `POST /widget/api/nas/containers/<id>/<action>` | POST | Start / stop / restart NAS container |
| `GET /widget/api/hub/repos` | GET | Docker Hub repo list for `penrithbeacon` (15 s cache) |
| `GET /widget/api/hub/repos/<name>/tags` | GET | Tags for a specific Docker Hub repo (15 s cache) |
| `GET /widget/api/settings` | GET | Current settings (tokens masked) |
| `POST /widget/api/settings` | POST | Update settings |
| `GET /widget/api/guids` | GET | Component UUIDs for Bonjour discovery |
| `GET /widget/export.wcp` | GET | Self-export as a `.wcp` package |
| `GET /` | GET | Published SPA (if present, else 404) |
| `POST /widget/publish` | POST | Publish SPA HTML to container root |
| `DELETE /widget/publish` | DELETE | Remove published SPA |

---

## WCP Request Headers

| Header | Description |
|--------|-------------|
| `Wcp-Instance-Id` | UUID identifying this widget instance |
| `Wcp-Dashboard-Id` | UUID identifying the requesting dashboard |
| `Wcp-Version` | Protocol version the dashboard speaks |
| `Wcp-Widget-Id` | Widget ID from Container Directory selection |
| `Wcp-Orchestration-Id` | UUID of the active orchestration |
| `Wcp-Application-Id` | UUID of the active application window (kiosk only) |

---

## Data Storage

Settings (NAS agent URL, tokens) are stored in `/app/data/settings.json` inside the
Docker volume. Tokens are never logged or exposed in responses — GET `/widget/api/settings`
returns masked values (`••••••••`) and a `_set: true/false` flag.

---

## WCP Compatibility

| Property | Value |
|----------|-------|
| WCP Version | 2.1.0 |
| Widget Version | 1.0.0 |
| Render mode | iframe |
| Auth | none (credentials stored server-side) |
| Default card size | 12 × 6 |

---

## Technical Details

- **Base image:** `python:3.12-slim`
- **Port:** `3744`
- **Framework:** Flask
- **Dependencies:** Flask, requests, docker (Python SDK)
- **Docker socket:** mounted at `/var/run/docker.sock:rw` for local container access
- **Persistent storage:** Named Docker volume for settings

---

## Links

- [Penrith Beacon](https://penrithbeacon.com)
- [Widget Context Protocol specification](https://widgetcontextprotocol.com)
- [wcp-docker-agent](https://github.com/penrithbeacon/wcp-docker-agent) — NAS proxy agent
- [Docker Hub — penrithbeacon/wcp-widget-docker](https://hub.docker.com/r/penrithbeacon/wcp-widget-docker)
