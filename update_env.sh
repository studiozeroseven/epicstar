#!/bin/bash

echo "🔧 Updating .env file with GitHub App private key path..."

# Update the private key path in .env
sed -i '' 's|GITHUB_PRIVATE_KEY_PATH=.*|GITHUB_PRIVATE_KEY_PATH=/Users/ian/.ssh/epicstar-github-app.pem|' .env

echo "✅ Private key path updated!"
echo ""
echo "📋 Current .env configuration:"
grep -E "GITHUB_|ONEDEV_" .env
echo ""
echo "⚠️  You still need to update:"
echo "   1. GITHUB_APP_ID (get from https://github.com/settings/apps)"
echo "   2. ONEDEV_API_TOKEN (get from https://dev.vivaed.com)"
