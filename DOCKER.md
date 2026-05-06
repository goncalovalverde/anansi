# Docker Setup for Anansi

## Quick Start

### With Docker Compose (Easiest)
```bash
docker-compose up -d
```

### With Docker Run (Named Volume)
```bash
docker volume create anansi-data
docker run -d --name anansi -p 9000:9000 -v anansi-data:/app/data anansi:latest
```

### With Docker Run (Host Directory)
```bash
mkdir -p ./data
docker run -d --name anansi -p 9000:9000 -v $(pwd)/data:/app/data anansi:latest
```

---

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

### Option 2: Using Docker CLI with Named Volume

**Step 1: Create the volume**
```bash
docker volume create anansi-data
```

**Step 2: Run the container**
```bash
docker run -d \
  --name anansi \
  -p 9000:9000 \
  -v anansi-data:/app/data \
  anansi:latest
```

**View logs:**
```bash
docker logs anansi
```

**Stop the container:**
```bash
docker stop anansi
```

**Remove the container (but keep volume):**
```bash
docker rm anansi
```

### Option 3: Using Docker CLI with Host Directory Volume

**Step 1: Create data directory**
```bash
mkdir -p ./data
```

**Step 2: Run the container**
```bash
docker run -d \
  --name anansi \
  -p 9000:9000 \
  -v $(pwd)/data:/app/data \
  anansi:latest
```

**Advantages:**
- Database stored in local `./data` directory
- Easy to backup: `tar czf backup.tar.gz data/`
- Easy to see files: `ls -la data/`
- Git can ignore with `.gitignore` entry: `echo "data/" >> .gitignore`

### Option 4: Using GitHub Container Registry Image

**Pull the latest image:**
```bash
docker pull ghcr.io/goncalovalverde/anansi:latest
```

**Run with named volume:**
```bash
docker volume create anansi-data
docker run -d \
  --name anansi \
  -p 9000:9000 \
  -v anansi-data:/app/data \
  ghcr.io/goncalovalverde/anansi:latest
```

**Run with host directory:**
```bash
mkdir -p ./data
docker run -d \
  --name anansi \
  -p 9000:9000 \
  -v $(pwd)/data:/app/data \
  ghcr.io/goncalovalverde/anansi:latest
```

## Access the Dashboard

Once running, open your browser:
```
http://localhost:9000
```

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
