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
    
    
    echo -e "${GREEN}✅ Language configuration seeded${NC}"
    
    # Start application services
    echo -e "${BLUE}🚀 Starting application services...${NC}"
    docker compose up -d news-fetcher news-processor news-api
    
    echo "⏳ Waiting for API to be healthy..."
    sleep 30
    
    # Seed language configuration
    echo -e "${BLUE}💾 Seeding language configuration...${NC}"
    docker compose exec -T news-api uv run python /app/scripts/seed_languages.py
    
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
    
    # Construct API URL
    API_URL="https://news-api-${GCP_PROJECT_ID}.${GCP_REGION}.run.app"
    
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
    
    # Get Redis host
    REDIS_HOST_GCP=$(gcloud redis instances describe news-redis --region=$GCP_REGION --format="value(host)" 2>/dev/null || echo "")
    
    if [ -z "$REDIS_HOST_GCP" ]; then
        echo -e "${YELLOW}⚠️  Using Redis host from env file: $REDIS_HOST${NC}"
        REDIS_HOST_GCP=$REDIS_HOST
    else
        echo -e "${GREEN}✅ Found Redis instance: $REDIS_HOST_GCP${NC}"
    fi
    
    # Construct Kafka bootstrap servers
    KAFKA_BOOTSTRAP="${KAFKA_BOOTSTRAP_SERVERS}"
    
    # Deploy API Service
    echo -e "${BLUE}Deploying API service...${NC}"
    gcloud run deploy news-api \
        --image ${REGISTRY}/${GCP_PROJECT_ID}/news-api:latest \
        --platform managed \
        --region $GCP_REGION \
        --allow-unauthenticated \
        --port 8080 \
        --memory ${API_MEMORY:-1Gi} \
        --cpu ${API_CPU:-1} \
        --min-instances ${API_MIN_INSTANCES:-1} \
        --max-instances ${API_MAX_INSTANCES:-10} \
        --set-env-vars="ENVIRONMENT=${ENVIRONMENT},LOG_LEVEL=${LOG_LEVEL},REDIS_HOST=${REDIS_HOST_GCP},KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP},ALLOWED_ORIGINS=${ALLOWED_ORIGINS}" \
        --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,ELEVENLABS_API_KEY=elevenlabs-api-key:latest"
    
    DEPLOYED_API_URL=$(gcloud run services describe news-api --region $GCP_REGION --format 'value(status.url)')
    echo -e "${GREEN}✅ API deployed: ${DEPLOYED_API_URL}${NC}"
    
    # Deploy Processor Service
    echo -e "${BLUE}Deploying processor service...${NC}"
    gcloud run deploy news-processor \
        --image ${REGISTRY}/${GCP_PROJECT_ID}/news-processor:latest \
        --platform managed \
        --region $GCP_REGION \
        --no-allow-unauthenticated \
        --memory ${PROCESSOR_MEMORY:-2Gi} \
        --cpu ${PROCESSOR_CPU:-2} \
        --min-instances ${PROCESSOR_MIN_INSTANCES:-1} \
        --max-instances ${PROCESSOR_MAX_INSTANCES:-10} \
        --set-env-vars="ENVIRONMENT=${ENVIRONMENT},LOG_LEVEL=${LOG_LEVEL},REDIS_HOST=${REDIS_HOST_GCP},KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP}" \
        --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,ELEVENLABS_API_KEY=elevenlabs-api-key:latest"
    
    echo -e "${GREEN}✅ Processor deployed${NC}"
    
    # Deploy Fetcher as Cloud Run Job
    echo -e "${BLUE}Deploying fetcher job...${NC}"
    gcloud run jobs deploy news-fetcher \
        --image ${REGISTRY}/${GCP_PROJECT_ID}/news-fetcher:latest \
        --region $GCP_REGION \
        --memory ${FETCHER_MEMORY:-512Mi} \
        --cpu ${FETCHER_CPU:-1} \
        --task-timeout ${FETCHER_TIMEOUT:-15m} \
        --max-retries 3 \
        --set-env-vars="ENVIRONMENT=${ENVIRONMENT},LOG_LEVEL=${LOG_LEVEL},REDIS_HOST=${REDIS_HOST_GCP},KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP}" \
        --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,ELEVENLABS_API_KEY=elevenlabs-api-key:latest" \
        2>/dev/null || echo "Job already exists, updating..."
    
    echo -e "${GREEN}✅ Fetcher job deployed${NC}"
    
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
        --set-env-vars="NEXT_PUBLIC_API_URL=${DEPLOYED_API_URL}"
    
    FRONTEND_URL=$(gcloud run services describe news-frontend --region $GCP_REGION --format 'value(status.url)')
    echo -e "${GREEN}✅ Frontend deployed: ${FRONTEND_URL}${NC}"
    
    # Trigger initial fetch
    echo ""
    echo -e "${BLUE}🚀 Triggering initial news fetch...${NC}"
    gcloud run jobs execute news-fetcher --region $GCP_REGION --wait || echo "Job execution started in background"
    
    # Verify deployment
    echo ""
    echo -e "${BLUE}🔍 Verifying deployment...${NC}"
    sleep 10
    
    if curl -f ${DEPLOYED_API_URL}/health &>/dev/null; then
        echo -e "${GREEN}✅ API is healthy${NC}"
    else
        echo -e "${RED}❌ API health check failed${NC}"
    fi
    
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
    
else
    echo -e "${RED}❌ Error: Invalid DEPLOYMENT_TARGET: $DEPLOYMENT_TARGET${NC}"
    echo "Valid values are: local, gcp"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
