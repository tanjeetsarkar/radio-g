#!/bin/bash
# ============================================
# Quick Setup Script - First Time Setup
# ============================================

echo "🚀 Radio-G First Time Setup"
echo "==========================="
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file already exists${NC}"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing .env file"
        exit 0
    fi
fi

# Copy template
echo -e "${BLUE}📋 Creating .env from template...${NC}"
cp .env.example .env

echo ""
echo -e "${YELLOW}Please provide your API keys:${NC}"
echo ""

# Get Gemini API key
echo -e "${BLUE}Google Gemini API Key${NC}"
echo "Get it from: https://aistudio.google.com/apikey"
read -p "Enter your Gemini API key: " GEMINI_KEY

if [ -z "$GEMINI_KEY" ]; then
    echo -e "${RED}❌ Gemini API key is required${NC}"
    exit 1
fi

# Get ElevenLabs API key
echo ""
echo -e "${BLUE}ElevenLabs API Key${NC}"
echo "Get it from: https://elevenlabs.io/app/settings/api-keys"
read -p "Enter your ElevenLabs API key: " ELEVENLABS_KEY

if [ -z "$ELEVENLABS_KEY" ]; then
    echo -e "${RED}❌ ElevenLabs API key is required${NC}"
    exit 1
fi

# Update .env file
echo ""
echo -e "${BLUE}💾 Updating .env file...${NC}"

# Use sed to replace the placeholder values
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s|GEMINI_API_KEY=your_gemini_api_key_here|GEMINI_API_KEY=${GEMINI_KEY}|g" .env
    sed -i '' "s|ELEVENLABS_API_KEY=your_elevenlabs_api_key_here|ELEVENLABS_API_KEY=${ELEVENLABS_KEY}|g" .env
else
    # Linux
    sed -i "s|GEMINI_API_KEY=your_gemini_api_key_here|GEMINI_API_KEY=${GEMINI_KEY}|g" .env
    sed -i "s|ELEVENLABS_API_KEY=your_elevenlabs_api_key_here|ELEVENLABS_API_KEY=${ELEVENLABS_KEY}|g" .env
fi

echo -e "${GREEN}✅ Configuration complete!${NC}"

# Test API keys
echo ""
echo -e "${BLUE}🧪 Testing API keys...${NC}"

# Test Gemini API
echo -ne "Testing Gemini API... "
if curl -s -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=${GEMINI_KEY}" \
    -H 'Content-Type: application/json' \
    -d '{"contents":[{"parts":[{"text":"test"}]}]}' | grep -q "candidates"; then
    echo -e "${GREEN}✅ Working${NC}"
else
    echo -e "${RED}❌ Failed - Please check your API key${NC}"
fi

# Test ElevenLabs API
echo -ne "Testing ElevenLabs API... "
if curl -s -H "xi-api-key: ${ELEVENLABS_KEY}" \
    "https://api.elevenlabs.io/v1/user" | grep -q "subscription"; then
    echo -e "${GREEN}✅ Working${NC}"
else
    echo -e "${RED}❌ Failed - Please check your API key${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}📋 Next steps:${NC}"
echo ""
echo -e "${YELLOW}For LOCAL testing:${NC}"
echo "  1. Make sure Docker is running"
echo "  2. Run: ./scripts/build_and_run_local.sh"
echo "  3. Test: ./scripts/test_deployment.sh"
echo "  4. Visit: http://localhost:3000"
echo ""
echo -e "${YELLOW}For GCP deployment:${NC}"
echo "  1. Setup GCP infrastructure (see QUICKSTART.md)"
echo "  2. Create .env.production file"
echo "  3. Run: ./scripts/deploy_to_gcp.sh"
echo ""
echo "📚 Full documentation: QUICKSTART.md"
echo ""
