# epicstar Setup Guide

Complete step-by-step guide to get epicstar running.

## ✅ Step 1: Build Complete

The container has been successfully built:
- **Image**: `localhost/epicstar:latest`
- **Size**: 401 MB
- **Status**: Ready to run

## 📋 Step 2: GitHub App Setup

### Create GitHub App

1. **Go to GitHub Settings**
   - Navigate to: https://github.com/settings/apps
   - Click "New GitHub App"

2. **Basic Information**
   - **GitHub App name**: `epicstar` (or your preferred name)
   - **Homepage URL**: `https://github.com/studiozeroseven/epicstar`
   - **Webhook URL**: `https://your-domain.com/webhooks/github`
     - For local testing, use ngrok: `https://abc123.ngrok.io/webhooks/github`
   - **Webhook secret**: Generate a strong secret (save this!)
     ```bash
     openssl rand -hex 32
     ```

3. **Permissions**
   Set these **Repository permissions**:
   - **Contents**: Read-only
   - **Metadata**: Read-only

4. **Subscribe to events**
   - ✅ Check "Watch" events

5. **Where can this GitHub App be installed?**
   - Select "Only on this account" (or "Any account" if you want)

6. **Create the App**
   - Click "Create GitHub App"
   - **Save the App ID** (you'll see it on the next page)

7. **Generate Private Key**
   - Scroll down to "Private keys"
   - Click "Generate a private key"
   - Download the `.pem` file
   - Save it securely (e.g., `~/.ssh/epicstar-github-app.pem`)

8. **Install the App**
   - Click "Install App" in the left sidebar
   - Select your account
   - Choose "All repositories" or "Only select repositories"
   - Click "Install"

### What You Need to Save

After creating the GitHub App, you should have:
- ✅ **App ID**: (e.g., `123456`)
- ✅ **Webhook Secret**: (the one you generated)
- ✅ **Private Key File**: (the `.pem` file you downloaded)

## 🔧 Step 3: OneDev Setup

### Get OneDev API Token

1. **Log into OneDev**
   - Go to your OneDev instance: `https://dev.vivaed.com`

2. **Create API Token**
   - Click your profile (top right)
   - Go to "Settings" → "Access Tokens"
   - Click "New Access Token"
   - **Name**: `epicstar`
   - **Permissions**: Select "Repository Management"
   - Click "Create"
   - **Copy the token** (you won't see it again!)

### What You Need to Save

- ✅ **OneDev API URL**: `https://dev.vivaed.com`
- ✅ **OneDev API Token**: (the token you just created)

## ⚙️ Step 4: Configure Environment

Create a `.env` file with your credentials:

```bash
cd /Users/ian/PycharmProjects/epicstar/epicstar

cat > .env << 'EOF'
# Environment
ENVIRONMENT=development

# Database (SQLite for development)
DATABASE_URL=sqlite:///./dev.db

# GitHub App Configuration
GITHUB_APP_ID=YOUR_APP_ID_HERE
GITHUB_WEBHOOK_SECRET=YOUR_WEBHOOK_SECRET_HERE
GITHUB_PRIVATE_KEY_PATH=/path/to/your/github-app-key.pem

# OneDev Configuration
ONEDEV_API_URL=https://dev.vivaed.com
ONEDEV_API_TOKEN=YOUR_ONEDEV_TOKEN_HERE

# Application Settings
APP_NAME=epicstar
APP_VERSION=0.1.0
LOG_LEVEL=INFO
EOF
```

**Replace the placeholders:**
- `YOUR_APP_ID_HERE` → Your GitHub App ID
- `YOUR_WEBHOOK_SECRET_HERE` → Your webhook secret
- `/path/to/your/github-app-key.pem` → Path to your private key file
- `YOUR_ONEDEV_TOKEN_HERE` → Your OneDev API token

## 🚀 Step 5: Run epicstar

### Option A: Run with Podman Compose (Recommended)

```bash
# Start the services
podman-compose up -d

# Check logs
podman-compose logs -f app

# Check status
podman-compose ps
```

### Option B: Run Container Directly

```bash
# Run the container
podman run -d \
  --name epicstar \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/dev.db:/app/dev.db \
  -v ~/.ssh/epicstar-github-app.pem:/app/github-app-key.pem:ro \
  localhost/epicstar:latest

# Check logs
podman logs -f epicstar

# Check status
podman ps
```

### Option C: Run Locally (Development)

```bash
# Install dependencies (if not already done)
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the app
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🧪 Step 6: Test the Setup

### 1. Health Check

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

### 2. API Documentation

Open in browser: http://localhost:8000/docs

You should see the interactive Swagger UI.

### 3. Metrics

```bash
curl http://localhost:8000/metrics/summary
```

## 🌐 Step 7: Expose to Internet (for GitHub Webhooks)

### Option A: Using ngrok (Quick Testing)

```bash
# Install ngrok
brew install ngrok  # macOS

# Start ngrok tunnel
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Update your GitHub App webhook URL to: https://abc123.ngrok.io/webhooks/github
```

### Option B: Production Deployment

See `docs/deployment/podman-deployment.md` for:
- Nginx reverse proxy setup
- SSL/TLS certificates
- Systemd service configuration
- Domain configuration

## ✅ Step 8: Test Webhook

1. **Star a Repository on GitHub**
   - Go to any public repository
   - Click the "Star" button

2. **Check epicstar Logs**
   ```bash
   # If using podman-compose
   podman-compose logs -f app
   
   # If using podman directly
   podman logs -f epicstar
   
   # If running locally
   # Check terminal output
   ```

3. **Verify in OneDev**
   - Log into OneDev
   - Check if the repository was created

## 🔍 Troubleshooting

### Webhook Not Received

1. **Check GitHub App webhook deliveries**
   - Go to your GitHub App settings
   - Click "Advanced" → "Recent Deliveries"
   - Check for errors

2. **Verify webhook URL is accessible**
   ```bash
   curl -X POST https://your-domain.com/webhooks/github
   ```

3. **Check signature verification**
   - Make sure `GITHUB_WEBHOOK_SECRET` matches what you set in GitHub App

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

# Check environment variables
podman exec epicstar env | grep GITHUB
```

## 📊 Next Steps

Once everything is working:

1. ✅ Test starring/unstarring repositories
2. ✅ Check OneDev for synced repositories
3. ✅ Monitor metrics at `/metrics/summary`
4. ✅ Set up production deployment (see deployment guide)
5. ✅ Configure monitoring and alerts

## 📚 Additional Resources

- **README**: Complete project overview
- **GETTING_STARTED**: Development guide
- **docs/setup/github-app-setup.md**: Detailed GitHub App setup
- **docs/deployment/podman-deployment.md**: Production deployment
- **docs/api/webhook-api.md**: Webhook API reference

---

**Need Help?**
- Check the troubleshooting guide: `docs/operations/troubleshooting.md`
- Review logs for error messages
- Verify all environment variables are set correctly

