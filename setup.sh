#!/bin/bash

echo "🚀 Starting Telegram AI Bot Setup..."

mkdir -p logs

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose."
    exit 1
fi

if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create the .env file."
    exit 1
fi

echo "✅ Requirements checked"

echo "🐳 Starting Docker containers..."
docker-compose up -d redis ollama

echo "⏳ Waiting for services to start..."
sleep 10

echo "🤖 Pulling AI model (this may take some time)..."
docker exec ollama ollama pull llama3.2:1b

echo "✅ Model pulled"

echo "🤖 Starting bot and worker..."
docker-compose up -d telegram-bot worker

echo "🎉 Setup complete!"
echo ""
echo "📋 For status check:"
echo "  docker-compose logs -f telegram-bot  # Bot logs"
echo "  docker-compose logs -f worker        # Worker logs"
echo "  docker-compose logs -f ollama        # Ollama logs"
echo ""
echo "🛑 To stop:"
echo "  docker-compose down"
echo ""
echo "🔄 To restart:"
echo "  docker-compose restart"