# Docker Setup for Anansi

## Building Locally

```bash
docker build -t anansi:latest .
```

## Running the Container

### Option 1: Using Docker Compose (Recommended)

```bash
docker-compose up -d
```

This automatically:
- Creates a named volume `anansi-data` for database persistence
- Exposes port 9000
- Sets up health checks
- Auto-restarts on failure

### Option 2: Using Docker CLI

```bash
# Create a named volume for the database
docker volume create anansi-data

# Run the container with volume mount
docker run -d \
  --name anansi \
  -p 9000:9000 \
  -v anansi-data:/app/data \
  anansi:latest
```

### Option 3: Using Host Directory Volume

```bash
# Create a data directory
mkdir -p ./data

# Run with host directory mount
docker run -d \
  --name anansi \
  -p 9000:9000 \
  -v $(pwd)/data:/app/data \
  anansi:latest
```

The dashboard will be available at `http://localhost:9000`

## Volume Management

### View Volumes

```bash
docker volume ls | grep anansi
```

### Inspect Volume

```bash
docker volume inspect anansi-data
```

### Backup Database

```bash
# Docker volume
docker run --rm \
  -v anansi-data:/app/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/anansi-backup.tar.gz -C /app/data .

# Host directory
tar czf anansi-backup.tar.gz -C ./data .
```

### Restore Database

```bash
# Docker volume
docker volume rm anansi-data
docker volume create anansi-data
docker run --rm \
  -v anansi-data:/app/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/anansi-backup.tar.gz -C /app/data

# Host directory
rm -rf ./data/*
tar xzf anansi-backup.tar.gz -C ./data
```

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

# Run it with volume
docker volume create anansi-data
docker run -p 9000:9000 -v anansi-data:/app/data ghcr.io/goncalovalverde/anansi:latest
```

### Architecture

- **Platform**: `linux/arm64` (Apple Silicon/macOS M1, M2, M3, etc.)
- **Port**: 9000
- **Multi-stage build**: Node.js frontend build → Python runtime
- **Data volume**: `/app/data` (persistent database storage)

## Docker Image Details

- Frontend: Built with Node.js 18 Alpine, served by FastAPI
- Backend: Python 3.11 slim image with minimal dependencies
- Database: SQLite (persisted via `/app/data` volume)
- Health check: Automatic container health verification
- Restart policy: Auto-restarts on failure (compose only)
