#!/bin/bash
# ============================================
# Local Build and Test Script
# ============================================
set -e

echo "🚀 Radio-G Local Build and Test"
echo "================================"

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo -e "${RED}❌ Please update .env with your API keys before continuing${NC}"
    exit 1
fi

# Verify required environment variables
echo -e "${BLUE}📋 Checking environment variables...${NC}"
source .env

if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" = "your_gemini_api_key_here" ]; then
    echo -e "${RED}❌ GEMINI_API_KEY not set in .env${NC}"
    exit 1
fi

if [ -z "$ELEVENLABS_API_KEY" ] || [ "$ELEVENLABS_API_KEY" = "your_elevenlabs_api_key_here" ]; then
    echo -e "${RED}❌ ELEVENLABS_API_KEY not set in .env${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment variables configured${NC}"

# Stop any running containers
echo -e "${BLUE}🛑 Stopping existing containers...${NC}"
docker compose down -v 2>/dev/null || true

# Build images
echo -e "${BLUE}🔨 Building Docker images...${NC}"
docker compose build --no-cache

echo -e "${GREEN}✅ Images built successfully${NC}"

# Start infrastructure services first
echo -e "${BLUE}🏗️  Starting infrastructure services...${NC}"
docker compose up -d redis zookeeper kafka

echo "⏳ Waiting for services to be healthy..."
sleep 20

# Check if Kafka is ready
echo -e "${BLUE}🔍 Checking Kafka health...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker compose exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 &>/dev/null; then
        echo -e "${GREEN}✅ Kafka is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Waiting for Kafka... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Kafka failed to start${NC}"
    docker compose logs kafka
    exit 1
fi

# Seed language configuration in Redis
echo -e "${BLUE}💾 Seeding language configuration...${NC}"
docker compose exec -T redis redis-cli SET languages:config '{"languages":[{"code":"en","name":"English","voice_id":"21m00Tcm4TlvDq8ikWAM"},{"code":"hi","name":"Hindi","voice_id":"pNInz6obpgDQGcFmaJgB"},{"code":"bn","name":"Bengali","voice_id":"onwK4e9ZLuTAKqWW03F9"}]}'

echo -e "${GREEN}✅ Language configuration seeded${NC}"

# Start application services
echo -e "${BLUE}🚀 Starting application services...${NC}"
docker compose up -d news-fetcher news-processor news-api

echo "⏳ Waiting for API to be healthy..."
sleep 30

# Wait for API health
API_HEALTHY=false
for i in {1..30}; do
    if curl -f http://localhost:8000/health &>/dev/null; then
        API_HEALTHY=true
        break
    fi
    echo "Waiting for API... ($i/30)"
    sleep 2
done

if [ "$API_HEALTHY" = false ]; then
    echo -e "${RED}❌ API failed to start${NC}"
    docker compose logs news-api
    exit 1
fi

echo -e "${GREEN}✅ API is healthy${NC}"

# Start frontend
echo -e "${BLUE}🎨 Starting frontend...${NC}"
docker compose up -d news-frontend

sleep 15

# Verify frontend
if curl -f http://localhost:3000 &>/dev/null; then
    echo -e "${GREEN}✅ Frontend is running${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend may still be starting...${NC}"
fi

# Show status
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ All services started successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}📊 Service URLs:${NC}"
echo "  • API:        http://localhost:8000"
echo "  • API Docs:   http://localhost:8000/docs"
echo "  • Frontend:   http://localhost:3000"
echo "  • Kafka UI:   http://localhost:8080"
echo ""
echo -e "${BLUE}🔧 Useful commands:${NC}"
echo "  • View logs:     docker compose logs -f [service-name]"
echo "  • Stop all:      docker compose down"
echo "  • Restart:       docker compose restart [service-name]"
echo "  • Scale:         docker compose up -d --scale news-processor=3"
echo ""
echo -e "${BLUE}📈 Monitoring:${NC}"
echo "  • docker compose ps                    # Service status"
echo "  • docker compose logs -f news-fetcher  # Fetcher logs"
echo "  • docker compose logs -f news-processor # Processor logs"
echo "  • docker compose logs -f news-api       # API logs"
echo ""
echo -e "${YELLOW}⏭️  Next steps:${NC}"
echo "  1. Visit http://localhost:3000 to see the frontend"
echo "  2. Check http://localhost:8000/docs for API documentation"
echo "  3. Monitor Kafka topics at http://localhost:8080"
echo "  4. Run './scripts/test_deployment.sh' to verify everything works"
echo ""
