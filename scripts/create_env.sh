#!/bin/bash
# ============================================
# Environment File Creator
# Helps create .env or .env.prod files interactively
# ============================================

echo "🔧 Radio-G Environment Configuration"
echo "====================================="
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Which environment do you want to configure?"
echo "1) Local development (.env)"
echo "2) Production/GCP (.env.prod)"
read -p "Select (1 or 2): " choice

if [ "$choice" = "1" ]; then
    ENV_FILE=".env"
    TEMPLATE=".env.example"
    TARGET="local"
elif [ "$choice" = "2" ]; then
    ENV_FILE=".env.prod"
    TEMPLATE=".env.prod.example"
    TARGET="gcp"
else
    echo "Invalid choice"
    exit 1
fi

if [ -f "$ENV_FILE" ]; then
    read -p "⚠️  $ENV_FILE already exists. Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing file"
        exit 0
    fi
fi

echo ""
echo -e "${BLUE}Creating $ENV_FILE from $TEMPLATE${NC}"
cp $TEMPLATE $ENV_FILE

echo ""
echo -e "${YELLOW}Please provide the required information:${NC}"
echo ""

# Get API keys
echo "1. Google Gemini API Key"
echo "   Get from: https://aistudio.google.com/apikey"
read -p "   Enter key: " GEMINI_KEY
sed -i "s|GEMINI_API_KEY=your_gemini_api_key_here|GEMINI_API_KEY=${GEMINI_KEY}|g" $ENV_FILE

echo ""
echo "2. ElevenLabs API Key"
echo "   Get from: https://elevenlabs.io/app/settings/api-keys"
read -p "   Enter key: " ELEVENLABS_KEY
sed -i "s|ELEVENLABS_API_KEY=your_elevenlabs_api_key_here|ELEVENLABS_API_KEY=${ELEVENLABS_KEY}|g" $ENV_FILE

if [ "$TARGET" = "local" ]; then
    echo ""
    echo "3. Storage Configuration (Local Development)"
    echo "   For local dev, files are typically stored on local filesystem"
    echo "   Press Enter to use local storage (recommended for development)"
    read -p "   " DUMMY
    echo -e "   ${GREEN}✓ Using local filesystem storage${NC}"
fi

if [ "$TARGET" = "gcp" ]; then
    echo ""
    echo "3. GCP Project ID"
    read -p "   Enter project ID: " PROJECT_ID
    sed -i "s|GCP_PROJECT_ID=your-gcp-project-id|GCP_PROJECT_ID=${PROJECT_ID}|g" $ENV_FILE
    
    echo ""
    echo "4. GCP Region (press Enter for us-central1)"
    read -p "   Enter region: " REGION
    if [ -n "$REGION" ]; then
        sed -i "s|GCP_REGION=us-central1|GCP_REGION=${REGION}|g" $ENV_FILE
    fi
    
    echo ""
    echo "5. Redis Host"
    read -p "   Enter Redis host: " REDIS_HOST
    if [ -n "$REDIS_HOST" ]; then
        sed -i "s|REDIS_HOST=your-redis-host-from-gcp|REDIS_HOST=${REDIS_HOST}|g" $ENV_FILE
    fi

    echo ""
    echo "6. Redis Username (Default: default)"
    read -p "   Enter Redis username: " REDIS_USER
    if [ -n "$REDIS_USER" ]; then
        # If env file doesn't have the var, append it, else replace
        if grep -q "REDIS_USERNAME=" $ENV_FILE; then
             sed -i "s|REDIS_USERNAME=.*|REDIS_USERNAME=${REDIS_USER}|g" $ENV_FILE
        else
             echo "REDIS_USERNAME=${REDIS_USER}" >> $ENV_FILE
        fi
    fi
    
    echo ""
    echo "7. Kafka Bootstrap Servers (from Confluent Cloud)"
    read -p "   Enter bootstrap servers: " KAFKA_SERVERS
    if [ -n "$KAFKA_SERVERS" ]; then
        sed -i "s|KAFKA_BOOTSTRAP_SERVERS=pkc-xxx.region.provider.confluent.cloud:9092|KAFKA_BOOTSTRAP_SERVERS=${KAFKA_SERVERS}|g" $ENV_FILE
    fi
    
    echo ""
    echo "8. Kafka API Key (from Confluent Cloud)"
    read -p "   Enter API key: " KAFKA_KEY
    if [ -n "$KAFKA_KEY" ]; then
        sed -i "s|KAFKA_API_KEY=your_kafka_api_key|KAFKA_API_KEY=${KAFKA_KEY}|g" $ENV_FILE
    fi
    
    echo ""
    echo "9. Kafka API Secret (from Confluent Cloud)"
    read -p "   Enter API secret: " KAFKA_SECRET
    if [ -n "$KAFKA_SECRET" ]; then
        sed -i "s|KAFKA_API_SECRET=your_kafka_api_secret|KAFKA_API_SECRET=${KAFKA_SECRET}|g" $ENV_FILE
    fi
    
    echo ""
    echo "10. GCS Storage Configuration"
    echo "    Storage backend for audio files (local or gcs)"
    read -p "    Use GCS storage? (Y/n): " USE_GCS
    if [[ ! $USE_GCS =~ ^[Nn]$ ]]; then
        # Set storage backend to gcs
        sed -i "s|STORAGE_BACKEND=local|STORAGE_BACKEND=gcs|g" $ENV_FILE
        
        # Set bucket name (default: radio-g-audio-{PROJECT_ID})
        DEFAULT_BUCKET="radio-g-audio-${PROJECT_ID}"
        echo ""
        echo "    GCS Bucket Name (press Enter for: ${DEFAULT_BUCKET})"
        read -p "    Enter bucket name: " BUCKET_NAME
        if [ -z "$BUCKET_NAME" ]; then
            BUCKET_NAME=$DEFAULT_BUCKET
        fi
        sed -i "s|GCS_BUCKET_NAME=.*|GCS_BUCKET_NAME=${BUCKET_NAME}|g" $ENV_FILE
        
        # Set project ID for GCS
        sed -i "s|GCS_PROJECT_ID=.*|GCS_PROJECT_ID=${PROJECT_ID}|g" $ENV_FILE
        
        # Set retention days
        echo ""
        echo "    Audio file retention (days before auto-deletion, press Enter for 1)"
        read -p "    Enter retention days: " RETENTION_DAYS
        if [ -z "$RETENTION_DAYS" ]; then
            RETENTION_DAYS=1
        fi
        sed -i "s|STORAGE_RETENTION_DAYS=.*|STORAGE_RETENTION_DAYS=${RETENTION_DAYS}|g" $ENV_FILE
        
        echo -e "    ${GREEN}✓ GCS storage configured (bucket: ${BUCKET_NAME}, retention: ${RETENTION_DAYS} days)${NC}"
    else
        echo -e "    ${YELLOW}Using local storage (files stored on container filesystem)${NC}"
    fi
fi

echo ""
echo -e "${GREEN}✅ Configuration file created: $ENV_FILE${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
if [ "$TARGET" = "local" ]; then
    echo "  1. Review and edit $ENV_FILE if needed"
    echo "  2. Run: ./scripts/deploy.sh $ENV_FILE"
    echo ""
    echo -e "${BLUE}Local Storage:${NC}"
    echo "  • Audio files will be stored in ./audio_output directory"
    echo "  • Files persist on local filesystem"
else
    echo "  1. Review and edit $ENV_FILE if needed"
    echo "  2. Ensure GCP infrastructure is set up"
    echo "  3. Run: ./scripts/deploy.sh $ENV_FILE"
    echo ""
    if [[ ! $USE_GCS =~ ^[Nn]$ ]]; then
        echo -e "${BLUE}GCS Storage:${NC}"
        echo "  • Bucket: gs://${BUCKET_NAME}"
        echo "  • Lifecycle: Audio files auto-delete after ${RETENTION_DAYS} day(s)"
        echo "  • Access: Public read, service account write"
        echo "  • Service Account: radio-g-storage-sa@${PROJECT_ID}.iam.gserviceaccount.com"
        echo ""
        echo -e "${YELLOW}Note: deploy.sh will automatically create bucket and configure permissions${NC}"
    else
        echo -e "${YELLOW}Warning: Using local storage in GCP Cloud Run is not recommended${NC}"
        echo "  • Files are ephemeral (deleted on container restart)"
        echo "  • Not shared across instances"
        echo "  • Consider enabling GCS storage for production"
    fi
fi
echo ""