#!/bin/bash

# Development Setup Script for Wheel Strategy

set -e

echo "🚀 Setting up Wheel Strategy development environment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if just is installed
if ! command -v just &> /dev/null; then
    echo "❌ Just is not installed. Please install Just first: https://just.systems/man/en/"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Create environment files if they don't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file (production) from template..."
    cp env.example .env
    echo "⚠️  Please edit .env with your production API keys"
fi

if [ ! -f env.dev ]; then
    echo "📝 Creating env.dev file (development) from template..."
    cp env.example env.dev
    echo "⚠️  Please edit env.dev with your development API keys"
fi

# Make test script executable
if [ -f infra/test-proxy.sh ]; then
    chmod +x infra/test-proxy.sh
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo ""
echo "DEVELOPMENT:"
echo "1. Edit env.dev with your development API keys:"
echo "   - TRADIER_ACCESS_TOKEN"
echo "   - TRADIER_ACCOUNT_ID"
echo "   - TELEGRAM_BOT_TOKEN (optional)"
echo "   - TELEGRAM_CHAT_ID (optional)"
echo "   - OPENAI_API_KEY (optional)"
echo ""
echo "2. Start development environment:"
echo "   just dev"
echo ""
echo "3. Access development application:"
echo "   - Frontend: http://localhost"
echo "   - API: http://localhost/api"
echo "   - API Docs: http://localhost/api/docs"
echo ""
echo "PRODUCTION:"
echo "4. Edit .env with your production API keys"
echo "5. Build and deploy:"
echo "   just build"
echo "   just deploy"
echo ""
echo "MONITORING:"
echo "6. View logs:"
echo "   just logs          # Development"
echo "   just logs-prod     # Production"
echo ""
echo "7. Check health:"
echo "   just health        # Development"
echo "   just health-prod   # Production"
echo ""
echo "For more commands, run: just help"
