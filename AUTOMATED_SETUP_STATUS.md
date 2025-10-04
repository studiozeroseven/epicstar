# epicstar - Automated Setup Status

## ✅ What I've Done Automatically

### 1. Container Build ✅
- **Status**: Complete
- **Image**: `localhost/epicstar:latest` (401 MB)
- **Features**: Multi-stage build, non-root user, health checks
- **Verification**: `podman images | grep epicstar`

### 2. Environment Configuration ✅
- **Status**: Template created
- **File**: `.env`
- **Webhook Secret Generated**: `0afbf7d43b23085dc4590fcd5427e12fb5ae6ff5deafd637146ee552082cfed0`
- **Location**: `/Users/ian/PycharmProjects/epicstar/epicstar/.env`

### 3. Database Initialization ✅
- **Status**: Complete
- **Type**: SQLite
- **File**: `dev.db`
- **Tables**: repositories, sync_logs, webhook_events
- **Migrations**: Applied successfully

### 4. Scripts Created ✅
- **Quick Start Script**: `scripts/quick-start.sh` (executable)
- **GitHub App Guide**: `scripts/create-github-app.md`
- **Setup Guide**: `SETUP_GUIDE.md`

### 5. Tools Verified ✅
- **Podman**: Running and ready
- **ngrok**: Installed at `/opt/homebrew/bin/ngrok`
- **Python**: Environment ready
- **Git**: Configured

## 🔧 What You Need to Do (Manual Steps)

Since I can't access your GitHub account or OneDev instance directly, you need to complete these steps:

### Step 1: Create GitHub App (15 minutes)

**Follow the guide**: `scripts/create-github-app.md`

**Quick Summary**:
1. Go to: https://github.com/settings/apps/new
2. Fill in:
   - **Name**: `epicstar`
   - **Webhook URL**: `https://TEMP.com/webhooks/github` (we'll update this)
   - **Webhook Secret**: `0afbf7d43b23085dc4590fcd5427e12fb5ae6ff5deafd637146ee552082cfed0`
   - **Permissions**: Contents (Read), Metadata (Read)
   - **Events**: Watch
3. Create the app
4. Save the **App ID**
5. Generate and download **Private Key** (.pem file)
6. Install the app on your account

**What to save**:
- App ID: `______`
- Private Key: Save to `~/.ssh/epicstar-github-app.pem`

### Step 2: Get OneDev API Token (5 minutes)

1. Go to: https://dev.vivaed.com
2. Profile → Settings → Access Tokens
3. Create new token:
   - **Name**: `epicstar`
   - **Permissions**: Repository Management
4. Copy the token

**What to save**:
- API Token: `______`

### Step 3: Update .env File (2 minutes)

Edit the `.env` file and replace these values:

```bash
# Replace this:
GITHUB_APP_ID=123456

# With your actual App ID:
GITHUB_APP_ID=YOUR_ACTUAL_APP_ID

# Replace this:
GITHUB_PRIVATE_KEY_PATH=/app/github-app-key.pem

# With your actual path:
GITHUB_PRIVATE_KEY_PATH=/Users/ian/.ssh/epicstar-github-app.pem

# Replace this:
ONEDEV_API_TOKEN=replace_with_your_onedev_token

# With your actual token:
ONEDEV_API_TOKEN=YOUR_ACTUAL_ONEDEV_TOKEN
```

## 🚀 After You Complete the Manual Steps

Once you've updated the `.env` file with your credentials, run:

```bash
cd /Users/ian/PycharmProjects/epicstar/epicstar
./scripts/quick-start.sh
```

This script will:
1. Verify your configuration
2. Let you choose how to run epicstar
3. Start the services
4. Provide next steps

## 📋 Complete Setup Checklist

- [ ] GitHub App created
- [ ] App ID saved and added to `.env`
- [ ] Private key downloaded and saved to `~/.ssh/epicstar-github-app.pem`
- [ ] GitHub App installed on your account
- [ ] OneDev API token created
- [ ] OneDev token added to `.env`
- [ ] `.env` file fully configured
- [ ] Run `./scripts/quick-start.sh`
- [ ] Start ngrok: `ngrok http 8000`
- [ ] Update GitHub App webhook URL with ngrok URL
- [ ] Test by starring a repository

## 🧪 Testing the Complete Flow

### 1. Start epicstar

```bash
./scripts/quick-start.sh
# Choose option 3 for local development (easiest for testing)
```

### 2. Start ngrok (in another terminal)

```bash
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

### 3. Update GitHub App Webhook URL

1. Go to: https://github.com/settings/apps
2. Click on your `epicstar` app
3. Update **Webhook URL** to: `https://abc123.ngrok.io/webhooks/github`
4. Click "Save changes"

### 4. Test the Webhook

1. Go to any public GitHub repository
2. Click the ⭐ **Star** button
3. Watch the epicstar logs:
   ```bash
   # You should see:
   # - Webhook received
   # - Repository cloned
   # - Pushed to OneDev
   # - Success message
   ```

4. Check OneDev:
   - Go to https://dev.vivaed.com
   - You should see the new repository!

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "database": "connected"
}
```

### Metrics
```bash
curl http://localhost:8000/metrics/summary
```

### API Documentation
Open in browser: http://localhost:8000/docs

## 🔍 Troubleshooting

### Webhook Not Received

1. Check ngrok is running: `curl https://your-ngrok-url.ngrok.io/health`
2. Check GitHub webhook deliveries: GitHub App → Advanced → Recent Deliveries
3. Verify webhook secret matches in both places

### Database Errors

```bash
# Reset database
rm dev.db
alembic upgrade head
```

### Container Won't Start

```bash
# Check logs
podman logs epicstar

# Check environment
podman exec epicstar env | grep GITHUB
```

## 📚 Documentation

- **Setup Guide**: `SETUP_GUIDE.md` - Complete setup instructions
- **GitHub App Guide**: `scripts/create-github-app.md` - Detailed GitHub App creation
- **Quick Start**: `scripts/quick-start.sh` - Automated startup script
- **README**: `README.md` - Project overview
- **Getting Started**: `GETTING_STARTED.md` - Development guide

## 🎯 Current Status

**What's Ready**:
- ✅ Container built
- ✅ Database initialized
- ✅ Configuration template created
- ✅ Scripts ready
- ✅ Documentation complete

**What's Needed**:
- ⏳ GitHub App credentials (App ID, Private Key)
- ⏳ OneDev API token
- ⏳ Update `.env` file
- ⏳ Start the services

## 💡 Quick Commands Reference

```bash
# Start epicstar (interactive)
./scripts/quick-start.sh

# Start with Podman Compose
podman-compose up -d

# Start locally
uvicorn app.main:app --reload

# Start ngrok
ngrok http 8000

# Check health
curl http://localhost:8000/health

# View logs (Podman Compose)
podman-compose logs -f app

# View logs (Podman)
podman logs -f epicstar

# Stop services
podman-compose down
# or
podman stop epicstar && podman rm epicstar
```

---

**Ready to proceed?**

1. Complete the manual steps above
2. Run `./scripts/quick-start.sh`
3. Let me know if you need help with any step!

