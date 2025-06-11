#!/bin/bash

echo "🔧 Fixing RQ import error..."

echo "🛑 Stopping containers..."
docker-compose down

echo "🧹 Cleaning old images to prevent cache issues..."
docker-compose build --no-cache telegram-bot worker

echo "🚀 Restarting containers..."
docker-compose up -d

echo "📋 Checking bot logs..."
sleep 5
docker-compose logs telegram-bot | tail -10

echo "✅ Fix complete!"
echo ""
echo "📊 For status check:"
echo "  docker-compose logs -f telegram-bot"
echo "  docker-compose logs -f worker"