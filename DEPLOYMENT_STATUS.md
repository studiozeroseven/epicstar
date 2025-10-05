# 🚀 epicstar Deployment Status

## ✅ What's Complete

### 1. Configuration Updated ✅
- **Port**: Changed from 8000 to 5000
- **Containerfile**: Updated to expose port 5000
- **Environment Variables**: Added to `.env`:
  ```
  PODMAN_SERVER=10.1.10.204
  PODMAN_SERVER_USER=root
  PODMAN_SERVER_PASS=9226969
  PODMAN_SERVER_URL=https://epicstar.bejai.com
  PORT=5000
  ```

### 2. Source Code Deployed ✅
- **Location**: `/root/epicstar/` on server 10.1.10.204
- **Files Copied**:
  - app/
  - alembic/
  - requirements.txt
  - alembic.ini
  - .env
  - github-app-key.pem

### 3. Deployment Scripts Created ✅
- `scripts/deploy-to-podman-server.sh` - Container deployment (has architecture issues)
- `scripts/deploy-remote-build.sh` - Build on server (Podman issues)
- `scripts/deploy-direct.sh` - Direct Python deployment (in progress)

## ⏳ What's Remaining

### Manual Deployment Steps

Since automated deployment is encountering issues, here's how to complete the deployment manually:

#### Step 1: SSH to Server
```bash
ssh root@10.1.10.204
# Password: 9226969
```

#### Step 2: Install Dependencies
```bash
cd /root/epicstar
apt-get update
apt-get install -y python3 python3-pip python3-venv git
```

#### Step 3: Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

#### Step 4: Install Python Packages
```bash
pip install -r requirements.txt
```

#### Step 5: Initialize Database
```bash
mkdir -p data
alembic upgrade head
```

#### Step 6: Start epicstar
```bash
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 5000 > epicstar.log 2>&1 &
```

#### Step 7: Verify It's Running
```bash
# Check process
ps aux | grep uvicorn

# Check logs
tail -f epicstar.log

# Test health endpoint
curl http://localhost:5000/health
```

### Expected Output
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "production",
  "database": "connected"
}
```

## 🔧 Configuration Details

### GitHub App
- **App ID**: Iv23liblo2T5AcWRBDO8
- **Private Key**: `/root/epicstar/github-app-key.pem`
- **Webhook Secret**: Configured in `.env`
- **Webhook URL**: `https://epicstar.bejai.com/webhooks/github`

### OneDev
- **URL**: https://dev.vivaed.com
- **API Token**: Configured in `.env`

### Server
- **IP**: 10.1.10.204
- **Internal Port**: 5000
- **External Port**: 5000
- **Public URL**: https://epicstar.bejai.com

## 📊 Next Steps After Deployment

### 1. Update GitHub App Webhook URL
1. Go to: https://github.com/settings/apps
2. Click on your epicstar app
3. Update **Webhook URL** to: `https://epicstar.bejai.com/webhooks/github`
4. Save changes

### 2. Test the Integration
1. Star any public GitHub repository
2. Watch the logs: `tail -f /root/epicstar/epicstar.log`
3. Check OneDev at https://dev.vivaed.com
4. Verify the repository was synced

### 3. Set Up as a Service (Optional)
Create a systemd service for automatic startup:

```bash
cat > /etc/systemd/system/epicstar.service << 'EOF'
[Unit]
Description=epicstar - GitHub to OneDev Sync
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/epicstar
Environment="PATH=/root/epicstar/venv/bin"
ExecStart=/root/epicstar/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 5000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable epicstar
systemctl start epicstar
systemctl status epicstar
```

## 💡 Useful Commands

### On Server (10.1.10.204)
```bash
# View logs
tail -f /root/epicstar/epicstar.log

# Restart service
pkill -f uvicorn
cd /root/epicstar && nohup venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 5000 > epicstar.log 2>&1 &

# Check status
ps aux | grep uvicorn
curl http://localhost:5000/health

# View database
cd /root/epicstar
sqlite3 data/epicstar.db ".tables"
sqlite3 data/epicstar.db "SELECT * FROM repositories;"
```

### From Your Mac
```bash
# SSH to server
ssh root@10.1.10.204

# Check health (if proxy is set up)
curl https://epicstar.bejai.com/health

# View logs remotely
ssh root@10.1.10.204 'tail -f /root/epicstar/epicstar.log'
```

## 🐛 Troubleshooting

### Issue: Service Won't Start
```bash
# Check logs
tail -100 /root/epicstar/epicstar.log

# Check if port is in use
netstat -tulpn | grep 5000

# Kill any existing process
pkill -f uvicorn
```

### Issue: Database Errors
```bash
cd /root/epicstar
rm -f data/epicstar.db
venv/bin/alembic upgrade head
```

### Issue: Import Errors
```bash
cd /root/epicstar
source venv/bin/activate
pip install -r requirements.txt
```

## 📝 Summary

**Current Status**: Source code deployed to server, ready for manual installation

**What You Need to Do**:
1. SSH to server: `ssh root@10.1.10.204`
2. Follow Steps 2-7 above
3. Update GitHub App webhook URL
4. Test by starring a repository

**Estimated Time**: 10-15 minutes

---

**All configuration is complete. The app just needs to be started on the server!** 🎉

