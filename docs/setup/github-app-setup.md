# GitHub App Setup Guide

## Overview

This guide walks you through creating and configuring a GitHub App to receive webhook notifications when you star repositories.

## Prerequisites

- GitHub account with admin access
- Access to create GitHub Apps (personal account or organization)
- Public URL for webhook endpoint (or ngrok/smee.io for testing)

## Step 1: Create GitHub App

### 1.1 Navigate to GitHub App Settings

**For Personal Account**:
1. Go to https://github.com/settings/apps
2. Click "New GitHub App"

**For Organization**:
1. Go to https://github.com/organizations/{org-name}/settings/apps
2. Click "New GitHub App"

### 1.2 Configure Basic Information

Fill in the following fields:

| Field | Value | Notes |
|-------|-------|-------|
| **GitHub App name** | `github-onedev-sync` | Must be unique across GitHub |
| **Description** | `Automatically sync starred repositories to OneDev` | Optional but recommended |
| **Homepage URL** | `https://github.com/your-username/epicstar` | Your project repository |
| **Webhook URL** | `https://your-domain.com/webhooks/github` | See Step 2 for testing URLs |
| **Webhook secret** | Generate a strong secret | Save this for later! |

**Generate Webhook Secret**:
```bash
# Generate a secure random secret
python -c "import secrets; print(secrets.token_hex(32))"
# Or
openssl rand -hex 32
```

**Save the secret**: You'll need this for the `GITHUB_WEBHOOK_SECRET` environment variable.

---

## Step 2: Configure Webhook URL

### Production URL

Use your production domain:
```
https://sync.example.com/webhooks/github
```

### Development/Testing URLs

**Option A: ngrok** (Recommended for local testing)
```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com/

# Start ngrok tunnel
ngrok http 8000

# Use the HTTPS URL provided:
# https://abc123.ngrok.io/webhooks/github
```

**Option B: smee.io** (GitHub's webhook proxy)
```bash
# Install smee client
npm install -g smee-client

# Start smee channel
smee --url https://smee.io/abc123 --target http://localhost:8000/webhooks/github

# Use the smee.io URL in GitHub App settings:
# https://smee.io/abc123
```

**Option C: Expose local server** (Not recommended for security)
```bash
# Only if you have a public IP and proper firewall
# Use your public IP or domain
https://your-public-ip:8000/webhooks/github
```

---

## Step 3: Configure Permissions

### Repository Permissions

Set the following permissions:

| Permission | Access | Reason |
|------------|--------|--------|
| **Metadata** | Read-only | Access repository metadata (name, URL, etc.) |
| **Contents** | Read-only | Access repository content (for private repos) |

### User Permissions

| Permission | Access | Reason |
|------------|--------|--------|
| **Starring** | Read-only | Detect when user stars repositories |

### Subscribe to Events

Check the following events:

- ✅ **Watch** (This is the "star" event)

**Important**: The event is called "watch" in the API, but it corresponds to starring repositories.

---

## Step 4: Configure Installation Settings

### Where can this GitHub App be installed?

Choose one:

- ⭕ **Only on this account** (Recommended for personal use)
- ⭕ **Any account** (If you want to share with others)

For personal use, select "Only on this account".

---

## Step 5: Create the App

1. Click "Create GitHub App"
2. You'll be redirected to the app's settings page
3. **Save the following information**:
   - App ID (shown at the top)
   - Client ID (shown in "About" section)

---

## Step 6: Generate Private Key

The private key is used for authenticating API requests as the GitHub App.

### 6.1 Generate Key

1. Scroll down to "Private keys" section
2. Click "Generate a private key"
3. A `.pem` file will be downloaded automatically

### 6.2 Store Private Key Securely

**Option A: Environment Variable** (Recommended for containers)
```bash
# Convert to base64 for easier storage
cat github-app-private-key.pem | base64 > github-app-private-key.b64

# Set environment variable
export GITHUB_PRIVATE_KEY=$(cat github-app-private-key.pem)
```

**Option B: File Path** (For local development)
```bash
# Move to secure location
mv github-app-private-key.pem ~/.ssh/github-app-key.pem
chmod 600 ~/.ssh/github-app-key.pem

# Set environment variable with path
export GITHUB_PRIVATE_KEY_PATH=~/.ssh/github-app-key.pem
```

**⚠️ Security Warning**: 
- Never commit the private key to Git
- Add `*.pem` to `.gitignore`
- Restrict file permissions to 600

---

## Step 7: Install the App

### 7.1 Install on Your Account

1. Go to the app's settings page
2. Click "Install App" in the left sidebar
3. Select your account
4. Choose repository access:
   - ⭕ **All repositories** (App will receive events for all repos)
   - ⭕ **Only select repositories** (Choose specific repos)

For this use case, select "All repositories" since you want to sync any repo you star.

5. Click "Install"

### 7.2 Verify Installation

After installation, you should see:
- Installation ID (save this)
- List of repositories the app has access to

---

## Step 8: Test Webhook Delivery

### 8.1 Start Your Local Server

```bash
# Make sure your middleware service is running
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, start ngrok (if using)
ngrok http 8000
```

### 8.2 Trigger a Test Event

1. Go to any GitHub repository
2. Click the "Star" button
3. Check your server logs for incoming webhook

### 8.3 Verify in GitHub

1. Go to your GitHub App settings
2. Click "Advanced" in the left sidebar
3. Scroll to "Recent Deliveries"
4. You should see the webhook delivery with:
   - ✅ Green checkmark (successful delivery)
   - Response code 200
   - Request and response payloads

### 8.4 Troubleshooting

**No webhook received?**
- Check that ngrok/smee is running
- Verify webhook URL in GitHub App settings
- Check firewall rules
- Look for errors in "Recent Deliveries"

**Webhook received but signature invalid?**
- Verify `GITHUB_WEBHOOK_SECRET` matches the secret in GitHub App settings
- Check that you're using the correct signature verification algorithm (HMAC-SHA256)

**Webhook received but returns 500?**
- Check server logs for errors
- Verify all environment variables are set
- Check database connection

---

## Step 9: Save Configuration

Create a `.env` file with the following variables:

```bash
# GitHub App Configuration
GITHUB_APP_ID=123456
GITHUB_WEBHOOK_SECRET=your-webhook-secret-here
GITHUB_PRIVATE_KEY_PATH=/path/to/github-app-key.pem
# OR
GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"

# OneDev Configuration
ONEDEV_API_URL=https://onedev.example.com
ONEDEV_API_TOKEN=your-onedev-token-here

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/syncdb

# Application Configuration
LOG_LEVEL=INFO
ENVIRONMENT=development
```

**⚠️ Important**: 
- Never commit `.env` to Git
- Add `.env` to `.gitignore`
- Use `.env.example` as a template (without actual secrets)

---

## Step 10: Verify Configuration

Run the configuration verification script:

```bash
python scripts/verify_config.py
```

Expected output:
```
✅ GitHub App ID: 123456
✅ GitHub Webhook Secret: Set (32 characters)
✅ GitHub Private Key: Valid RSA key
✅ OneDev API URL: https://onedev.example.com
✅ OneDev API Token: Set
✅ Database URL: Valid PostgreSQL connection string

All configuration checks passed!
```

---

## Configuration Reference

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `GITHUB_APP_ID` | Yes | GitHub App ID | `123456` |
| `GITHUB_WEBHOOK_SECRET` | Yes | Webhook secret for signature verification | `abc123...` |
| `GITHUB_PRIVATE_KEY` | Yes* | Private key content (base64 or PEM) | `-----BEGIN RSA...` |
| `GITHUB_PRIVATE_KEY_PATH` | Yes* | Path to private key file | `/path/to/key.pem` |
| `ONEDEV_API_URL` | Yes | OneDev instance URL | `https://onedev.example.com` |
| `ONEDEV_API_TOKEN` | Yes | OneDev API token | `token123...` |
| `DATABASE_URL` | Yes | PostgreSQL connection string | `postgresql://...` |

*Either `GITHUB_PRIVATE_KEY` or `GITHUB_PRIVATE_KEY_PATH` is required, not both.

---

## Security Best Practices

### 1. Webhook Secret
- Use a strong, randomly generated secret (32+ characters)
- Rotate the secret periodically (every 90 days)
- Never log or expose the secret

### 2. Private Key
- Store securely with restricted permissions (600)
- Never commit to version control
- Consider using a secret management system (Vault, AWS Secrets Manager)
- Rotate keys annually

### 3. API Tokens
- Use tokens with minimal required permissions
- Set expiration dates if supported
- Rotate regularly
- Revoke immediately if compromised

### 4. Webhook Endpoint
- Always use HTTPS in production
- Implement rate limiting
- Log all webhook attempts
- Monitor for suspicious activity

---

## Updating GitHub App Configuration

### Update Webhook URL

1. Go to GitHub App settings
2. Update "Webhook URL" field
3. Click "Save changes"
4. Test with a new star event

### Update Permissions

1. Go to GitHub App settings
2. Scroll to "Permissions & events"
3. Update required permissions
4. Click "Save changes"
5. **Important**: Users must accept the new permissions
   - Go to "Install App"
   - Click "Configure" next to your installation
   - Review and accept new permissions

### Rotate Webhook Secret

1. Generate new secret: `openssl rand -hex 32`
2. Update in GitHub App settings
3. Update `GITHUB_WEBHOOK_SECRET` environment variable
4. Restart the service
5. Test webhook delivery

### Rotate Private Key

1. Generate new private key in GitHub App settings
2. Download the new `.pem` file
3. Update `GITHUB_PRIVATE_KEY` or `GITHUB_PRIVATE_KEY_PATH`
4. Restart the service
5. Revoke old key in GitHub App settings

---

## Troubleshooting

### Common Issues

#### Issue: "Webhook URL is not reachable"

**Symptoms**: GitHub shows error when testing webhook

**Solutions**:
- Verify URL is publicly accessible
- Check firewall rules
- Ensure service is running
- Test with `curl https://your-url/webhooks/github`

#### Issue: "Invalid signature"

**Symptoms**: Webhook received but returns 401

**Solutions**:
- Verify `GITHUB_WEBHOOK_SECRET` matches GitHub App settings
- Check signature verification code
- Ensure using HMAC-SHA256 algorithm
- Verify header name is `X-Hub-Signature-256`

#### Issue: "App not receiving events"

**Symptoms**: Star repos but no webhooks received

**Solutions**:
- Verify "Watch" event is subscribed
- Check app is installed on your account
- Verify webhook URL is correct
- Check "Recent Deliveries" in GitHub App settings

#### Issue: "Permission denied"

**Symptoms**: Cannot access repository metadata

**Solutions**:
- Verify "Metadata" permission is set to "Read-only"
- Re-install the app to accept new permissions
- Check app is installed on correct account

---

## Next Steps

After completing GitHub App setup:

1. ✅ Proceed to [OneDev Configuration](onedev-configuration.md)
2. ✅ Set up the [Development Environment](../development/local-setup.md)
3. ✅ Test the [Complete Workflow](../use-cases/basic-sync.md)

---

## References

- [GitHub Apps Documentation](https://docs.github.com/en/developers/apps)
- [Webhook Events and Payloads](https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads)
- [Authenticating with GitHub Apps](https://docs.github.com/en/developers/apps/building-github-apps/authenticating-with-github-apps)
- [Securing Webhooks](https://docs.github.com/en/developers/webhooks-and-events/webhooks/securing-your-webhooks)

---

**Last Updated**: 2025-10-04  
**Version**: 1.0

