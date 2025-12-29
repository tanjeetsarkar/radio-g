#!/bin/bash
# ============================================
# Deploy to Google Cloud Platform Script
# ============================================
set -e

echo "☁️  Radio-G GCP Deployment"
echo "=========================="

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-multilingual-news-radio}"
REGION="${GCP_REGION:-us-central1}"
REGISTRY="gcr.io"

echo -e "${BLUE}📋 Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Registry: $REGISTRY"
echo ""

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

# Verify gcloud authentication
echo -e "${BLUE}🔐 Verifying GCP authentication...${NC}"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}⚠️  Not authenticated. Running gcloud auth login...${NC}"
    gcloud auth login
fi

# Set project
echo -e "${BLUE}📦 Setting GCP project...${NC}"
gcloud config set project $PROJECT_ID

# Configure Docker for GCR
echo -e "${BLUE}🐳 Configuring Docker for GCR...${NC}"
gcloud auth configure-docker

# Load environment variables for production
if [ -f .env.production ]; then
    echo -e "${BLUE}📋 Loading production environment variables...${NC}"
    source .env.production
else
    echo -e "${YELLOW}⚠️  .env.production not found, using .env${NC}"
    source .env
fi

# Verify required secrets exist
echo -e "${BLUE}🔐 Checking GCP secrets...${NC}"
REQUIRED_SECRETS=("gemini-api-key" "elevenlabs-api-key")

for secret in "${REQUIRED_SECRETS[@]}"; do
    if ! gcloud secrets describe $secret &>/dev/null; then
        echo -e "${RED}❌ Secret '$secret' not found${NC}"
        echo "Create it with: echo -n 'YOUR_KEY' | gcloud secrets create $secret --data-file=-"
        exit 1
    fi
done

echo -e "${GREEN}✅ All required secrets exist${NC}"

# Build and push images
echo ""
echo -e "${BLUE}🔨 Building and pushing Docker images...${NC}"

IMAGES=("api" "fetcher" "processor")

for image in "${IMAGES[@]}"; do
    IMAGE_NAME="news-${image}"
    IMAGE_TAG="${REGISTRY}/${PROJECT_ID}/${IMAGE_NAME}:latest"
    DOCKERFILE="Dockerfile.${image}"
    
    echo -e "${BLUE}Building ${IMAGE_NAME}...${NC}"
    docker build -f $DOCKERFILE -t $IMAGE_TAG .
    
    echo -e "${BLUE}Pushing ${IMAGE_NAME}...${NC}"
    docker push $IMAGE_TAG
    
    echo -e "${GREEN}✅ ${IMAGE_NAME} pushed successfully${NC}"
done

# Build and push frontend
echo -e "${BLUE}Building frontend...${NC}"
cd frontend
docker build \
    --build-arg NEXT_PUBLIC_API_URL="https://news-api-${PROJECT_ID}.${REGION}.run.app" \
    -t ${REGISTRY}/${PROJECT_ID}/news-frontend:latest .

echo -e "${BLUE}Pushing frontend...${NC}"
docker push ${REGISTRY}/${PROJECT_ID}/news-frontend:latest
echo -e "${GREEN}✅ Frontend pushed successfully${NC}"
cd ..

echo ""
echo -e "${GREEN}✅ All images built and pushed${NC}"

# Deploy to Cloud Run
echo ""
echo -e "${BLUE}🚀 Deploying services to Cloud Run...${NC}"

# Get infrastructure connection details
echo -e "${BLUE}📋 Getting infrastructure details...${NC}"
REDIS_HOST=$(gcloud redis instances describe news-redis --region=$REGION --format="value(host)" 2>/dev/null || echo "")

if [ -z "$REDIS_HOST" ]; then
    echo -e "${YELLOW}⚠️  Redis instance not found. Create it first:${NC}"
    echo "  gcloud redis instances create news-redis --size=1 --region=$REGION --redis-version=redis_7_0 --tier=basic --enable-auth"
    exit 1
fi

# Deploy API Service
echo -e "${BLUE}Deploying API service...${NC}"
gcloud run deploy news-api \
    --image ${REGISTRY}/${PROJECT_ID}/news-api:latest \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 8080 \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 1 \
    --max-instances 10 \
    --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=INFO,REDIS_HOST=${REDIS_HOST},KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS}" \
    --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,ELEVENLABS_API_KEY=elevenlabs-api-key:latest"

API_URL=$(gcloud run services describe news-api --region $REGION --format 'value(status.url)')
echo -e "${GREEN}✅ API deployed: ${API_URL}${NC}"

# Deploy Processor Service
echo -e "${BLUE}Deploying processor service...${NC}"
gcloud run deploy news-processor \
    --image ${REGISTRY}/${PROJECT_ID}/news-processor:latest \
    --platform managed \
    --region $REGION \
    --no-allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 1 \
    --max-instances 10 \
    --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=INFO,REDIS_HOST=${REDIS_HOST},KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS}" \
    --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,ELEVENLABS_API_KEY=elevenlabs-api-key:latest"

echo -e "${GREEN}✅ Processor deployed${NC}"

# Deploy Fetcher as Cloud Run Job
echo -e "${BLUE}Deploying fetcher job...${NC}"
gcloud run jobs deploy news-fetcher \
    --image ${REGISTRY}/${PROJECT_ID}/news-fetcher:latest \
    --region $REGION \
    --memory 512Mi \
    --cpu 1 \
    --task-timeout 15m \
    --max-retries 3 \
    --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=INFO,REDIS_HOST=${REDIS_HOST},KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS}" \
    --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,ELEVENLABS_API_KEY=elevenlabs-api-key:latest" \
    || echo "Job already exists, updating..."

echo -e "${GREEN}✅ Fetcher job deployed${NC}"

# Create/update Cloud Scheduler
echo -e "${BLUE}Setting up Cloud Scheduler...${NC}"
SCHEDULER_EXISTS=$(gcloud scheduler jobs list --location=$REGION --filter="name:fetch-news" --format="value(name)" | wc -l)

if [ "$SCHEDULER_EXISTS" -eq "0" ]; then
    gcloud scheduler jobs create http fetch-news \
        --location $REGION \
        --schedule "*/15 * * * *" \
        --uri "https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/news-fetcher:run" \
        --http-method POST \
        --oauth-service-account-email "${PROJECT_ID}@appspot.gserviceaccount.com"
    echo -e "${GREEN}✅ Scheduler created${NC}"
else
    echo -e "${YELLOW}⚠️  Scheduler already exists${NC}"
fi

# Deploy Frontend
echo -e "${BLUE}Deploying frontend...${NC}"
gcloud run deploy news-frontend \
    --image ${REGISTRY}/${PROJECT_ID}/news-frontend:latest \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 5 \
    --set-env-vars="NEXT_PUBLIC_API_URL=${API_URL}"

FRONTEND_URL=$(gcloud run services describe news-frontend --region $REGION --format 'value(status.url)')
echo -e "${GREEN}✅ Frontend deployed: ${FRONTEND_URL}${NC}"

# Run initial fetch
echo ""
echo -e "${BLUE}🚀 Triggering initial news fetch...${NC}"
gcloud run jobs execute news-fetcher --region $REGION --wait || echo "Job execution started"

# Verify deployment
echo ""
echo -e "${BLUE}🔍 Verifying deployment...${NC}"

sleep 10

if curl -f ${API_URL}/health &>/dev/null; then
    echo -e "${GREEN}✅ API is healthy${NC}"
else
    echo -e "${RED}❌ API health check failed${NC}"
fi

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}📊 Service URLs:${NC}"
echo "  • API:      ${API_URL}"
echo "  • API Docs: ${API_URL}/docs"
echo "  • Frontend: ${FRONTEND_URL}"
echo ""
echo -e "${BLUE}🔧 Useful commands:${NC}"
echo "  • View logs:     gcloud logging read \"resource.type=cloud_run_revision\" --limit 50"
echo "  • List services: gcloud run services list --region ${REGION}"
echo "  • Update API:    gcloud run deploy news-api --image ${REGISTRY}/${PROJECT_ID}/news-api:latest --region ${REGION}"
echo "  • Scale:         gcloud run services update news-processor --min-instances 2 --region ${REGION}"
echo ""
echo -e "${BLUE}📈 Monitoring:${NC}"
echo "  • Cloud Console: https://console.cloud.google.com/run?project=${PROJECT_ID}"
echo "  • Logs:          https://console.cloud.google.com/logs/query?project=${PROJECT_ID}"
echo ""
