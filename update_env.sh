#!/bin/bash
# One-shot helper: point .env at the local GitHub App key and remind you what's left.

cd "$(dirname "$0")" || exit 1

if [ ! -f .env ]; then
    echo "No .env found - create one first: cp .env.example .env"
    exit 1
fi

KEY_PATH="${1:-$HOME/.ssh/epicstar-github-app.pem}"
if [[ "$OSTYPE" == darwin* ]]; then
    sed -i '' "s|^GITHUB_PRIVATE_KEY_PATH=.*|GITHUB_PRIVATE_KEY_PATH=$KEY_PATH|" .env
else
    sed -i "s|^GITHUB_PRIVATE_KEY_PATH=.*|GITHUB_PRIVATE_KEY_PATH=$KEY_PATH|" .env
fi
echo "GITHUB_PRIVATE_KEY_PATH set to $KEY_PATH"

echo ""
echo "Still required in .env:"
echo "  1. GITHUB_APP_ID        (https://github.com/settings/apps)"
echo "  2. GITHUB_WEBHOOK_SECRET (openssl rand -hex 32)"
echo "  3. ONEDEV_API_URL / ONEDEV_USERNAME / ONEDEV_API_TOKEN"
