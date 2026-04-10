# 🚀 Gradio Demo - Deployment Complete!

## ✅ Deployment Status

### Server Details
- **Server IP**: 56.68.28.55
- **Domain**: team-coral-workshop.i2go.io
- **SSH User**: ubuntu
- **SSH Key**: ~/.ssh/tigerlab_i2go_uat.pem

### Container Status
- **Image**: gradio-demo:latest
- **Container ID**: 7f1c3ef24c02
- **Status**: ✅ Healthy & Running
- **Port**: 7860 (internal), exposed on 0.0.0.0:7860

### Environment Variables Configured
- AWS_ACCESS_KEY_ID: Configured
- AWS_SECRET_ACCESS_KEY: Configured
- AWS_DEFAULT_REGION: us-east-2
- PYTHONUNBUFFERED: 1

### Deployment Setup
- **Method**: Direct Docker (No external registry)
- **Restart Policy**: unless-stopped (auto-restart on failure)
- **Volume**: /tmp/gradio:/tmp/gradio (for storage)
- **Health Check**: Enabled (30s interval)

## 🌐 Access Information

### Direct Access ✅
- **URL**: http://56.68.28.55:7860
- **Status**: Working

### Domain Access ✅
- **URL**: http://team-coral-workshop.i2go.io:7860
- **Status**: DNS Configured

## 📋 Useful Commands

### Check Container Status
```bash
ssh -i ~/.ssh/tigerlab_i2go_uat.pem ubuntu@56.68.28.55 "docker ps | grep gradio"
```

### View Logs
```bash
ssh -i ~/.ssh/tigerlab_i2go_uat.pem ubuntu@56.68.28.55 "docker logs gradio-demo -f"
```

### Restart Container
```bash
ssh -i ~/.ssh/tigerlab_i2go_uat.pem ubuntu@56.68.28.55 "docker restart gradio-demo"
```

### SSH Into Server
```bash
ssh -i ~/.ssh/tigerlab_i2go_uat.pem ubuntu@56.68.28.55
```

### Update the App (Redeploy)
1. Update code locally
2. Rebuild: `docker build -t gradio-demo:latest .`
3. Save & transfer: `docker save gradio-demo:latest | gzip > /tmp/gradio-demo.tar.gz`
4. SCP to server: `scp -i ~/.ssh/tigerlab_i2go_uat.pem /tmp/gradio-demo.tar.gz ubuntu@56.68.28.55:/tmp/`
5. Load on server: `docker load < /tmp/gradio-demo.tar.gz`
6. Restart: `docker restart gradio-demo`

## ⚠️ Security Notes

**IMPORTANT**: AWS credentials are embedded in the container.
- ⚠️ Rotate AWS keys ASAP (you shared them earlier in plain text)
- Use AWS IAM Roles instead of access keys in production
- Consider using secrets management (Vault, AWS Secrets Manager)

## ✨ Next Steps Optional

**To access on port 80 (without :7860):**
```bash
ssh -i ~/.ssh/tigerlab_i2go_uat.pem ubuntu@56.68.28.55

# Run nginx reverse proxy
docker run -d \
  --name gradio-proxy \
  --restart unless-stopped \
  -p 80:80 \
  --network host \
  -v "$(pwd)/nginx-conf:/etc/nginx/conf.d:ro" \
  nginx:latest
```

---
**Status**: ✅ Production Ready
**Deployed**: 2026-04-10
