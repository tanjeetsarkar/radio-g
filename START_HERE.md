# 🎯 Simplified Deployment - Quick Start

## ✨ New Unified Deployment System

You now have **one deployment script** that handles both local and production deployments!

---

## 🚀 Quick Start (3 Steps)

### Step 1: Create Environment File

**For Local Development:**
```bash
# Interactive setup
./scripts/create_env.sh
# Select option 1 (Local development)

# OR copy template manually
cp .env.example .env
# Edit .env and add your API keys
```

**For Production (GCP):**
```bash
# Interactive setup
./scripts/create_env.sh
# Select option 2 (Production/GCP)

# OR copy template manually
cp .env.prod.example .env.prod
# Edit .env.prod with your GCP settings
```

### Step 2: Deploy

**Local:**
```bash
./scripts/deploy.sh .env
```

**Production:**
```bash
./scripts/deploy.sh .env.prod
```

### Step 3: Access Your Application

**Local URLs:**
- Frontend: http://localhost:3000
- API: http://localhost:8000/docs

**Production URLs:**
- Displayed after deployment completes

---

## 📋 Environment Files Explained

### `.env` - Local Development
```bash
DEPLOYMENT_TARGET=local          # Deploy to Docker locally
GEMINI_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
REDIS_HOST=redis
```

### `.env.prod` - Production (GCP)
```bash
DEPLOYMENT_TARGET=gcp            # Deploy to Google Cloud
GCP_PROJECT_ID=your-project
GCP_REGION=us-central1
GEMINI_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
KAFKA_BOOTSTRAP_SERVERS=pkc-xxx.confluent.cloud:9092
REDIS_HOST=10.x.x.x             # From GCP Memorystore
```

---

## 🔄 Complete Workflow

```bash
# 1. Setup environment (one-time)
./scripts/create_env.sh

# 2. Deploy locally
./scripts/deploy.sh .env

# 3. Make changes, redeploy
# ... edit code ...
./scripts/deploy.sh .env

# 4. When ready, deploy to production
./scripts/deploy.sh .env.prod
```

---

## 📊 What Each Script Does

### `./scripts/create_env.sh`
Interactive wizard to create `.env` or `.env.prod` files

### `./scripts/deploy.sh <env-file>`
**Single script** that:
- ✅ Detects deployment target (local or GCP)
- ✅ Builds Docker images
- ✅ Deploys services
- ✅ Runs tests automatically (for local)
- ✅ Shows service URLs

### `./scripts/test_deployment.sh`
Tests the deployment (runs automatically for local deploys)

---

## 💡 Common Commands

```bash
# Deploy locally
./scripts/deploy.sh .env

# Deploy to production
./scripts/deploy.sh .env.prod

# View local logs
docker compose logs -f

# View GCP logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Stop local services
docker compose down
```

---

## 🎓 First Time Setup

### Local Development

1. **Prerequisites:** Docker installed and running
2. **Create config:** `./scripts/create_env.sh` → Select 1
3. **Deploy:** `./scripts/deploy.sh .env`
4. **Done!** Access at http://localhost:3000

### Production (GCP)

1. **Setup GCP** (one-time):
   ```bash
   # Create project
   gcloud projects create your-project-id
   gcloud config set project your-project-id
   
   # Enable APIs
   gcloud services enable run.googleapis.com redis.googleapis.com
   
   # Create Redis
   gcloud redis instances create news-redis --size=1 --region=us-central1
   
   # Get Redis host
   gcloud redis instances describe news-redis --region=us-central1 --format="value(host)"
   ```

2. **Setup Kafka** (one-time):
   - Sign up at https://www.confluent.io/
   - Create cluster and topics
   - Get API credentials

3. **Create config:** `./scripts/create_env.sh` → Select 2
4. **Deploy:** `./scripts/deploy.sh .env.prod`
5. **Done!** URLs displayed after deployment

---

## 🆚 Deployment Comparison

| Feature | Local (`.env`) | Production (`.env.prod`) |
|---------|----------------|--------------------------|
| **Target** | Docker Compose | Google Cloud Run |
| **Redis** | Local container | GCP Memorystore |
| **Kafka** | Local container | Confluent Cloud |
| **Cost** | Free | ~$450-550/month |
| **Setup Time** | 5 minutes | 30 minutes (first time) |
| **Scalability** | Single machine | Auto-scaling |
| **Use Case** | Development, Testing | Production |

---

## 🐛 Troubleshooting

### Local Deployment Issues

**Problem:** Docker not running
```bash
# Start Docker Desktop or daemon
sudo systemctl start docker
```

**Problem:** Ports already in use
```bash
# Stop existing services
docker compose down
# Or change ports in docker compose.yml
```

**Problem:** Services not healthy
```bash
# Check logs
docker compose logs -f [service-name]
# Restart
docker compose restart
```

### GCP Deployment Issues

**Problem:** Not authenticated
```bash
gcloud auth login
gcloud auth configure-docker
```

**Problem:** Secrets missing
```bash
# View secrets
gcloud secrets list

# Create if missing
echo -n "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
```

**Problem:** Deployment fails
```bash
# Check logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Check service status
gcloud run services list
```

---

## 📚 Documentation

- **[DEPLOYMENT_UNIFIED.md](DEPLOYMENT_UNIFIED.md)** - Complete unified deployment guide
- **[QUICKSTART.md](QUICKSTART.md)** - Detailed setup instructions
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Comprehensive deployment docs
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture

---

## ✅ Success Checklist

After deployment, verify:

- [ ] Frontend loads (http://localhost:3000 or production URL)
- [ ] API returns data: `/health`, `/languages`, `/news?lang=en`
- [ ] News articles appear in frontend
- [ ] Language switching works
- [ ] No errors in logs

---

## 🎉 You're All Set!

**Start now:**
```bash
# Create environment and deploy locally
./scripts/create_env.sh
./scripts/deploy.sh .env

# Visit http://localhost:3000
```

**Need help?** Check logs:
- Local: `docker compose logs -f`
- GCP: `gcloud logging read "resource.type=cloud_run_revision" --limit 50`
