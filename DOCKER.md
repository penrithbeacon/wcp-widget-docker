# WCP Widget: Docker

A [Widget Context Protocol (WCP)](https://widgetcontextprotocol.com) compliant widget
container that brings full Docker management into any WCP-compatible dashboard. Monitor
and control containers and images on your local machine and a remote NAS, browse your
Docker Hub repositories with inline rendered documentation, and manage credentials —
all without leaving the dashboard.

**Specification:** [widgetcontextprotocol.com](https://widgetcontextprotocol.com)

## Quick Start

```bash
docker run -d \
  --name wcp-widget-docker \
  -p 3744:3744 \
  -v /var/run/docker.sock:/var/run/docker.sock:rw \
  -v docker_data:/app/data \
  --restart unless-stopped \
  docker.io/penrithbeacon/wcp-widget-docker:latest
```

Then add it to your WCP dashboard at the container's network address.

## Docker Compose

```yaml
services:
  docker-widget:
    image: docker.io/penrithbeacon/wcp-widget-docker:latest
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

## Components

The widget exposes four components, each `12 × 6` by default (full stave in Penrith Beacon WCP):

| Component | What it shows |
|-----------|---------------|
| **Local Docker** | Containers and images on the local machine. Start / stop / restart per container. |
| **NAS Docker** | Containers and images on a remote NAS via [wcp-docker-agent](https://github.com/penrithbeacon/wcp-docker-agent). |
| **Docker Hub** | All `penrithbeacon` repositories. Tags sorted newest-first. Expandable inline documentation rendered from Docker Hub. Open on Docker Hub or GitHub in one click. |
| **Settings** | NAS agent URL and Bearer token configuration. Test connection validates before save. Optional Docker Hub PAT. |

## NAS Docker Setup

Deploy [wcp-docker-agent](https://github.com/penrithbeacon/wcp-docker-agent) on your NAS,
then paste its URL (`http://nas.local:3745`) and Bearer token into the Settings instrument.

```bash
# Get the Bearer token after deploying the agent
docker logs wcp-docker-agent
# [wcp-docker-agent] *** Bearer token (save this): <token> ***
```

## WCP Request Headers

This widget supports the WCP 2.1.0 request headers:

| Header | Required | Description |
|--------|----------|-------------|
| `Wcp-Instance-Id` | Required | UUID identifying this widget instance |
| `Wcp-Dashboard-Id` | Optional | UUID identifying the requesting dashboard |
| `Wcp-Version` | Optional | Protocol version the dashboard speaks |
| `Wcp-Widget-Id` | Optional | Widget ID from Container Directory selection |
| `Wcp-Orchestration-Id` | Optional | UUID of the active orchestration — shared state key for multi-component coordination |
| `Wcp-Application-Id` | Optional | UUID of the active application window (kiosk only) |

## WCP Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /wcp` | WCP 2.1.0 Container Directory |
| `GET /widget/` | Widget index — instrument selector |
| `GET /widget/wcp` | WCP 2.1.0 manifest |
| `GET /widget/health` | Health check |
| `GET /widget/icon.svg` | Widget icon (SVG) |
| `GET /widget/local` | Local Docker instrument page |
| `GET /widget/nas` | NAS Docker instrument page |
| `GET /widget/hub` | Docker Hub instrument page |
| `GET /widget/settings` | Settings instrument page |
| `GET /widget/api/local/containers` | Local container list (15 s cache) |
| `GET /widget/api/local/images` | Local image list (15 s cache) |
| `POST /widget/api/local/containers/<id>/<action>` | Start / stop / restart local container |
| `GET /widget/api/nas/containers` | NAS container list via agent (15 s cache) |
| `GET /widget/api/nas/images` | NAS image list via agent (15 s cache) |
| `POST /widget/api/nas/test` | Test NAS agent connection using supplied URL and token |
| `POST /widget/api/nas/containers/<id>/<action>` | Start / stop / restart NAS container |
| `GET /widget/api/hub/repos` | `penrithbeacon` repository list (15 s cache) |
| `GET /widget/api/hub/repos/<name>/tags` | Tags for a repo, newest-first (15 s cache) |
| `GET /widget/api/hub/repos/<name>/description` | Full README markdown for a repo (15 s cache) |
| `GET /widget/api/settings` | Current settings (tokens masked) |
| `POST /widget/api/settings` | Update settings |
| `GET /widget/api/guids` | Component UUIDs for Bonjour discovery |
| `GET /widget/export.wcp` | Self-export as a `.wcp` package |

## WCP Compatibility

| Property | Value |
|----------|-------|
| WCP Version | 2.1.0 |
| Widget Version | 1.4.0 |
| Render mode | iframe |
| Auth | none (credentials stored server-side) |
| Default card size | 12 × 6 |
| Multi-instance | Yes — per `Wcp-Instance-Id` |

## Technical Details

- **Base image:** `python:3.12-slim`
- **Platforms:** `linux/amd64`, `linux/arm64`
- **Port:** `3744`
- **Dependencies:** Flask, requests, docker (Python SDK)
- **Docker socket:** mounted at `/var/run/docker.sock:rw` for local container access
- **Persistent storage:** Named Docker volume for settings and NAS credentials

## Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest stable release — multi-arch (`linux/amd64`, `linux/arm64`) |
| `1.3.0-wcp2.1.0` | Widget v1.3.0, WCP 2.1.0 — `/widget/health` returns `container` name |
| `1.1.0-wcp2.1.0` | Widget v1.1.0, WCP 2.1.0 — inline Hub docs, tags newest-first, test-connection fix |
| `1.0.0-wcp2.1.0` | Widget v1.0.0, WCP 2.1.0 — initial release |

> **Platform history:** `latest` was rebuilt as a multi-arch image on 2026-06-05, adding
> `linux/amd64` support (Synology NAS, Intel/AMD servers). The initial `1.0.0-wcp2.1.0`
> tag was built on Apple Silicon and is `linux/arm64` only.

## Source

- Docker Hub: [penrithbeacon/wcp-widget-docker](https://hub.docker.com/r/penrithbeacon/wcp-widget-docker)
- GitHub: [penrithbeacon/wcp-widget-docker](https://github.com/penrithbeacon/wcp-widget-docker)
- NAS agent: [penrithbeacon/wcp-docker-agent](https://github.com/penrithbeacon/wcp-docker-agent)
- WCP Specification: [widgetcontextprotocol.com](https://widgetcontextprotocol.com)
