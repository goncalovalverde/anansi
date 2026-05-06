# Docker Setup for Anansi

## Building Locally

```bash
docker build -t anansi:latest .
```

## Running the Container

```bash
# Run on port 9000
docker run -p 9000:9000 \
  -v $(pwd)/anansi.db:/app/anansi.db \
  anansi:latest
```

The dashboard will be available at `http://localhost:9000`

## GitHub Actions CI/CD

The workflow (`.github/workflows/docker-build.yml`) automatically builds and pushes Docker images to GitHub Container Registry (ghcr.io) whenever code is pushed to the `main` branch.

### Setup

**No additional setup required!** The workflow uses GitHub's built-in `GITHUB_TOKEN` for authentication.

### Image Tags

Built images are available at:
- `ghcr.io/goncalovalverde/anansi:latest` — Most recent build from main
- `ghcr.io/goncalovalverde/anansi:<commit-sha>` — Specific commit version

### Pulling the Image

```bash
# Authenticate with GitHub Container Registry
echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin

# Pull the latest image
docker pull ghcr.io/goncalovalverde/anansi:latest

# Run it
docker run -p 9000:9000 ghcr.io/goncalovalverde/anansi:latest
```

### Architecture

- **Platform**: `linux/arm64` (Apple Silicon/macOS M1, M2, M3, etc.)
- **Port**: 9000
- **Multi-stage build**: Node.js frontend build → Python runtime

## Docker Image Details

- Frontend: Built with Node.js 18 Alpine, served by FastAPI
- Backend: Python 3.11 slim image with minimal dependencies
- Database: SQLite (persisted via volume mount)
- Health check: Automatic container health verification
