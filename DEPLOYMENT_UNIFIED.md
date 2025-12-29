# 🚀 Unified Deployment System - Quick Reference

## Overview

You now have a **single deployment script** that handles both local and GCP deployments based on environment files.

## 📁 Environment Files

### 1. `.env` - Local Development
```bash
DEPLOYMENT_TARGET=local
ENVIRONMENT=development
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
REDIS_HOST=redis
# ... other local settings
```

### 2. `.env.prod` - Production/GCP
```bash
DEPLOYMENT_TARGET=gcp
ENVIRONMENT=production
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
KAFKA_BOOTSTRAP_SERVERS=pkc-xxx.confluent.cloud:9092
REDIS_HOST=10.x.x.x  # GCP Memorystore
# ... other production settings
```

## 🎯 Deployment Commands

### Local Deployment
```bash
# Deploy to local Docker
./scripts/deploy.sh .env
```

This will:
1. ✅ Build Docker images
2. ✅ Start infrastructure (Redis, Kafka)
3. ✅ Deploy all services
4. ✅ Run deployment tests automatically
5. ✅ Display service URLs

**Services available at:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- Kafka UI: http://localhost:8080

### Production/GCP Deployment
```bash
# Deploy to Google Cloud Platform
./scripts/deploy.sh .env.prod
```

This will:
1. ✅ Verify GCP authentication
2. ✅ Build and push Docker images to GCR
3. ✅ Deploy to Cloud Run
4. ✅ Configure all services
5. ✅ Display production URLs

## 🛠️ Setup Instructions

### First Time Setup - Local

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env and add your API keys
nano .env

# 3. Set deployment target
DEPLOYMENT_TARGET=local

# 4. Deploy
./scripts/deploy.sh .env
```

### First Time Setup - Production

```bash
# 1. Create GCP infrastructure (one-time)
export GCP_PROJECT_ID=your-project-id
export GCP_REGION=us-central1

gcloud projects create $GCP_PROJECT_ID
gcloud config set project $GCP_PROJECT_ID

# Enable APIs
gcloud services enable run.googleapis.com redis.googleapis.com secretmanager.googleapis.com

# Create Redis
gcloud redis instances create news-redis \
  --size=1 --region=$GCP_REGION --redis-version=redis_7_0 --tier=basic

# Get Redis host
REDIS_HOST=$(gcloud redis instances describe news-redis --region=$GCP_REGION --format="value(host)")

# 2. Setup Confluent Kafka
# - Sign up at https://www.confluent.io/
# - Create cluster and topics
# - Get bootstrap servers and API credentials

# 3. Create production environment file
cp .env.prod.example .env.prod

# 4. Edit .env.prod with your values
nano .env.prod

# Update these values:
# - GCP_PROJECT_ID=your-actual-project-id
# - GCP_REGION=us-central1
# - REDIS_HOST=<from gcloud command above>
# - KAFKA_BOOTSTRAP_SERVERS=<from Confluent>
# - KAFKA_API_KEY and KAFKA_API_SECRET=<from Confluent>
# - GEMINI_API_KEY=<your key>
# - ELEVENLABS_API_KEY=<your key>

# 5. Deploy to GCP
./scripts/deploy.sh .env.prod
```

## 📊 What the Script Does

### For Local Deployment (`DEPLOYMENT_TARGET=local`)

1. **Pre-checks**: Validates Docker is running
2. **Build**: Creates Docker images for all services
3. **Infrastructure**: Starts Redis, Kafka, Zookeeper
4. **Seed**: Configures language settings
5. **Deploy**: Starts Fetcher, Processor, API, Frontend
6. **Verify**: Checks health endpoints
7. **Test**: Automatically runs `test_deployment.sh`

### For GCP Deployment (`DEPLOYMENT_TARGET=gcp`)

1. **Pre-checks**: Validates gcloud CLI and authentication
2. **Secrets**: Creates/verifies GCP secrets
3. **Build**: Creates Docker images
4. **Push**: Uploads to Google Container Registry
5. **Deploy**: Deploys to Cloud Run services
6. **Configure**: Sets environment variables and scaling
7. **Verify**: Checks API health

## 🔄 Workflow Examples

### Develop Locally, Deploy to Production

```bash
# 1. Develop and test locally
./scripts/deploy.sh .env

# 2. Make changes to code
# ... edit files ...

# 3. Test locally again
docker compose down
./scripts/deploy.sh .env

# 4. When ready, deploy to production
./scripts/deploy.sh .env.prod
```

### Quick Iteration During Development

```bash
# After making changes, rebuild specific service
docker compose build news-api
docker compose restart news-api

# Or rebuild everything
./scripts/deploy.sh .env
```

### Switch Between Environments

```bash
# Test in local
./scripts/deploy.sh .env

# Deploy to staging (create .env.staging)
./scripts/deploy.sh .env.staging

# Deploy to production
./scripts/deploy.sh .env.prod
```

## 🧪 Testing

The deployment script automatically runs tests for local deployments. For manual testing:

```bash
# Test local deployment
./scripts/test_deployment.sh

# Test specific endpoints
curl http://localhost:8000/health
curl http://localhost:8000/languages
curl http://localhost:8000/news?lang=en
```

## 🔍 Monitoring & Logs

### Local

```bash
# View all services
docker compose ps

# View logs
docker compose logs -f
docker compose logs -f news-api

# Check Kafka
docker compose exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

### GCP

```bash
# View services
gcloud run services list --region us-central1

# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Stream logs
gcloud logging tail "resource.type=cloud_run_revision"
```

## 🛑 Stopping Services

### Local

```bash
# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v
```

### GCP

```bash
# Scale down to zero
gcloud run services update news-api --min-instances 0 --region us-central1

# Or delete services
gcloud run services delete news-api --region us-central1
```

## ⚙️ Configuration Options

### `.env` and `.env.prod` Variables

**Required Variables:**
- `DEPLOYMENT_TARGET` - `local` or `gcp`
- `GEMINI_API_KEY` - Google Gemini API key
- `ELEVENLABS_API_KEY` - ElevenLabs API key

**GCP-Specific Variables:**
- `GCP_PROJECT_ID` - Your GCP project ID
- `GCP_REGION` - Deployment region (default: us-central1)
- `REDIS_HOST` - GCP Memorystore Redis host
- `KAFKA_BOOTSTRAP_SERVERS` - Confluent Cloud bootstrap servers
- `KAFKA_API_KEY` and `KAFKA_API_SECRET` - Kafka credentials

**Scaling Variables (GCP only):**
- `API_MIN_INSTANCES` / `API_MAX_INSTANCES`
- `PROCESSOR_MIN_INSTANCES` / `PROCESSOR_MAX_INSTANCES`
- `FRONTEND_MIN_INSTANCES` / `FRONTEND_MAX_INSTANCES`
- `API_MEMORY` / `API_CPU`
- `PROCESSOR_MEMORY` / `PROCESSOR_CPU`

## 📝 Example .env.prod

```bash
# Deployment
DEPLOYMENT_TARGET=gcp
ENVIRONMENT=production
LOG_LEVEL=INFO

# GCP
GCP_PROJECT_ID=radio-g-prod
GCP_REGION=us-central1

# API Keys
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
ELEVENLABS_API_KEY=sk_XXXXXXXXXXXXXXXXXXXXXXXXXX

# Redis (GCP Memorystore)
REDIS_HOST=10.128.0.3
REDIS_PORT=6379
REDIS_SSL=true

# Kafka (Confluent Cloud)
KAFKA_BOOTSTRAP_SERVERS=pkc-xxx.us-east-1.aws.confluent.cloud:9092
KAFKA_API_KEY=XXXXXXXXXX
KAFKA_API_SECRET=YYYYYYYYYY

# Scaling
API_MIN_INSTANCES=1
API_MAX_INSTANCES=10
PROCESSOR_MIN_INSTANCES=2
PROCESSOR_MAX_INSTANCES=20
```

## 🚨 Troubleshooting

### Issue: Script fails with "Environment file not found"
```bash
# Make sure you created the env file
cp .env.example .env
# or
cp .env.prod.example .env.prod
```

### Issue: "DEPLOYMENT_TARGET not set"
```bash
# Add to your env file
echo "DEPLOYMENT_TARGET=local" >> .env
```

### Issue: Local deployment - Kafka not ready
```bash
# Wait longer or check logs
docker compose logs kafka
docker compose restart kafka
```

### Issue: GCP deployment - Authentication failed
```bash
gcloud auth login
gcloud auth configure-docker
```

### Issue: GCP deployment - Secrets not found
```bash
# Create secrets manually
echo -n "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
echo -n "$ELEVENLABS_API_KEY" | gcloud secrets create elevenlabs-api-key --data-file=-
```

## 📚 Related Documentation

- [QUICKSTART.md](QUICKSTART.md) - Detailed setup guide
- [DEPLOYMENT.md](DEPLOYMENT.md) - Comprehensive deployment docs
- [DEPLOYMENT_WORKFLOW.md](DEPLOYMENT_WORKFLOW.md) - Complete workflow
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture

---

**Quick Commands:**
```bash
# Local deployment
./scripts/deploy.sh .env

# Production deployment
./scripts/deploy.sh .env.prod

# View logs (local)
docker compose logs -f

# View logs (GCP)
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```
