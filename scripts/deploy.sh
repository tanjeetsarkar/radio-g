#!/bin/bash
# ============================================
# Unified Deployment Script
# Usage: ./scripts/deploy.sh <env-file>
# Example: ./scripts/deploy.sh .env        (for local)
#          ./scripts/deploy.sh .env.prod   (for production/GCP)
# ============================================
set -e

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Display usage
usage() {
    echo "Usage: $0 <env-file>"
    echo ""
    echo "Examples:"
    echo "  $0 .env           # Deploy locally"
    echo "  $0 .env.prod      # Deploy to GCP"
    echo ""
    exit 1
}

# Check arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}❌ Error: Environment file not specified${NC}"
    usage
fi

ENV_FILE=$1

# Check if env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Error: Environment file '$ENV_FILE' not found${NC}"
    echo ""
    if [ "$ENV_FILE" = ".env" ]; then
        echo "Create it from template: cp .env.example .env"
    elif [ "$ENV_FILE" = ".env.prod" ]; then
        echo "Create it from template: cp .env.prod.example .env.prod"
    fi
    exit 1
fi

echo "🚀 Radio-G Deployment"
echo "====================="
echo ""
echo -e "${BLUE}📋 Using environment file: ${ENV_FILE}${NC}"

# Load environment variables
source "$ENV_FILE"

# Validate required variables
if [ -z "$DEPLOYMENT_TARGET" ]; then
    echo -e "${RED}❌ Error: DEPLOYMENT_TARGET not set in $ENV_FILE${NC}"
    echo "Add: DEPLOYMENT_TARGET=local or DEPLOYMENT_TARGET=gcp"
    exit 1
fi

if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" = "your_gemini_api_key_here" ]; then
    echo -e "${RED}❌ Error: GEMINI_API_KEY not configured in $ENV_FILE${NC}"
    exit 1
fi

if [ -z "$ELEVENLABS_API_KEY" ] || [ "$ELEVENLABS_API_KEY" = "your_elevenlabs_api_key_here" ]; then
    echo -e "${RED}❌ Error: ELEVENLABS_API_KEY not configured in $ENV_FILE${NC}"
    exit 1
fi

echo -e "${BLUE}🎯 Deployment target: ${DEPLOYMENT_TARGET}${NC}"
echo -e "${BLUE}🌍 Environment: ${ENVIRONMENT}${NC}"
echo ""

# Deploy based on target
if [ "$DEPLOYMENT_TARGET" = "local" ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}🏠 LOCAL DEPLOYMENT${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo -e "${RED}❌ Docker daemon not running. Please start Docker.${NC}"
        exit 1
    fi
    
    # Stop any existing containers
    echo -e "${BLUE}🛑 Stopping existing containers...${NC}"
    docker compose down -v 2>/dev/null || true
    
    # Build images
    echo -e "${BLUE}🔨 Building Docker images...${NC}"
    docker compose build --no-cache
    
    echo -e "${GREEN}✅ Images built successfully${NC}"
    
    # Start infrastructure
    echo -e "${BLUE}🏗️  Starting infrastructure services...${NC}"
    docker compose up -d redis zookeeper kafka
    
    echo "⏳ Waiting for infrastructure to be ready..."
    sleep 20
    
    # Check Kafka health
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
    
    
    # Seed language configuration using dedicated seed service
    # echo -e "${BLUE}💾 Seeding language configuration...${NC}"
    # docker compose run --rm news-seed
    
    # echo -e "${GREEN}✅ Language configuration seeded${NC}"
    
    # Start application services
    echo -e "${BLUE}🚀 Starting application services...${NC}"
    docker compose up -d news-fetcher news-processor news-api
    
    echo "⏳ Waiting for API to be healthy..."
    sleep 30
    
    # Wait for API
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
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ Local deployment complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}📊 Service URLs:${NC}"
    echo "  • Frontend:   http://localhost:3000"
    echo "  • API:        http://localhost:8000"
    echo "  • API Docs:   http://localhost:8000/docs"
    echo "  • Kafka UI:   http://localhost:8080"
    echo ""
    
    # Run tests
    echo -e "${BLUE}🧪 Running deployment tests...${NC}"
    echo ""
    sleep 5
    ./scripts/test_deployment.sh
    
elif [ "$DEPLOYMENT_TARGET" = "gcp" ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}☁️  GCP DEPLOYMENT${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    
    # Validate GCP-specific variables
    if [ -z "$GCP_PROJECT_ID" ] || [ "$GCP_PROJECT_ID" = "your-gcp-project-id" ]; then
        echo -e "${RED}❌ Error: GCP_PROJECT_ID not configured in $ENV_FILE${NC}"
        exit 1
    fi
    
    if [ -z "$GCP_REGION" ]; then
        GCP_REGION="us-central1"
        echo -e "${YELLOW}⚠️  GCP_REGION not set, using default: $GCP_REGION${NC}"
    fi
    
    # Check prerequisites
    echo -e "${BLUE}🔍 Checking prerequisites...${NC}"
    
    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}❌ gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install${NC}"
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker not found${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Prerequisites check passed${NC}"
    
    # Verify authentication
    echo -e "${BLUE}🔐 Verifying GCP authentication...${NC}"
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        echo -e "${YELLOW}⚠️  Not authenticated. Running gcloud auth login...${NC}"
        gcloud auth login
    fi
    
    # Set project
    echo -e "${BLUE}📦 Setting GCP project...${NC}"
    gcloud config set project $GCP_PROJECT_ID
    
    # Configure Docker for GCR
    echo -e "${BLUE}🐳 Configuring Docker for GCR...${NC}"
    gcloud auth configure-docker
    
    # Check secrets
    echo -e "${BLUE}🔐 Checking GCP secrets...${NC}"
    REQUIRED_SECRETS=("gemini-api-key" "elevenlabs-api-key")
    
    for secret in "${REQUIRED_SECRETS[@]}"; do
        if ! gcloud secrets describe $secret &>/dev/null; then
            echo -e "${YELLOW}⚠️  Secret '$secret' not found. Creating...${NC}"
            if [ "$secret" = "gemini-api-key" ]; then
                echo -n "$GEMINI_API_KEY" | gcloud secrets create $secret --data-file=-
            elif [ "$secret" = "elevenlabs-api-key" ]; then
                echo -n "$ELEVENLABS_API_KEY" | gcloud secrets create $secret --data-file=-
            fi
        fi
    done
    
    # Check and create Kafka credentials secrets
    if [ -n "${KAFKA_USERNAME}" ] && [ "${KAFKA_USERNAME}" != "" ]; then
        if ! gcloud secrets describe kafka-username &>/dev/null; then
            echo -e "${YELLOW}⚠️  Secret 'kafka-username' not found. Creating...${NC}"
            echo -n "$KAFKA_USERNAME" | gcloud secrets create kafka-username --data-file=-
        else
            echo -e "${BLUE}Updating kafka-username secret...${NC}"
            echo -n "$KAFKA_USERNAME" | gcloud secrets versions add kafka-username --data-file=-
        fi
    fi
    
    if [ -n "${KAFKA_PASSWORD}" ] && [ "${KAFKA_PASSWORD}" != "" ]; then
        if ! gcloud secrets describe kafka-password &>/dev/null; then
            echo -e "${YELLOW}⚠️  Secret 'kafka-password' not found. Creating...${NC}"
            echo -n "$KAFKA_PASSWORD" | gcloud secrets create kafka-password --data-file=-
        else
            echo -e "${BLUE}Updating kafka-password secret...${NC}"
            echo -n "$KAFKA_PASSWORD" | gcloud secrets versions add kafka-password --data-file=-
        fi
    fi
    
    if [ -n "${KAFKA_CREDENTIALS}" ] && [ "${KAFKA_CREDENTIALS}" != "" ]; then
        if ! gcloud secrets describe kafka-credentials &>/dev/null; then
            echo -e "${YELLOW}⚠️  Secret 'kafka-credentials' not found. Creating...${NC}"
            echo -n "$KAFKA_CREDENTIALS" | gcloud secrets create kafka-credentials --data-file=-
        else
            echo -e "${BLUE}Updating kafka-credentials secret...${NC}"
            echo -n "$KAFKA_CREDENTIALS" | gcloud secrets versions add kafka-credentials --data-file=-
        fi
    fi
    
    echo -e "${GREEN}✅ All required secrets exist${NC}"
    
    # Build and push images
    echo ""
    echo -e "${BLUE}🔨 Building and pushing Docker images...${NC}"
    
    REGISTRY="gcr.io"
    IMAGES=("api" "fetcher" "processor")
    
    for image in "${IMAGES[@]}"; do
        IMAGE_NAME="news-${image}"
        IMAGE_TAG="${REGISTRY}/${GCP_PROJECT_ID}/${IMAGE_NAME}:latest"
        DOCKERFILE="Dockerfile.${image}"
        
        echo -e "${BLUE}Building ${IMAGE_NAME}...${NC}"
        docker build -f $DOCKERFILE -t $IMAGE_TAG .
        
        echo -e "${BLUE}Pushing ${IMAGE_NAME}...${NC}"
        docker push $IMAGE_TAG
        
        echo -e "${GREEN}✅ ${IMAGE_NAME} pushed successfully${NC}"
    done
    
    # Build and push frontend
    echo -e "${BLUE}Building frontend...${NC}"
    
    # Use API URL from environment or construct default
    if [ -z "$NEXT_PUBLIC_API_URL" ]; then
        API_URL="https://news-api-${GCP_PROJECT_ID}.${GCP_REGION}.run.app"
        echo -e "${YELLOW}⚠️  NEXT_PUBLIC_API_URL not set, using default: $API_URL${NC}"
    else
        API_URL="$NEXT_PUBLIC_API_URL"
        echo -e "${GREEN}✅ Using NEXT_PUBLIC_API_URL from environment: $API_URL${NC}"
    fi
    
    cd frontend
    docker build \
        --build-arg NEXT_PUBLIC_API_URL="$API_URL" \
        -t ${REGISTRY}/${GCP_PROJECT_ID}/news-frontend:latest .
    
    echo -e "${BLUE}Pushing frontend...${NC}"
    docker push ${REGISTRY}/${GCP_PROJECT_ID}/news-frontend:latest
    echo -e "${GREEN}✅ Frontend pushed successfully${NC}"
    cd ..
    
    echo ""
    echo -e "${GREEN}✅ All images built and pushed${NC}"
    
    # Deploy to Cloud Run
    echo ""
    echo -e "${BLUE}🚀 Deploying services to Cloud Run...${NC}"
    
    # Get Redis host (Prioritize env file for Public Redis)
    if [ -n "$REDIS_HOST" ]; then
        echo -e "${GREEN}✅ Using Redis from environment: $REDIS_HOST${NC}"
        REDIS_HOST_GCP=$REDIS_HOST
    else
        # Fallback to GCP Memorystore lookup
        REDIS_HOST_GCP=$(gcloud redis instances describe news-redis --region=$GCP_REGION --format="value(host)" 2>/dev/null || echo "")
        if [ -n "$REDIS_HOST_GCP" ]; then
             echo -e "${GREEN}✅ Found GCP Redis instance: $REDIS_HOST_GCP${NC}"
        else
             echo -e "${RED}❌ Redis Host not found in environment or GCP.${NC}"
             exit 1
        fi
    fi
    
    # Construct Kafka bootstrap servers
    KAFKA_BOOTSTRAP="${KAFKA_BOOTSTRAP_SERVERS}"
    
    # Determine which Kafka secrets to use
    KAFKA_SECRETS=""
    if [ -n "${KAFKA_CREDENTIALS}" ] && [ "${KAFKA_CREDENTIALS}" != "" ]; then
        echo -e "${GREEN}✅ Using KAFKA_CREDENTIALS from secrets${NC}"
        KAFKA_SECRETS="KAFKA_CREDENTIALS=kafka-credentials:latest"
    elif [ -n "${KAFKA_USERNAME}" ] && [ -n "${KAFKA_PASSWORD}" ]; then
        echo -e "${GREEN}✅ Using KAFKA_USERNAME and KAFKA_PASSWORD from secrets${NC}"
        KAFKA_SECRETS="KAFKA_USERNAME=kafka-username:latest,KAFKA_PASSWORD=kafka-password:latest"
    else
        echo -e "${YELLOW}⚠️  No Kafka credentials found - using unauthenticated connection${NC}"
    fi
    
    # Deploy API Service
    echo -e "${BLUE}Deploying API service...${NC}"
    
    # Create temporary env vars file to handle special characters in URLs
    # Added REDIS_USERNAME, PORT, PASSWORD, SSL
    cat > /tmp/api-env-vars.yaml <<EOF
ENVIRONMENT: "${ENVIRONMENT}"
LOG_LEVEL: "${LOG_LEVEL}"
REDIS_HOST: "${REDIS_HOST_GCP}"
REDIS_PORT: "${REDIS_PORT:-6379}"
REDIS_PASSWORD: "${REDIS_PASSWORD}"
REDIS_USERNAME: "${REDIS_USERNAME:-default}"
REDIS_SSL: "${REDIS_SSL:-false}"
REDIS_DB: "0"
KAFKA_BOOTSTRAP_SERVERS: "${KAFKA_BOOTSTRAP}"
TRANSLATION_PROVIDER: "${TRANSLATION_PROVIDER:-gemini}"
TTS_PROVIDER: "${TTS_PROVIDER:-elevenlabs}"
ALLOWED_ORIGINS: "${ALLOWED_ORIGINS}"
EOF
    
    # Build secrets string
    API_SECRETS="GEMINI_API_KEY=gemini-api-key:latest,ELEVENLABS_API_KEY=elevenlabs-api-key:latest"
    if [ -n "${KAFKA_SECRETS}" ]; then
        API_SECRETS="${API_SECRETS},${KAFKA_SECRETS}"
    fi
    
    gcloud run deploy news-api \
        --image ${REGISTRY}/${GCP_PROJECT_ID}/news-api:latest \
        --platform managed \
        --region $GCP_REGION \
        --allow-unauthenticated \
        --port 8000 \
        --timeout 300 \
        --cpu-boost \
        --memory ${API_MEMORY:-1Gi} \
        --cpu ${API_CPU:-1} \
        --min-instances ${API_MIN_INSTANCES:-1} \
        --max-instances ${API_MAX_INSTANCES:-10} \
        --env-vars-file=/tmp/api-env-vars.yaml \
        --set-secrets="${API_SECRETS}"
    
    # Clean up
    rm /tmp/api-env-vars.yaml
    
    DEPLOYED_API_URL=$(gcloud run services describe news-api --region $GCP_REGION --format 'value(status.url)')
    echo -e "${GREEN}✅ API deployed: ${DEPLOYED_API_URL}${NC}"

    # Prepare common env vars string for other services (including new Redis vars)
    COMMON_ENV_VARS="ENVIRONMENT=${ENVIRONMENT},LOG_LEVEL=${LOG_LEVEL},REDIS_HOST=${REDIS_HOST_GCP},REDIS_PORT=${REDIS_PORT:-6379},REDIS_PASSWORD=${REDIS_PASSWORD},REDIS_USERNAME=${REDIS_USERNAME:-default},REDIS_SSL=${REDIS_SSL:-false},KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP}"
    
    # Deploy Processor Service
    echo -e "${BLUE}Deploying processor service...${NC}"
    
    # Build secrets string for processor
    PROCESSOR_SECRETS="GEMINI_API_KEY=gemini-api-key:latest,ELEVENLABS_API_KEY=elevenlabs-api-key:latest"
    if [ -n "${KAFKA_SECRETS}" ]; then
        PROCESSOR_SECRETS="${PROCESSOR_SECRETS},${KAFKA_SECRETS}"
    fi
    
    gcloud run deploy news-processor \
        --image ${REGISTRY}/${GCP_PROJECT_ID}/news-processor:latest \
        --platform managed \
        --region $GCP_REGION \
        --no-allow-unauthenticated \
        --port 8080 \
        --timeout 300 \
        --memory ${PROCESSOR_MEMORY:-2Gi} \
        --cpu ${PROCESSOR_CPU:-2} \
        --min-instances ${PROCESSOR_MIN_INSTANCES:-1} \
        --max-instances ${PROCESSOR_MAX_INSTANCES:-10} \
        --set-env-vars="${COMMON_ENV_VARS},TRANSLATION_PROVIDER=${TRANSLATION_PROVIDER:-gemini},TTS_PROVIDER=${TTS_PROVIDER:-elevenlabs},GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION:-global},GOOGLE_GENAI_USE_VERTEXAI=${GOOGLE_GENAI_USE_VERTEXAI:-True}" \
        --set-secrets="${PROCESSOR_SECRETS}"
    
    echo -e "${GREEN}✅ Processor deployed${NC}"
    
    # Deploy Fetcher Service
    echo -e "${BLUE}Deploying fetcher service...${NC}"
    
    # Build secrets string for fetcher
    FETCHER_SECRETS="GEMINI_API_KEY=gemini-api-key:latest,ELEVENLABS_API_KEY=elevenlabs-api-key:latest"
    if [ -n "${KAFKA_SECRETS}" ]; then
        FETCHER_SECRETS="${FETCHER_SECRETS},${KAFKA_SECRETS}"
    fi
    
    gcloud run deploy news-fetcher \
        --image ${REGISTRY}/${GCP_PROJECT_ID}/news-fetcher:latest \
        --platform managed \
        --region $GCP_REGION \
        --no-allow-unauthenticated \
        --port 8080 \
        --timeout 300 \
        --memory ${FETCHER_MEMORY:-512Mi} \
        --cpu ${FETCHER_CPU:-1} \
        --min-instances ${FETCHER_MIN_INSTANCES:-1} \
        --max-instances ${FETCHER_MAX_INSTANCES:-3} \
        --set-env-vars="${COMMON_ENV_VARS}" \
        --set-secrets="${FETCHER_SECRETS}"
    
    echo -e "${GREEN}✅ Fetcher deployed${NC}"
    
    # Deploy Frontend
    echo -e "${BLUE}Deploying frontend...${NC}"
    gcloud run deploy news-frontend \
        --image ${REGISTRY}/${GCP_PROJECT_ID}/news-frontend:latest \
        --platform managed \
        --region $GCP_REGION \
        --allow-unauthenticated \
        --memory ${FRONTEND_MEMORY:-512Mi} \
        --cpu ${FRONTEND_CPU:-1} \
        --min-instances ${FRONTEND_MIN_INSTANCES:-0} \
        --max-instances ${FRONTEND_MAX_INSTANCES:-5} \
        --set-env-vars="NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}"
    
    FRONTEND_URL=$(gcloud run services describe news-frontend --region $GCP_REGION --format 'value(status.url)')
    echo -e "${GREEN}✅ Frontend deployed: ${FRONTEND_URL}${NC}"

    # Auto-update CORS (New Feature)
    echo -e "${BLUE}🔄 Updating CORS configuration...${NC}"
    NEW_ALLOWED_ORIGINS="${ALLOWED_ORIGINS},${FRONTEND_URL}"
    
    # Create complete env vars file to update CORS without losing other vars
    cat > /tmp/api-update-env-vars.yaml <<EOF
ENVIRONMENT: "${ENVIRONMENT}"
LOG_LEVEL: "${LOG_LEVEL}"
REDIS_HOST: "${REDIS_HOST_GCP}"
REDIS_PORT: "${REDIS_PORT:-6379}"
REDIS_PASSWORD: "${REDIS_PASSWORD}"
REDIS_USERNAME: "${REDIS_USERNAME:-default}"
REDIS_SSL: "${REDIS_SSL:-false}"
REDIS_DB: "0"
KAFKA_BOOTSTRAP_SERVERS: "${KAFKA_BOOTSTRAP}"
TRANSLATION_PROVIDER: "${TRANSLATION_PROVIDER:-gemini}"
TTS_PROVIDER: "${TTS_PROVIDER:-elevenlabs}"
ALLOWED_ORIGINS: "${NEW_ALLOWED_ORIGINS}"
EOF
    
    gcloud run services update news-api \
        --region $GCP_REGION \
        --env-vars-file=/tmp/api-update-env-vars.yaml
    
    # Clean up
    rm /tmp/api-update-env-vars.yaml
    
    echo -e "${GREEN}✅ CORS updated${NC}"
    
    # Verify deployment
    echo ""
    echo -e "${BLUE}🔍 Verifying deployment...${NC}"
    echo -e "${BLUE}⏳ Waiting for services to be ready (30s)...${NC}"
    sleep 30
    
    # if curl -f ${DEPLOYED_API_URL}/health &>/dev/null; then
    #     echo -e "${GREEN}✅ API is healthy${NC}"
    # else
    #     echo -e "${RED}❌ API health check failed${NC}"
    #     echo -e "${YELLOW}⚠️  This might be normal if services are still initializing${NC}"
    #     echo -e "${YELLOW}⚠️  Check logs: gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=news-api\" --limit 20${NC}"
    # fi
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}🎉 GCP deployment complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}📊 Service URLs:${NC}"
    echo "  • API:      ${DEPLOYED_API_URL}"
    echo "  • API Docs: ${DEPLOYED_API_URL}/docs"
    echo "  • Frontend: ${FRONTEND_URL}"
    echo ""
    echo -e "${BLUE}🔧 Useful commands:${NC}"
    echo "  • View logs:     gcloud logging read \"resource.type=cloud_run_revision\" --limit 50"
    echo "  • List services: gcloud run services list --region ${GCP_REGION}"
    echo "  • Scale:         gcloud run services update news-processor --min-instances 2 --region ${GCP_REGION}"
    echo ""
    echo -e "${YELLOW}⚠️  Remember to seed languages locally: uv run python scripts/seed_languages.py${NC}"
    echo ""
    
else
    echo -e "${RED}❌ Error: Invalid DEPLOYMENT_TARGET: $DEPLOYMENT_TARGET${NC}"
    echo "Valid values are: local, gcp"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"