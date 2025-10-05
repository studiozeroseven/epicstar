# Finding Your GitHub App Private Key

## The Fingerprint You Have

`SHA256:9Isln6IuwRGSYCLT+vPyfUdtyU3+Hypnh16xH1yHjZo=`

This fingerprint doesn't match any keys currently on your system. This means:

1. **You have a GitHub App** with this key fingerprint
2. **The private key file** is either:
   - Not downloaded yet
   - Downloaded but in a different location
   - Downloaded and deleted

## ✅ Solution: Get the Key

### Step 1: Check Your GitHub Apps

Go to: https://github.com/settings/apps

Look for an app named:
- `epicstar`
- `epic_star`
- `github-onedev-sync`
- Or any app you created recently

### Step 2: Get the App ID

Click on the app and note the **App ID** (you'll need this for `.env`)

### Step 3: Generate New Private Key

Since we can't find the key file, generate a new one:

1. In your GitHub App settings
2. Scroll to "Private keys"
3. Click "Generate a private key"
4. Save the downloaded `.pem` file to:
   ```bash
   ~/.ssh/epicstar-github-app.pem
   ```

5. Set permissions:
   ```bash
   chmod 600 ~/.ssh/epicstar-github-app.pem
   ```

### Step 4: Update .env

```bash
cd /Users/ian/PycharmProjects/epicstar/epicstar
nano .env
```

Update these lines:
```bash
GITHUB_APP_ID=YOUR_APP_ID_FROM_STEP_2
GITHUB_PRIVATE_KEY_PATH=/Users/ian/.ssh/epicstar-github-app.pem
```

## 🔍 Alternative: Search for the Key

If you think you already downloaded it, try:

```bash
# Search Downloads
ls -lt ~/Downloads/*.pem 2>/dev/null | head -10

# Search Desktop
ls -lt ~/Desktop/*.pem 2>/dev/null | head -10

# Search Documents
find ~/Documents -name "*.pem" -type f 2>/dev/null

# Search entire home directory (may take a while)
find ~ -name "*.pem" -type f -mtime -60 2>/dev/null | grep -v Library
```

## ✨ Once You Have the Key

Run the quick start script:

```bash
cd /Users/ian/PycharmProjects/epicstar/epicstar
./scripts/quick-start.sh
```

It will validate your configuration and start epicstar!
