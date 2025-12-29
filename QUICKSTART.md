# 🚀 Quick Deployment Guide

This guide walks you through deploying Radio-G locally and to Google Cloud Platform (GCP).

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Deployment](#local-deployment)
3. [GCP Deployment](#gcp-deployment)
4. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
- **Docker** (v20.10+) and **Docker Compose** (v2.0+)
- **Python** (3.13+) with **uv** package manager
- **Node.js** (20+) and **npm**
- **gcloud CLI** (for GCP deployment)

### Required API Keys
- **Google Gemini API Key** - Get from: https://aistudio.google.com/apikey
- **ElevenLabs API Key** - Get from: https://elevenlabs.io/app/settings/api-keys

### Install Prerequisites

```bash
# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 🏠 Local Deployment

### Step 1: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

Update these required values in `.env`:
```bash
GEMINI_API_KEY=your_actual_gemini_api_key
ELEVENLABS_API_KEY=your_actual_elevenlabs_api_key
```

### Step 2: Build and Run

```bash
# Run the automated build script
./scripts/build_and_run_local.sh
```

This script will:
1. ✅ Check environment variables
2. 🔨 Build all Docker images
3. 🏗️ Start infrastructure (Redis, Kafka)
4. 💾 Seed language configuration
5. 🚀 Start application services
6. 🎨 Start frontend

**Expected output:**
```
✅ All services started successfully!

📊 Service URLs:
  • API:        http://localhost:8000
  • API Docs:   http://localhost:8000/docs
  • Frontend:   http://localhost:3000
  • Kafka UI:   http://localhost:8080
```

### Step 3: Test the Deployment

```bash
# Run comprehensive tests
./scripts/test_deployment.sh
```

This will verify:
- ✅ Infrastructure services (Redis, Kafka)
- ✅ Application services (Fetcher, Processor, API)
- ✅ API endpoints and responses
- ✅ Frontend accessibility
- ✅ Docker health checks

### Step 4: Use the Application

Open your browser to:
- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Kafka UI**: http://localhost:8080

### Managing Local Services

```bash
# View all services
docker compose ps

# View logs
docker compose logs -f                    # All services
docker compose logs -f news-api           # Specific service

# Restart a service
docker compose restart news-processor

# Scale processor service
docker compose up -d --scale news-processor=3

# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v
```

---

## ☁️ GCP Deployment

### Step 1: GCP Project Setup

```bash
# Set your project ID
export GCP_PROJECT_ID=your-project-id
export GCP_REGION=us-central1

# Create project
gcloud projects create $GCP_PROJECT_ID --name="Radio-G"
gcloud config set project $GCP_PROJECT_ID

# Enable billing (required)
# Visit: https://console.cloud.google.com/billing

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  redis.googleapis.com \
  secretmanager.googleapis.com \
  cloudlogging.googleapis.com \
  monitoring.googleapis.com \
  storage.googleapis.com \
  cloudscheduler.googleapis.com
```

### Step 2: Infrastructure Setup

#### A. Create Redis Instance

```bash
gcloud redis instances create news-redis \
  --size=1 \
  --region=$GCP_REGION \
  --redis-version=redis_7_0 \
  --tier=basic \
  --enable-auth

# Get connection details
export REDIS_HOST=$(gcloud redis instances describe news-redis \
  --region=$GCP_REGION --format="value(host)")
echo "Redis Host: $REDIS_HOST"
```

#### B. Setup Kafka (Confluent Cloud)

1. Sign up at https://www.confluent.io/get-started/
2. Create a **Basic** cluster (~$0.50/hr)
3. Create topics:
   - `raw-news-feed` (3 partitions, 7 days retention)
   - `news-english` (3 partitions, 30 days retention)
   - `news-hindi` (3 partitions, 30 days retention)
   - `news-bengali` (3 partitions, 30 days retention)
4. Create API key and secret

```bash
# Save Kafka credentials
export KAFKA_BOOTSTRAP_SERVERS=pkc-xxx.us-east-1.aws.confluent.cloud:9092
export KAFKA_API_KEY=your_kafka_api_key
export KAFKA_API_SECRET=your_kafka_api_secret
```

#### C. Store Secrets in Secret Manager

```bash
# Store API keys
echo -n "$GEMINI_API_KEY" | \
  gcloud secrets create gemini-api-key --data-file=-

echo -n "$ELEVENLABS_API_KEY" | \
  gcloud secrets create elevenlabs-api-key --data-file=-

echo -n "${KAFKA_API_KEY}:${KAFKA_API_SECRET}" | \
  gcloud secrets create kafka-credentials --data-file=-
```

#### D. Create Cloud Storage Bucket (Optional)

```bash
export BUCKET_NAME=${GCP_PROJECT_ID}-audio-files

gsutil mb -p $GCP_PROJECT_ID -l $GCP_REGION gs://${BUCKET_NAME}
gsutil iam ch allUsers:objectViewer gs://${BUCKET_NAME}
```

### Step 3: Create Production Environment File

Create `.env.production`:

```bash
cat > .env.production << EOF
# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO

# API Keys (will be loaded from Secret Manager)
GEMINI_API_KEY=\${GEMINI_API_KEY}
ELEVENLABS_API_KEY=\${ELEVENLABS_API_KEY}

# Service Providers
TRANSLATION_PROVIDER=gemini
TTS_PROVIDER=elevenlabs

# Kafka (Confluent Cloud)
KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS}
KAFKA_CREDENTIALS=${KAFKA_API_KEY}:${KAFKA_API_SECRET}

# Redis (GCP Memorystore)
REDIS_HOST=${REDIS_HOST}
REDIS_PORT=6379
REDIS_SSL=true

# Application
MAX_WORKERS=4
FETCH_INTERVAL_MINUTES=15
EOF
```

### Step 4: Deploy to GCP

```bash
# Run automated deployment script
./scripts/deploy_to_gcp.sh
```

This script will:
1. ✅ Verify prerequisites and authentication
2. 🔨 Build Docker images
3. 📤 Push images to Google Container Registry
4. 🚀 Deploy services to Cloud Run
5. ⏰ Setup Cloud Scheduler for fetcher job
6. 🔍 Verify deployment

**Expected output:**
```
🎉 Deployment Complete!

📊 Service URLs:
  • API:      https://news-api-xxx.run.app
  • API Docs: https://news-api-xxx.run.app/docs
  • Frontend: https://news-frontend-xxx.run.app
```

### Step 5: Seed Language Configuration

```bash
# Connect to Redis and seed languages
gcloud redis instances describe news-redis --region=$GCP_REGION

# Use redis-cli or a script to set:
# SET languages:config '{"languages":[...]}'
```

### Step 6: Verify Deployment

```bash
# Get API URL
API_URL=$(gcloud run services describe news-api \
  --region $GCP_REGION --format 'value(status.url)')

# Test API
curl ${API_URL}/health
curl ${API_URL}/languages

# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```

---

## 🔧 Troubleshooting

### Local Deployment Issues

**Problem: Services fail to start**
```bash
# Check logs
docker compose logs [service-name]

# Restart services
docker compose restart

# Full reset
docker compose down -v
./scripts/build_and_run_local.sh
```

**Problem: Kafka not ready**
```bash
# Check Kafka health
docker compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Wait longer and retry
sleep 30
docker compose restart news-fetcher news-processor
```

**Problem: API returns 500 errors**
```bash
# Check if Redis has language config
docker compose exec redis redis-cli GET languages:config

# If empty, seed it:
docker compose exec redis redis-cli SET languages:config '{"languages":[{"code":"en","name":"English","voice_id":"21m00Tcm4TlvDq8ikWAM"}]}'
```

### GCP Deployment Issues

**Problem: Authentication failed**
```bash
gcloud auth login
gcloud auth configure-docker
```

**Problem: Service won't start**
```bash
# Check logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50 --format=json

# Check service status
gcloud run services describe news-api --region $GCP_REGION
```

**Problem: Secrets not accessible**
```bash
# Verify secrets exist
gcloud secrets list

# Grant access to service account
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:${GCP_PROJECT_ID}@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Common Issues

**Problem: Out of memory errors**
```bash
# Increase memory for service
gcloud run services update news-processor \
  --memory 4Gi --region $GCP_REGION
```

**Problem: High latency**
```bash
# Scale up instances
gcloud run services update news-api \
  --min-instances 2 --max-instances 20 \
  --region $GCP_REGION
```

---

## 📊 Monitoring

### Local Monitoring

```bash
# Resource usage
docker stats

# Service health
docker compose ps

# Check Kafka topics
docker compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Check Redis keys
docker compose exec redis redis-cli KEYS '*'
```

### GCP Monitoring

```bash
# View services
gcloud run services list --region $GCP_REGION

# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# View metrics in Cloud Console
open "https://console.cloud.google.com/run?project=${GCP_PROJECT_ID}"
```

---

## 💰 Cost Optimization

### Development
- Use local Docker Compose (free)
- Or use GCP free tier (limited)

### Production (Estimated Monthly Costs)
- Cloud Run API: $20-50
- Cloud Run Processor: $30-80
- Memorystore Redis (1GB): $45
- Confluent Kafka Basic: $360
- Cloud Storage: $1-5
- **Total: ~$450-550/month**

### Reduce Costs
- Use smaller Redis instance
- Reduce processor instances
- Use self-hosted Kafka on GCE
- Implement request caching

---

## 🎉 Next Steps

After successful deployment:

1. **Configure more languages** - Add languages via Redis
2. **Monitor performance** - Set up alerts and dashboards
3. **Add more RSS feeds** - Update `config/sources.yaml`
4. **Custom voices** - Configure ElevenLabs voices per language
5. **Setup CI/CD** - Automate deployments with GitHub Actions

---

## 📚 Additional Resources

- [Full Deployment Guide](DEPLOYMENT.md)
- [Architecture Documentation](ARCHITECTURE.md)
- [API Documentation](API.md)
- [Testing Guide](TESTING.md)

---

**Need help?** Check the logs first:
```bash
# Local
docker compose logs -f [service]

# GCP
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```
