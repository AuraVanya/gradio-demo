# Docker & Kamal Deployment Guide

## Prerequisites

1. **Docker** installed locally
2. **Kamal** installed: `gem install kamal` or `brew install kamal`
3. **SSH access** to your deployment server
4. **Docker Hub or GitHub Container Registry** account for image hosting
5. **AWS credentials** with appropriate permissions

## Local Development with Docker

### Build the Docker image locally:

```bash
docker build -t gradio-demo:latest .
```

### Run locally:

```bash
docker run -p 7860:7860 \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  -e AWS_DEFAULT_REGION=us-east-2 \
  gradio-demo:latest
```

Visit `http://localhost:7860`

## Deployment with Kamal

### 1. Initialize Kamal (if not already done):

```bash
kamal init
```

### 2. Configure Kamal

Edit `config/deploy.yml` and update:
- `image:` with your registry path (e.g., `ghcr.io/yourusername/gradio-demo`)
- `servers.web.hosts:` with your server IP/hostname
- `servers.web.labels:` traefik rule with your domain
- Registry credentials (username/password)

### 3. Set up secrets

Create or update `.kamal/secrets`:

```bash
AWS_ACCESS_KEY_ID=your_actual_access_key
AWS_SECRET_ACCESS_KEY=your_actual_secret_key
AWS_DEFAULT_REGION=us-east-2
KAMAL_REGISTRY_USERNAME=your_registry_username
KAMAL_REGISTRY_PASSWORD=your_registry_token
```

**Important:** Add `.kamal/secrets` to `.gitignore`

### 4. Deploy

First deployment (sets up server and deploys):
```bash
kamal setup
```

Subsequent deployments:
```bash
kamal deploy
```

### 5. Useful Kamal commands

```bash
# View logs
kamal logs -f

# SSH into server
kamal app exec --interactive --reuse bash

# Check status
kamal status

# Stop the app
kamal stop

# Restart
kamal restart

# Remove deployment
kamal remove
```

## Environment Variables

The following AWS environment variables are required and injected via Kamal secrets:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION`

Ensure your AWS IAM user has permissions for:
- S3 (GetObject, PutObject)
- Textract
- Rekognition
- Bedrock

## Monitoring

With Traefik reverse proxy configured in `config.yml`, your app will be:
- Accessible at your domain
- Auto-HTTPS ready (requires DNS pointing to your server)
- Load-balanced and monitored

## Troubleshooting

### Check if container is running:
```bash
kamal app exec ps aux
```

### View recent logs:
```bash
kamal logs --lines 100
```

### Rebuild and redeploy:
```bash
kamal deploy --force
```

### SSH and inspect manually:
```bash
kamal app exec --interactive --reuse bash
docker ps
docker logs <container-id>
```
